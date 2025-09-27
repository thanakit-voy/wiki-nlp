import argparse
from pathlib import Path

from .wiki_fetcher import FetchConfig, fetch_all
from .segmenter import SegmentDbConfig, generate_records_grouped_by_file
from .db import get_collection
from .state_store import load_segment_state, save_segment_state


def cmd_greet(args) -> int:
    message = f"สวัสดี {args.name}"
    if args.upper:
        message = message.upper()
    print(message)
    return 0


def cmd_fetch(args) -> int:
    cfg = FetchConfig(
        titles_file=Path(args.titles),
        out_dir=Path(args.out_dir),
        state_file=Path(args.state),
        delay_sec=args.delay,
        timeout_sec=args.timeout,
        max_titles=args.max,
    )
    fetch_all(cfg)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app",
        description="CLI สำหรับงานสคริปต์ (ไม่มี API) รวมถึงดึงบทความจากวิกิพีเดียภาษาไทย",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # greet (ตัวอย่างเดิม)
    p_greet = sub.add_parser("greet", help="ทักทายง่ายๆ")
    p_greet.add_argument("--name", default="world", help="ชื่อที่จะทักทาย (ดีฟอลต์: world)")
    p_greet.add_argument("--upper", action="store_true", help="พิมพ์ตัวพิมพ์ใหญ่ทั้งหมด")
    p_greet.set_defaults(func=cmd_greet)

    # fetch (ดึงบทความวิกิ)
    p_fetch = sub.add_parser("fetch", help="ดึงบทความภาษาไทยจากวิกิพีเดียตามรายการหัวข้อ")
    p_fetch.add_argument("--titles", default="data/input/titles.txt", help="ไฟล์รายชื่อหัวข้อ (UTF-8)")
    p_fetch.add_argument("--out-dir", default="data/output/articles", help="โฟลเดอร์สำหรับบันทึกไฟล์ .txt")
    p_fetch.add_argument("--state", default="data/state.json", help="ไฟล์เก็บ state (done/not_found)")
    p_fetch.add_argument("--delay", type=float, default=0.2, help="ดีเลย์ระหว่างคำขอ (วินาที)")
    p_fetch.add_argument("--timeout", type=float, default=15.0, help="timeout ต่อคำขอ (วินาที)")
    p_fetch.add_argument("--max", type=int, default=None, help="จำนวนสูงสุดของหัวข้อที่จะดึง (เว้นว่าง=ทั้งหมด)")
    p_fetch.set_defaults(func=cmd_fetch)

    # segment-db (แยกหัวข้อและบันทึกลง MongoDB)
    p_sdb = sub.add_parser("segment-db", help="แยกข้อความจากไฟล์ .txt แล้วบันทึกลง MongoDB collection: corpus")
    p_sdb.add_argument("--articles-dir", default="data/output/articles", help="โฟลเดอร์ไฟล์ .txt")
    p_sdb.add_argument("--collection", default="corpus", help="ชื่อ collection ปลายทาง")
    p_sdb.add_argument("--max", type=int, default=None, help="จำนวนไฟล์สูงสุด")
    p_sdb.add_argument("--batch", type=int, default=100, help="ขนาด batch ต่อการ insert_many")
    p_sdb.add_argument("--state", default="data/state.json", help="ไฟล์ state (อัปโหลดแล้ว)")
    p_sdb.set_defaults(func=cmd_segment_db)

    return parser


def cmd_segment_db(args) -> int:
    cfg = SegmentDbConfig(
        articles_dir=Path(args.articles_dir),
        max_files=args.max,
        collection_name=args.collection,
    )
    col = get_collection(cfg.collection_name)
    state_path = Path(args.state)
    uploaded, base_state = load_segment_state(state_path)
    total = 0
    for title, records in generate_records_grouped_by_file(cfg):
        if title in uploaded:
            print(f"skip (uploaded): {title}")
            continue
        # insert in batches to avoid large payloads
        start = 0
        while start < len(records):
            chunk = records[start:start + args.batch]
            col.insert_many(chunk, ordered=False)
            total += len(chunk)
            start += args.batch
        uploaded.add(title)
        save_segment_state(state_path, uploaded, base_state)
        print(f"inserted file: {title} (total docs: {total})")
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
