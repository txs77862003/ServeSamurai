#!/usr/bin/env bash
# Robust cutter with UNIQUE filenames.
# - Accepts MANIFEST as CSV (file,start,end,player,hand,shot,side) or TXT with "first 3 = space, rest = comma"
# - Skips header automatically
# - Swaps start/end if reversed
# - Sanitizes filenames (commas/spaces -> _)
# - Appends start/end to output name to avoid overwrites
# Usage:
#   MANIFEST=clip_list_fed.csv IN_DIR=. OUT_DIR=clips ./cut_clips_unique.sh
#   MANIFEST=clip_list_fed.txt IN_DIR=. OUT_DIR=clips ./cut_clips_unique.sh
set -euo pipefail

MANIFEST="${MANIFEST:-clip_list_fed.csv}"
IN_DIR="${IN_DIR:-.}"
OUT_DIR="${OUT_DIR:-clips}"
mkdir -p "$OUT_DIR"

sanitize() { tr -c 'A-Za-z0-9._-' '_' <<<"$1"; }

is_number(){ [[ "$1" =~ ^[0-9]*\.?[0-9]+$ ]]; }

fmt_time(){
  # keep at most 2 decimals and replace '.' with 'p' for filesystem safety
  local x="$1"
  printf "%.2f" "$x" | tr '.' 'p'
}

read_stream() {
  # Normalize CRLF and strip BOM, skip empty or comment lines
  # Also skip CSV header if present
  perl -pe 'BEGIN{binmode(STDIN); binmode(STDOUT)} s/^\xEF\xBB\xBF//; s/\r$//' "$MANIFEST" \
  | awk 'NR==1 && tolower($0) ~ /^file,/ {next} {print}'
}

line_no=0
read_stream | while IFS= read -r raw || [ -n "${raw-}" ]; do
  ((line_no++))
  # skip blank/comment lines
  [[ -z "${raw// }" || "${raw:0:1}" == "#" ]] && continue

  fname="" start="" end="" player="" hand="" shot="" side=""

  # Prefer CSV if there are 3+ commas; else handle "3 columns + comma labels"
  if [[ "$raw" == *","*","*","* ]]; then
    IFS=, read -r fname start end player hand shot side _ <<<"$raw"
  else
    read -r fname start end rest <<<"$raw"
    IFS=, read -r player hand shot side _ <<<"${rest:-}"
  fi

  # Basic validation
  if [[ -z "${fname:-}" || -z "${start:-}" || -z "${end:-}" ]]; then
    echo "[WARN] $MANIFEST:$line_no: parse failed: $raw" >&2
    continue
  fi
  if ! is_number "$start" || ! is_number "$end"; then
    echo "[WARN] $MANIFEST:$line_no: non-numeric times: $start,$end" >&2
    continue
  fi
  # Swap if reversed
  awk -v s="$start" -v e="$end" 'BEGIN{if(s>e)print "swap"}' | read -r need_swap || true
  [[ "${need_swap:-}" == "swap" ]] && tmp="$start" && start="$end" && end="$tmp"

  in="$IN_DIR/$fname"
  if [[ ! -f "$in" ]]; then
    echo "[WARN] $MANIFEST:$line_no: missing input: $in" >&2
    continue
  fi

  stem="${fname%.*}"
  s_tag="s$(fmt_time "$start")"
  e_tag="e$(fmt_time "$end")"
  out_base="${stem}_${s_tag}-${e_tag}_${player:-na}_${shot:-na}_${hand:-na}_${side:-na}"
  out="${OUT_DIR}/$(sanitize "$out_base").mp4"

  echo "[CUT] $in ($start-$end) -> $out"
  if ! ffmpeg -y -hide_banner -loglevel error \
        -ss "$start" -to "$end" -i "$in" \
        -c:v libx264 -preset veryfast -crf 18 -an "$out"; then
    echo "[WARN] $MANIFEST:$line_no: ffmpeg failed" >&2
  fi
done
