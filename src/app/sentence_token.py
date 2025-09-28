from __future__ import annotations

import datetime as dt
from typing import Dict, List

from pymongo.collection import Collection
from pymongo import UpdateOne

try:
    from pythainlp.tokenize import sent_tokenize
except Exception as e:
    # Defer import error to runtime; this module requires pythainlp installed
    raise


def retokenize_sentences_array(sentences: List[dict]) -> List[dict] | None:
    """Return a new sentences array after Thai sentence tokenization.

    - Input is the existing sentences array (list of {text, created_at, ...}).
    - For each item, split its text by PyThaiNLP sent_tokenize and expand in place.
    - Preserve created_at from the original item for all produced sub-sentences.
    - Returns None if no changes were made (i.e., output equals input).
    """
    out: List[dict] = []
    changed = False
    for item in sentences:
        text = str(item.get("text", ""))
        created_at = item.get("created_at")
        subs = [s.strip() for s in (sent_tokenize(text) or []) if s and s.strip()]
        if subs and not (len(subs) == 1 and subs[0] == text):
            changed = True
        if not subs:
            # Keep as-is if tokenizer yields nothing
            out.append({"text": text, "created_at": created_at})
            continue
        for s in subs:
            out.append({"text": s, "created_at": created_at})
    return out if changed else None


def update_corpus_sentence_tokenization(
    col: Collection,
    *,
    limit: int | None = None,
    batch: int = 200,
    missing_only: bool = True,
    verbose: bool = False,
) -> int:
    """Re-tokenize existing sentences using PyThaiNLP and set process.sentence_token=true.

    Returns number of documents modified.
    """
    # Only process documents that have sentences and not yet processed by sentence_token
    base = {"sentences": {"$exists": True, "$ne": []}}
    if missing_only:
        filt: Dict = {
            **base,
            "$or": [
                {"process.sentence_token": {"$exists": False}},
                {"process.sentence_token": False},
            ],
        }
    else:
        filt = base

    # Optional pre-count to help diagnose "nothing happened" cases
    try:
        candidates = col.count_documents(filt)
        if verbose:
            print(f"sentence-token candidates: {candidates}")
    except Exception:
        candidates = None

    proj = {"sentences": 1}
    cursor = col.find(filt, projection=proj, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    ops: list[UpdateOne] = []
    modified_docs = 0
    changed_content = 0
    flagged_only = 0
    try:
        for doc in cursor:
            doc_id = doc.get("_id")
            sentences = list(doc.get("sentences") or [])
            new_sentences = retokenize_sentences_array(sentences)
            if new_sentences is None:
                # No change in content; still mark the process flag
                ops.append(UpdateOne({"_id": doc_id}, {"$set": {"process.sentence_token": True}}))
                flagged_only += 1
            else:
                ops.append(
                    UpdateOne(
                        {"_id": doc_id},
                        {"$set": {"sentences": new_sentences, "process.sentence_token": True}},
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
        # Note: modified_docs may be less than changed_content+flagged_only if some docs already matched set values
        print(
            f"sentence-token summary -> changed_content: {changed_content}, flagged_only: {flagged_only}, modified_docs: {modified_docs}"
        )
    return modified_docs
