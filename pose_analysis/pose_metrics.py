"""Utilities for extracting key tennis pose metrics from pose-tracking CSV files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# Mapping based on COCO keypoint indices used in pose_tracks CSVs.
KEYPOINT_NAME_TO_ID: Dict[str, int] = {
    "nose": 0,
    "left_eye": 1,
    "right_eye": 2,
    "left_ear": 3,
    "right_ear": 4,
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_wrist": 9,
    "right_wrist": 10,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16,
}


def _column_names(joint_id: int) -> Tuple[str, str]:
    return (f"kpt_{joint_id}_x", f"kpt_{joint_id}_y")


def load_pose_sequence(csv_path: Path | str) -> pd.DataFrame:
    """Load a keypoint CSV into a DataFrame indexed by frame."""
    df = pd.read_csv(csv_path)
    if "frame_index" in df.columns:
        df = df.set_index("frame_index")
    return df


def get_joint_series(df: pd.DataFrame, joint_name: str) -> np.ndarray:
    """Return an (n_frames, 2) array of XY coordinates for the given joint."""
    joint_id = KEYPOINT_NAME_TO_ID[joint_name]
    x_col, y_col = _column_names(joint_id)
    if x_col not in df.columns or y_col not in df.columns:
        raise KeyError(
            f"Joint '{joint_name}' (columns '{x_col}', '{y_col}') not present in data"
        )
    return df[[x_col, y_col]].to_numpy(dtype=np.float64)


def compute_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Vectorised angle (in degrees) for points A-B-C across frames."""
    ba = a - b
    bc = c - b
    # Norms of the vectors, add epsilon to avoid division by zero.
    ba_norm = np.linalg.norm(ba, axis=1)
    bc_norm = np.linalg.norm(bc, axis=1)
    denom = ba_norm * bc_norm
    denom[denom == 0] = np.finfo(float).eps
    cos_angle = np.einsum("ij,ij->i", ba, bc) / denom
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return np.degrees(np.arccos(cos_angle))


def knee_angles(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    return {
        "left": compute_angle(
            get_joint_series(df, "left_hip"),
            get_joint_series(df, "left_knee"),
            get_joint_series(df, "left_ankle"),
        ),
        "right": compute_angle(
            get_joint_series(df, "right_hip"),
            get_joint_series(df, "right_knee"),
            get_joint_series(df, "right_ankle"),
        ),
    }


def shoulder_elbow_metrics(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    return {
        "right_arm_extension": compute_angle(
            get_joint_series(df, "left_shoulder"),
            get_joint_series(df, "right_shoulder"),
            get_joint_series(df, "right_elbow"),
        ),
        "left_arm_lift": compute_angle(
            get_joint_series(df, "left_elbow"),
            get_joint_series(df, "left_shoulder"),
            get_joint_series(df, "right_shoulder"),
        ),
    }


def right_ear_shoulder_elbow_angle(df: pd.DataFrame) -> Optional[np.ndarray]:
    """Return shoulder-elbow angle using right ear, falling back to right eye."""

    for anchor in ("right_ear", "right_eye"):
        try:
            return compute_angle(
                get_joint_series(df, anchor),
                get_joint_series(df, "right_shoulder"),
                get_joint_series(df, "right_elbow"),
            )
        except KeyError:
            continue
    return None


def find_min_angle_frame(angle_series: np.ndarray, frame_range: Tuple[int, int]) -> int:
    start, end = frame_range
    end = min(end, len(angle_series) - 1)
    window = angle_series[start : end + 1]
    offset = np.nanargmin(window)
    return start + int(offset)


def find_min_y_frame(y_series: np.ndarray, frame_range: Tuple[int, int]) -> int:
    start, end = frame_range
    end = min(end, len(y_series) - 1)
    window = y_series[start : end + 1]
    offset = np.nanargmin(window)
    return start + int(offset)


def find_trophy_frame(df: pd.DataFrame, frame_range: Tuple[int, int] = (15, 30)) -> int:
    knees = knee_angles(df)
    combined = np.vstack([knees["left"], knees["right"]])
    min_series = np.nanmin(combined, axis=0)
    return find_min_angle_frame(min_series, frame_range)


def find_impact_frame(
    df: pd.DataFrame, frame_range: Tuple[int, int] = (25, 40)
) -> int:
    right_elbow = get_joint_series(df, "right_elbow")[:, 1]
    right_wrist = get_joint_series(df, "right_wrist")[:, 1]
    height_series = np.minimum(right_elbow, right_wrist)
    return find_min_y_frame(height_series, frame_range)


@dataclass
class PoseMetrics:
    trophy_frame: int
    impact_frame: int
    trophy_knee_angle: float
    trophy_right_arm_extension: float
    trophy_left_arm_lift: float
    impact_right_shoulder_angle: Optional[float]


def compute_pose_metrics(
    csv_path: Path | str,
    trophy_range: Tuple[int, int] = (15, 30),
    impact_range: Tuple[int, int] = (25, 40),
    trophy_frame_override: Optional[int] = None,
    impact_frame_override: Optional[int] = None,
) -> PoseMetrics:
    df = load_pose_sequence(csv_path)

    def _clamp(idx: int) -> int:
        n_frames = len(df)
        return max(0, min(idx, n_frames - 1))

    if trophy_frame_override is not None:
        trophy_idx = _clamp(int(trophy_frame_override))
    else:
        trophy_idx = find_trophy_frame(df, trophy_range)

    if impact_frame_override is not None:
        impact_idx = _clamp(int(impact_frame_override))
    else:
        impact_idx = find_impact_frame(df, impact_range)

    knees = knee_angles(df)
    trophy_knee = float(min(knees["left"][trophy_idx], knees["right"][trophy_idx]))

    arms = shoulder_elbow_metrics(df)
    right_arm_extension = float(arms["right_arm_extension"][trophy_idx])
    left_arm_lift = float(arms["left_arm_lift"][trophy_idx])

    ear_angle_series = right_ear_shoulder_elbow_angle(df)
    impact_ear_angle: Optional[float]
    if ear_angle_series is None:
        impact_ear_angle = None
    else:
        impact_ear_angle = float(ear_angle_series[impact_idx])

    return PoseMetrics(
        trophy_frame=trophy_idx,
        impact_frame=impact_idx,
        trophy_knee_angle=trophy_knee,
        trophy_right_arm_extension=right_arm_extension,
        trophy_left_arm_lift=left_arm_lift,
        impact_right_shoulder_angle=impact_ear_angle,
    )
