from dataclasses import replace

import pytest

from baseball_motion_analysis.analysis import (
    SwingAnalysisConfig,
    SwingAnalysisResult,
    SwingFaultResult,
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
from baseball_motion_analysis.pose import PoseFrame, PoseKeypoint, PoseKeypointName
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
    assert all(score.metric_deduction == 0.0 for score in result.phase_scores)
    assert all(score.fault_deduction == 0.0 for score in result.phase_scores)
    assert "Setup stance width matched the baseline." in result.good_points
    stance_metric = next(
        metric
        for metric in result.metrics
        if metric.name == SwingMetricName.NORMALIZED_STANCE_WIDTH
    )
    assert stance_metric.target_min == pytest.approx(1.0)
    assert stance_metric.target_max == pytest.approx(1.2)
    assert stance_metric.severity == SwingSeverity.GOOD


def test_phase_weights_match_dev007_03_distribution() -> None:
    result = analyze_swing(
        good_swing_frames(),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )
    weights = {score.phase: score.weight for score in result.phase_scores}

    assert weights == {
        SwingPhase.SETUP: pytest.approx(0.15),
        SwingPhase.STRIDE: pytest.approx(0.25),
        SwingPhase.FOOT_STRIKE: pytest.approx(0.25),
        SwingPhase.IMPACT: pytest.approx(0.25),
        SwingPhase.FOLLOW_THROUGH: pytest.approx(0.10),
    }
    assert sum(weights.values()) == pytest.approx(1.0)


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
    assert all(fault.linked_metrics for fault in result.detected_faults)
    assert all(fault.deduction >= 0.0 for fault in result.detected_faults)
    assert result.overall_score < 100.0


def test_fault_aware_score_exposes_largest_improvement_priority() -> None:
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


def test_impact_metric_deduction_uses_updated_phase_budget() -> None:
    result = analyze_swing(
        good_swing_frames(scenario="upper_swing"),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        config=SwingAnalysisConfig(attack_angle_severe_high_degrees=20.0),
    )
    attack_metric = next(
        metric for metric in result.metrics if metric.name == SwingMetricName.ESTIMATED_ATTACK_ANGLE
    )
    impact_score = next(score for score in result.phase_scores if score.phase == SwingPhase.IMPACT)

    assert attack_metric.deduction == pytest.approx(8.33)
    assert impact_score.metric_deduction == pytest.approx(33.32)


def test_secondary_fault_evidence_lowers_score_without_metric_deduction() -> None:
    result = analyze_swing(
        good_swing_frames(),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        config=SwingAnalysisConfig(wrist_chest_distance_ratio=0.1),
    )
    fault = next(
        fault
        for fault in result.detected_faults
        if fault.fault_type == SwingFaultType.DOOR_SWING_CASTING
    )
    linked_metric_deduction = sum(
        metric.deduction for metric in result.metrics if metric.name in fault.linked_metrics
    )
    foot_strike_score = next(
        score for score in result.phase_scores if score.phase == SwingPhase.FOOT_STRIKE
    )

    assert linked_metric_deduction == pytest.approx(0.0)
    assert fault.deduction > 0.0
    assert foot_strike_score.fault_deduction > 0.0
    assert result.overall_score < 100.0


def test_metric_backed_fault_uses_capped_incremental_deduction() -> None:
    config = SwingAnalysisConfig()
    result = analyze_swing(
        good_swing_frames(scenario="door_swing"),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        config=config,
    )
    fault = next(
        fault
        for fault in result.detected_faults
        if fault.fault_type == SwingFaultType.DOOR_SWING_CASTING
    )
    linked_metric_deduction = sum(
        metric.deduction for metric in result.metrics if metric.name in fault.linked_metrics
    )
    severity_ratio = (
        config.fault_severe_phase_penalty_ratio
        if fault.severity == SwingSeverity.SEVERE
        else config.fault_warning_phase_penalty_ratio
    )
    fault_budget = 25.0 * severity_ratio * fault.confidence

    assert linked_metric_deduction > 0.0
    assert fault.deduction == pytest.approx(
        max(0.0, round(fault_budget - linked_metric_deduction, 2))
    )
    assert fault.deduction <= fault_budget


def test_secondary_fault_score_impact_scales_with_confidence() -> None:
    high_confidence = analyze_swing(
        good_swing_frames(),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        config=SwingAnalysisConfig(wrist_chest_distance_ratio=0.1),
    )
    low_confidence = analyze_swing(
        _with_keypoint_confidence(
            good_swing_frames(),
            frame_index=GOOD_PHASES[SwingPhase.FOOT_STRIKE],
            keypoint_name=PoseKeypointName.LEFT_WRIST,
            confidence=0.25,
        ),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        config=SwingAnalysisConfig(wrist_chest_distance_ratio=0.1),
    )
    high_fault = next(
        fault
        for fault in high_confidence.detected_faults
        if fault.fault_type == SwingFaultType.DOOR_SWING_CASTING
    )
    low_fault = next(
        fault
        for fault in low_confidence.detected_faults
        if fault.fault_type == SwingFaultType.DOOR_SWING_CASTING
    )

    assert high_fault.deduction > low_fault.deduction
    assert high_confidence.overall_score < low_confidence.overall_score


def test_severe_fault_score_impact_exceeds_warning_fault_impact() -> None:
    warning_result = analyze_swing(
        good_swing_frames(),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        config=SwingAnalysisConfig(wrist_chest_distance_ratio=0.1),
    )
    severe_result = analyze_swing(
        good_swing_frames(scenario="upper_swing"),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
        config=SwingAnalysisConfig(attack_angle_severe_high_degrees=20.0),
    )
    warning_fault = next(
        fault
        for fault in warning_result.detected_faults
        if fault.fault_type == SwingFaultType.DOOR_SWING_CASTING
    )
    severe_fault = next(
        fault
        for fault in severe_result.detected_faults
        if fault.fault_type == SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION
    )

    assert severe_fault.severity == SwingSeverity.SEVERE
    assert _score_impact(severe_result, severe_fault) > _score_impact(
        warning_result,
        warning_fault,
    )


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
    assert all(fault.deduction >= 0.0 for fault in result.detected_faults)


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
    assert next(
        phase_score for phase_score in result.phase_scores if phase_score.phase == SwingPhase.IMPACT
    ).fault_deduction == pytest.approx(0.0)
    assert SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION not in {
        fault.fault_type for fault in result.detected_faults
    }


def _score_impact(result: SwingAnalysisResult, fault: SwingFaultResult) -> float:
    linked_metric_deduction = sum(
        metric.deduction for metric in result.metrics if metric.name in fault.linked_metrics
    )
    return fault.deduction + linked_metric_deduction


def _with_keypoint_confidence(
    frames: tuple[PoseFrame, ...],
    *,
    frame_index: int,
    keypoint_name: PoseKeypointName,
    confidence: float,
) -> tuple[PoseFrame, ...]:
    adjusted: list[PoseFrame] = []
    for frame in frames:
        if frame.frame_index != frame_index:
            adjusted.append(frame)
            continue
        keypoints = dict(frame.keypoints)
        keypoint = keypoints[keypoint_name]
        keypoints[keypoint_name] = PoseKeypoint(
            keypoint.point,
            confidence=confidence,
            interpolated=keypoint.interpolated,
            smoothed=keypoint.smoothed,
            out_of_frame=keypoint.out_of_frame,
        )
        adjusted.append(replace(frame, keypoints=keypoints))
    return tuple(adjusted)
