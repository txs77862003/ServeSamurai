#!/bin/bash

# サーブ動画自動切り取りWebサーバーの起動スクリプト

echo "=== サーブ動画自動切り取り機能 ==="
echo ""

# 現在のディレクトリを確認
CURRENT_DIR=$(pwd)
echo "現在のディレクトリ: $CURRENT_DIR"

# Pythonの依存関係をチェック
echo "Python依存関係をチェック中..."
python3 -c "import cv2, pandas, numpy, torch, sklearn; print('✓ 必要なライブラリが利用可能です')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  必要なライブラリが不足しています。以下をインストールしてください:"
    echo "   pip install opencv-python pandas numpy torch scikit-learn"
    echo ""
fi

# ポート番号を取得（デフォルト: 8080）
PORT=${1:-8080}

echo "Webサーバーを起動します..."
echo "ポート: $PORT"
echo ""
echo "ブラウザで以下のURLにアクセスしてください:"
echo "  http://localhost:$PORT"
echo ""
echo "終了するには Ctrl+C を押してください"
echo ""

# Webサーバーを起動
python3 simple_web_server.py $PORT
