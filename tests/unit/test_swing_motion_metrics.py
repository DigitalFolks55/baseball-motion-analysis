import math

import pytest

from baseball_motion_analysis.motion import (
    BodySide,
    SwingHandedness,
    SwingMetricName,
    SwingPhase,
    angle_between_vectors_degrees,
    angle_difference_degrees,
    calculate_swing_metrics,
    detect_swing_phases,
    joint_angle_degrees,
    resolve_body_sides,
)
from baseball_motion_analysis.pose import Point2D
from unit.swing_test_helpers import GOOD_PHASES, good_swing_frames


def test_geometry_helpers_calculate_expected_angles() -> None:
    assert angle_difference_degrees(350.0, 10.0) == pytest.approx(20.0)
    assert angle_between_vectors_degrees(
        Point2D(0.0, 0.0),
        Point2D(1.0, 0.0),
        Point2D(0.0, 0.0),
        Point2D(0.0, 1.0),
    ) == pytest.approx(90.0)
    assert joint_angle_degrees(
        Point2D(0.0, 0.0),
        Point2D(1.0, 0.0),
        Point2D(1.0, 1.0),
    ) == pytest.approx(90.0)


def test_resolve_body_sides_from_handedness() -> None:
    right_handed = resolve_body_sides(SwingHandedness.RIGHT_HANDED)
    left_handed = resolve_body_sides(SwingHandedness.LEFT_HANDED)
    unknown = resolve_body_sides(SwingHandedness.UNKNOWN)

    assert right_handed.lead == BodySide.LEFT
    assert right_handed.rear == BodySide.RIGHT
    assert left_handed.lead == BodySide.RIGHT
    assert left_handed.rear == BodySide.LEFT
    assert unknown.lead == BodySide.LEFT
    assert unknown.confidence < 1.0
    assert unknown.limitation is not None


def test_detect_swing_phases_accepts_caller_provided_frames() -> None:
    frames = good_swing_frames()

    phases = detect_swing_phases(frames, GOOD_PHASES)

    assert phases.frame_index_for(SwingPhase.SETUP) == 0
    assert phases.frame_index_for(SwingPhase.IMPACT) == 3
    assert phases.confidence == pytest.approx(1.0)


def test_detect_swing_phases_uses_motion_aware_automatic_detection() -> None:
    frames = good_swing_frames()

    phases = detect_swing_phases(frames)

    assert phases.setup == 0
    assert phases.stride == 1
    assert phases.foot_strike == 2
    assert phases.impact == 3
    assert phases.follow_through == 4
    assert phases.confidence < 1.0
    assert phases.detection_method_for(SwingPhase.IMPACT) == "peak_wrist_velocity_window"
    assert phases.confidence_for(SwingPhase.IMPACT) == pytest.approx(phases.confidence)
    assert any("estimated impact window" in limitation for limitation in phases.limitations)


def test_calculate_swing_metrics_for_good_sequence() -> None:
    frames = good_swing_frames()

    metrics = {
        metric.name: metric
        for metric in calculate_swing_metrics(
            frames,
            detect_swing_phases(frames, GOOD_PHASES),
            SwingHandedness.RIGHT_HANDED,
        )
    }

    assert metrics[SwingMetricName.SHIN_TORSO_PARALLELISM].value == pytest.approx(0.0)
    assert metrics[SwingMetricName.EARLY_CONNECTION_ANGLE].value == pytest.approx(101.31, abs=0.1)
    assert metrics[SwingMetricName.LEAD_KNEE_BLOCKING_INDEX].value == pytest.approx(0.0)
    assert metrics[SwingMetricName.HEAD_TRANSLATION_RATIO].value == pytest.approx(0.0)
    assert metrics[SwingMetricName.ESTIMATED_ATTACK_ANGLE].value == pytest.approx(10.0, abs=0.1)
    assert metrics[SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING].value == pytest.approx(1.0)
    assert all(math.isfinite(metric.value or 0.0) for metric in metrics.values())
