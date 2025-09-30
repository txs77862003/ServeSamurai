# ⚡ クイックスタートガイド

Tennis Serve Analysis フロントエンドを最短時間で起動するためのガイドです。

## 🚀 5分で起動

### 1. リポジトリをクローン
```bash
git clone <repository-url>
cd "Tennis Serve Analysis/40_UI_Taro"
```

### 2. 自動セットアップ（推奨）
```bash
npm run setup
```

### 3. 開発サーバーを起動
```bash
npm run dev
```

### 4. ブラウザでアクセス
```
http://localhost:3030
```

## 🎯 手動セットアップ

自動セットアップが失敗した場合：

### 1. 依存関係をインストール
```bash
npm install
```

### 2. 必要なディレクトリを作成
```bash
mkdir -p public/clipped-videos
mkdir -p tmp
```

### 3. 開発サーバーを起動
```bash
npm run dev
```

## ✅ 動作確認

起動後、以下の機能をテストしてください：

1. **ホーム画面** - 動画ファイルをドラッグ&ドロップ
2. **クリッピング画面** - 動画の開始・終了時間を設定
3. **結果画面** - 「Run Serve Analysis」ボタンをクリック
4. **ポーズアドバイス画面** - 詳細分析ツール

## 🔧 よくある問題

### ポート3030が使用中
```bash
# プロセスを確認
lsof -i :3030

# プロセスを終了
kill -9 <PID>
```

### 依存関係エラー
```bash
# 完全リセット
npm run clean
```

### メモリ不足
```bash
# メモリ制限を増やす
export NODE_OPTIONS="--max-old-space-size=4096"
npm run dev
```

## 📱 対応ブラウザ

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## 🎾 機能概要

1. **動画アップロード** - テニスサーブ動画をアップロード
2. **手動クリッピング** - サーブ部分を正確に切り取り
3. **結果表示** - プロ選手との比較分析
4. **ポーズアドバイス** - 詳細な技術分析

## 🆘 サポート

問題が発生した場合は `TROUBLESHOOTING.md` を確認してください。

---

**Happy Coding! 🚀**
