from __future__ import annotations

from typing import Dict, List, Optional

from pymongo.collection import Collection
from pymongo import UpdateOne


def _lemma_or_text(tok: dict) -> str:
    v = tok.get("lemma")
    if v is None or v == "":
        return tok.get("text", "")
    return str(v)


def build_sentence_heads(tokens: List[dict]) -> List[dict]:
    """Build head-based phrases from a token list.

    For each unique head id (including 0 for root), collect tokens whose head equals that id, and also include the token
    whose id equals that head id (the governor). Skip head==0 for output. Keep the original order by token id.
    Returns a list of items: { head: <head_lemma>, text: <joined_lemmas>, tokens: [<token subset>] }.
    """
    if not tokens:
        return []

    # Map id -> token for quick lookup and preserve ordering by id
    id_to_tok: Dict[int, dict] = {}
    for t in tokens:
        try:
            tid = int(t.get("id"))
        except Exception:
            continue
        id_to_tok[tid] = t

    # Unique heads present in tokens (ints only)
    heads: List[int] = []
    seen = set()
    for t in tokens:
        h = t.get("head")
        if isinstance(h, int) and h not in seen:
            heads.append(h)
            seen.add(h)

    out: List[dict] = []
    for h in heads:
        if h == 0:
            continue  # skip root
        # collect tokens with head==h plus the governor (id==h)
        group: List[dict] = []
        for t in tokens:
            try:
                tid = int(t.get("id"))
            except Exception:
                continue
            if t.get("head") == h or tid == h:
                group.append(t)
        # Order by token id ascending
        try:
            group.sort(key=lambda x: int(x.get("id")))
        except Exception:
            pass

        # Determine head text
        head_tok: Optional[dict] = id_to_tok.get(h)
        head_text = _lemma_or_text(head_tok) if head_tok else str(h)
        text = " ".join(_lemma_or_text(t) for t in group).strip()
        out.append({"head": head_text, "text": text, "tokens": group})
    return out


def update_corpus_sentence_heads(
    col: Collection,
    *,
    limit: Optional[int] = None,
    batch: int = 200,
    missing_only: bool = True,
    verbose: bool = False,
) -> int:
    """Compute dependency-based head phrases for each sentence and store into sentence_heads.

    - Skips documents with process.sentence_heads=true when missing_only is True
    - After processing, sets process.sentence_heads=true
    - Requires sentences[].tokens
    """
    base = {"sentences": {"$exists": True, "$ne": []}, "sentences.tokens": {"$exists": True}}
    if missing_only:
        filt: Dict = {
            "$and": [
                base,
                {"$or": [
                    {"process.sentence_heads": {"$exists": False}},
                    {"process.sentence_heads": False},
                ]},
            ]
        }
    else:
        filt = base

    projection = {"sentences": 1}
    cursor = col.find(filt, projection=projection, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    ops: List[UpdateOne] = []
    modified = 0
    processed = 0
    try:
        for doc in cursor:
            doc_id = doc.get("_id")
            sentences = list(doc.get("sentences") or [])
            heads_all: List[dict] = []
            for s in sentences:
                toks = list(s.get("tokens") or [])
                heads = build_sentence_heads(toks)
                if heads:
                    heads_all.extend(heads)

            ops.append(
                UpdateOne(
                    {"_id": doc_id},
                    {"$set": {"sentence_heads": heads_all, "process.sentence_heads": True}},
                )
            )
            processed += 1
            if len(ops) >= batch:
                res = col.bulk_write(ops, ordered=False)
                modified += res.modified_count
                ops = []
        if ops:
            res = col.bulk_write(ops, ordered=False)
            modified += res.modified_count
    finally:
        try:
            cursor.close()
        except Exception:
            pass
    if verbose:
        print(f"sentence-heads summary -> processed: {processed}, modified_docs: {modified}")
    return modified
