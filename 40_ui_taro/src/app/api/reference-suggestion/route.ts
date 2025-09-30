import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs/promises';

import { buildReferenceSuggestions, makeSlug } from '../_utils/referenceSuggestion';
import { getProjectRoot, resolvePythonCommand } from '../_utils/python';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const userCsvInput = (body?.userCsv as string | undefined)?.trim();

    if (!userCsvInput) {
      return NextResponse.json({
        success: false,
        error: 'userCsv を指定してください',
      }, { status: 400 });
    }

    const projectRoot = getProjectRoot();
    const pythonCmd = resolvePythonCommand();
    const previewOutputDir = path.join(process.cwd(), 'public', 'pose-reference');

    const csvPath = path.isAbsolute(userCsvInput)
      ? userCsvInput
      : path.join(projectRoot, userCsvInput);

    try {
      await fs.access(csvPath);
    } catch {
      return NextResponse.json({
        success: false,
        error: '指定された userCsv が見つかりません',
        csvPath,
      }, { status: 404 });
    }

    const inferPath = path.join(projectRoot, '30_Classification_LSTM', 'infer_similarity.py');
    const modelPath = path.join(projectRoot, '30_Classification_LSTM', 'best_augmented_model.pth');

    const inferArgs = [inferPath, '--csv', csvPath, '--model', modelPath];
    const py = spawn(pythonCmd, inferArgs);

    let stdout = '';
    let stderr = '';

    py.stdout.on('data', (d) => {
      stdout += d.toString();
    });
    py.stderr.on('data', (d) => {
      stderr += d.toString();
    });

    await new Promise<void>((resolve) => py.on('close', () => resolve()));

    if (!stdout) {
      return NextResponse.json({
        success: false,
        error: 'infer_similarity.py からの出力が空でした',
        stderr,
      }, { status: 500 });
    }

    let similarity: any = null;
    try {
      similarity = JSON.parse(stdout);
    } catch (error) {
      return NextResponse.json({
        success: false,
        error: '類似度推論結果のパースに失敗しました',
        raw: stdout,
        stderr,
      }, { status: 500 });
    }

    if (!similarity || !similarity.top1 || !similarity.top1.player) {
      return NextResponse.json({
        success: false,
        error: 'トップ候補の選手を特定できませんでした',
        similarity,
      }, { status: 500 });
    }

    let referenceSuggestions: any[] | null = null;
    try {
      const suggestions = await buildReferenceSuggestions(
        similarity.top1.player,
        projectRoot,
        previewOutputDir,
      );
      if (suggestions.length > 0) {
        referenceSuggestions = suggestions.map((item) => ({
          ...item,
          confidence: similarity.top1.score ?? undefined,
        }));
      }
    } catch (error) {
      referenceSuggestions = null;
    }

    const csvDir = path.dirname(csvPath);
    const clipName = path.basename(csvDir);
    const userFrameDirCandidates = [
      path.join(projectRoot, 'frames', 'Cleaned_data', 'players', 'User', clipName),
      path.join(projectRoot, 'frames', 'Cleaned_Data', 'players', 'User', clipName),
      path.join(projectRoot, 'frames', 'players', 'User', clipName),
    ];
    let userFrameDir: string | null = null;
    for (const candidate of userFrameDirCandidates) {
      try {
        const stat = await fs.stat(candidate);
        if (stat.isDirectory()) {
          userFrameDir = candidate;
          break;
        }
      } catch {
        continue;
      }
    }

    return NextResponse.json({
      success: true,
      similarity,
      referenceSuggestions,
      userCsv: path.relative(projectRoot, csvPath).split(path.sep).join('/'),
      userClip: {
        clipName,
        frameDirRelative: userFrameDir
          ? path.relative(projectRoot, userFrameDir).split(path.sep).join('/')
          : undefined,
        slug: makeSlug('User', clipName),
      },
    });
  } catch (error) {
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : '不明なエラーが発生しました',
    }, { status: 500 });
  }
}
