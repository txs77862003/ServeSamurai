import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const playerName = searchParams.get('player');

    if (!playerName) {
      return NextResponse.json({ error: 'Missing "player" parameter' }, { status: 400 });
    }

    // Next.jsアプリ直下から一つ上がプロジェクトルート
    const projectRoot = path.join(process.cwd(), '..');
    const videosDir = path.join(projectRoot, 'tennis_videos', 'Cleaned_Data', playerName);
    
    if (!fs.existsSync(videosDir)) {
      return NextResponse.json({ 
        videos: [],
        error: `Player directory not found: ${playerName}`
      });
    }

    // 動画ファイルを検索
    const files = fs.readdirSync(videosDir);
    const videoFiles = files
      .filter(file => file.endsWith('.mp4'))
      .map(file => ({
        filename: file,
        path: `tennis_videos/Cleaned_Data/${playerName}/${file}`,
        fullPath: path.join(videosDir, file)
      }))
      .sort((a, b) => a.filename.localeCompare(b.filename));

    return NextResponse.json({ 
      videos: videoFiles,
      player: playerName
    });

  } catch (error: any) {
    console.error('Video listing error:', error);
    return NextResponse.json(
      { error: error?.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
