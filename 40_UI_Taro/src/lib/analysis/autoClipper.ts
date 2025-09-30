/**
 * サーブ動画の自動切り取り機能
 * LSTMで学習されたデータを利用してサーブの開始から終了までを自動的に検出・切り取り
 */

export type ServeSegment = {
  start_frame: number
  end_frame: number
  confidence: number
  predicted_class: number
}

export type ClippedVideo = {
  path: string
  start_frame: number
  end_frame: number
  start_time: number
  end_time: number
  confidence: number
  duration: number
}

export type ProcessingResult = {
  original_video: string
  processed_at: string
  serve_segments: ServeSegment[]
  clipped_videos: ClippedVideo[]
  total_serves: number
}

export type AutoClipResponse = {
  success: boolean
  result?: ProcessingResult
  error?: string
  details?: string
  output?: string
}

/**
 * サーブ動画の自動切り取りを実行
 * @param videoPath 処理する動画ファイルのパス
 * @param outputDir 出力ディレクトリ（オプション）
 * @returns 処理結果
 */
export async function autoClipServeVideo(
  videoPath: string, 
  outputDir?: string
): Promise<AutoClipResponse> {
  try {
    const response = await fetch('/api/auto-clip-serve', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        videoPath,
        outputDir
      })
    })

    const data = await response.json()

    if (!response.ok) {
      return {
        success: false,
        error: data.error || 'Unknown error',
        details: data.details,
        output: data.output
      }
    }

    return {
      success: true,
      result: data.result,
      output: data.output
    }

  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error',
      details: 'Failed to communicate with the server'
    }
  }
}

/**
 * 動画ファイルをアップロードして自動切り取りを実行
 * @param file アップロードされた動画ファイル
 * @param outputDir 出力ディレクトリ（オプション）
 * @returns 処理結果
 */
export async function uploadAndAutoClipServe(
  file: File,
  outputDir?: string
): Promise<AutoClipResponse> {
  try {
    // 一時ディレクトリにファイルを保存
    const tempDir = '/tmp/auto_clip_uploads'
    const fileName = `upload_${Date.now()}_${file.name}`
    const tempPath = `${tempDir}/${fileName}`

    // FormDataでファイルをアップロード
    const formData = new FormData()
    formData.append('video', file)
    formData.append('tempPath', tempPath)
    if (outputDir) {
      formData.append('outputDir', outputDir)
    }

    const response = await fetch('/api/upload-and-clip', {
      method: 'POST',
      body: formData
    })

    const data = await response.json()

    if (!response.ok) {
      return {
        success: false,
        error: data.error || 'Unknown error',
        details: data.details
      }
    }

    return {
      success: true,
      result: data.result,
      output: data.output
    }

  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Upload error',
      details: 'Failed to upload and process video'
    }
  }
}

/**
 * 処理結果を表示用にフォーマット
 * @param result 処理結果
 * @returns フォーマットされた文字列
 */
export function formatProcessingResult(result: ProcessingResult): string {
  let output = `サーブ動画自動切り取り結果\n`
  output += `元動画: ${result.original_video}\n`
  output += `処理日時: ${result.processed_at}\n`
  output += `検出されたサーブ数: ${result.total_serves}個\n\n`

  output += `切り取られたサーブ動画:\n`
  result.clipped_videos.forEach((video, index) => {
    output += `${index + 1}. ${video.path}\n`
    output += `   時間: ${video.start_time.toFixed(2)}s - ${video.end_time.toFixed(2)}s\n`
    output += `   信頼度: ${(video.confidence * 100).toFixed(1)}%\n`
    output += `   継続時間: ${video.duration.toFixed(2)}s\n\n`
  })

  return output
}

/**
 * 信頼度に基づいてサーブ動画をフィルタリング
 * @param result 処理結果
 * @param minConfidence 最小信頼度（0-1）
 * @returns フィルタリングされた結果
 */
export function filterByConfidence(
  result: ProcessingResult, 
  minConfidence: number
): ProcessingResult {
  const filteredVideos = result.clipped_videos.filter(
    video => video.confidence >= minConfidence
  )

  return {
    ...result,
    clipped_videos: filteredVideos,
    total_serves: filteredVideos.length
  }
}

/**
 * 処理進捗を監視するためのフック
 * @param onProgress 進捗更新時のコールバック
 * @returns 進捗監視の制御関数
 */
export function useProcessingProgress(onProgress: (progress: number, message: string) => void) {
  let isProcessing = false

  const startProcessing = () => {
    isProcessing = true
    onProgress(0, '処理を開始しています...')
  }

  const updateProgress = (progress: number, message: string) => {
    if (isProcessing) {
      onProgress(Math.min(100, Math.max(0, progress)), message)
    }
  }

  const endProcessing = () => {
    isProcessing = false
    onProgress(100, '処理が完了しました')
  }

  const cancelProcessing = () => {
    isProcessing = false
    onProgress(0, '処理がキャンセルされました')
  }

  return {
    startProcessing,
    updateProgress,
    endProcessing,
    cancelProcessing,
    isProcessing: () => isProcessing
  }
}

