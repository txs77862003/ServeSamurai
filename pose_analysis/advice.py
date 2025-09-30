"""Generate simple textual advice from pose metric differences."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .comparison import PoseMetricDiff


@dataclass(frozen=True)
class AdviceFinding:
    """Represents a single high-level coaching suggestion."""

    metric: str
    difference: float
    recommendation: str


_DEFAULT_THRESHOLDS: Dict[str, float] = {
    "trophy_knee_angle": 15.0,
    "trophy_right_arm_extension": 15.0,
    "trophy_left_arm_lift": 15.0,
    "impact_right_shoulder_angle": 15.0,
}


def generate_advice(
    diff: PoseMetricDiff,
    thresholds: Dict[str, float] | None = None,
) -> List[AdviceFinding]:
    """Create coaching advice using simple difference heuristics."""

    th = dict(_DEFAULT_THRESHOLDS)
    if thresholds:
        th.update(thresholds)

    findings: List[AdviceFinding] = []

    knee_delta = diff.trophy_knee_angle_diff
    if abs(knee_delta) >= th["trophy_knee_angle"]:
        if knee_delta > 0:
            recommendation = (
                "トロフィーポーズでの膝の曲げが浅いようです。もう少し膝を沈めて脚の力を溜めましょう。"
            )
        else:
            recommendation = (
                "トロフィーポーズで膝を深く曲げています。膝に負担がかかったり、パワーが逃げてしまったりするので注意しましょう。"
            )
        findings.append(
            AdviceFinding("trophy_knee_angle", knee_delta, recommendation)
        )

    arm_delta = diff.trophy_right_arm_extension_diff
    if abs(arm_delta) >= th["trophy_right_arm_extension"]:
        if arm_delta > 0:
            recommendation = (
                "トス時の右肘が高く上がりすぎています。肩の力を抜き肩から肘にかけて一直線を意識しましょう。"
            )
        else:
            recommendation = (
                "トス時の右肘が下がりすぎています。肩や肘を痛める可能性もあるので注意して下さい。"
            )
        findings.append(
            AdviceFinding("trophy_right_arm_extension", arm_delta, recommendation)
        )

    left_delta = diff.trophy_left_arm_lift_diff
    if abs(left_delta) >= th["trophy_left_arm_lift"]:
        if left_delta > 0:
            recommendation = (
                "トス時の左腕が十分に上がっていません。左手で上体を支える意識を持ちましょう。"
            )
        else:
            recommendation = (
                "トス時の左腕が上がりすぎています。上体のブレにつながる場合は少し余裕を残しましょう。"
            )
        findings.append(
            AdviceFinding("trophy_left_arm_lift", left_delta, recommendation)
        )

    if diff.impact_right_shoulder_angle_diff is not None:
        impact_delta = diff.impact_right_shoulder_angle_diff
        if abs(impact_delta) >= th["impact_right_shoulder_angle"]:
            if impact_delta > 0:
                recommendation = (
                    "インパクト時の右肩〜右肘の角度が大きく、腕が上がりすぎている可能性があります。もう少し肘を下げて窮屈さを減らしましょう。"
                )
            else:
                recommendation = (
                    "インパクト時の右肩〜右肘の角度が小さく、肘が落ちぎみです。もう少し高い打点で捉えることを意識しましょう。"
                )
            findings.append(
                AdviceFinding("impact_right_shoulder_angle", impact_delta, recommendation)
            )

    if not findings:
        findings.append(
            AdviceFinding(
                "overall_match",
                0.0,
                "全体的に綺麗なフォームです。この調子で参考動画と見比べながら細部を磨いてみましょう。",
            )
        )

    return findings
