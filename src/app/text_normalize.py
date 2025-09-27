from __future__ import annotations

from .constants import EMOJI_RE, NOISE_RE, WS_RE


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
