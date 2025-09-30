"use client";

import React, { useEffect, useRef, useState } from "react";

type VideoPlayerProps = {
  videoPath: string;
  title?: string;
  className?: string;
  currentTime?: number;
  isControlled?: boolean;
  onTimeUpdate?: (time: number) => void;
  onLoadedMetadata?: (duration: number) => void;
};

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoPath,
  title,
  className,
  currentTime,
  isControlled = false,
  onTimeUpdate,
  onLoadedMetadata,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!isControlled || currentTime === undefined) return;
    if (videoRef.current) {
      // 同期再生用に現在時刻を設定
      if (Math.abs(videoRef.current.currentTime - currentTime) > 0.05) {
        videoRef.current.currentTime = currentTime;
      }
    }
  }, [currentTime, isControlled]);

  // 動画パスが変更されたときに読み込み状態をリセット
  useEffect(() => {
    setIsLoading(true);
    setError(null);
  }, [videoPath]);

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return;
    const d = isFinite(videoRef.current.duration) ? videoRef.current.duration : 0;
    setDuration(d);
    if (onLoadedMetadata) onLoadedMetadata(d);
    setIsLoading(false);
  };

  const handleTimeUpdate = () => {
    if (videoRef.current && onTimeUpdate) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  const handleLoadStart = () => {
    console.log("Video load started:", videoPath);
    setIsLoading(true);
    setError(null);
  };

  const handleCanPlay = () => {
    console.log("Video can play:", videoPath);
  };

  const handleLoadedData = () => {
    console.log("Video loaded data:", videoPath);
  };

  const handleCanPlayThrough = () => {
    console.log("Video can play through:", videoPath);
  };

  const handleWaiting = () => {
    console.log("Video waiting:", videoPath);
  };

  const handleStalled = () => {
    console.log("Video stalled:", videoPath);
  };

  const handleError = (e: any) => {
    console.error("Video loading error:", e);
    console.error("Video path:", videoPath);
    console.error("Video element:", videoRef.current);
    console.error("Video error details:", {
      error: videoRef.current?.error,
      networkState: videoRef.current?.networkState,
      readyState: videoRef.current?.readyState
    });
    
    // より詳細なエラー情報を表示
    let errorMessage = `動画の読み込みに失敗しました: ${videoPath}`;
    if (videoRef.current?.error) {
      const error = videoRef.current.error;
      switch (error.code) {
        case 1:
          errorMessage += "\nエラー: 動画の読み込みが中断されました";
          break;
        case 2:
          errorMessage += "\nエラー: ネットワークエラー";
          break;
        case 3:
          errorMessage += "\nエラー: 動画のデコードエラー";
          break;
        case 4:
          errorMessage += "\nエラー: 動画の形式がサポートされていません";
          break;
        default:
          errorMessage += `\nエラーコード: ${error.code}`;
      }
    }
    
    setError(errorMessage);
    setIsLoading(false);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className={className}>
      {title && <div className="mb-2 text-sm font-medium text-gray-700">{title}</div>}
      <div className="relative w-full bg-black aspect-video rounded-lg overflow-hidden">
        <video
          ref={videoRef}
          src={videoPath}
          className="w-full h-full"
          controls={!isControlled}
          onLoadStart={handleLoadStart}
          onLoadedMetadata={handleLoadedMetadata}
          onLoadedData={handleLoadedData}
          onCanPlay={handleCanPlay}
          onCanPlayThrough={handleCanPlayThrough}
          onWaiting={handleWaiting}
          onStalled={handleStalled}
          onTimeUpdate={handleTimeUpdate}
          onError={handleError}
        />
        {isLoading && !error && (
          <div className="absolute inset-0 grid place-items-center text-white text-sm bg-black/30">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
              動画を読み込み中...<br/>
              <span className="text-xs text-gray-300">{videoPath}</span>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 grid place-items-center text-red-200 text-sm bg-red-900/60 p-3 text-center">
            {error}
          </div>
        )}
      </div>
      <div className="mt-1 text-xs text-gray-500">長さ: {formatTime(duration)}</div>
    </div>
  );
};

export default VideoPlayer;


