from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict

from pymongo.collection import Collection
from pymongo import UpdateOne

# sentence-transformers / torch
from sentence_transformers import SentenceTransformer, InputExample, losses
import torch
from torch.utils.data import DataLoader


# -------------------------------
# Model utilities
# -------------------------------


DEFAULT_BASE_MODEL = "intfloat/multilingual-e5-large"


def _select_device() -> str:
    """Return 'cuda' only if a CUDA device is available and architecture is supported by current PyTorch wheel."""
    if not torch.cuda.is_available():
        return "cpu"
    try:
        major, minor = torch.cuda.get_device_capability(0)
        # Supported SM list per current wheel note (sm_50, sm_60, sm_70, sm_75, sm_80, sm_86, sm_90)
        supported = {(5, 0), (6, 0), (7, 0), (7, 5), (8, 0), (8, 6), (9, 0)}
        if (major, minor) in supported:
            return "cuda"
        # Unknown/newer arch -> prefer CPU to avoid runtime errors
        return "cpu"
    except Exception:
        return "cpu"


def _load_model(base_model: str = DEFAULT_BASE_MODEL, finetuned_dir: Optional[str] = None, *, device: Optional[str] = None) -> SentenceTransformer:
    """Load a SentenceTransformer model.

    - If finetuned_dir exists and is non-empty, load from there.
    - Otherwise download/load the base model from the hub.
    """
    device = device or _select_device()
    if finetuned_dir:
        p = Path(finetuned_dir)
        print(p)
        if p.exists() and any(p.iterdir()):
            return SentenceTransformer(str(p), device=device)
    return SentenceTransformer(base_model, device=device)


def _prepare_text(text: str, *, prefix: str = "passage: ") -> str:
    # E5 models expect a prefix. Use passage: for documents.
    t = str(text or "").strip()
    if not t:
        return t
    # Avoid double-prefixing
    if t.startswith("passage:") or t.startswith("query:"):
        return t
    return f"{prefix}{t}"


# -------------------------------
# Training (optional fine-tune)
# -------------------------------


@dataclass
class TrainConfig:
    output_dir: str = "models/e5-finetuned"
    epochs: int = 1
    batch_size: int = 64
    shuffle: bool = True


def collect_training_corpus(col: Collection, *, limit_docs: Optional[int] = None) -> List[str]:
    """Collect a list of texts from both sentences[] and sentence_heads[].text.

    Returns:
        texts: List[str] - deduplicated texts for training
        doc_ids: List - list of document _id's used for training
    """
    projection = {"sentences.text": 1, "sentence_heads.text": 1}
    query = {"$or": [
        {"process.finetuned": {"$exists": False}},
        {"process.finetuned": False}
    ]}
    cursor = col.find(query, projection=projection, no_cursor_timeout=True)
    if limit_docs is not None:
        cursor = cursor.limit(limit_docs)
    seen = set()
    texts: List[str] = []
    doc_ids: List = []
    try:
        for doc in cursor:
            used = False
            for s in (doc.get("sentences") or []):
                t = str((s or {}).get("text", "")).strip()
                if t and t not in seen:
                    seen.add(t)
                    texts.append(t)
                    used = True
            for h in (doc.get("sentence_heads") or []):
                t = str((h or {}).get("text", "")).strip()
                if t and t not in seen:
                    seen.add(t)
                    texts.append(t)
                    used = True
            if used and doc.get("_id") is not None:
                doc_ids.append(doc["_id"])
    finally:
        try:
            cursor.close()
        except Exception:
            pass
    return texts, doc_ids


def finetune_model(
    base_model: str,
    texts: List[str],
    cfg: TrainConfig,
    *,
    device: Optional[str] = None,
) -> str:
    """Unsupervised SimCSE-style fine-tuning using identical pairs with dropout.

    Returns the path to the saved finetuned model directory.
    """
    if not texts:
        return cfg.output_dir

    device = device or _select_device()
    model = SentenceTransformer(base_model, device=device)

    # Prepare InputExamples as (text, text) pairs
    train_examples = [InputExample(texts=[_prepare_text(t), _prepare_text(t)]) for t in texts]
    train_dataloader = DataLoader(train_examples, shuffle=cfg.shuffle, batch_size=cfg.batch_size)
    train_loss = losses.MultipleNegativesRankingLoss(model)

    os.makedirs(cfg.output_dir, exist_ok=True)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=cfg.epochs,
        output_path=cfg.output_dir,
        show_progress_bar=True,
    )
    return cfg.output_dir


def mark_finetuned(col: Collection, doc_ids: List) -> int:
    """Set process.finetuned: true for all docs with _id in doc_ids."""
    from bson import ObjectId
    print("mark_finetuned doc_ids:", doc_ids)
    if not doc_ids:
        print("No doc_ids to update.")
        return 0
    # Ensure all doc_ids are ObjectId
    doc_ids_obj = [ObjectId(x) if not isinstance(x, ObjectId) else x for x in doc_ids]
    res = col.update_many({"_id": {"$in": doc_ids_obj}}, {"$set": {"process.finetuned": True}})
    print("update_many matched:", res.matched_count, "modified:", res.modified_count)
    return res.modified_count


# -------------------------------
# Embedding updater (incremental)
# -------------------------------


def _texts_to_embed(doc: dict) -> Tuple[List[str], List[Tuple[str, int, int]]]:
    """Collect texts that need embeddings.

    Returns:
      - texts: list[str] texts to embed (prefixed for E5)
      - index_map: list of tuples (section, index_in_section, kind), where section ∈ {"sentences", "sentence_heads"}
                   and kind is 0 for sentences, 1 for sentence_heads (kept for clarity)
    """
    pending: List[str] = []
    index_map: List[Tuple[str, int, int]] = []

    sents = list(doc.get("sentences") or [])
    for i, s in enumerate(sents):
        if not isinstance(s, dict):
            continue
        if "embedding" in s and isinstance(s.get("embedding"), (list, tuple)) and len(s.get("embedding")) > 0:
            continue
        text = str(s.get("text", "")).strip()
        if text:
            pending.append(_prepare_text(text))
            index_map.append(("sentences", i, 0))

    heads = list(doc.get("sentence_heads") or [])
    for j, h in enumerate(heads):
        if not isinstance(h, dict):
            continue
        if "embedding" in h and isinstance(h.get("embedding"), (list, tuple)) and len(h.get("embedding")) > 0:
            continue
        text = str(h.get("text", "")).strip()
        if text:
            pending.append(_prepare_text(text))
            index_map.append(("sentence_heads", j, 1))

    return pending, index_map


def update_corpus_embeddings(
    col: Collection,
    *,
    base_model: str = DEFAULT_BASE_MODEL,
    finetuned_dir: Optional[str] = None,
    limit: Optional[int] = None,
    batch: int = 100,
    missing_only: bool = True,
    encode_batch_size: int = 64,
    device_override: Optional[str] = None,
    verbose: bool = False,
    embeddings_collection_name: str = "embeddings",
) -> int:
    """Embed sentences and sentence_heads incrementally and set process.embeddings=true.

    - Only adds embeddings where missing; existing embeddings are preserved.
    - By default, processes only documents with process.embeddings=false/missing.
    """
    base_query = {"sentences": {"$exists": True, "$ne": []}}
    if missing_only:
        query: Dict = {
            "$and": [
                base_query,
                {"$or": [
                    {"process.embeddings": {"$exists": False}},
                    {"process.embeddings": False},
                ]},
            ]
        }
    else:
        query = base_query

    projection = {"sentences": 1, "sentence_heads": 1}
    cursor = col.find(query, projection=projection, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    device = device_override or _select_device()
    if verbose:
        print(f"embeddings: using device -> {device}")
    model = _load_model(base_model, finetuned_dir, device=device)

    from .embeddings_store import insert_embeddings
    from pymongo import UpdateOne
    client = col.database.client
    emb_col = client[col.database.name][embeddings_collection_name]

    ops: List[UpdateOne] = []
    modified_docs = 0
    processed = 0
    try:
        for doc in cursor:
            _id = doc.get("_id")
            to_embed, index_map = _texts_to_embed(doc)
            if not to_embed:
                # No new embeddings needed; still set the flag so we don't revisit unless --all
                ops.append(UpdateOne({"_id": _id}, {"$set": {"process.embeddings": True}}))
            else:
                # Compute embeddings in batches
                embeddings: List[List[float]] = []
                start = 0
                while start < len(to_embed):
                    chunk = to_embed[start:start + encode_batch_size]
                    vecs = model.encode(
                        chunk,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        batch_size=encode_batch_size,
                        device=device,
                    )
                    embeddings.extend(v.astype("float32").tolist() for v in vecs)
                    start += encode_batch_size

                # Insert embeddings to embeddings collection and get ids
                section_indices = [(section, idx) for (section, idx, kind) in index_map]
                sent_indices = [idx for (section, idx) in section_indices if section == "sentences"]
                head_indices = [idx for (section, idx) in section_indices if section == "sentence_heads"]
                sent_vecs = [vec for (section, idx), vec in zip(section_indices, embeddings) if section == "sentences"]
                head_vecs = [vec for (section, idx), vec in zip(section_indices, embeddings) if section == "sentence_heads"]

                sent_ids = insert_embeddings(emb_col, _id, "sentences", sent_vecs, sent_indices) if sent_vecs else []
                head_ids = insert_embeddings(emb_col, _id, "sentence_heads", head_vecs, head_indices) if head_vecs else []

                # Apply embedding_id to doc copy
                new_sentences = list(doc.get("sentences") or [])
                new_heads = list(doc.get("sentence_heads") or [])
                sent_ptr = 0
                head_ptr = 0
                for (section, idx, kind), vec in zip(index_map, embeddings):
                    if section == "sentences":
                        item = dict(new_sentences[idx]) if idx < len(new_sentences) else {}
                        if "embedding_id" not in item or not item.get("embedding_id"):
                            item["embedding_id"] = sent_ids[sent_ptr]
                            sent_ptr += 1
                            new_sentences[idx] = item
                    else:
                        item = dict(new_heads[idx]) if idx < len(new_heads) else {}
                        if "embedding_id" not in item or not item.get("embedding_id"):
                            item["embedding_id"] = head_ids[head_ptr]
                            head_ptr += 1
                            new_heads[idx] = item

                ops.append(
                    UpdateOne(
                        {"_id": _id},
                        {"$set": {"sentences": new_sentences, "sentence_heads": new_heads, "process.embeddings": True}},
                    )
                )

            processed += 1
            if len(ops) >= batch:
                res = col.bulk_write(ops, ordered=False)
                modified_docs += res.modified_count
                ops = []
        if ops:
            res = col.bulk_write(ops, ordered=False)
            modified_docs += res.modified_count
    finally:
        try:
            cursor.close()
        except Exception:
            pass
    if verbose:
        print(f"embeddings summary -> processed: {processed}, modified_docs: {modified_docs}")
    return modified_docs


__all__ = [
    "TrainConfig",
    "collect_training_corpus",
    "finetune_model",
    "update_corpus_embeddings",
    "mark_finetuned",
]
