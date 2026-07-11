#!/usr/bin/env python3
"""Two-phase extraction, preserving Korean (CP949) filenames:
  1) each district zip in zips/  ->  {구}_{신규|재공급}/ folders
  2) nested [사진]*.zip photo archives inside those folders -> unpacked in place
"""
import os, zipfile
from common import WORK

ZIPS = os.path.join(WORK, "zips")
SKIP_DIRS = {ZIPS, os.path.join(WORK, "logs"), os.path.join(WORK, ".git")}

def fix_name(info):
    """Decode a zip member name, repairing CP949/EUC-KR mojibake."""
    name = info.filename
    # If the entry declared UTF-8 (flag bit 0x800), python already decoded correctly.
    if info.flag_bits & 0x800:
        return name
    # Otherwise python decoded raw bytes as cp437; recover bytes and try cp949.
    try:
        raw = name.encode("cp437")
    except Exception:
        return name
    for enc in ("cp949", "euc-kr", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return name

def safe_join(base, *paths):
    """Join and ensure result stays within base (zip-slip guard)."""
    target = os.path.normpath(os.path.join(base, *paths))
    if not (target == base or target.startswith(base + os.sep)):
        raise ValueError(f"unsafe path: {paths}")
    return target

def extract_zip(zip_path, dest):
    os.makedirs(dest, exist_ok=True)
    n = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = fix_name(info).replace("\\", "/")
            parts = [p for p in name.split("/") if p not in ("", ".", "..")]
            if not parts:
                continue
            out = safe_join(dest, *parts)
            if info.is_dir() or name.endswith("/"):
                os.makedirs(out, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with zf.open(info) as src, open(out, "wb") as dst:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    dst.write(chunk)
            n += 1
    return n

def phase1():
    zips = sorted(f for f in os.listdir(ZIPS) if f.endswith(".zip")) if os.path.isdir(ZIPS) else []
    print(f"=== phase 1: {len(zips)} district zips ===")
    ok = fail = 0
    for z in zips:
        region = z[:-4]
        try:
            n = extract_zip(os.path.join(ZIPS, z), os.path.join(WORK, region))
            print(f"OK    {region}: {n} files")
            ok += 1
        except Exception as e:
            print(f"FAIL  {region}: {e}")
            fail += 1
    print(f"=== phase 1 done: {ok} ok, {fail} failed ===")

def phase2():
    targets = []
    for root, dirs, files in os.walk(WORK):
        if any(root == d or root.startswith(d + os.sep) for d in SKIP_DIRS):
            dirs[:] = []
            continue
        for f in files:
            if f.lower().endswith(".zip"):
                targets.append(os.path.join(root, f))
    targets.sort()
    print(f"=== phase 2: {len(targets)} nested zips ===")
    ok = fail = total = 0
    for z in targets:
        try:
            n = extract_zip(z, z[:-4])
            total += n
            ok += 1
            print(f"OK    {os.path.relpath(z, WORK)} -> {n} files")
        except Exception as e:
            fail += 1
            print(f"FAIL  {os.path.relpath(z, WORK)}: {e}")
    print(f"=== phase 2 done: {ok} ok, {fail} failed, {total} files extracted ===")

if __name__ == "__main__":
    phase1()
    phase2()
