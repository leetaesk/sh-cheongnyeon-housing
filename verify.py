#!/usr/bin/env python3
"""QA: verify every referenced media path exists, geocode coords are sane,
and prices are internally consistent."""
import json, os
from common import WORK
D = json.load(open(os.path.join(WORK, "data.json")))
cache = json.load(open(os.path.join(WORK, "geocode_cache.json")))

# 1) media path existence
missing = []
total_paths = 0
for b in D:
    for k in ("images", "domyeon_pdfs", "sajin_pdfs", "combined_pdfs", "others"):
        for p in b["media"][k]:
            total_paths += 1
            if not os.path.exists(os.path.join(WORK, p)):
                missing.append(p)
print(f"[1] media paths: {total_paths} referenced, MISSING={len(missing)}")
for m in missing[:20]:
    print("    MISSING:", m)

# 2) geocode sanity: within Seoul bbox + display_name contains 구
SEOUL = (37.40, 37.72, 126.73, 127.20)  # lat_min,lat_max,lng_min,lng_max
geo_out, gu_mismatch = [], []
for b in D:
    if b["lat"] is None:
        geo_out.append(("NULL", b)); continue
    if not (SEOUL[0] <= b["lat"] <= SEOUL[1] and SEOUL[2] <= b["lng"] <= SEOUL[3]):
        geo_out.append(("OOB", b))
    disp = ""
    for v in cache.values():
        if v and abs(v["lat"] - b["lat"]) < 1e-6 and abs(v["lng"] - b["lng"]) < 1e-6:
            disp = v.get("display", ""); break
    if disp and b["구"] not in disp:
        gu_mismatch.append((b, disp))
print(f"[2] geocode: {sum(1 for b in D if b['lat'])} located, out-of-Seoul/null={len(geo_out)}, 구-name mismatch={len(gu_mismatch)}")
for tag, b in geo_out[:20]:
    print(f"    {tag}: {b['구']} {b['주택명']} ({b['lat']},{b['lng']})")
print("    -- 구 not in geocode display (검토 필요, 지오코더가 인접지역으로 잡았을 수 있음):")
for b, disp in gu_mismatch[:30]:
    print(f"      {b['구']} {b['주택명']} | {b['도로명']} -> {disp[:55]}")

# 3) price consistency: every unit has 1순위_청년 보증금/임대료 (핵심 가격)
bad_price = [f"{b['구']} {b['주택명']} {u['호']}" for b in D for u in b["units"]
             if u["가격"]["1순위_청년"]["보증금"] is None or u["가격"]["1순위_청년"]["임대료"] is None]
print(f"[3] units missing 청년 1순위 price: {len(bad_price)} / {sum(b['호수'] for b in D)}")
for x in bad_price[:10]:
    print("    ", x)

print("\n=== 요약 ===")
print(f"건물 {len(D)} · 호 {sum(b['호수'] for b in D)} · 이미지경로 {total_paths} · 지오코딩 {sum(1 for b in D if b['lat'])}/{len(D)}")
print(f"이슈: 이미지누락 {len(missing)}, 지오OOB/null {len(geo_out)}, 구불일치(검토) {len(gu_mismatch)}, 가격누락 {len(bad_price)}")
