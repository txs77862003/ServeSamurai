import { NextApiRequest, NextApiResponse } from 'next'
import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs'
import formidable from 'formidable'

export const config = {
  api: {
    bodyParser: false,
  },
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    // アップロードディレクトリを作成
    const uploadDir = '/tmp/auto_clip_uploads'
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true })
    }

    // フォームデータを解析
    const form = formidable({
      uploadDir: uploadDir,
      keepExtensions: true,
      maxFileSize: 500 * 1024 * 1024, // 500MB
    })

    const [fields, files] = await form.parse(req)
    
    const videoFile = Array.isArray(files.video) ? files.video[0] : files.video
    const outputDir = Array.isArray(fields.outputDir) ? fields.outputDir[0] : fields.outputDir

    if (!videoFile) {
      return res.status(400).json({ error: 'No video file uploaded' })
    }

    const videoPath = videoFile.filepath
    const originalName = videoFile.originalFilename || 'uploaded_video.mp4'
    
    // ファイル名を変更（拡張子を保持）
    const ext = path.extname(originalName)
    const newFileName = `upload_${Date.now()}${ext}`
    const newVideoPath = path.join(uploadDir, newFileName)
    
    fs.renameSync(videoPath, newVideoPath)

    // サーブ自動切り取りスクリプトのパス
    const scriptPath = path.join(process.cwd(), '..', 'tmp_auto_clip_taro', 'serve_auto_clipper.py')
    
    // スクリプトが存在するかチェック
    if (!fs.existsSync(scriptPath)) {
      // 一時ファイルを削除
      fs.unlinkSync(newVideoPath)
      return res.status(500).json({ 
        error: 'Serve auto clipper script not found',
        path: scriptPath 
      })
    }

    // Pythonプロセスを起動
    const pythonProcess = spawn('python3', [
      scriptPath,
      newVideoPath,
      ...(outputDir ? [outputDir] : [])
    ], {
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let output = ''
    let errorOutput = ''

    // 出力を収集
    pythonProcess.stdout.on('data', (data) => {
      output += data.toString()
    })

    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data.toString()
    })

    // プロセス完了を待機
    const exitCode = await new Promise<number>((resolve) => {
      pythonProcess.on('close', (code) => {
        resolve(code || 0)
      })
    })

    // 一時ファイルを削除
    try {
      fs.unlinkSync(newVideoPath)
    } catch (cleanupError) {
      console.warn('Failed to cleanup temporary file:', cleanupError)
    }

    if (exitCode !== 0) {
      console.error('Serve auto clipper error:', errorOutput)
      return res.status(500).json({ 
        error: 'Serve auto clipping failed',
        details: errorOutput,
        output: output
      })
    }

    // 出力ディレクトリから結果ファイルを探す
    const videoName = path.basename(newFileName, path.extname(newFileName))
    const defaultOutputDir = path.join(uploadDir, `${videoName}_processed`)
    const resultOutputDir = outputDir || defaultOutputDir
    
    // 結果JSONファイルを読み込み
    const resultFile = path.join(resultOutputDir, 'processing_result.json')
    
    if (fs.existsSync(resultFile)) {
      try {
        const resultData = JSON.parse(fs.readFileSync(resultFile, 'utf-8'))
        
        // 切り取られた動画ファイルの存在を確認
        const validVideos = resultData.clipped_videos.filter((video: any) => 
          fs.existsSync(video.path)
        )
        
        resultData.clipped_videos = validVideos
        resultData.total_serves = validVideos.length
        
        return res.status(200).json({
          success: true,
          result: resultData,
          output: output
        })
      } catch (parseError) {
        console.error('Failed to parse result file:', parseError)
        return res.status(500).json({ 
          error: 'Failed to parse processing result',
          output: output
        })
      }
    } else {
      return res.status(500).json({ 
        error: 'Processing result file not found',
        output: output
      })
    }

  } catch (error) {
    console.error('Upload and clip API error:', error)
    return res.status(500).json({ 
      error: 'Internal server error',
      details: error instanceof Error ? error.message : String(error)
    })
  }
}
