#!/usr/bin/env python3
"""Extract photos from '사진' PDFs of buildings that have NO individual images, so
the trapped photos show up as gallery thumbnails.

Per page, hybrid strategy:
  * exactly ONE "real" embedded image (min side >= MIN_DIM, sane aspect) -> save it
    directly (tight crop, native resolution).
  * otherwise (0, or many banded strips, or vector floor plan) -> render the whole
    page to a JPG. This handles PDFs that slice a page into horizontal bands.
Result: exactly one image per page, in page order, no fragment junk.

Output goes to "[사진추출] <pdf-name>/" inside the building folder, so
catalog_media.py picks the files up automatically as gallery images."""
import json, os, re, sys, fitz
from common import WORK

MIN_DIM = 250           # a "real" image's shortest side must be >= this (drops bands/logos)
RENDER_DPI = 150        # whole-page fallback render resolution
OUT_PREFIX = "[사진추출] "

def targets(only_ids=None):
    txt = open(os.path.join(WORK, "data.js"), encoding="utf-8").read()
    DATA = json.loads(re.search(r"window\.DATA\s*=\s*(\[.*?\]);", txt, re.S).group(1))
    out = []
    for b in DATA:
        md = b["media"]
        if md["images"]:
            continue
        pdfs = []
        for key in ("sajin_pdfs", "combined_pdfs", "domyeon_pdfs"):
            for p in md[key]:
                if "사진" in os.path.basename(p):
                    pdfs.append(p)
        if pdfs and (only_ids is None or b["id"] in only_ids):
            out.append((b["id"], b["구"], b["주택명"], pdfs))
    return out

def real_images(doc, pno):
    """Embedded images on the page whose own bitmap is large with a sane aspect.
    Images that fail to decode (e.g. alpha/CMYK quirks) are skipped so the page
    falls back to a whole-page render."""
    res = []
    for im in doc.get_page_images(pno, full=True):
        try:
            info = doc.extract_image(im[0])
        except Exception:
            continue
        if not info.get("image"):
            continue
        w, h = info["width"], info["height"]
        if min(w, h) < MIN_DIM:
            continue
        ar = w / h if h else 99
        if ar < 0.2 or ar > 5:      # ultra-thin band / banner -> not a standalone photo
            continue
        res.append(info)
    return res

def extract_pdf(rel_pdf):
    full = os.path.join(WORK, rel_pdf)
    doc = fitz.open(full)
    base = os.path.splitext(os.path.basename(rel_pdf))[0]
    outdir = os.path.join(os.path.dirname(full), OUT_PREFIX + base)
    os.makedirs(outdir, exist_ok=True)
    n = n_render = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        imgs = real_images(doc, pno)
        if len(imgs) == 1:
            info = imgs[0]
            ext = info["ext"].lower()
            ext = "jpg" if ext in ("jpeg", "jpg") else ext
            with open(os.path.join(outdir, f"p{pno+1:02d}.{ext}"), "wb") as f:
                f.write(info["image"])
        else:
            pix = page.get_pixmap(dpi=RENDER_DPI)
            pix.save(os.path.join(outdir, f"p{pno+1:02d}.jpg"), jpg_quality=85)
            n_render += 1
        n += 1
    doc.close()
    if n == 0:
        os.rmdir(outdir)
    return n, n_render

def main():
    only_ids = set(int(x) for x in sys.argv[1:]) if len(sys.argv) > 1 else None
    tg = targets(only_ids)
    print(f"=== {sum(len(p) for _,_,_,p in tg)} PDFs ({len(tg)} buildings) ===")
    total = total_r = 0
    for bid, gu, name, pdfs in tg:
        for p in pdfs:
            try:
                n, nr = extract_pdf(p)
            except Exception as e:
                print(f"FAIL [{gu}] {name}: {e}  <- {os.path.basename(p)}")
                continue
            total += n; total_r += nr
            tag = f"{n}p (render {nr})" if nr else f"{n}p"
            print(f"OK  [{gu}] {name}: {tag}")
    print(f"=== done: {total} images ({total_r} rendered, {total-total_r} embedded) ===")

if __name__ == "__main__":
    main()
