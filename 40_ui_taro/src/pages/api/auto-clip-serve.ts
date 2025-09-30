import { NextApiRequest, NextApiResponse } from 'next'
import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { videoPath, outputDir } = req.body

    if (!videoPath) {
      return res.status(400).json({ error: 'videoPath is required' })
    }

    // サーブ自動切り取りスクリプトのパス
    const scriptPath = path.join(process.cwd(), '..', 'tmp_auto_clip_taro', 'serve_auto_clipper.py')
    
    // スクリプトが存在するかチェック
    if (!fs.existsSync(scriptPath)) {
      return res.status(500).json({ 
        error: 'Serve auto clipper script not found',
        path: scriptPath 
      })
    }

    // 動画ファイルが存在するかチェック
    if (!fs.existsSync(videoPath)) {
      return res.status(400).json({ 
        error: 'Video file not found',
        path: videoPath 
      })
    }

    // Pythonプロセスを起動
    const pythonProcess = spawn('python3', [
      scriptPath,
      videoPath,
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

    if (exitCode !== 0) {
      console.error('Serve auto clipper error:', errorOutput)
      return res.status(500).json({ 
        error: 'Serve auto clipping failed',
        details: errorOutput,
        output: output
      })
    }

    // 出力ディレクトリから結果ファイルを探す
    const videoName = path.basename(videoPath, path.extname(videoPath))
    const defaultOutputDir = path.join(path.dirname(videoPath), `${videoName}_processed`)
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
    console.error('Auto clip API error:', error)
    return res.status(500).json({ 
      error: 'Internal server error',
      details: error instanceof Error ? error.message : String(error)
    })
  }
}
