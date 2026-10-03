"""Mobile AI Recommender: หามือถือ 5 รุ่นที่เหมาะกับงบและการใช้งาน (เน้นรุ่นที่ขายในไทย)"""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import ui
from ai_service import compact, explain, has_gemini_key
from config import DATASET_NAME, DEFAULT_INR_TO_THB, TOP_N
from dataset_service import apply_manual_specs, apply_prices, coverage, load_dataset, load_prices, prices_csv
from firebase_auth import guest_allowed, login_user, register_user, reset_password
from scoring_service import DIMENSIONS, USE_CASE_ICONS, USE_CASES, Request, pros_cons, recommend, score, spec_text
from thailand_filter import load_catalog
from youtube_service import has_youtube_key, review_videos, search_link

st.set_page_config(page_title="Mobile AI Recommender", page_icon="📱", layout="wide")
ui.apply_theme()

PRIORITIES = ["ประสิทธิภาพ", "กล้อง", "กล้องหน้า", "แบตเตอรี่", "ชาร์จเร็ว", "จอลื่น", "ความจุ", "ความคุ้มค่า"]
SPEC_TABLE = {"chipset": "ชิป", "ram_gb": "RAM (GB)", "storage_gb": "ความจุเริ่มต้น (GB)", "camera_mp": "กล้องหลัก (MP)",
              "front_mp": "กล้องหน้า (MP)", "battery_mah": "แบต (mAh)", "charging_w": "ชาร์จ (W)", "display_in": "จอ (นิ้ว)",
              "refresh_hz": "รีเฟรช (Hz)", "os": "ระบบ"}
RADAR_COLORS = [ui.INDIGO, "#E07A00", "#0E7A4F"]


# ---------------------------------------------------------------------------
# state และ cache
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults = {"user": None, "result": None, "prices": None, "thailand_only": True, "inr_to_thb": DEFAULT_INR_TO_THB}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


@st.cache_data(show_spinner="กำลังโหลดข้อมูลมือถือ...")
def base_dataset() -> pd.DataFrame:
    return apply_manual_specs(load_dataset())


@st.cache_data(show_spinner=False, ttl=86400)
def cached_explain(request_json: str, picks_json: str) -> dict:
    return explain(json.loads(request_json), json.loads(picks_json))


@st.cache_data(show_spinner=False, ttl=86400 * 7)
def cached_videos(name: str) -> list[dict]:
    return review_videos(name)


def current_prices() -> pd.DataFrame:
    if st.session_state.prices is None:
        st.session_state.prices = load_prices()
    return st.session_state.prices


def show_all_models() -> None:
    st.session_state.thailand_only = False
    st.session_state.result = None
    st.session_state.run_again = True


def radar(rows: pd.DataFrame, names: list[str]) -> go.Figure:
    dims = list(DIMENSIONS)
    labels = [DIMENSIONS[d][2] for d in dims]
    fig = go.Figure()
    for i, (_, r) in enumerate(rows.iterrows()):
        values = [0 if pd.isna(r.get(f"s_{d}")) else r[f"s_{d}"] for d in dims]
        fig.add_trace(go.Scatterpolar(r=values + values[:1], theta=labels + labels[:1], name=names[i], fill="toself",
                                      opacity=0.55, line=dict(color=RADAR_COLORS[i % 3], width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor=ui.LINE),
                                 angularaxis=dict(gridcolor=ui.LINE)),
                      height=420, margin=dict(l=40, r=40, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Anuphan, sans-serif", size=14, color=ui.INK),
                      legend=dict(orientation="h", y=-0.08))
    return fig


init_state()

# ---------------------------------------------------------------------------
# ล็อกอิน
# ---------------------------------------------------------------------------
if st.session_state.user is None:
    left, right = st.columns([5, 4], gap="large")
    with left:
        ui.hero("เลือกมือถือที่ใช่ ในงบที่มี",
                "บอกงบกับสิ่งที่ใช้บ่อย แล้วดู 5 รุ่นที่เหมาะที่สุด พร้อมข้อดีข้อเสียจากสเปกจริงและคลิปรีวิว")
        ui.html_block(ui.chips(["📚 เรียน", "🎮 เล่นเกม", "📸 ถ่ายรูป", "🔋 แบตอึด", "💼 ทำงาน"]))
    with right:
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("อีเมล")
                    password = st.text_input("รหัสผ่าน", type="password")
                    submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
                if submitted:
                    if not email or not password:
                        st.error("กรอกอีเมลและรหัสผ่านก่อน")
                    else:
                        with st.spinner("กำลังเข้าสู่ระบบ..."):
                            result = login_user(email, password)
                        if result["ok"]:
                            st.session_state.user = result
                            st.rerun()
                        st.error(result["message"])
                with st.expander("ลืมรหัสผ่าน"):
                    with st.form("reset_form"):
                        reset_email = st.text_input("อีเมลที่สมัครไว้")
                        if st.form_submit_button("ส่งลิงก์ตั้งรหัสใหม่"):
                            r = reset_password(reset_email) if reset_email else {"ok": False, "message": "กรอกอีเมลก่อน"}
                            (st.success if r["ok"] else st.error)(r["message"])
            with tab_register:
                with st.form("register_form"):
                    reg_email = st.text_input("อีเมล", key="reg_email")
                    reg_pw = st.text_input("รหัสผ่าน (อย่างน้อย 6 ตัว)", type="password")
                    reg_pw2 = st.text_input("ยืนยันรหัสผ่าน", type="password")
                    submitted = st.form_submit_button("สร้างบัญชี", use_container_width=True)
                if submitted:
                    if not reg_email or not reg_pw:
                        st.error("กรอกข้อมูลให้ครบ")
                    elif reg_pw != reg_pw2:
                        st.error("รหัสผ่านสองช่องไม่ตรงกัน")
                    else:
                        with st.spinner("กำลังสร้างบัญชี..."):
                            result = register_user(reg_email, reg_pw)
                        (st.success if result["ok"] else st.error)(
                            "สร้างบัญชีแล้ว เข้าสู่ระบบได้เลย" if result["ok"] else result["message"])
            if guest_allowed():
                if st.button("ลองใช้โดยไม่ล็อกอิน (โหมดทดสอบ)", key="guest", use_container_width=True):
                    st.session_state.user = {"ok": True, "email": "ผู้ทดสอบ"}
                    st.rerun()
    st.stop()

# ---------------------------------------------------------------------------
# ข้อมูล + แถบข้าง
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"**{ui.esc(st.session_state.user.get('email', '-'))}**")
    if st.button("ออกจากระบบ", key="logout"):
        st.session_state.user = None
        st.session_state.result = None
        st.rerun()
    st.divider()
    st.markdown("**ตั้งค่าราคา**")
    st.number_input("อัตราแลกเปลี่ยน (บาท ต่อ 1 รูปี)", 0.10, 1.00, step=0.01, format="%.3f", key="inr_to_thb",
                    help="ใช้แปลงราคาอินเดียเป็นราคาประมาณ สำหรับรุ่นที่ยังไม่ได้ใส่ราคาไทย ตรวจอัตราวันนี้ก่อนใช้")
    st.caption("ราคาไทยที่กรอกในแท็บ “ราคาไทย” จะใช้แทนราคาประมาณเสมอ")
    st.divider()
    st.caption(f"ข้อมูลสเปก: {DATASET_NAME}")
    st.caption(("✅" if has_gemini_key() else "⚪") + " Gemini อธิบายผล" + ("" if has_gemini_key() else " (ยังไม่ตั้ง key)"))
    st.caption(("✅" if has_youtube_key() else "⚪") + " คลิปรีวิว YouTube" + ("" if has_youtube_key() else " (ใช้ลิงก์ค้นหา)"))

try:
    phones = apply_prices(base_dataset(), current_prices(), st.session_state.inr_to_thb)
except (FileNotFoundError, ValueError) as err:
    st.error(f"อ่านไฟล์ข้อมูลมือถือไม่ได้: {err} ตรวจว่ามีไฟล์ data/smartphones_2026.csv")
    st.stop()
cov = coverage(phones)

tab_find, tab_compare, tab_price, tab_about = st.tabs(["หามือถือ", "เทียบเอง", "ราคาไทย", "ข้อมูลและวิธีคิด"])

# ---------------------------------------------------------------------------
# แท็บ: หามือถือ
# ---------------------------------------------------------------------------
with tab_find:
    ui.hero("เลือกมือถือที่ใช่ ในงบที่มี", "ตั้งงบและการใช้งาน ระบบจะเทียบสเปกจริงแล้วเลือก 5 รุ่นที่คุ้มที่สุดให้")
    with st.container(border=True):
        budget = st.slider("งบประมาณ (บาท)", 0, 80000, (0, 15000), 500, key="budget", format="฿%d")
        use_case = ui.pills("ใช้ทำอะไรเป็นหลัก", list(USE_CASES), multi=False, default="ใช้งานทั่วไป/เรียน", key="use_case",
                            format_func=lambda x: f"{USE_CASE_ICONS.get(x, '')} {x}")
        priorities = ui.pills("อยากให้เด่นเรื่องไหนเป็นพิเศษ (เลือกได้หลายข้อ)", PRIORITIES, multi=True, default=[],
                              key="priorities")
        with st.expander("ตัวกรองเพิ่มเติม"):
            c1, c2 = st.columns(2)
            with c1:
                brands = st.multiselect("แบรนด์", sorted(phones["brand"].unique()), key="brands",
                                        placeholder="ทุกแบรนด์")
                min_storage = st.selectbox("ความจุขั้นต่ำ", [0, 128, 256, 512], key="min_storage",
                                           format_func=lambda x: "ไม่กำหนด" if x == 0 else f"{x} GB ขึ้นไป")
            with c2:
                need_5g = st.checkbox("ต้องรองรับ 5G", key="need_5g")
                need_nfc = st.checkbox("ต้องมี NFC", key="need_nfc")
                st.toggle("เฉพาะรุ่นที่ขายอย่างเป็นทางการในไทย", key="thailand_only",
                          help=f"ตามรายชื่อใน thailand_catalog.json ตอนนี้พบใน dataset {cov['thai_matched']} รุ่น")
            note = st.text_area("บอกเพิ่มได้ (AI จะนำไปอธิบาย)", key="note", max_chars=300,
                                placeholder="เช่น ถ่ายกลางคืนบ่อย มือเล็ก ใช้ LINE ทั้งวัน")
        go_clicked = st.button(f"หา {TOP_N} รุ่นที่เหมาะที่สุด", type="primary", key="go", use_container_width=True)

    if go_clicked or st.session_state.pop("run_again", False):
        req = Request(budget_min=budget[0], budget_max=budget[1] or None, use_case=use_case, priorities=priorities,
                      brands=brands, min_storage=min_storage, need_5g=need_5g, need_nfc=need_nfc,
                      thailand_only=st.session_state.thailand_only, note=note)
        picks, n_cands = recommend(phones, req, TOP_N)
        rows = [compact(r, *pros_cons(r, req)) for _, r in picks.iterrows()]
        ai = None
        if rows:
            with st.spinner("กำลังสรุปคำแนะนำ..."):
                ai = cached_explain(json.dumps(req.describe(), ensure_ascii=False, sort_keys=True),
                                    json.dumps(rows, ensure_ascii=False))
        st.session_state.result = {"req": req, "picks": picks, "rows": rows, "ai": ai, "n": n_cands}

    res = st.session_state.result
    if res is None:
        st.markdown(f'<p class="note">ฐานข้อมูลมี {cov["dataset_models"]} รุ่น ในจำนวนนี้ {cov["thai_matched"]} รุ่น'
                    f'อยู่ในรายชื่อขายในไทย</p>', unsafe_allow_html=True)
    elif res["picks"].empty:
        st.warning("ไม่มีรุ่นที่ตรงทุกเงื่อนไข ลองขยายงบ ลดความจุขั้นต่ำ หรือเอาตัวกรองแบรนด์/5G/NFC ออก")
        if res["req"].thailand_only:
            st.button("ค้นจากทุกรุ่นในฐานข้อมูล", on_click=show_all_models, key="widen_empty")
    else:
        req, ai, picks = res["req"], res["ai"], res["picks"]
        scope = "รุ่นที่ขายในไทย" if req.thailand_only else "ทุกรุ่นในฐานข้อมูล"
        st.markdown(f'<p class="note">เทียบ {res["n"]} รุ่นจาก{scope} ในงบ {ui.baht(req.budget_min)}–{ui.baht(req.budget_max)}'
                    f' สำหรับ{req.use_case}</p>', unsafe_allow_html=True)
        if res["n"] < TOP_N and req.thailand_only:
            st.info(f"มีรุ่นที่ขายในไทยตรงเงื่อนไขแค่ {res['n']} รุ่น")
            st.button("ดูตัวเลือกจากทุกรุ่นในฐานข้อมูล", on_click=show_all_models, key="widen")
        if ai.get("error"):
            st.caption(ai["error"])
        if ai.get("summary"):
            ui.html_block(f'<div class="summary">{ui.esc(ai["summary"])}</div>')

        for i, (row, item) in enumerate(zip(res["rows"], ai["items"]), start=1):
            r = picks.iloc[i - 1]
            with st.container(border=True):
                head, price = st.columns([3, 1.3])
                sub = ", ".join(x for x in (spec_text(r, "performance"), spec_text(r, "storage"),
                                            spec_text(r, "battery")) if x)
                if not r["in_thailand"]:
                    sub += " (ไม่อยู่ในรายชื่อขายในไทย)"
                with head:
                    ui.html_block(ui.pick_header(i, r["name"], sub))
                with price:
                    ui.html_block(ui.price_block(r["price_thb"], r["price_kind"], highlight=i == 1))
                ui.html_block(ui.meter(r["score"]) + f'<p class="why">{ui.esc(item.get("why", ""))}</p>')
                good, bad = st.columns(2)
                with good:
                    ui.html_block('<div class="list-title">ข้อดี</div>' + ui.chips(item.get("pros", []), "good"))
                with bad:
                    ui.html_block('<div class="list-title">ข้อควรรู้</div>' + ui.chips(item.get("cons", []), "bad"))
                if item.get("best_for"):
                    ui.html_block(f'<p class="note">เหมาะกับ: {ui.esc(item["best_for"])}</p>')
                videos = cached_videos(r["name"])
                if videos:
                    links = "".join(f'<li><a href="{ui.esc(v["url"])}" target="_blank" rel="noopener">{ui.esc(v["title"])}</a>'
                                    f' <span class="note">{ui.esc(v["channel"])}</span></li>' for v in videos)
                    ui.html_block(f'<div class="list-title">คลิปรีวิว</div><ul>{links}</ul>')
                else:
                    st.link_button(f"ดูรีวิว {r['name']} บน YouTube", search_link(r["name"]))

        st.subheader("เทียบจุดเด่นแต่ละด้าน")
        top3 = picks.head(3)
        st.plotly_chart(radar(top3, list(top3["name"])), use_container_width=True, config={"displayModeBar": False})
        st.caption("คะแนนแต่ละด้าน 0–100 เทียบกับรุ่นอื่นที่ผ่านการกรองในรอบนี้ (100 = ดีที่สุดในกลุ่ม)")
        table = pd.DataFrame({"รุ่น": picks["name"], "ราคา (บาท)": picks["price_thb"], "คะแนน": picks["score"]})
        for col, label in SPEC_TABLE.items():
            table[label] = picks[col]
        st.dataframe(table, hide_index=True, use_container_width=True, column_config={
            "ราคา (บาท)": st.column_config.NumberColumn(format="%.0f"),
            "คะแนน": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f")})
        caution = ai.get("caution") or "ราคาและโปรโมชันเปลี่ยนบ่อย ตรวจกับร้านค้าก่อนซื้อ"
        st.caption(caution + (f" ระบบตัดคำตอบของ AI ที่อ้างถึงรุ่นนอกรายการ {ai['dropped']} รายการ" if ai.get("dropped") else ""))

# ---------------------------------------------------------------------------
# แท็บ: เทียบเอง
# ---------------------------------------------------------------------------
with tab_compare:
    st.subheader("เลือก 2–3 รุ่นมาเทียบกัน")
    pool = phones[phones["in_thailand"]] if st.session_state.thailand_only else phones
    chosen = st.multiselect("รุ่นที่อยากเทียบ", sorted(pool["name"]), max_selections=3, key="compare_pick",
                            placeholder="พิมพ์ชื่อรุ่น เช่น Galaxy S26")
    if len(chosen) >= 2:
        scored = score(pool, Request(use_case=st.session_state.get("use_case") or "ใช้งานทั่วไป/เรียน"))
        sel = scored[scored["name"].isin(chosen)].set_index("name").loc[chosen].reset_index()
        st.plotly_chart(radar(sel, chosen), use_container_width=True, config={"displayModeBar": False})
        view = sel.set_index("name")[["price_thb", "price_kind"] + list(SPEC_TABLE) + ["has_5g", "has_nfc"]]
        view = view.rename(columns={"price_thb": "ราคา (บาท)", "price_kind": "ที่มาราคา", "has_5g": "5G", "has_nfc": "NFC",
                                    **SPEC_TABLE}).T
        st.dataframe(view.astype(str).replace({"nan": "—", "None": "—", "True": "มี", "False": "ไม่มี"}),
                     use_container_width=True)
        st.caption("คะแนนบนกราฟเทียบกับทุกรุ่นในกลุ่มที่เลือก (ขายในไทย หรือทั้งฐานข้อมูล)")
    else:
        st.markdown('<p class="note">เลือกอย่างน้อย 2 รุ่น</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# แท็บ: ราคาไทย
# ---------------------------------------------------------------------------
with tab_price:
    st.subheader("ราคาขายในไทย")
    st.write("ใส่ราคาเริ่มต้นจากเว็บแบรนด์ทางการ ระบบจะใช้ราคานี้แทนราคาประมาณ กด “ใช้ราคานี้” แล้วดาวน์โหลดไฟล์ไปแทนที่ "
             "`data/prices.csv` ใน GitHub เพื่อเก็บถาวร")
    m1, m2, m3 = st.columns(3)
    m1.metric("รุ่นในรายชื่อไทย", cov["catalog_models"])
    m2.metric("พบใน dataset", cov["thai_matched"])
    m3.metric("ใส่ราคาไทยแล้ว", cov["thai_priced"])
    edited = st.data_editor(current_prices(), hide_index=True, num_rows="dynamic", key="price_editor",
                            use_container_width=True, column_config={
                                "brand": st.column_config.TextColumn("แบรนด์"), "model": st.column_config.TextColumn("รุ่น"),
                                "price_thb": st.column_config.NumberColumn("ราคา (บาท)", min_value=0, format="%.0f"),
                                "updated": st.column_config.TextColumn("วันที่เช็ก", help="เช่น 2026-10-03"),
                                "source": st.column_config.TextColumn("ที่มา", help="ลิงก์หน้าเว็บแบรนด์")})
    a, b = st.columns(2)
    with a:
        if st.button("ใช้ราคานี้", type="primary", key="apply_prices", use_container_width=True):
            st.session_state.prices = edited.reset_index(drop=True)
            st.session_state.result = None
            st.success("ใช้ราคาใหม่แล้ว กดหามือถืออีกครั้งเพื่อดูผล")
    with b:
        st.download_button("ดาวน์โหลด prices.csv", prices_csv(edited), "prices.csv", "text/csv", key="dl_prices",
                           use_container_width=True)
    if cov["missing"]:
        with st.expander(f"รุ่นในรายชื่อไทยที่ยังไม่พบใน dataset ({len(cov['missing'])} รุ่น)"):
            st.write(", ".join(cov["missing"]))
            st.caption("อาจเป็นรุ่นที่ dataset ยังไม่มี หรือชื่อเรียกต่างกันในแต่ละประเทศ เติมสเปกเองได้ใน data/specs_manual.csv")

# ---------------------------------------------------------------------------
# แท็บ: ข้อมูลและวิธีคิด
# ---------------------------------------------------------------------------
with tab_about:
    st.subheader("ระบบเลือกให้อย่างไร")
    st.markdown("""
1. **กรอง** ตามงบ แบรนด์ ความจุ 5G/NFC และเลือกได้ว่าจะดูเฉพาะรุ่นที่ขายอย่างเป็นทางการในไทย
2. **ให้คะแนนรายด้าน** ประสิทธิภาพ กล้องหลัก กล้องหน้า แบต ชาร์จเร็ว จอลื่น ความจุ RAM เป็น 0–100 โดยเทียบกับรุ่นอื่นในกลุ่ม
3. **ถ่วงน้ำหนักตามการใช้งาน** เช่น เล่นเกมเน้นประสิทธิภาพและจอ ถ่ายรูปเน้นกล้องและความจุ ด้านที่คุณเลือกเน้นจะได้น้ำหนักเพิ่ม
4. **คิดความคุ้มค่า** จากคะแนนสเปกต่อบาท รุ่นที่ข้อมูลไม่ครบจะถูกลดคะแนนตามสัดส่วน
5. **ข้อดี/ข้อควรรู้** มาจากคะแนนรายด้าน (≥70 = เด่น, ≤30 = ด้อย) อ้างตัวเลขจริง
6. **AI อธิบาย** Gemini เขียนเหตุผลจาก 5 รุ่นที่ระบบเลือกแล้วเท่านั้น ระบบตัดคำตอบที่พูดถึงรุ่นอื่นทิ้ง ถ้าไม่มี key ใช้คำอธิบายจากสูตรแทน
""")
    st.subheader("แหล่งข้อมูล")
    cat = load_catalog()
    st.markdown(f"""
- **สเปกและราคาอินเดีย**: {DATASET_NAME} ({cov['dataset_models']} รุ่นหลังรวมรุ่นย่อย)
- **รายชื่อรุ่นที่ขายในไทย**: `thailand_catalog.json` อัปเดต {cat.get('updated', '-')} จากเว็บแบรนด์ทางการ
- **ราคาไทย**: กรอกเองใน `data/prices.csv` ถ้าไม่มี ใช้ราคาอินเดีย × {st.session_state.inr_to_thb:.3f} บาท/รูปี (เป็นค่าประมาณเท่านั้น)
""")
    st.subheader("ข้อจำกัด")
    st.markdown("""
- ราคาประมาณจากอินเดียไม่ใช่ราคาไทย ภาษีและโปรโมชันต่างกัน ใส่ราคาไทยจริงก่อนนำเสนอหรือใช้งานจริง
- คะแนนประสิทธิภาพประมาณจากชื่อชิป ไม่ใช่ผล benchmark
- จำนวนเมกะพิกเซลไม่ได้บอกคุณภาพภาพทั้งหมด ควรดูรีวิวประกอบ
- คะแนนเป็นการเทียบในกลุ่มที่ผ่านการกรอง เปลี่ยนงบแล้วคะแนนเปลี่ยนได้
""")
    with st.expander("ดูฐานข้อมูลทั้งหมด"):
        cols = ["name", "in_thailand", "price_thb", "price_kind", "variants"] + list(SPEC_TABLE)
        st.dataframe(phones[cols].rename(columns={"name": "รุ่น", "in_thailand": "ขายในไทย", "price_thb": "ราคา (บาท)",
                                                  "price_kind": "ที่มาราคา", "variants": "รุ่นย่อย", **SPEC_TABLE}),
                     hide_index=True, use_container_width=True)
