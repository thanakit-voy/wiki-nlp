import argparse
from pathlib import Path

from .wiki_fetcher import FetchConfig, fetch_all
from .segmenter import SegmentDbConfig, generate_records_grouped_by_file
from .db import get_collection
from .sentence_split import update_corpus_sentences
from .num_tag import tag_corpus_numbers
from .sentence_token import update_corpus_sentence_tokenization
from .state_store import load_segment_state, save_segment_state
from .thai_clock import update_corpus_thai_clock
from .connectors import update_corpus_connectors
from .abbreviation import update_corpus_abbreviation
from .tokenize import update_corpus_tokenize
from .sentence_heads import update_corpus_sentence_heads
from .word_pattern import update_corpus_word_pattern


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
    p_sdb = sub.add_parser("segment", help="แยกข้อความจากไฟล์ .txt แล้วบันทึกลง MongoDB collection: corpus")
    p_sdb.add_argument("--articles-dir", default="data/output/articles", help="โฟลเดอร์ไฟล์ .txt")
    p_sdb.add_argument("--collection", default="corpus", help="ชื่อ collection ปลายทาง")
    p_sdb.add_argument("--max", type=int, default=None, help="จำนวนไฟล์สูงสุด")
    p_sdb.add_argument("--batch", type=int, default=100, help="ขนาด batch ต่อการ insert_many")
    p_sdb.add_argument("--state", default="data/state.json", help="ไฟล์ state (อัปโหลดแล้ว)")
    p_sdb.add_argument("--replace", action="store_true", help="ลบเอกสารเดิมของหัวข้อนั้นๆ ออกจาก collection ก่อนแทรกใหม่")
    p_sdb.add_argument("--force", action="store_true", help="เพิกเฉย state uploaded (ประมวลผลซ้ำแม้เคยอัปโหลดแล้ว)")
    p_sdb.set_defaults(func=cmd_segment)

    # sentences (ตัดประโยคด้วยเว้นวรรคแล้วอัปเดตลง corpus)
    p_sent = sub.add_parser("sentences", help="ตัดประโยคด้วยเว้นวรรคแล้วอัปเดต sentences และตั้งค่า process.sentence_split=true")
    p_sent.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_sent.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_sent.add_argument("--batch", type=int, default=500, help="ขนาด batch ต่อ bulk_write")
    p_sent.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ค่าเริ่มต้นคือเฉพาะที่ยังไม่มี sentences)")
    p_sent.set_defaults(func=cmd_sentences)

    # tag-num (ใส่ type=NUM, pos=NUM ให้ข้อความที่เป็นรูปแบบตัวเลข)
    p_tn = sub.add_parser("tag-num", help="วิเคราะห์ sentences ที่เป็นตัวเลข ใส่ type/pos=NUM และตั้งค่า process.num_tag=true")
    p_tn.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_tn.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_tn.add_argument("--batch", type=int, default=200, help="ขนาด batch ต่อ bulk_write")
    p_tn.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่มี type/pos)")
    p_tn.set_defaults(func=cmd_tag_num)

    # sentence-token (re-tokenize existing sentences with PyThaiNLP)
    p_st = sub.add_parser(
        "sentence-token",
        help="นำ sentences ที่มีอยู่มาแบ่งเป็นประโยคด้วย PyThaiNLP แล้วตั้งค่า process.sentence_token=true",
    )
    p_st.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_st.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_st.add_argument("--batch", type=int, default=200, help="ขนาด batch ต่อ bulk_write")
    p_st.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่ถูก sentence_token)")
    p_st.add_argument("--verbose", action="store_true", help="แสดงจำนวน candidates และสรุปผลหลังรัน")
    p_st.set_defaults(func=cmd_sentence_token)

    # thai-clock (normalize Thai time patterns in raw.content)
    p_tc = sub.add_parser(
        "thai-clock",
        help="แปลงเวลาภาษาไทยใน raw.content (01:30 น. -> 01.30 นาฬิกา ฯลฯ) และตั้งค่า process.thai_clock=true",
    )
    p_tc.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_tc.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_tc.add_argument("--batch", type=int, default=200, help="ขนาด batch ต่อ bulk_write")
    p_tc.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่ถูก thai_clock)")
    p_tc.add_argument("--verbose", action="store_true", help="แสดงจำนวน candidates และสรุปผลหลังรัน")
    p_tc.set_defaults(func=cmd_thai_clock)

    # connectors (merge sentences based on connector rules)
    p_conn = sub.add_parser(
        "connectors",
        help="รวมประโยคกับประโยคก่อนหน้าตามกฎ connectors และตั้งค่า process.connector=true",
    )
    p_conn.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_conn.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_conn.add_argument("--batch", type=int, default=200, help="ขนาด batch ต่อ bulk_write")
    p_conn.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่ถูก connectors)")
    p_conn.add_argument("--min-len", dest="min_len", type=int, default=25, help="ความยาวขั้นต่ำของประโยคที่ถือว่า 'สั้น'")
    p_conn.add_argument("--verbose", action="store_true", help="แสดงจำนวน candidates และสรุปผลหลังรัน")
    p_conn.set_defaults(func=cmd_connectors)

    # abbreviation (expand abbreviations and record candidates)
    p_abbr = sub.add_parser(
        "abbreviation",
        help="แปลงตัวย่อใน sentences เป็นคำเต็มด้วย PyThaiNLP และบันทึก candidates ลง collection abbreviation",
    )
    p_abbr.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_abbr.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_abbr.add_argument("--batch", type=int, default=200, help="ขนาด batch ต่อ bulk_write")
    p_abbr.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่ถูก abbreviation)")
    p_abbr.add_argument("--verbose", action="store_true", help="แสดงจำนวน candidates และสรุปผลหลังรัน")
    p_abbr.set_defaults(func=cmd_abbreviation)

    # tokenize (word-level tokens with POS/lemma/depparse via Stanza)
    p_tok = sub.add_parser(
        "tokenize",
        help="เพิ่ม tokens ให้แต่ละ sentences ด้วย Stanza (รองรับ custom dict) และตั้งค่า process.tokenize=true",
    )
    p_tok.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_tok.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_tok.add_argument("--batch", type=int, default=200, help="ขนาด batch ต่อ bulk_write")
    p_tok.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่ถูก tokenize)")
    p_tok.add_argument("--verbose", action="store_true", help="แสดงจำนวน candidates และสรุปผลหลังรัน")
    p_tok.set_defaults(func=cmd_tokenize)

    # sentence-heads (build phrases based on dependency heads)
    p_heads = sub.add_parser(
        "sentence-heads",
        help="สร้างประโยคย่อยตาม head ของ dependency ในแต่ละประโยค และตั้งค่า process.sentence_heads=true",
    )
    p_heads.add_argument("--collection", default="corpus", help="collection เป้าหมาย (ดีฟอลต์: corpus)")
    p_heads.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดต")
    p_heads.add_argument("--batch", type=int, default=200, help="ขนาด batch ต่อ bulk_write")
    p_heads.add_argument("--all", action="store_true", help="อัปเดตทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่ถูก sentence_heads)")
    p_heads.add_argument("--verbose", action="store_true", help="แสดงสรุปหลังรัน")
    p_heads.set_defaults(func=cmd_sentence_heads)

    # word-pattern (build masked word patterns from sentence_heads)
    p_wp = sub.add_parser(
        "word-pattern",
        help="สร้าง masked patterns ต่อ token จาก sentence_heads และบันทึกลง collection words; ตั้งค่า process.word_pattern=true",
    )
    p_wp.add_argument("--corpus", default="corpus", help="collection ของเอกสารต้นทาง (ดีฟอลต์: corpus)")
    p_wp.add_argument("--words", default="words", help="collection สำหรับเก็บ word stats (ดีฟอลต์: words)")
    p_wp.add_argument("--patterns", default="patterns", help="collection สำหรับเก็บรายการ pattern และนับรวม (ดีฟอลต์: patterns)")
    p_wp.add_argument("--limit", type=int, default=None, help="จำนวนเอกสารสูงสุดที่จะอัปเดตจาก corpus")
    p_wp.add_argument("--batch", type=int, default=200, help="สำรองไว้ (ไม่ได้ใช้กับ upsert แบบทีละรายการ)")
    p_wp.add_argument("--all", action="store_true", help="ประมวลผลทุกเอกสาร (ไม่จำกัดเฉพาะที่ยังไม่ถูก word_pattern)")
    p_wp.add_argument("--verbose", action="store_true", help="แสดงสรุปหลังรัน")
    p_wp.set_defaults(func=cmd_word_pattern)

    return parser


def cmd_segment(args) -> int:
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
        if (not args.force) and (title in uploaded):
            # print(f"skip (uploaded): {title}")
            continue
        if args.replace:
            # Replace existing docs for this title
            del_res = col.delete_many({"title": title})
            print(f"deleted existing docs for title '{title}': {del_res.deleted_count}")
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


def cmd_sentences(args) -> int:
    col = get_collection(args.collection)
    missing_only = not bool(args.all)
    updated = update_corpus_sentences(col, limit=args.limit, batch=args.batch, missing_only=missing_only)
    print(f"modified documents: {updated}")
    return 0


def cmd_tag_num(args) -> int:
    col = get_collection(args.collection)
    modified = tag_corpus_numbers(col, limit=args.limit, batch=args.batch, missing_only=not args.all)
    print(f"modified documents: {modified}")
    return 0


def cmd_sentence_token(args) -> int:
    col = get_collection(args.collection)
    modified = update_corpus_sentence_tokenization(
        col, limit=args.limit, batch=args.batch, missing_only=not args.all, verbose=args.verbose
    )
    print(f"modified documents: {modified}")
    return 0


def cmd_thai_clock(args) -> int:
    col = get_collection(args.collection)
    modified = update_corpus_thai_clock(
        col, limit=args.limit, batch=args.batch, missing_only=not args.all, verbose=args.verbose
    )
    print(f"modified documents: {modified}")
    return 0


def cmd_connectors(args) -> int:
    col = get_collection(args.collection)
    modified = update_corpus_connectors(
        col,
        limit=args.limit,
        batch=args.batch,
        missing_only=not args.all,
        min_len=args.min_len,
        verbose=args.verbose,
    )
    print(f"modified documents: {modified}")
    return 0


def cmd_abbreviation(args) -> int:
    col = get_collection(args.collection)
    modified = update_corpus_abbreviation(
        col,
        limit=args.limit,
        batch=args.batch,
        missing_only=not args.all,
        verbose=args.verbose,
    )
    print(f"modified documents: {modified}")
    return 0


def cmd_tokenize(args) -> int:
    col = get_collection(args.collection)
    modified = update_corpus_tokenize(
        col,
        limit=args.limit,
        batch=args.batch,
        missing_only=not args.all,
        verbose=args.verbose,
    )
    print(f"modified documents: {modified}")
    return 0


def cmd_sentence_heads(args) -> int:
    col = get_collection(args.collection)
    modified = update_corpus_sentence_heads(
        col,
        limit=args.limit,
        batch=args.batch,
        missing_only=not args.all,
        verbose=args.verbose,
    )
    print(f"modified documents: {modified}")
    return 0


def cmd_word_pattern(args) -> int:
    corpus_col = get_collection(args.corpus)
    words_col = get_collection(args.words)
    patterns_col = get_collection(args.patterns)
    modified = update_corpus_word_pattern(
        corpus_col,
        words_col,
        patterns_col,
        limit=args.limit,
        batch=args.batch,
        missing_only=not args.all,
        verbose=args.verbose,
    )
    print(f"modified documents: {modified}")
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
