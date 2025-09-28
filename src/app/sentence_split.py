from __future__ import annotations

from typing import Iterable, List

from pymongo.collection import Collection
from pymongo import UpdateOne
from .constants import WS_RE


def split_by_space(text: str) -> List[str]:
    if not text:
        return []
    # Split on any whitespace, drop empties
    parts = [p for p in WS_RE.split(text.strip()) if p]
    return parts


def build_sentences_array(text: str) -> List[dict]:
    tokens = split_by_space(text)
    return [{"text": t} for t in tokens]


def update_corpus_sentences(
    col: Collection,
    *,
    limit: int | None = None,
    batch: int = 500,
    missing_only: bool = True,
) -> int:
    """Populate the 'sentences' array for documents in corpus.

    Returns number of documents updated.
    """
    filt = {}
    if missing_only:
        # Select docs that have not been processed by sentence_split yet
        filt = {
            "$or": [
                {"process.sentence_split": {"$exists": False}},
                {"process.sentence_split": False},
            ]
        }

    proj = {"raw.content": 1}
    cursor = col.find(filt, projection=proj, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    ops: list[UpdateOne] = []
    updated = 0
    try:
        for doc in cursor:
            doc_id = doc.get("_id")
            content = (((doc or {}).get("raw") or {}).get("content")) or ""
            sentences = build_sentences_array(content)
            ops.append(
                UpdateOne(
                    {"_id": doc_id},
                    {"$set": {"sentences": sentences, "process.sentence_split": True}},
                )
            )
            if len(ops) >= batch:
                res = col.bulk_write(ops, ordered=False)
                updated += res.modified_count + res.upserted_count
                ops = []
        if ops:
            res = col.bulk_write(ops, ordered=False)
            updated += res.modified_count + res.upserted_count
    finally:
        try:
            cursor.close()
        except Exception:
            pass
    return updated
