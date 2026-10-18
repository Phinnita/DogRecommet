# 🐶 DogRecommet

ระบบแนะนำสายพันธุ์สุนัขด้วย Graph Database (Neo4j Aura) สร้างด้วย Streamlit บอกเหตุผลของคำแนะนำได้ทุกครั้ง

คะแนน = (เส้นทางจากคนที่ชอบคล้ายกัน × 2) + (เส้นทางจากกลุ่มสายพันธุ์เดียวกัน × 1)

## ไฟล์
- `app.py` — ตัวเว็บแอป
- `requirements.txt` — ไลบรารีที่ต้องใช้
- `.streamlit/secrets.toml.example` — ตัวอย่างค่าเชื่อมต่อ Neo4j (ห้ามอัปโหลดไฟล์ secrets.toml จริง)

## Deploy บน Streamlit Community Cloud
1. สร้าง repo ใหม่บน GitHub เช่น `dogrecommet` แล้วอัปโหลด `app.py`, `requirements.txt`, `README.md`, `.gitignore`
2. เข้า https://share.streamlit.io → Create app → เลือก repo, branch `main`, ไฟล์ `app.py`
3. ตั้ง App URL เช่น `dogrecommet`
4. กด Advanced settings → Secrets แล้ววางค่าจาก `secrets.toml.example` พร้อมใส่รหัสผ่านจริง
5. กด Deploy แล้วไปที่เมนู ⚙️ Setup → กด "สร้างข้อมูลตัวอย่าง"
