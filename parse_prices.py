#!/usr/bin/env python3
"""Parse the SH price-list PDF -> units.json (849 units with prices).
Usage: parse_prices.py [모집공고.pdf]"""
import json, os, re, subprocess, sys
from common import WORK

PDF = sys.argv[1] if len(sys.argv) > 1 else \
    "/Users/leetaesk/Downloads/2_ [주택목록] 2026년 1차 청년 매입임대주택 입주자 모집공고(홈페이지 공개용).pdf"
OUT = os.path.join(WORK, "units.json")

NUM = re.compile(r"^[\d,]+$")
ROW = re.compile(r"^\s*(\d+)\s+(신규공급|재공급)\s+")

def is_price_tok(s):
    return s == "-" or bool(NUM.match(s))

def won(s):
    return None if s == "-" else int(s.replace(",", ""))

def parse_addr(addr):
    # "서울특별시 <구> <도로명...> (<지번>)"
    m = re.match(r"서울특별시\s+(\S+구)\s+(.*?)\s*\((.*)\)\s*$", addr)
    if m:
        return m.group(2).strip(), m.group(3).strip()  # 도로명, 지번
    return addr, ""

def main():
    text = subprocess.run(["pdftotext", "-layout", PDF, "-"],
                          capture_output=True, text=True).stdout
    units, errors = [], []
    for line in text.splitlines():
        if not ROW.match(line):
            continue
        t = line.split()
        try:
            yeonbeon, gubun, gu, ho = t[0], t[1], t[2], t[3]
            # address span: first "서울특별시" .. first token ending ")"
            a = next(i for i, x in enumerate(t) if x.startswith("서울"))
            b = next(i for i in range(a, len(t)) if t[i].endswith(")"))
            juhaengmyeong = " ".join(t[4:a])
            juso = " ".join(t[a:b + 1])
            # right side: last 8 numeric = prices, then 면적, 성별
            prices = t[-8:]
            assert all(is_price_tok(p) for p in prices), "price tokens not numeric"
            area = float(t[-9])
            seongbyeol = t[-10]
            juhaengtype = t[b + 1]
            structure = " ".join(t[b + 2:-10])
            doro, jibeon = parse_addr(juso)
            units.append({
                "연번": int(yeonbeon), "구분": gubun, "구": gu, "호": ho,
                "주택명": juhaengmyeong, "주소": juso, "도로명": doro, "지번": jibeon,
                "주택형": juhaengtype, "주택구조": structure, "성별": seongbyeol,
                "전용면적": area,
                "가격": {
                    "1순위_청년":   {"보증금": won(prices[0]), "임대료": won(prices[1])},
                    "1순위_대학생": {"보증금": won(prices[2]), "임대료": won(prices[3])},
                    "2~3순위_청년":   {"보증금": won(prices[4]), "임대료": won(prices[5])},
                    "2~3순위_대학생": {"보증금": won(prices[6]), "임대료": won(prices[7])},
                },
            })
        except Exception as e:
            errors.append((line.strip()[:80], str(e)))
    json.dump(units, open(OUT, "w"), ensure_ascii=False, indent=1)

    # ---- validation report ----
    print(f"parsed units: {len(units)}  (expected 849)")
    print(f"errors: {len(errors)}")
    for ln, err in errors[:10]:
        print("  ERR:", err, "|", ln)
    # distinct buildings by (구분, 구, 주택명, 지번)
    bldg = {(u["구분"], u["구"], u["주택명"], u["지번"]) for u in units}
    print(f"distinct buildings: {len(bldg)}")
    # sanity: structures, genders seen
    print("주택구조:", dict((s, sum(1 for u in units if u['주택구조']==s)) for s in sorted({u['주택구조'] for u in units})))
    print("성별:", sorted({u['성별'] for u in units}))
    print("가격 예시(연번1):", json.dumps(units[0]['가격'], ensure_ascii=False))

if __name__ == "__main__":
    main()
