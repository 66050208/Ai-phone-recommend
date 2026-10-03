"""ผู้ช่วย AI: (1) แปลงคำขอภาษาพูดเป็นตัวกรอง  (2) แชทถามต่อจากผลแนะนำ (Agent + Tools แบบ Lab 7)

ทั้งสองส่วนทำงานได้แม้ไม่มี Gemini key:
- แปลงคำขอ: มีตัวแปลงด้วยกฎ (regex) เป็นค่าสำรอง
- แชท: ต้องใช้ Gemini ถ้าไม่มี key แอปจะแจ้งให้ตั้งค่า
ตัวเลขทุกตัวในคำตอบแชทมาจาก Tool ที่คำนวณจากข้อมูลจริง ไม่ให้ AI เดา
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, replace

import pandas as pd

from config import DEFAULT_GEMINI_MODEL, secret
from insight_service import budget_upgrade, why_not
from scoring_service import DIMENSIONS, USE_CASES, Request, filter_candidates, score

PRIORITY_OPTIONS = ["ประสิทธิภาพ", "กล้อง", "กล้องหน้า", "แบตเตอรี่", "ชาร์จเร็ว", "จอลื่น", "ความจุ", "ความคุ้มค่า"]
BRAND_ALIASES = {"apple": "Apple", "ไอโฟน": "Apple", "iphone": "Apple", "แอปเปิ้ล": "Apple", "samsung": "Samsung",
                 "ซัมซุง": "Samsung", "galaxy": "Samsung", "oppo": "OPPO", "ออปโป้": "OPPO", "vivo": "vivo",
                 "วีโว่": "vivo", "xiaomi": "Xiaomi", "เสี่ยวหมี่": "Xiaomi", "redmi": "Xiaomi", "เรดมี": "Xiaomi",
                 "poco": "POCO", "realme": "realme", "เรียลมี": "realme", "honor": "HONOR", "ออนเนอร์": "HONOR",
                 "oneplus": "OnePlus", "google": "Google", "pixel": "Google", "infinix": "Infinix", "tecno": "TECNO",
                 "motorola": "Motorola", "nothing": "Nothing", "huawei": "HUAWEI", "หัวเว่ย": "HUAWEI"}
USE_CASE_WORDS = [
    ("เล่นเกม", r"เกม|rov|pubg|genshin|free ?fire|ฟีฟาย|valorant|game"),
    ("เซลฟี่/โซเชียล", r"เซลฟี่|selfie|tiktok|ติ๊กต็อก|ไลฟ์|live|โซเชียล"),
    ("ถ่ายรูป/วิดีโอ", r"ถ่ายรูป|ถ่ายภาพ|กล้อง|วิดีโอ|วีดีโอ|ถ่ายคลิป|camera"),
    ("แบตอึด/เดินทาง", r"แบตอึด|แบตทน|เดินทาง|ใช้ทั้งวัน|แบตเยอะ"),
    ("ทำงาน", r"ทำงาน|งานเอกสาร|ประชุม|อีเมล|office"),
    ("ผู้สูงอายุ/ใช้ง่าย", r"ผู้สูงอายุ|พ่อ|แม่|ยาย|ตา |ปู่|ย่า|คนแก่|ใช้ง่าย"),
    ("ใช้งานทั่วไป/เรียน", r"เรียน|นักเรียน|นักศึกษา|ทั่วไป"),
]
PRIORITY_WORDS = [("แบตเตอรี่", r"แบต"), ("ชาร์จเร็ว", r"ชาร์จเร็ว|ชาร์จไว"), ("จอลื่น", r"จอลื่น|\d{3} ?hz|จอดี"),
                  ("กล้องหน้า", r"กล้องหน้า|เซลฟี่"), ("กล้อง", r"กล้อง|ถ่ายรูป"), ("ความจุ", r"ความจุ|เมมเยอะ|เก็บรูปเยอะ"),
                  ("ประสิทธิภาพ", r"แรง|ลื่น|เร็ว"), ("ความคุ้มค่า", r"คุ้ม|ถูก|ประหยัด")]


# ---------------------------------------------------------------------------
# 1) แปลงคำขอภาษาพูด → ตัวกรอง
# ---------------------------------------------------------------------------
@dataclass
class Parsed:
    budget_min: int = 0
    budget_max: int | None = None
    use_case: str | None = None
    priorities: list[str] | None = None
    brands: list[str] | None = None
    min_storage: int = 0
    need_5g: bool = False
    need_nfc: bool = False
    source: str = "rules"


def _money_values(text: str) -> list[int]:
    """'1.5 หมื่น' → 15000, '15k' → 15000, '12,990' → 12990, 'หมื่นนึง' → 10000"""
    t = text.lower().replace(",", "")
    vals = []
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(หมื่น|พัน|k|บาท)?", t):
        v = float(num)
        if unit == "หมื่น":
            v *= 10000
        elif unit in ("พัน", "k"):
            v *= 1000
        if 1000 <= v <= 200000 and not re.search(rf"{re.escape(num)}\s*(gb|tb|hz|mp|mah|w\b)", t):
            vals.append(int(v))
    if not vals and re.search(r"หมื่น(นึง|หนึ่ง)?", t):
        vals.append(10000)
    return vals


def parse_rules(text: str, brands_available: list[str] | None = None) -> Parsed:
    t = (text or "").lower()
    p = Parsed()
    money = _money_values(t)
    if len(money) >= 2 and re.search(r"[-–]|ถึง|ระหว่าง", t):
        p.budget_min, p.budget_max = min(money[:2]), max(money[:2])
    elif money:
        p.budget_max = money[0]
    p.use_case = next((uc for uc, pat in USE_CASE_WORDS if re.search(pat, t)), None)
    p.priorities = [name for name, pat in PRIORITY_WORDS if re.search(pat, t)] or None
    found = [b for alias, b in BRAND_ALIASES.items() if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", t)]
    if brands_available is not None:
        found = [b for b in found if b in brands_available]
    p.brands = sorted(set(found)) or None
    storage = re.search(r"(128|256|512|1024)\s*(gb|กิ๊ก)|1\s*tb", t)
    if storage:
        p.min_storage = 1024 if "tb" in storage.group(0) else int(storage.group(1))
    p.need_5g = bool(re.search(r"5\s*g\b|5จี", t))
    p.need_nfc = "nfc" in t
    return p


PARSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "budget_min": {"type": "INTEGER", "description": "งบขั้นต่ำ (บาท) ถ้าไม่ระบุให้เป็น 0"},
        "budget_max": {"type": "INTEGER", "description": "งบสูงสุด (บาท) ถ้าไม่ระบุให้เป็น 0", "nullable": True},
        "use_case": {"type": "STRING", "enum": list(USE_CASES), "nullable": True},
        "priorities": {"type": "ARRAY", "items": {"type": "STRING", "enum": PRIORITY_OPTIONS}},
        "brands": {"type": "ARRAY", "items": {"type": "STRING"}},
        "min_storage": {"type": "INTEGER", "description": "ความจุขั้นต่ำ GB: 0, 128, 256, 512"},
        "need_5g": {"type": "BOOLEAN"},
        "need_nfc": {"type": "BOOLEAN"},
    },
}


def parse_request(text: str, brands_available: list[str]) -> Parsed:
    """ใช้ Gemini ถ้ามี key (เข้าใจภาษาพูดดีกว่า) ไม่งั้นหรือถ้าล้มเหลวใช้กฎ ผลลัพธ์ถูกตรวจให้อยู่ในตัวเลือกที่มีจริง"""
    rules = parse_rules(text, brands_available)
    if not secret("GEMINI_API_KEY") or not text.strip():
        return rules
    try:
        from google.genai import types
        prompt = (f"แปลงคำขอซื้อมือถือของคนไทยต่อไปนี้เป็นตัวกรอง แบรนด์ที่มี: {', '.join(brands_available)}\n"
                  f"'หมื่นนึง' = 10000, '1.5 หมื่น' = 15000 ถ้าไม่พูดถึงเรื่องใดให้เว้นว่าง\n\nคำขอ: {text}")
        resp = _generate(contents=prompt, config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=PARSE_SCHEMA, temperature=0))
        data = json.loads(resp.text)
    except Exception:
        return rules
    brands = [b for b in data.get("brands") or [] if b in brands_available]
    return Parsed(
        budget_min=max(0, int(data.get("budget_min") or 0)),
        budget_max=int(data["budget_max"]) if data.get("budget_max") else rules.budget_max,
        use_case=data.get("use_case") if data.get("use_case") in USE_CASES else rules.use_case,
        priorities=[x for x in data.get("priorities") or [] if x in PRIORITY_OPTIONS] or rules.priorities,
        brands=brands or rules.brands,
        min_storage=int(data.get("min_storage") or 0) if int(data.get("min_storage") or 0) in (0, 128, 256, 512) else 0,
        need_5g=bool(data.get("need_5g")), need_nfc=bool(data.get("need_nfc")), source="gemini")


# ---------------------------------------------------------------------------
# 2) แชทถามต่อจากผลแนะนำ
# ---------------------------------------------------------------------------
def _generate(**kwargs):
    from google import genai
    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    last = None
    for delay in (0, 2, 5):
        if delay:
            time.sleep(delay)
        try:
            return client.models.generate_content(model=secret("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL, **kwargs)
        except Exception as err:
            last = err
            if not any(c in str(err) for c in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                raise
    raise last


def _num(v, nd=0):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if hasattr(v, "item"):
        v = v.item()
    return round(float(v), nd) if isinstance(v, (int, float)) and not isinstance(v, bool) else v


def _phone_dict(r: pd.Series) -> dict:
    keys = ["name", "price_thb", "price_kind", "chipset", "ram_gb", "storage_gb", "camera_mp", "front_mp",
            "battery_mah", "charging_w", "display_in", "refresh_hz", "has_5g", "has_nfc", "os", "in_thailand",
            "fair_price_thb", "deal_label", "segment"]
    out = {k: _num(r.get(k)) for k in keys}
    if "score" in r and pd.notna(r.get("score")):
        out["คะแนนความเหมาะสม"] = _num(r["score"], 1)
        out["คะแนนรายด้าน"] = {DIMENSIONS[d][2]: _num(r.get(f"s_{d}")) for d in DIMENSIONS}
    return out


class ChatTools:
    """เครื่องมือที่ AI เรียกใช้ได้ คำนวณจากข้อมูลจริงทั้งหมด"""

    def __init__(self, phones: pd.DataFrame, req: Request):
        self.phones, self.req = phones, req
        self.ranked = score(filter_candidates(phones, req), req)

    def _find(self, name: str):
        q = (name or "").lower().strip()
        exact = self.phones[self.phones["name"].str.lower() == q]
        hit = exact if len(exact) else self.phones[self.phones["name"].str.lower().str.contains(q, regex=False)]
        return None if hit.empty else hit.iloc[0]

    def get_ranking(self, n: int = 5) -> dict:
        n = max(1, min(int(n), 10))
        return {"เงื่อนไข": self.req.describe(), "จำนวนรุ่นที่ผ่านตัวกรอง": len(self.ranked),
                "อันดับ": [{"อันดับ": i + 1, **_phone_dict(r)} for i, (_, r) in enumerate(self.ranked.head(n).iterrows())]}

    def get_phone(self, name: str) -> dict:
        r = self._find(name)
        if r is None:
            return {"error": f"ไม่พบรุ่น {name}"}
        in_rank = self.ranked[self.ranked["name"] == r["name"]]
        return _phone_dict(in_rank.iloc[0] if len(in_rank) else r)

    def compare(self, names: list[str]) -> dict:
        return {"รุ่น": [self.get_phone(n) for n in names[:4]]}

    def why_not(self, name: str) -> dict:
        r = self._find(name)
        return why_not(self.phones, self.req, r["name"] if r is not None else name)

    def budget_upgrade(self) -> dict:
        ups = budget_upgrade(self.phones, self.req)
        return {"ข้อเสนอ": ups} if ups else {"ข้อเสนอ": [], "หมายเหตุ": "เพิ่มงบ 2,000–5,000 บาทแล้วไม่ได้รุ่นที่ดีขึ้นชัดเจน"}

    def search(self, query: str = "", max_price: float = 0) -> dict:
        d = self.ranked if len(self.ranked) else self.phones
        d = self.phones if query else d
        if query:
            d = d[d["name"].str.contains(query, case=False, regex=False)]
        if max_price:
            d = d[d["price_thb"] <= max_price]
        return {"พบ": len(d), "รายการ": [_phone_dict(r) for _, r in d.head(8).iterrows()]}

    def run(self, name: str, args: dict) -> dict:
        fn = {"get_ranking": self.get_ranking, "get_phone": self.get_phone, "compare": self.compare,
              "why_not": self.why_not, "budget_upgrade": self.budget_upgrade, "search": self.search}.get(name)
        if fn is None:
            return {"error": f"ไม่รู้จัก tool {name}"}
        try:
            return fn(**(args or {}))
        except Exception as err:
            return {"error": str(err)}


TOOL_DECLARATIONS = [
    {"name": "get_ranking", "description": "อันดับมือถือที่เหมาะที่สุดตามเงื่อนไขปัจจุบันของผู้ใช้ พร้อมสเปกและคะแนน",
     "parameters": {"type": "OBJECT", "properties": {"n": {"type": "INTEGER", "description": "จำนวนอันดับ (1–10)"}}}},
    {"name": "get_phone", "description": "สเปก ราคา และคะแนนของมือถือรุ่นหนึ่ง",
     "parameters": {"type": "OBJECT", "properties": {"name": {"type": "STRING"}}, "required": ["name"]}},
    {"name": "compare", "description": "เทียบสเปกและคะแนนของมือถือ 2–4 รุ่น",
     "parameters": {"type": "OBJECT", "properties": {"names": {"type": "ARRAY", "items": {"type": "STRING"}}},
                    "required": ["names"]}},
    {"name": "why_not", "description": "อธิบายว่าทำไมรุ่นที่ผู้ใช้ถามไม่ติดอันดับ (ตกตัวกรองอะไร หรือแพ้ด้านไหน)",
     "parameters": {"type": "OBJECT", "properties": {"name": {"type": "STRING"}}, "required": ["name"]}},
    {"name": "budget_upgrade", "description": "ถ้าเพิ่มงบ 2,000–5,000 บาท จะได้รุ่นที่ดีขึ้นแค่ไหน",
     "parameters": {"type": "OBJECT", "properties": {}}},
    {"name": "search", "description": "ค้นหามือถือตามชื่อ หรือราคาไม่เกินที่กำหนด",
     "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "max_price": {"type": "NUMBER"}}}},
]

SYSTEM_CHAT = """คุณคือผู้ช่วยเลือกซื้อมือถือ ตอบภาษาไทย สั้น กระชับ เป็นกันเอง
- ตัวเลขทุกตัว (ราคา สเปก คะแนน) ต้องมาจากผลของ tool เท่านั้น ห้ามเดา ถ้าไม่มีข้อมูลให้บอกตรงๆ
- ถ้า price_kind เป็นราคาประมาณ ให้บอกว่าเป็นราคาประมาณ ควรเช็กราคาไทยกับร้าน
- ตอบเฉพาะเรื่องมือถือและการเลือกซื้อ คำถามนอกเรื่องให้ปฏิเสธสุภาพ
- ปิดท้ายด้วยคำแนะนำ 1 ข้อเมื่อเหมาะสม"""


def chat(question: str, history: list[dict], tools: ChatTools, max_steps: int = 5) -> dict:
    """คืน {"answer", "trace"} ; history = [{"role": "user"|"assistant", "content": str}]"""
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_CHAT, temperature=0.2,
        tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents = [types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part.from_text(text=m["content"])])
                for m in history[-10:]]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))
    trace, seen = [], set()
    for _ in range(max_steps):
        resp = _generate(contents=contents, config=config)
        calls = resp.function_calls or []
        if not calls:
            return {"answer": (resp.text or "").strip() or "ขออภัย ตอบไม่ได้ ลองถามใหม่อีกครั้ง", "trace": trace}
        contents.append(resp.candidates[0].content)
        parts = []
        for call in calls:
            args = dict(call.args or {})
            sig = (call.name, json.dumps(args, sort_keys=True, ensure_ascii=False, default=str))
            result = {"error": "เรียกซ้ำ ใช้ผลก่อนหน้าได้เลย"} if sig in seen else tools.run(call.name, args)
            seen.add(sig)
            trace.append({"tool": call.name, "args": args})
            parts.append(types.Part.from_function_response(name=call.name, response={"result": json.loads(
                json.dumps(result, ensure_ascii=False, default=str))}))
        contents.append(types.Content(role="user", parts=parts))
    return {"answer": "คำถามนี้ซับซ้อนเกินไป ลองถามทีละเรื่อง", "trace": trace}


def apply_parsed(req: Request, p: Parsed) -> Request:
    """รวมผลแปลงเข้ากับตัวกรองเดิม (ช่องที่แปลงไม่ได้คงค่าเดิมไว้)"""
    return replace(req, budget_min=p.budget_min if p.budget_max else req.budget_min,
                   budget_max=p.budget_max or req.budget_max, use_case=p.use_case or req.use_case,
                   priorities=p.priorities if p.priorities is not None else req.priorities,
                   brands=p.brands if p.brands is not None else req.brands, min_storage=p.min_storage or req.min_storage,
                   need_5g=p.need_5g or req.need_5g, need_nfc=p.need_nfc or req.need_nfc)
