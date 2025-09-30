'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import ManualVideoClipper from '@/components/ManualVideoClipper';
import StepIndicator from '@/components/StepIndicator';
import { useEffect, useState } from 'react';

export default function ManualClipPage() {
  const [uploadedFileName, setUploadedFileName] = useState<string>('');
  const [hasVideo, setHasVideo] = useState<boolean>(false);

  useEffect(() => {
    // sessionStorageから動画情報を取得
    const fileName = sessionStorage.getItem('uploadedFileName');
    const videoFileData = sessionStorage.getItem('uploadedVideoFile');
    
    console.log('manual-clip/page - fileName:', fileName);
    console.log('manual-clip/page - videoFileData:', videoFileData);
    
    if (fileName && videoFileData) {
      try {
        const fileData = JSON.parse(videoFileData);
        if (fileData.name && (fileData.data || fileData.size > 0)) {
          setUploadedFileName(fileData.name);
          setHasVideo(true);
          console.log('manual-clip/page - Video detected:', fileData.name);
        }
      } catch (error) {
        console.error('manual-clip/page - Error parsing videoFileData:', error);
      }
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
      <div className="container mx-auto py-8">
        <StepIndicator currentStep={2} />
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                ✂️ サーブ動画クリッピング
              </h1>
              <p className="text-lg text-gray-600">
                アップロードした動画から、サーブ部分を手動で切り取りましょう
              </p>
            </div>
            <div className="flex gap-2">
              <Link href="/">
                <Button variant="outline">
                  ← Back
                </Button>
              </Link>
              <Link href="/results">
                <Button 
                  variant="outline"
                  disabled={!hasVideo}
                >
                  Next: Results →
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {hasVideo ? (
          <div className="space-y-6">
            <Card className="bg-green-50 border-green-200">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <p className="text-green-800 font-medium">
                    アップロード済み: {uploadedFileName}
                  </p>
                </div>
              </CardContent>
            </Card>
            
            <ManualVideoClipper />
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>⚠️ 動画がアップロードされていません</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-600">
                クリッピングを行うには、まずホーム画面で動画をアップロードしてください。
              </p>
              <Link href="/">
                <Button>
                  🏠 Go Home & Upload Video
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
