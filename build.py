#!/usr/bin/env python3
"""Embed data.json into data.js as window.DATA (avoids file:// fetch/CORS)."""
import json, os
from common import WORK

data = json.load(open(os.path.join(WORK, "data.json")))

# lightweight top-level meta for the UI header
meta = {
    "건물수": len(data),
    "호수": sum(b["호수"] for b in data),
    "구목록": sorted({b["구"] for b in data}),
    "geocoded": sum(1 for b in data if b.get("lat")),
}
with open(os.path.join(WORK, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.META = " + json.dumps(meta, ensure_ascii=False) + ";\n")
    f.write("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")

print("data.js written:",
      f"{meta['건물수']} buildings, {meta['호수']} units, geocoded {meta['geocoded']}")
print("size:", round(os.path.getsize(os.path.join(WORK, "data.js")) / 1024), "KB")
