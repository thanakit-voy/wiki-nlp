from __future__ import annotations

from typing import Dict, List, Optional

from pymongo.collection import Collection

from .constants import MASK_POS, NOT_MASK_TYPE


def _lemma(tok: dict) -> str:
    return str(tok.get("lemma") or tok.get("text") or "")


def _surface(tok: dict) -> str:
    return str(tok.get("text") or tok.get("lemma") or "")


def _deprel(tok: dict) -> str:
    return str(tok.get("depparse") or tok.get("deprel") or "dep")


def _upos(tok: dict) -> str:
    v = tok.get("pos") or tok.get("upos") or "X"
    return str(v).upper()


def _should_mask_other(tok: dict) -> bool:
    t = tok.get("type")
    if t:
        # If type exists and is in NOT_MASK_TYPE => do not mask
        if t in NOT_MASK_TYPE:
            return False
    # Else mask when POS is in MASK_POS
    return _upos(tok) in MASK_POS


def build_pattern_for_tokens(tokens: List[dict], pivot_index: int) -> str:
    """Build a masked pattern string for a token group given a pivot token index.

    - Pivot token is always masked as <WORD|{deprel}>.
    - Other tokens: if type in NOT_MASK_TYPE -> keep lemma; else if POS in MASK_POS -> mask as <POS|{deprel}>; else keep lemma.
    - Join pieces with space and preserve original order.
    """
    parts: List[str] = []
    for i, tok in enumerate(tokens):
        if i == pivot_index:
            parts.append(f"<WORD|{_deprel(tok)}>")
            continue
        if _should_mask_other(tok):
            parts.append(f"<{_upos(tok)}|{_deprel(tok)}>")
        else:
            parts.append(_lemma(tok))
    return " ".join(parts).strip()


def update_word_pattern_for_doc(words_col: Collection, patterns_col: Collection, sentence_heads: List[dict]) -> int:
    """Update the words collection using sentence_heads from a single corpus document.

    Returns number of upserts/updates performed (roughly equals number of pivot tokens processed).
    """
    updated = 0
    for sh in sentence_heads or []:
        toks = list(sh.get("tokens") or [])
        if not toks:
            continue
        for idx, tok in enumerate(toks):
            pos = _upos(tok)
            # Only record for pivot tokens whose POS is in MASK_POS
            if pos not in MASK_POS:
                continue
            word = _surface(tok)
            if not word:
                continue
            dep = _deprel(tok)
            key = f"{word} | {pos} | {dep}"

            pattern = build_pattern_for_tokens(toks, idx)

            # A) Upsert global pattern and increment its global count; get pattern _id
            res_pat = patterns_col.update_one(
                {"pattern": pattern},
                {"$setOnInsert": {"pattern": pattern}, "$inc": {"count": 1}},
                upsert=True,
            )
            if res_pat.upserted_id is not None:
                pattern_id = res_pat.upserted_id
            else:
                doc_pat = patterns_col.find_one({"pattern": pattern}, {"_id": 1})
                if not doc_pat:
                    # Extremely rare: fallback create
                    doc_pat = {"_id": patterns_col.insert_one({"pattern": pattern, "count": 1}).inserted_id}
                pattern_id = doc_pat["_id"]

            # B) Ensure word document exists and increment total usage count
            res_upsert = words_col.update_one(
                {"key": key},
                {
                    "$setOnInsert": {"word": word, "pos": pos, "depparse": dep, "patterns": []},
                    "$inc": {"count": 1},
                },
                upsert=True,
            )

            # C) Try to increment per-word pattern counter using pattern_id
            res_inc = words_col.update_one(
                {"key": key, "patterns.pattern_id": pattern_id},
                {"$inc": {"patterns.$.count": 1}},
                upsert=False,
            )

            # D) If pattern isn't present yet, push it
            res_push = None
            if res_inc.matched_count == 0:
                res_push = words_col.update_one(
                    {"key": key},
                    {"$push": {"patterns": {"pattern_id": pattern_id, "count": 1}}},
                    upsert=False,
                )

            updated += (
                (res_upsert.modified_count or 0)
                + (1 if res_upsert.upserted_id else 0)
                + (res_inc.modified_count or 0)
                + ((res_push.modified_count or 0) if res_push else 0)
            )
    return updated


def update_corpus_word_pattern(
    corpus_col: Collection,
    words_col: Collection,
    patterns_col: Collection,
    *,
    limit: Optional[int] = None,
    batch: int = 200,
    missing_only: bool = True,
    verbose: bool = False,
) -> int:
    """Generate masked word patterns from sentence_heads and record into words collection.

    - Skips corpus docs with process.word_pattern=true when missing_only is True.
    - After processing a corpus doc, sets process.word_pattern=true.
    - Writes (upserts) into words collection per (word|pos|deprel) key and per-pattern counts.
    """
    base = {"sentence_heads": {"$exists": True}}
    if missing_only:
        filt: Dict = {
            "$and": [
                base,
                {"$or": [
                    {"process.word_pattern": {"$exists": False}},
                    {"process.word_pattern": False},
                ]},
            ]
        }
    else:
        filt = base

    projection = {"sentence_heads": 1}
    cursor = corpus_col.find(filt, projection=projection, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    processed = 0
    flagged = 0
    try:
        for doc in cursor:
            sid = doc.get("_id")
            heads = list(doc.get("sentence_heads") or [])
            _ = update_word_pattern_for_doc(words_col, patterns_col, heads)

            # flag corpus doc
            res = corpus_col.update_one({"_id": sid}, {"$set": {"process.word_pattern": True}})
            flagged += res.modified_count
            processed += 1
    finally:
        try:
            cursor.close()
        except Exception:
            pass
    if verbose:
        print(f"word-pattern summary -> processed_docs: {processed}, flagged_docs: {flagged}")
    return flagged
