"""Comparison utilities for tennis pose metrics."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .pose_metrics import PoseMetrics, compute_pose_metrics


@dataclass(frozen=True)
class PoseMetricDiff:
    """Difference between user and reference metrics (user minus reference)."""

    trophy_frame: int
    reference_trophy_frame: int
    impact_frame: int
    reference_impact_frame: int

    trophy_knee_angle_diff: float
    trophy_right_arm_extension_diff: float
    trophy_left_arm_lift_diff: float
    impact_right_shoulder_angle_diff: Optional[float]


def compare_pose_metrics(
    user_metrics: PoseMetrics, reference_metrics: PoseMetrics
) -> PoseMetricDiff:
    """Compute simple differences (user minus reference) for key pose metrics."""
    impact_diff: Optional[float]
    if (
        user_metrics.impact_right_shoulder_angle is None
        or reference_metrics.impact_right_shoulder_angle is None
    ):
        impact_diff = None
    else:
        impact_diff = (
            user_metrics.impact_right_shoulder_angle
            - reference_metrics.impact_right_shoulder_angle
        )

    return PoseMetricDiff(
        trophy_frame=user_metrics.trophy_frame,
        reference_trophy_frame=reference_metrics.trophy_frame,
        impact_frame=user_metrics.impact_frame,
        reference_impact_frame=reference_metrics.impact_frame,
        trophy_knee_angle_diff=
        user_metrics.trophy_knee_angle - reference_metrics.trophy_knee_angle,
        trophy_right_arm_extension_diff=
        user_metrics.trophy_right_arm_extension
        - reference_metrics.trophy_right_arm_extension,
        trophy_left_arm_lift_diff=
        user_metrics.trophy_left_arm_lift - reference_metrics.trophy_left_arm_lift,
        impact_right_shoulder_angle_diff=impact_diff,
    )


def compare_from_csv(
    user_csv: Path | str,
    reference_csv: Path | str,
    trophy_range=(15, 30),
    impact_range=(25, 40),
    user_trophy_override: Optional[int] = None,
    user_impact_override: Optional[int] = None,
    reference_trophy_override: Optional[int] = None,
    reference_impact_override: Optional[int] = None,
) -> PoseMetricDiff:
    """Convenience wrapper to load both sequences and return metric differences."""
    user = compute_pose_metrics(
        user_csv,
        trophy_range,
        impact_range,
        trophy_frame_override=user_trophy_override,
        impact_frame_override=user_impact_override,
    )
    reference = compute_pose_metrics(
        reference_csv,
        trophy_range,
        impact_range,
        trophy_frame_override=reference_trophy_override,
        impact_frame_override=reference_impact_override,
    )
    return compare_pose_metrics(user, reference)
