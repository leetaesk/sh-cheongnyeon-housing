#!/bin/bash
# Convert every raster image to WebP (q$Q, longest side <= $MAX, never upscale),
# then delete the original. 15-way parallel. Korean/space/bracket filenames safe.
# CMYK JPEGs (which cwebp can't read) fall back to sips -> RGB PNG -> cwebp.
set -u
WORK="$(cd "$(dirname "$0")" && pwd)"
export Q=80
export MAX=2000

convert_one() {
  f="$1"
  out="${f%.*}.webp"
  # dimensions via sips
  dims=$(sips -g pixelWidth -g pixelHeight "$f" 2>/dev/null | awk '/pixelWidth/{w=$2}/pixelHeight/{h=$2}END{print w" "h}')
  w=${dims% *}; h=${dims#* }
  r=""
  if [[ "$w" =~ ^[0-9]+$ && "$h" =~ ^[0-9]+$ ]]; then
    if [ "$w" -ge "$h" ] && [ "$w" -gt "$MAX" ]; then r="-resize $MAX 0"
    elif [ "$h" -gt "$w" ] && [ "$h" -gt "$MAX" ]; then r="-resize 0 $MAX"; fi
  fi
  if cwebp -quiet -q "$Q" $r "$f" -o "$out" 2>/dev/null && [ -s "$out" ]; then
    rm -f "$f"
    return 0
  fi
  # fallback: CMYK / odd colorspace -> RGB PNG (downscaled) via sips, then cwebp
  tmp="$(mktemp -t rgb).png"
  if sips -s format png -Z "$MAX" "$f" --out "$tmp" >/dev/null 2>&1 && [ -s "$tmp" ] \
     && cwebp -quiet -q "$Q" "$tmp" -o "$out" 2>/dev/null && [ -s "$out" ]; then
    rm -f "$f" "$tmp"
  else
    rm -f "$tmp"
    echo "FAIL $f"
  fi
}
export -f convert_one

# all jpg/jpeg/png (case-insensitive), excluding .git
find "$WORK" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
  -not -path '*/.git/*' -print0 \
  | xargs -0 -P 15 -n 1 bash -c 'convert_one "$1"' _

echo "=== webp 변환 완료 ==="
