from __future__ import annotations

import re
from typing import Dict

from pymongo.collection import Collection
from pymongo import UpdateOne


# --- Text transformation ----------------------------------------------------

_RE_COLON_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
# For HH.MM + suffix handling:
# - Before 'น' (no nu), spaces may or may not exist
# - Case 'น.' (with dot): do NOT require space after it
# - Case 'น' (no dot): REQUIRE there is at least one space following 'น'
_RE_DOT_TIME_N_DOT = re.compile(r"(?<!\d)(?P<h>\d{1,2})\.(?P<m>[0-5]\d)\s*น\.")
_RE_DOT_TIME_N_SPACE = re.compile(r"(?<!\d)(?P<h>\d{1,2})\.(?P<m>[0-5]\d)\s*น(?= )")


def transform_thai_clock_in_text(text: str) -> str:
    """Normalize Thai time expressions in text.

    Rules:
      - Convert HH:MM to HH.MM
      - For HH.MM followed by "น." or "น" (with optional spaces), replace that suffix with "นาฬิกา".
      - For colon-form inputs with suffix, the first rule converts them to dot-form, then the suffix rule applies.

    Examples:
      01:00 น.  -> 01.00 นาฬิกา
      1:00 น    -> 1.00 นาฬิกา
      01.30 น.  -> 01.30 นาฬิกา
      01.30น    -> 01.30 นาฬิกา
      1:20      -> 1.20
    """
    if not text:
        return text

    # 1) Convert HH:MM -> HH.MM (strict minutes two digits; avoids touching ratios like 1:2)
    out = _RE_COLON_TIME.sub(lambda m: f"{m.group(1)}.{m.group(2)}", text)

    # 2) Replace suffixes with the rules above
    out = _RE_DOT_TIME_N_DOT.sub(lambda m: f"{m.group('h')}.{m.group('m')} นาฬิกา", out)
    out = _RE_DOT_TIME_N_SPACE.sub(lambda m: f"{m.group('h')}.{m.group('m')} นาฬิกา", out)
    # Normalize duplicate spaces and trim edges
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


# --- MongoDB updater --------------------------------------------------------

def update_corpus_thai_clock(
    col: Collection,
    *,
    limit: int | None = None,
    batch: int = 200,
    missing_only: bool = True,
    verbose: bool = False,
) -> int:
    """Update raw.content by normalizing Thai time expressions and set process.thai_clock=true.

    Returns number of documents modified by MongoDB.
    """
    base: Dict = {"raw.content": {"$type": "string"}}
    if missing_only:
        filt: Dict = {
            **base,
            "$or": [
                {"process.thai_clock": {"$exists": False}},
                {"process.thai_clock": False},
            ],
        }
    else:
        filt = base

    if verbose:
        try:
            print(f"thai-clock candidates: {col.count_documents(filt)}")
        except Exception:
            pass

    proj = {"raw.content": 1}
    cursor = col.find(filt, projection=proj, no_cursor_timeout=True)
    if limit is not None:
        cursor = cursor.limit(limit)

    ops: list[UpdateOne] = []
    modified_docs = 0
    changed_content = 0
    flagged_only = 0
    try:
        for doc in cursor:
            _id = doc.get("_id")
            content = doc.get("raw", {}).get("content", "")
            new_content = transform_thai_clock_in_text(str(content))
            if new_content != content:
                changed_content += 1
                ops.append(
                    UpdateOne(
                        {"_id": _id},
                        {"$set": {"raw.content": new_content, "process.thai_clock": True}},
                    )
                )
            else:
                flagged_only += 1
                ops.append(UpdateOne({"_id": _id}, {"$set": {"process.thai_clock": True}}))

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
            f"thai-clock summary -> changed_content: {changed_content}, flagged_only: {flagged_only}, modified_docs: {modified_docs}"
        )
    return modified_docs
