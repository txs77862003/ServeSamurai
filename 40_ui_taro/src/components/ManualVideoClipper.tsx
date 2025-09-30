'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Trash2, Play, Pause, RotateCcw, Download, ArrowRight } from 'lucide-react';

interface Segment {
  start: number;
  end: number;
  duration: number;
}

interface ClippedVideo {
  filename: string;
  path: string;
  duration: number;
}

export default function ManualVideoClipper() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [videoDuration, setVideoDuration] = useState<number>(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [currentSegmentStart, setCurrentSegmentStart] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [clippedVideos, setClippedVideos] = useState<ClippedVideo[]>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const router = useRouter();

  // クリーンアップ時にBlob URLを解放
  useEffect(() => {
    return () => {
      if (videoUrl && videoUrl.startsWith('blob:')) {
        URL.revokeObjectURL(videoUrl);
      }
    };
  }, [videoUrl]);

  // sessionStorageから動画データを読み込み
  useEffect(() => {
    const videoUrl = sessionStorage.getItem('uploadedVideoUrl');
    const videoFileData = sessionStorage.getItem('uploadedVideoFile');
    
    console.log('ManualVideoClipper - sessionStorage videoUrl:', videoUrl);
    console.log('ManualVideoClipper - sessionStorage videoFileData:', videoFileData);
    
    if (videoFileData) {
      try {
        const fileData = JSON.parse(videoFileData);
        
        if (fileData.data) {
          console.log('ManualVideoClipper - Found base64 data, length:', fileData.data.length);
          // Base64データからBlob URLを作成
          const binaryString = atob(fileData.data);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: fileData.type });
          const newVideoUrl = URL.createObjectURL(blob);
          setVideoUrl(newVideoUrl);
          console.log('ManualVideoClipper - Created new videoUrl from base64:', newVideoUrl);
        } else {
          console.log('ManualVideoClipper - No base64 data found in fileData:', Object.keys(fileData));
          if (videoUrl) {
            // フォールバック: 既存のvideoUrlを使用
            setVideoUrl(videoUrl);
            console.log('ManualVideoClipper - Using existing videoUrl:', videoUrl);
          }
        }
      } catch (error) {
        console.error('ManualVideoClipper - Error parsing videoFileData:', error);
        if (videoUrl) {
          setVideoUrl(videoUrl);
        }
      }
    } else {
      console.log('ManualVideoClipper - No videoFileData found in sessionStorage');
    }
  }, []);

  // ファイル選択ハンドラー（フォールバック用）
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setVideoFile(file);
      const url = URL.createObjectURL(file);
      setVideoUrl(url);
      setSegments([]);
      setClippedVideos([]);
      setCurrentSegmentStart(null);
    }
  };

  // 動画のメタデータ読み込み
  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      const duration = videoRef.current.duration;
      setVideoDuration(duration);
      console.log('ManualVideoClipper - Video metadata loaded, duration:', duration);
    }
  };

  // 再生時間更新
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  // 再生/停止切り替え
  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  // 時間シーク
  const seekTo = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  // 5秒戻る
  const seekBackward = () => {
    const newTime = Math.max(0, currentTime - 5);
    seekTo(newTime);
  };

  // 5秒進む
  const seekForward = () => {
    const newTime = Math.min(videoDuration, currentTime + 5);
    seekTo(newTime);
  };

  // 1フレーム進む/戻る（30fps想定）
  const FRAME_STEP = 1 / 30;
  const stepFrame = (frames: number) => {
    const delta = frames * FRAME_STEP;
    const t = Math.min(videoDuration, Math.max(0, currentTime + delta));
    seekTo(t);
  };

  // サーブ開始マーク（固定長1.6秒 = 48frames@30fps）
  const markServeStart = () => {
    const FIXED_DURATION = 1.6; // seconds
    const start = currentTime;
    const end = Math.min(videoDuration, start + FIXED_DURATION);
    if (end <= start) return;
    const newSegment: Segment = { start, end, duration: end - start };
    setSegments([...segments, newSegment]);
  };

  // 現在のセグメントをキャンセル
  const cancelCurrentSegment = () => {
    setCurrentSegmentStart(null);
  };

  // 全てのセグメントをリセット
  const resetAllSegments = () => {
    setSegments([]);
    setCurrentSegmentStart(null);
  };

  // セグメントを削除
  const deleteSegment = (index: number) => {
    setSegments(segments.filter((_, i) => i !== index));
  };

  // セグメントにジャンプ
  const jumpToSegment = (segment: Segment) => {
    seekTo(segment.start);
  };

  // 動画クリッピング実行
  const executeClipping = async () => {
    if (!videoUrl || segments.length === 0) {
      alert('動画ファイルとセグメントを指定してください');
      return;
    }

    setIsProcessing(true);
    setClippedVideos([]);

    try {
      // Base64データから動画ファイルを復元
      const videoFileData = sessionStorage.getItem('uploadedVideoFile');
      if (!videoFileData) {
        alert('動画ファイルデータが見つかりません');
        return;
      }

      const fileData = JSON.parse(videoFileData);
      const binaryString = atob(fileData.data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: fileData.type });
      const videoFile = new File([blob], fileData.name, { type: fileData.type });

      const formData = new FormData();
      formData.append('video', videoFile);
      formData.append('segments', JSON.stringify(segments));

      const response = await fetch('/api/manual-clip', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        setClippedVideos(result.clippedVideos);
        // クリッピング結果をsessionStorageに保存
        sessionStorage.setItem('clippedVideos', JSON.stringify(result.clippedVideos));
        sessionStorage.setItem('segments', JSON.stringify(segments));
        
        console.log('クリッピング完了');
      } else {
        alert(`エラー: ${result.error}`);
      }
    } catch (error) {
      console.error('クリッピングエラー:', error);
      alert('動画クリッピングに失敗しました');
    } finally {
      setIsProcessing(false);
    }
  };

  // 時間フォーマット
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // プログレスバーの進捗
  const progress = videoDuration > 0 ? (currentTime / videoDuration) * 100 : 0;

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            サーブ映像の時間区切り処理
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ファイル選択（ホームからのアップロード前提のため非表示） */}

          {/* 動画プレーヤー */}
          {videoUrl ? (
            <div className="space-y-4">
              <div className="text-sm text-gray-600 mb-2">
                Video URL: {videoUrl.substring(0, 50)}...
              </div>
              <video
                ref={videoRef}
                src={videoUrl}
                className="w-full rounded-lg"
                onLoadedMetadata={handleLoadedMetadata}
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />

              {/* コントロール */}
              <div className="flex items-center gap-2">
                <Button onClick={togglePlayPause} size="sm">
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  Play/Pause
                </Button>
                <Button onClick={seekBackward} size="sm">⏪ 5s</Button>
                <Button onClick={seekForward} size="sm">5s ⏩</Button>
                <Button onClick={() => stepFrame(-1)} size="sm">⏪ 1f</Button>
                <Button onClick={() => stepFrame(1)} size="sm">1f ⏩</Button>
                <span className="text-sm font-mono">
                  {formatTime(currentTime)} / {formatTime(videoDuration)}
                </span>
              </div>

              {/* プログレスバー */}
              <div className="space-y-2">
                <Progress value={progress} className="w-full" />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>{formatTime(currentTime)}</span>
                  <span>{formatTime(videoDuration)}</span>
                </div>
              </div>

              {/* マークボタン */}
              <div className="flex gap-2">
                <Button onClick={markServeStart} variant="default">
                  Serve Initiation (Add 48f)
                </Button>
                <Button onClick={resetAllSegments} variant="outline">
                  <RotateCcw className="w-4 h-4" />
                  Reset
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center p-8 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-yellow-800 font-medium">No video loaded</p>
              <p className="text-yellow-600 text-sm mt-2">
                Please upload a video from the home page first.
              </p>
            </div>
          )}

          {/* セグメント一覧 */}
          {segments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>サーブセグメント一覧</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {segments.map((segment, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <Badge variant="secondary">Segment {index + 1}</Badge>
                        <span className="ml-2 text-sm">
                          {formatTime(segment.start)} → {formatTime(segment.end)} 
                          ({formatTime(segment.duration)})
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => jumpToSegment(segment)}
                          size="sm"
                          variant="outline"
                        >
                          📍 Jump
                        </Button>
                        <Button
                          onClick={() => deleteSegment(index)}
                          size="sm"
                          variant="destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* クリッピング実行ボタン */}
                <div className="mt-4">
                  <Button
                    onClick={executeClipping}
                    disabled={isProcessing}
                    className="w-full"
                  >
                    {isProcessing ? 'Processing...' : '💾 Execute Video Clipping'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 編集中のセグメント */}
          {/* 固定長方式に変更したため、編集中インジケータは非表示 */}

          {/* 切り取られた動画 */}
          {clippedVideos.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>✅ 切り取られた動画</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {clippedVideos.map((video, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div>
                        <Badge variant="secondary">Video {index + 1}</Badge>
                        <span className="ml-2 text-sm">
                          {video.filename} ({formatTime(video.duration)})
                        </span>
                      </div>
                      <Button
                        onClick={() => window.open(video.path, '_blank')}
                        size="sm"
                        variant="outline"
                      >
                        <Download className="w-4 h-4 mr-1" />
                        Download
                      </Button>
                    </div>
                  ))}
                  
                  <div className="pt-4 border-t space-y-3">
                    <div className="flex gap-3">
                      <Button 
                        onClick={() => router.push('/')}
                        variant="outline"
                        className="flex-1"
                        size="lg"
                      >
                        ← Back: Upload
                      </Button>
                      <Button 
                        onClick={() => router.push('/results')}
                        className="flex-1"
                        size="lg"
                      >
                        <ArrowRight className="w-4 h-4 mr-2" />
                        Next: Results Analysis
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
