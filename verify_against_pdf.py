#!/usr/bin/env python3
"""Verification loop: re-parse the (possibly updated) price PDF and confirm every
unit is present & consistent in units.json AND attached in data.json."""
import json, os, re, subprocess, sys
from common import WORK

PDF = sys.argv[1] if len(sys.argv) > 1 else \
    "/Users/leetaesk/Downloads/2_ [주택목록] 2026년 1차 청년 매입임대주택 입주자 모집공고(홈페이지 공개용) (1).pdf"

NUM = re.compile(r"^[\d,]+$")
ROW = re.compile(r"^\s*(\d+)\s+(신규공급|재공급)\s+")
is_price = lambda s: s == "-" or bool(NUM.match(s))
won = lambda s: None if s == "-" else int(s.replace(",", ""))

def parse_pdf(pdf):
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    out = {}
    for line in text.splitlines():
        if not ROW.match(line):
            continue
        t = line.split()
        a = next(i for i, x in enumerate(t) if x.startswith("서울"))
        b = next(i for i in range(a, len(t)) if t[i].endswith(")"))
        prices = t[-8:]
        assert all(is_price(p) for p in prices)
        juso = " ".join(t[a:b+1])
        jibeon = re.search(r"\(([^)]*)\)\s*$", juso)
        jibeon = jibeon.group(1).strip() if jibeon else juso
        key = (t[1], t[2], " ".join(t[4:a]), jibeon, t[3])   # 구분,구,주택명,지번,호
        assert key not in out, f"DUP key in PDF: {key}"       # must be unique
        out[key] = {"면적": float(t[-9]), "prices": [won(p) for p in prices]}
    return out

def unit_key(u):
    return (u["구분"], u["구"], u["주택명"], u["지번"], u["호"])

def unit_prices(u):
    g = u["가격"]
    return [g["1순위_청년"]["보증금"], g["1순위_청년"]["임대료"],
            g["1순위_대학생"]["보증금"], g["1순위_대학생"]["임대료"],
            g["2~3순위_청년"]["보증금"], g["2~3순위_청년"]["임대료"],
            g["2~3순위_대학생"]["보증금"], g["2~3순위_대학생"]["임대료"]]

def main():
    pdf = parse_pdf(PDF)
    units = json.load(open(os.path.join(WORK, "units.json")))
    data = json.load(open(os.path.join(WORK, "data.json")))
    ujson = {unit_key(u): u for u in units}

    print(f"PDF rows: {len(pdf)}   units.json: {len(units)}   (dup keys in units.json: {len(units)-len(ujson)})")

    missing = [k for k in pdf if k not in ujson]         # in PDF, not in app
    extra   = [k for k in ujson if k not in pdf]         # in app, not in PDF
    price_mismatch, area_mismatch = [], []
    for k, pv in pdf.items():
        if k not in ujson:
            continue
        u = ujson[k]
        if unit_prices(u) != pv["prices"]:
            price_mismatch.append(k)
        if abs(u["전용면적"] - pv["면적"]) > 1e-9:
            area_mismatch.append(k)

    # every unit attached in data.json?
    attached = {unit_key(u) for b in data for u in b["units"]}
    not_attached = [k for k in ujson if k not in attached]
    total_attached = sum(len(b["units"]) for b in data)

    print(f"[A] PDF→app 누락(missing): {len(missing)}")
    for k in missing[:20]: print("     MISSING:", k)
    print(f"[B] app→PDF 잉여(extra):   {len(extra)}")
    for k in extra[:20]: print("     EXTRA:", k)
    print(f"[C] 가격 불일치: {len(price_mismatch)}")
    for k in price_mismatch[:20]: print("     PRICE:", k)
    print(f"[D] 면적 불일치: {len(area_mismatch)}")
    for k in area_mismatch[:20]: print("     AREA:", k)
    print(f"[E] data.json 미첨부 unit: {len(not_attached)}  (총 첨부 {total_attached}호)")
    for k in not_attached[:20]: print("     UNATTACHED:", k)

    ok = not (missing or extra or price_mismatch or area_mismatch or not_attached) and total_attached == len(pdf) == len(units)
    print("\n=== 결과:", "✅ 완전 일치 — 빠진 것 없음" if ok else "⚠️ 위 이슈 확인 필요", "===")

if __name__ == "__main__":
    main()
