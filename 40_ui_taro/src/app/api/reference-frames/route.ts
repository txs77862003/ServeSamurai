import { NextRequest, NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs/promises';
import fsSync from 'fs';

import { getProjectRoot } from '../_utils/python';

const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png']);

async function ensureDirectory(dir: string) {
  await fs.mkdir(dir, { recursive: true });
}

async function copyFrame(source: string, destination: string) {
  try {
    const [srcStat, dstStat] = await Promise.all([
      fs.stat(source),
      fs.stat(destination).catch(() => null),
    ]);
    if (!dstStat || srcStat.mtimeMs > dstStat.mtimeMs) {
      await fs.copyFile(source, destination);
    }
  } catch {
    await fs.copyFile(source, destination);
  }
}

export async function POST(request: NextRequest): Promise<Response> {
  try {
    const body = await request.json();
    const frameDirRelative = (body?.frameDirRelative as string | undefined)?.trim();
    const slug = (body?.slug as string | undefined)?.trim();

    if (!frameDirRelative || !slug) {
      return NextResponse.json({
        success: false,
        error: 'frameDirRelative と slug は必須です',
      }, { status: 400 });
    }

    const projectRoot = getProjectRoot();
    const sourceDir = path.join(projectRoot, frameDirRelative);

    if (!sourceDir.startsWith(projectRoot)) {
      return NextResponse.json({
        success: false,
        error: 'frameDirRelative が無効です',
      }, { status: 400 });
    }

    let entries: fsSync.Dirent[];
    try {
      entries = await fs.readdir(sourceDir, { withFileTypes: true });
    } catch (error) {
      return NextResponse.json({
        success: false,
        error: 'フレームディレクトリを読み込めません',
        details: error instanceof Error ? error.message : String(error),
      }, { status: 404 });
    }

    const images = entries
      .filter((entry) => entry.isFile() && IMAGE_EXTENSIONS.has(path.extname(entry.name).toLowerCase()))
      .map((entry) => entry.name)
      .sort();

    if (images.length === 0) {
      return NextResponse.json({
        success: false,
        error: 'フレーム画像が見つかりません',
      }, { status: 404 });
    }

    const destDir = path.join(process.cwd(), 'public', 'pose-reference', slug, 'frames');
    await ensureDirectory(destDir);

    const framePaths: string[] = [];
    for (const name of images) {
      const src = path.join(sourceDir, name);
      const dest = path.join(destDir, name);
      await copyFrame(src, dest);
      framePaths.push(`/pose-reference/${slug}/frames/${name}`);
    }

    return NextResponse.json({
      success: true,
      frames: framePaths,
    });
  } catch (error) {
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : '不明なエラーが発生しました',
    }, { status: 500 });
  }
}
