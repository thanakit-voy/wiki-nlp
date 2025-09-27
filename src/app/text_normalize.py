from __future__ import annotations

import re

# Basic emoji pattern (covers most common ranges)
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

# Collapse whitespace
WS_RE = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    if not s:
        return ""
    # Remove emojis and control characters
    s = EMOJI_RE.sub(" ", s)
    s = NOISE_RE.sub(" ", s)
    # Replace newlines/tabs with space and collapse
    s = s.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    s = WS_RE.sub(" ", s)
    return s.strip()
