"""ทดสอบโดยไม่ต้องใช้ API key: python tests/test_core.py  (หรือ python -m pytest tests -q)"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
for k in ("GEMINI_API_KEY", "YOUTUBE_API_KEY"):
    os.environ.pop(k, None)

import ai_service  # noqa: E402
import youtube_service  # noqa: E402
from dataset_service import apply_prices, chip_score, coverage, load_dataset, load_prices  # noqa: E402
from scoring_service import Request, filter_candidates, pros_cons, recommend, score, youtube_search_url  # noqa: E402
from thailand_filter import match_thai, model_key  # noqa: E402


def phones(rate=0.37, prices=None):
    return apply_prices(load_dataset(), prices if prices is not None else load_prices(), rate)


class Resp:
    def __init__(self, status, payload):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeHTTP:
    def __init__(self, responses):
        self.responses = list(responses)

    def get(self, url, params=None, timeout=None, **_):
        return self.responses.pop(0)


# ---------------------------------------------------------------------------
def test_model_key_normalises_variants():
    assert model_key("SAMSUNG Galaxy S26 5G", "samsung") == "galaxy s26"
    assert model_key("Samsung Galaxy S26 Ultra (12GB RAM + 512GB)", "samsung") == "galaxy s26 ultra"
    assert model_key("Galaxy S26+", "Samsung") == model_key("Samsung Galaxy S26 Plus", "samsung")
    assert model_key("Xiaomi Redmi Note 15 Pro 5G", "xiaomi") == "redmi note 15 pro"
    assert match_thai("oppo", "Oppo Find X9 5G") == ("OPPO", "Find X9")
    assert match_thai("oneplus", "OnePlus 17") is None  # ต้องไม่ไปจับคู่กับ "Xiaomi 17"
    assert match_thai("samsung", "Samsung Galaxy S26 FE") is None


def test_chip_score():
    assert chip_score("Snapdragon 8 Elite Gen 5") == 95 and chip_score("Snapdragon 8Elite") == 95
    assert chip_score("Apple A19 Pro") == 95 and chip_score("Bionic A18") == 90
    assert chip_score("Dimensity 7300") == 52 and chip_score("Octa Core Processor") is None


def test_dataset_loads_and_merges_variants():
    d = phones()
    assert d["name"].is_unique and len(d) > 500
    s26u = d[d["name"] == "Samsung Galaxy S26 Ultra"].iloc[0]
    assert s26u["variants"] == 3 and s26u["price_inr"] <= s26u["price_inr_max"] and s26u["in_thailand"]
    cov = coverage(d)
    assert cov["thai_matched"] >= 18 and cov["catalog_models"] == 42
    assert (d["price_kind"] == "ประมาณจากราคาอินเดีย").all()


def test_thai_price_overrides_estimate():
    p = pd.DataFrame({"brand": ["Samsung"], "model": ["Galaxy A57"], "price_thb": [13999.0], "updated": ["2026-10-01"],
                      "source": ["samsung.com/th"]})
    d = phones(prices=p)
    row = d[d["name"] == "Samsung Galaxy A57"].iloc[0]
    assert row["price_thb"] == 13999 and row["price_kind"] == "ราคาไทย"
    assert coverage(d)["thai_priced"] == 1
    assert phones(rate=0.5).loc[lambda x: x["name"] == "Samsung Galaxy S26", "price_thb"].iloc[0] > \
        phones(rate=0.3).loc[lambda x: x["name"] == "Samsung Galaxy S26", "price_thb"].iloc[0]


def test_filters():
    d = phones()
    req = Request(budget_min=10000, budget_max=20000, thailand_only=False, need_5g=True, need_nfc=True, min_storage=256)
    c = filter_candidates(d, req)
    assert len(c) > 0 and c["price_thb"].between(10000, 20000).all() and c["has_5g"].all() and c["has_nfc"].all()
    assert filter_candidates(d, Request(budget_max=99999, thailand_only=True))["in_thailand"].all()
    assert filter_candidates(d, Request(budget_max=99999, brands=["Apple"], thailand_only=False))["brand"].eq("Apple").all()


def test_scoring_follows_use_case():
    d = phones()
    game, n = recommend(d, Request(budget_max=25000, use_case="เล่นเกม", thailand_only=False))
    assert n > 50 and len(game) == 5 and game["score"].is_monotonic_decreasing
    pool = score(filter_candidates(d, Request(budget_max=25000, thailand_only=False)), Request(budget_max=25000, thailand_only=False))
    assert game["perf_score"].mean() > pool["perf_score"].mean()
    cam, _ = recommend(d, Request(budget_max=25000, use_case="ถ่ายรูป/วิดีโอ", thailand_only=False))
    assert cam["camera_mp"].mean() > pool["camera_mp"].mean()
    bat, _ = recommend(d, Request(budget_max=25000, use_case="แบตอึด/เดินทาง", thailand_only=False))
    assert bat["battery_mah"].mean() > pool["battery_mah"].mean()


def test_missing_data_is_penalised_and_reported():
    d = filter_candidates(phones(), Request(budget_max=25000, thailand_only=False)).copy()
    req = Request(budget_max=25000, use_case="เล่นเกม", thailand_only=False)
    top = score(d, req).iloc[0]["name"]
    full = score(d, req).set_index("name").loc[top, "score"]
    d.loc[d["name"] == top, ["perf_score", "refresh_hz"]] = None
    part = score(d, req).set_index("name").loc[top]
    assert part["score"] < full
    assert any("ไม่มีข้อมูล" in c for c in pros_cons(part, req)[1])


def test_ai_validate_and_fallback():
    picks = [{"model": "OPPO Find X9s", "score": 90, "ข้อดีจากการคำนวณ": ["a"], "ข้อเสียจากการคำนวณ": []},
             {"model": "OPPO A6", "score": 70, "ข้อดีจากการคำนวณ": [], "ข้อเสียจากการคำนวณ": ["b"]}]
    out = ai_service.validate({"summary": "s", "items": [
        {"model": "iPhone 99 Ultra", "why": "fake", "pros": [], "cons": []},
        {"model": "oppo find x9s", "why": "ok", "pros": ["x"], "cons": ["y"]}]}, picks)
    assert [i["model"].lower() for i in out["items"]] == ["oppo find x9s", "oppo a6"] and out["dropped"] == 1
    assert ai_service.explain({}, picks)["source"] == "rules"
    d = phones()
    req = Request(budget_max=20000)
    top, _ = recommend(d, req)
    row = ai_service.compact(top.iloc[0], *pros_cons(top.iloc[0], req))
    json.dumps(row, ensure_ascii=False)  # ต้องแปลงเป็น JSON ได้ (ไม่มีชนิด numpy)


def test_youtube():
    assert youtube_search_url("Samsung Galaxy S26").startswith("https://www.youtube.com/results?search_query=")
    assert youtube_service.review_videos("x") == []
    os.environ["YOUTUBE_API_KEY"] = "k"
    http = FakeHTTP([Resp(200, {"items": [{"id": {"videoId": "abc"}, "snippet": {"title": "รีวิว &amp; ทดสอบ",
                                                                                   "channelTitle": "ช่อง"}}]})])
    v = youtube_service.review_videos("Samsung Galaxy S26", session=http)
    assert v[0]["url"].endswith("abc") and v[0]["title"] == "รีวิว & ทดสอบ"
    assert youtube_service.review_videos("x", session=FakeHTTP([Resp(500, {})])) == []
    os.environ.pop("YOUTUBE_API_KEY")


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception:
                failed += 1
                import traceback
                traceback.print_exc()
                print("FAIL", name)
    sys.exit(1 if failed else 0)
