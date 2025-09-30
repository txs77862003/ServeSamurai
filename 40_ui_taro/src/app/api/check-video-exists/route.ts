import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const rel = searchParams.get('rel');

    if (!rel) {
      return NextResponse.json({ error: 'Missing "rel" parameter' }, { status: 400 });
    }

    // 許可ディレクトリのホワイトリスト
    const ALLOWED_PREFIXES = [
      'tennis_videos/Cleaned_Data/',
      '40_UI_Taro/public/clipped-videos/',
    ];

    if (!ALLOWED_PREFIXES.some((p) => rel.startsWith(p))) {
      return NextResponse.json({ error: 'Access denied' }, { status: 403 });
    }

    // Next.jsアプリ直下から一つ上がプロジェクトルート
    const projectRoot = path.join(process.cwd(), '..');
    const fullPath = path.join(projectRoot, rel);
    
    // パスのサニタイズ（ディレクトリトラバーサル対策）
    const normalized = path.normalize(fullPath);
    if (!normalized.startsWith(path.join(projectRoot, path.dirname(rel.split('/')[0])))) {
      return NextResponse.json({ error: 'Invalid path' }, { status: 400 });
    }

    const exists = fs.existsSync(normalized);
    
    return NextResponse.json({ 
      exists,
      path: rel,
      fullPath: normalized
    });

  } catch (error: any) {
    console.error('Video existence check error:', error);
    return NextResponse.json(
      { error: error?.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
