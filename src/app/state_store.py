from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Set, Tuple


def _ensure_sets(d: Dict) -> Dict[str, Set[str]]:
    return {
        "done": set(d.get("done", [])),
        "not_found": set(d.get("not_found", [])),
        "uploaded": set(d.get("uploaded", [])),
    }


def load_state_all(path: Path) -> Dict:
    if not path.exists():
        return {"done": [], "not_found": [], "uploaded": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # If corrupted, start fresh and keep a backup
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            path.replace(backup)
        except Exception:
            pass
        return {"done": [], "not_found": [], "uploaded": []}


def save_state_all(path: Path, state: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Normalize sets to lists for JSON
    d = load_state_all(path)
    d.update(state)
    for k in ("done", "not_found", "uploaded"):
        if isinstance(d.get(k), set):
            d[k] = sorted(d[k])
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_fetch_state(path: Path) -> Tuple[Set[str], Set[str], Dict]:
    d = load_state_all(path)
    sets = _ensure_sets(d)
    return sets["done"], sets["not_found"], d


def save_fetch_state(path: Path, done: Set[str], not_found: Set[str], base: Dict) -> None:
    d = dict(base)
    d["done"] = sorted(done)
    d["not_found"] = sorted(not_found)
    save_state_all(path, d)


def load_segment_state(path: Path) -> Tuple[Set[str], Dict]:
    d = load_state_all(path)
    sets = _ensure_sets(d)
    return sets["uploaded"], d


def save_segment_state(path: Path, uploaded: Set[str], base: Dict) -> None:
    d = dict(base)
    d["uploaded"] = sorted(uploaded)
    save_state_all(path, d)
