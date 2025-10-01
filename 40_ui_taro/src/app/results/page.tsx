'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import ResultsDashboard from '@/components/ResultsDashboard';
import StepIndicator from '@/components/StepIndicator';
import * as Serve from '../../lib/analysis/serveAnalysis';
type AnalysisResult = Serve.AnalysisResult;
type ServeFeatures = Serve.ServeFeatures;

export default function ResultsPage() {
  const [clippedVideos, setClippedVideos] = useState<any[]>([]);
  const [currentVideoIndex, setCurrentVideoIndex] = useState<number>(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [processing, setProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisComplete, setAnalysisComplete] = useState<boolean>(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const router = useRouter();

  useEffect(() => {
    // sessionStorageからクリッピング結果を取得
    const savedClippedVideos = sessionStorage.getItem('clippedVideos');
    const savedVideoFile = sessionStorage.getItem('uploadedVideoFile');
    const savedVideoUrl = sessionStorage.getItem('uploadedVideoUrl');
    
    console.log('results/page - savedClippedVideos:', savedClippedVideos);
    console.log('results/page - savedVideoFile:', savedVideoFile);
    console.log('results/page - savedVideoUrl:', savedVideoUrl);
    
    if (savedClippedVideos && (savedVideoFile || savedVideoUrl)) {
      setClippedVideos(JSON.parse(savedClippedVideos));
      console.log('results/page - クリッピング結果を読み込み:', JSON.parse(savedClippedVideos));
    } else {
      // クリッピング結果がない場合はホームに戻る
      console.log('results/page - クリッピング結果が見つからないため、ホームに戻ります');
      router.push('/');
    }
  }, [router]);

  const currentVideo = clippedVideos[currentVideoIndex];

  const onAnalyze = useCallback(async () => {
    if (!videoRef.current || !currentVideo) return;
    
    try {
      setProcessing(true);
      setError(null);
      
      // 実際の分析処理
      const res = await Serve.analyzeServe(videoRef.current);
      setResult(res);
      setAnalysisComplete(true);
      
      // 分析結果をsessionStorageに保存
      sessionStorage.setItem('analysisResult', JSON.stringify(res));
      console.log('分析結果をsessionStorageに保存:', res);
    } catch (e: any) {
      setError(e?.message ?? "分析に失敗しました");
    } finally {
      setProcessing(false);
    }
  }, [currentVideo]);

  const runDemo = useCallback(() => {
    // デモ用の分析結果を生成
    const motionEnergy = Array.from({ length: 24 }, (_, i) => Math.max(0, Math.sin(i / 5) * 0.6 + 0.4));
    const centroidPath = motionEnergy.map((m, i) => ({ x: 0.5 + Math.sin(i / 7) * 0.15, y: 0.55 - Math.cos(i / 6) * 0.1 }));
    const features: ServeFeatures = {
      durationMs: 1600,
      motionEnergy,
      centroidPath,
      peakTossIndex: 5,
      contactIndex: 9,
      followThroughIndex: 14,
      lowerBodyEngagement: 0.72,
      shoulderRotationProxy: 0.68,
      racquetDropProxy: 0.78,
    };
    const similarities = Serve.compareToPros(features);
    const advice = Serve.generateAdvice(features, similarities[0]);
    const demo: AnalysisResult = { features, similarities, advice };
    setResult(demo);
    setAnalysisComplete(true);
    setError(null);
    
    // デモ結果もsessionStorageに保存
    sessionStorage.setItem('analysisResult', JSON.stringify(demo));
    console.log('デモ分析結果をsessionStorageに保存:', demo);
  }, []);

  const resetAnalysis = useCallback(() => {
    setResult(null);
    setAnalysisComplete(false);
    setError(null);
  }, []);

  if (clippedVideos.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>⚠️ 分析対象が見つかりません</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-gray-600">
              クリッピングされた動画が見つかりません。最初からやり直してください。
            </p>
            <Link href="/">
              <Button className="w-full">
                🏠 Go Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50">
      <section className="container mx-auto max-w-6xl px-6 py-12">
        <StepIndicator currentStep={3} />
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                📊 サーブ分析結果
              </h1>
              <p className="text-lg text-gray-600">
                クリッピングされた動画からサーブを分析し、プロ選手との比較を行います
              </p>
            </div>
            <div className="flex gap-2">
              <Link href="/manual-clip">
                <Button variant="outline">
                  ← Back: Clipping
                </Button>
              </Link>
              <Link href="/">
                <Button variant="outline">
                  🏠 Home
                </Button>
              </Link>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
          <div className="lg:col-span-3 space-y-6">
            {/* 動画選択 */}
            <Card>
              <CardHeader>
                <CardTitle>🎥 分析対象動画</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {clippedVideos.length > 1 && (
                  <div className="flex gap-2 flex-wrap">
                    {clippedVideos.map((video, index) => (
                      <Button
                        key={index}
                        variant={index === currentVideoIndex ? "default" : "outline"}
                        size="sm"
                        onClick={() => setCurrentVideoIndex(index)}
                      >
                        Video {index + 1}
                      </Button>
                    ))}
                  </div>
                )}
                
                {currentVideo && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">
                        {currentVideo.filename}
                      </Badge>
                      <span className="text-sm text-gray-600">
                        長さ: {Math.round(currentVideo.duration * 100) / 100}秒
                      </span>
                    </div>
                    
                    <video
                      ref={videoRef}
                      src={currentVideo.path}
                      className="w-full rounded-lg"
                      controls
                      preload="auto"
                      playsInline
                    />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 分析コントロール */}
            <Card>
              <CardHeader>
                <CardTitle>🔬 分析コントロール</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {!analysisComplete ? (
                  <div className="space-y-3">
                    <div className="flex gap-3">
                      <Button 
                        onClick={onAnalyze} 
                        disabled={!currentVideo || processing}
                        className="flex-1"
                      >
                        {processing ? "Analyzing..." : "📊 Run Serve Analysis"}
                      </Button>
                      <Button 
                        variant="secondary" 
                        onClick={runDemo} 
                        disabled={processing}
                      >
                        Run Demo
                      </Button>
                    </div>
                    <div className="flex gap-3 pt-2 border-t">
                      <Link href="/manual-clip">
                        <Button variant="outline" className="flex-1">
                          ← Back: Clipping
                        </Button>
                      </Link>
                      <Link href="/">
                        <Button variant="outline" className="flex-1">
                          🏠 Go Home
                        </Button>
                      </Link>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex gap-3">
                      <Button onClick={resetAnalysis} variant="outline">
                        🔄 Re-analyze
                      </Button>
                      <Button 
                        onClick={runDemo} 
                        variant="secondary"
                      >
                        Run Demo Again
                      </Button>
                      <Link href="/pose-advice">
                        <Button variant="default">
                          🎯 Pose Advice Tool
                        </Button>
                      </Link>
                    </div>
                    <div className="flex gap-3 pt-2 border-t">
                      <Link href="/manual-clip">
                        <Button variant="outline" className="flex-1">
                          ← Back: Clipping
                        </Button>
                      </Link>
                      <Link href="/">
                        <Button variant="outline" className="flex-1">
                          🏠 Go Home
                        </Button>
                      </Link>
                    </div>
                  </div>
                )}
                
                {error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-800 text-sm">
                      ❌ エラー: {error}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 分析結果 */}
            {result && (
              <ResultsDashboard 
                result={result} 
                videoUrl={currentVideo?.path || ""} 
              />
            )}
          </div>

          {/* サイドバー */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>📈 分析の進捗</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-100 text-green-600 rounded-full flex items-center justify-center font-bold">✓</div>
                  <div>
                    <p className="font-medium">動画アップロード</p>
                    <p className="text-sm text-gray-600">完了</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-100 text-green-600 rounded-full flex items-center justify-center font-bold">✓</div>
                  <div>
                    <p className="font-medium">動画クリッピング</p>
                    <p className="text-sm text-gray-600">完了 ({clippedVideos.length}個)</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    analysisComplete 
                      ? 'bg-green-100 text-green-600' 
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {analysisComplete ? '✓' : '3'}
                  </div>
                  <div>
                    <p className="font-medium">結果分析</p>
                    <p className="text-sm text-gray-600">
                      {analysisComplete ? '完了' : '待機中'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>📋 分析項目</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span>モーションエネルギー</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>重心軌道</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                  <span>トス・コンタクト・フォロースルー</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                  <span>下半身の動き</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                  <span>肩の回転</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-indigo-500 rounded-full"></div>
                  <span>ラケットドロップ</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}
