#!/usr/bin/env python3
"""
動画からキーポイントを抽出するスクリプト
YOLOを使用して人体のキーポイントを検出し、CSVファイルに出力
"""

import os
import sys
import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO
from pathlib import Path

def extract_keypoints_from_video(video_path, output_dir):
    """動画からキーポイントを抽出"""
    try:
        # YOLOモデルを読み込み
        model_path = Path(__file__).parent.parent / "22_Joint_Detection_YOLO" / "yolo11n-pose.pt"
        if not model_path.exists():
            print(f"YOLOモデルが見つかりません: {model_path}")
            return None
        
        model = YOLO(str(model_path))
        
        # 動画を読み込み
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"動画ファイルを開けません: {video_path}")
            return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"動画情報: {width}x{height}, FPS={fps}, 総フレーム数={total_frames}")
        
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # キーポイントデータを格納するリスト
        keypoint_data = []
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # YOLOでキーポイントを検出
            results = model(frame, verbose=False)
            
            # 最も信頼度の高い人物を選択
            best_person = None
            best_confidence = 0
            
            for result in results:
                if result.keypoints is not None and len(result.keypoints.data) > 0:
                    for person in result.keypoints.data:
                        # 最初のキーポイントの信頼度をチェック
                        if len(person) > 0 and person[0][2] > best_confidence:
                            best_confidence = person[0][2]
                            best_person = person
            
            if best_person is not None:
                # キーポイントデータを抽出
                frame_data = {
                    'frame_name': f"frame_{frame_idx:06d}.jpg",
                    'frame_idx': frame_idx,
                    'timestamp': frame_idx / fps
                }
                
                # 各キーポイントのx, y座標と信頼度を追加（kpt5-16のみ）
                for i, (x, y, conf) in enumerate(best_person):
                    if i >= 5:  # kpt5-16のみを使用
                        frame_data[f'kpt_{i}_x'] = float(x)
                        frame_data[f'kpt_{i}_y'] = float(y)
                        frame_data[f'kpt_{i}_conf'] = float(conf)
                
                keypoint_data.append(frame_data)
            else:
                # キーポイントが検出されない場合は空のデータを追加
                frame_data = {
                    'frame_name': f"frame_{frame_idx:06d}.jpg",
                    'frame_idx': frame_idx,
                    'timestamp': frame_idx / fps
                }
                
                for i in range(5, 17):  # kpt5-16のみ（12キーポイント）
                    frame_data[f'kpt_{i}_x'] = 0.0
                    frame_data[f'kpt_{i}_y'] = 0.0
                    frame_data[f'kpt_{i}_conf'] = 0.0
                
                keypoint_data.append(frame_data)
            
            frame_idx += 1
            
            # 進捗表示
            if frame_idx % 30 == 0:
                print(f"処理中... {frame_idx}/{total_frames} フレーム ({frame_idx/total_frames*100:.1f}%)")
        
        cap.release()
        
        # DataFrameを作成してCSVファイルに保存
        if keypoint_data:
            df = pd.DataFrame(keypoint_data)
            csv_path = output_path / "keypoints.csv"
            df.to_csv(csv_path, index=False)
            
            print(f"✓ キーポイント抽出完了: {csv_path}")
            print(f"  抽出フレーム数: {len(keypoint_data)}")
            print(f"  キーポイント数: 17個/フレーム")
            
            return str(csv_path)
        else:
            print("キーポイントデータが抽出されませんでした")
            return None
            
    except Exception as e:
        print(f"キーポイント抽出エラー: {e}")
        return None

def main():
    """メイン処理"""
    if len(sys.argv) < 3:
        print("使用方法: python video_keypoint_extractor.py <動画ファイル> <出力ディレクトリ>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    csv_path = extract_keypoints_from_video(video_path, output_dir)
    
    if csv_path:
        print(f"成功: {csv_path}")
        sys.exit(0)
    else:
        print("失敗")
        sys.exit(1)

if __name__ == "__main__":
    main()
