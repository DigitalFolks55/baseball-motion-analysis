"""Swing-specific phase models and metric calculations."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from statistics import mean

from baseball_motion_analysis.pose import Point2D, PoseFrame, PoseKeypoint, PoseKeypointName


class BodySide(StrEnum):
    """Body side after handedness normalization."""

    LEFT = "left"
    RIGHT = "right"


class SwingHandedness(StrEnum):
    """Swing handedness supplied by a caller or selected by a user."""

    RIGHT_HANDED = "right_handed"
    LEFT_HANDED = "left_handed"
    UNKNOWN = "unknown"


class SwingPhase(StrEnum):
    """Canonical swing phase names."""

    SETUP = "setup"
    STRIDE = "stride"
    FOOT_STRIKE = "foot_strike"
    IMPACT = "impact"
    FOLLOW_THROUGH = "follow_through"


class SwingMetricName(StrEnum):
    """Kinematic metrics for swing evaluation v1."""

    SHIN_TORSO_PARALLELISM = "shin_torso_parallelism"
    EARLY_CONNECTION_ANGLE = "early_connection_angle"
    LEAD_KNEE_BLOCKING_INDEX = "lead_knee_blocking_index"
    HEAD_TRANSLATION_RATIO = "head_translation_ratio"
    ESTIMATED_ATTACK_ANGLE = "estimated_attack_angle"
    HIP_SHOULDER_SEPARATION_TIMING = "hip_shoulder_separation_timing"


@dataclass(frozen=True)
class NormalizedBodySides:
    """Resolved lead and rear body sides."""

    lead: BodySide
    rear: BodySide
    confidence: float
    limitation: str | None = None


@dataclass(frozen=True)
class SwingPhaseFrames:
    """Frame indexes for the key phases of one swing."""

    setup: int
    stride: int
    foot_strike: int
    impact: int
    follow_through: int
    confidence: float = 1.0
    limitations: tuple[str, ...] = ()
    phase_confidences: Mapping[SwingPhase, float] | None = None
    detection_methods: Mapping[SwingPhase, str] | None = None

    def frame_index_for(self, phase: SwingPhase) -> int:
        """Return the frame index assigned to a phase."""
        return {
            SwingPhase.SETUP: self.setup,
            SwingPhase.STRIDE: self.stride,
            SwingPhase.FOOT_STRIKE: self.foot_strike,
            SwingPhase.IMPACT: self.impact,
            SwingPhase.FOLLOW_THROUGH: self.follow_through,
        }[phase]

    def confidence_for(self, phase: SwingPhase) -> float:
        """Return confidence for one phase when available."""
        if self.phase_confidences is None:
            return self.confidence
        return self.phase_confidences.get(phase, self.confidence)

    def detection_method_for(self, phase: SwingPhase) -> str:
        """Return the detection method for one phase when available."""
        if self.detection_methods is None:
            return "provided" if self.confidence >= 1.0 else "conservative_fallback"
        return self.detection_methods.get(phase, "motion_aware")


@dataclass(frozen=True)
class SwingMetricValue:
    """Raw metric value before rule evaluation."""

    name: SwingMetricName
    value: float | None
    confidence: float
    evidence_frames: tuple[int, ...]
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class _DetectedPhasePositions:
    positions: tuple[int, int, int, int, int]
    sequence_confidence: float
    phase_confidences: Mapping[SwingPhase, float]
    detection_methods: Mapping[SwingPhase, str]
    limitations: tuple[str, ...]


def resolve_body_sides(handedness: SwingHandedness) -> NormalizedBodySides:
    """Resolve lead and rear body sides from swing handedness."""
    if handedness == SwingHandedness.LEFT_HANDED:
        return NormalizedBodySides(lead=BodySide.RIGHT, rear=BodySide.LEFT, confidence=1.0)
    if handedness == SwingHandedness.RIGHT_HANDED:
        return NormalizedBodySides(lead=BodySide.LEFT, rear=BodySide.RIGHT, confidence=1.0)
    return NormalizedBodySides(
        lead=BodySide.LEFT,
        rear=BodySide.RIGHT,
        confidence=0.5,
        limitation=(
            "Swing handedness was unknown; lead and rear sides were interpreted using "
            "a right-handed default."
        ),
    )


def detect_swing_phases(
    frames: Sequence[PoseFrame],
    provided_phase_frames: Mapping[SwingPhase, int] | None = None,
) -> SwingPhaseFrames:
    """Return provided phases or detect representative event frames from pose motion."""
    if not frames:
        raise ValueError("At least one pose frame is required for swing phase detection.")

    ordered_frames = tuple(sorted(frames, key=lambda frame: frame.frame_index))
    frame_indexes = tuple(frame.frame_index for frame in ordered_frames)
    if provided_phase_frames is not None:
        missing = [phase.value for phase in SwingPhase if phase not in provided_phase_frames]
        if missing:
            raise ValueError(f"Missing swing phase frame indexes: {', '.join(missing)}")
        unknown = [
            index for index in provided_phase_frames.values() if index not in set(frame_indexes)
        ]
        if unknown:
            raise ValueError(f"Swing phase frame indexes are not present: {unknown}")
        return SwingPhaseFrames(
            setup=provided_phase_frames[SwingPhase.SETUP],
            stride=provided_phase_frames[SwingPhase.STRIDE],
            foot_strike=provided_phase_frames[SwingPhase.FOOT_STRIKE],
            impact=provided_phase_frames[SwingPhase.IMPACT],
            follow_through=provided_phase_frames[SwingPhase.FOLLOW_THROUGH],
            phase_confidences={phase: 1.0 for phase in SwingPhase},
            detection_methods={phase: "provided" for phase in SwingPhase},
        )

    if len(ordered_frames) < 5:
        selected = _spread_frame_indexes(ordered_frames, 5)
        return SwingPhaseFrames(
            setup=selected[0],
            stride=selected[1],
            foot_strike=selected[2],
            impact=selected[3],
            follow_through=selected[4],
            confidence=0.4,
            limitations=("Automatic phase fallback used fewer than five unique frames.",),
            phase_confidences={phase: 0.4 for phase in SwingPhase},
            detection_methods={phase: "short_sequence_fallback" for phase in SwingPhase},
        )

    detected = _detect_motion_aware_phase_positions(ordered_frames)
    selected = tuple(ordered_frames[position].frame_index for position in detected.positions)
    return SwingPhaseFrames(
        setup=selected[0],
        stride=selected[1],
        foot_strike=selected[2],
        impact=selected[3],
        follow_through=selected[4],
        confidence=detected.sequence_confidence,
        limitations=detected.limitations,
        phase_confidences=detected.phase_confidences,
        detection_methods=detected.detection_methods,
    )


def calculate_swing_metrics(
    frames: Sequence[PoseFrame],
    phases: SwingPhaseFrames,
    handedness: SwingHandedness,
    *,
    min_keypoint_confidence: float = 0.2,
) -> tuple[SwingMetricValue, ...]:
    """Calculate raw v1 swing metrics from pose observations."""
    frame_by_index = {frame.frame_index: frame for frame in frames}
    sides = resolve_body_sides(handedness)
    limitations = (sides.limitation,) if sides.limitation else ()
    setup = frame_by_index[phases.setup]
    stride = frame_by_index[phases.stride]
    foot_strike = frame_by_index[phases.foot_strike]
    impact = frame_by_index[phases.impact]

    return (
        _shin_torso_parallelism(setup, stride, min_keypoint_confidence, limitations),
        _early_connection_angle(foot_strike, sides, min_keypoint_confidence, limitations),
        _lead_knee_blocking_index(foot_strike, impact, sides, min_keypoint_confidence),
        _head_translation_ratio(setup, impact, min_keypoint_confidence),
        _estimated_attack_angle(frames, phases, min_keypoint_confidence),
        _hip_shoulder_separation_timing(frames, min_keypoint_confidence),
    )


def vector_angle_degrees(start: Point2D, end: Point2D) -> float:
    """Return the angle of a vector relative to the horizontal axis."""
    return math.degrees(math.atan2(end.y - start.y, end.x - start.x))


def angle_difference_degrees(first: float, second: float) -> float:
    """Return the smallest absolute difference between two angles."""
    diff = (first - second + 180.0) % 360.0 - 180.0
    return abs(diff)


def angle_between_vectors_degrees(
    first_start: Point2D,
    first_end: Point2D,
    second_start: Point2D,
    second_end: Point2D,
) -> float:
    """Return the non-oriented angle between two 2D vectors."""
    ax = first_end.x - first_start.x
    ay = first_end.y - first_start.y
    bx = second_end.x - second_start.x
    by = second_end.y - second_start.y
    first_length = math.hypot(ax, ay)
    second_length = math.hypot(bx, by)
    if first_length == 0.0 or second_length == 0.0:
        raise ValueError("Cannot calculate angle for a zero-length vector.")
    cosine = max(-1.0, min(1.0, (ax * bx + ay * by) / (first_length * second_length)))
    return math.degrees(math.acos(cosine))


def joint_angle_degrees(first: Point2D, middle: Point2D, last: Point2D) -> float:
    """Return the angle at the middle point."""
    return angle_between_vectors_degrees(middle, first, middle, last)


def torso_length(frame: PoseFrame, *, min_confidence: float = 0.2) -> float | None:
    """Return a scale value from shoulder and hip midpoints."""
    shoulder = _midpoint_keypoint(
        frame,
        PoseKeypointName.LEFT_SHOULDER,
        PoseKeypointName.RIGHT_SHOULDER,
        min_confidence=min_confidence,
    )
    hip = _midpoint_keypoint(
        frame,
        PoseKeypointName.LEFT_HIP,
        PoseKeypointName.RIGHT_HIP,
        min_confidence=min_confidence,
    )
    if shoulder is None or hip is None:
        return None
    length = math.dist((shoulder.point.x, shoulder.point.y), (hip.point.x, hip.point.y))
    return length if length > 0.0 else None


def side_keypoint(side: BodySide, part: str) -> PoseKeypointName:
    """Return a named keypoint for one body side."""
    prefix = "LEFT" if side == BodySide.LEFT else "RIGHT"
    return PoseKeypointName[f"{prefix}_{part.upper()}"]


def _spread_frame_indexes(frames: Sequence[PoseFrame], count: int) -> tuple[int, ...]:
    if len(frames) == 1:
        return tuple(frames[0].frame_index for _ in range(count))
    positions = [round(index * (len(frames) - 1) / (count - 1)) for index in range(count)]
    return tuple(frames[position].frame_index for position in positions)


def _detect_motion_aware_phase_positions(frames: Sequence[PoseFrame]) -> _DetectedPhasePositions:
    setup_position = _setup_position(frames)
    movement_scores = _movement_scores(frames)
    impact_position = _impact_position(frames, movement_scores)
    stride_position = _stride_position(frames, movement_scores, setup_position, impact_position)
    foot_strike_position = _foot_strike_position(
        frames,
        stride_position=stride_position,
        impact_position=impact_position,
    )
    follow_position = min(len(frames) - 1, max(impact_position + 1, foot_strike_position + 1))
    positions = _ordered_unique_positions(
        (
            setup_position,
            stride_position,
            foot_strike_position,
            impact_position,
            follow_position,
        ),
        max_position=len(frames) - 1,
    )
    cue_count = sum(1 for score in movement_scores if score > 0.02)
    confidence = 0.82 if cue_count >= 2 else 0.55
    phase_confidences = {
        SwingPhase.SETUP: min(0.9, confidence + 0.05),
        SwingPhase.STRIDE: confidence,
        SwingPhase.FOOT_STRIKE: max(0.45, confidence - 0.05),
        SwingPhase.IMPACT: confidence,
        SwingPhase.FOLLOW_THROUGH: max(0.45, confidence - 0.05),
    }
    detection_methods = {
        SwingPhase.SETUP: "early_stability_window",
        SwingPhase.STRIDE: "first_body_or_hand_movement",
        SwingPhase.FOOT_STRIKE: "ankle_or_pre_impact_window",
        SwingPhase.IMPACT: "peak_wrist_velocity_window",
        SwingPhase.FOLLOW_THROUGH: "post_impact_motion_window",
    }
    limitations: list[str] = [
        "Impact is an estimated impact window from body-pose motion cues; bat/ball "
        "contact is not detected."
    ]
    if cue_count < 2:
        limitations.append(
            "Automatic phase detection found weak motion cues and used conservative "
            "ordered event selection."
        )
    return _DetectedPhasePositions(
        positions=positions,
        sequence_confidence=confidence,
        phase_confidences=phase_confidences,
        detection_methods=detection_methods,
        limitations=tuple(limitations),
    )


def _setup_position(frames: Sequence[PoseFrame]) -> int:
    stable_limit = max(1, min(len(frames) // 4, 6))
    movement_scores = _movement_scores(frames[: stable_limit + 1])
    if not movement_scores:
        return 0
    return min(range(len(movement_scores)), key=lambda index: movement_scores[index])


def _impact_position(frames: Sequence[PoseFrame], movement_scores: Sequence[float]) -> int:
    if not movement_scores:
        return min(len(frames) - 2, max(1, round(len(frames) * 0.7)))
    start = max(1, len(frames) // 3)
    end = max(start + 1, len(frames) - 1)
    candidate_positions = range(start, end)
    return max(candidate_positions, key=lambda position: movement_scores[position])


def _stride_position(
    frames: Sequence[PoseFrame],
    movement_scores: Sequence[float],
    setup_position: int,
    impact_position: int,
) -> int:
    if impact_position - setup_position <= 2:
        return min(len(frames) - 4, setup_position + 1)
    baseline = max(0.015, max(movement_scores[: max(1, setup_position + 1)], default=0.0) * 1.5)
    for position in range(setup_position + 1, impact_position):
        if movement_scores[position] >= baseline:
            return position
    return max(setup_position + 1, round((setup_position + impact_position) * 0.4))


def _foot_strike_position(
    frames: Sequence[PoseFrame],
    *,
    stride_position: int,
    impact_position: int,
) -> int:
    if impact_position - stride_position <= 1:
        return max(stride_position, impact_position - 1)

    ankle_changes = _ankle_displacement_from_setup(frames)
    search_positions = range(stride_position + 1, impact_position)
    if any(ankle_changes[position] > 0.01 for position in search_positions):
        return max(search_positions, key=lambda position: ankle_changes[position])
    return max(stride_position + 1, impact_position - 1)


def _movement_scores(frames: Sequence[PoseFrame]) -> tuple[float, ...]:
    if not frames:
        return ()
    scores = [0.0]
    for index in range(1, len(frames)):
        previous = frames[index - 1]
        current = frames[index]
        scale = torso_length(previous, min_confidence=0.1) or torso_length(
            current,
            min_confidence=0.1,
        )
        scale = scale or 0.25
        grip_score = _point_velocity(previous, current, _grip_point, scale)
        ankle_score = _ankle_velocity(previous, current, scale)
        rotation_score = _rotation_change(previous, current)
        scores.append(grip_score * 0.6 + ankle_score * 0.25 + rotation_score * 0.15)
    return tuple(scores)


def _point_velocity(
    previous: PoseFrame,
    current: PoseFrame,
    getter: Callable[[PoseFrame, float], PoseKeypoint | None],
    scale: float,
) -> float:
    previous_point = getter(previous, 0.1)
    current_point = getter(current, 0.1)
    if previous_point is None or current_point is None:
        return 0.0
    distance = math.dist(
        (previous_point.point.x, previous_point.point.y),
        (current_point.point.x, current_point.point.y),
    )
    return distance / max(scale, 0.01)


def _ankle_velocity(previous: PoseFrame, current: PoseFrame, scale: float) -> float:
    values: list[float] = []
    for side in (BodySide.LEFT, BodySide.RIGHT):
        name = side_keypoint(side, "ankle")
        previous_point = previous.get(name, min_confidence=0.1)
        current_point = current.get(name, min_confidence=0.1)
        if previous_point is None or current_point is None:
            continue
        values.append(
            math.dist(
                (previous_point.point.x, previous_point.point.y),
                (current_point.point.x, current_point.point.y),
            )
            / max(scale, 0.01)
        )
    return max(values, default=0.0)


def _rotation_change(previous: PoseFrame, current: PoseFrame) -> float:
    changes: list[float] = []
    for part in ("hip", "shoulder"):
        previous_vector = _side_to_side_vector(previous, part, 0.1)
        current_vector = _side_to_side_vector(current, part, 0.1)
        if previous_vector is None or current_vector is None:
            continue
        previous_angle = vector_angle_degrees(previous_vector[0].point, previous_vector[1].point)
        current_angle = vector_angle_degrees(current_vector[0].point, current_vector[1].point)
        changes.append(angle_difference_degrees(current_angle, previous_angle) / 45.0)
    return max(changes, default=0.0)


def _ankle_displacement_from_setup(frames: Sequence[PoseFrame]) -> tuple[float, ...]:
    setup = frames[0]
    values: list[float] = []
    for frame in frames:
        frame_values: list[float] = []
        scale = torso_length(setup, min_confidence=0.1) or torso_length(
            frame,
            min_confidence=0.1,
        )
        scale = scale or 0.25
        for side in (BodySide.LEFT, BodySide.RIGHT):
            name = side_keypoint(side, "ankle")
            setup_point = setup.get(name, min_confidence=0.1)
            frame_point = frame.get(name, min_confidence=0.1)
            if setup_point is None or frame_point is None:
                continue
            frame_values.append(abs(frame_point.point.x - setup_point.point.x) / max(scale, 0.01))
        values.append(max(frame_values, default=0.0))
    return tuple(values)


def _ordered_unique_positions(
    positions: tuple[int, int, int, int, int],
    *,
    max_position: int,
) -> tuple[int, int, int, int, int]:
    output: list[int] = []
    minimum = 0
    for position in positions:
        bounded = min(max_position, max(minimum, position))
        output.append(bounded)
        minimum = min(max_position, bounded + 1)
    if output[-1] > max_position:
        output[-1] = max_position
    for index in range(len(output) - 2, -1, -1):
        output[index] = min(output[index], output[index + 1])
    return (output[0], output[1], output[2], output[3], output[4])


def _shin_torso_parallelism(
    setup: PoseFrame,
    stride: PoseFrame,
    min_confidence: float,
    base_limitations: tuple[str, ...],
) -> SwingMetricValue:
    values: list[float] = []
    confidences: list[float] = []
    for frame in (setup, stride):
        torso = _torso_vector(frame, min_confidence)
        if torso is None:
            continue
        torso_angle = vector_angle_degrees(torso[0].point, torso[1].point)
        confidences.extend([torso[0].confidence, torso[1].confidence])
        for side in (BodySide.LEFT, BodySide.RIGHT):
            ankle = frame.get(side_keypoint(side, "ankle"), min_confidence=min_confidence)
            knee = frame.get(side_keypoint(side, "knee"), min_confidence=min_confidence)
            if ankle is None or knee is None:
                continue
            shin_angle = vector_angle_degrees(ankle.point, knee.point)
            values.append(angle_difference_degrees(shin_angle, torso_angle))
            confidences.extend([ankle.confidence, knee.confidence])
    if not values:
        return _missing_metric(
            SwingMetricName.SHIN_TORSO_PARALLELISM,
            "Required shin or torso keypoints were missing.",
            (setup.frame_index, stride.frame_index),
        )
    return SwingMetricValue(
        name=SwingMetricName.SHIN_TORSO_PARALLELISM,
        value=mean(values),
        confidence=min(confidences),
        evidence_frames=(setup.frame_index, stride.frame_index),
        limitations=base_limitations,
    )


def _early_connection_angle(
    frame: PoseFrame,
    sides: NormalizedBodySides,
    min_confidence: float,
    base_limitations: tuple[str, ...],
) -> SwingMetricValue:
    torso = _torso_vector(frame, min_confidence)
    shoulder = frame.get(side_keypoint(sides.lead, "shoulder"), min_confidence=min_confidence)
    wrist = frame.get(side_keypoint(sides.lead, "wrist"), min_confidence=min_confidence)
    if torso is None or shoulder is None or wrist is None:
        return _missing_metric(
            SwingMetricName.EARLY_CONNECTION_ANGLE,
            "Required torso or lead wrist keypoints were missing.",
            (frame.frame_index,),
        )
    try:
        value = angle_between_vectors_degrees(
            torso[0].point,
            torso[1].point,
            shoulder.point,
            wrist.point,
        )
    except ValueError:
        return _missing_metric(
            SwingMetricName.EARLY_CONNECTION_ANGLE,
            "Required vectors were zero length.",
            (frame.frame_index,),
        )
    return SwingMetricValue(
        name=SwingMetricName.EARLY_CONNECTION_ANGLE,
        value=value,
        confidence=min(
            torso[0].confidence,
            torso[1].confidence,
            shoulder.confidence,
            wrist.confidence,
        ),
        evidence_frames=(frame.frame_index,),
        limitations=base_limitations,
    )


def _lead_knee_blocking_index(
    foot_strike: PoseFrame,
    impact: PoseFrame,
    sides: NormalizedBodySides,
    min_confidence: float,
) -> SwingMetricValue:
    foot_angle = _side_knee_angle(foot_strike, sides.lead, min_confidence)
    impact_angle = _side_knee_angle(impact, sides.lead, min_confidence)
    if foot_angle is None or impact_angle is None:
        return _missing_metric(
            SwingMetricName.LEAD_KNEE_BLOCKING_INDEX,
            "Required lead hip, knee, or ankle keypoints were missing.",
            (foot_strike.frame_index, impact.frame_index),
        )
    return SwingMetricValue(
        name=SwingMetricName.LEAD_KNEE_BLOCKING_INDEX,
        value=impact_angle[0] - foot_angle[0],
        confidence=min(foot_angle[1], impact_angle[1]),
        evidence_frames=(foot_strike.frame_index, impact.frame_index),
    )


def _head_translation_ratio(
    setup: PoseFrame,
    impact: PoseFrame,
    min_confidence: float,
) -> SwingMetricValue:
    setup_head = _head_keypoint(setup, min_confidence)
    impact_head = _head_keypoint(impact, min_confidence)
    scale = torso_length(setup, min_confidence=min_confidence)
    if setup_head is None or impact_head is None or scale is None:
        return _missing_metric(
            SwingMetricName.HEAD_TRANSLATION_RATIO,
            "Required head or torso scale keypoints were missing.",
            (setup.frame_index, impact.frame_index),
        )
    return SwingMetricValue(
        name=SwingMetricName.HEAD_TRANSLATION_RATIO,
        value=abs(impact_head.point.x - setup_head.point.x) / scale,
        confidence=min(setup_head.confidence, impact_head.confidence),
        evidence_frames=(setup.frame_index, impact.frame_index),
    )


def _estimated_attack_angle(
    frames: Sequence[PoseFrame],
    phases: SwingPhaseFrames,
    min_confidence: float,
) -> SwingMetricValue:
    frame_by_index = {frame.frame_index: frame for frame in frames}
    impact = frame_by_index[phases.impact]
    grip = _grip_point(impact, min_confidence)
    bat = impact.get(PoseKeypointName.BAT_TIP, min_confidence=min_confidence) or impact.get(
        PoseKeypointName.BAT_BARREL,
        min_confidence=min_confidence,
    )
    if grip is not None and bat is not None:
        angle = -vector_angle_degrees(grip.point, bat.point)
        return SwingMetricValue(
            name=SwingMetricName.ESTIMATED_ATTACK_ANGLE,
            value=angle,
            confidence=min(grip.confidence, bat.confidence),
            evidence_frames=(impact.frame_index,),
        )

    foot_strike = frame_by_index[phases.foot_strike]
    grip_start = _grip_point(foot_strike, min_confidence)
    grip_end = _grip_point(impact, min_confidence)
    if grip_start is None or grip_end is None:
        return _missing_metric(
            SwingMetricName.ESTIMATED_ATTACK_ANGLE,
            "Required wrist/grip or bat keypoints were missing.",
            (phases.foot_strike, phases.impact),
        )
    angle = -vector_angle_degrees(grip_start.point, grip_end.point)
    return SwingMetricValue(
        name=SwingMetricName.ESTIMATED_ATTACK_ANGLE,
        value=angle,
        confidence=min(grip_start.confidence, grip_end.confidence, 0.45),
        evidence_frames=(phases.foot_strike, phases.impact),
        limitations=(
            "Bat tip/barrel keypoint was missing; grip trajectory was used as a fallback.",
        ),
    )


def _hip_shoulder_separation_timing(
    frames: Sequence[PoseFrame],
    min_confidence: float,
) -> SwingMetricValue:
    if len(frames) < 3:
        return _missing_metric(
            SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING,
            "At least three frames are required to estimate hip-shoulder timing.",
            tuple(frame.frame_index for frame in frames),
        )

    hip_angles: list[tuple[int, float]] = []
    shoulder_angles: list[tuple[int, float]] = []
    confidences: list[float] = []
    for index, frame in enumerate(frames):
        hips = _side_to_side_vector(frame, "hip", min_confidence)
        shoulders = _side_to_side_vector(frame, "shoulder", min_confidence)
        if hips is None or shoulders is None:
            continue
        hip_angles.append((index, vector_angle_degrees(hips[0].point, hips[1].point)))
        shoulder_angles.append(
            (index, vector_angle_degrees(shoulders[0].point, shoulders[1].point))
        )
        confidences.extend(
            [
                hips[0].confidence,
                hips[1].confidence,
                shoulders[0].confidence,
                shoulders[1].confidence,
            ]
        )
    if len(hip_angles) < 3 or len(shoulder_angles) < 3:
        return _missing_metric(
            SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING,
            "Required hip or shoulder vectors were missing across the sequence.",
            tuple(frame.frame_index for frame in frames),
        )

    hip_onset = _rotation_onset_index(hip_angles)
    shoulder_onset = _rotation_onset_index(shoulder_angles)
    if hip_onset is None or shoulder_onset is None:
        return SwingMetricValue(
            name=SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING,
            value=0.0,
            confidence=min(confidences) * 0.6,
            evidence_frames=tuple(frame.frame_index for frame in frames),
            limitations=("Clear hip or shoulder rotation onset was not detected.",),
        )
    return SwingMetricValue(
        name=SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING,
        value=float(shoulder_onset - hip_onset),
        confidence=min(confidences),
        evidence_frames=(frames[hip_onset].frame_index, frames[shoulder_onset].frame_index),
    )


def _missing_metric(
    name: SwingMetricName,
    reason: str,
    evidence_frames: tuple[int, ...],
) -> SwingMetricValue:
    return SwingMetricValue(
        name=name,
        value=None,
        confidence=0.0,
        evidence_frames=evidence_frames,
        limitations=(reason,),
    )


def _torso_vector(
    frame: PoseFrame,
    min_confidence: float,
) -> tuple[PoseKeypoint, PoseKeypoint] | None:
    hip = _midpoint_keypoint(
        frame,
        PoseKeypointName.LEFT_HIP,
        PoseKeypointName.RIGHT_HIP,
        min_confidence=min_confidence,
    )
    shoulder = _midpoint_keypoint(
        frame,
        PoseKeypointName.LEFT_SHOULDER,
        PoseKeypointName.RIGHT_SHOULDER,
        min_confidence=min_confidence,
    )
    if hip is None or shoulder is None:
        return None
    return hip, shoulder


def _side_to_side_vector(
    frame: PoseFrame,
    part: str,
    min_confidence: float,
) -> tuple[PoseKeypoint, PoseKeypoint] | None:
    left = frame.get(side_keypoint(BodySide.LEFT, part), min_confidence=min_confidence)
    right = frame.get(side_keypoint(BodySide.RIGHT, part), min_confidence=min_confidence)
    if left is None or right is None:
        return None
    return right, left


def _midpoint_keypoint(
    frame: PoseFrame,
    first_name: PoseKeypointName,
    second_name: PoseKeypointName,
    *,
    min_confidence: float,
) -> PoseKeypoint | None:
    first = frame.get(first_name, min_confidence=min_confidence)
    second = frame.get(second_name, min_confidence=min_confidence)
    if first is None or second is None:
        return None
    return PoseKeypoint(
        point=Point2D(
            x=(first.point.x + second.point.x) / 2.0,
            y=(first.point.y + second.point.y) / 2.0,
        ),
        confidence=min(first.confidence, second.confidence),
    )


def _head_keypoint(frame: PoseFrame, min_confidence: float) -> PoseKeypoint | None:
    for name in (PoseKeypointName.NOSE, PoseKeypointName.LEFT_EAR, PoseKeypointName.RIGHT_EAR):
        keypoint = frame.get(name, min_confidence=min_confidence)
        if keypoint is not None:
            return keypoint
    return None


def _grip_point(frame: PoseFrame, min_confidence: float) -> PoseKeypoint | None:
    left = frame.get(PoseKeypointName.LEFT_WRIST, min_confidence=min_confidence)
    right = frame.get(PoseKeypointName.RIGHT_WRIST, min_confidence=min_confidence)
    if left is None or right is None:
        return left or right
    return PoseKeypoint(
        point=Point2D(
            x=(left.point.x + right.point.x) / 2.0,
            y=(left.point.y + right.point.y) / 2.0,
        ),
        confidence=min(left.confidence, right.confidence),
    )


def _side_knee_angle(
    frame: PoseFrame,
    side: BodySide,
    min_confidence: float,
) -> tuple[float, float] | None:
    hip = frame.get(side_keypoint(side, "hip"), min_confidence=min_confidence)
    knee = frame.get(side_keypoint(side, "knee"), min_confidence=min_confidence)
    ankle = frame.get(side_keypoint(side, "ankle"), min_confidence=min_confidence)
    if hip is None or knee is None or ankle is None:
        return None
    return joint_angle_degrees(hip.point, knee.point, ankle.point), min(
        hip.confidence,
        knee.confidence,
        ankle.confidence,
    )


def _rotation_onset_index(angle_series: Sequence[tuple[int, float]]) -> int | None:
    baseline = angle_series[0][1]
    for frame_position, angle in angle_series[1:]:
        if angle_difference_degrees(angle, baseline) >= 5.0:
            return frame_position
    return None
