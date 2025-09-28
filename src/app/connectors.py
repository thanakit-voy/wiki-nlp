from __future__ import annotations

from typing import Dict, List

from pymongo.collection import Collection
from pymongo import UpdateOne

from .constants import (
    THAI_CONNECTORS_PREFIX,
    THAI_CONNECTORS_SUFFIX,
    OPENING_PUNCTS,
    THAI_NUMBER_WORDS,
    ALL_PUNCTS,
    WS_RE,
)


def _lstrip_opening(text: str) -> str:
    i = 0
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    while i < n and text[i] in OPENING_PUNCTS:
        i += 1
    return text[i:]


def _rstrip_punct(text: str) -> str:
    i = len(text) - 1
    while i >= 0 and text[i].isspace():
        i -= 1
    while i >= 0 and text[i] in ALL_PUNCTS:
        i -= 1
    return text[: i + 1]


def _first_token(text: str) -> str:
    t = _lstrip_opening(text)
    parts = t.strip().split()
    return parts[0] if parts else ""


def _last_token(text: str) -> str:
    t = _rstrip_punct(text)
    parts = t.strip().split()
    return parts[-1] if parts else ""


def _has_opening_punct(text: str) -> bool:
    for ch in text.lstrip():
        return ch in OPENING_PUNCTS
    return False


def _normalize_space(text: str) -> str:
    return WS_RE.sub(" ", text).strip()


def _should_merge(prev_text: str, curr_item: dict, *, min_len: int) -> bool:
    curr_text = str(curr_item.get("text", ""))
    if not prev_text:
        return False

    # Conditions
    is_curr_short = len(curr_text) < min_len
    is_prev_short = len(prev_text) < min_len

    pos = (curr_item.get("pos") or "").upper()
    typ = (curr_item.get("type") or "").upper()
    is_curr_num = pos == "NUM" or typ == "NUM"

    first_tok = _first_token(curr_text)
    last_tok_prev = _last_token(prev_text)

    starts_with_connector = first_tok in THAI_CONNECTORS_PREFIX
    prev_ends_with_connector = last_tok_prev in THAI_CONNECTORS_SUFFIX

    has_opening = _has_opening_punct(curr_text)

    starts_with_thai_number = first_tok in THAI_NUMBER_WORDS

    return (
        is_curr_short
        or is_prev_short
        or is_curr_num
        or starts_with_connector
        or prev_ends_with_connector
        or has_opening
        or starts_with_thai_number
    )


def merge_sentences_array(sentences: List[dict], *, min_len: int) -> List[dict] | None:
    """Merge sentences based on connector rules.

    - Output items only contain {text}. Drops type/pos and created_at.
    - Returns None if no merges were applied.
    """
    if not sentences:
        return None

    out: List[dict] = []
    changed = False

    for item in sentences:
        text = str(item.get("text", "")).strip()
        if not text:
            # skip empty pieces entirely
            continue
        if not out:
            out.append({"text": text})
            continue

        prev = out[-1]
        if _should_merge(prev.get("text", ""), item, min_len=min_len):
            merged = _normalize_space(f"{prev.get('text', '').rstrip()} {text.lstrip()}")
            prev["text"] = merged
            changed = True
        else:
            out.append({"text": text})

    return out if changed else None


def update_corpus_connectors(
    col: Collection,
    *,
    limit: int | None = None,
    batch: int = 200,
    missing_only: bool = True,
    min_len: int = 25,
    verbose: bool = False,
) -> int:
    """Apply connector-based merging to documents' sentences.

    Sets process.connector=true after processing. Returns number of modified documents.
    """
    base = {"sentences": {"$exists": True, "$ne": []}}
    if missing_only:
        filt: Dict = {
            **base,
            "$or": [
                {"process.connector": {"$exists": False}},
                {"process.connector": False},
            ],
        }
    else:
        filt = base

    try:
        candidates = col.count_documents(filt)
        if verbose:
            print(f"connectors candidates: {candidates}")
    except Exception:
        candidates = None

    proj = {"sentences": 1}
    cursor = col.find(filt, projection=proj, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    ops: List[UpdateOne] = []
    modified_docs = 0
    changed_content = 0
    flagged_only = 0
    try:
        for doc in cursor:
            doc_id = doc.get("_id")
            sentences = list(doc.get("sentences") or [])
            new_sentences = merge_sentences_array(sentences, min_len=min_len)
            if new_sentences is None:
                ops.append(UpdateOne({"_id": doc_id}, {"$set": {"process.connector": True}}))
                flagged_only += 1
            else:
                ops.append(
                    UpdateOne(
                        {"_id": doc_id},
                        {"$set": {"sentences": new_sentences, "process.connector": True}},
                    )
                )
                changed_content += 1
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
        print(
            f"connectors summary -> changed_content: {changed_content}, flagged_only: {flagged_only}, modified_docs: {modified_docs}"
        )
    return modified_docs
