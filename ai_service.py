"""ให้ Gemini อธิบายผลจัดอันดับ (ไม่ได้ให้ AI เลือกรุ่นหรือเดาสเปก/ราคาเอง)

- ส่งเฉพาะรุ่นที่ผ่านการจัดอันดับแล้ว พร้อมสเปกจริงและข้อดี/ข้อเสียที่คำนวณได้
- ตรวจคำตอบ: ชื่อรุ่นต้องอยู่ในรายการที่ส่งไป ถ้าไม่ตรงจะตัดทิ้ง
- ถ้าไม่มี key หรือเรียกไม่สำเร็จ ใช้คำอธิบายจากกฎแทน (แอปยังใช้งานได้)
"""
from __future__ import annotations

import json
import re
import time

import pandas as pd

from config import DEFAULT_GEMINI_MODEL, secret


def has_gemini_key() -> bool:
    return bool(secret("GEMINI_API_KEY"))


def _clean(v):
    if hasattr(v, "item"):  # numpy → python
        v = v.item()
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def compact(row: pd.Series, pros: list[str], cons: list[str]) -> dict:
    keys = ["name", "price_thb", "price_kind", "chipset", "ram_gb", "storage_gb", "camera_mp", "front_mp",
            "battery_mah", "charging_w", "display_in", "refresh_hz", "has_5g", "has_nfc", "os", "score",
            "fair_price_thb", "deal_label", "segment"]
    out = {k: _clean(row.get(k)) for k in keys}
    out["model"] = out.pop("name")
    out["ข้อดีจากการคำนวณ"] = pros
    out["ข้อเสียจากการคำนวณ"] = cons
    return out


SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "items": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "model": {"type": "STRING"},
            "why": {"type": "STRING"},
            "pros": {"type": "ARRAY", "items": {"type": "STRING"}},
            "cons": {"type": "ARRAY", "items": {"type": "STRING"}},
            "best_for": {"type": "STRING"},
        }, "required": ["model", "why", "pros", "cons"]}},
        "caution": {"type": "STRING"},
    },
    "required": ["summary", "items"],
}


def build_prompt(request: dict, picks: list[dict]) -> str:
    return f"""คุณเป็นผู้ช่วยแนะนำสมาร์ตโฟนสำหรับคนไทย ตอบภาษาไทย กระชับ เป็นกันเอง

ความต้องการของผู้ใช้:
{json.dumps(request, ensure_ascii=False, indent=2)}

รุ่นที่ระบบจัดอันดับแล้ว (เรียงจากเหมาะที่สุด) พร้อมสเปกจริงและข้อดี/ข้อเสียที่คำนวณได้:
{json.dumps(picks, ensure_ascii=False, indent=2)}

กติกา:
- อธิบายทุกรุ่นตามลำดับเดิม ห้ามเพิ่มรุ่นอื่น ห้ามเปลี่ยนลำดับ ใช้ชื่อ model ตรงตามที่ให้
- ใช้เฉพาะตัวเลขในข้อมูลข้างบน ห้ามเดาสเปกหรือราคาที่ไม่มี ถ้าช่องเป็น null ให้บอกว่าไม่มีข้อมูล
- why: ทำไมรุ่นนี้เหมาะกับความต้องการนี้ 1–2 ประโยค
- pros/cons: 2–3 ข้อ อิงจากข้อดี/ข้อเสียที่คำนวณได้ เขียนให้คนทั่วไปเข้าใจ
- best_for: เหมาะกับใครในประโยคเดียว
- summary: สรุปภาพรวม 1–2 ประโยค ว่าควรเลือกรุ่นไหนในกรณีใด
- ถ้า price_kind เป็น "ประมาณจากราคาอินเดีย" ต้องบอกว่าเป็นราคาประมาณ ไม่ใช่ราคาไทย
- fair_price_thb คือราคาที่ควรเป็นตามสเปกจากโมเดล Machine Learning, deal_label บอกว่าถูกหรือแพงกว่าสเปก, segment คือกลุ่มจาก K-Means ใช้ประกอบเหตุผลได้
- caution: ข้อจำกัดของข้อมูล เช่น ราคาอาจเปลี่ยน ควรเช็กกับร้านก่อนซื้อ"""


def _parse(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            raise ValueError("Gemini ตอบกลับในรูปแบบที่อ่านไม่ได้")
        return json.loads(m.group())


def validate(result: dict, picks: list[dict]) -> dict:
    """เก็บเฉพาะรุ่นที่อยู่ในรายการ เรียงตามลำดับเดิม รุ่นที่ AI ลืมอธิบายจะใช้ข้อความจากกฎแทน"""
    allowed = {p["model"].lower(): p for p in picks}
    by_model = {}
    for item in result.get("items", []) or []:
        name = str(item.get("model", "")).strip().lower()
        if name in allowed and name not in by_model:
            by_model[name] = item
    items, dropped = [], len(result.get("items", []) or []) - len(by_model)
    for p in picks:
        items.append(by_model.get(p["model"].lower()) or fallback_item(p))
    return {"summary": result.get("summary", ""), "items": items, "caution": result.get("caution", ""),
            "dropped": max(0, dropped), "source": "gemini"}


def fallback_item(p: dict) -> dict:
    return {"model": p["model"], "why": f"คะแนนรวม {p.get('score')} จากการเทียบสเปกในงบนี้",
            "pros": p["ข้อดีจากการคำนวณ"] or ["สเปกสมดุลในกลุ่มที่เทียบ"],
            "cons": p["ข้อเสียจากการคำนวณ"] or ["ไม่มีจุดด้อยชัดเจนในกลุ่มที่เทียบ"], "best_for": ""}


def fallback(picks: list[dict]) -> dict:
    return {"summary": "จัดอันดับจากสเปกและราคาด้วยสูตรคะแนน (ไม่ได้ใช้ AI อธิบาย)",
            "items": [fallback_item(p) for p in picks], "caution": "ราคาอาจเปลี่ยน ตรวจสอบกับร้านค้าก่อนซื้อ",
            "dropped": 0, "source": "rules"}


def explain(request: dict, picks: list[dict]) -> dict:
    if not picks:
        return fallback(picks)
    if not has_gemini_key():
        return fallback(picks)
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    last = None
    for delay in (0, 2, 5):
        if delay:
            time.sleep(delay)
        try:
            resp = client.models.generate_content(
                model=secret("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
                contents=build_prompt(request, picks),
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=SCHEMA,
                                                   temperature=0.2),
            )
            return validate(_parse(resp.text), picks)
        except Exception as err:
            last = err
            if not any(c in str(err) for c in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                break
    out = fallback(picks)
    out["error"] = f"เรียก Gemini ไม่สำเร็จ ใช้คำอธิบายจากกฎแทน ({str(last)[:200]})"
    return out
