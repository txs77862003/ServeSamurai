#!/bin/bash

# Web UI 切り取りサーバーの起動スクリプト

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# ポート番号を取得（デフォルト: 8085）
PORT=${1:-8085}

echo "🎾 Web UI サーブ切り取りサーバー"
echo "==============================="
echo "ポート: $PORT"
echo "URL: http://localhost:$PORT"
echo ""

# 仮想環境をアクティベート
if [ -f "../.venv/bin/activate" ]; then
    echo "仮想環境をアクティベート中..."
    source ../.venv/bin/activate
else
    echo "⚠️  仮想環境が見つかりません: ../.venv/bin/activate"
    echo "システムのPythonを使用します"
fi

# 必要なライブラリをチェック
echo "必要なライブラリをチェック中..."
python3 -c "import cv2, json" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 必要なライブラリが不足しています"
    echo "以下のライブラリをインストールしてください:"
    echo "  pip install opencv-python"
    exit 1
fi

echo "✅ 必要なライブラリが利用可能です"
echo ""

# ディレクトリを作成
mkdir -p uploads outputs

echo "🚀 Web UI 切り取りサーバーを起動中..."
echo "ブラウザで http://localhost:$PORT にアクセスしてください"
echo ""
echo "特徴:"
echo "  • ブラウザ上で動画プレーヤーを使用"
echo "  • キーボードショートカット対応"
echo "  • リアルタイムでセグメント管理"
echo "  • 個別切り取りと結合切り取りの両方に対応"
echo ""
echo "操作方法:"
echo "  • スペース: 再生/停止"
echo "  • S: サーブ開始マーク"
echo "  • E: サーブ終了マーク"
echo "  • C: 現在のセグメントをキャンセル"
echo "  • R: 全てのセグメントをリセット"
echo "  • ←/→: 5秒戻る/進む"
echo ""

python3 web_server_ui_clipper.py $PORT
