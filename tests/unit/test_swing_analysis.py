import pytest

from baseball_motion_analysis.analysis import (
    SwingAnalysisConfig,
    SwingFaultType,
    SwingSeverity,
    analyze_swing,
)
from baseball_motion_analysis.motion import SwingHandedness, SwingMetricName
from baseball_motion_analysis.pose import PoseKeypointName
from unit.swing_test_helpers import GOOD_PHASES, good_swing_frames


def test_analyze_swing_scores_good_sequence_highly() -> None:
    result = analyze_swing(
        good_swing_frames(),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    assert result.overall_score == pytest.approx(100.0)
    assert not result.detected_faults
    assert result.confidence == pytest.approx(1.0)
    assert "Attack angle stayed near the target range." in result.good_points


@pytest.mark.parametrize(
    ("scenario", "expected_fault"),
    [
        ("door_swing", SwingFaultType.DOOR_SWING_CASTING),
        ("forward_drift", SwingFaultType.FORWARD_AXIS_DRIFT_RUSHING),
        ("arms_only", SwingFaultType.ARMS_ONLY_ONE_PIECE),
        ("upper_swing", SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION),
        ("collapsed_lead_side", SwingFaultType.COLLAPSED_LEAD_SIDE),
    ],
)
def test_analyze_swing_detects_each_fault_candidate(
    scenario: str,
    expected_fault: SwingFaultType,
) -> None:
    result = analyze_swing(
        good_swing_frames(scenario=scenario),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    fault_types = {fault.fault_type for fault in result.detected_faults}
    assert expected_fault in fault_types
    assert result.overall_score < 100.0


def test_metric_deductions_expose_largest_improvement_priority() -> None:
    result = analyze_swing(
        good_swing_frames(scenario="upper_swing"),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )
    attack_metric = next(
        metric for metric in result.metrics if metric.name == SwingMetricName.ESTIMATED_ATTACK_ANGLE
    )

    assert attack_metric.severity in {SwingSeverity.WARNING, SwingSeverity.SEVERE}
    assert attack_metric.deduction > 0.0
    assert "Excessive Upper Swing / Early Extension" in result.improvement_priorities


def test_missing_keypoints_lower_confidence_and_add_limitations() -> None:
    frames = good_swing_frames(
        remove_keypoints={PoseKeypointName.LEFT_WRIST, PoseKeypointName.RIGHT_WRIST}
    )

    result = analyze_swing(
        frames,
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    assert result.confidence < 1.0
    assert any("wrist" in limitation.lower() for limitation in result.limitations)
    assert any(metric.severity == SwingSeverity.NOT_EVALUATED for metric in result.metrics)


def test_unknown_handedness_adds_limitation_without_crashing() -> None:
    result = analyze_swing(
        good_swing_frames(),
        handedness=SwingHandedness.UNKNOWN,
        phase_frames=GOOD_PHASES,
        config=SwingAnalysisConfig(),
    )

    assert result.handedness == SwingHandedness.UNKNOWN
    assert any("handedness" in limitation.lower() for limitation in result.limitations)
    assert result.confidence < 1.0
