# wiki-nlp CLI (Python 3.12.10 + Docker)

CLI สำหรับดึงบทความวิกิพีเดียภาษาไทย แยกหัวข้อ ตัด/โทเค็นประโยค วิเคราะห์ไวยากรณ์ และสกัดลวดลายคำ (word patterns) ลง MongoDB โดยติดตามสถานะผ่านฟิลด์ `process.*` ของเอกสาร

## โครงสร้างโปรเจกต์

```
.
├─ Dockerfile
├─ requirements.txt
├─ scripts/
│  ├─ build.ps1              # สร้าง Docker image (wiki-nlp-cli)
│  ├─ run.ps1                # รันคำสั่ง任意ในคอนเทนเนอร์
│  ├─ fetch.ps1              # ดึงบทความ .txt ตาม titles.txt
│  ├─ segment.ps1            # แยกหัวข้อ/ย่อย document แล้วบันทึกลง Mongo (collection: corpus)
│  ├─ sentences.ps1          # สร้าง sentences แบบเว้นวรรคจาก raw.content
│  ├─ sentence_token.ps1     # ตัดประโยคใหม่ด้วย PyThaiNLP จาก sentences เดิม
│  ├─ thai_clock.ps1         # ปรับรูปแบบเวลาไทยใน raw.content
│  ├─ tag_num.ps1            # ติดแท็ก NUM ให้ข้อความที่เป็นตัวเลข
│  ├─ connectors.ps1         # รวมประโยคสั้นตามกฎเชื่อม (connectors)
│  ├─ abbreviation.ps1       # ขยายตัวย่อและบันทึก candidates
│  ├─ tokenize.ps1           # สร้าง tokens (POS/lemma/deprel) ด้วย Stanza + custom dict
│  ├─ sentence_heads.ps1     # สร้างประโยคย่อยตาม dependency heads
│  ├─ word_pattern.ps1       # สร้าง masked word patterns ลง collections words/patterns
│  └─ pipeline.ps1           # รันทุกขั้นแบบวนจนเสร็จ
├─ data/
│  ├─ input/
│  │  ├─ titles.txt
│  │  └─ custom_dict.txt     # (ตัวเลือก) คำศัพท์เพิ่มสำหรับ tokenizer
│  └─ state.json
└─ src/
   └─ app/
      ├─ __main__.py         # CLI entry (python -m app ...)
      ├─ wiki_fetcher.py     # ดึงบทความวิกิพีเดีย
      ├─ segmenter.py        # เตรียมเอกสารลง Mongo
      ├─ sentence_split.py   # ตัดประโยคเว้นวรรค
      ├─ sentence_token.py   # ตัดประโยคด้วย PyThaiNLP
      ├─ thai_clock.py       # ปรับรูปแบบเวลา
      ├─ connectors.py       # รวมประโยคตามกฎเชื่อม
      ├─ abbreviation.py     # ขยายตัวย่อและเก็บ candidates
      ├─ tokenize.py         # สร้าง tokens ด้วย Stanza (POS/lemma/depparse)
      ├─ sentence_heads.py   # กลุ่ม token ตาม dependency head
      ├─ word_pattern.py     # สร้าง masked patterns
      ├─ num_tag.py          # ติดแท็กตัวเลข
      ├─ text_normalize.py   # ทำความสะอาดข้อความ
      ├─ constants.py        # ค่าคงที่/พจนานุกรมโดเมน
      ├─ db.py               # เชื่อม MongoDB จาก env
      └─ state_store.py      # จัดการ state อัปโหลดไฟล์
```

## ติดตั้ง/รัน (Windows PowerShell)

1) สร้าง Docker image

```powershell
./scripts/build.ps1
```

2) ดึง > แยก > เตรียม sentences

```powershell
./scripts/fetch.ps1
./scripts/segment.ps1 -Collection corpus -Batch 100
./scripts/sentences.ps1 -Collection corpus -Limit 200 -Batch 500
./scripts/sentence_token.ps1 -Collection corpus -Limit 200 -Batch 200
```

3) ขั้นวิเคราะห์เพิ่มเติม (เลือกใช้ได้)

```powershell
./scripts/thai_clock.ps1
./scripts/tag_num.ps1
./scripts/connectors.ps1
./scripts/abbreviation.ps1
```

4) โทเค็นคำ + ไวยากรณ์ + head phrases + word patterns

```powershell
./scripts/tokenize.ps1          # เพิ่ม fields: id/start/end/head/pos/lemma/depparse/type/lang ต่อ token
./scripts/sentence_heads.ps1    # สร้าง sentence_heads[] จาก dependency
./scripts/word_pattern.ps1      # เติม collections: patterns, words (อธิบายด้านล่าง)
```

5) ทางลัดครบชุดแบบวนจนจบขั้นละ 0 changes

```powershell
./scripts/pipeline.ps1 -Fetch -Segment
```

หมายเหตุ: ทุกสคริปต์รองรับพารามิเตอร์ Mongo เช่น `-MongoUri`, `-MongoDb`, `-MongoUser`, `-MongoPassword`, `-MongoAuthDb` และ `-Network` สำหรับ docker network เดียวกับ MongoDB

## คำสั่ง CLI (python -m app)

- fetch: ดึงบทความตาม `data/input/titles.txt`
- segment: สร้างเอกสารลง Mongo collection (ดีฟอลต์: corpus)
- sentences: ตัดประโยคเว้นวรรค → `process.sentence_split=true`
- sentence-token: ตัดประโยคด้วย PyThaiNLP → `process.sentence_token=true`
- thai-clock: ปรับเวลาไทยใน raw.content → `process.thai_clock=true`
- connectors: รวมประโยคสั้นตามกฎ → `process.connector=true`
- abbreviation: ขยายตัวย่อและบันทึก candidates → `process.abbreviation=true`
- tokenize: สร้าง tokens ต่อ sentence ด้วย Stanza (รองรับ custom dict) → `process.tokenize=true`
- sentence-heads: กลุ่ม token ตาม dependency head → `process.sentence_heads=true`
- word-pattern: สร้าง masked patterns และนับสถิติ → `process.word_pattern=true`

ตัวเลือกทั่วไป: `--collection/--corpus`, `--limit`, `--batch`, `--all`, `--verbose`

## พจนานุกรมเสริม (custom dict)

- วางไฟล์คำศัพท์ใน `data/input/custom_dict.txt` (หนึ่งคำต่อบรรทัด)
- ใช้ร่วมกับตัวตัดคำ PyThaiNLP ก่อนป้อนเข้า Stanza เพื่อให้ตัดตรงกับโดเมนของคุณ

## แบบจำลองข้อมูล (สำคัญ)

1) corpus.sentences[].tokens[] จากคำสั่ง tokenize

- ฟิลด์ต่อ token: `id` (เริ่ม 1), `text`, `pos` (UPOS), `lemma`, `depparse` (deprel), `head` (int), `start`, `end` (offset อักษร), `lang` ("th"), `type` (อนุมาน เช่น TIME/DATE/MONEY/UNIT_*/PERCENT เป็นต้น)
- หลังรันจะตั้ง `process.tokenize=true`

2) corpus.sentence_heads[] จากคำสั่ง sentence-heads

- รายการของ `{ head: <หัว (lemma)>, text: <บรรทัดสรุป>, tokens: [<กลุ่มโทเค็น> ] }` ต่อ head id (ยกเว้น root)
- หลังรันจะตั้ง `process.sentence_heads=true`

3) patterns (คอลเลกชันใหม่) จากคำสั่ง word-pattern

- เอกสาร: `{ _id, pattern: <string>, tokens: [<string>], length: <int>, count: <นับรวมทั่วทั้ง corpora> }`

4) words (คอลเลกชันสถิติตามคำ)

- เอกลักษณ์ต่อเอกสาร: `word`
- โครงสร้าง: `{ word, count, pos: [ { pos, count } ], depparse: [ { depparse, count } ], patterns: [ { pattern_id, count } ] }`
- เก็บเฉพาะ pivot token ที่ POS อยู่ในชุด `MASK_POS` (กำหนดใน `constants.py` เช่น {NOUN, PROPN, VERB})
- การสร้าง pattern:
  - โทเค็น pivot แทนเป็น `<WORD|{deprel}>`
  - โทเค็นอื่น หาก `type ∈ NOT_MASK_TYPE` จะคง lemma; มิฉะนั้นถ้า `POS ∈ MASK_POS` จะใช้ `<POS|{deprel}>`; ไม่เช่นนั้นใช้ lemma

## สถานะการประมวลผล (process flags)

- `process.sentence_split`, `process.sentence_token`, `process.num_tag`, `process.thai_clock`, `process.connector`, `process.abbreviation`, `process.tokenize`, `process.sentence_heads`, `process.word_pattern`
- ดีฟอลต์จะประมวลผลเฉพาะเอกสารที่ยังไม่ถูกตั้ง flag นั้น ๆ; ใช้ `-All` เพื่อประมวลผลทั้งหมด

## ตัวแปรแวดล้อม MongoDB

- `MONGO_URI` เช่น `mongodb://host.docker.internal:27017`
- `MONGO_DB` เช่น `tiktok_live`
- `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_AUTH_DB`

## รันแบบไม่ใช้ Docker (ตัวเลือกนักพัฒนา)

ติดตั้ง Python 3.12.10 และตั้งค่า PYTHONPATH ให้เห็น `src`

```powershell
$env:PYTHONPATH = ".\src"; python -m app --help
```

## ใบอนุญาต

MIT
