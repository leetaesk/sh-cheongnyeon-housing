#!/bin/bash
# Download all SH webhard district zips in parallel with integrity checks.
WORK="$(cd "$(dirname "$0")" && pwd)"
ZIPS="$WORK/zips"
LOGS="$WORK/logs"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
mkdir -p "$ZIPS" "$LOGS"

download_one() {
  local region="$1" lid="$2"
  local out="$ZIPS/${region}.zip"
  local hdr="$LOGS/${region}.hdr"
  local errlog="$LOGS/${region}.err"

  # Skip if already a valid, complete zip
  if [ -f "$out" ] && [ "$(head -c4 "$out" 2>/dev/null | xxd -p)" = "504b0304" ]; then
    echo "SKIP  $region ($(stat -f%z "$out") bytes)"
    return 0
  fi

  local attempt rc expected actual magic
  for attempt in 1 2 3; do
    curl -sS --fail -D "$hdr" \
      -A "$UA" \
      -H "Referer: https://webhard.i-sh.co.kr/pm/linkdown.htm?lid=${lid}" \
      --data "lid=${lid}&act=down&linkpwd=" \
      "https://webhard.i-sh.co.kr/pm/linkdown.htm?lid=${lid}" \
      -o "$out" 2>"$errlog"
    rc=$?
    expected=$(grep -i '^Content-Length:' "$hdr" 2>/dev/null | tr -d '\r' | awk '{print $2}' | tail -1)
    actual=$(stat -f%z "$out" 2>/dev/null)
    magic=$(head -c4 "$out" 2>/dev/null | xxd -p)
    if [ $rc -eq 0 ] && [ -n "$expected" ] && [ "$expected" = "$actual" ] && [ "$magic" = "504b0304" ]; then
      echo "OK    $region ($actual bytes)"
      return 0
    fi
    echo "RETRY $region attempt=$attempt rc=$rc expected=${expected:-?} actual=${actual:-?} magic=${magic:-?}"
    sleep 5
  done
  echo "FAIL  $region"
  return 1
}
export -f download_one
export ZIPS LOGS UA

echo "=== download start: $(cat "$WORK/links.tsv" | wc -l | tr -d ' ') regions, concurrency=5 ==="
# TSV is region<TAB>lid; xargs -n2 feeds each pair as $1 $2
xargs -P 5 -n 2 bash -c 'download_one "$1" "$2"' _ < "$WORK/links.tsv"
echo "=== download done ==="

echo "=== SUMMARY ==="
ok=0; fail=0; total=0
while IFS=$'\t' read -r region lid; do
  total=$((total+1))
  out="$ZIPS/${region}.zip"
  if [ -f "$out" ] && [ "$(head -c4 "$out" 2>/dev/null | xxd -p)" = "504b0304" ]; then
    ok=$((ok+1))
  else
    fail=$((fail+1)); echo "MISSING/INVALID: $region"
  fi
done < "$WORK/links.tsv"
echo "valid zips: $ok / $total,  problems: $fail"
