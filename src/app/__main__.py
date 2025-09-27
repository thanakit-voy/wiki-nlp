import argparse


def run(name: str, upper: bool = False) -> None:
    message = f"สวัสดี {name}"
    if upper:
        message = message.upper()
    print(message)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="app",
        description="สคริปต์ตัวอย่างสำหรับรันใน Docker โดยไม่มี API — แค่รันคำสั่ง CLI",
    )
    parser.add_argument("--name", default="world", help="ชื่อที่จะทักทาย (ดีฟอลต์: world)")
    parser.add_argument("--upper", action="store_true", help="พิมพ์ตัวพิมพ์ใหญ่ทั้งหมด")

    args = parser.parse_args(argv)
    run(args.name, args.upper)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
