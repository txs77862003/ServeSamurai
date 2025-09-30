# 🎾 Tennis Serve Analysis - Frontend

テニスサーブ分析アプリケーションのフロントエンド部分です。

## 🚀 クイックスタート

### 前提条件
- Node.js 18.0.0 以上
- npm または yarn

### インストール

1. リポジトリをクローン
```bash
git clone <repository-url>
cd "Tennis Serve Analysis/40_UI_Taro"
```

2. 依存関係をインストール
```bash
npm install
```

3. 開発サーバーを起動
```bash
npm run dev
```

4. ブラウザでアクセス
```
http://localhost:3030
```

## 📁 プロジェクト構造

```
src/
├── app/                    # Next.js App Router
│   ├── page.tsx           # ホーム画面（動画アップロード）
│   ├── manual-clip/       # 手動クリッピング画面
│   ├── results/           # 結果表示画面
│   ├── pose-advice/       # ポーズアドバイス画面
│   └── api/               # API エンドポイント
├── components/            # React コンポーネント
├── lib/                   # ユーティリティ関数
└── hooks/                 # カスタムフック
```

## 🛠️ 利用可能なスクリプト

- `npm run dev` - 開発サーバーを起動（ポート3030）
- `npm run build` - プロダクションビルド
- `npm run start` - プロダクションサーバーを起動
- `npm run lint` - ESLintでコードをチェック

## 🎯 機能

### 4画面ワークフロー
1. **動画アップロード** - テニスサーブ動画をアップロード
2. **手動クリッピング** - サーブ部分を手動で切り取り
3. **結果表示** - プロ選手との比較分析結果を表示
4. **ポーズアドバイス** - 詳細なポーズ分析とアドバイス

### 主な機能
- 動画ファイルのドラッグ&ドロップアップロード
- リアルタイム動画プレビュー
- 手動での動画クリッピング（開始・終了時間指定）
- プロ選手（錦織圭、フェデラー、ジョコビッチ）との比較分析
- モック分析結果の表示
- レスポンシブデザイン

## 🔧 技術スタック

- **フレームワーク**: Next.js 15.3.5 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS
- **UI コンポーネント**: Radix UI
- **アイコン**: Lucide React
- **動画処理**: HTML5 Video API
- **ファイル処理**: Formidable

## 🐛 トラブルシューティング

### ポート3030が使用中の場合
```bash
# ポート3030を使用しているプロセスを確認
lsof -i :3030

# プロセスを終了
kill -9 <PID>
```

### 依存関係のインストールエラー
```bash
# node_modulesを削除して再インストール
rm -rf node_modules package-lock.json
npm install
```

### ビルドエラー
```bash
# TypeScriptの型チェック
npm run lint

# キャッシュをクリア
rm -rf .next
npm run dev
```

## 📝 開発メモ

- 動画ファイルはBase64エンコードしてsessionStorageに保存
- クリッピングはffmpegを使用（サーバーサイド）
- 分析結果はモックデータを返す（実際の分析は今後実装予定）

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。
