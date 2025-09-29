from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from pymongo.collection import Collection
from pymongo import UpdateOne

# External NLP libs
import stanza
import torch

try:
    from pythainlp.tokenize import word_tokenize
    from pythainlp.util import Trie
except Exception:
    # Defer import error to runtime if pythainlp is missing
    pass

from .constants import (
    THAI_DIGIT_MAP,
    RE_INT,
    RE_DECIMAL,
    RE_THOUSANDS,
    RE_TIME,
    RE_FRACTION,
    RE_RANGE,
    RE_PERCENT,
    RE_PHONE,
    WS_RE,
    THAI_MONTHS,
    CURRENCY_WORDS,
    CURRENCY_SYMBOLS,
    UNIT_DISTANCE,
    UNIT_WEIGHT,
    UNIT_VOLUME,
    UNIT_AREA,
    UNIT_TIME,
    TIME_TOKENS,
    ERA_TOKENS,
    PERCENT_TOKENS,
)


# -------------------------------
# Utilities
# -------------------------------


def _normalize_digits(text: str) -> str:
    return (text or "").translate(THAI_DIGIT_MAP)


def _is_number_like(text: str) -> bool:
    if not text:
        return False
    s = _normalize_digits(text.strip())
    if not any(ch.isdigit() for ch in s):
        return False
    return any(p.match(s) is not None for p in (RE_INT, RE_DECIMAL, RE_THOUSANDS, RE_TIME, RE_FRACTION, RE_RANGE, RE_PERCENT, RE_PHONE))


# Domain dictionaries moved to constants.py


# -------------------------------
# Custom dictionary loading for PyThaiNLP
# -------------------------------


@dataclass
class CustomDict:
    trie: Optional[Trie]
    size: int


def load_custom_dict(path: str = "data/input/custom_dict.txt") -> CustomDict:
    try:
        if not os.path.exists(path):
            return CustomDict(trie=None, size=0)
        with open(path, "r", encoding="utf-8") as f:
            words = [WS_RE.sub(" ", w.strip()) for w in f if w.strip()]
        if not words:
            return CustomDict(trie=None, size=0)
        # Build Trie for efficient tokenization hints
        trie = Trie(words)
        return CustomDict(trie=trie, size=len(words))
    except Exception:
        return CustomDict(trie=None, size=0)


# -------------------------------
# Stanza init (download model on-demand)
# -------------------------------


def _ensure_stanza(
    lang: str = "th",
    processors: str = "tokenize,pos,lemma,depparse",
    tokenize_pretokenized: bool = True,
) -> stanza.Pipeline:
    def _build(p: str) -> stanza.Pipeline:
        return stanza.Pipeline(
            lang=lang,
            processors=p,
            use_gpu=bool(torch.cuda.is_available()),
            tokenize_pretokenized=tokenize_pretokenized,
            verbose=False,
        )

    # Try full pipeline first
    try:
        return _build(processors)
    except Exception:
        # Try download if missing, then build again
        try:
            resources_dir = os.getenv("STANZA_RESOURCES_DIR")
            if resources_dir:
                stanza.download(lang, model_dir=resources_dir)
            else:
                stanza.download(lang)
        except Exception:
            pass
        # Try again with full processors
        try:
            return _build(processors)
        except Exception:
            # Gradually degrade: remove lemma, then depparse, but keep tokenize for POS requirements
            for p in ("tokenize,pos,depparse", "tokenize,pos"):
                try:
                    return _build(p)
                except Exception:
                    continue
            # As a last resort, raise the original error
            return _build("tokenize,pos")


# -------------------------------
# Classification heuristics
# -------------------------------


def _classify_numeric(idx: int, words: Sequence[Dict]) -> Optional[str]:
    """Heuristics to assign a finer-grained type for numeric tokens based on context."""
    cur = words[idx]
    text = cur.get("text", "")
    t_norm = _normalize_digits(text)
    upos = (cur.get("pos") or cur.get("upos") or "").upper()

    prev_w = words[idx - 1] if idx - 1 >= 0 else None
    next_w = words[idx + 1] if idx + 1 < len(words) else None
    prev = (prev_w or {}).get("text", "")
    next = (next_w or {}).get("text", "")

    # Time like 12:34 or 12:34:56
    if RE_TIME.match(t_norm):
        return "TIME"

    # Percent
    if (next in PERCENT_TOKENS) or (text in PERCENT_TOKENS) or RE_PERCENT.match(t_norm):
        return "PERCENT"

    # Money
    if (prev in CURRENCY_SYMBOLS) or (next in CURRENCY_SYMBOLS) or (prev in CURRENCY_WORDS) or (next in CURRENCY_WORDS):
        return "MONEY"

    # Distance / Volume / Weight / Area / Duration by following unit
    if next in UNIT_DISTANCE:
        return "DISTANCE"
    if next in UNIT_VOLUME:
        return "VOLUME"
    if next in UNIT_WEIGHT:
        return "WEIGHT"
    if next in UNIT_AREA:
        return "AREA"
    if next in UNIT_TIME:
        return "DURATION"

    # Time words (e.g., 5 โมง, 10 นาฬิกา)
    if next in TIME_TOKENS:
        return "TIME"

    # Date contexts: adjacent to month or era or preceded/followed by ปี
    if (prev in ERA_TOKENS) or (next in ERA_TOKENS):
        # Likely year number
        return "YEAR"
    if (prev == "ปี") or (next == "ปี"):
        # Disambiguate short numbers as year if large (>= 1000)
        try:
            val = int("".join(ch for ch in t_norm if ch.isdigit()))
            if val >= 1000:
                return "YEAR"
        except Exception:
            pass
        # Otherwise duration (e.g., 3 ปี)
        if next == "ปี":
            return "DURATION"
    if (prev in THAI_MONTHS) or (next in THAI_MONTHS):
        return "DATE"

    # Range marks might be separated; keep NUMBER if unsure
    if upos == "NUM":
        return "NUMBER"
    return None


def _classify_non_numeric(idx: int, words: Sequence[Dict]) -> Optional[str]:
    text = words[idx].get("text", "")
    if text in THAI_MONTHS:
        return "MONTH"
    if text in CURRENCY_SYMBOLS or text in CURRENCY_WORDS:
        return "CURRENCY"
    if text in UNIT_DISTANCE:
        return "UNIT_DISTANCE"
    if text in UNIT_VOLUME:
        return "UNIT_VOLUME"
    if text in UNIT_WEIGHT:
        return "UNIT_WEIGHT"
    if text in UNIT_AREA:
        return "UNIT_AREA"
    if text in UNIT_TIME or text in TIME_TOKENS:
        return "TIME_UNIT"
    if text in ERA_TOKENS:
        return "ERA"
    if text in PERCENT_TOKENS:
        return "PERCENT_SIGN"
    # Ordinal indicators
    if text in {"อันดับ", "อันดับที่", "ครั้ง", "ครั้งที่", "ที่"}:
        return "ORDINAL_MARK"
    return None


def _assign_types(words: List[Dict]) -> None:
    for i, w in enumerate(words):
        upos = (w.get("pos") or w.get("upos") or "").upper()
        t: Optional[str]
        if upos == "NUM" or _is_number_like(w.get("text", "")):
            t = _classify_numeric(i, words)
        else:
            t = _classify_non_numeric(i, words)
        if t:
            w["type"] = t


# -------------------------------
# Tokenization and annotation per sentence
# -------------------------------


def _pretok_with_pythainlp(text: str, cd: Optional[Trie]) -> List[str]:
    # Prefer newmm with optional custom dict; keep_whitespace=False
    try:
        return word_tokenize(text, engine="newmm", keep_whitespace=False, custom_dict=cd)
    except TypeError:
        # Older PyThaiNLP versions may not accept custom_dict param
        return word_tokenize(text, engine="newmm", keep_whitespace=False)


def annotate_sentence(
    text: str,
    nlp: stanza.Pipeline,
    custom_trie: Optional[Trie] = None,
) -> List[Dict]:
    # 1) Pre-tokenize (so custom dict is respected)
    pretok = _pretok_with_pythainlp(text, custom_trie)
    if not pretok:
        pretok = [text]

    # Compute character offsets for each token by left-to-right alignment
    offsets: List[tuple[int | None, int | None]] = []
    pos = 0
    for tk in pretok:
        if not tk:
            offsets.append((None, None))
            continue
        # Try to find starting at current cursor
        idx = text.find(tk, pos)
        if idx == -1:
            # Try global search as fallback
            idx = text.find(tk)
        if idx == -1:
            # Skip intervening whitespace and approximate
            while pos < len(text) and text[pos].isspace():
                pos += 1
            start = pos
            end = start + len(tk)
            offsets.append((start, end))
            pos = end
        else:
            start = idx
            end = idx + len(tk)
            offsets.append((start, end))
            pos = end

    # 2) Run Stanza with pretokenized tokens
    doc = nlp([pretok])
    if not doc.sentences:
        # Fallback to simple tokens with offsets and sequential IDs
        out: List[Dict] = []
        for i, tk in enumerate(pretok):
            st, en = offsets[i] if i < len(offsets) else (None, None)
            out.append({
                "id": i + 1,
                "text": tk,
                "pos": None,
                "lemma": tk,
                "depparse": None,
                "head": 0,
                "start": st,
                "end": en,
                "lang": "th",
            })
        return out

    sent = doc.sentences[0]
    words: List[Dict] = []
    for i, w in enumerate(sent.words):
        st, en = offsets[i] if i < len(offsets) else (None, None)
        words.append({
            "id": getattr(w, "id", i + 1),
            "text": w.text,
            "pos": w.upos,
            "lemma": w.lemma if getattr(w, "lemma", None) is not None else w.text,
            "depparse": w.deprel if getattr(w, "deprel", None) is not None else None,
            "head": getattr(w, "head", 0),
            "start": st,
            "end": en,
            "lang": "th",
        })

    _assign_types(words)
    return words


# -------------------------------
# Corpus updater
# -------------------------------


def update_corpus_tokenize(
    col: Collection,
    *,
    limit: Optional[int] = None,
    batch: int = 200,
    missing_only: bool = True,
    verbose: bool = False,
) -> int:
    """Annotate each sentence with tokens (text,pos,lemma,depparse,type,lang) using Stanza.

    Skips documents with process.tokenize=true. After processing, sets process.tokenize=true.

    Returns number of documents modified.
    """
    base = {"sentences": {"$exists": True, "$ne": []}}
    if missing_only:
        # Also include docs where token structural fields are missing, even if process.tokenize is true
        missing_token_fields = {
            "$or": [
                {"sentences": {"$elemMatch": {"tokens": {"$elemMatch": {"id": {"$exists": False}}}}}},
                {"sentences": {"$elemMatch": {"tokens": {"$elemMatch": {"start": {"$exists": False}}}}}},
                {"sentences": {"$elemMatch": {"tokens": {"$elemMatch": {"end": {"$exists": False}}}}}},
                {"sentences": {"$elemMatch": {"tokens": {"$elemMatch": {"head": {"$exists": False}}}}}},
            ]
        }
        filt: Dict = {
            "$and": [
                base,
                {
                    "$or": [
                        {"process.tokenize": {"$exists": False}},
                        {"process.tokenize": False},
                        missing_token_fields,
                    ]
                },
            ]
        }
    else:
        filt = base

    projection = {"sentences": 1}

    cursor = col.find(filt, projection=projection, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    # Prepare NLP resources
    custom = load_custom_dict()
    if verbose:
        print(f"tokenize: custom_dict entries -> {custom.size}")
    nlp = _ensure_stanza()

    ops: List[UpdateOne] = []
    modified = 0
    processed = 0
    try:
        for doc in cursor:
            doc_id = doc.get("_id")
            sents = list(doc.get("sentences") or [])
            changed = False
            new_sents: List[dict] = []
            for s in sents:
                text = str(s.get("text", ""))
                tokens = annotate_sentence(text, nlp, custom.trie)
                # Compare with existing tokens (basic length check)
                if s.get("tokens") != tokens:
                    changed = True
                new_item = dict(s)
                new_item["tokens"] = tokens
                new_sents.append(new_item)
            if changed:
                ops.append(UpdateOne({"_id": doc_id}, {"$set": {"sentences": new_sents, "process.tokenize": True}}))
            else:
                # still ensure process flag is set
                ops.append(UpdateOne({"_id": doc_id}, {"$set": {"process.tokenize": True}}))
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
        print(f"tokenize summary -> processed: {processed}, modified_docs: {modified}")
    return modified
