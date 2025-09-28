from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .constants import WIKI_API


@dataclass
class FetchConfig:
    titles_file: Path
    out_dir: Path
    state_file: Path
    delay_sec: float = 0.2
    timeout_sec: float = 15.0
    max_titles: Optional[int] = None


def read_titles(path: Path) -> List[str]:
    titles: List[str] = []
    if not path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์หัวข้อ: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        titles.append(line)
    return titles


def load_state(path: Path) -> Tuple[Set[str], Set[str]]:
    if not path.exists():
        return set(), set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        done = set(data.get("done", []))
        not_found = set(data.get("not_found", []))
        return done, not_found
    except Exception:
        # ถ้าไฟล์เสียหาย เริ่มใหม่ (และสำรองไฟล์เดิม)
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            path.replace(backup)
        except Exception:
            pass
        return set(), set()


def save_state(path: Path, done: Set[str], not_found: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"done": sorted(done), "not_found": sorted(not_found)}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def sanitize_filename(name: str) -> str:
    # Remove invalid Windows filename chars and limit length
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip().strip(".")
    # Limit to 180 chars to be safe with path lengths
    if len(name) > 180:
        name = name[:180]
    return name or "untitled"


def build_user_agent() -> str:
    contact = os.getenv("WIKI_CONTACT", "contact:N/A")
    app_url = os.getenv("WIKI_APP_URL", "https://example.com/wiki-nlp")
    return f"wiki-nlp/0.1 (+{app_url}; {contact}) requests/{requests.__version__}"


def build_session() -> requests.Session:
    session = requests.Session()
    # Set Wikipedia-friendly headers
    session.headers.update({
        "User-Agent": build_user_agent(),
        "Accept": "application/json",
    })
    # Configure retries for transient errors
    retry = Retry(
        total=4,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_wiki_extract(session: requests.Session, title: str, timeout: float) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (normalized_title, extract_text) or (None, None) if not found.
    """
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "redirects": 1,
        "format": "json",
        "titles": title,
    }
    r = session.get(WIKI_API, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None, None
    # pages is dict keyed by pageid or -1
    for page in pages.values():
        if page.get("missing") is not None:
            return None, None
        normalized_title = page.get("title") or title
        extract = page.get("extract")
        if extract is None:
            return None, None
        return normalized_title, extract
    return None, None


def ensure_out_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_article(out_dir: Path, title: str, text: str) -> Path:
    ensure_out_dir(out_dir)
    fname = sanitize_filename(title) + ".txt"
    fpath = out_dir / fname
    fpath.write_text(text, encoding="utf-8")
    return fpath


def fetch_all(cfg: FetchConfig) -> None:
    titles = read_titles(cfg.titles_file)
    if cfg.max_titles is not None:
        titles = titles[: cfg.max_titles]

    done, not_found = load_state(cfg.state_file)

    session = build_session()
    processed = 0
    for i, title in enumerate(titles, start=1):
        if title in done or title in not_found:
            # print(f"[{i}/{len(titles)}] ข้าม (มีใน state แล้ว): {title}")
            continue
        try:
            norm_title, extract = fetch_wiki_extract(session, title, cfg.timeout_sec)
            if norm_title and extract:
                out_path = write_article(cfg.out_dir, norm_title, extract)
                done.add(title)
                done.add(norm_title)
                print(f"[{i}/{len(titles)}] บันทึกแล้ว: {norm_title} -> {out_path}")
            else:
                not_found.add(title)
                print(f"[{i}/{len(titles)}] ไม่พบบทความ: {title}")
        except requests.HTTPError as e:
            code = getattr(e.response, "status_code", "?")
            print(f"[{i}/{len(titles)}] HTTP {code} ขณะดึง: {title}")
        except requests.RequestException as e:
            print(f"[{i}/{len(titles)}] ข้อผิดพลาดเครือข่าย: {title} :: {e}")
        except Exception as e:
            print(f"[{i}/{len(titles)}] ข้อผิดพลาดไม่ทราบสาเหตุ: {title} :: {e}")
        finally:
            # Save state incrementally to be resumable
            save_state(cfg.state_file, done, not_found)
            processed += 1
            if cfg.delay_sec > 0 and processed < len(titles):
                time.sleep(cfg.delay_sec)
