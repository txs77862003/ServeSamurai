#!/bin/bash
set -euo pipefail

# スクリプトのあるディレクトリを基準にパスを解決
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 入出力の実体はプロジェクト直下に配置
IN_DIR="$PROJECT_ROOT/tennis_videos"
OUT_DIR="$PROJECT_ROOT/clips"
INPUT_FILE="$SCRIPT_DIR/clip_list_taro.txt"
mkdir -p "$OUT_DIR"

while read -r fname start end player angle shot tags; do
    # 空行やコメント行はスキップ
    if [ -z "${fname:-}" ] || echo "$fname" | grep -qE '^#'; then
        continue
    fi
    in="$IN_DIR/$fname"
    # 入力ファイルが見つからない場合、先頭に"k"が落ちているケースをフォールバックで補正
    if [ ! -f "$in" ] && [ -f "$IN_DIR/k$fname" ]; then
        in="$IN_DIR/k$fname"
    fi

    # 実際に使用するファイル名からstemを再計算
    actual_name="$(basename "$in")"
    stem="${actual_name%.mp4}"

    out="${OUT_DIR}/${stem}_${player}_${shot}_${angle}_${tags}.mp4"

    echo "[CUT] $in ($start ~ $end) -> $out"

    ffmpeg -y -hide_banner -loglevel warning \
        -ss "$start" -to "$end" -i "$in" \
        -vf "fps=30" \
        -an "$out"  
done < "$INPUT_FILE"