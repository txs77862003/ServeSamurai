#!/bin/bash




set -euo pipefail

IN_DIR="tennis_videos"
OUT_DIR="clips"
INPUT_FILE="clip_list_taro.txt"   # 上記のリストを保存したファイル　
mkdir -p "$OUT_DIR"

while read -r fname start end tags; do
    in="$IN_DIR/$fname"
    stem="${fname%.mp4}"
    # tags の中のカンマを _ に変換してファイル名に使いやすくする
    tag_str=$(echo "$tags" | tr ',' '_')
    out="${OUT_DIR}/${stem}_${tag_str}_30fps.mp4"

    echo "[CUT] $in ($start ~ +1.6s) -> $out"

    ffmpeg -y -hide_banner -loglevel warning \
        -ss "$start" -i "$in" \
        -t 1.6 -vf "fps=30" \
        -c:v libx264 -preset veryfast -crf 18 -an "$out"
done < "$INPUT_FILE"

#実行手順

#　kei_serve_back1.mp4 1.96 3.45 kei,back,serve,deuce　みたいな感じでclip_list.txt ファイルに格納しておく。これをcut_clips_taro.sh で実行する。
#chmod +x cut_clips_taro.sh     # 実行権限を付与
# 実行　./cut_clips_taro.sh

