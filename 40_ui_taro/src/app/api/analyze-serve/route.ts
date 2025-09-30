import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs/promises';
import fsSync from 'fs';

import { buildReferenceSuggestions, makeSlug } from '../_utils/referenceSuggestion';
import { getProjectRoot, resolvePythonCommand } from '../_utils/python';

async function directoryExists(target: string): Promise<boolean> {
  try {
    const stat = await fs.stat(target);
    return stat.isDirectory();
  } catch {
    return false;
  }
}

export async function POST(request: NextRequest) {
  try {
    console.log('API: 分析リクエスト開始');
    
    const raw = await request.text();
    console.log('API: 受信したraw:', raw);
    let body: any = {};
    try {
      body = raw ? JSON.parse(raw) : {};
    } catch (e) {
      console.warn('API: JSON parse失敗。rawを返します');
      return NextResponse.json({ error: 'Invalid JSON', raw }, { status: 400 });
    }
    console.log('API: 受信したボディ:', body);

    let { videoPath, segments, videoData } = body as { videoPath?: string; segments?: any[]; videoData?: string };
    
    console.log('API: 動画パス:', videoPath);
    console.log('API: セグメント:', segments);
    console.log('API: 動画データ:', videoData ? `Base64 data (${videoData.length} chars)` : 'なし');

    // videoPathとsegments、またはvideoDataのいずれかが必要
    if (!videoPath && !videoData) {
      return NextResponse.json({ 
        error: '動画パスまたは動画データが必要です' 
      }, { status: 400 });
    }

    if (!segments || segments.length === 0) {
      return NextResponse.json({ 
        error: 'セグメントが必要です' 
      }, { status: 400 });
    }

    // videoDataのみ提供された場合、/tmpに一時ファイルを書き出してvideoPathに置換
    let tempFilePath: string | null = null;
    if (!videoPath && videoData) {
      try {
        console.log('API: videoDataを一時ファイルに保存します');
        const sanitized = Date.now().toString(36) + '_' + Math.random().toString(36).slice(2);
        tempFilePath = `/tmp/analyze_${sanitized}.mp4`;
        const buffer = Buffer.from(videoData, 'base64');
        await fs.writeFile(tempFilePath, buffer);
        videoPath = tempFilePath;
        console.log('API: 一時ファイル作成:', tempFilePath, 'size:', buffer.length);
      } catch (e) {
        console.error('API: videoData保存エラー', e);
        return NextResponse.json({ error: '動画データの保存に失敗しました' }, { status: 500 });
      }
    }

    // Pythonスクリプトを起動
    const projectRoot = getProjectRoot();
    const previewOutputDir = path.join(process.cwd(), 'public', 'pose-reference');
    const scriptPath = path.join(process.cwd(), 'src', 'app', 'api', 'analyze-serve', 'analyze_serve.py');
    const pythonCmd = resolvePythonCommand();
    console.log('API: 選択されたPython:', pythonCmd);
    console.log('API: CWD:', process.cwd());
    console.log('API: analyze_serve.py パス:', scriptPath);
    const py = spawn(pythonCmd, [scriptPath], {
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });
    const payload = JSON.stringify({ videoPath, segments });
    console.log('API: Pythonへ送信するpayload:', payload);

    return await new Promise<NextResponse>((resolve) => {
      let stdout = '';
      let stderr = '';
      const timeoutMs = 20000; // 20s timeout
      const timer = setTimeout(() => {
        try { py.kill('SIGKILL'); } catch {}
      }, timeoutMs);
      let clipName: string | null = null;

      py.stdout.on('data', (d) => {
        const s = d.toString();
        stdout += s;
        for (const line of s.split(/\r?\n/)) {
          if (line) console.log('[py][stdout]', line);
        }
      });
      py.stderr.on('data', (d) => {
        const s = d.toString();
        stderr += s;
        for (const line of s.split(/\r?\n/)) {
          if (line) console.warn('[py][stderr]', line);
        }
      });

      py.on('close', async (code) => {
        clearTimeout(timer);
        console.log('Python exit code:', code);
        console.log('API: Python stdout bytes:', Buffer.byteLength(stdout, 'utf8'));
        console.log('API: Python stderr bytes:', Buffer.byteLength(stderr, 'utf8'));
        // 後始末: 一時ファイルがあれば削除
        if (tempFilePath) {
          try { await fs.unlink(tempFilePath); console.log('API: 一時ファイル削除:', tempFilePath); } catch {}
        }
        if (stderr) console.warn('Python stderr:', stderr);
        try {
          const parsed = JSON.parse(stdout || '{}');
          if (parsed && parsed.success) {
            // 追加: 単体YOLO + 最活性抽出（必要時）→ 類似度推論
            try {
            let userCsvRelative: string | null = null;              // 1) videoPathがpublic配下の相対パスなら絶対化
              if (videoPath && videoPath.startsWith('/')) {
                const publicDir = path.resolve(process.cwd(), 'public');
                const absVideo = path.join(publicDir, videoPath.replace(/^\/+/, ''));
                console.log('API: 解決された動画の絶対パス:', absVideo);
                try {
                  await fs.access(absVideo);
                  console.log('API: 動画ファイル存在OK');
                  // 2) クリップ名を抽出し、単体YOLOを実行
                  clipName = path.basename(absVideo, path.extname(absVideo));
                  const singleRunner = path.join(projectRoot, '22_Joint_Detection_YOLO', 'run_yolo_single.py');
                  const singleArgs = [singleRunner, '--clip-name', clipName, '--player', 'User', '--video', absVideo, '--run-active-track'];
                  console.log('API: run_yolo_single 実行:', pythonCmd, singleArgs.join(' '));
                  const pySingle = spawn(pythonCmd, singleArgs);
                  let srOut = '';
                  let srErr = '';
                  pySingle.stdout.on('data', (d) => {
                    const s = d.toString();
                    srOut += s;
                    for (const line of s.split(/\r?\n/)) {
                      if (line) console.log('[single][stdout]', line);
                    }
                  });
                  pySingle.stderr.on('data', (d) => {
                    const s = d.toString();
                    srErr += s;
                    for (const line of s.split(/\r?\n/)) {
                      if (line) console.warn('[single][stderr]', line);
                    }
                  });
                  await new Promise<void>((res) => pySingle.on('close', () => res()));
                  console.log('API: run_yolo_single 終了。stdout bytes:', Buffer.byteLength(srOut, 'utf8'), 'stderr bytes:', Buffer.byteLength(srErr, 'utf8'));
                } catch {}
              }

              // 3) ユーザーのCSVを最優先で使用（新標準: pose_tracks/players）。無ければ旧パス(Cleaned_Data)を試し、なければエラー
              const poseTracksBaseNew = path.join(projectRoot, 'pose_tracks', 'players');
              const poseTracksBaseLegacy = path.join(projectRoot, 'pose_tracks', 'Cleaned_Data', 'players');
              if (!clipName) {
                console.warn('API: clipName 未確定のためユーザーCSVを参照できません');
                return resolve(NextResponse.json({ success: false, error: 'clipNameを特定できませんでした' }, { status: 400 }));
              }
                return;              const userCsvNew = path.join(poseTracksBaseNew, 'User', clipName, 'keypoints_with_tracks.csv');
              const userCsvLegacy = path.join(poseTracksBaseLegacy, 'User', clipName, 'keypoints_with_tracks.csv');
              let csvCandidate: string | null = null;
                path.join(projectRoot, 'frames', 'Cleaned_data', 'players', 'User', clipName),
                path.join(projectRoot, 'frames', 'Cleaned_Data', 'players', 'User', clipName),
                path.join(projectRoot, 'frames', 'players', 'User', clipName),
              ];
              let userFrameDir: string | null = null;
              for (const candidate of userFrameDirCandidates) {
                if (await directoryExists(candidate)) {
                  userFrameDir = candidate;
                  break;
                }
              }
              const userClipInfo = {
                clipName,
                frameDirRelative: userFrameDir
                  ? path.relative(projectRoot, userFrameDir).split(path.sep).join('/')
                  : undefined,
                slug: makeSlug('User', clipName),
              };
              try {
                await fs.access(userCsvNew);
                csvCandidate = userCsvNew;
                userCsvRelative = path.relative(projectRoot, userCsvNew).split(path.sep).join('/');
                console.log('API: 類似度推論のCSV候補(新標準):', csvCandidate);
              } catch {
                try {
                  await fs.access(userCsvLegacy);
                  csvCandidate = userCsvLegacy;
                  userCsvRelative = path.relative(projectRoot, userCsvLegacy).split(path.sep).join('/');
                  console.log('API: 類似度推論のCSV候補(レガシー互換):', csvCandidate);
                } catch {
                  console.warn('API: ユーザーCSVが見つかりません:', userCsvNew, 'または', userCsvLegacy);
                  return resolve(NextResponse.json({ success: false, error: 'ユーザーのCSVが見つかりません', expected: userCsvNew, fallbackTried: userCsvLegacy }, { status: 404 }));
                }
              }
              const modelPath = path.join(projectRoot, '30_Classification_LSTM', 'best_augmented_model.pth');
              let similarity: any = null;
              if (csvCandidate) {
                const inferPath = path.join(projectRoot, '30_Classification_LSTM', 'infer_similarity.py');
                const inferArgs = [inferPath, '--csv', csvCandidate, '--model', modelPath];
                console.log('API: infer_similarity 実行:', pythonCmd, inferArgs.join(' '));
                const py2 = spawn(pythonCmd, inferArgs);
                let out2 = '';
                let err2 = '';
                py2.stdout.on('data', (d) => {
                  const s = d.toString();
                  out2 += s;
                  for (const line of s.split(/\r?\n/)) {
                    if (line) console.log('[infer][stdout]', line);
                  }
                });
                py2.stderr.on('data', (d) => {
                  const s = d.toString();
                  err2 += s;
                  for (const line of s.split(/\r?\n/)) {
                    if (line) console.warn('[infer][stderr]', line);
                  }
                });
                await new Promise<void>((res2) => py2.on('close', () => res2()));
                try { similarity = JSON.parse(out2); } catch {}
                if (!similarity) similarity = { error: 'parse_failed', raw: out2 };

                let referenceSuggestions: any[] | null = null;
                if (similarity && similarity.top1 && similarity.top1.player) {
                  try {
                    const suggestions = await buildReferenceSuggestions(
                      similarity.top1.player,
                      projectRoot,
                      previewOutputDir,
                    );
                    if (suggestions.length > 0) {
                      referenceSuggestions = suggestions.map((item) => ({
                        ...item,
                        confidence: typeof similarity.top1.score === 'number'
                          ? similarity.top1.score
                          : undefined,
                      }));
                    }
                  } catch (suggestErr) {
                    console.warn('API: reference suggestion failed:', suggestErr);
                  }
                }

                if (similarity && similarity.probabilities) {
                  console.log('API: 類似度詳細:');
                  const probs = similarity.probabilities as Record<string, number>;
                  for (const [player, score] of Object.entries(probs)) {
                    console.log(`  - ${player}: ${score.toFixed(4)}`);
                  }
                  if (similarity.top1) {
                    console.log(`API: 類似度Top1: ${similarity.top1.player} (${Number(similarity.top1.score).toFixed(4)})`);
                  }
                }

                if (err2) console.warn('infer stderr (bytes):', Buffer.byteLength(err2, 'utf8'));
                resolve(NextResponse.json({ ...parsed, similarity, referenceSuggestions, userCsv: userCsvRelative || null, userClip: userClipInfo }));
                return;
              }
              resolve(NextResponse.json({ ...parsed, similarity: null, referenceSuggestions: null, userCsv: userCsvRelative || null, userClip: userClipInfo }));
              return;
            } catch (e) {
              console.warn('similarity inference skipped:', e);
              resolve(NextResponse.json({ ...parsed, referenceSuggestions: null, userCsv: userCsvRelative || null, userClip: userClipInfo }));
              return;
            }
          } else {
            resolve(NextResponse.json({ success: false, error: parsed?.error || 'Python returned no success', stdout, stderr, code }, { status: 500 }));
          }
        } catch (e: any) {
          resolve(NextResponse.json({ success: false, error: e?.message || 'Invalid Python JSON', stdout, stderr, code }, { status: 500 }));
        }
      });

      py.stdin.write(payload);
      py.stdin.end();
    });

  } catch (error) {
    console.error('API: 分析エラー:', error);
    return NextResponse.json({ 
      error: 'サーブ分析に失敗しました',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
// Force redeploy Tue Sep 30 13:54:05 JST 2025
