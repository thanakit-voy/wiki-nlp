from __future__ import annotations

import re
from typing import Set

# External endpoints
WIKI_API = "https://th.wikipedia.org/w/api.php"

# Common whitespace pattern
WS_RE = re.compile(r"\s+")

# Wikipedia plaintext heading pattern (e.g., == Heading ==)
HEADING_RE = re.compile(r"^\s*(=+)\s*(.*?)\s*(=+)\s*$")

# Emoji and noise patterns for normalization
EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F]"  # Emoticons
    "|[\U0001F300-\U0001F5FF]"  # Symbols & pictographs
    "|[\U0001F680-\U0001F6FF]"  # Transport & map
    "|[\U0001F1E0-\U0001F1FF]"  # Flags
    "|[\U00002700-\U000027BF]"  # Dingbats
    "|[\U0001F900-\U0001F9FF]"  # Supplemental Symbols and Pictographs
    "|[\U00002600-\U000026FF]"  # Misc symbols
    , flags=re.UNICODE
)

# Characters to remove as non-human noise (tune as needed)
NOISE_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Thai digits ๐-๙ to ASCII 0-9
THAI_DIGIT_MAP = str.maketrans({
    "๐": "0", "๑": "1", "๒": "2", "๓": "3", "๔": "4",
    "๕": "5", "๖": "6", "๗": "7", "๘": "8", "๙": "9",
})

# Numeric-like patterns
RE_INT = re.compile(r"^[+-]?\d+$")
RE_DECIMAL = re.compile(r"^[+-]?\d+[\.,]\d+$")
RE_THOUSANDS = re.compile(r"^[+-]?(?:\d{1,3}(?:[ ,.'’]\d{3})+)(?:[\.,]\d+)?$")
RE_TIME = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
RE_FRACTION = re.compile(r"^\d+\/\d+$")
RE_RANGE = re.compile(r"^\d+[-–—]\d+$")
RE_PERCENT = re.compile(r"^[+-]?\d+(?:[\.,]\d+)?%$")
RE_PHONE = re.compile(r"^\+?\d[\d\-()\s]{6,}$")

THAI_NUMBER_WORDS: Set[str] = {
    "ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า",
    "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน", "จุด"
}

THAI_CONNECTORS_PREFIX: Set[str] = {"และ", "กับ", "ถึง", "ถึงแม้", "แม้ว่า", "แม้", "หรือ", "ไม่ก็"}

THAI_CONNECTORS_SUFFIX: Set[str] = {"แล้ว", "แต่", "ทั้งนี้", "อย่างไรก็ตาม", "ในขณะเดียวกัน"}

OPENING_PUNCTS: Set[str] = {'«', '“', '‘', '(', '[', '{', '<', '‹', '„', '‚', '〝', '（', '［', '｛', '＜'}

CLOSING_PUNCTS: Set[str] = {'»', '”', '’', ')', ']', '}', '>', '›', '“', '‘', '〞', '）', '］', '｝', '＞'}

EDGE_PUNCTS: Set[str] = OPENING_PUNCTS.union(CLOSING_PUNCTS).union({'"', "'", '‘', '’', '“', '”', '«', '»'})

OTHER_PUNCTS: Set[str] = {'!', '?', '.', ',', ';', ':', '…', 'ฯ', 'ฯลฯ', '-', '–', '—', '·', '•', '·', '/', '\\', '|', '~', '`', '@', '#', '$', '%', '^', '&', '*', '_', '=', '+'}

ALL_PUNCTS: Set[str] = EDGE_PUNCTS.union(OTHER_PUNCTS)