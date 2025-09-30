# Tennis Serve Analysis Project

## 概要

このプロジェクトは、テニスサーブの動画を分析し、キーポイント検出、姿勢分析、プロ選手との比較、そして改善アドバイスを提供するアプリケーションです。

## プロジェクト構成

```
./Tennis Serve Analysis/
├── 40_UI_ideal/                    ← UI設計・プロトタイプ
├── 40_UI_Taro/                     ← ServeSim関連ファイル (Next.js)
├── 30_Classification_LSTM/         ← 分析ロジックのソース (Python)
├── 22_Joint_Detection_YOLO/        ← キーポイント検出 (Python)
├── 1_DataProcess/                  ← データ処理 (Python)
├── _deprecated/                    ← 古いファイル（参考用）
├── README.md                       ← このファイル
└── その他のデータフォルダ
```

## 主要機能

- **動画アップロード**: テニスサーブの動画ファイルをアップロード
- **キーポイント検出**: YOLOを使用した人体姿勢の検出
- **姿勢分析**: LSTMモデルによるサーブフォームの分析
- **プロ選手比較**: プロ選手のデータとの比較分析
- **改善アドバイス**: パーソナライズされた改善提案

## 技術スタック

- **フロントエンド**: Next.js, React, TypeScript
- **バックエンド**: Python, FastAPI
- **機械学習**: PyTorch, YOLO, LSTM
- **データ処理**: OpenCV, Pandas, NumPy

## セットアップ

### 前提条件
- Python 3.8+
- Node.js 18+
- Git

### インストール

1. リポジトリのクローン
```bash
git clone <repository-url>
cd "Tennis Serve Analysis"
```

2. Python依存関係のインストール
```bash
pip install -r requirements.txt
```

3. Node.js依存関係のインストール
```bash
cd 40_UI_ideal
npm install --legacy-peer-deps
```

## 使用方法

### 開発サーバーの起動
```bash
# フロントエンド（40_UI_ideal）
cd 40_UI_ideal
npm run dev

# ビデオクリッピング（40_UI_ideal）
http://localhost:3030/manual_clip

# または ServeSim関連（40_UI_Taro）
cd 40_UI_Taro
npm install --legacy-peer-deps
npm run dev
```

### データ処理
```bash
# 0 )データの準備
tennis_videos というディレクトリをプロジェクト直下に作り、そこにGoogle Driveからダウンロードしたzipファイルを解凍する。
# 1) パイプライン一括実行（推奨）
bash "./run_pipeline.sh" --fps 30


### 出力仕様（重要）
- CSV出力のキーポイント列は `kpt_5_*` から始まり `kpt_16_*` が最後になるよう並びます（`kpt_0`〜`kpt_4` は出力しません）。
- 出力先ディレクトリ構成:
  - フレーム: `frames/<クリップ>/frame_*.jpg`
  - 1フレーム座標CSV: `frames/pose_coords_yolo/<選手>/<クリップ>/*_coords.csv`
  - 集約CSV/要約: `pose_tracks/<選手>/<クリップ>/keypoints_with_tracks.csv`, `movement_summary.csv`（`pose_tracks` は `frames` と同じ階層）


## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
