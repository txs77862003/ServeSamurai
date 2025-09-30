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
    from pose_analysis.advice import generate_advice
    from pose_analysis.pose_metrics import compute_pose_metrics
except ImportError as e:
    print(json.dumps({"success": False, "error": f"Import error: {e}"}))
    sys.exit(1)

def process_pose_advice(data):
    """ポーズアドバイスを生成"""
    try:
        user_csv = data.get('userCsv')
        reference_csv = data.get('referenceCsv')
        
        if not user_csv or not reference_csv:
            return {
                "success": False,
                "error": "userCsv and referenceCsv are required"
            }
        
        # 絶対パスに変換
        user_csv_path = project_root / user_csv
        reference_csv_path = project_root / reference_csv
        
        if not user_csv_path.exists():
            return {
                "success": False,
                "error": f"User CSV not found: {user_csv}"
            }
        
        if not reference_csv_path.exists():
            return {
                "success": False,
                "error": f"Reference CSV not found: {reference_csv}"
            }
        
        # ポーズ比較実行
        comparison_result = compare_from_csv(str(user_csv_path), str(reference_csv_path))
        
        if not comparison_result:
            return {
                "success": False,
                "error": "Failed to compare pose data"
            }
        
        # アドバイス生成
        advice = generate_advice(comparison_result)
        
        return {
            "success": True,
            "user_metrics": comparison_result.user_metrics.__dict__ if hasattr(comparison_result, 'user_metrics') else {},
            "reference_metrics": comparison_result.reference_metrics.__dict__ if hasattr(comparison_result, 'reference_metrics') else {},
            "difference": comparison_result.difference.__dict__ if hasattr(comparison_result, 'difference') else {},
            "advice": [adv.__dict__ for adv in advice] if isinstance(advice, list) else [advice.__dict__]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error processing pose advice: {e}"
        }

def main():
    try:
        # 標準入力からJSONデータを読み取り
        input_data = json.loads(sys.stdin.read())
        
        # ポーズアドバイス処理実行
        result = process_pose_advice(input_data)
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Main error: {e}"}))

if __name__ == "__main__":
    main()