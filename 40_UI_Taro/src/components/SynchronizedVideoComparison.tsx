"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import VideoPlayer from './VideoPlayer';

interface SynchronizedVideoComparisonProps {
  userVideoPath: string;
  referenceVideoPath: string;
  mostSimilarPlayer: string;
}

const SynchronizedVideoComparison: React.FC<SynchronizedVideoComparisonProps> = ({
  userVideoPath,
  referenceVideoPath,
  mostSimilarPlayer
}) => {
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [userDuration, setUserDuration] = useState(0);
  const [referenceDuration, setReferenceDuration] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const userVideoRef = useRef<HTMLVideoElement>(null);
  const referenceVideoRef = useRef<HTMLVideoElement>(null);

  // 動画の同期制御
  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        setCurrentTime(prev => {
          const maxDuration = Math.min(userDuration, referenceDuration);
          if (prev >= maxDuration) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 0.1; // 100msごとに更新
        });
      }, 100);

      return () => clearInterval(interval);
    }
  }, [isPlaying, userDuration, referenceDuration]);

  // 動画要素の時間を同期
  useEffect(() => {
    if (userVideoRef.current) {
      userVideoRef.current.currentTime = currentTime;
    }
    if (referenceVideoRef.current) {
      referenceVideoRef.current.currentTime = currentTime;
    }
  }, [currentTime]);

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
    
    // 動画要素の再生/停止を制御
    if (userVideoRef.current) {
      if (isPlaying) {
        userVideoRef.current.pause();
      } else {
        userVideoRef.current.play();
      }
    }
    if (referenceVideoRef.current) {
      if (isPlaying) {
        referenceVideoRef.current.pause();
      } else {
        referenceVideoRef.current.play();
      }
    }
  };

  const resetTime = () => {
    setCurrentTime(0);
    setIsPlaying(false);
    if (userVideoRef.current) {
      userVideoRef.current.currentTime = 0;
      userVideoRef.current.pause();
    }
    if (referenceVideoRef.current) {
      referenceVideoRef.current.currentTime = 0;
      referenceVideoRef.current.pause();
    }
  };

  const seekTo = (time: number) => {
    setCurrentTime(time);
    if (userVideoRef.current) {
      userVideoRef.current.currentTime = time;
    }
    if (referenceVideoRef.current) {
      referenceVideoRef.current.currentTime = time;
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const maxDuration = Math.min(userDuration, referenceDuration);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">🎯 動画比較</CardTitle>
        <p className="text-gray-600">
          ユーザーの動画と{mostSimilarPlayer}の動画を同期表示します
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* コントロールパネル */}
          <div className="flex flex-wrap items-center justify-center gap-4 p-4 bg-gray-50 rounded-lg">
            <Button
              onClick={togglePlayback}
              variant={isPlaying ? "destructive" : "default"}
              size="sm"
            >
              {isPlaying ? "⏸️ 停止" : "▶️ 再生"}
            </Button>
            <Button onClick={resetTime} variant="outline" size="sm">
              🔄 リセット
            </Button>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">速度:</label>
              <select
                value={playbackSpeed}
                onChange={(e) => {
                  const speed = Number(e.target.value);
                  setPlaybackSpeed(speed);
                  if (userVideoRef.current) userVideoRef.current.playbackRate = speed;
                  if (referenceVideoRef.current) referenceVideoRef.current.playbackRate = speed;
                }}
                className="px-2 py-1 border rounded text-sm"
              >
                <option value={0.25}>0.25x</option>
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={1.25}>1.25x</option>
                <option value={1.5}>1.5x</option>
                <option value={2}>2x</option>
              </select>
            </div>
            <div className="text-sm text-gray-600">
              時間: {formatTime(currentTime)} / {formatTime(maxDuration)}
            </div>
          </div>

          {/* プログレスバー */}
          <div className="w-full">
            <input
              type="range"
              min="0"
              max={maxDuration}
              step="0.1"
              value={currentTime}
              onChange={(e) => seekTo(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* 動画比較表示 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <VideoPlayer
              videoPath={userVideoPath}
              title="👤 ユーザーの動画"
              className="h-full"
              currentTime={currentTime}
              isControlled={true}
              onLoadedMetadata={setUserDuration}
            />
            <VideoPlayer
              videoPath={referenceVideoPath}
              title={`🏆 ${mostSimilarPlayer}の動画`}
              className="h-full"
              currentTime={currentTime}
              isControlled={true}
              onLoadedMetadata={setReferenceDuration}
            />
          </div>

          {/* ファイル情報 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
            <div>
              <strong>ユーザー動画:</strong> {userVideoPath.split('/').pop()}
              <br />
              <span>長さ: {formatTime(userDuration)}</span>
            </div>
            <div>
              <strong>参考動画:</strong> {referenceVideoPath.split('/').pop()}
              <br />
              <span>長さ: {formatTime(referenceDuration)}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default SynchronizedVideoComparison;
