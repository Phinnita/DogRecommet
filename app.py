"""DogRecommet — ระบบแนะนำสายพันธุ์สุนัขด้วย Graph Database (Neo4j) + Streamlit

โมเดลกราฟ
    (:DogLover {name})-[:LIKES]->(:DogBreed {name, size, energy, condo_ok, emoji, note})
    (:DogBreed)-[:IN_GROUP]->(:BreedGroup {name})

คะแนนแนะนำ = (เส้นทางจากคนที่ชอบคล้ายกัน x 2) + (เส้นทางจากกลุ่มสายพันธุ์เดียวกัน x 1)
"""
import streamlit as st
from neo4j import GraphDatabase

st.set_page_config(page_title="DogRecommet", page_icon="🐶", layout="wide")

W_PEOPLE = 2   # น้ำหนักของเส้นทาง "คนที่ชอบคล้ายกัน"
W_GROUP = 1    # น้ำหนักของเส้นทาง "กลุ่มสายพันธุ์เดียวกัน"
SIZES = ["Small", "Medium", "Large"]
ENERGY = ["Low", "Medium", "High"]

# ---------------------------------------------------------------- style
st.markdown("""
<style>
.hero{background:linear-gradient(120deg,#0f766e,#14b8a6 55%,#f59e0b);padding:22px 26px;border-radius:16px;color:#fff;margin-bottom:18px}
.hero h1{margin:0;font-size:1.9rem;color:#fff}
.hero p{margin:4px 0 0;opacity:.92}
.card{border:1px solid rgba(128,128,128,.25);border-radius:14px;padding:14px 16px;height:100%;background:rgba(20,184,166,.04)}
.card .emoji{font-size:2.6rem;line-height:1}
.card .name{font-weight:700;font-size:1.08rem;margin-top:6px}
.card .meta{opacity:.7;font-size:.85rem}
.rank{display:inline-block;background:#0f766e;color:#fff;border-radius:999px;padding:1px 10px;font-size:.78rem;font-weight:600}
.score{display:inline-block;background:#f59e0b;color:#1f2937;border-radius:999px;padding:1px 10px;font-size:.78rem;font-weight:700;margin-left:4px}
.why{font-size:.86rem;margin-top:8px;line-height:1.5}
.why b{color:#0f766e}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- database
@st.cache_resource
def get_driver():
    s = st.secrets
    driver = GraphDatabase.driver(s["NEO4J_URI"], auth=(s["NEO4J_USERNAME"], s["NEO4J_PASSWORD"]))
    driver.verify_connectivity()
    return driver


def db_name():
    return st.secrets.get("NEO4J_DATABASE") or None


def run(query, **params):
    records, _, _ = get_driver().execute_query(query, database_=db_name(), **params)
    return [r.data() for r in records]


SAMPLE_BREEDS = [
    # name, group, size, energy, condo_ok, emoji, note
    ("Pomeranian", "Toy", "Small", "Medium", True, "🐕", "ตัวเล็ก ขนฟู ขี้เล่น"),
    ("Chihuahua", "Toy", "Small", "Low", True, "🐕", "ตัวเล็กที่สุด เหมาะกับห้องเล็ก"),
    ("Corgi", "Herding", "Medium", "High", True, "🐶", "ขาสั้น ร่าเริง ฉลาด"),
    ("Border Collie", "Herding", "Medium", "High", False, "🐕‍🦺", "ฉลาดมาก ต้องการพื้นที่วิ่ง"),
    ("Golden Retriever", "Retriever", "Large", "High", False, "🦮", "ใจดี เข้ากับเด็ก"),
    ("Labrador", "Retriever", "Large", "High", False, "🦮", "เป็นมิตร ชอบว่ายน้ำ"),
    ("Shiba Inu", "Spitz", "Medium", "Medium", True, "🐶", "สะอาด รักอิสระ"),
    ("Siberian Husky", "Spitz", "Large", "High", False, "🐺", "พลังเยอะ ชอบอากาศเย็น"),
]
SAMPLE_LIKES = {
    "Mild": ["Pomeranian", "Corgi"],
    "Ten": ["Pomeranian", "Corgi", "Shiba Inu"],
    "Pim": ["Corgi", "Shiba Inu"],
    "Arm": ["Golden Retriever", "Labrador"],
    "Bow": ["Labrador", "Shiba Inu"],
}


def setup_sample_data():
    run("MATCH (n) WHERE n:DogLover OR n:DogBreed OR n:BreedGroup DETACH DELETE n")
    for label in ("DogLover", "DogBreed", "BreedGroup"):
        run(f"CREATE CONSTRAINT {label.lower()}_name_unique IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.name IS UNIQUE")
    run("""
    UNWIND $rows AS r
    MERGE (b:DogBreed {name: r[0]})
    SET b.size = r[2], b.energy = r[3], b.condo_ok = r[4], b.emoji = r[5], b.note = r[6]
    MERGE (g:BreedGroup {name: r[1]})
    MERGE (b)-[:IN_GROUP]->(g)
    """, rows=[list(r) for r in SAMPLE_BREEDS])
    run("""
    UNWIND $rows AS r
    MERGE (u:DogLover {name: r.name})
    WITH u, r UNWIND r.breeds AS bn
    MATCH (b:DogBreed {name: bn})
    MERGE (u)-[:LIKES]->(b)
    """, rows=[{"name": k, "breeds": v} for k, v in SAMPLE_LIKES.items()])


# ---------------------------------------------------------------- queries
def lovers():
    return [r["name"] for r in run("MATCH (u:DogLover) RETURN u.name AS name ORDER BY name")]


def breeds():
    return run("""
    MATCH (b:DogBreed) OPTIONAL MATCH (b)-[:IN_GROUP]->(g:BreedGroup)
    OPTIONAL MATCH (u:DogLover)-[:LIKES]->(b)
    RETURN b.name AS name, g.name AS grp, b.size AS size, b.energy AS energy,
           b.condo_ok AS condo_ok, b.emoji AS emoji, b.note AS note, count(u) AS likes
    ORDER BY likes DESC, name
    """)


def groups():
    return [r["name"] for r in run("MATCH (g:BreedGroup) RETURN g.name AS name ORDER BY name")]


def liked_by(name):
    return [r["b"] for r in run(
        "MATCH (:DogLover {name:$n})-[:LIKES]->(b:DogBreed) RETURN b.name AS b ORDER BY b", n=name)]


def set_like(name, breed, on=True):
    if on:
        run("""MERGE (u:DogLover {name:$n}) WITH u
               MATCH (b:DogBreed {name:$b}) MERGE (u)-[:LIKES]->(b)""", n=name, b=breed)
    else:
        run("MATCH (:DogLover {name:$n})-[r:LIKES]->(:DogBreed {name:$b}) DELETE r", n=name, b=breed)


def recommend(name, condo_only=False):
    """คืนรายการคำแนะนำ พร้อมคะแนนและเหตุผลของทุกเส้นทาง"""
    people = run("""
    MATCH (me:DogLover {name:$n})-[:LIKES]->(via:DogBreed)<-[:LIKES]-(o:DogLover)-[:LIKES]->(rec:DogBreed)
    WHERE o <> me AND NOT EXISTS { (me)-[:LIKES]->(rec) }
    RETURN rec.name AS breed, count(*) AS paths,
           collect(DISTINCT o.name) AS people, collect(DISTINCT via.name) AS via
    """, n=name)
    group = run("""
    MATCH (me:DogLover {name:$n})-[:LIKES]->(via:DogBreed)-[:IN_GROUP]->(g:BreedGroup)<-[:IN_GROUP]-(rec:DogBreed)
    WHERE NOT EXISTS { (me)-[:LIKES]->(rec) }
    RETURN rec.name AS breed, count(*) AS paths,
           collect(DISTINCT g.name) AS groups, collect(DISTINCT via.name) AS via
    """, n=name)

    info = {b["name"]: b for b in breeds()}
    out = {}
    for r in people:
        d = out.setdefault(r["breed"], {"p": 0, "g": 0, "reasons": []})
        d["p"] = r["paths"]
        d["reasons"].append(
            f"👥 <b>{', '.join(r['people'])}</b> ชอบ {', '.join(r['via'])} เหมือนคุณ "
            f"และชอบพันธุ์นี้ด้วย ({r['paths']} เส้นทาง × {W_PEOPLE})")
    for r in group:
        d = out.setdefault(r["breed"], {"p": 0, "g": 0, "reasons": []})
        d["g"] = r["paths"]
        d["reasons"].append(
            f"🧬 อยู่กลุ่ม <b>{', '.join(r['groups'])}</b> เดียวกับ {', '.join(r['via'])} "
            f"ที่คุณชอบ ({r['paths']} เส้นทาง × {W_GROUP})")
    rows = []
    for b, d in out.items():
        meta = info.get(b, {})
        if condo_only and not meta.get("condo_ok"):
            continue
        rows.append({"breed": b, "score": d["p"] * W_PEOPLE + d["g"] * W_GROUP,
                     "people_paths": d["p"], "group_paths": d["g"], "reasons": d["reasons"], **meta})
    rows.sort(key=lambda x: (-x["score"], x["breed"]))
    return rows


# ---------------------------------------------------------------- ui helpers
def breed_card(b, rank=None, score=None, reasons=None):
    head = ""
    if rank is not None:
        head = f'<span class="rank">#{rank}</span><span class="score">{score} คะแนน</span>'
    condo = "🏢 เลี้ยงคอนโดได้" if b.get("condo_ok") else "🏡 ต้องการพื้นที่"
    why = "".join(f'<div class="why">{r}</div>' for r in (reasons or []))
    st.markdown(f"""
    <div class="card">{head}
      <div class="emoji">{b.get('emoji') or '🐶'}</div>
      <div class="name">{b.get('name') or b.get('breed')}</div>
      <div class="meta">กลุ่ม {b.get('grp') or '-'} · {b.get('size') or '-'} · พลังงาน {b.get('energy') or '-'}</div>
      <div class="meta">{condo} · ❤️ {b.get('likes', 0)}</div>
      {why}
    </div>""", unsafe_allow_html=True)


def grid(items, cols=3):
    for i in range(0, len(items), cols):
        cs = st.columns(cols)
        for c, it in zip(cs, items[i:i + cols]):
            with c:
                yield it


def hero(title, sub):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- connection check
try:
    get_driver()
except Exception as e:  # noqa: BLE001
    st.error("เชื่อมต่อ Neo4j ไม่ได้ ตรวจสอบค่าใน Secrets (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)")
    st.exception(e)
    st.stop()

page = st.sidebar.radio("เมนู", ["🏠 Dashboard", "✨ แนะนำสุนัข", "👤 ผู้ใช้", "🐕 สายพันธุ์",
                                 "🕸️ Graph Explorer", "⚙️ Setup"])
st.sidebar.caption("DogRecommet · Neo4j Aura + Streamlit")

# ---------------------------------------------------------------- pages
if page == "🏠 Dashboard":
    hero("🐶 DogRecommet", "ระบบแนะนำสายพันธุ์สุนัขด้วย Graph Database บอกเหตุผลของคำแนะนำได้ทุกครั้ง")
    c = run("""
    CALL { MATCH (u:DogLover) RETURN count(u) AS lovers }
    CALL { MATCH (b:DogBreed) RETURN count(b) AS breeds }
    CALL { MATCH (g:BreedGroup) RETURN count(g) AS groups }
    CALL { MATCH (:DogLover)-[r:LIKES]->(:DogBreed) RETURN count(r) AS likes }
    RETURN lovers, breeds, groups, likes""")[0]
    m = st.columns(4)
    m[0].metric("👤 ผู้ใช้", c["lovers"])
    m[1].metric("🐕 สายพันธุ์", c["breeds"])
    m[2].metric("🧬 กลุ่ม", c["groups"])
    m[3].metric("❤️ ความชอบ (LIKES)", c["likes"])
    if c["breeds"] == 0:
        st.info("ยังไม่มีข้อมูล ไปที่เมนู ⚙️ Setup แล้วกดสร้างข้อมูลตัวอย่าง")
    st.subheader("🔥 สายพันธุ์ยอดนิยม")
    for b in grid(breeds()):
        breed_card(b)

elif page == "✨ แนะนำสุนัข":
    hero("✨ แนะนำสุนัขให้คุณ", "เลือกชื่อหรือพิมพ์ชื่อใหม่ แล้วเลือกสายพันธุ์ที่ชอบ ระบบจะเดินตามเส้นทางในกราฟเพื่อหาคำแนะนำ")
    all_breeds = [b["name"] for b in breeds()]
    names = lovers()
    left, right = st.columns([1, 2])
    with left:
        mode = st.radio("ผู้ใช้", ["เลือกผู้ใช้ที่มีอยู่", "ผู้ใช้ใหม่"], horizontal=True)
        if mode == "เลือกผู้ใช้ที่มีอยู่" and names:
            name = st.selectbox("ชื่อ", names)
        else:
            name = st.text_input("ชื่อของคุณ", placeholder="เช่น Fern").strip()
        condo = st.toggle("🏢 อยู่คอนโด (แนะนำเฉพาะพันธุ์ที่เลี้ยงในคอนโดได้)")
    with right:
        if name:
            current = liked_by(name)
            chosen = st.multiselect("สายพันธุ์ที่คุณชอบ", all_breeds, default=current)
            if st.button("💾 บันทึกความชอบ", type="primary"):
                for b in set(chosen) - set(current):
                    set_like(name, b, True)
                for b in set(current) - set(chosen):
                    set_like(name, b, False)
                run("MERGE (:DogLover {name:$n})", n=name)
                st.success(f"บันทึกความชอบของ {name} แล้ว")
                st.rerun()
    st.caption(f"คะแนน = (คนที่ชอบคล้ายกัน × {W_PEOPLE}) + (กลุ่มสายพันธุ์เดียวกัน × {W_GROUP}) · "
               "ไม่แนะนำพันธุ์ที่คุณกดชอบไปแล้ว")

    if name and liked_by(name):
        recs = recommend(name, condo_only=condo)
        st.subheader(f"คำแนะนำสำหรับ {name}")
        if not recs:
            st.info("ยังไม่มีคำแนะนำจากเส้นทางในกราฟ ลองเลือกสายพันธุ์ที่ชอบเพิ่ม")
        cols_per_row = 3
        for i in range(0, len(recs), cols_per_row):
            cs = st.columns(cols_per_row)
            for j, (c, r) in enumerate(zip(cs, recs[i:i + cols_per_row])):
                with c:
                    breed_card(r, rank=i + j + 1, score=r["score"], reasons=r["reasons"])
                    if st.button("❤️ ชอบพันธุ์นี้", key=f"like_{r['breed']}"):
                        set_like(name, r["breed"], True)
                        st.rerun()
    elif name:
        st.subheader("ยังไม่มีข้อมูลความชอบ — แสดงสายพันธุ์ยอดนิยมแทน")
        for b in grid(breeds()[:3]):
            breed_card(b)

elif page == "👤 ผู้ใช้":
    hero("👤 ผู้ใช้", "ดูว่าแต่ละคนชอบสายพันธุ์อะไร และลบผู้ใช้ได้")
    rows = run("""
    MATCH (u:DogLover) OPTIONAL MATCH (u)-[:LIKES]->(b:DogBreed)
    RETURN u.name AS name, collect(b.name) AS likes ORDER BY name""")
    st.dataframe([{"ชื่อ": r["name"], "สายพันธุ์ที่ชอบ": ", ".join(r["likes"]), "จำนวน": len(r["likes"])}
                  for r in rows], use_container_width=True, hide_index=True)
    with st.form("del_user"):
        target = st.selectbox("เลือกผู้ใช้ที่จะลบ", [r["name"] for r in rows])
        if st.form_submit_button("🗑️ ลบผู้ใช้") and target:
            run("MATCH (u:DogLover {name:$n}) DETACH DELETE u", n=target)
            st.success(f"ลบ {target} แล้ว")
            st.rerun()

elif page == "🐕 สายพันธุ์":
    hero("🐕 จัดการสายพันธุ์", "เพิ่ม แก้ไข หรือลบสายพันธุ์ ทุกการเปลี่ยนแปลงบันทึกลง Neo4j ทันที")
    data = breeds()
    t1, t2, t3 = st.tabs(["📋 รายการ", "➕ เพิ่ม", "✏️ แก้ไข / ลบ"])
    with t1:
        for b in grid(data, 4):
            breed_card(b)
    with t2:
        with st.form("add_breed", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nm = c1.text_input("ชื่อสายพันธุ์ *")
            gp = c2.text_input("กลุ่ม *", placeholder="เช่น Toy, Herding, Spitz")
            sz = c1.selectbox("ขนาด", SIZES)
            en = c2.selectbox("ระดับพลังงาน", ENERGY)
            em = c1.text_input("อีโมจิ", value="🐶")
            co = c2.checkbox("เลี้ยงในคอนโดได้", value=True)
            nt = st.text_input("คำอธิบายสั้น ๆ")
            if st.form_submit_button("เพิ่มสายพันธุ์", type="primary"):
                if nm.strip() and gp.strip():
                    run("""MERGE (b:DogBreed {name:$nm})
                           SET b.size=$sz, b.energy=$en, b.condo_ok=$co, b.emoji=$em, b.note=$nt
                           MERGE (g:BreedGroup {name:$gp}) MERGE (b)-[:IN_GROUP]->(g)""",
                        nm=nm.strip(), gp=gp.strip(), sz=sz, en=en, co=co, em=em, nt=nt)
                    st.success(f"เพิ่ม {nm} แล้ว")
                else:
                    st.warning("กรอกชื่อและกลุ่มให้ครบ")
    with t3:
        if data:
            pick = st.selectbox("เลือกสายพันธุ์", [b["name"] for b in data])
            cur = next(b for b in data if b["name"] == pick)
            with st.form("edit_breed"):
                c1, c2 = st.columns(2)
                gp = c1.text_input("กลุ่ม", value=cur["grp"] or "")
                sz = c2.selectbox("ขนาด", SIZES, index=SIZES.index(cur["size"]) if cur["size"] in SIZES else 0)
                en = c1.selectbox("ระดับพลังงาน", ENERGY, index=ENERGY.index(cur["energy"]) if cur["energy"] in ENERGY else 0)
                em = c2.text_input("อีโมจิ", value=cur["emoji"] or "🐶")
                co = c1.checkbox("เลี้ยงในคอนโดได้", value=bool(cur["condo_ok"]))
                nt = st.text_input("คำอธิบาย", value=cur["note"] or "")
                s1, s2 = st.columns(2)
                save = s1.form_submit_button("💾 บันทึก", type="primary")
                delete = s2.form_submit_button("🗑️ ลบสายพันธุ์นี้")
            if save:
                run("""MATCH (b:DogBreed {name:$nm})
                       SET b.size=$sz, b.energy=$en, b.condo_ok=$co, b.emoji=$em, b.note=$nt
                       WITH b OPTIONAL MATCH (b)-[r:IN_GROUP]->() DELETE r
                       WITH b MERGE (g:BreedGroup {name:$gp}) MERGE (b)-[:IN_GROUP]->(g)""",
                    nm=pick, gp=gp.strip() or "Other", sz=sz, en=en, co=co, em=em, nt=nt)
                run("MATCH (g:BreedGroup) WHERE NOT EXISTS { (g)<-[:IN_GROUP]-() } DELETE g")
                st.success("บันทึกแล้ว")
                st.rerun()
            if delete:
                run("MATCH (b:DogBreed {name:$nm}) DETACH DELETE b", nm=pick)
                run("MATCH (g:BreedGroup) WHERE NOT EXISTS { (g)<-[:IN_GROUP]-() } DELETE g")
                st.success(f"ลบ {pick} แล้ว")
                st.rerun()

elif page == "🕸️ Graph Explorer":
    hero("🕸️ Graph Explorer", "ดูโครงสร้างกราฟทั้งหมด หรือดูเส้นทางคำแนะนำของแต่ละคน")
    names = lovers()
    focus = st.selectbox("เน้นผู้ใช้", ["(ทั้งหมด)"] + names)
    likes = run("MATCH (u:DogLover)-[:LIKES]->(b:DogBreed) RETURN u.name AS a, b.name AS b")
    ingrp = run("MATCH (b:DogBreed)-[:IN_GROUP]->(g:BreedGroup) RETURN b.name AS a, g.name AS b")
    q = lambda s: '"' + s.replace('"', "'") + '"'
    dot = ['digraph G { rankdir=LR; bgcolor="transparent"; node [style=filled, fontname="Helvetica", fontcolor=white, color=white];',
           'subgraph cluster_l { label=""; color=transparent; node [shape=circle, fillcolor="#7C6FD0", width=0.9]; ']
    dot += [q(n) + ";" for n in names] + ["}"]
    dot += ['node [shape=box, style="rounded,filled", fillcolor="#2A9D8F"];']
    dot += [q(b["name"]) + ";" for b in breeds()]
    dot += ['node [shape=ellipse, fillcolor="#E9A23B"];'] + [q(g) + ";" for g in groups()]
    hot = set()
    if focus != "(ทั้งหมด)":
        hot = {r["breed"] for r in recommend(focus)}
        dot.append(f'{q(focus)} [fillcolor="#C2410C", penwidth=3];')
        dot += [f'{q(b)} [fillcolor="#F59E0B", fontcolor="#1f2937"];' for b in hot]
    for e in likes:
        strong = focus != "(ทั้งหมด)" and e["a"] == focus
        dot.append(f'{q(e["a"])} -> {q(e["b"])} [color="{"#C2410C" if strong else "#94A3B8"}", penwidth={2.5 if strong else 1.2}];')
    for e in ingrp:
        dot.append(f'{q(e["a"])} -> {q(e["b"])} [color="#B5527A", style=dashed];')
    dot.append("}")
    st.graphviz_chart("\n".join(dot), use_container_width=True)
    st.caption("ม่วง = ผู้ใช้ · เขียว = สายพันธุ์ · เหลือง = กลุ่ม · เส้นประ = IN_GROUP"
               + (" · ส้ม = สายพันธุ์ที่ระบบแนะนำ" if hot else ""))

elif page == "⚙️ Setup":
    hero("⚙️ Setup", "สร้างข้อมูลตัวอย่างใหม่ทั้งหมด (ลบเฉพาะข้อมูลของระบบนี้)")
    st.write("ข้อมูลตัวอย่าง: ผู้ใช้ 5 คน · สายพันธุ์ 8 พันธุ์ · กลุ่ม 4 กลุ่ม · ความชอบ 11 รายการ")
    if st.button("🚀 สร้างข้อมูลตัวอย่าง", type="primary"):
        setup_sample_data()
        st.success("สร้างข้อมูลตัวอย่างเรียบร้อย")
        st.balloons()
