import pytest

from baseball_motion_analysis.analysis import (
    SwingAnalysisConfig,
    SwingFaultType,
    SwingSeverity,
    analyze_swing,
)
from baseball_motion_analysis.motion import (
    SwingEventDetectionConfig,
    SwingHandedness,
    SwingImpactDetectionPolicy,
    SwingMetricName,
    SwingPhase,
)
from baseball_motion_analysis.pose import PoseKeypointName
from unit.swing_test_helpers import GOOD_PHASES, good_swing_frames


def test_analyze_swing_scores_good_sequence_highly() -> None:
    result = analyze_swing(
        good_swing_frames(),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    assert result.methodology_version == "swing_evaluation_v2"
    assert result.overall_score == pytest.approx(100.0)
    assert not result.detected_faults
    assert result.confidence == pytest.approx(1.0)
    assert "Setup stance width matched the baseline." in result.good_points
    stance_metric = next(
        metric
        for metric in result.metrics
        if metric.name == SwingMetricName.NORMALIZED_STANCE_WIDTH
    )
    assert stance_metric.target_min == pytest.approx(1.0)
    assert stance_metric.target_max == pytest.approx(1.2)
    assert stance_metric.severity == SwingSeverity.GOOD


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

    assert result.methodology_version == "swing_evaluation_v2"
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


def test_analyze_swing_does_not_emit_impact_faults_when_impact_is_skipped() -> None:
    result = analyze_swing(
        good_swing_frames(scenario="upper_swing"),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        event_config=SwingEventDetectionConfig(
            impact_detection_policy=SwingImpactDetectionPolicy.SKIP_WITHOUT_BALL,
        ),
    )

    impact_metric = next(
        metric for metric in result.metrics if metric.name == SwingMetricName.ESTIMATED_ATTACK_ANGLE
    )
    head_metric = next(
        metric for metric in result.metrics if metric.name == SwingMetricName.HEAD_TRANSLATION_RATIO
    )
    follow_metric = next(
        metric
        for metric in result.metrics
        if metric.name == SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE
    )
    follow_score = next(
        phase_score
        for phase_score in result.phase_scores
        if phase_score.phase == SwingPhase.FOLLOW_THROUGH
    )

    assert impact_metric.severity == SwingSeverity.NOT_EVALUATED
    assert head_metric.severity != SwingSeverity.NOT_EVALUATED
    assert any("no-ball fallback anchor" in limitation for limitation in head_metric.limitations)
    assert follow_metric.severity != SwingSeverity.NOT_EVALUATED
    assert any("no-ball fallback anchor" in limitation for limitation in follow_metric.limitations)
    assert follow_score.confidence > 0.0
    assert SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION not in {
        fault.fault_type for fault in result.detected_faults
    }
