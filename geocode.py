#!/usr/bin/env python3
"""Geocode each building's road address via Nominatim (OSM). Adds lat/lng to data.json.
Rate-limited to 1 req/sec, cached, with fallback queries."""
import json, os, time, urllib.parse, urllib.request
from common import WORK

DATA = os.path.join(WORK, "data.json")
CACHE = os.path.join(WORK, "geocode_cache.json")
UA = "sh-cheongnyeon-housing-map/1.0"

cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

def query(q):
    if q in cache:
        return cache[q]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "format": "json", "limit": 1, "countrycodes": "kr",
        "accept-language": "ko", "q": q,
    })
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.load(r)
    except Exception as e:
        data = []
    time.sleep(1.1)  # respect Nominatim 1 req/s policy
    res = None
    if data:
        res = {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"]),
               "display": data[0].get("display_name", "")}
    cache[q] = res
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=1)
    return res

def geocode_building(b):
    gu, doro = b["구"], b["도로명"]
    candidates = [
        f"서울특별시 {gu} {doro}",
        f"{gu} {doro}",
        f"서울특별시 {gu} {b['지번']}",
    ]
    for q in candidates:
        r = query(q)
        if r:
            return r, q
    return None, None

def main():
    buildings = json.load(open(DATA))
    ok = fail = 0
    fails = []
    for i, b in enumerate(buildings, 1):
        r, used = geocode_building(b)
        if r:
            b["lat"], b["lng"] = round(r["lat"], 7), round(r["lng"], 7)
            b["geo_source"] = used
            ok += 1
        else:
            b["lat"], b["lng"] = None, None
            fail += 1
            fails.append(f"{b['구']} {b['도로명']} ({b['주택명']})")
        if i % 20 == 0:
            print(f"  ... {i}/{len(buildings)} (ok={ok} fail={fail})", flush=True)
    json.dump(buildings, open(DATA, "w"), ensure_ascii=False, indent=1)
    print(f"=== geocode done: ok={ok}, fail={fail} ===")
    for f in fails:
        print("  FAIL:", f)

if __name__ == "__main__":
    main()
