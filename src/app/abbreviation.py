from __future__ import annotations

from typing import Dict, List, Tuple, Any

from pymongo.collection import Collection
from pymongo import UpdateOne

try:
    from pythainlp.util import abbreviation_to_full_text
except Exception:
    # Defer import error to runtime
    raise


def _to_float(score: Any) -> float | None:
    try:
        return float(score)
    except Exception:
        try:
            return float(score.item())  # torch.Tensor
        except Exception:
            return None


def expand_abbreviation_for_text(text: str) -> Tuple[str, List[Tuple[str, float | None]]]:
    """Return best expanded text and all candidates with scores.

    - If no candidates, best is original text and candidates is [].
    - Scores are converted to float when possible.
    """
    if not text:
        return text, []
    try:
        cands = abbreviation_to_full_text(text) or []
    except Exception:
        cands = []
    norm_cands: List[Tuple[str, float | None]] = []
    for tup in cands:
        if isinstance(tup, (list, tuple)) and len(tup) >= 2:
            cand_text = str(tup[0])
            cand_score = _to_float(tup[1])
            norm_cands.append((cand_text, cand_score))
    if not norm_cands:
        return text, []
    # Pick best by score (None treated as -inf)
    def key_fn(it: Tuple[str, float | None]):
        s = it[1]
        return -1e18 if s is None else s

    best_text, _ = max(norm_cands, key=key_fn)
    return best_text, norm_cands


def update_corpus_abbreviation(
    col_corpus: Collection,
    *,
    limit: int | None = None,
    batch: int = 200,
    missing_only: bool = True,
    verbose: bool = False,
) -> int:
    """Expand abbreviations in sentences and record all candidates into abbreviation collection.

    - Updates corpus.sentences text to the highest-probability expansion when different.
    - Writes documents to abbreviation collection for every sentence with candidates, including all candidate forms.
    - Sets process.abbreviation=true on processed corpus documents.
    - Returns number of modified corpus documents.
    """
    base = {"sentences": {"$exists": True, "$ne": []}}
    if missing_only:
        filt: Dict = {
            **base,
            "$or": [
                {"process.abbreviation": {"$exists": False}},
                {"process.abbreviation": False},
            ],
        }
    else:
        filt = base

    try:
        candidates = col_corpus.count_documents(filt)
        if verbose:
            print(f"abbreviation candidates: {candidates}")
    except Exception:
        candidates = None

    proj = {"sentences": 1, "title": 1, "content_index": 1}
    cursor = col_corpus.find(filt, projection=proj, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    ops_corpus: List[UpdateOne] = []
    modified_docs = 0
    changed_docs = 0

    try:
        for doc in cursor:
            doc_id = doc.get("_id")
            title = doc.get("title")
            content_index = doc.get("content_index")
            sentences = list(doc.get("sentences") or [])

            new_sentences: List[dict] = []
            doc_changed = False

            for idx, item in enumerate(sentences):
                text = str((item or {}).get("text", ""))
                best_text, cand_list = expand_abbreviation_for_text(text)

                # Preserve other keys (e.g., type/pos) but replace text if changed
                new_item = dict(item)
                if best_text and best_text != text:
                    new_item["text"] = best_text
                    doc_changed = True
                new_sentences.append(new_item)

            # Write back to corpus (always set flag; update sentences only if changed)
            if doc_changed:
                ops_corpus.append(
                    UpdateOne(
                        {"_id": doc_id},
                        {"$set": {"sentences": new_sentences, "process.abbreviation": True}},
                    )
                )
                changed_docs += 1
            else:
                ops_corpus.append(UpdateOne({"_id": doc_id}, {"$set": {"process.abbreviation": True}}))

            if len(ops_corpus) >= batch:
                res = col_corpus.bulk_write(ops_corpus, ordered=False)
                modified_docs += res.modified_count
                ops_corpus = []

        # final flushes
        if ops_corpus:
            res = col_corpus.bulk_write(ops_corpus, ordered=False)
            modified_docs += res.modified_count
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    if verbose:
        print(f"abbreviation summary -> changed_docs: {changed_docs}, modified_docs: {modified_docs}")
    return modified_docs
