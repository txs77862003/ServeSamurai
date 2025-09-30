#!/usr/bin/env python3
"""
サーブ動画の自動切り取り機能
LSTMで学習されたデータを利用してサーブの開始から終了までを自動的に検出・切り取り
"""

import os
import sys
import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from pathlib import Path
import json
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent.parent
lstm_path = str(project_root / "30_Classification_LSTM")
sys.path.append(lstm_path)

try:
    from tennis_pose_augmented import AugmentedTennisPoseTrainer, AugmentedLSTM
    from tennis_pose_analysis import TennisPoseAnalyzer
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class ServeAutoClipper:
    """サーブ動画の自動切り取りクラス"""
    
    def __init__(self, model_path=None):
        self.project_root = project_root
        self.model_path = model_path or (project_root / "30_Classification_LSTM" / "best_augmented_model.pth")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # モデルを初期化
        self.lstm_model = None
        self.scaler = None
        self.sequence_length = 48
        self.n_features = 24  # 12キーポイント × 2座標(x,y) - 学習済みモデルに合わせる
        
        print(f"使用デバイス: {self.device}")
        self.load_model()
    
    def load_model(self):
        """学習済みLSTMモデルを読み込み"""
        try:
            if self.model_path.exists():
                # モデルを作成
                self.lstm_model = AugmentedLSTM(
                    input_size=24,  # 12キーポイント × 2座標
                    hidden_size=64,
                    num_layers=2,
                    num_classes=3,
                    dropout=0.3
                ).to(self.device)
                
                # 学習済み重みを読み込み
                self.lstm_model.load_state_dict(torch.load(str(self.model_path), map_location=self.device))
                self.lstm_model.eval()
                
                # スケーラーを初期化（実際の実装では保存されたスケーラーを使用すべき）
                from sklearn.preprocessing import StandardScaler
                self.scaler = StandardScaler()
                
                print("✓ LSTMモデルを正常に読み込みました")
            else:
                print(f"警告: モデルファイルが見つかりません: {self.model_path}")
        except Exception as e:
            print(f"モデル読み込みエラー: {e}")
    
    def extract_keypoints_from_video(self, video_path, output_dir=None):
        """動画からキーポイントを抽出"""
        try:
            # 専用のキーポイント抽出スクリプトを使用
            extractor_script = Path(__file__).parent / "video_keypoint_extractor.py"
            
            if not extractor_script.exists():
                print(f"キーポイント抽出スクリプトが見つかりません: {extractor_script}")
                return None
            
            # 出力ディレクトリを設定
            if output_dir is None:
                output_dir = Path(video_path).parent / "keypoints_output"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(exist_ok=True)
            
            # キーポイント抽出スクリプトを実行
            import subprocess
            cmd = [
                "python3", str(extractor_script),
                str(video_path),
                str(output_dir)
            ]
            
            print(f"キーポイント抽出を実行中: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ キーポイント抽出が完了しました")
                return output_dir
            else:
                print(f"キーポイント抽出エラー: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"キーポイント抽出エラー: {e}")
            return None
    
    def detect_serve_segments(self, keypoints_data):
        """キーポイントデータからサーブセグメントを検出"""
        try:
            if self.lstm_model is None:
                print("LSTMモデルが読み込まれていません")
                return None
            
            # キーポイントデータを読み込み
            if isinstance(keypoints_data, str):
                # CSVファイルから読み込み
                df = pd.read_csv(keypoints_data)
            else:
                df = keypoints_data
            
            # キーポイント列を取得（kpt5-16のx, y座標のみ）
            keypoint_cols = []
            for i in range(5, 17):  # kpt5-16の12キーポイントを使用
                x_col = f'kpt_{i}_x'
                y_col = f'kpt_{i}_y'
                if x_col in df.columns and y_col in df.columns:
                    keypoint_cols.extend([x_col, y_col])
            
            if len(keypoint_cols) == 0:
                print("キーポイントデータが見つかりません")
                return None
            
            if len(keypoint_cols) < 24:
                print(f"警告: 十分なキーポイントがありません。{len(keypoint_cols)}/24")
                # 不足分を0で埋める
                while len(keypoint_cols) < 24:
                    keypoint_cols.append('dummy')
            
            keypoint_cols = keypoint_cols[:24]  # 24特徴量に制限
            print(f"使用するキーポイント: kpt5-16 (12キーポイント)")
            print(f"除外するキーポイント: kpt0-4 (5キーポイント)")
            print(f"特徴量数: {len(keypoint_cols)}")
            
            # データを正規化
            sequences = []
            sequence_length = self.sequence_length
            
            # スライディングウィンドウでシーケンスを生成
            for i in range(0, len(df) - sequence_length + 1, 10):  # 10フレーム間隔
                sequence = df.iloc[i:i + sequence_length][keypoint_cols].values
                if len(sequence) == sequence_length:
                    sequences.append(sequence)
            
            if len(sequences) == 0:
                print("有効なシーケンスが見つかりません")
                return None
            
            # シーケンスを正規化
            sequences = np.array(sequences)
            n_sequences, n_frames, n_features = sequences.shape
            sequences_flat = sequences.reshape(-1, n_features)
            sequences_normalized = self.scaler.fit_transform(sequences_flat)
            sequences_normalized = sequences_normalized.reshape(n_sequences, n_frames, n_features)
            
            # LSTMモデルで予測
            self.lstm_model.eval()
            serve_segments = []
            
            with torch.no_grad():
                for i, sequence in enumerate(sequences_normalized):
                    sequence_tensor = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)
                    prediction = self.lstm_model(sequence_tensor)
                    probabilities = torch.softmax(prediction, dim=1)
                    
                    # 最も高い確率のクラスを取得
                    predicted_class = torch.argmax(probabilities, dim=1).item()
                    confidence = probabilities[0][predicted_class].item()
                    
                    # 信頼度が高い場合のみサーブとして認識
                    if confidence > 0.7:  # 閾値は調整可能
                        start_frame = i * 10
                        end_frame = start_frame + sequence_length
                        serve_segments.append({
                            'start_frame': start_frame,
                            'end_frame': end_frame,
                            'confidence': confidence,
                            'predicted_class': predicted_class
                        })
            
            return serve_segments
            
        except Exception as e:
            print(f"サーブセグメント検出エラー: {e}")
            return None
    
    def clip_serve_videos(self, video_path, serve_segments, output_dir=None):
        """検出されたサーブセグメントから動画を切り取り"""
        try:
            if output_dir is None:
                output_dir = Path(video_path).parent / "clipped_serves"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(exist_ok=True)
            
            # 動画を読み込み
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                print(f"動画ファイルを開けません: {video_path}")
                return None
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps == 0 or total_frames == 0:
                print(f"無効な動画ファイル: FPS={fps}, 総フレーム数={total_frames}")
                cap.release()
                return None
            
            print(f"動画情報: FPS={fps}, 総フレーム数={total_frames}")
            
            clipped_videos = []
            
            for i, segment in enumerate(serve_segments):
                start_frame = segment['start_frame']
                end_frame = min(segment['end_frame'], total_frames)
                confidence = segment['confidence']
                
                # 出力ファイル名を生成
                video_name = Path(video_path).stem
                output_filename = f"{video_name}_serve_{i+1}_conf{confidence:.2f}.mp4"
                output_path = output_dir / output_filename
                
                # フレーム範囲を設定
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                
                # 動画ライターを初期化
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(
                    str(output_path),
                    fourcc,
                    fps,
                    (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
                )
                
                # フレームを書き込み
                for frame_idx in range(start_frame, end_frame):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                
                out.release()
                
                clipped_videos.append({
                    'path': str(output_path),
                    'start_frame': start_frame,
                    'end_frame': end_frame,
                    'start_time': start_frame / fps,
                    'end_time': end_frame / fps,
                    'confidence': confidence,
                    'duration': (end_frame - start_frame) / fps
                })
                
                print(f"✓ サーブ動画を保存: {output_path}")
            
            cap.release()
            return clipped_videos
            
        except Exception as e:
            print(f"動画切り取りエラー: {e}")
            return None
    
    def process_video(self, video_path, output_dir=None):
        """動画を完全に処理（キーポイント抽出→サーブ検出→切り取り）"""
        try:
            print(f"=== サーブ動画の自動処理開始: {video_path} ===")
            
            video_path = Path(video_path)
            if not video_path.exists():
                print(f"動画ファイルが見つかりません: {video_path}")
                return None
            
            # 出力ディレクトリを設定
            if output_dir is None:
                output_dir = video_path.parent / f"{video_path.stem}_processed"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(exist_ok=True)
            
            # 1. キーポイントを抽出
            print("1. キーポイント抽出中...")
            keypoints_dir = self.extract_keypoints_from_video(
                video_path, 
                output_dir / "keypoints"
            )
            
            if keypoints_dir is None:
                print("キーポイント抽出に失敗しました")
                return None
            
            # キーポイントCSVファイルを探す
            keypoints_csv = keypoints_dir / "keypoints.csv"
            
            if not keypoints_csv.exists():
                print(f"キーポイントCSVファイルが見つかりません: {keypoints_csv}")
                return None
            
            # 2. サーブセグメントを検出
            print("2. サーブセグメント検出中...")
            serve_segments = self.detect_serve_segments(str(keypoints_csv))
            
            if not serve_segments:
                print("サーブセグメントが検出されませんでした")
                return None
            
            print(f"✓ {len(serve_segments)}個のサーブセグメントを検出")
            
            # 3. 動画を切り取り
            print("3. サーブ動画切り取り中...")
            clipped_videos = self.clip_serve_videos(
                video_path,
                serve_segments,
                output_dir / "clipped_serves"
            )
            
            if clipped_videos:
                # 結果をJSONファイルに保存
                result = {
                    'original_video': str(video_path),
                    'processed_at': datetime.now().isoformat(),
                    'serve_segments': serve_segments,
                    'clipped_videos': clipped_videos,
                    'total_serves': len(clipped_videos)
                }
                
                result_file = output_dir / "processing_result.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"✓ 処理完了: {len(clipped_videos)}個のサーブ動画を生成")
                print(f"✓ 結果ファイル: {result_file}")
                
                return result
            else:
                print("動画切り取りに失敗しました")
                return None
                
        except Exception as e:
            print(f"動画処理エラー: {e}")
            return None

def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python serve_auto_clipper.py <動画ファイルパス> [出力ディレクトリ]")
        sys.exit(1)
    
    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 自動切り取り器を初期化
    clipper = ServeAutoClipper()
    
    # 動画を処理
    result = clipper.process_video(video_path, output_dir)
    
    if result:
        print("\n=== 処理結果 ===")
        print(f"元動画: {result['original_video']}")
        print(f"検出されたサーブ数: {result['total_serves']}")
        print("切り取られたサーブ動画:")
        for i, video in enumerate(result['clipped_videos'], 1):
            print(f"  {i}. {video['path']}")
            print(f"     時間: {video['start_time']:.2f}s - {video['end_time']:.2f}s")
            print(f"     信頼度: {video['confidence']:.3f}")
    else:
        print("処理に失敗しました")

if __name__ == "__main__":
    main()
