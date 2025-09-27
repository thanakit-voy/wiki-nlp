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

- ส่งอาร์กิวเมนต์เข้าไป (หลัง `--` คือ args ของโปรแกรม):

```powershell
docker run --rm wiki-nlp-cli -- --name "คุณ" --upper
```

หมายเหตุ: `--` ใช้คั่นระหว่างอาร์กิวเมนต์ของ Docker และของโปรแกรม Python

## เพิ่มไลบรารี

เพิ่มชื่อแพ็กเกจใน `requirements.txt` แล้ว build image ใหม่:

```powershell
docker build -t wiki-nlp-cli .
```

## รันแบบไม่ใช้ Docker (ตัวเลือก)

ถ้าติดตั้ง Python 3.12.10 บนเครื่องแล้ว สามารถรันได้โดยตรง:

```powershell
python -m src.app --name test
```

หรือเพิ่ม `src` ใน `PYTHONPATH` ก่อน (ขึ้นกับสภาพแวดล้อมของคุณ)

## ไลเซนส์

MIT (แก้ไขได้ตามต้องการ)
