#!/usr/bin/env python3
"""Merge units.json (prices) + media.json (files) -> data.json (buildings).
One card per location (구분, 구, 지번). All price-units at that location AND all
media folders at that location are combined into the single card.
Folder→location resolution falls back 지번 → 주택명 → 도로명."""
import json, os, re
from collections import defaultdict
from common import WORK, natkey

units = json.load(open(os.path.join(WORK, "units.json")))
media = json.load(open(os.path.join(WORK, "media.json")))

def norm_jibeon(s):
    s = re.sub(r"외\s*\d*\s*필지", "", s)
    s = re.sub(r"\s+", "", s)
    return re.sub(r"외$", "", s)

def norm_name(s):
    return re.sub(r"\s+", "", s).replace("(", "").replace(")", "")

def norm_doro(s):
    return re.sub(r"\s+", "", s)

# --- group units by location ---
loc_units = defaultdict(list)
for u in units:
    loc_units[(u["구분"], u["구"], norm_jibeon(u["지번"]))].append(u)

name_to_loc, doro_to_loc = {}, {}
for lk, us in loc_units.items():
    for u in us:
        if u["주택명"] != "-":
            name_to_loc.setdefault((u["구분"], u["구"], norm_name(u["주택명"])), lk)
        doro_to_loc.setdefault((u["구분"], u["구"], norm_doro(u["도로명"])), lk)

MEDIA_KEYS = ("images", "domyeon_pdfs", "sajin_pdfs", "combined_pdfs", "others")

def new_agg():
    d = {k: [] for k in MEDIA_KEYS}
    d.update(folders=[], 주택명=[], 도로명="")
    return d

loc_media = defaultdict(new_agg)
unmatched_media = []

for mb in media:
    gubun, gu = mb["구분"], mb["구"]
    lk = None
    if (gubun, gu, norm_jibeon(mb["지번"])) in loc_units:
        lk = (gubun, gu, norm_jibeon(mb["지번"]))
    elif (gubun, gu, norm_name(mb["주택명"])) in name_to_loc:
        lk = name_to_loc[(gubun, gu, norm_name(mb["주택명"]))]
    elif (gubun, gu, norm_doro(mb["도로명"])) in doro_to_loc:
        lk = doro_to_loc[(gubun, gu, norm_doro(mb["도로명"]))]
    if lk is None:
        unmatched_media.append(mb); continue
    agg = loc_media[lk]
    for k in MEDIA_KEYS:
        agg[k] += mb[k]
    agg["folders"].append(mb["folder"])
    if mb["주택명"]:
        agg["주택명"].append(mb["주택명"])
    agg["도로명"] = agg["도로명"] or mb["도로명"]

# --- build one card per location ---
buildings = []
for lk in sorted(loc_units, key=lambda k: (k[0], k[1], k[2])):
    gubun, gu, _ = lk
    us = sorted(loc_units[lk], key=lambda u: (u["주택명"], u["호"]))
    agg = loc_media.get(lk, new_agg())
    names = sorted({u["주택명"] for u in us if u["주택명"] != "-"})
    folder_names = sorted(set(agg["주택명"])) or names
    doro = us[0]["도로명"]  # PDF 도로명 is clean (folder 도로명 can include 동 lists)
    jibeon = us[0]["지번"]
    title = (folder_names[0] if folder_names else "") or f"{gu} {doro}"
    media_out = {}
    for k in MEDIA_KEYS:
        seen, uniq = set(), []
        for p in agg[k]:
            if p not in seen:
                seen.add(p); uniq.append(p)
        media_out[k] = sorted(uniq, key=natkey) if k == "images" else sorted(uniq)
    buildings.append({
        "id": len(buildings) + 1, "구분": gubun, "구": gu,
        "주택명": title, "주택명들": names,
        "도로명": doro, "지번": jibeon,
        "주소": f"서울특별시 {gu} {doro} ({jibeon})",
        "geocode_addr": f"서울특별시 {gu} {doro}",
        "주택구조들": sorted({u["주택구조"] for u in us}),
        "면적_min": min(u["전용면적"] for u in us),
        "면적_max": max(u["전용면적"] for u in us),
        "호수": len(us), "folders": agg["folders"],
        "lat": None, "lng": None,
        "media": media_out, "units": us,
    })

json.dump(buildings, open(os.path.join(WORK, "data.json"), "w"), ensure_ascii=False, indent=1)

# ---- report ----
print(f"building cards: {len(buildings)}   (locations)   media folders: {len(media)}")
print(f"  units attached: {sum(b['호수'] for b in buildings)} / {len(units)}")
print(f"  cards with images: {sum(1 for b in buildings if b['media']['images'])}")
print(f"  cards with any 도면/사진 pdf: {sum(1 for b in buildings if b['media']['domyeon_pdfs'] or b['media']['sajin_pdfs'] or b['media']['combined_pdfs'])}")
print(f"  cards with NO media at all: {sum(1 for b in buildings if not any(b['media'][k] for k in MEDIA_KEYS))}")
print(f"  multi-folder cards: {sum(1 for b in buildings if len(b['folders'])>1)}")
print(f"  total images: {sum(len(b['media']['images']) for b in buildings)}")
print(f"  UNMATCHED media folders: {len(unmatched_media)}")
for mb in unmatched_media:
    print(f"     [{mb['구분']}] {mb['구']} | {mb['주택명']} | 지번:{mb['지번']}")
