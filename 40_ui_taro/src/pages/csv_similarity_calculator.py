#!/usr/bin/env python3
import sys
import json
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from pose_analysis.comparison import compare_from_csv
    from pose_analysis.pose_metrics import PoseMetrics
except ImportError as e:
    print(json.dumps({"success": False, "error": f"Import error: {e}"}))
    sys.exit(1)

def find_most_similar_csv(user_csv_path, player_name):
    """指定されたプレイヤーのCSVファイルの中で最も類似度の高いものを検索"""
    try:
        # プレイヤーのCSVファイルディレクトリを検索
        players_dir = project_root / "pose_tracks" / "Cleaned_Data" / "players" / player_name
        
        if not players_dir.exists():
            return {
                "success": False,
                "error": f"Player directory not found: {players_dir}"
            }
        
        # プレイヤーディレクトリ内のCSVファイルを検索
        csv_files = list(players_dir.glob("**/keypoints_with_tracks.csv"))
        
        if not csv_files:
            return {
                "success": False,
                "error": f"No CSV files found for player: {player_name}"
            }
        
        best_match = None
        best_similarity = float('inf')  # 距離なので小さいほど良い
        
        # 各CSVファイルとの類似度を計算
        for csv_file in csv_files:
            try:
                # 相対パスに変換
                rel_path = csv_file.relative_to(project_root)
                
                # 類似度計算（絶対パスを使用）
                result = compare_from_csv(str(user_csv_path), str(csv_file))
                
                if result:
                    # PoseMetricDiffから類似度を計算（各メトリックの差分の絶対値の合計）
                    similarity = (
                        abs(result.trophy_knee_angle_diff) +
                        abs(result.trophy_right_arm_extension_diff) +
                        abs(result.trophy_left_arm_lift_diff) +
                        (abs(result.impact_right_shoulder_angle_diff) if result.impact_right_shoulder_angle_diff is not None else 0)
                    )
                    
                    if similarity < best_similarity:
                        best_similarity = similarity
                        best_match = {
                            "csv_path": str(rel_path),
                            "similarity": similarity,
                            "player": player_name
                        }
                        
            except Exception as e:
                print(f"Error comparing with {csv_file}: {e}", file=sys.stderr)
                continue
        
        if best_match is None:
            return {
                "success": False,
                "error": "No valid comparisons could be made"
            }
        
        return {
            "success": True,
            "best_match": best_match
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error in similarity calculation: {e}"
        }

def main():
    try:
        # 標準入力からJSONデータを読み取り
        input_data = json.loads(sys.stdin.read())
        user_csv = input_data.get('userCsv')
        player_name = input_data.get('playerName')
        
        if not user_csv or not player_name:
            print(json.dumps({"success": False, "error": "Missing userCsv or playerName"}))
            return
        
        # ユーザーCSVファイルの存在確認
        user_csv_path = project_root / user_csv
        if not user_csv_path.exists():
            print(json.dumps({"success": False, "error": f"User CSV not found: {user_csv}"}))
            return
        
        # 類似度計算実行
        result = find_most_similar_csv(str(user_csv_path), player_name)
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Main error: {e}"}))

if __name__ == "__main__":
    main()