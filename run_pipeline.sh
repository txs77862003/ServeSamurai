#!/bin/bash
set -euo pipefail

# 使い方:
#   bash run_pipeline.sh [--fps 30] [--coords-root frames/pose_coords_yolo]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

FPS=30
COORDS_ROOT="$PROJECT_ROOT/frames/pose_coords_yolo"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fps)
      FPS="${2:-30}"; shift 2 ;;
    --coords-root)
      COORDS_ROOT="${2:-$COORDS_ROOT}"; shift 2 ;;
    *)
      echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "[1/3] フレーム抽出 (既存の48フレーム動画を frames 下へ)"
python3 "$PROJECT_ROOT/1_DataProcess/10_dataclean.py" extract-frames --target "$PROJECT_ROOT/tennis_videos" --frames-root "$PROJECT_ROOT/frames" --fps "$FPS"

echo "[2/3] YOLO ポーズ推定とトラッキング"
# Ultralytics のキャッシュ/作業を /tmp に固定し、モデルを /tmp に用意
cp -f "$PROJECT_ROOT/yolo11n-pose.pt" /tmp/yolo11n-pose.pt 2>/dev/null || true
ULTRALYTICS_CACHE_DIR=/tmp TMPDIR=/tmp HOME=/tmp \
  python3 "$PROJECT_ROOT/22_Joint_Detection_YOLO/YOLO.py"

echo "[3/3] 最も活発なトラックの特定とCSV整形"
python3 "$PROJECT_ROOT/22_Joint_Detection_YOLO/find_most_active_tracks.py" --coords-root "$COORDS_ROOT"

echo "✅ パイプライン完了"


