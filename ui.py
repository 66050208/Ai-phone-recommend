"""หน้าตาเว็บ: ธีม CSS และชิ้นส่วน UI ที่ใช้ซ้ำ

แนวคิด: "ป้ายราคาบนชั้นวางร้านมือถือ" พื้นเทาอลูมิเนียมสว่าง ตัวอักษรน้ำเงินเข้ม สีหลักน้ำเงินคราม
และใช้สีเหลืองป้ายราคาเพียงจุดเดียว คือราคาของรุ่นอันดับ 1 ฟอนต์ Anuphan (ไทย/อังกฤษในตระกูลเดียว)
"""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

INK = "#16203A"
MUTED = "#55607A"
LINE = "#DFE3EA"
SURFACE = "#FFFFFF"
PAGE = "#F3F5F8"
INDIGO = "#3A3FD9"
TAG = "#FFD23F"
GOOD = "#0E7A4F"
BAD = "#B4372F"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Anuphan:wght@400;500;600;700&display=swap');
html, body, .stApp, p, li, label, input, textarea, button, h1, h2, h3, h4, [class*="st-"] {{
  font-family: 'Anuphan', 'Noto Sans Thai', sans-serif;
}}
.stApp {{ background: {PAGE}; color: {INK}; }}
.block-container {{ max-width: 1120px; padding-top: 2rem; }}
h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {LINE}; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ background: {SURFACE}; border-color: {LINE} !important; border-radius: 14px; }}
.stButton > button[kind="primary"] {{ background: {INDIGO}; border-color: {INDIGO}; font-weight: 600; }}
.stButton > button:focus-visible, a:focus-visible {{ outline: 3px solid {TAG}; outline-offset: 2px; }}

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

.meter {{ height: 8px; background: #E8EBF1; border-radius: 99px; overflow: hidden; margin: .55rem 0 .2rem; }}
.meter > span {{ display: block; height: 100%; background: {INDIGO}; border-radius: 99px; }}
.meter-label {{ font-size: .85rem; color: {MUTED}; }}

.chips {{ display: flex; flex-wrap: wrap; gap: .35rem; margin: .3rem 0 .2rem; }}
.chip {{ font-size: .84rem; padding: .18rem .6rem; border-radius: 99px; border: 1px solid {LINE}; background: {PAGE}; color: {INK}; }}
.chip.good {{ border-color: #BFE3D2; background: #EEF8F3; color: {GOOD}; }}
.chip.bad {{ border-color: #F0C9C5; background: #FCF1F0; color: {BAD}; }}
.why {{ margin: .6rem 0 .3rem; font-size: 1rem; line-height: 1.6; max-width: 75ch; }}
.list-title {{ font-weight: 600; font-size: .92rem; margin-top: .5rem; }}
.summary {{ border-left: 4px solid {INDIGO}; background: {SURFACE}; padding: .9rem 1.1rem; border-radius: 0 12px 12px 0;
  margin: .4rem 0 1rem; line-height: 1.6; }}
.note {{ color: {MUTED}; font-size: .86rem; }}
@media (max-width: 640px) {{
  .pick-sub {{ margin-left: 0; }} .price {{ text-align: left; margin-top: .4rem; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


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
    """ปุ่มเลือกแบบเม็ดยา (st.pills) ถ้า Streamlit รุ่นเก่าไม่มี ใช้ selectbox/multiselect แทน"""
    fmt = format_func or (lambda x: x)
    if hasattr(st, "pills"):
        value = st.pills(label, options, selection_mode="multi" if multi else "single", default=default,
                         key=key, format_func=fmt)
        if not multi and value is None:  # ผู้ใช้กดยกเลิกการเลือก กลับไปค่าเริ่มต้น
            return default
        return value or []
    if multi:
        return st.multiselect(label, options, default=default, key=key, format_func=fmt)
    return st.selectbox(label, options, index=options.index(default), key=key, format_func=fmt)
