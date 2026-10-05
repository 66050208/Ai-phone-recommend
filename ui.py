"""หน้าตาเว็บ: ธีม CSS และชิ้นส่วน UI ที่ใช้ซ้ำ

แนวคิด v11: palette หลัก #353A5F → #9EBAF3 เป็นพื้นหลังไล่สีแบบเบลอจางๆ ทุกหน้า
กรอบต่างๆ เป็นกระจกฝ้า (frosted glass) มองทะลุเห็นพื้นหลังได้ แถบเมนูด้านข้างสีขาว
ตารางมีเงาให้ดูนูนเป็น 3 มิติ ราคาอันดับ 1 ยังใช้ป้ายเหลืองจุดเดียว ฟอนต์ Anuphan
"""
from __future__ import annotations

import html
import urllib.parse

import pandas as pd
import streamlit as st

INK = "#16203A"
MUTED = "#4F5A75"
LINE = "#D5DCEA"
SURFACE = "#FFFFFF"
PAGE = "#EEF2FA"
NAVY = "#353A5F"      # palette สีหลัก (เข้ม)
SKY = "#9EBAF3"       # palette สีหลัก (อ่อน)
INDIGO = "#3E4C94"    # สีเน้น อยู่ระหว่าง NAVY กับ SKY แต่เข้มพอให้ตัวอักษรขาวบนปุ่มอ่านชัด
DANGER = "#E0352B"
TAG = "#FFD23F"
GOOD = "#0E7A4F"
BAD = "#B4372F"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Anuphan:wght@400;500;600;700&display=swap');
/* ฟอนต์: ใส่เฉพาะข้อความ ห้ามแตะ span ทั่วไป ไม่งั้นไอคอนจะกลายเป็นตัวหนังสือ เช่น "visibility" */
html, body, .stApp, p, li, label, input, textarea, button, h1, h2, h3, h4,
[data-testid="stMarkdownContainer"], [data-baseweb="tab"], [data-baseweb="select"] {{
  font-family: 'Anuphan', 'Noto Sans Thai', sans-serif;
}}
[data-testid="stIconMaterial"], .material-symbols-rounded, .material-icons {{
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}}

/* บังคับโทนสว่างทั้งหน้า ให้หน้าตาเหมือนกันแม้เบราว์เซอร์หรือ Streamlit ตั้งเป็นธีมมืด */
/* พื้นหลัง: palette หลักแบบเบลอ จางๆ ไม่แย่งสายตา (ทุกหน้า รวมหน้าล็อกอิน) */
.stApp {{ color: {INK};
  background:
    radial-gradient(42rem 32rem at 8% 6%, rgba(53,58,95,.30), transparent 70%),
    radial-gradient(46rem 34rem at 92% 10%, rgba(158,186,243,.75), transparent 70%),
    radial-gradient(40rem 30rem at 78% 92%, rgba(95,116,176,.32), transparent 70%),
    radial-gradient(36rem 28rem at 18% 88%, rgba(158,186,243,.55), transparent 70%),
    linear-gradient(135deg, #E3E9F7 0%, #EDF1FA 50%, #E6ECF9 100%);
  background-attachment: fixed; }}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main {{ background: transparent; }}
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"],
[data-testid="stMarkdownContainer"], [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
[data-testid="stExpander"] summary, [data-testid="stCheckbox"] label {{ color: {INK}; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: {MUTED}; }}

input, textarea, [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"],
[data-baseweb="select"] > div, [data-testid="stNumberInputContainer"] {{
  background: {SURFACE} !important; color: {INK} !important; border-color: {LINE} !important; }}
input::placeholder, textarea::placeholder {{ color: #8A93A8 !important; }}
[data-testid="stNumberInputContainer"] button {{ background: {PAGE}; color: {INK}; }}
[data-baseweb="tab-list"] {{ gap: .4rem; border-bottom: 1px solid {LINE}; }}
[data-baseweb="tab"] {{ color: {MUTED}; }}
[data-baseweb="tab"][aria-selected="true"] {{ color: {INDIGO}; }}
[data-baseweb="tab-highlight"] {{ background: {INDIGO}; }}

.block-container {{ max-width: 1120px; padding-top: 4.5rem; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
/* กรอบกระจกฝ้า: ขุ่นๆ มัวๆ แต่ยังเห็นสีพื้นหลังทะลุ (ใช้กับทุกกรอบ ยกเว้นแถบเมนู) */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background: rgba(255,255,255,.46); border: 1px solid rgba(255,255,255,.75) !important; border-radius: 20px;
  -webkit-backdrop-filter: blur(18px) saturate(150%); backdrop-filter: blur(18px) saturate(150%);
  box-shadow: 0 10px 34px rgba(53,58,95,.14), inset 0 1px 0 rgba(255,255,255,.85); }}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {{
  background: transparent; box-shadow: none; -webkit-backdrop-filter: none; backdrop-filter: none; }}
.glass, .summary, .upgrade, .mini {{
  background: rgba(255,255,255,.5) !important; border: 1px solid rgba(255,255,255,.75) !important;
  -webkit-backdrop-filter: blur(16px) saturate(150%); backdrop-filter: blur(16px) saturate(150%);
  box-shadow: 0 8px 26px rgba(53,58,95,.12), inset 0 1px 0 rgba(255,255,255,.85); }}
/* กราฟอยู่บนกระจกที่ขุ่นกว่าเล็กน้อย เพื่อให้เส้นและสีในกราฟอ่านชัด */
[data-testid="stPlotlyChart"] {{
  background: rgba(255,255,255,.66); border: 1px solid rgba(255,255,255,.8); border-radius: 18px; padding: .7rem .6rem .3rem;
  -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  box-shadow: 0 10px 30px rgba(53,58,95,.13), inset 0 1px 0 rgba(255,255,255,.9); }}

/* ปุ่ม: หลัก = น้ำเงินคราม (รวมปุ่มในฟอร์ม), รอง = ขาวขอบเทา */
button[kind="primary"], button[kind="primaryFormSubmit"], [data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"] {{
  background: linear-gradient(135deg, {NAVY} 0%, #5C70B8 100%) !important; border-color: transparent !important;
  color: #fff !important; font-weight: 600; box-shadow: 0 6px 18px rgba(53,58,95,.28); }}
button[kind="primary"] p, [data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primaryFormSubmit"] p {{ color: #fff !important; }}
button[kind="secondary"], button[kind="secondaryFormSubmit"], [data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stBaseLinkButton-secondary"] {{
  background: {SURFACE} !important; color: {INK} !important; border: 1px solid {LINE} !important; }}
/* ปุ่มเม็ดยา (st.pills) */
[data-testid="stBaseButton-pills"] {{ background: {SURFACE} !important; color: {INK} !important; border: 1px solid {LINE} !important; }}
[data-testid="stBaseButton-pillsActive"] {{ background: #ECEDFC !important; color: {INDIGO} !important;
  border: 1px solid {INDIGO} !important; font-weight: 600; }}
[data-testid="stBaseButton-pills"] p, [data-testid="stBaseButton-pillsActive"] p {{ color: inherit !important; }}
button:focus-visible, a:focus-visible {{ outline: 3px solid {TAG} !important; outline-offset: 2px; }}
.stApp a {{ color: {INDIGO}; }}

.hero h1 {{ font-size: clamp(1.9rem, 4vw, 2.7rem); line-height: 1.15; margin: 0 0 .35rem; font-weight: 700; }}
.hero p {{ color: {MUTED}; font-size: 1.05rem; margin: 0 0 1.2rem; max-width: 62ch; }}

.rank {{ display: inline-flex; align-items: center; justify-content: center; width: 2rem; height: 2rem;
  border-radius: 50%; background: {INK}; color: #fff; font-weight: 700; margin-right: .6rem; flex: none; }}
.rank.first {{ background: {INDIGO}; }}
.pick-head {{ display: flex; align-items: center; gap: .2rem; }}
.pick-name {{ font-size: 1.35rem; font-weight: 700; color: {INK}; margin: 0; line-height: 1.25; }}
.pick-sub {{ color: {MUTED}; font-size: .92rem; margin: .15rem 0 0 2.6rem; }}

.price {{ text-align: right; }}
.price .amount {{ font-size: 1.6rem; font-weight: 700; color: {INK}; line-height: 1.1; }}
.price .kind {{ font-size: .8rem; color: {MUTED}; }}
.price.tag .amount {{ display: inline-block; background: {TAG}; padding: .25rem .75rem .3rem 1.4rem; border-radius: 6px;
  position: relative; }}
.price.tag .amount::before {{ content: ""; position: absolute; left: .55rem; top: 50%; width: 7px; height: 7px;
  margin-top: -3.5px; border-radius: 50%; background: {SURFACE}; box-shadow: inset 0 0 0 1px rgba(22,32,58,.35); }}

.meter {{ height: 8px; background: rgba(53,58,95,.12); border-radius: 99px; overflow: hidden; margin: .55rem 0 .2rem; }}
.meter > span {{ display: block; height: 100%; background: linear-gradient(90deg, {NAVY}, #7F98D6); border-radius: 99px; }}
.meter-label {{ font-size: .85rem; color: {MUTED}; }}

.chips {{ display: flex; flex-wrap: wrap; gap: .35rem; margin: .3rem 0 .2rem; }}
.chip {{ font-size: .84rem; padding: .18rem .6rem; border-radius: 99px; border: 1px solid {LINE}; background: {PAGE}; color: {INK}; }}
.chip.good {{ border-color: #BFE3D2; background: #EEF8F3; color: {GOOD}; }}
.chip.bad {{ border-color: #F0C9C5; background: #FCF1F0; color: {BAD}; }}
.why {{ margin: .6rem 0 .3rem; font-size: 1rem; line-height: 1.6; max-width: 75ch; }}
.list-title {{ font-weight: 600; font-size: .92rem; margin-top: .5rem; }}
.summary {{ border-left: 4px solid {INDIGO} !important; padding: .9rem 1.1rem; border-radius: 0 12px 12px 0;
  margin: .4rem 0 1rem; line-height: 1.6; }}
.note {{ color: {MUTED}; font-size: .86rem; }}
/* ตารางเทียบรุ่น */
/* ตาราง: สีเดิม แต่ยกให้นูนเป็น 3 มิติด้วยเงาหลายชั้น + ขอบล่างหนา */
.cmp {{ width: 100%; border-collapse: separate; border-spacing: 0; background: {SURFACE}; border: 1px solid {LINE};
  border-bottom: 4px solid #C3CDE3; border-radius: 16px; overflow: hidden; font-size: .95rem;
  box-shadow: 0 1px 0 rgba(255,255,255,.9) inset, 0 2px 4px rgba(53,58,95,.08), 0 12px 24px rgba(53,58,95,.16),
              0 28px 48px -18px rgba(53,58,95,.28); }}
.cmp th, .cmp td {{ padding: .6rem .8rem; border-bottom: 1px solid {LINE}; text-align: left; vertical-align: top;
  line-height: 1.45; white-space: normal; }}
.cmp thead th {{ background: linear-gradient(180deg, #F7F9FD 0%, {PAGE} 100%); font-weight: 700; color: {INK};
  box-shadow: inset 0 -2px 0 {LINE}; }}
.cmp tbody tr {{ transition: background .15s; }}
.cmp tbody tr:hover {{ background: #F5F8FE; }}
.cmp tbody th {{ color: {MUTED}; font-weight: 500; width: 26%; }}
.cmp td.best {{ color: {GOOD}; font-weight: 700; }}
.cmp tr:last-child th, .cmp tr:last-child td {{ border-bottom: 0; }}
.cmp-wrap {{ overflow-x: auto; margin: .4rem 0 1.4rem; padding: 4px 6px 30px; }}

/* การ์ดรุ่นในหน้าดูทุกรุ่น */
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: .8rem; margin-top: .6rem; }}
.mini {{ border-radius: 16px; padding: .9rem 1rem; display: flex;
  flex-direction: column; gap: .3rem; }}
.mini .n {{ font-weight: 700; font-size: 1.05rem; color: {INK}; line-height: 1.3; }}
.mini .p {{ font-weight: 700; font-size: 1.15rem; color: {INDIGO}; }}
.mini .k {{ font-size: .78rem; color: {MUTED}; }}
.mini .chips {{ margin: .2rem 0 0; }}
.mini .chip {{ font-size: .78rem; padding: .1rem .5rem; }}
.flag {{ font-size: .75rem; color: {GOOD}; font-weight: 600; }}
/* รูปมือถือ */
.phone-img {{ width: 100%; max-width: 132px; aspect-ratio: 4 / 5; border-radius: 14px; background: #fff;
  border: 1px solid {LINE}; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
.phone-img img {{ width: 100%; height: 100%; object-fit: contain; }}
.phone-img svg {{ height: 72%; width: auto; }}
.phone-img.sm {{ max-width: none; aspect-ratio: 16 / 10; margin-bottom: .2rem; }}
.upgrade {{ border-left: 4px solid {SKY} !important; border-radius: 14px; padding: .8rem 1rem; margin: .4rem 0; }}
.upgrade b {{ color: {INDIGO}; }}
.reason-list {{ margin: .3rem 0 0 1.1rem; line-height: 1.7; }}
@media (max-width: 640px) {{
  .login-art {{ display: none; }}
  .pick-sub {{ margin-left: 0; }} .price {{ text-align: left; margin-top: .4rem; }}
}}
/* ---------- หน้าล็อกอิน: กรอบขาวทึบ ตัวอักษรดำ อ่านง่าย ---------- */
.st-key-login_card, [data-testid="stVerticalBlockBorderWrapper"]:has(> .st-key-login_card),
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-login_card) {{
  background: #fff !important; border-radius: 26px !important; border: 1px solid rgba(255,255,255,.9) !important;
  box-shadow: 0 30px 70px rgba(53,58,95,.28), 0 8px 20px rgba(53,58,95,.12) !important; }}
.st-key-login_card {{ padding: .6rem; }}
.st-key-login_card, .st-key-login_card p, .st-key-login_card label, .st-key-login_card h1, .st-key-login_card h2 {{ color: #111 !important; }}
.st-key-login_card input {{ background: #fff !important; color: #111 !important; border-radius: 10px !important; }}
.st-key-login_card [data-baseweb="input"], .st-key-login_card [data-baseweb="base-input"] {{ border-radius: 10px !important;
  border-color: #CDD4E2 !important; }}
.login-brand {{ display: flex; align-items: center; gap: .6rem; margin: .4rem 0 1.2rem; }}
.login-brand .logo {{ width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, {NAVY}, {SKY}); color: #fff; font-size: 1.25rem; box-shadow: 0 6px 16px rgba(53,58,95,.3); }}
.login-brand .name {{ font-weight: 700; color: #111; font-size: 1.05rem; line-height: 1.2; }}
.login-brand .tag {{ color: #5A6275; font-size: .82rem; }}
.login-title {{ font-size: 2rem; font-weight: 700; color: #111; margin: 0 0 .2rem; }}
.login-sub {{ color: #5A6275; margin: 0 0 1rem; }}
.login-art {{ height: 100%; min-height: 540px; border-radius: 20px; overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(53,58,95,.06); }}
.login-art svg {{ width: 100%; height: 100%; min-height: 540px; display: block; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
"""


SIDEBAR_CSS = f"""
<style>
/* ---------- แถบเมนูด้านข้าง (สีขาว) ---------- */
section[data-testid="stSidebar"] {{ background: #fff !important; border-right: 1px solid {LINE};
  box-shadow: 6px 0 28px rgba(53,58,95,.10); }}
section[data-testid="stSidebar"] > div {{ background: #fff !important; }}
/* ใช้ปุ่มย่อ/ขยายของเราเอง ซ่อนปุ่มของ Streamlit และไม่ให้ลากเปลี่ยนความกว้าง */
[data-testid="stSidebarCollapseButton"], [data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"],
[data-testid="stSidebarHeader"] {{ display: none !important; }}
[data-testid="stSidebarUserContent"] {{ padding: 1rem .9rem 1.2rem !important; }}
/* ดันปุ่มออกจากระบบไปล่างสุด */
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]:has(> .st-key-logout) {{ min-height: calc(100vh - 2.4rem); gap: .3rem; }}
.st-key-logout {{ margin-top: auto; padding-top: .8rem; border-top: 1px solid {LINE}; }}

/* ปุ่มย่อ/ขยาย (แสดงแค่ไอคอนลูกศร) */
.st-key-sb_toggle [data-testid="stMarkdownContainer"] {{ display: none !important; }}
.st-key-sb_toggle {{ display: flex; justify-content: flex-end; }}
.st-key-sb_toggle button {{ width: 34px !important; min-height: 34px; height: 34px; padding: 0 !important; border-radius: 50% !important;
  border: 1px solid {LINE} !important; background: #fff !important; color: {MUTED} !important; }}
.st-key-sb_toggle button:hover {{ color: {NAVY} !important; border-color: {SKY} !important; }}

/* โปรไฟล์: วงกลมไอคอน + อีเมล */
.profile {{ display: flex; align-items: center; gap: .7rem; padding: .3rem .2rem .9rem; border-bottom: 1px solid {LINE};
  margin-bottom: .4rem; }}
.profile .avatar {{ flex: none; width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: #fff; font-weight: 700; font-size: 1.15rem;
  background: linear-gradient(135deg, {NAVY}, {SKY}); box-shadow: 0 0 0 3px #fff, 0 0 0 5px {SKY}55, 0 6px 14px rgba(53,58,95,.3); }}
.profile .who {{ min-width: 0; }}
.profile .hi {{ font-size: .78rem; color: {MUTED}; line-height: 1.2; }}
.profile .mail {{ font-weight: 700; color: {INK}; font-size: .95rem; line-height: 1.25; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; max-width: 160px; }}

/* รายการเมนู: ไอคอนอยู่หน้า ชื่ออยู่หลัง */
section[data-testid="stSidebar"] [class*="st-key-nav_"] button {{
  justify-content: flex-start !important; gap: .65rem; border: 0 !important; background: transparent !important;
  color: {MUTED} !important; padding: .55rem .75rem !important; border-radius: 12px !important; min-height: 44px;
  transition: background .15s, color .15s; }}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button > div {{ justify-content: flex-start !important; }}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button p {{ font-size: .98rem; }}
section[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] button p {{ color: inherit !important; }}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button [data-testid="stIconMaterial"] {{ font-size: 1.3rem; }}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button:hover {{ background: {PAGE} !important; color: {NAVY} !important; }}

/* ปุ่มออกจากระบบ: ไอคอนประตูเปิด ชี้แล้วนูนขึ้นและเรืองแสงแดง */
.st-key-logout button {{ justify-content: flex-start !important; gap: .65rem; width: 100%; min-height: 46px;
  background: #fff !important; color: {DANGER} !important; border: 1px solid #F3C9C6 !important; border-radius: 12px !important;
  padding: .55rem .75rem !important; transition: transform .18s ease, box-shadow .18s ease, background .18s ease; }}
.st-key-logout button > div {{ justify-content: flex-start !important; }}
.st-key-logout button p {{ color: inherit !important; font-weight: 600; }}
.st-key-logout button [data-testid="stIconMaterial"] {{ font-size: 1.35rem; transition: transform .18s ease; }}
.st-key-logout button:hover, .st-key-logout button:focus-visible {{
  background: linear-gradient(135deg, #FF5B52 0%, {DANGER} 100%) !important; color: #fff !important;
  border-color: transparent !important; transform: translateY(-3px) scale(1.03);
  box-shadow: 0 0 0 4px rgba(255,91,82,.22), 0 10px 26px rgba(224,53,43,.55), 0 0 22px rgba(255,91,82,.65); }}
.st-key-logout button:hover [data-testid="stIconMaterial"] {{ transform: scale(1.18); }}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)


def sidebar_state_css(collapsed: bool, active: str) -> str:
    """CSS ที่เปลี่ยนตามสถานะ: ความกว้างแถบเมนู (กาง/หุบ) และเมนูที่เลือกอยู่"""
    width = 84 if collapsed else 268
    css = f"""
section[data-testid="stSidebar"] {{ width: {width}px !important; min-width: {width}px !important; max-width: {width}px !important;
  transform: none !important; visibility: visible !important; }}
section[data-testid="stSidebar"] > div:first-child {{ width: {width}px !important; }}
.st-key-nav_{active} button {{ background: linear-gradient(135deg, #E6ECFB, #F1F4FC) !important; color: {NAVY} !important;
  box-shadow: inset 3px 0 0 {NAVY}; }}
.st-key-nav_{active} button p {{ font-weight: 700; }}
"""
    if collapsed:  # หุบแล้วเห็นแค่ไอคอน
        css += f"""
section[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] {{ display: none !important; }}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button, .st-key-logout button {{ justify-content: center !important;
  padding: .55rem 0 !important; }}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button > div, .st-key-logout button > div {{ justify-content: center !important; }}
.st-key-sb_toggle {{ justify-content: center; }}
.profile {{ justify-content: center; padding-left: 0; padding-right: 0; }}
.profile .who {{ display: none; }}
[data-testid="stSidebarUserContent"] {{ padding-left: .7rem !important; padding-right: .7rem !important; }}
"""
    return f"<style>{css}</style>"


def profile_block(email: str) -> str:
    initial = esc((email or "?").strip()[:1].upper() or "?")
    return (f'<div class="profile" title="{esc(email)}"><div class="avatar" aria-hidden="true">{initial}</div>'
            f'<div class="who"><div class="hi">สวัสดี 👋</div><div class="mail">{esc(email)}</div></div></div>')


def _wave_path(a, b, amp, waves, close):
    """เส้นคลื่นจากจุด a ไป b แล้วปิดรูปตามมุม close"""
    import math
    (x0, y0), (x1, y1) = a, b
    n = waves * 4
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    pts = []
    for i in range(n + 1):
        t = i / n
        off = amp * math.sin(t * waves * 2 * math.pi) * math.sin(t * math.pi) ** 0.6
        pts.append((x0 + dx * t + nx * off, y0 + dy * t + ny * off))
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} "
    for i in range(len(pts) - 1):  # Catmull-Rom → Bezier ให้เส้นโค้งเนียน
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} "
    d += " ".join(f"L{x},{y}" for x, y in close) + " Z"
    return d


def login_art() -> str:
    """ภาพตกแต่งฝั่งขวาของหน้าล็อกอิน: กระดาษตัดซ้อนชั้นเป็นคลื่น ไล่สีตาม palette (วาดเอง ไม่ใช้รูปภายนอก)"""
    W, H = 400, 560
    layers = [  # (จุดเริ่ม, จุดจบ, ความสูงคลื่น, จำนวนลูกคลื่น, สี)
        ((250, 0), (W, 170), 22, 2, "#DCE6F8"),
        ((185, 0), (W, 265), 26, 2, "#B9CDF4"),
        ((120, 0), (W, 370), 30, 3, SKY),
        ((55, 0), (W, 470), 30, 3, "#7E97D4"),
        ((0, 60), (W, 560), 32, 3, "#5D72AE"),
        ((0, 190), (300, H), 28, 2, "#46507F"),
        ((0, 330), (190, H), 22, 2, NAVY),
    ]
    paths = []
    for a, b, amp, waves, color in layers:
        if b[0] == W:   # จบที่ขอบขวา: ปิดรูปผ่านมุมขวาล่าง ซ้ายล่าง (และซ้ายบนถ้าเริ่มที่ขอบบน)
            close = [(W, H), (0, H)] + ([(0, 0)] if a[1] == 0 else [])
        else:           # เริ่มขอบซ้าย จบขอบล่าง
            close = [(0, H)]
        paths.append(f'<path d="{_wave_path(a, b, amp, waves, close)}" fill="{color}" filter="url(#paper)"/>')
    svg = (f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="ภาพตกแต่งคลื่นกระดาษสีน้ำเงิน">'
           f'<defs><filter id="paper" x="-20%" y="-20%" width="140%" height="140%">'
           f'<feDropShadow dx="-5" dy="7" stdDeviation="7" flood-color="#1B1F3A" flood-opacity=".35"/></filter></defs>'
           f'<rect width="{W}" height="{H}" fill="#F5F3EE"/>{"".join(paths)}</svg>')
    return f'<div class="login-art">{svg}</div>'



def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def baht(x) -> str:
    return "—" if x is None or pd.isna(x) else f"฿{x:,.0f}"


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)


def pick_header(rank: int, name: str, sub: str) -> str:
    first = " first" if rank == 1 else ""
    return (f'<div class="pick-head"><span class="rank{first}">{rank}</span><p class="pick-name">{esc(name)}</p></div>'
            f'<p class="pick-sub">{esc(sub)}</p>')


def price_block(price, kind: str, highlight: bool) -> str:
    label = "ราคาไทย" if kind == "ราคาไทย" else "ราคาประมาณ (แปลงจากราคาอินเดีย)"
    cls = "price tag" if highlight else "price"
    return f'<div class="{cls}"><div class="amount">{baht(price)}</div><div class="kind">{esc(label)}</div></div>'


def meter(score, label: str = "ความเหมาะสม") -> str:
    v = 0 if score is None or pd.isna(score) else float(score)
    return (f'<div class="meter" role="img" aria-label="{esc(label)} {v:.0f} จาก 100"><span style="width:{v:.0f}%"></span></div>'
            f'<div class="meter-label">{esc(label)} {v:.0f}/100</div>')


def chips(items: list[str], kind: str = "") -> str:
    if not items:
        return ""
    return '<div class="chips">' + "".join(f'<span class="chip {kind}">{esc(i)}</span>' for i in items) + "</div>"


def html_block(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def pills(label: str, options: list[str], *, multi: bool, default, key: str, format_func=None):
    """ปุ่มเลือกแบบเม็ดยา (st.pills) ถ้า Streamlit รุ่นเก่าไม่มี ใช้ selectbox/multiselect แทน

    ค่าเริ่มต้นเก็บใน session_state[key] (ไม่ส่ง default ให้ widget ซ้ำ เพื่อไม่ให้ Streamlit เตือน)
    """
    fmt = format_func or (lambda x: x)
    st.session_state.setdefault(key, default)
    if hasattr(st, "pills"):
        value = st.pills(label, options, selection_mode="multi" if multi else "single", key=key, format_func=fmt)
        if not multi and value is None:  # กดยกเลิกการเลือก ใช้ค่าเริ่มต้นแทน
            return default
        return value or []
    if multi:
        return st.multiselect(label, options, key=key, format_func=fmt)
    return st.selectbox(label, options, key=key, format_func=fmt)


def compare_table(columns: list[str], rows: list[tuple[str, list[str], int | None]]) -> str:
    """ตาราง HTML เทียบรุ่น: rows = [(หัวข้อ, [ค่าแต่ละรุ่น], index ของค่าที่ดีที่สุดหรือ None)]"""
    head = "".join(f"<th scope='col'>{esc(c)}</th>" for c in columns)
    body = ""
    for label, values, best in rows:
        cells = "".join(f"<td class='best'>{esc(v)}</td>" if i == best else f"<td>{esc(v)}</td>" for i, v in enumerate(values))
        body += f"<tr><th scope='row'>{esc(label)}</th>{cells}</tr>"
    return f"<div class='cmp-wrap'><table class='cmp'><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def mini_card(name: str, price: str, price_note: str, specs: list[str], thai: bool, image: str = "") -> str:
    flag = "<span class='flag'>ขายในไทย</span>" if thai else ""
    return (f"<div class='mini'>{image}{flag}<div class='n'>{esc(name)}</div><div class='p'>{esc(price)}</div>"
            f"<div class='k'>{esc(price_note)}</div>{chips(specs)}</div>")


def grid(cards: list[str]) -> str:
    return "<div class='grid'>" + "".join(cards) + "</div>"


def _placeholder_svg(brand: str) -> str:
    """รูปสำรองเมื่อยังไม่มีรูปจริง: โครงมือถือเรียบๆ กับตัวย่อแบรนด์"""
    initials = esc((brand or "?")[:2].upper())
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 100' width='62%' role='img' aria-label='ยังไม่มีรูป {esc(brand)}'>"
            f"<rect x='18' y='6' width='44' height='88' rx='9' fill='#fff' stroke='{LINE}' stroke-width='2'/>"
            f"<rect x='34' y='11' width='12' height='3' rx='1.5' fill='{LINE}'/>"
            f"<text x='40' y='56' text-anchor='middle' font-size='14' font-weight='700' fill='{MUTED}' "
            f"font-family='Anuphan, sans-serif'>{initials}</text></svg>")


def phone_image(url: str, name: str, brand: str, small: bool = False) -> str:
    cls = "phone-img sm" if small else "phone-img"
    if isinstance(url, str) and url.startswith("http"):
        # ซ้อนพื้นหลัง 2 ชั้น: รูปจริงอยู่บน รูปสำรองอยู่ล่าง ถ้าลิงก์รูปเสีย ชั้นบนจะโปร่งใสและเห็นรูปสำรองแทน (ไม่ต้องใช้ JavaScript)
        fallback = "data:image/svg+xml;utf8," + urllib.parse.quote(_placeholder_svg(brand).replace("width='62%'", ""))
        safe_url = url.replace("'", "%27").replace('"', "%22").replace(")", "%29").replace("(", "%28")
        style = (f"background-image:url('{esc(safe_url)}'),url('{fallback}');background-size:contain,auto 70%;"
                 "background-position:center;background-repeat:no-repeat;background-color:#fff")
        return f"<div class='{cls}' role='img' aria-label='{esc(name)}' style=\"{style}\"></div>"
    return f"<div class='{cls}'>{_placeholder_svg(brand)}</div>"
