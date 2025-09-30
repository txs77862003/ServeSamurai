"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import PoseVisualization from './PoseVisualization';

interface SynchronizedPoseComparisonProps {
  userCsvPath: string;
  referenceCsvPath: string;
  mostSimilarPlayer: string;
}

const SynchronizedPoseComparison: React.FC<SynchronizedPoseComparisonProps> = ({
  userCsvPath,
  referenceCsvPath,
  mostSimilarPlayer
}) => {
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [userFrameCount, setUserFrameCount] = useState(0);
  const [referenceFrameCount, setReferenceFrameCount] = useState(0);

  // フレーム数を取得するための関数
  const getFrameCount = async (csvPath: string) => {
    try {
      const response = await fetch(`/api/load-csv?path=${encodeURIComponent(csvPath)}`);
      if (response.ok) {
        const csvText = await response.text();
        const lines = csvText.split('\n').filter(line => line.trim());
        return lines.length - 1; // ヘッダー行を除く
      }
    } catch (error) {
      console.error('Frame count error:', error);
    }
    return 0;
  };

  useEffect(() => {
    // 両方のCSVファイルのフレーム数を取得
    const loadFrameCounts = async () => {
      const userCount = await getFrameCount(userCsvPath);
      const referenceCount = await getFrameCount(referenceCsvPath);
      setUserFrameCount(userCount);
      setReferenceFrameCount(referenceCount);
    };
    loadFrameCounts();
  }, [userCsvPath, referenceCsvPath]);

  // 再生/停止機能
  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        setCurrentFrame(prev => {
          const maxFrame = Math.min(userFrameCount, referenceFrameCount) - 1;
          if (prev >= maxFrame) {
            setIsPlaying(false);
            return 0; // 最初に戻る
          }
          return prev + 1;
        });
      }, 1000 / playbackSpeed);
      return () => clearInterval(interval);
    }
  }, [isPlaying, playbackSpeed, userFrameCount, referenceFrameCount]);

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const resetFrame = () => {
    setCurrentFrame(0);
    setIsPlaying(false);
  };

  const nextFrame = () => {
    const maxFrame = Math.min(userFrameCount, referenceFrameCount) - 1;
    if (currentFrame < maxFrame) {
      setCurrentFrame(currentFrame + 1);
    }
  };

  const prevFrame = () => {
    if (currentFrame > 0) {
      setCurrentFrame(currentFrame - 1);
    }
  };

  const maxFrame = Math.min(userFrameCount, referenceFrameCount) - 1;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">🎯 同期ポーズ比較</CardTitle>
        <p className="text-gray-600">
          ユーザーのポーズと{mostSimilarPlayer}のポーズを同期表示します
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
            <Button onClick={resetFrame} variant="outline" size="sm">
              🔄 リセット
            </Button>
            <Button onClick={prevFrame} variant="outline" size="sm" disabled={currentFrame === 0}>
              ⏮️ 前
            </Button>
            <Button onClick={nextFrame} variant="outline" size="sm" disabled={currentFrame >= maxFrame}>
              ⏭️ 次
            </Button>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">速度:</label>
              <select
                value={playbackSpeed}
                onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                className="px-2 py-1 border rounded text-sm"
              >
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={4}>4x</option>
              </select>
            </div>
            <div className="text-sm text-gray-600">
              フレーム: {currentFrame + 1} / {maxFrame + 1}
            </div>
          </div>

          {/* ポーズ比較表示 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <PoseVisualization
              csvPath={userCsvPath}
              title="👤 ユーザーのポーズ"
              className="h-full"
              currentFrame={currentFrame}
              isControlled={true}
            />
            <PoseVisualization
              csvPath={referenceCsvPath}
              title={`🏆 ${mostSimilarPlayer}のポーズ`}
              className="h-full"
              currentFrame={currentFrame}
              isControlled={true}
            />
          </div>

          {/* ファイル情報 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
            <div>
              <strong>ユーザーCSV:</strong> {userCsvPath.split('/').pop()}
              <br />
              <span>フレーム数: {userFrameCount}</span>
            </div>
            <div>
              <strong>参考CSV:</strong> {referenceCsvPath.split('/').pop()}
              <br />
              <span>フレーム数: {referenceFrameCount}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default SynchronizedPoseComparison;
