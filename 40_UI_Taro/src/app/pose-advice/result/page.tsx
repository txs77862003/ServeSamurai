"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StepIndicator from "@/components/StepIndicator";

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

type ResultMeta = {
  selectedSuggestion?: string;
};

type ReferenceSuggestion = {
  player: string;
  clipName: string;
  csvPathRelative: string;
  previewImagePath?: string;
  frameDirRelative?: string;
  slug: string;
  confidence?: number;
};

type UserClipInfo = {
  clipName: string;
  frameDirRelative?: string;
  slug: string;
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export default function PoseAdviceResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<PoseAdviceResponse | null>(null);
  const [meta, setMeta] = useState<ResultMeta | null>(null);
  const [suggestions, setSuggestions] = useState<ReferenceSuggestion[]>([]);
  const [userClip, setUserClip] = useState<UserClipInfo | null>(null);

  const [userFrames, setUserFrames] = useState<string[]>([]);
  const [userFrameLoading, setUserFrameLoading] = useState(false);
  const [userFrameError, setUserFrameError] = useState<string | null>(null);
  const [userFrameIndex, setUserFrameIndex] = useState(0);

  const [referenceFrames, setReferenceFrames] = useState<string[]>([]);
  const [referenceFrameLoading, setReferenceFrameLoading] = useState(false);
  const [referenceFrameError, setReferenceFrameError] = useState<string | null>(null);
  const [referenceFrameIndex, setReferenceFrameIndex] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const storedResult = sessionStorage.getItem("poseAdviceResult");
    const storedMeta = sessionStorage.getItem("poseAdviceResultMeta");
    const storedSuggestions = sessionStorage.getItem("poseAdviceReferenceSuggestions");
    const storedUserClip = sessionStorage.getItem("poseAdviceUserClip");

    if (storedResult) {
      try {
        setResult(JSON.parse(storedResult) as PoseAdviceResponse);
      } catch (err) {
        console.warn("pose-advice-result: failed to parse result", err);
      }
    }

    if (storedMeta) {
      try {
        setMeta(JSON.parse(storedMeta) as ResultMeta);
      } catch (err) {
        console.warn("pose-advice-result: failed to parse meta", err);
      }
    }

    if (storedSuggestions) {
      try {
        setSuggestions(JSON.parse(storedSuggestions) as ReferenceSuggestion[]);
      } catch (err) {
        console.warn("pose-advice-result: failed to parse suggestions", err);
      }
    }

    if (storedUserClip) {
      try {
        setUserClip(JSON.parse(storedUserClip) as UserClipInfo);
      } catch (err) {
        console.warn("pose-advice-result: failed to parse user clip", err);
      }
    }
  }, []);

  const selectedSuggestion = useMemo(() => {
    if (!meta?.selectedSuggestion) return null;
    return suggestions.find((item) => item.slug === meta.selectedSuggestion) ?? null;
  }, [meta, suggestions]);

  useEffect(() => {
    const loadFrames = async (
      frameDirRelative: string | undefined,
      slug: string,
      setFrames: React.Dispatch<React.SetStateAction<string[]>>,
      setError: React.Dispatch<React.SetStateAction<string | null>>,
      setLoading: React.Dispatch<React.SetStateAction<boolean>>,
    ) => {
      if (!frameDirRelative) {
        setFrames([]);
        setError("フレーム画像が見つかりません");
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/reference-frames", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frameDirRelative, slug }),
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error(data.error ?? "フレームの取得に失敗しました");
        }
        setFrames(data.frames as string[]);
      } catch (err) {
        setFrames([]);
        setError(err instanceof Error ? err.message : "フレームの取得に失敗しました");
      } finally {
        setLoading(false);
      }
    };

    if (userClip) {
      setUserFrameIndex(0);
      loadFrames(userClip.frameDirRelative, userClip.slug, setUserFrames, setUserFrameError, setUserFrameLoading);
    }
  }, [userClip]);

  useEffect(() => {
    const loadFrames = async (
      frameDirRelative: string | undefined,
      slug: string,
      setFrames: React.Dispatch<React.SetStateAction<string[]>>,
      setError: React.Dispatch<React.SetStateAction<string | null>>,
      setLoading: React.Dispatch<React.SetStateAction<boolean>>,
    ) => {
      if (!frameDirRelative) {
        setFrames([]);
        setError("フレーム画像が見つかりません");
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/reference-frames", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frameDirRelative, slug }),
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error(data.error ?? "フレームの取得に失敗しました");
        }
        setFrames(data.frames as string[]);
      } catch (err) {
        setFrames([]);
        setError(err instanceof Error ? err.message : "フレームの取得に失敗しました");
      } finally {
        setLoading(false);
      }
    };

    if (selectedSuggestion) {
      setReferenceFrameIndex(0);
      loadFrames(
        selectedSuggestion.frameDirRelative,
        selectedSuggestion.slug,
        setReferenceFrames,
        setReferenceFrameError,
        setReferenceFrameLoading,
      );
    }
  }, [selectedSuggestion]);

  const handleBackToSelection = () => {
    router.push("/pose-advice");
  };

  if (!result) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>⚠️ アドバイス結果が見つかりません</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-gray-600">
              アドバイス結果が保存されていません。もう一度比較条件を設定して実行してください。
            </p>
            <Button className="w-full" onClick={handleBackToSelection}>
              🎯 Pose Advice に戻る
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const formatFrameLabel = (index: number | null, total: number) => {
    if (index === null) return "未設定";
    return `Frame ${index + 1} / ${total}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50">
      <section className="container mx-auto max-w-5xl px-6 py-12">
        <StepIndicator currentStep={5} />

        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                ✅ Pose Advice Result
              </h1>
              <p className="text-lg text-gray-600">
                指定した比較条件に基づくポーズ分析の結果です。
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleBackToSelection}>
                ← Back: Pose Advice
              </Button>
              <Link href="/">
                <Button variant="outline">
                  🏠 Home
                </Button>
              </Link>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-green-200 bg-green-50">
            <CardHeader>
              <CardTitle className="text-xl">👤 ユーザー動画</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant="secondary" className="text-green-800">
                  {userClip?.clipName ?? "未取得"}
                </Badge>
                <span className="text-xs text-green-700">
                  {userFrames.length > 0 ? `${userFrames.length} フレーム` : "フレーム未取得"}
                </span>
              </div>
              {userFrameError && <div className="text-sm text-red-600">{userFrameError}</div>}
              {userFrameLoading && <div className="text-sm text-green-700">フレームを読み込み中です…</div>}
              {userFrames.length > 0 && (
                <div className="space-y-3">
                  <div className="w-full overflow-hidden rounded-lg border border-green-200 bg-white">
                    <img
                      src={userFrames[userFrameIndex]}
                      alt={`User frame ${userFrameIndex + 1}`}
                      className="w-full object-contain"
                    />
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={Math.max(userFrames.length - 1, 0)}
                    value={userFrameIndex}
                    onChange={(event) => setUserFrameIndex(Number(event.target.value))}
                    className="w-full"
                  />
                  <div className="flex items-center gap-2 flex-wrap">
                    <Button type="button" size="sm" variant="outline" onClick={() => setUserFrameIndex((prev) => clamp(prev - 5, 0, userFrames.length - 1))}>
                      ← 5フレーム
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => setUserFrameIndex((prev) => clamp(prev - 1, 0, userFrames.length - 1))}>
                      ← 1フレーム
                    </Button>
                    <div className="text-sm text-green-900 font-semibold">
                      {formatFrameLabel(userFrameIndex, userFrames.length)}
                    </div>
                    <Button type="button" size="sm" variant="outline" onClick={() => setUserFrameIndex((prev) => clamp(prev + 1, 0, userFrames.length - 1))}>
                      1フレーム →
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => setUserFrameIndex((prev) => clamp(prev + 5, 0, userFrames.length - 1))}>
                      5フレーム →
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-blue-200 bg-blue-50">
            <CardHeader>
              <CardTitle className="text-xl">🎯 参照動画</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant="secondary" className="text-blue-800">
                  {selectedSuggestion?.player ?? "未取得"}
                </Badge>
                <span className="text-sm text-blue-800">{selectedSuggestion?.clipName ?? "-"}</span>
                <span className="text-xs text-blue-700">
                  {referenceFrames.length > 0 ? `${referenceFrames.length} フレーム` : "フレーム未取得"}
                </span>
              </div>
              {referenceFrameError && <div className="text-sm text-red-600">{referenceFrameError}</div>}
              {referenceFrameLoading && <div className="text-sm text-blue-700">フレームを読み込み中です…</div>}
              {referenceFrames.length > 0 && (
                <div className="space-y-3">
                  <div className="w-full overflow-hidden rounded-lg border border-blue-200 bg-white">
                    <img
                      src={referenceFrames[referenceFrameIndex]}
                      alt={`Reference frame ${referenceFrameIndex + 1}`}
                      className="w-full object-contain"
                    />
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={Math.max(referenceFrames.length - 1, 0)}
                    value={referenceFrameIndex}
                    onChange={(event) => setReferenceFrameIndex(Number(event.target.value))}
                    className="w-full"
                  />
                  <div className="flex items-center gap-2 flex-wrap">
                    <Button type="button" size="sm" variant="outline" onClick={() => setReferenceFrameIndex((prev) => clamp(prev - 5, 0, referenceFrames.length - 1))}>
                      ← 5フレーム
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => setReferenceFrameIndex((prev) => clamp(prev - 1, 0, referenceFrames.length - 1))}>
                      ← 1フレーム
                    </Button>
                    <div className="text-sm text-blue-900 font-semibold">
                      {formatFrameLabel(referenceFrameIndex, referenceFrames.length)}
                    </div>
                    <Button type="button" size="sm" variant="outline" onClick={() => setReferenceFrameIndex((prev) => clamp(prev + 1, 0, referenceFrames.length - 1))}>
                      1フレーム →
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => setReferenceFrameIndex((prev) => clamp(prev + 5, 0, referenceFrames.length - 1))}>
                      5フレーム →
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="mt-6 border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="text-2xl">💡 コーチングヒント</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {result.advice.length > 0 ? (
              result.advice.map((item, index) => (
                <div key={index} className="p-4 bg-white border border-blue-100 rounded-lg text-blue-900 leading-relaxed">
                  {item.recommendation}
                </div>
              ))
            ) : (
              <div className="text-sm text-blue-800">
                特筆すべき差分はありません。フォームは非常に良好です！
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
