"use client";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StepIndicator from "@/components/StepIndicator";
import VideoPlayer from "@/components/VideoPlayer";
import SynchronizedVideoComparison from "@/components/SynchronizedVideoComparison";

type AdviceFinding = {
  metric: string;
  difference: number;
  recommendation: string;
};

type PoseAdviceResponse = {
  success: boolean;
  user_metrics: Record<string, number | null>;
  reference_metrics: Record<string, number | null>;
  difference: Record<string, number | null>;
  advice: AdviceFinding[];
  error?: string;
};

const defaultTrophyRange = "15,30";
const defaultImpactRange = "25,40";

const parseRangeInput = (value: string) => {
  const parts = value
    .split(",")
    .map((part) => Number(part.trim()))
    .filter((num) => Number.isFinite(num));
  return parts.length === 2 ? parts : undefined;
};

export default function PoseAdvicePage() {
  const [userCsv, setUserCsv] = useState("");
  const [referenceCsv, setReferenceCsv] = useState("");
  const [trophyRange, setTrophyRange] = useState(defaultTrophyRange);
  const [impactRange, setImpactRange] = useState(defaultImpactRange);
  const [userTrophyFrame, setUserTrophyFrame] = useState("");
  const [userImpactFrame, setUserImpactFrame] = useState("");
  const [referenceTrophyFrame, setReferenceTrophyFrame] = useState("");
  const [referenceImpactFrame, setReferenceImpactFrame] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PoseAdviceResponse | null>(null);
  const [mostSimilarPlayer, setMostSimilarPlayer] = useState<string | null>(null);
  const [mostSimilarVideo, setMostSimilarVideo] = useState<string | null>(null);
  const [userVideoPath, setUserVideoPath] = useState<string | null>(null);
  const [referenceVideoPath, setReferenceVideoPath] = useState<string | null>(null);

  // ページ読み込み時にユーザーCSVと最も似ている選手を自動設定
  useEffect(() => {
    // ユーザーCSVファイルを自動検出
    const userCsvPath = "pose_tracks/players/User/serve_1_2_4/keypoints_with_tracks.csv";
    setUserCsv(userCsvPath);

    // 3画面目の結果から最も似ている選手を取得
    const getMostSimilarPlayer = async () => {
      // sessionStorageから分析結果を取得
      const analysisResult = sessionStorage.getItem('analysisResult');
      console.log('sessionStorageから取得した分析結果:', analysisResult);
      
      if (analysisResult) {
        try {
          const result = JSON.parse(analysisResult);
          console.log('解析された分析結果:', result);
          console.log('similarities:', result.similarities);
          
          if (result.similarities && result.similarities.length > 0) {
            const mostSimilar = result.similarities[0];
            console.log('最も似ている選手:', mostSimilar);
            setMostSimilarPlayer(mostSimilar.player);
            
            // 数学的に最も類似度の高いCSVファイルを検索
            console.log('類似度計算を開始...');
            const playerCsvPath = await findMostSimilarCsv(mostSimilar.player);
            console.log('選択されたCSVパス:', playerCsvPath);
            setMostSimilarVideo(playerCsvPath);
            setReferenceCsv(playerCsvPath);
            
            // 対応する動画パスも設定
            const userVideo = await getVideoPathFromCsv(userCsvPath);
            const referenceVideo = await getVideoPathFromCsv(playerCsvPath);
            console.log('ユーザー動画パス:', userVideo);
            console.log('参考動画パス:', referenceVideo);
            setUserVideoPath(userVideo);
            setReferenceVideoPath(referenceVideo);
            return;
          }
        } catch (e) {
          console.error('Failed to parse analysis result:', e);
        }
      }
      
      // フォールバック: デモ用にFedererを設定
      console.log('フォールバック: Federerを設定');
      setMostSimilarPlayer("Federer");
      const fallbackCsvPath = await findMostSimilarCsv("Federer");
      setMostSimilarVideo(fallbackCsvPath);
      setReferenceCsv(fallbackCsvPath);
      
      // 対応する動画パスも設定
      const userVideo = await getVideoPathFromCsv(userCsvPath);
      const referenceVideo = await getVideoPathFromCsv(fallbackCsvPath);
      console.log('フォールバック - ユーザー動画パス:', userVideo);
      console.log('フォールバック - 参考動画パス:', referenceVideo);
      setUserVideoPath(userVideo);
      setReferenceVideoPath(referenceVideo);
    };

    getMostSimilarPlayer();
  }, []);

  // 最も類似度の高いCSVファイルを検索する関数
  const findMostSimilarCsv = async (playerName: string): Promise<string> => {
    try {
      // userCsvが空の場合はデフォルトのパスを使用
      const userCsvPath = userCsv || "pose_tracks/players/User/serve_1_2_4/keypoints_with_tracks.csv";
      
      const response = await fetch('/api/find-similar-csv', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userCsv: userCsvPath,
          playerName: playerName
        }),
      });

      if (!response.ok) {
        throw new Error(`APIエラー: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        console.log('最も類似度の高いCSVファイル:', result.best_match);
        return result.best_match.csv_path;
      } else {
        console.error('類似度計算エラー:', result.error);
        // フォールバック: 固定のCSVファイルパス
        return getFallbackCsvPath(playerName);
      }
    } catch (error) {
      console.error('類似度計算API呼び出しエラー:', error);
      // フォールバック: 固定のCSVファイルパス
      return getFallbackCsvPath(playerName);
    }
  };

  // フォールバック用のCSVファイルパスを取得する関数
  const getFallbackCsvPath = (playerName: string): string => {
    const playerMap: { [key: string]: string } = {
      "Nishikori": "pose_tracks/Cleaned_Data/players/Kei/kei_serve_back1_kei,back,serve,deuce___/keypoints_with_tracks.csv",
      "Federer": "pose_tracks/Cleaned_Data/players/Fed/fed_ser_2_s608p94-e610p54_fed_serve_back_deuce_/keypoints_with_tracks.csv",
      "Djokovic": "pose_tracks/Cleaned_Data/players/Djo/djoko_C4Gl-T2dtss_back_30fps_djokovic_serve_back/keypoints_with_tracks.csv",
      "Alcaraz": "pose_tracks/Cleaned_Data/players/Alc/alc_ser_1_s626p68-e628p28_alc_serve_back_deuce_/keypoints_with_tracks.csv",
      // 略称にも対応
      "Kei": "pose_tracks/Cleaned_Data/players/Kei/kei_serve_back1_kei,back,serve,deuce___/keypoints_with_tracks.csv",
      "Fed": "pose_tracks/Cleaned_Data/players/Fed/fed_ser_2_s608p94-e610p54_fed_serve_back_deuce_/keypoints_with_tracks.csv",
      "Djo": "pose_tracks/Cleaned_Data/players/Djo/djoko_C4Gl-T2dtss_back_30fps_djokovic_serve_back/keypoints_with_tracks.csv",
      "Alc": "pose_tracks/Cleaned_Data/players/Alc/alc_ser_1_s626p68-e628p28_alc_serve_back_deuce_/keypoints_with_tracks.csv"
    };
    
    return playerMap[playerName] || playerMap["Federer"];
  };

  // CSVファイルから対応する動画ファイルのパスを取得する関数
  const getVideoPathFromCsv = async (csvPath: string): Promise<string> => {
    // CSVファイルのパスから動画ファイルのパスを推測
    const pathParts = csvPath.split('/');
    const fileName = pathParts[pathParts.length - 2]; // ディレクトリ名を取得
    
    if (csvPath.includes('players/User/')) {
      // ユーザーの動画はclipped-videosディレクトリにある
      return `/clipped-videos/${fileName}.mp4`;
    } else if (csvPath.includes('Cleaned_Data/players/')) {
      // プロ選手の動画パスを推測
      const playerIndex = pathParts.findIndex(part => part === 'players') + 1;
      const playerName = pathParts[playerIndex];
      
      // フォールバック: 固定の動画ファイル（直接publicディレクトリから配信）
      if (playerName === 'Kei') {
        return `/kei_serve_converted.mp4`;
      } else if (playerName === 'Fed') {
        return `/test_video.mp4`; // 一時的にtest_videoを使用
      } else if (playerName === 'Djo') {
        return `/test_video.mp4`; // 一時的にtest_videoを使用
      } else if (playerName === 'Alc') {
        return `/test_video.mp4`; // 一時的にtest_videoを使用
      }
      
      return `/test_video.mp4`; // デフォルト
    }
    
    return `/test_video.mp4`; // デフォルト
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!userCsv.trim()) {
      setError("ユーザー用CSVのパスを入力してください");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const trophyRangeParsed = parseRangeInput(trophyRange);
    const impactRangeParsed = parseRangeInput(impactRange);

    const payload = {
      userCsv: userCsv.trim(),
      referenceCsv: referenceCsv.trim() || undefined,
      trophyRange: trophyRangeParsed,
      impactRange: impactRangeParsed,
      userTrophyFrame: userTrophyFrame ? Number(userTrophyFrame) : undefined,
      userImpactFrame: userImpactFrame ? Number(userImpactFrame) : undefined,
      referenceTrophyFrame: referenceTrophyFrame
        ? Number(referenceTrophyFrame)
        : undefined,
      referenceImpactFrame: referenceImpactFrame
        ? Number(referenceImpactFrame)
        : undefined,
    };

    try {
      const response = await fetch("/api/pose-advice", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        const message = errorPayload?.error ?? `APIエラー (HTTP ${response.status})`;
        throw new Error(message);
      }

      const data: PoseAdviceResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "未知のエラーが発生しました",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50">
      <section className="container mx-auto max-w-6xl px-6 py-12">
        <StepIndicator currentStep={4} />
        
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                🎯 Pose Advice Tool
              </h1>
              <p className="text-lg text-gray-600">
                ポーズ分析モジュールを使用して、ユーザーのポーズCSVと比較対象CSVを比較し、アドバイスを生成します
              </p>
            </div>
            <div className="flex gap-2">
              <Link href="/results">
                <Button variant="outline">
                  ← Back: Results
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

        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle className="text-2xl">📊 ポーズ分析設定</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 自動選択されたファイル情報の表示 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    ユーザーCSVファイル
                  </label>
                  <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                    <p className="text-sm text-green-800 font-medium">
                      ✓ 自動選択: {userCsv}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    比較対象CSVファイル
                  </label>
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                    <p className="text-sm text-blue-800 font-medium">
                      ✓ 最も似ている選手: {mostSimilarPlayer}
                    </p>
                    <p className="text-xs text-blue-600 mt-1">
                      {referenceCsv}
                    </p>
                  </div>
                </div>
              </div>

              {/* フレーム探索レンジ設定 - 後で使用する可能性があるためコメントアウト */}
              {/* 
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    トロフィーフレーム探索レンジ (例: 15,30)
                  </label>
                  <input
                    type="text"
                    value={trophyRange}
                    onChange={(event) => setTrophyRange(event.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    インパクトフレーム探索レンジ (例: 25,40)
                  </label>
                  <input
                    type="text"
                    value={impactRange}
                    onChange={(event) => setImpactRange(event.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">ユーザー側フレーム指定 (任意)</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">トロフィーフレーム</label>
                      <input
                        type="number"
                        value={userTrophyFrame}
                        onChange={(event) => setUserTrophyFrame(event.target.value)}
                        placeholder="未指定なら自動検出"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">インパクトフレーム</label>
                      <input
                        type="number"
                        value={userImpactFrame}
                        onChange={(event) => setUserImpactFrame(event.target.value)}
                        placeholder="未指定なら自動検出"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">比較対象フレーム指定 (任意)</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">トロフィーフレーム</label>
                      <input
                        type="number"
                        value={referenceTrophyFrame}
                        onChange={(event) => setReferenceTrophyFrame(event.target.value)}
                        placeholder="未指定なら自動検出"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">インパクトフレーム</label>
                      <input
                        type="number"
                        value={referenceImpactFrame}
                        onChange={(event) => setReferenceImpactFrame(event.target.value)}
                        placeholder="未指定なら自動検出"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>
              */}

              <div className="flex gap-3 pt-4">
                <Button
                  type="submit"
                  disabled={loading}
                  className="flex-1"
                  size="lg"
                >
                  {loading ? "分析中…" : "🎯 分析を実行"}
                </Button>
                <Link href="/results">
                  <Button variant="outline" size="lg">
                    ← Back: Results
                  </Button>
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>

        {error && (
          <Card className="mt-6 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="text-red-800">
                <strong>❌ エラーが発生しました:</strong> {error}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 動画比較表示 */}
        {(userCsv && referenceCsv) && (
          <div className="mt-8">
            <SynchronizedVideoComparison
              userVideoPath={userVideoPath}
              referenceVideoPath={referenceVideoPath}
              mostSimilarPlayer={mostSimilarPlayer || 'プロ選手'}
            />
          </div>
        )}

        {result && (
          <div className="mt-8 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-2xl">📊 解析結果</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-2xl">💡 アドバイス</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {result.advice.map((item, index) => (
                    <div key={index} className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="font-semibold text-blue-900 mb-2">
                        {item.metric}
                      </div>
                      <div className="text-sm text-blue-700 mb-1">
                        差分: {item.difference}
                      </div>
                      <div className="text-blue-800">
                        {item.recommendation}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </section>
    </div>
  );
}
