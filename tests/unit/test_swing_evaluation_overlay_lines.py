import pytest

from baseball_motion_analysis.analysis import analyze_swing
from baseball_motion_analysis.app.swing_services import build_evaluation_overlay_lines
from baseball_motion_analysis.motion import SwingHandedness, SwingMetricName
from baseball_motion_analysis.pose import PoseKeypointName
from unit.swing_test_helpers import GOOD_PHASES, good_swing_frames


def test_build_evaluation_overlay_lines_returns_metric_primitives() -> None:
    frames = good_swing_frames()
    analysis = analyze_swing(
        frames,
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    lines = build_evaluation_overlay_lines(frames, analysis)

    stance_line = next(
        line for line in lines if line.metric_name == SwingMetricName.NORMALIZED_STANCE_WIDTH.value
    )
    assert stance_line.frame_index == 0
    assert stance_line.phase == "setup"
    assert stance_line.start_keypoint_name == "left_ankle"
    assert stance_line.end_keypoint_name == "right_ankle"
    assert stance_line.start.x == pytest.approx(0.993)
    assert stance_line.end.x == pytest.approx(0.0)
    assert stance_line.label == "Stance width"
    assert stance_line.severity == "good"
    assert stance_line.confidence == pytest.approx(1.0)
    assert stance_line.style == "solid"
    assert stance_line.color_role == "good"

    line_counts = {
        metric_name: sum(1 for line in lines if line.metric_name == metric_name.value)
        for metric_name in SwingMetricName
    }
    assert line_counts == {
        SwingMetricName.NORMALIZED_STANCE_WIDTH: 1,
        SwingMetricName.TORSO_FORWARD_TILT: 1,
        SwingMetricName.TORSO_TILT_PRESERVATION: 2,
        SwingMetricName.GRIP_LOADING_VECTOR: 1,
        SwingMetricName.REAR_KNEE_SWAY: 1,
        SwingMetricName.HEAD_TRANSLATION_RATIO: 1,
        SwingMetricName.EARLY_CONNECTION_ANGLE: 1,
        SwingMetricName.LEAD_KNEE_BLOCKING_INDEX: 4,
        SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING: 4,
        SwingMetricName.ESTIMATED_ATTACK_ANGLE: 1,
        SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE: 2,
    }
    assert {
        "Stance width",
        "Torso tilt",
        "Tilt hold",
        "Grip load",
        "Rear knee sway",
        "Head drift",
        "Connection",
        "Lead block",
        "Hip axis",
        "Shoulder axis",
        "Attack angle",
        "Finish posture",
        "Finish balance",
    }.issubset({line.label for line in lines})


def test_build_evaluation_overlay_lines_skips_missing_keypoint_metric() -> None:
    frames = good_swing_frames(remove_keypoints={PoseKeypointName.LEFT_ANKLE})
    analysis = analyze_swing(
        frames,
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    lines = build_evaluation_overlay_lines(frames, analysis)

    assert not any(
        line.metric_name == SwingMetricName.NORMALIZED_STANCE_WIDTH.value for line in lines
    )
    assert any(line.metric_name == SwingMetricName.TORSO_FORWARD_TILT.value for line in lines)


def test_build_evaluation_overlay_lines_marks_grip_attack_angle_fallback_low_confidence() -> None:
    frames = good_swing_frames(remove_keypoints={PoseKeypointName.BAT_TIP})
    analysis = analyze_swing(
        frames,
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    lines = build_evaluation_overlay_lines(frames, analysis)

    attack_line = next(
        line for line in lines if line.metric_name == SwingMetricName.ESTIMATED_ATTACK_ANGLE.value
    )
    assert attack_line.label == "Grip path"
    assert attack_line.confidence <= 0.45
    assert attack_line.style == "dashed"
    assert attack_line.color_role == "low_confidence"
