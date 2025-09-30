"use client";

import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PoseVisualizationProps {
  csvPath: string;
  title: string;
  className?: string;
  currentFrame?: number;
  onFrameChange?: (frame: number) => void;
  isControlled?: boolean;
}

interface PoseData {
  frame_index: number;
  kpt_5_x: number;  // left_shoulder
  kpt_5_y: number;
  kpt_6_x: number;  // right_shoulder
  kpt_6_y: number;
  kpt_7_x: number;  // left_elbow
  kpt_7_y: number;
  kpt_8_x: number;  // right_elbow
  kpt_8_y: number;
  kpt_9_x: number;  // left_wrist
  kpt_9_y: number;
  kpt_10_x: number; // right_wrist
  kpt_10_y: number;
  kpt_11_x: number; // left_hip
  kpt_11_y: number;
  kpt_12_x: number; // right_hip
  kpt_12_y: number;
  kpt_13_x: number; // left_knee
  kpt_13_y: number;
  kpt_14_x: number; // right_knee
  kpt_14_y: number;
  kpt_15_x: number; // left_ankle
  kpt_15_y: number;
  kpt_16_x: number; // right_ankle
  kpt_16_y: number;
}

const PoseVisualization: React.FC<PoseVisualizationProps> = ({ 
  csvPath, 
  title, 
  className, 
  currentFrame: externalCurrentFrame,
  onFrameChange,
  isControlled = false
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [poseData, setPoseData] = useState<PoseData[]>([]);
  const [internalCurrentFrame, setInternalCurrentFrame] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 外部制御か内部制御かを決定
  const currentFrame = isControlled ? (externalCurrentFrame || 0) : internalCurrentFrame;
  const setCurrentFrame = isControlled ? (onFrameChange || (() => {})) : setInternalCurrentFrame;

  useEffect(() => {
    loadPoseData();
  }, [csvPath]);

  const loadPoseData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // CSVファイルを読み込み
      const response = await fetch(`/api/load-csv?path=${encodeURIComponent(csvPath)}`);
      if (!response.ok) {
        throw new Error('CSVファイルの読み込みに失敗しました');
      }
      
      const csvText = await response.text();
      const lines = csvText.split('\n');
      const headers = lines[0].split(',');
      
      const data: PoseData[] = [];
      for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim()) {
          const values = lines[i].split(',');
          const row: any = {};
          headers.forEach((header, index) => {
            row[header.trim()] = parseFloat(values[index]) || 0;
          });
          data.push(row as PoseData);
        }
      }
      
      setPoseData(data);
      setCurrentFrame(0);
    } catch (err) {
      console.error('Pose data loading error:', err);
      setError(err instanceof Error ? err.message : 'データの読み込みに失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (poseData.length > 0) {
      drawPose();
    }
  }, [poseData, currentFrame]);

  const drawPose = () => {
    const canvas = canvasRef.current;
    if (!canvas || poseData.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // キャンバスをクリア
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const frame = poseData[currentFrame];
    if (!frame) return;

    // 座標を正規化（0-1の範囲に変換）
    const normalizeX = (x: number) => (x / 800) * canvas.width;
    const normalizeY = (y: number) => (y / 600) * canvas.height;

    // キーポイントの描画
    const keypoints = [
      { x: frame.kpt_5_x, y: frame.kpt_5_y, name: 'L_Shoulder', color: '#ff6b6b' },
      { x: frame.kpt_6_x, y: frame.kpt_6_y, name: 'R_Shoulder', color: '#4ecdc4' },
      { x: frame.kpt_7_x, y: frame.kpt_7_y, name: 'L_Elbow', color: '#45b7d1' },
      { x: frame.kpt_8_x, y: frame.kpt_8_y, name: 'R_Elbow', color: '#96ceb4' },
      { x: frame.kpt_9_x, y: frame.kpt_9_y, name: 'L_Wrist', color: '#feca57' },
      { x: frame.kpt_10_x, y: frame.kpt_10_y, name: 'R_Wrist', color: '#ff9ff3' },
      { x: frame.kpt_11_x, y: frame.kpt_11_y, name: 'L_Hip', color: '#54a0ff' },
      { x: frame.kpt_12_x, y: frame.kpt_12_y, name: 'R_Hip', color: '#5f27cd' },
      { x: frame.kpt_13_x, y: frame.kpt_13_y, name: 'L_Knee', color: '#00d2d3' },
      { x: frame.kpt_14_x, y: frame.kpt_14_y, name: 'R_Knee', color: '#ff9f43' },
      { x: frame.kpt_15_x, y: frame.kpt_15_y, name: 'L_Ankle', color: '#10ac84' },
      { x: frame.kpt_16_x, y: frame.kpt_16_y, name: 'R_Ankle', color: '#ee5a24' }
    ];

    // 骨格の接続線を描画
    const connections = [
      [0, 1], // 肩
      [0, 2], [2, 4], // 左腕
      [1, 3], [3, 5], // 右腕
      [0, 6], [1, 7], // 肩から腰
      [6, 7], // 腰
      [6, 8], [8, 10], // 左脚
      [7, 9], [9, 11]  // 右脚
    ];

    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    connections.forEach(([start, end]) => {
      const startPoint = keypoints[start];
      const endPoint = keypoints[end];
      if (startPoint && endPoint) {
        ctx.beginPath();
        ctx.moveTo(normalizeX(startPoint.x), normalizeY(startPoint.y));
        ctx.lineTo(normalizeX(endPoint.x), normalizeY(endPoint.y));
        ctx.stroke();
      }
    });

    // キーポイントを描画
    keypoints.forEach((point) => {
      if (point.x > 0 && point.y > 0) {
        ctx.fillStyle = point.color;
        ctx.beginPath();
        ctx.arc(normalizeX(point.x), normalizeY(point.y), 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    });
  };

  const nextFrame = () => {
    if (currentFrame < poseData.length - 1) {
      setCurrentFrame(currentFrame + 1);
    }
  };

  const prevFrame = () => {
    if (currentFrame > 0) {
      setCurrentFrame(currentFrame - 1);
    }
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">読み込み中...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <div className="text-red-500">エラー: {error}</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <div className="text-sm text-gray-600">
          フレーム: {currentFrame + 1} / {poseData.length}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <canvas
            ref={canvasRef}
            width={400}
            height={300}
            className="border rounded-lg bg-gray-50"
          />
          <div className="flex justify-center space-x-2">
            <button
              onClick={prevFrame}
              disabled={currentFrame === 0}
              className="px-3 py-1 bg-blue-500 text-white rounded disabled:bg-gray-300"
            >
              ← 前
            </button>
            <button
              onClick={nextFrame}
              disabled={currentFrame === poseData.length - 1}
              className="px-3 py-1 bg-blue-500 text-white rounded disabled:bg-gray-300"
            >
              次 →
            </button>
          </div>
          <div className="text-xs text-gray-500">
            CSV: {csvPath.split('/').pop()}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PoseVisualization;
