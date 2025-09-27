from __future__ import annotations

import datetime as dt
import re
from typing import Dict, List

from pymongo.collection import Collection
from pymongo import UpdateOne
from .constants import (
    THAI_DIGIT_MAP,
    RE_INT, RE_DECIMAL, RE_THOUSANDS, RE_TIME, RE_FRACTION,
    RE_RANGE, RE_PERCENT, RE_PHONE,
)


def normalize_digits(s: str) -> str:
    return s.translate(THAI_DIGIT_MAP)


def is_numeric_like(text: str) -> bool:
    if not text:
        return False
    s = normalize_digits(text.strip())
    # quick bail-out if no digits at all
    if not re.search(r"\d", s):
        return False
    return any(
        p.match(s) is not None
        for p in (
            RE_INT, RE_DECIMAL, RE_THOUSANDS, RE_TIME, RE_FRACTION,
            RE_RANGE, RE_PERCENT, RE_PHONE,
        )
    )


def tag_sentences_array(sentences: List[dict], created_at_iso: str | None = None) -> List[dict]:
    changed_any = False
    out: List[dict] = []
    created_at_iso = created_at_iso or dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    for s in sentences:
        item = dict(s)
        text = str(item.get("text", ""))
        if is_numeric_like(text):
            if item.get("type") != "NUM":
                item["type"] = "NUM"
                changed_any = True
            if item.get("pos") != "NUM":
                item["pos"] = "NUM"
                changed_any = True
            # do not change created_at if present; keep as is
        out.append(item)
    return out if changed_any else sentences


def tag_corpus_numbers(
    col: Collection,
    *,
    limit: int | None = None,
    batch: int = 200,
    missing_only: bool = False,
) -> int:
    """Add type=NUM and pos=NUM to numeric-like sentences in corpus.

    Returns number of documents modified.
    """
    # Base: require sentences present and non-empty to limit scope
    filt: Dict = {"sentences": {"$exists": True, "$ne": []}}
    if missing_only:
        # Select docs not yet processed by num_tag
        filt = {
            "sentences": {"$exists": True, "$ne": []},
            "$or": [
                {"process.num_tag": {"$exists": False}},
                {"process.num_tag": False},
            ],
        }

    proj = {"sentences": 1}
    cursor = col.find(filt, projection=proj, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    ops: list[UpdateOne] = []
    modified_docs = 0
    try:
        for doc in cursor:
            doc_id = doc.get("_id")
            sentences = list(doc.get("sentences") or [])
            new_sentences = tag_sentences_array(sentences)
            if new_sentences is sentences:
                # No sentence changes, but still mark process flag
                ops.append(UpdateOne({"_id": doc_id}, {"$set": {"process.num_tag": True}}))
            else:
                ops.append(
                    UpdateOne(
                        {"_id": doc_id},
                        {"$set": {"sentences": new_sentences, "process.num_tag": True}},
                    )
                )
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
    return modified_docs
