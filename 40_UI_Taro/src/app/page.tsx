"use client"

import Link from "next/link"
import React, { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import UploadDropzone from "@/components/UploadDropzone"
import StepIndicator from "@/components/StepIndicator"

export default function Home() {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const router = useRouter()

  // Revoke object URLs when replaced
  useEffect(() => {
    return () => {
      if (videoUrl?.startsWith("blob:")) URL.revokeObjectURL(videoUrl)
    }
  }, [videoUrl])

  const onVideoReady = useCallback((file: File, url: string) => {
    setVideoFile(file)
    setVideoUrl(url)
    setFileName(file.name)
  }, [])

  const proceedToClipping = useCallback(async () => {
    if (videoFile && videoUrl) {
      console.log('proceedToClipping - Starting base64 conversion for file:', videoFile.name, 'size:', videoFile.size)
      
      try {
        // File をBase64エンコードして保存（チャンク方式で安全に処理）
        const arrayBuffer = await videoFile.arrayBuffer()
        console.log('proceedToClipping - ArrayBuffer size:', arrayBuffer.byteLength)
        
        const uint8Array = new Uint8Array(arrayBuffer)
        let binaryString = ''
        const chunkSize = 8192 // 8KB chunks
        
        for (let i = 0; i < uint8Array.length; i += chunkSize) {
          const chunk = uint8Array.subarray(i, i + chunkSize)
          binaryString += String.fromCharCode(...chunk)
        }
        
        const base64 = btoa(binaryString)
        console.log('proceedToClipping - Base64 length:', base64.length)
        
        const fileData = {
          name: videoFile.name,
          size: videoFile.size,
          type: videoFile.type,
          data: base64
        }
        
        // 動画データをsessionStorageに保存
        sessionStorage.setItem('uploadedVideoFile', JSON.stringify(fileData))
        sessionStorage.setItem('uploadedFileName', fileName || '')
        
        console.log('proceedToClipping - Saved to sessionStorage:', fileData.name, 'with base64 data')
        
        // クリッピング画面に遷移
        router.push('/manual-clip')
      } catch (error) {
        console.error('Error converting video to base64:', error)
        // フォールバック: 元の方法を使用
        sessionStorage.setItem('uploadedVideoFile', JSON.stringify({
          name: videoFile.name,
          size: videoFile.size,
          type: videoFile.type
        }))
        sessionStorage.setItem('uploadedVideoUrl', videoUrl)
        sessionStorage.setItem('uploadedFileName', fileName || '')
        router.push('/manual-clip')
      }
    }
  }, [videoFile, videoUrl, fileName, router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">
      <section className="container mx-auto max-w-4xl px-6 py-12">
        <StepIndicator currentStep={1} />
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 mb-4">
            🎾 Tennis Serve Analyzer
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            テニスのサーブ動画をアップロードして、プロ選手との比較分析を行います
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          {/* メインアップロードエリア */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="shadow-lg">
              <CardHeader>
                <CardTitle className="text-2xl">📹 動画アップロード</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <UploadDropzone onVideoReady={onVideoReady} />
                
                {fileName && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-green-800 font-medium">
                      ✓ 動画が選択されました: {fileName}
                    </p>
                  </div>
                )}

                <div className="flex justify-center">
                  <Button 
                    onClick={proceedToClipping}
                    disabled={!videoFile}
                    size="lg"
                    className="px-8 py-3 text-lg"
                  >
                    Next: Clip Video →
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* サイドバー */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>📋 分析の流れ</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold">1</div>
                  <div>
                    <p className="font-medium">動画アップロード</p>
                    <p className="text-gray-600">テニスサーブの動画を選択</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-gray-100 text-gray-600 rounded-full flex items-center justify-center font-bold">2</div>
                  <div>
                    <p className="font-medium">手動クリッピング</p>
                    <p className="text-gray-600">サーブ部分を正確に切り取り</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-gray-100 text-gray-600 rounded-full flex items-center justify-center font-bold">3</div>
                  <div>
                    <p className="font-medium">結果表示</p>
                    <p className="text-gray-600">プロ選手との比較分析</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>🏆 比較対象</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 gap-3">
                  {[
                    { name: "錦織圭", flag: "🇯🇵" },
                    { name: "フェデラー", flag: "🇨🇭" },
                    { name: "ジョコビッチ", flag: "🇷🇸" },
                    { name: "アルカラス", flag: "🇪🇸" }
                  ].map((player, i) => (
                    <div key={i} className="flex items-center gap-3 p-2 bg-gray-50 rounded">
                      <span className="text-2xl">{player.flag}</span>
                      <span className="font-medium">{player.name}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </div>
  )
}