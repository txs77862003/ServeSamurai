import os
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from ultralytics import YOLO

# 入力設定（スクリプト位置基準の絶対パスに解決）
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = str(SCRIPT_DIR.parent)
IMAGE_DIR = str((SCRIPT_DIR.parent / "frames").resolve())
# 既存モデルの場所を環境変数から受け取り、未指定なら /tmp を使用
MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "/tmp/yolo11n-pose.pt")

# 書き込み不可環境対策: キャッシュや一時ファイルの保存先を /tmp に固定（未設定時）
os.environ.setdefault("ULTRALYTICS_CACHE_DIR", "/tmp")
os.environ.setdefault("TMPDIR", "/tmp")
os.environ.setdefault("HOME", "/tmp")

# トラッキング設定
TRACK_DISTANCE_THRESHOLD = 150.0  # キーポイント中心同士がこの距離以内なら同一人物とみなす
MAX_MISSED_FRAMES = 30            # 連続で見失ったフレーム数の上限


model = YOLO(MODEL_PATH)

# 出力用ディレクトリ
COORDS_DIR = os.path.join(IMAGE_DIR, "pose_coords_yolo")
VIS_DIR = os.path.join(IMAGE_DIR, "pose_visualization")
# pose_tracks は frames と同じ階層に出力
TRACK_DIR = os.path.join(PROJECT_ROOT, "pose_tracks")
for path in (COORDS_DIR, VIS_DIR, TRACK_DIR):
    os.makedirs(path, exist_ok=True)

EXCLUDED_DIRS = {os.path.abspath(COORDS_DIR), os.path.abspath(VIS_DIR), os.path.abspath(TRACK_DIR)}


def initialise_player_roots(image_dir):
    """Ensure output roots contain the same top-level player folders as ``image_dir``."""

    player_dirs = []
    for entry in sorted(os.listdir(image_dir)):
        abs_path = os.path.abspath(os.path.join(image_dir, entry))
        if abs_path in EXCLUDED_DIRS:
            continue
        if os.path.isdir(abs_path):
            player_dirs.append(entry)

    if not player_dirs:
        return

    for base in (COORDS_DIR, VIS_DIR, TRACK_DIR):
        for player in player_dirs:
            os.makedirs(os.path.join(base, player), exist_ok=True)


initialise_player_roots(IMAGE_DIR)


def gather_frame_groups(base_dir):
    """フレーム画像のサブフォルダをまとめて取得する"""
    groups = []
    for root, dirs, files in os.walk(base_dir):
        # 生成した出力ディレクトリを探索対象から除外
        dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) not in EXCLUDED_DIRS]

        image_files = sorted(
            f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff"))
        )
        if not image_files:
            continue
        groups.append((root, [os.path.join(root, f) for f in image_files]))

    groups.sort(key=lambda item: item[0])
    return groups


def make_subdir(base, relative):
    path = base if not relative else os.path.join(base, relative)
    os.makedirs(path, exist_ok=True)
    return path


def flatten_keypoints_row(frame_index, frame_name, track_id, keypoints):
    row = {"frame_index": frame_index, "frame_name": frame_name, "track_id": track_id}
    # kpt_0 ～ kpt_4 は出力しない
    for idx, (x, y) in enumerate(keypoints):
        if idx < 5:
            continue
        row[f"kpt_{idx}_x"] = float(x)
        row[f"kpt_{idx}_y"] = float(y)
    return row


def _strip_cleaned_data_prefix(rel_path: str) -> str:
    """If relative path starts with Cleaned_Data, drop that first segment."""
    if not rel_path:
        return rel_path
    parts = Path(rel_path).parts
    if parts and parts[0] == "Cleaned_Data":
        parts = parts[1:]
    return os.path.join(*parts) if parts else ""


frame_groups = gather_frame_groups(IMAGE_DIR)

if not frame_groups:
    print("⚠️ 対象となるフレームが見つかりませんでした。")
    raise SystemExit

processed_frames = 0

for clip_root, image_paths in frame_groups:
    relative_path = os.path.relpath(clip_root, IMAGE_DIR)
    clip_relative = "" if relative_path == "." else _strip_cleaned_data_prefix(relative_path)
    clip_display = clip_relative if clip_relative else os.path.basename(clip_root)

    coords_dir = make_subdir(COORDS_DIR, clip_relative)
    viz_dir = make_subdir(VIS_DIR, clip_relative)
    tracks_output_dir = make_subdir(TRACK_DIR, clip_relative)

    tracks = {}
    next_track_id = 0
    clip_records = []
    keypoint_count = None

    for frame_index, image_path in enumerate(image_paths):
        processed_frames += 1
        frame_name = os.path.basename(image_path)
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ 画像を読み込めませんでした: {frame_name}")
            continue

        results = model(image)
        result = results[0]
        annotated_image = result.plot()

        keypoints_tensor = result.keypoints
        if keypoints_tensor is None:
            keypoints_array = np.empty((0, 0, 2))
        else:
            keypoints_array = keypoints_tensor.xy.cpu().numpy()

        boxes_tensor = result.boxes
        boxes_array = boxes_tensor.xyxy.cpu().numpy() if boxes_tensor is not None else np.empty((0, 4))

        num_people = keypoints_array.shape[0]
        frame_rows = []

        if num_people > 0:
            if keypoint_count is None:
                keypoint_count = keypoints_array.shape[1]

            centers = keypoints_array.mean(axis=1)
            unmatched = set(range(num_people))
            detection_to_track = {}

            for track_id in sorted(tracks.keys()):
                track = tracks[track_id]
                if not track["active"]:
                    continue
                if track["last_center"] is None:
                    continue

                best_det = None
                best_distance = TRACK_DISTANCE_THRESHOLD
                for det_idx in sorted(unmatched):
                    distance = np.linalg.norm(track["last_center"] - centers[det_idx])
                    if distance < best_distance:
                        best_distance = distance
                        best_det = det_idx

                if best_det is not None:
                    detection_to_track[best_det] = track_id
                    unmatched.remove(best_det)

            for det_idx in sorted(unmatched):
                track_id = next_track_id
                next_track_id += 1
                tracks[track_id] = {
                    "last_keypoints": None,
                    "last_center": None,
                    "total_movement": 0.0,
                    "frames": [],
                    "missed": 0,
                    "active": True,
                }
                detection_to_track[det_idx] = track_id

            matched_track_ids = set(detection_to_track.values())

            for det_idx in range(num_people):
                track_id = detection_to_track.get(det_idx)
                if track_id is None:
                    continue

                keypoints = keypoints_array[det_idx]
                center = centers[det_idx]
                track = tracks[track_id]

                prev_keypoints = track["last_keypoints"]
                if prev_keypoints is not None and prev_keypoints.shape == keypoints.shape:
                    displacement = np.linalg.norm(keypoints - prev_keypoints, axis=1).sum()
                    track["total_movement"] += float(displacement)

                track["last_keypoints"] = keypoints
                track["last_center"] = center
                track["frames"].append(frame_name)
                track["missed"] = 0
                track["active"] = True

                row = flatten_keypoints_row(frame_index, frame_name, track_id, keypoints)
                clip_records.append(row)
                frame_rows.append(row.copy())

                if det_idx < boxes_array.shape[0]:
                    x1, y1, x2, y2 = boxes_array[det_idx]
                    label_position = (int(x1), int(max(0, y1 - 10)))
                    cv2.putText(
                        annotated_image,
                        f"ID {track_id}",
                        label_position,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )

            for track_id, track in tracks.items():
                if track_id not in matched_track_ids and track["active"]:
                    track["missed"] += 1
                    if track["missed"] > MAX_MISSED_FRAMES:
                        track["active"] = False
        else:
            for track in tracks.values():
                if track["active"]:
                    track["missed"] += 1
                    if track["missed"] > MAX_MISSED_FRAMES:
                        track["active"] = False

        frame_base = os.path.splitext(frame_name)[0]
        frame_csv_path = os.path.join(coords_dir, f"{frame_base}_coords.csv")
        frame_viz_path = os.path.join(viz_dir, f"{frame_base}_pose_visualized.jpg")

        if frame_rows:
            frame_df = pd.DataFrame(frame_rows)
        else:
            base_columns = ["frame_index", "frame_name", "track_id"]
            if keypoint_count is not None:
                for idx in range(keypoint_count):
                    base_columns.extend([f"kpt_{idx}_x", f"kpt_{idx}_y"])
            frame_df = pd.DataFrame(columns=base_columns)

        frame_df.to_csv(frame_csv_path, index=False)
        cv2.imwrite(frame_viz_path, annotated_image)
        print(f"✅ {clip_display}/{frame_name}: 座標保存完了 & 可視化画像保存完了")

    if clip_records:
        clip_df = pd.DataFrame(clip_records)
        # kpt列は kpt_5 → kpt_16（各 _x, _y）の順にソートして出力
        ordered_kpt_cols = []
        for idx in range(5, 17):
            x_col = f"kpt_{idx}_x"
            y_col = f"kpt_{idx}_y"
            if x_col in clip_df.columns:
                ordered_kpt_cols.append(x_col)
            if y_col in clip_df.columns:
                ordered_kpt_cols.append(y_col)
        ordered_columns = ["frame_index", "frame_name", "track_id"] + ordered_kpt_cols
        clip_df = clip_df.reindex(columns=ordered_columns)
        clip_csv_path = os.path.join(tracks_output_dir, "keypoints_with_tracks.csv")
        clip_df.to_csv(clip_csv_path, index=False)

    summary_rows = []
    for track_id, track in sorted(tracks.items()):
        if not track["frames"]:
            continue
        summary_rows.append(
            {
                "track_id": track_id,
                "total_movement": track["total_movement"],
                "num_frames": len(track["frames"]),
                "first_frame": track["frames"][0],
                "last_frame": track["frames"][-1],
                "active": track["active"],
            }
        )

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        summary_csv_path = os.path.join(tracks_output_dir, "movement_summary.csv")
        summary_df.to_csv(summary_csv_path, index=False)

        most_active = max(summary_rows, key=lambda item: item["total_movement"])
        print(
            f"🏃 {clip_display}: ID {most_active['track_id']} が最も動いています (総移動量 {most_active['total_movement']:.2f})"
        )
    else:
        print(f"⚠️ {clip_display}: キーポイントを取得できませんでした。")

print(f"✅ 処理完了: {processed_frames} フレームを解析しました。")
