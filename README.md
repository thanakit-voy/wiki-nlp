# โปรเจกต์สคริปต์ Python 3.12.10 แบบ Docker (ไม่มี API)

.\scripts\fetch.ps1
.\scripts\segment.ps1
.\scripts\thai_clock.ps1
.\scripts\sentences.ps1
.\scripts\sentence_token.ps1
.\scripts\tag_num.ps1
.\scripts\connectors.ps1
.\scripts\abbreviation.ps1


โปรเจกต์นี้เป็น CLI ที่รันใน Docker สำหรับงานดึงบทความวิกิพีเดียภาษาไทย, แยกหัวข้อ, ตัดประโยค และประมวลผลข้อความลง MongoDB โดยมีการติดตามสถานะการประมวลผลในฟิลด์ `process.*` ของเอกสาร

## โครงสร้าง

```
.
├─ Dockerfile
├─ .dockerignore
├─ requirements.txt
├─ data/
│  ├─ input/
│  │  └─ titles.txt
│  ├─ output/
│  │  └─ articles/ (ผลลัพธ์ไฟล์ .txt)
│  └─ state.json (ไฟล์สถานะ)
└─ src/
   └─ app/
      ├─ __init__.py
      └─ __main__.py
```

   ├─ __main__.py          # CLI entry
   ├─ wiki_fetcher.py      # ดึงบทความจากวิกิพีเดีย
   ├─ segmenter.py         # แยกหัวข้อและเตรียมบันทึกลง DB
   ├─ sentence_split.py    # ตัดประโยคแบบเว้นวรรค (เบื้องต้น)
   ├─ sentence_token.py    # ตัดประโยคด้วย PyThaiNLP จาก sentences เดิม
   ├─ num_tag.py           # ใส่แท็กให้ประโยคที่เป็นตัวเลข
   ├─ text_normalize.py    # ทำความสะอาด/ normalize ข้อความ
   ├─ db.py                # เชื่อมต่อ MongoDB ผ่าน env
   ├─ state_store.py       # จัดการไฟล์สถานะ
   └─ constants.py         # ค่าคงที่/regex ใช้ร่วมกัน
## วิธีใช้งาน (Windows PowerShell)


# ตั้งชื่อ image ตามต้องการ (เช่น wiki-nlp-cli)
```
## การเตรียมใช้งาน (Windows PowerShell)
docker run --rm wiki-nlp-cli
# wiki-nlp CLI (Python 3.12.10 + Docker)

CLI สำหรับดึงบทความวิกิพีเดียภาษาไทย แยกหัวข้อ ตัดประโยค และประมวลผลข้อความลง MongoDB รองรับสถานะการประมวลผลผ่านฟิลด์ `process.*` ของแต่ละเอกสาร

## โครงสร้างโปรเจกต์

```
.
├─ Dockerfile
├─ .dockerignore
├─ requirements.txt
├─ scripts/
│  ├─ build.ps1
│  ├─ run.ps1
│  ├─ fetch.ps1
│  ├─ segment.ps1
│  ├─ sentences.ps1
│  ├─ sentence_token.ps1
│  └─ tag_num.ps1
├─ data/
│  ├─ input/
│  │  └─ titles.txt
│  ├─ output/
│  │  └─ articles/
│  └─ state.json
└─ src/
    └─ app/
         ├─ __main__.py          # CLI entry
         ├─ wiki_fetcher.py      # ดึงบทความจากวิกิพีเดีย
         ├─ segmenter.py         # แยกหัวข้อและเตรียมบันทึกลง DB
         ├─ sentence_split.py    # ตัดประโยคแบบเว้นวรรค (เบื้องต้น)
         ├─ sentence_token.py    # ตัดประโยคด้วย PyThaiNLP จาก sentences เดิม
         ├─ num_tag.py           # ใส่แท็กให้ประโยคที่เป็นตัวเลข
         ├─ text_normalize.py    # ทำความสะอาด/ normalize ข้อความ
         ├─ db.py                # เชื่อมต่อ MongoDB
         ├─ state_store.py       # จัดการไฟล์สถานะ
         └─ constants.py         # ค่าคงที่/regex ใช้ร่วมกัน
```

## เตรียมใช้งาน (Windows PowerShell)

1) Build Docker image (รวม PyThaiNLP แล้ว)

```powershell
./scripts/build.ps1  # จะสร้าง image ชื่อ wiki-nlp-cli
```

2) ใช้งานผ่านสคริปต์ (แนะนำ)

สคริปต์รองรับพารามิเตอร์ `-Image` (ดีฟอลต์ `wiki-nlp-cli`) และตัวเลือก MongoDB เช่น `-MongoUri`, `-MongoDb`, `-MongoUser`, `-MongoPassword`, `-MongoAuthDb`, และ `-Network` (กรณีใช้ Docker network เดียวกับ Mongo)

- ดึงบทความวิกิพีเดียตามรายการหัวข้อ

```powershell
./scripts/fetch.ps1
```

- แยกหัวข้อและบันทึกลง MongoDB (collection: corpus)

```powershell
./scripts/segment.ps1 -Collection corpus -Batch 100
```

- ตัดประโยคแบบเว้นวรรคจาก raw.content และตั้ง `process.sentence_split=true`

```powershell
./scripts/sentences.ps1 -Collection corpus -Limit 200 -Batch 500
```

- นำ sentences เดิมมา “ตัดอีกรอบ” ด้วย PyThaiNLP และตั้ง `process.sentence_token=true`

```powershell
./scripts/sentence_token.ps1 -Collection corpus -Limit 200 -Batch 200
```

- ใส่แท็กให้ประโยคที่เป็นตัวเลข และตั้ง `process.num_tag=true`

```powershell
./scripts/tag_num.ps1 -Collection corpus -Limit 200 -Batch 200
```

3) เรียกผ่าน Docker ตรง (ตัวเลือก)

ตัวอย่าง (แมปโฟลเดอร์โปรเจกต์เข้าไปเพื่อให้ไฟล์ผลลัพธ์/สถานะเก็บบนเครื่อง):

```powershell
docker run --rm -v "${PWD}:/app" wiki-nlp-cli fetch --titles data/input/titles.txt --out-dir data/output/articles --state data/state.json
```

ตั้งค่าเชื่อมต่อ MongoDB ด้วยตัวแปรแวดล้อม (ตัวอย่าง):

```powershell
docker run --rm -v "${PWD}:/app" `
   -e MONGO_URI="mongodb://host.docker.internal:27017" `
   -e MONGO_DB="tiktok_live" -e MONGO_USER="appuser" -e MONGO_PASSWORD="apppass" -e MONGO_AUTH_DB="admin" `
   wiki-nlp-cli segment --articles-dir data/output/articles --collection corpus --batch 100 --state data/state.json
```

## สถานะการประมวลผล (process flags)

- `process.sentence_split`: ถูกตั้งเป็น `true` หลังสร้างฟิลด์ `sentences` แบบเว้นวรรคจาก `raw.content`
- `process.sentence_token`: ถูกตั้งเป็น `true` หลัง retokenize `sentences` เดิมด้วย PyThaiNLP
- `process.num_tag`: ถูกตั้งเป็น `true` หลังใส่ `type=NUM` และ `pos=NUM` ให้ประโยคที่เป็นตัวเลข

ค่าเริ่มต้นของแต่ละคำสั่งจะประมวลผลเฉพาะเอกสารที่ยังไม่ถูกทำขั้นตอนนั้น (เช็ค flag ข้างต้น) หากต้องการประมวลผลทั้งหมด ใช้ตัวเลือก `-All` (หรือ `--all` สำหรับเรียกผ่าน Docker)

## ตัวแปรแวดล้อม MongoDB

- `MONGO_URI` เช่น `mongodb://host.docker.internal:27017`
- `MONGO_DB` เช่น `tiktok_live`
- `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_AUTH_DB`

## รันแบบไม่ใช้ Docker (ตัวเลือก)

ติดตั้ง Python 3.12.10 และตั้งค่า PYTHONPATH ให้เห็นโฟลเดอร์ `src`

```powershell
$env:PYTHONPATH = ".\src"; python -m app --help
```

## ใบอนุญาต

MIT

- นำ sentences เดิมมา “ตัดอีกรอบ” ด้วย PyThaiNLP และตั้ง `process.sentence_token=true`

```powershell
./scripts/sentence_token.ps1 -Collection corpus -Limit 200 -Batch 200
```

- ใส่แท็กให้ประโยคที่เป็นตัวเลข และตั้ง `process.num_tag=true`

```powershell
./scripts/tag_num.ps1 -Collection corpus -Limit 200 -Batch 200
```

3) เรียกผ่าน Docker ตรง (ตัวเลือก)

ตัวอย่าง (แมปโฟลเดอร์โปรเจกต์เข้าไปเพื่อให้ไฟล์ผลลัพธ์/สถานะเก็บบนเครื่อง):

```powershell
docker run --rm -v "${PWD}:/app" wiki-nlp-cli fetch --titles data/input/titles.txt --out-dir data/output/articles --state data/state.json
```

ตั้งค่าเชื่อมต่อ MongoDB ด้วยตัวแปรแวดล้อม (ตัวอย่าง):

```powershell
docker run --rm -v "${PWD}:/app" `
  -e MONGO_URI="mongodb://host.docker.internal:27017" `
  -e MONGO_DB="tiktok_live" -e MONGO_USER="appuser" -e MONGO_PASSWORD="apppass" -e MONGO_AUTH_DB="admin" `
  wiki-nlp-cli segment --articles-dir data/output/articles --collection corpus --batch 100 --state data/state.json
```

## สถานะการประมวลผล (process flags)

- `process.sentence_split`: ถูกตั้งเป็น `true` หลังสร้างฟิลด์ `sentences` แบบเว้นวรรคจาก `raw.content`
- `process.sentence_token`: ถูกตั้งเป็น `true` หลัง retokenize `sentences` เดิมด้วย PyThaiNLP
- `process.num_tag`: ถูกตั้งเป็น `true` หลังใส่ `type=NUM` และ `pos=NUM` ให้ประโยคที่เป็นตัวเลข

ค่าเริ่มต้นของแต่ละคำสั่งจะประมวลผลเฉพาะเอกสารที่ยังไม่ถูกทำขั้นตอนนั้น (เช็ค flag ข้างต้น) หากต้องการประมวลผลทั้งหมด ใช้ตัวเลือก `-All` (หรือ `--all` สำหรับเรียกผ่าน Docker)

## ตัวแปรแวดล้อม MongoDB

- `MONGO_URI` เช่น `mongodb://host.docker.internal:27017`
- `MONGO_DB` เช่น `tiktok_live`
- `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_AUTH_DB`

## รันแบบไม่ใช้ Docker (ตัวเลือก)

ติดตั้ง Python 3.12.10 และตั้งค่า PYTHONPATH ให้เห็นโฟลเดอร์ `src`

```powershell
$env:PYTHONPATH = ".\src"; python -m app --help
```

## ใบอนุญาต

MIT
