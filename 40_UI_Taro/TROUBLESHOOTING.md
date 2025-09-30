# 🐛 トラブルシューティングガイド

このガイドは、Tennis Serve Analysis フロントエンドでよくある問題とその解決方法を説明します。

## 🚨 よくある問題

### 1. ポート3030が使用中

**エラーメッセージ:**
```
Error: listen EADDRINUSE: address already in use :::3030
```

**解決方法:**
```bash
# ポート3030を使用しているプロセスを確認
npm run check-port

# または
lsof -i :3030

# プロセスを終了
kill -9 <PID>

# 別のポートを使用する場合
npm run dev -- --port 3031
```

### 2. 依存関係のインストールエラー

**エラーメッセージ:**
```
npm ERR! peer dep missing
npm ERR! code ENOENT
```

**解決方法:**
```bash
# キャッシュをクリアして再インストール
npm run clean

# または手動で
rm -rf node_modules package-lock.json
npm install
```

### 3. Node.jsのバージョンエラー

**エラーメッセージ:**
```
The engine "node" is incompatible with this module
```

**解決方法:**
- Node.js 18.0.0以上をインストール
- nvmを使用している場合:
```bash
nvm install 18
nvm use 18
```

### 4. TypeScriptエラー

**エラーメッセージ:**
```
Type error: Cannot find module
```

**解決方法:**
```bash
# TypeScriptの型定義を再インストール
npm install @types/node @types/react @types/react-dom

# 型チェックを実行
npm run lint
```

### 5. ビルドエラー

**エラーメッセージ:**
```
Failed to compile
```

**解決方法:**
```bash
# キャッシュをクリア
rm -rf .next

# 再ビルド
npm run build
```

### 6. 動画ファイルのアップロードエラー

**問題:**
- 動画が表示されない
- アップロードが失敗する

**解決方法:**
- 対応形式: MP4, MOV, AVI, QuickTime
- ファイルサイズ: 100MB以下
- ブラウザのJavaScriptが有効になっているか確認

### 7. メモリ不足エラー

**エラーメッセージ:**
```
JavaScript heap out of memory
```

**解決方法:**
```bash
# Node.jsのメモリ制限を増やす
export NODE_OPTIONS="--max-old-space-size=4096"
npm run dev
```

## 🔧 開発環境の確認

### 必要な環境
- Node.js 18.0.0以上
- npm 8.0.0以上
- 現代的なブラウザ（Chrome, Firefox, Safari, Edge）

### 環境チェック
```bash
# Node.jsバージョン確認
node -v

# npmバージョン確認
npm -v

# ポート確認
npm run check-port
```

## 📱 ブラウザ別の注意点

### Chrome
- 動画の自動再生が制限される場合があります
- ユーザーが手動で再生ボタンをクリックする必要があります

### Firefox
- 一部の動画形式で問題が発生する場合があります
- MP4形式を推奨します

### Safari
- 古いバージョンでは一部機能が動作しない場合があります
- 最新版の使用を推奨します

## 🆘 それでも解決しない場合

1. **ログを確認**
   ```bash
   npm run dev 2>&1 | tee debug.log
   ```

2. **完全リセット**
   ```bash
   npm run clean
   npm run setup
   ```

3. **GitHubのIssuesで報告**
   - エラーメッセージの全文
   - 使用しているOSとブラウザ
   - Node.jsとnpmのバージョン
   - 実行したコマンド

## 📞 サポート

問題が解決しない場合は、以下の情報と一緒にサポートに連絡してください：

- OS: (Windows/macOS/Linux)
- Node.jsバージョン: `node -v`
- npmバージョン: `npm -v`
- ブラウザ: (Chrome/Firefox/Safari/Edge)
- エラーメッセージの全文
- 実行したコマンドの履歴
