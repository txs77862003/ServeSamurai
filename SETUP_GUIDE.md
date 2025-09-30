# 🎾 Tennis Serve Analysis - セットアップガイド

このプロジェクトを友達の環境で実行するための完全なセットアップガイドです。

## 📋 前提条件

- **Node.js**: 18.0.0以上
- **npm**: 8.0.0以上
- **Git**: 最新版
- **OS**: Windows/macOS/Linux

## 🚀 クイックスタート（推奨）

### 1. リポジトリをクローン
```bash
git clone <repository-url>
cd "Tennis Serve Analysis"
```

### 2. フロントエンドをセットアップ
```bash
cd 40_UI_Taro
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

## 📁 プロジェクト構造

```
Tennis Serve Analysis/
├── 40_UI_Taro/              # フロントエンド（Next.js）
│   ├── src/                 # ソースコード
│   ├── public/              # 静的ファイル
│   ├── package.json         # 依存関係
│   ├── setup.sh            # 自動セットアップスクリプト
│   ├── README.md           # フロントエンド詳細説明
│   ├── QUICKSTART.md       # クイックスタートガイド
│   └── TROUBLESHOOTING.md  # トラブルシューティング
├── pose_analysis/           # ポーズ分析モジュール
├── pose_tracks/            # ポーズデータ
└── README.md               # プロジェクト全体の説明
```

## 🔧 詳細セットアップ

### フロントエンド（40_UI_Taro）

```bash
cd 40_UI_Taro

# 依存関係をインストール
npm install

# 必要なディレクトリを作成
mkdir -p public/clipped-videos
mkdir -p tmp

# 開発サーバーを起動
npm run dev
```

### 利用可能なスクリプト

```bash
npm run dev          # 開発サーバー起動（ポート3030）
npm run build        # プロダクションビルド
npm run start        # プロダクションサーバー起動
npm run lint         # コードチェック
npm run setup        # 自動セットアップ
npm run clean        # 完全リセット
npm run check-port   # ポート3030の使用状況確認
```

## 🎯 機能テスト

起動後、以下の手順で機能をテストしてください：

1. **動画アップロード**
   - テニスサーブ動画をドラッグ&ドロップ
   - 対応形式: MP4, MOV, AVI, QuickTime
   - 最大サイズ: 100MB

2. **手動クリッピング**
   - 動画の開始・終了時間を設定
   - 「Execute Video Clipping」をクリック

3. **結果表示**
   - 「Run Serve Analysis」をクリック
   - プロ選手との比較結果を確認

4. **ポーズアドバイス**
   - 「Pose Advice Tool」をクリック
   - 詳細なポーズ分析を実行

## 🐛 トラブルシューティング

### よくある問題

1. **ポート3030が使用中**
   ```bash
   lsof -i :3030
   kill -9 <PID>
   ```

2. **依存関係エラー**
   ```bash
   npm run clean
   ```

3. **Node.jsバージョンエラー**
   - Node.js 18.0.0以上をインストール

4. **メモリ不足**
   ```bash
   export NODE_OPTIONS="--max-old-space-size=4096"
   npm run dev
   ```

詳細は `40_UI_Taro/TROUBLESHOOTING.md` を参照してください。

## 📱 対応環境

### ブラウザ
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### OS
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Ubuntu 18.04+
- ✅ CentOS 7+

## 🆘 サポート

問題が解決しない場合は、以下の情報と一緒にサポートに連絡してください：

- OSとバージョン
- Node.jsとnpmのバージョン
- ブラウザとバージョン
- エラーメッセージの全文
- 実行したコマンドの履歴

## 📚 参考資料

- [フロントエンド詳細説明](40_UI_Taro/README.md)
- [クイックスタートガイド](40_UI_Taro/QUICKSTART.md)
- [トラブルシューティング](40_UI_Taro/TROUBLESHOOTING.md)

---

**Happy Coding! 🚀**
