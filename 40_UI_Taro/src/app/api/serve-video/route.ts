import { NextRequest } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

// OPTIONSリクエストに対応
export async function OPTIONS() {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
      'Access-Control-Allow-Headers': 'Range',
    },
  });
}

// 参考動画を安全に配信するAPI（Range対応）
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const rel = searchParams.get('rel');

    if (!rel) {
      return new Response(JSON.stringify({ error: 'Missing rel parameter' }), { status: 400 });
    }

    // 許可ディレクトリのホワイトリスト
    const ALLOWED_PREFIXES = [
      'tennis_videos/Cleaned_Data/',
      '40_UI_Taro/public/clipped-videos/',
    ];

    if (!ALLOWED_PREFIXES.some((p) => rel.startsWith(p))) {
      return new Response(JSON.stringify({ error: 'Access denied' }), { status: 403 });
    }

    // Next.jsアプリ直下から一つ上がプロジェクトルート
    const projectRoot = path.join(process.cwd(), '..');
    const fullPath = path.join(projectRoot, rel);
    
    console.log('serve-video API:', { rel, projectRoot, fullPath });

    // パスのサニタイズ（ディレクトリトラバーサル対策）
    const normalized = path.normalize(fullPath);
    if (!normalized.startsWith(path.join(projectRoot, path.dirname(rel.split('/')[0])))) {
      return new Response(JSON.stringify({ error: 'Invalid path' }), { status: 400 });
    }

    if (!fs.existsSync(normalized)) {
      return new Response(JSON.stringify({ error: 'File not found' }), { status: 404 });
    }

    const stat = fs.statSync(normalized);
    const fileSize = stat.size;
    const range = req.headers.get('range');

        // 動画ファイルの拡張子に基づいてContent-Typeを設定
        const ext = path.extname(normalized).toLowerCase();
        let contentType = 'video/mp4';
        
        if (ext === '.mp4') {
          contentType = 'video/mp4';
        } else if (ext === '.webm') {
          contentType = 'video/webm';
        } else if (ext === '.ogg') {
          contentType = 'video/ogg';
        }

    if (range) {
      // Range request handling
      const parts = range.replace(/bytes=/, '').split('-');
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;

      if (isNaN(start) || isNaN(end) || start > end || end >= fileSize) {
        return new Response(JSON.stringify({ error: 'Invalid range' }), { status: 416 });
      }

          const chunkSize = end - start + 1;
          const fileBuffer = fs.readFileSync(normalized);
          const chunk = fileBuffer.slice(start, end + 1);

          return new Response(chunk, {
            status: 206,
            headers: {
              'Content-Range': `bytes ${start}-${end}/${fileSize}`,
              'Accept-Ranges': 'bytes',
              'Content-Length': String(chunkSize),
              'Content-Type': contentType,
              'Cache-Control': 'no-store',
              'Access-Control-Allow-Origin': '*',
              'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
              'Access-Control-Allow-Headers': 'Range',
            },
          });
    }

        // Full content
        const fileBuffer = fs.readFileSync(normalized);
        return new Response(fileBuffer, {
          status: 200,
          headers: {
            'Content-Length': String(fileSize),
            'Content-Type': contentType,
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'no-store',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': 'Range',
          },
        });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err?.message || 'Internal error' }), { status: 500 });
  }
}


