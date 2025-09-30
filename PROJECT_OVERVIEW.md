## プロジェクト全体像（スライド用ドキュメント）

### 1. 目的と価値
- **目的**: テニスのサーブ動作を解析し、プロ選手（Nishikori/Federer/Djokovic）との類似度を算出、改善ポイントを提示する。
- **価値**: スマホやPCでのアップロードだけで、手軽にフォームの良否や改善点を可視化。

### 2. 全体アーキテクチャ
- **データ取得**: 48フレームのクリップ（または既存フレーム画像）を用意
- **前処理/抽出**: フレーム展開（必要時）、YOLOによるキーポイント推定＋トラッキング
- **集約**: 人物トラックごとにフレーム座標をCSVに統合、最も活発なトラックを自動選別
- **分析**: 統計特徴量計算、参照プロファイルとの重み付き差分で類似度スコア化、改善アドバイス生成
- **UI**: Next.jsアプリでアップロード、結果ダッシュボード表示（類似度・進捗バー・助言）

```text
User → (40_UI_Taro) → API(analyze-serve.py)
           │                │
           │                ├─ (30_Classification_LSTM) 特徴量/比較/助言
           │                └─ (pose_tracks 参照)
           └─ 動画準備 → (run_pipeline.sh) → YOLO/集約（22_Joint_Detection_YOLO）
```

### 3. ディレクトリ構成（要点）
- `40_UI_Taro/`: Next.js UI（アップロード、結果表示）
- `22_Joint_Detection_YOLO/`: キーポイント推定（`YOLO.py`）、最活発トラック抽出（`find_most_active_tracks.py`）
- `30_Classification_LSTM/`: 解析ロジックとモデル（`analyze-serve.py`から呼び出し）
- `1_DataProcess/10_dataclean.py`: データ準備（動画→フレーム、または既存画像ミラー）
- 出力系:
  - フレーム: `frames/<clip>/frame_*.jpg`
  - 1フレCSV: `frames/pose_coords_yolo/<選手>/<clip>/*_coords.csv`
  - 集約CSV/要約: `pose_tracks/<選手>/<clip>/keypoints_with_tracks.csv`, `movement_summary.csv`

### 4. パイプライン（実行順）
- 推奨: 一括実行
```bash
bash "./run_pipeline.sh" --fps 30
```
- 内訳
  1) クリップのフレーム展開（動画が無い場合は既存JPG群をミラー）
  2) YOLOでポーズ推定＋トラッキング（CSV/可視化出力）
  3) 最活発トラックを自動選定し、`pose_tracks`に統合CSVを生成

### 5. キーポイント出力ポリシー
- CSV列は以下の順を保証（x→yのペア）: `kpt_5_x, kpt_5_y, ..., kpt_16_x, kpt_16_y`
- `kpt_0`〜`kpt_4`は出力しない（除外済み）。

### 6. 類似度スコアの算出（`analyze-serve.py`）
- 代表値（Nishikori/Federer/Djokovic）の参照プロファイルと、抽出した特徴量（例: 下半身使用度、肩回転、ラケットドロップ）を比較。
- 特徴ごとの重み付き差分の平均を 0〜100 にスケールしてスコア化（差が小さいほど高スコア）。
- スコア上位の選手を「closest match」としてUIに表示。

### 7. 主要スクリプトの役割
- `1_DataProcess/10_dataclean.py`: 入力動画のコピー、フレーム抽出、既存画像のミラー展開
- `22_Joint_Detection_YOLO/YOLO.py`: YOLOを用いたキーポイント推定、トラッキング、CSV集計
- `22_Joint_Detection_YOLO/find_most_active_tracks.py`: 移動量合計で最活発トラックを選定、CSVの整形
- `40_UI_Taro/src/pages/api/analyze-serve.py`: 特徴抽出→類似度算出→助言生成のエンドツーエンド

### 8. Web UIの主な画面
- 動画アップロード→解析実行→結果ダッシュボード
- 類似度バー（Nishikori/Federer/Djokovic）と改善アドバイスの表示
  - 再生プレイヤー、メトリクス説明、学習用の参考イメージを表示

### 9. 最近の改善点（発表ポイント）
- 48フレーム固定クリッピングの自動化（開始マークのみ）
- YOLO出力CSVから `kpt_0`〜`kpt_4` を除外、列順を `kpt_5`→`kpt_16` に統一
- `pose_tracks` を `frames` と同階層に変更し、`Cleaned_Data` を除去したフラットな選手別配下へ出力
- 孫ディレクトリにある既存フレーム（JPG）も自動で処理対象にミラー

### 10. 実行デモのチェックリスト
- `tennis_videos` にクリップ素材を配置（または既存JPG群）
- 一括実行: `run_pipeline.sh` → フォルダに出力（`frames`, `pose_tracks`）
- UI起動（任意）: `40_UI_Taro` を起動して動画アップロード→結果確認

### 11. 次の発展案
- 類似度指標の拡張（正規化ベクトル/コサイン類似とのハイブリッド）
- 参照プロファイルのデータドリブン更新（モデル再学習）
- UIで48フレーム長の可変化、比較対象選手の柔軟な追加

### 12. 参考パス
- ルート: `./`
- 出力: `frames/**`, `pose_tracks/**`
- UI: `40_UI_Taro/`
- YOLO: `22_Joint_Detection_YOLO/`


