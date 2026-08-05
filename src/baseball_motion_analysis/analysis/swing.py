"""Rule evaluation and scoring for swing analysis."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from baseball_motion_analysis.motion import (
    BodySide,
    SwingHandedness,
    SwingMetricName,
    SwingMetricValue,
    SwingPhase,
    SwingPhaseFrames,
    angle_difference_degrees,
    calculate_swing_metrics,
    detect_swing_phases,
    resolve_body_sides,
    side_keypoint,
    torso_length,
    vector_angle_degrees,
)
from baseball_motion_analysis.pose import PoseFrame, PoseKeypoint, PoseKeypointName


class SwingSeverity(StrEnum):
    """Severity for metric and fault evaluation."""

    GOOD = "good"
    WARNING = "warning"
    SEVERE = "severe"
    NOT_EVALUATED = "not_evaluated"


class SwingFaultType(StrEnum):
    """Swing fault candidates evaluated in v1."""

    DOOR_SWING_CASTING = "door_swing_casting"
    FORWARD_AXIS_DRIFT_RUSHING = "forward_axis_drift_rushing"
    ARMS_ONLY_ONE_PIECE = "arms_only_one_piece"
    EXCESSIVE_UPPER_SWING_EARLY_EXTENSION = "excessive_upper_swing_early_extension"
    COLLAPSED_LEAD_SIDE = "collapsed_lead_side"


@dataclass(frozen=True)
class SwingAnalysisConfig:
    """Configurable swing thresholds for conservative v1 rule evaluation."""

    min_keypoint_confidence: float = 0.2
    shin_torso_warning_degrees: float = 18.0
    shin_torso_severe_degrees: float = 32.0
    early_connection_min_degrees: float = 80.0
    early_connection_max_degrees: float = 105.0
    early_connection_warning_margin_degrees: float = 15.0
    early_connection_severe_margin_degrees: float = 30.0
    lead_knee_warning_flexion_degrees: float = -8.0
    lead_knee_severe_flexion_degrees: float = -20.0
    head_translation_warning_ratio: float = 0.35
    head_translation_severe_ratio: float = 0.55
    attack_angle_min_degrees: float = 5.0
    attack_angle_max_degrees: float = 15.0
    excessive_attack_angle_degrees: float = 20.0
    attack_angle_severe_high_degrees: float = 30.0
    attack_angle_severe_low_degrees: float = -10.0
    wrist_chest_distance_ratio: float = 0.95
    rear_knee_sway_ratio: float = 0.12
    lead_knee_forward_drift_ratio: float = 0.12
    torso_tilt_change_warning_degrees: float = 18.0
    hip_shoulder_min_lag_frames: float = 1.0


@dataclass(frozen=True)
class SwingMetricResult:
    """Evaluated swing metric with scoring information."""

    name: SwingMetricName
    value: float | None
    target_min: float | None
    target_max: float | None
    severity: SwingSeverity
    confidence: float
    evidence_frames: tuple[int, ...]
    deduction: float
    message: str
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SwingFaultResult:
    """Detected swing fault and supporting evidence."""

    fault_type: SwingFaultType
    phase: SwingPhase
    severity: SwingSeverity
    confidence: float
    evidence: str
    evidence_frames: tuple[int, ...]


@dataclass(frozen=True)
class SwingPhaseScore:
    """Score and confidence for one swing phase."""

    phase: SwingPhase
    score: float
    weight: float
    confidence: float


@dataclass(frozen=True)
class SwingAnalysisResult:
    """Complete rule and score result for a swing."""

    overall_score: float
    phase_scores: tuple[SwingPhaseScore, ...]
    metrics: tuple[SwingMetricResult, ...]
    detected_faults: tuple[SwingFaultResult, ...]
    good_points: tuple[str, ...]
    improvement_priorities: tuple[str, ...]
    confidence: float
    limitations: tuple[str, ...]
    phases: SwingPhaseFrames
    handedness: SwingHandedness


_PHASE_WEIGHTS: Mapping[SwingPhase, float] = {
    SwingPhase.SETUP: 0.10,
    SwingPhase.STRIDE: 0.20,
    SwingPhase.FOOT_STRIKE: 0.25,
    SwingPhase.IMPACT: 0.35,
    SwingPhase.FOLLOW_THROUGH: 0.10,
}

_METRIC_PHASES: Mapping[SwingMetricName, SwingPhase] = {
    SwingMetricName.SHIN_TORSO_PARALLELISM: SwingPhase.SETUP,
    SwingMetricName.HEAD_TRANSLATION_RATIO: SwingPhase.STRIDE,
    SwingMetricName.EARLY_CONNECTION_ANGLE: SwingPhase.FOOT_STRIKE,
    SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING: SwingPhase.FOOT_STRIKE,
    SwingMetricName.LEAD_KNEE_BLOCKING_INDEX: SwingPhase.IMPACT,
    SwingMetricName.ESTIMATED_ATTACK_ANGLE: SwingPhase.IMPACT,
}


def analyze_swing(
    frames: Sequence[PoseFrame],
    *,
    handedness: SwingHandedness = SwingHandedness.UNKNOWN,
    phase_frames: Mapping[SwingPhase, int] | None = None,
    config: SwingAnalysisConfig | None = None,
) -> SwingAnalysisResult:
    """Analyze one swing pose sequence and return scores, faults, and confidence."""
    if not frames:
        raise ValueError("At least one pose frame is required for swing analysis.")
    ordered_frames = tuple(sorted(frames, key=lambda frame: frame.frame_index))
    evaluation_config = config or SwingAnalysisConfig()
    phases = detect_swing_phases(ordered_frames, phase_frames)
    raw_metrics = calculate_swing_metrics(
        ordered_frames,
        phases,
        handedness,
        min_keypoint_confidence=evaluation_config.min_keypoint_confidence,
    )
    metrics = tuple(_evaluate_metric(metric, evaluation_config) for metric in raw_metrics)
    faults = _detect_faults(ordered_frames, phases, handedness, metrics, evaluation_config)
    phase_scores = _score_phases(metrics)
    limitations = _collect_limitations(phases, raw_metrics, handedness)
    confidence = _aggregate_confidence(metrics, phases.confidence)
    confidence *= resolve_body_sides(handedness).confidence
    overall_score = sum(score.score * score.weight for score in phase_scores)

    return SwingAnalysisResult(
        overall_score=round(overall_score, 2),
        phase_scores=phase_scores,
        metrics=metrics,
        detected_faults=faults,
        good_points=_good_points(metrics),
        improvement_priorities=_improvement_priorities(metrics, faults),
        confidence=round(confidence, 3),
        limitations=limitations,
        phases=phases,
        handedness=handedness,
    )


def _evaluate_metric(
    metric: SwingMetricValue,
    config: SwingAnalysisConfig,
) -> SwingMetricResult:
    if metric.value is None:
        return SwingMetricResult(
            name=metric.name,
            value=None,
            target_min=None,
            target_max=None,
            severity=SwingSeverity.NOT_EVALUATED,
            confidence=0.0,
            evidence_frames=metric.evidence_frames,
            deduction=0.0,
            message="Metric could not be evaluated from the visible keypoints.",
            limitations=metric.limitations,
        )

    evaluators = {
        SwingMetricName.SHIN_TORSO_PARALLELISM: _evaluate_shin_torso,
        SwingMetricName.EARLY_CONNECTION_ANGLE: _evaluate_early_connection,
        SwingMetricName.LEAD_KNEE_BLOCKING_INDEX: _evaluate_lead_knee_blocking,
        SwingMetricName.HEAD_TRANSLATION_RATIO: _evaluate_head_translation,
        SwingMetricName.ESTIMATED_ATTACK_ANGLE: _evaluate_attack_angle,
        SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING: _evaluate_hip_shoulder_timing,
    }
    return evaluators[metric.name](metric, config)


def _evaluate_shin_torso(
    metric: SwingMetricValue,
    config: SwingAnalysisConfig,
) -> SwingMetricResult:
    value = _require_value(metric)
    penalty, severity = _upper_bound_penalty(
        value,
        warning=config.shin_torso_warning_degrees,
        severe=config.shin_torso_severe_degrees,
    )
    return _result(
        metric,
        target_min=0.0,
        target_max=config.shin_torso_warning_degrees,
        severity=severity,
        penalty=penalty,
        message="Shin and torso posture were compared during setup and stride.",
    )


def _evaluate_early_connection(
    metric: SwingMetricValue,
    config: SwingAnalysisConfig,
) -> SwingMetricResult:
    value = _require_value(metric)
    penalty, severity = _range_penalty(
        value,
        target_min=config.early_connection_min_degrees,
        target_max=config.early_connection_max_degrees,
        warning_margin=config.early_connection_warning_margin_degrees,
        severe_margin=config.early_connection_severe_margin_degrees,
    )
    return _result(
        metric,
        target_min=config.early_connection_min_degrees,
        target_max=config.early_connection_max_degrees,
        severity=severity,
        penalty=penalty,
        message="Lead arm connection was checked at rotation start.",
    )


def _evaluate_lead_knee_blocking(
    metric: SwingMetricValue,
    config: SwingAnalysisConfig,
) -> SwingMetricResult:
    value = _require_value(metric)
    if value >= 0.0:
        penalty = 0.0
        severity = SwingSeverity.GOOD
    elif value >= config.lead_knee_warning_flexion_degrees:
        penalty = abs(value / config.lead_knee_warning_flexion_degrees) * 0.5
        severity = SwingSeverity.WARNING
    else:
        severe_span = abs(config.lead_knee_severe_flexion_degrees)
        penalty = min(1.0, abs(value) / severe_span)
        severity = SwingSeverity.SEVERE
    return _result(
        metric,
        target_min=0.0,
        target_max=None,
        severity=severity,
        penalty=penalty,
        message="Lead knee bracing was checked from foot strike to impact.",
    )


def _evaluate_head_translation(
    metric: SwingMetricValue,
    config: SwingAnalysisConfig,
) -> SwingMetricResult:
    value = _require_value(metric)
    penalty, severity = _upper_bound_penalty(
        value,
        warning=config.head_translation_warning_ratio,
        severe=config.head_translation_severe_ratio,
    )
    return _result(
        metric,
        target_min=0.0,
        target_max=config.head_translation_warning_ratio,
        severity=severity,
        penalty=penalty,
        message="Head movement was normalized by torso length.",
    )


def _evaluate_attack_angle(
    metric: SwingMetricValue,
    config: SwingAnalysisConfig,
) -> SwingMetricResult:
    value = _require_value(metric)
    penalty, severity = _range_penalty(
        value,
        target_min=config.attack_angle_min_degrees,
        target_max=config.attack_angle_max_degrees,
        warning_margin=5.0,
        severe_margin=15.0,
    )
    if value > config.excessive_attack_angle_degrees:
        severity = SwingSeverity.WARNING
    if (
        value >= config.attack_angle_severe_high_degrees
        or value <= config.attack_angle_severe_low_degrees
    ):
        severity = SwingSeverity.SEVERE
        penalty = max(penalty, 1.0)
    return _result(
        metric,
        target_min=config.attack_angle_min_degrees,
        target_max=config.attack_angle_max_degrees,
        severity=severity,
        penalty=penalty,
        message="Attack angle was estimated around impact.",
    )


def _evaluate_hip_shoulder_timing(
    metric: SwingMetricValue,
    config: SwingAnalysisConfig,
) -> SwingMetricResult:
    value = _require_value(metric)
    if value >= config.hip_shoulder_min_lag_frames:
        penalty = 0.0
        severity = SwingSeverity.GOOD
    elif value >= 0.0:
        penalty = 0.7
        severity = SwingSeverity.WARNING
    else:
        penalty = 1.0
        severity = SwingSeverity.SEVERE
    return _result(
        metric,
        target_min=config.hip_shoulder_min_lag_frames,
        target_max=None,
        severity=severity,
        penalty=penalty,
        message="Pelvis and shoulder rotation timing were compared.",
    )


def _result(
    metric: SwingMetricValue,
    *,
    target_min: float | None,
    target_max: float | None,
    severity: SwingSeverity,
    penalty: float,
    message: str,
) -> SwingMetricResult:
    phase_weight = _PHASE_WEIGHTS[_METRIC_PHASES[metric.name]]
    metric_phase = _METRIC_PHASES[metric.name]
    phase_metric_count = sum(1 for phase in _METRIC_PHASES.values() if phase == metric_phase)
    deduction = phase_weight * 100.0 * max(0.0, min(1.0, penalty)) / phase_metric_count
    return SwingMetricResult(
        name=metric.name,
        value=round(_require_value(metric), 4),
        target_min=target_min,
        target_max=target_max,
        severity=severity,
        confidence=round(metric.confidence, 3),
        evidence_frames=metric.evidence_frames,
        deduction=round(deduction, 2),
        message=message,
        limitations=metric.limitations,
    )


def _detect_faults(
    frames: Sequence[PoseFrame],
    phases: SwingPhaseFrames,
    handedness: SwingHandedness,
    metrics: Sequence[SwingMetricResult],
    config: SwingAnalysisConfig,
) -> tuple[SwingFaultResult, ...]:
    metric_by_name = {metric.name: metric for metric in metrics}
    frame_by_index = {frame.frame_index: frame for frame in frames}
    sides = resolve_body_sides(handedness)
    faults: list[SwingFaultResult] = []

    early_connection = metric_by_name[SwingMetricName.EARLY_CONNECTION_ANGLE]
    wrist_chest_ratio = _wrist_chest_distance_ratio(
        frame_by_index[phases.foot_strike],
        sides.lead,
        config.min_keypoint_confidence,
    )
    if _is_problem(early_connection) or _ratio_exceeds(
        wrist_chest_ratio,
        config.wrist_chest_distance_ratio,
    ):
        faults.append(
            SwingFaultResult(
                fault_type=SwingFaultType.DOOR_SWING_CASTING,
                phase=SwingPhase.FOOT_STRIKE,
                severity=_fault_severity(early_connection),
                confidence=max(early_connection.confidence, _ratio_confidence(wrist_chest_ratio)),
                evidence="Lead arm connection or wrist distance suggests the hands may cast away.",
                evidence_frames=early_connection.evidence_frames,
            )
        )

    head_translation = metric_by_name[SwingMetricName.HEAD_TRANSLATION_RATIO]
    rear_knee_sway = _rear_knee_sway_ratio(
        frame_by_index[phases.setup],
        frame_by_index[phases.stride],
        sides.rear,
        sides.lead,
        config.min_keypoint_confidence,
    )
    if _is_problem(head_translation) or _ratio_exceeds(rear_knee_sway, config.rear_knee_sway_ratio):
        faults.append(
            SwingFaultResult(
                fault_type=SwingFaultType.FORWARD_AXIS_DRIFT_RUSHING,
                phase=SwingPhase.STRIDE,
                severity=_fault_severity(head_translation),
                confidence=max(head_translation.confidence, _ratio_confidence(rear_knee_sway)),
                evidence="Head movement or rear-knee sway suggests early forward drift.",
                evidence_frames=head_translation.evidence_frames,
            )
        )

    separation = metric_by_name[SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING]
    if _is_problem(separation):
        faults.append(
            SwingFaultResult(
                fault_type=SwingFaultType.ARMS_ONLY_ONE_PIECE,
                phase=SwingPhase.FOOT_STRIKE,
                severity=_fault_severity(separation),
                confidence=separation.confidence,
                evidence="Pelvis and shoulders did not show a clear timing lag.",
                evidence_frames=separation.evidence_frames,
            )
        )

    attack = metric_by_name[SwingMetricName.ESTIMATED_ATTACK_ANGLE]
    torso_tilt_change = _torso_tilt_change(
        frame_by_index[phases.setup],
        frame_by_index[phases.impact],
        config.min_keypoint_confidence,
    )
    attack_value = attack.value if attack.value is not None else -math.inf
    if attack_value > config.excessive_attack_angle_degrees or _ratio_exceeds(
        torso_tilt_change, config.torso_tilt_change_warning_degrees
    ):
        faults.append(
            SwingFaultResult(
                fault_type=SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION,
                phase=SwingPhase.IMPACT,
                severity=_fault_severity(attack),
                confidence=max(attack.confidence, _ratio_confidence(torso_tilt_change)),
                evidence="Attack angle or trunk posture suggests an excessive upward path.",
                evidence_frames=attack.evidence_frames,
            )
        )

    lead_knee = metric_by_name[SwingMetricName.LEAD_KNEE_BLOCKING_INDEX]
    lead_knee_drift = _lead_knee_forward_drift_ratio(
        frame_by_index[phases.foot_strike],
        frame_by_index[phases.impact],
        sides.lead,
        sides.rear,
        config.min_keypoint_confidence,
    )
    if _is_problem(lead_knee) or _ratio_exceeds(
        lead_knee_drift,
        config.lead_knee_forward_drift_ratio,
    ):
        faults.append(
            SwingFaultResult(
                fault_type=SwingFaultType.COLLAPSED_LEAD_SIDE,
                phase=SwingPhase.IMPACT,
                severity=_fault_severity(lead_knee),
                confidence=max(lead_knee.confidence, _ratio_confidence(lead_knee_drift)),
                evidence="Lead knee behavior suggests the front side may not be bracing.",
                evidence_frames=lead_knee.evidence_frames,
            )
        )

    return tuple(faults)


def _score_phases(metrics: Sequence[SwingMetricResult]) -> tuple[SwingPhaseScore, ...]:
    scores: list[SwingPhaseScore] = []
    for phase, weight in _PHASE_WEIGHTS.items():
        phase_metrics = [metric for metric in metrics if _METRIC_PHASES[metric.name] == phase]
        if not phase_metrics:
            scores.append(
                SwingPhaseScore(
                    phase=phase,
                    score=100.0,
                    weight=weight,
                    confidence=0.0,
                )
            )
            continue
        evaluated = [
            metric for metric in phase_metrics if metric.severity != SwingSeverity.NOT_EVALUATED
        ]
        deduction = (
            sum(metric.deduction for metric in phase_metrics) / weight if weight > 0.0 else 0.0
        )
        score = max(0.0, 100.0 - deduction)
        confidence = sum(metric.confidence for metric in phase_metrics) / len(phase_metrics)
        if not evaluated:
            confidence = 0.0
        scores.append(
            SwingPhaseScore(
                phase=phase,
                score=round(score, 2),
                weight=weight,
                confidence=round(confidence, 3),
            )
        )
    return tuple(scores)


def _collect_limitations(
    phases: SwingPhaseFrames,
    raw_metrics: Sequence[SwingMetricValue],
    handedness: SwingHandedness,
) -> tuple[str, ...]:
    limitations: list[str] = list(phases.limitations)
    if handedness == SwingHandedness.UNKNOWN:
        limitations.append(
            "Swing handedness was unknown, so lead/rear side mapping is lower confidence."
        )
    for metric in raw_metrics:
        limitations.extend(metric.limitations)
    return tuple(dict.fromkeys(limitations))


def _aggregate_confidence(
    metrics: Sequence[SwingMetricResult],
    phase_confidence: float,
) -> float:
    if not metrics:
        return 0.0
    metric_confidence = sum(metric.confidence for metric in metrics) / len(metrics)
    missing_count = sum(1 for metric in metrics if metric.severity == SwingSeverity.NOT_EVALUATED)
    missing_penalty = 1.0 - (missing_count / len(metrics) * 0.35)
    return max(0.0, min(1.0, metric_confidence * phase_confidence * missing_penalty))


def _good_points(metrics: Sequence[SwingMetricResult]) -> tuple[str, ...]:
    messages = {
        SwingMetricName.SHIN_TORSO_PARALLELISM: "Setup posture maintained shin-torso alignment.",
        SwingMetricName.EARLY_CONNECTION_ANGLE: "Lead arm connection stayed in the target range.",
        SwingMetricName.LEAD_KNEE_BLOCKING_INDEX: (
            "Lead knee braced or extended from foot strike to impact."
        ),
        SwingMetricName.HEAD_TRANSLATION_RATIO: "Head movement stayed controlled through impact.",
        SwingMetricName.ESTIMATED_ATTACK_ANGLE: "Attack angle stayed near the target range.",
        SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING: "Pelvis rotation led shoulder rotation.",
    }
    return tuple(
        messages[metric.name] for metric in metrics if metric.severity == SwingSeverity.GOOD
    )


def _improvement_priorities(
    metrics: Sequence[SwingMetricResult],
    faults: Sequence[SwingFaultResult],
) -> tuple[str, ...]:
    if faults:
        return tuple(_fault_label(fault.fault_type) for fault in faults)
    sorted_metrics = sorted(metrics, key=lambda metric: metric.deduction, reverse=True)
    return tuple(
        metric.name.value
        for metric in sorted_metrics
        if metric.severity in {SwingSeverity.WARNING, SwingSeverity.SEVERE}
    )


def _fault_label(fault_type: SwingFaultType) -> str:
    labels = {
        SwingFaultType.DOOR_SWING_CASTING: "Door Swing / Casting",
        SwingFaultType.FORWARD_AXIS_DRIFT_RUSHING: "Forward Axis Drift / Rushing",
        SwingFaultType.ARMS_ONLY_ONE_PIECE: "Arms-Only / One-Piece Swing",
        SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION: (
            "Excessive Upper Swing / Early Extension"
        ),
        SwingFaultType.COLLAPSED_LEAD_SIDE: "Collapsed Lead Side",
    }
    return labels[fault_type]


def _range_penalty(
    value: float,
    *,
    target_min: float,
    target_max: float,
    warning_margin: float,
    severe_margin: float,
) -> tuple[float, SwingSeverity]:
    if target_min <= value <= target_max:
        return 0.0, SwingSeverity.GOOD
    deviation = target_min - value if value < target_min else value - target_max
    if deviation <= warning_margin:
        return min(0.5, deviation / warning_margin * 0.5), SwingSeverity.WARNING
    return min(1.0, deviation / severe_margin), SwingSeverity.SEVERE


def _upper_bound_penalty(
    value: float,
    *,
    warning: float,
    severe: float,
) -> tuple[float, SwingSeverity]:
    if value <= warning:
        return 0.0, SwingSeverity.GOOD
    if value <= severe:
        span = severe - warning
        return 0.5 + ((value - warning) / span * 0.5), SwingSeverity.WARNING
    return 1.0, SwingSeverity.SEVERE


def _is_problem(metric: SwingMetricResult) -> bool:
    return metric.severity in {SwingSeverity.WARNING, SwingSeverity.SEVERE}


def _fault_severity(metric: SwingMetricResult) -> SwingSeverity:
    if metric.severity == SwingSeverity.SEVERE:
        return SwingSeverity.SEVERE
    return SwingSeverity.WARNING


def _require_value(metric: SwingMetricValue) -> float:
    if metric.value is None:
        raise ValueError(f"{metric.name.value} is missing a value.")
    return metric.value


def _ratio_exceeds(value: tuple[float, float] | None, threshold: float) -> bool:
    return value is not None and value[0] > threshold


def _ratio_confidence(value: tuple[float, float] | None) -> float:
    return 0.0 if value is None else value[1]


def _wrist_chest_distance_ratio(
    frame: PoseFrame,
    lead_side: BodySide,
    min_confidence: float,
) -> tuple[float, float] | None:
    wrist = frame.get(side_keypoint(lead_side, "wrist"), min_confidence=min_confidence)
    chest = _midpoint(
        frame.get(PoseKeypointName.LEFT_SHOULDER, min_confidence=min_confidence),
        frame.get(PoseKeypointName.RIGHT_SHOULDER, min_confidence=min_confidence),
    )
    scale = torso_length(frame, min_confidence=min_confidence)
    if wrist is None or chest is None or scale is None:
        return None
    ratio = abs(wrist.point.x - chest.point.x) / scale
    return ratio, min(wrist.confidence, chest.confidence)


def _rear_knee_sway_ratio(
    setup: PoseFrame,
    stride: PoseFrame,
    rear_side: BodySide,
    lead_side: BodySide,
    min_confidence: float,
) -> tuple[float, float] | None:
    setup_rear_ankle = setup.get(
        side_keypoint(rear_side, "ankle"),
        min_confidence=min_confidence,
    )
    setup_lead_ankle = setup.get(
        side_keypoint(lead_side, "ankle"),
        min_confidence=min_confidence,
    )
    stride_rear_knee = stride.get(
        side_keypoint(rear_side, "knee"),
        min_confidence=min_confidence,
    )
    scale = torso_length(setup, min_confidence=min_confidence)
    if (
        setup_rear_ankle is None
        or setup_lead_ankle is None
        or stride_rear_knee is None
        or scale is None
    ):
        return None
    forward_sign = 1.0 if setup_lead_ankle.point.x >= setup_rear_ankle.point.x else -1.0
    outward_distance = -forward_sign * (stride_rear_knee.point.x - setup_rear_ankle.point.x)
    return max(0.0, outward_distance / scale), min(
        setup_rear_ankle.confidence,
        setup_lead_ankle.confidence,
        stride_rear_knee.confidence,
    )


def _lead_knee_forward_drift_ratio(
    foot_strike: PoseFrame,
    impact: PoseFrame,
    lead_side: BodySide,
    rear_side: BodySide,
    min_confidence: float,
) -> tuple[float, float] | None:
    foot_lead_ankle = foot_strike.get(
        side_keypoint(lead_side, "ankle"),
        min_confidence=min_confidence,
    )
    foot_rear_ankle = foot_strike.get(
        side_keypoint(rear_side, "ankle"),
        min_confidence=min_confidence,
    )
    impact_lead_knee = impact.get(
        side_keypoint(lead_side, "knee"),
        min_confidence=min_confidence,
    )
    scale = torso_length(foot_strike, min_confidence=min_confidence)
    if (
        foot_lead_ankle is None
        or foot_rear_ankle is None
        or impact_lead_knee is None
        or scale is None
    ):
        return None
    forward_sign = 1.0 if foot_lead_ankle.point.x >= foot_rear_ankle.point.x else -1.0
    forward_distance = forward_sign * (impact_lead_knee.point.x - foot_lead_ankle.point.x)
    return max(0.0, forward_distance / scale), min(
        foot_lead_ankle.confidence,
        foot_rear_ankle.confidence,
        impact_lead_knee.confidence,
    )


def _torso_tilt_change(
    setup: PoseFrame,
    impact: PoseFrame,
    min_confidence: float,
) -> tuple[float, float] | None:
    setup_hip = _midpoint(
        setup.get(PoseKeypointName.LEFT_HIP, min_confidence=min_confidence),
        setup.get(PoseKeypointName.RIGHT_HIP, min_confidence=min_confidence),
    )
    setup_shoulder = _midpoint(
        setup.get(PoseKeypointName.LEFT_SHOULDER, min_confidence=min_confidence),
        setup.get(PoseKeypointName.RIGHT_SHOULDER, min_confidence=min_confidence),
    )
    impact_hip = _midpoint(
        impact.get(PoseKeypointName.LEFT_HIP, min_confidence=min_confidence),
        impact.get(PoseKeypointName.RIGHT_HIP, min_confidence=min_confidence),
    )
    impact_shoulder = _midpoint(
        impact.get(PoseKeypointName.LEFT_SHOULDER, min_confidence=min_confidence),
        impact.get(PoseKeypointName.RIGHT_SHOULDER, min_confidence=min_confidence),
    )
    if setup_hip is None or setup_shoulder is None or impact_hip is None or impact_shoulder is None:
        return None
    setup_angle = vector_angle_degrees(setup_hip.point, setup_shoulder.point)
    impact_angle = vector_angle_degrees(impact_hip.point, impact_shoulder.point)
    return angle_difference_degrees(setup_angle, impact_angle), min(
        setup_hip.confidence,
        setup_shoulder.confidence,
        impact_hip.confidence,
        impact_shoulder.confidence,
    )


def _midpoint(
    first: PoseKeypoint | None,
    second: PoseKeypoint | None,
) -> PoseKeypoint | None:
    if first is None or second is None:
        return None
    return PoseKeypoint(
        point=type(first.point)(
            x=(first.point.x + second.point.x) / 2.0,
            y=(first.point.y + second.point.y) / 2.0,
        ),
        confidence=min(first.confidence, second.confidence),
    )
