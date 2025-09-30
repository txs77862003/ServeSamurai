import { NextRequest, NextResponse } from 'next/server';
import formidable from 'formidable';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

const writeFile = promisify(fs.writeFile);
const mkdir = promisify(fs.mkdir);

export async function POST(request: NextRequest): Promise<Response> {
  try {
    console.log('API: クリッピングリクエスト開始');
    
    // フォームデータを解析
    const formData = await request.formData();
    
    const videoFile = formData.get('video') as File;
    const segmentsData = formData.get('segments') as string;

    console.log('API: 動画ファイル:', videoFile ? `${videoFile.name} (${videoFile.size} bytes)` : 'なし');
    console.log('API: セグメントデータ:', segmentsData);

    if (!videoFile) {
      console.log('API: エラー - 動画ファイルがアップロードされていません');
      return NextResponse.json({ error: '動画ファイルがアップロードされていません' }, { status: 400 });
    }

    if (!segmentsData) {
      console.log('API: エラー - セグメントが指定されていません');
      return NextResponse.json({ error: 'セグメントが指定されていません' }, { status: 400 });
    }

    const segments = JSON.parse(segmentsData);
    console.log('API: パースされたセグメント:', segments);

    if (!segments || segments.length === 0) {
      console.log('API: エラー - セグメントが空です');
      return NextResponse.json({ error: 'セグメントが指定されていません' }, { status: 400 });
    }

    // 出力ディレクトリを作成
    const outputDir = path.join(process.cwd(), 'public', 'clipped-videos');
    await mkdir(outputDir, { recursive: true });
    console.log('API: 出力ディレクトリ作成:', outputDir);

    // 一時ファイルとして保存
    const tempDir = path.join(process.cwd(), 'tmp');
    await mkdir(tempDir, { recursive: true });
    
    // ファイル名をサニタイズ（スペースをアンダースコアに置換）
    const sanitizedFileName = videoFile.name.replace(/[^a-zA-Z0-9.-]/g, '_');
    const tempFilePath = path.join(tempDir, `temp_${Date.now()}_${sanitizedFileName}`);
    console.log('API: 一時ファイルパス:', tempFilePath);
    
    const buffer = await videoFile.arrayBuffer();
    console.log('API: 動画ファイルバッファサイズ:', buffer.byteLength);
    
    await writeFile(tempFilePath, Buffer.from(buffer));
    console.log('API: 一時ファイル保存完了');

    // 動画クリッピング処理
    console.log('API: クリッピング処理開始');
    const clippedVideos = await clipVideoSegments(tempFilePath, segments, outputDir);
    console.log('API: クリッピング処理完了:', clippedVideos);

    // 一時ファイルを削除
    fs.unlinkSync(tempFilePath);

    return NextResponse.json({
      success: true,
      clippedVideos,
      message: `${clippedVideos.length}個の動画が切り取られました`,
    });

  } catch (error) {
    console.error('動画クリッピングエラー:', error);
    return NextResponse.json({ error: '動画クリッピングに失敗しました' }, { status: 500 });
  }
}

async function clipVideoSegments(
  videoPath: string,
  segments: Array<{ start: number; end: number }>,
  outputDir: string
): Promise<Array<{ filename: string; path: string; duration: number }>> {
  const { spawn } = require('child_process');
  
  const clippedVideos = [];
  console.log('clipVideoSegments: 処理開始, セグメント数:', segments.length);

  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    const outputFilename = `serve_${i + 1}_${Math.floor(segment.start)}_${Math.floor(segment.end)}.mp4`;
    const outputPath = path.join(outputDir, outputFilename);

    console.log(`clipVideoSegments: セグメント ${i + 1} 処理開始`, {
      start: segment.start,
      end: segment.end,
      duration: segment.end - segment.start,
      outputPath
    });

    try {
      // ffmpegを使用して動画を切り取り
      await new Promise<void>((resolve, reject) => {
        const duration = (segment.end - segment.start).toString();
        // QuickTime 冒頭の黒画面対策: 正確シーク + 再エンコード + faststart + 30fps
        const ffmpegArgs = [
          '-ss', segment.start.toString(),
          '-i', videoPath,
          '-t', duration,
          '-vf', 'fps=30',
          '-c:v', 'libx264',
          '-preset', 'veryfast',
          '-crf', '18',
          '-pix_fmt', 'yuv420p',
          '-movflags', '+faststart',
          '-an',
          '-avoid_negative_ts', 'make_zero',
          '-y',
          outputPath
        ];
        
        console.log('clipVideoSegments: ffmpeg実行:', ffmpegArgs);
        
        const ffmpeg = spawn('ffmpeg', ffmpegArgs);
        
        // タイムアウトを設定（30秒）
        const timeout = setTimeout(() => {
          console.error(`clipVideoSegments: ffmpegタイムアウト (30秒)`);
          ffmpeg.kill('SIGTERM');
          reject(new Error('ffmpeg timeout after 30 seconds'));
        }, 30000);

        let stderr = '';
        
        ffmpeg.stderr.on('data', (data: Buffer) => {
          stderr += data.toString();
        });

        ffmpeg.on('close', (code: number) => {
          clearTimeout(timeout);
          console.log(`clipVideoSegments: ffmpeg終了コード: ${code}`);
          if (code === 0) {
            console.log(`clipVideoSegments: セグメント ${i + 1} 処理完了`);
            resolve(void 0);
          } else {
            console.error(`clipVideoSegments: ffmpegエラー出力: ${stderr}`);
            reject(new Error(`ffmpeg exited with code ${code}: ${stderr}`));
          }
        });

        ffmpeg.on('error', (err: Error) => {
          clearTimeout(timeout);
          console.error(`clipVideoSegments: ffmpegプロセスエラー:`, err);
          reject(err);
        });
      });

      clippedVideos.push({
        filename: outputFilename,
        path: `/clipped-videos/${outputFilename}`,
        duration: segment.end - segment.start,
      });

    } catch (error) {
      console.error(`セグメント ${i + 1} の切り取りに失敗:`, error);
    }
  }

  return clippedVideos;
}
