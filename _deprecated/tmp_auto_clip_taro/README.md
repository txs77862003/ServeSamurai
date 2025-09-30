# サーブ動画自動切り取り機能

LSTMで学習されたデータを利用して、テニスサーブの開始から終了までを自動的に検出・切り取りする機能です。

## 特徴

- **LSTMモデルによる自動検出**: 学習済みのLSTMモデルがサーブの開始と終了を自動検出
- **データ拡張対応**: `tennis_pose_augmented.py`の高度なデータ拡張機能を活用
- **Webインターフェース**: ブラウザから簡単に動画をアップロードして処理
- **独立動作**: `40_UI_Taro`に影響を与えずに独立して動作

## 必要な環境

### Pythonライブラリ
```bash
pip install opencv-python pandas numpy torch scikit-learn matplotlib seaborn
```

### 学習済みモデル
- `best_augmented_model.pth` (30_Classification_LSTMディレクトリ内)

## 使用方法

### 1. Webサーバーの起動
```bash
cd tmp_auto_clip_taro
./start_server.sh
```

または直接Pythonで起動:
```bash
python3 simple_web_server.py
```

### 2. ブラウザでアクセス
```
http://localhost:8080
```

### 3. 動画をアップロード
- テニスサーブの動画ファイルを選択
- 「動画を処理」ボタンをクリック
- 処理完了後、切り取られたサーブ動画が表示されます

### 4. コマンドラインでの使用
```bash
python3 serve_auto_clipper.py <動画ファイルパス> [出力ディレクトリ]
```

## 処理の流れ

1. **キーポイント抽出**: YOLOを使用して動画から人体のキーポイントを抽出
2. **サーブ検出**: LSTMモデルがキーポイントシーケンスからサーブを検出
3. **動画切り取り**: 検出されたサーブセグメントから動画を自動切り取り
4. **結果出力**: 切り取られた動画とメタデータを保存

## 出力ファイル

処理完了後、以下のファイルが生成されます:

```
{動画名}_processed/
├── keypoints/                    # キーポイントデータ
├── clipped_serves/               # 切り取られたサーブ動画
│   ├── video_serve_1_conf0.85.mp4
│   ├── video_serve_2_conf0.92.mp4
│   └── ...
└── processing_result.json        # 処理結果のメタデータ
```

## 設定可能なパラメータ

### 信頼度閾値
```python
# serve_auto_clipper.py内で調整
if confidence > 0.7:  # 閾値を変更可能
```

### シーケンス長
```python
self.sequence_length = 48  # フレーム数
```

### スライディングウィンドウ間隔
```python
for i in range(0, len(df) - sequence_length + 1, 10):  # 10フレーム間隔
```

## トラブルシューティング

### モデルファイルが見つからない
```
警告: モデルファイルが見つかりません: best_augmented_model.pth
```
→ `30_Classification_LSTM/best_augmented_model.pth`が存在することを確認

### キーポイント抽出エラー
```
キーポイント抽出エラー: YOLOスクリプトが見つかりません
```
→ `22_Joint_Detection_YOLO/YOLO.py`が存在することを確認

### メモリ不足
大量の動画を処理する場合は、バッチサイズを調整:
```python
# シーケンスを分割して処理
batch_size = 10
```

## ファイル構成

```
tmp_auto_clip_taro/
├── serve_auto_clipper.py      # メイン処理スクリプト
├── simple_web_server.py       # Webサーバー
├── test_auto_clipper.py       # テストスクリプト
├── start_server.sh            # 起動スクリプト
├── README.md                  # このファイル
└── uploads/                   # アップロードされたファイル（自動作成）
```

## 技術仕様

- **モデル**: AugmentedLSTM (hidden_size=64, layers=2)
- **入力**: 48フレーム × 24特徴量（12関節のx,y座標）
- **出力**: 3クラス分類（djo, fed, kei）
- **信頼度**: 0-1の範囲でサーブ検出の確信度

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
