#!/usr/bin/env python3
"""
サーブ自動切り取り機能のテストスクリプト
"""

import sys
import os
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from serve_auto_clipper import ServeAutoClipper

def test_with_sample_video():
    """サンプル動画でテスト"""
    
    # サンプル動画のパス（実際の動画ファイルに置き換えてください）
    sample_videos = [
        project_root / "tennis_videos" / "kei_serve_back1.mp4",
        project_root / "clips" / "kei_serve_back1_kei,back,serve,deuce___.mp4"
    ]
    
    for video_path in sample_videos:
        if video_path.exists():
            print(f"テスト動画: {video_path}")
            
            # 自動切り取り器を初期化
            clipper = ServeAutoClipper()
            
            # 動画を処理
            result = clipper.process_video(video_path)
            
            if result:
                print("\n=== 処理結果 ===")
                print(f"元動画: {result['original_video']}")
                print(f"検出されたサーブ数: {result['total_serves']}")
                print("切り取られたサーブ動画:")
                for i, video in enumerate(result['clipped_videos'], 1):
                    print(f"  {i}. {video['path']}")
                    print(f"     時間: {video['start_time']:.2f}s - {video['end_time']:.2f}s")
                    print(f"     信頼度: {video['confidence']:.3f}")
                break
            else:
                print("処理に失敗しました")
        else:
            print(f"サンプル動画が見つかりません: {video_path}")
    
    else:
        print("利用可能なサンプル動画が見つかりません")

def test_model_loading():
    """モデル読み込みのテスト"""
    print("=== モデル読み込みテスト ===")
    
    try:
        clipper = ServeAutoClipper()
        if clipper.lstm_model is not None:
            print("✓ LSTMモデルの読み込みに成功しました")
        else:
            print("✗ LSTMモデルの読み込みに失敗しました")
    except Exception as e:
        print(f"✗ エラー: {e}")

def main():
    """メイン処理"""
    print("=== サーブ自動切り取り機能テスト ===")
    
    # 1. モデル読み込みテスト
    test_model_loading()
    
    # 2. サンプル動画でのテスト
    test_with_sample_video()

if __name__ == "__main__":
    main()
