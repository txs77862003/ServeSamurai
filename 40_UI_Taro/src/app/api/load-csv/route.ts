import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const csvPath = searchParams.get('path');

    console.log('CSV読み込みAPI - リクエストパス:', csvPath);

    if (!csvPath) {
      console.log('CSV読み込みAPI - エラー: パスが指定されていません');
      return NextResponse.json(
        { error: 'CSVパスが指定されていません' },
        { status: 400 }
      );
    }

    // プロジェクトルートを基準としたパス解決
    // 40_UI_Taroディレクトリから親ディレクトリ（Tennis Serve Analysis）に移動
    const projectRoot = path.join(process.cwd(), '..');
    const fullPath = path.join(projectRoot, csvPath);

    console.log('CSV読み込みAPI - プロジェクトルート:', projectRoot);
    console.log('CSV読み込みAPI - 完全パス:', fullPath);

    // セキュリティチェック: プロジェクトルート外へのアクセスを防ぐ
    if (!fullPath.startsWith(projectRoot)) {
      console.log('CSV読み込みAPI - エラー: 不正なパス');
      return NextResponse.json(
        { error: '不正なパスです' },
        { status: 400 }
      );
    }

    // ファイルの存在確認
    const fs = require('fs');
    if (!fs.existsSync(fullPath)) {
      console.log('CSV読み込みAPI - エラー: ファイルが存在しません:', fullPath);
      return NextResponse.json(
        { error: `CSVファイルが見つかりません: ${fullPath}` },
        { status: 404 }
      );
    }

    try {
      const csvContent = await readFile(fullPath, 'utf-8');
      console.log('CSV読み込みAPI - 成功: ファイルサイズ:', csvContent.length);
      return new NextResponse(csvContent, {
        headers: {
          'Content-Type': 'text/csv; charset=utf-8',
        },
      });
    } catch (fileError) {
      console.error('CSV読み込みAPI - ファイル読み込みエラー:', fileError);
      return NextResponse.json(
        { error: `CSVファイルの読み込みに失敗しました: ${fileError}` },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('CSV読み込みAPI - サーバーエラー:', error);
    return NextResponse.json(
      { error: `サーバーエラーが発生しました: ${error}` },
      { status: 500 }
    );
  }
}
