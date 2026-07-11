#!/usr/bin/env python3
"""Walk the region folders -> media.json (per-building files, classified)."""
import json, os, re
from common import WORK, natkey

OUT = os.path.join(WORK, "media.json")
# Only browser-renderable formats are cataloged as gallery images.
# (All photos are .webp after to_webp.sh; the rest stay for robustness.)
IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
# Raw/non-web formats are skipped: they'd show as broken tiles in the gallery.
RAW_IMG_EXT = {".heic", ".heif", ".tif", ".tiff"}
SKIP = {"logs"}

def parse_folder(name):
    """'강동구 양재대로95길 36-9, 성지빌라(성내동 404-10)' -> (주택명, 지번, 도로명).
    Handles double parens (지번 vs 부가설명) by picking the 지번-like group."""
    groups = [(m.group(1).strip(), m.start()) for m in re.finditer(r"\(([^()]*)\)", name)]
    jibeon, jstart = "", len(name)
    for g, s in groups:  # a 지번 has a 동/가/리/로 name AND a number
        if re.search(r"\d", g) and re.search(r"(동|가|리)", g):
            jibeon, jstart = g, s
            break
    if not jibeon and groups:  # fallback: last group
        jibeon, jstart = groups[-1]
    base = name[:jstart].strip()  # text before the 지번 parens
    juhaengmyeong, doro = "", ""
    if "," in base:
        left, right = base.rsplit(",", 1)
        juhaengmyeong = right.strip()
        doro = re.sub(r"^\S+구\s+", "", left.strip())  # drop leading 구
    else:
        juhaengmyeong = re.sub(r"^\S+구\s+", "", base)
    return juhaengmyeong, jibeon, doro

def main():
    buildings = []
    for region in sorted(os.listdir(WORK)):
        rpath = os.path.join(WORK, region)
        if not os.path.isdir(rpath) or region in SKIP or "_" not in region:
            continue
        gu, gubun_short = region.split("_", 1)
        gubun = "신규공급" if gubun_short.startswith("신규") else "재공급"
        for bname in sorted(os.listdir(rpath)):
            bpath = os.path.join(rpath, bname)
            if not os.path.isdir(bpath):
                continue
            juhaengmyeong, jibeon, doro = parse_folder(bname)
            images, domyeon_pdfs, sajin_pdfs, combined_pdfs, others = [], [], [], [], []
            for root, _, files in os.walk(bpath):
                for f in files:
                    if f.startswith("._"):
                        continue
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, WORK)
                    ext = os.path.splitext(f)[1].lower()
                    low = f
                    if ext in RAW_IMG_EXT:
                        continue
                    if ext in IMG_EXT:
                        images.append(rel)
                    elif ext == ".pdf":
                        if "도면 및 사진" in low or "도면및사진" in low:
                            combined_pdfs.append(rel)
                        elif low.startswith("[사진]") or "[사진]" in low:
                            sajin_pdfs.append(rel)
                        else:
                            domyeon_pdfs.append(rel)
                    else:
                        others.append(rel)
            images.sort(key=natkey)
            buildings.append({
                "region_dir": region, "구": gu, "구분": gubun,
                "folder": bname, "주택명": juhaengmyeong, "지번": jibeon, "도로명": doro,
                "images": images,
                "domyeon_pdfs": sorted(domyeon_pdfs),
                "sajin_pdfs": sorted(sajin_pdfs),
                "combined_pdfs": sorted(combined_pdfs),
                "others": sorted(others),
            })
    json.dump(buildings, open(OUT, "w"), ensure_ascii=False, indent=1)

    # ---- report ----
    print(f"building folders: {len(buildings)}")
    print(f"  with images:        {sum(1 for b in buildings if b['images'])}")
    print(f"  with 사진 pdf:       {sum(1 for b in buildings if b['sajin_pdfs'])}")
    print(f"  with 도면 및 사진pdf: {sum(1 for b in buildings if b['combined_pdfs'])}")
    print(f"  with 도면 pdf:       {sum(1 for b in buildings if b['domyeon_pdfs'])}")
    print(f"  NO photo/도면 at all: {sum(1 for b in buildings if not(b['images'] or b['sajin_pdfs'] or b['combined_pdfs'] or b['domyeon_pdfs']))}")
    print(f"  total images: {sum(len(b['images']) for b in buildings)}")
    print(f"  empty 지번 parse: {sum(1 for b in buildings if not b['지번'])}")
    others = [o for b in buildings for o in b['others']]
    print(f"  other files (hwp 등): {len(others)}")

if __name__ == "__main__":
    main()
