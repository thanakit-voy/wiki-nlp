from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from .text_normalize import normalize_text
from .constants import HEADING_RE




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


def split_paragraphs(content: str) -> List[str]:
    """Split section content into paragraphs separated by blank lines.

    Groups consecutive non-empty lines together; empty lines (or whitespace-only)
    act as paragraph delimiters.
    """
    lines = content.splitlines()
    paras: List[str] = []
    buf: List[str] = []
    for line in lines:
        if line.strip() == "":
            if buf:
                paras.append("\n".join(buf).strip())
                buf = []
        else:
            buf.append(line)
    if buf:
        paras.append("\n".join(buf).strip())
    # If no paragraphs found but content exists, return the content as one paragraph
    if not paras and content.strip():
        return [content.strip()]
    return paras


def split_nonempty_lines(block: str) -> List[str]:
    """Split a text block into non-empty trimmed lines."""
    out: List[str] = []
    for line in block.splitlines():
        t = line.strip()
        if t:
            out.append(t)
    return out


def to_corpus_records(title: str, sections: Dict[str, str]) -> List[Dict[str, object]]:
    created_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    records: List[Dict[str, object]] = []
    idx = 1
    for header, content in sections.items():
        # Normalize duplicate-suffixed keys like "Header (2)" back to base header text
        m = re.match(r"^(.*?)(?: \(\d+\))?$", header)
        header_base = (m.group(1) if m else header).strip()
        header_text = header_base if header_base != "_root" else ""
        paras = split_paragraphs(content)
        for para in paras:
            for line in split_nonempty_lines(para):
                norm = normalize_text(line)
                if not norm:
                    continue
                rec = {
                    "title": title,
                    "content_index": idx,
                    "raw": {
                        "header": header_text,
                        "content": norm,
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

def generate_records_grouped_by_file(cfg: SegmentDbConfig) -> Iterator[Tuple[str, List[Dict[str, object]]]]:
    """Yield (title, records_for_that_title) per file.

    Helpful to ensure we insert all sections of one article together,
    so we can safely mark the title as uploaded once inserted.
    """
    paths = sorted([p for p in cfg.articles_dir.glob("*.txt") if p.is_file()])
    if cfg.max_files is not None:
        paths = paths[: cfg.max_files]
    for p in paths:
        title = p.stem
        text = p.read_text(encoding="utf-8")
        sections = split_sections(text)
        records = to_corpus_records(title, sections)
        yield title, records
