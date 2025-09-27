from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

from .text_normalize import normalize_text


HEADING_RE = re.compile(r"^\s*(=+)\s*(.*?)\s*(=+)\s*$")


def split_sections(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    sections: Dict[str, List[str]] = {}
    current_key = "_root"
    sections[current_key] = []
    seen: Dict[str, int] = {}

    for line in lines:
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == len(m.group(3)):
            base = m.group(2).strip() or "_untitled"
            seen[base] = seen.get(base, 0) + 1
            key = base if seen[base] == 1 else f"{base} ({seen[base]})"
            current_key = key
            sections.setdefault(current_key, [])
        else:
            sections[current_key].append(line)

    return {k: "\n".join(v).rstrip("\n") for k, v in sections.items()}


def to_corpus_records(title: str, sections: Dict[str, str]) -> List[Dict[str, object]]:
    created_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    records: List[Dict[str, object]] = []
    idx = 1
    for header, content in sections.items():
        rec = {
            "title": title,
            "content_index": idx,
            "raw": {
                "header": header if header != "_root" else "",
                "content": normalize_text(content),
                "created_at": created_at,
            },
        }
        records.append(rec)
        idx += 1
    return records


@dataclass
class SegmentDbConfig:
    articles_dir: Path
    max_files: Optional[int] = None
    collection_name: str = "corpus"


def generate_records_from_dir(cfg: SegmentDbConfig) -> Iterator[Dict[str, object]]:
    paths = sorted([p for p in cfg.articles_dir.glob("*.txt") if p.is_file()])
    if cfg.max_files is not None:
        paths = paths[: cfg.max_files]
    for p in paths:
        title = p.stem
        text = p.read_text(encoding="utf-8")
        sections = split_sections(text)
        for rec in to_corpus_records(title, sections):
            yield rec
