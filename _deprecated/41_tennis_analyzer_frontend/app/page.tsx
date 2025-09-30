"use client";

import { useCallback, useMemo, useRef, useState } from "react";

type AnalyzeResponse = {
  // 解析サーバーの返却に合わせて調整してください
  ok: boolean;
  id: string;
  filename: string;
  size_bytes: number;
  serve_speed?: number;
  form?: string;
  classification?: string;
  advice?: string[];
  [k: string]: any;
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";
  const canSubmit = useMemo(() => !!file && !uploading, [file, uploading]);

  const onPick = useCallback((f: File | null) => {
    setError(null);
    setResult(null);
    setProgress(0);
    setFile(f);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(f ? URL.createObjectURL(f) : null);
  }, [preview]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    if (!f) return onPick(null);
    if (!f.type.startsWith("video/")) {
      setError("動画ファイルを選んでください（mp4 など）");
      return onPick(null);
    }
    // 例: 200MB 超は弾く（必要に応じて調整）
    if (f.size > 200 * 1024 * 1024) {
      setError("ファイルサイズは 200MB 以下にしてください");
      return onPick(null);
    }
    onPick(f);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0] ?? null;
    if (!f) return;
    (inputRef.current as HTMLInputElement).files = e.dataTransfer.files;
    handleFileChange({ target: inputRef.current! } as any);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    setProgress(0);

    // fetch では onUploadProgress が使えないため、XHR を使用してプログレス表示
    const form = new FormData();
    form.append("file", file, file.name);

    const xhr = new XMLHttpRequest();
    const url = `${apiBase}/analyze`;
    console.log("API URL:", url);
    console.log("File:", file.name, file.type, file.size);
    xhr.open("POST", url, true);

    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) {
        setProgress(Math.round((ev.loaded / ev.total) * 100));
      }
    };

    xhr.onerror = () => {
      setError("アップロードに失敗しました（ネットワークエラー）");
      setUploading(false);
    };

    xhr.onload = () => {
      setUploading(false);
      console.log("Response status:", xhr.status);
      console.log("Response text:", xhr.responseText);
      try {
        if (xhr.status >= 200 && xhr.status < 300) {
          const data = JSON.parse(xhr.responseText || "{}");
          setResult(data);
        } else {
          const errorData = JSON.parse(xhr.responseText || "{}");
          setError(`サーバーエラー: ${xhr.status} ${xhr.statusText} - ${errorData.detail || 'Unknown error'}`);
        }
      } catch (e) {
        console.error("Parse error:", e);
        setError(`サーバーからの応答を解析できませんでした: ${xhr.responseText}`);
      }
    };

    xhr.send(form);
  };

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-black">🎾 テニス動画解析</h1>
        <p className="mt-1 text-gray-600">
          自分の動画をアップロードしてください。
        </p>

        {/* アップロードカード */}
        <div
          className="mt-6 rounded-2xl border border-dashed border-gray-300 bg-white p-6 hover:border-gray-400 transition"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <div className="flex items-center gap-4">
            <input
              ref={inputRef}
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              className="hidden"
            />
            <button
              onClick={() => inputRef.current?.click()}
              className="rounded-lg border px-4 py-2 font-medium hover:bg-gray-80"
            >
              ファイルを選ぶ
            </button>
            <span className="text-gray-500">
              もしくはここに動画をドラッグ＆ドロップ
            </span>
          </div>

          {/* プレビュー */}
          {preview && (
            <div className="mt-4">
              <video
                src={preview}
                className="w-full rounded-lg"
                controls
                preload="metadata"
              />
              <p className="mt-2 text-sm text-gray-500">
                選択中: <span className="font-medium">{file?.name}</span>{" "}
                ({Math.round((file!.size / (1024*1024)) * 10) / 10} MB)
              </p>
            </div>
          )}

          {/* エラー */}
          {error && (
            <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* 送信ボタン & 進捗 */}
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleUpload}
              disabled={!canSubmit}
              className={`rounded-lg px-4 py-2 font-semibold text-white ${
                canSubmit ? "bg-blue-600 hover:bg-blue-700" : "bg-blue-300 cursor-not-allowed"
              }`}
            >
              解析する
            </button>
            {uploading && (
              <div className="flex-1">
                <div className="h-2 w-full rounded bg-gray-200">
                  <div
                    className="h-2 rounded bg-blue-600 transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-gray-600">{progress}%</p>
              </div>
            )}
          </div>
        </div>

        {/* 結果表示 */}
        {result && (
          <div className="mt-6 rounded-2xl border bg-white p-6">
            <h2 className="text-lg font-semibold dark:text-black">解析結果</h2>
            
            {/* 基本情報 */}
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-blue-50 p-4">
                <h3 className="font-medium text-blue-900">サーブ速度</h3>
                <p className="text-2xl font-bold text-blue-600">
                  {result.serve_speed || 'N/A'} km/h
                </p>
              </div>
              <div className="rounded-lg bg-green-50 p-4">
                <h3 className="font-medium text-green-900">フォーム評価</h3>
                <p className="text-lg font-semibold text-green-600">
                  {result.form || 'N/A'}
                </p>
              </div>
            </div>

            {/* 分類結果 */}
            {result.classification && (
              <div className="mt-4 rounded-lg bg-purple-50 p-4">
                <h3 className="font-medium text-purple-900">サーブ分類</h3>
                <p className="text-lg text-purple-700">{result.classification}</p>
              </div>
            )}

            {/* アドバイス */}
            {result.advice && result.advice.length > 0 && (
              <div className="mt-4 rounded-lg bg-yellow-50 p-4">
                <h3 className="font-medium text-yellow-900">アドバイス</h3>
                <ul className="mt-2 space-y-1">
                  {result.advice.map((tip, index) => (
                    <li key={index} className="text-yellow-700">
                      • {tip}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* デバッグ情報（開発時のみ） */}
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-gray-600">
                デバッグ情報を表示
              </summary>
              <pre className="mt-2 overflow-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* フッタ */}
        <div className="mt-10 text-xs text-gray-500">
          API: <code>{process.env.NEXT_PUBLIC_API_BASE}/analyze</code>
        </div>
      </div>
    </main>
  );
}
