# โปรเจกต์สคริปต์ Python 3.12.10 แบบ Docker (ไม่มี API)

โปรเจกต์นี้เป็นตัวอย่างโครงสร้างสำหรับเขียนสคริปต์ Python ที่รันผ่านคำสั่ง (CLI) เท่านั้น และแพ็กด้วย Docker โดยใช้ Python 3.12.10

## โครงสร้าง

```
.
├─ Dockerfile
├─ .dockerignore
├─ requirements.txt
└─ src/
   └─ app/
      ├─ __init__.py
      └─ __main__.py
```

ไฟล์ `__main__.py` จะทำให้แพ็กเกจ `app` รันได้ด้วยคำสั่ง `python -m app` ภายในคอนเทนเนอร์

## วิธีใช้งาน (Windows PowerShell)

- สร้างอิมเมจ:

```powershell
# ตั้งชื่อ image ตามต้องการ (เช่น wiki-nlp-cli)
docker build -t wiki-nlp-cli .
```

- รันคำสั่งในคอนเทนเนอร์ (ดีฟอลต์):

```powershell
docker run --rm wiki-nlp-cli
```

- ส่งอาร์กิวเมนต์เข้าไปให้โปรแกรม:

```powershell
docker run --rm wiki-nlp-cli --name "คุณ" --upper
```

หมายเหตุ: เมื่อใช้รูปแบบ ENTRYPOINT (แบบใน Dockerfile นี้) ไม่ต้องใส่ `--` หลังชื่ออิมเมจ อาร์กิวเมนต์จะถูกส่งต่อให้โปรแกรมโดยตรง

### คำสั่งดึงบทความวิกิพีเดียภาษาไทย

โปรแกรมรองรับ subcommand `fetch` สำหรับดึงบทความจากไฟล์หัวข้อ (`title.txt`) และบันทึกเป็น .txt พร้อมเก็บ state ว่าหัวข้อไหนดึงแล้ว/ไม่พบ

```powershell
# รันด้วยค่าดีฟอลต์: ใช้ไฟล์ title.txt, บันทึกไว้ที่ data/articles และ state ที่ data/state.json
docker run --rm -v "$PWD/data":"/app/data" -v "$PWD/title.txt":"/app/title.txt" wiki-nlp-cli fetch

# ปรับ path หรือ parameter ได้ตามต้องการ
docker run --rm -v "$PWD:/app" wiki-nlp-cli fetch --titles title.txt --out-dir data/articles --state data/state.json --delay 0.2 --timeout 15
```

หมายเหตุ: ใช้ `-v` เพื่อแมปโฟลเดอร์/ไฟล์จากเครื่องโฮสต์เข้าคอนเทนเนอร์ เพื่อให้ไฟล์ผลลัพธ์และ state ถูกเก็บไว้ที่เครื่องคุณ

## เพิ่มไลบรารี

เพิ่มชื่อแพ็กเกจใน `requirements.txt` แล้ว build image ใหม่:

```powershell
docker build -t wiki-nlp-cli .
```

## รันแบบไม่ใช้ Docker (ตัวเลือก)

ถ้าติดตั้ง Python 3.12.10 บนเครื่องแล้ว สามารถรันได้โดยตรง (ตั้งค่า PYTHONPATH ให้เห็นโฟลเดอร์ `src`):

```powershell
$env:PYTHONPATH = ".\src"; python -m app --name test
```

ดึงบทความแบบไม่ใช้ Docker:

```powershell
$env:PYTHONPATH = ".\src"; python -m app fetch --titles .\title.txt --out-dir .\data\articles --state .\data\state.json
```

## ไลเซนส์

MIT (แก้ไขได้ตามต้องการ)
