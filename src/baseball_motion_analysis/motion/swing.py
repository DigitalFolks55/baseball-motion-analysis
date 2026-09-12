"""Swing-specific phase models and metric calculations."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from baseball_motion_analysis.pose import Point2D, PoseFrame, PoseKeypoint, PoseKeypointName

_REFERENCE_FPS = 30.0
_MIN_VALID_DELTA_SECONDS = 0.001
_SPARSE_DELTA_SECONDS = 0.250


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


class SwingImpactDetectionPolicy(StrEnum):
    """Policy for handling impact/contact evidence."""

    BODY_POSE_ESTIMATED = "body_pose_estimated"
    REQUIRE_BALL_CONTACT = "require_ball_contact"
    SKIP_WITHOUT_BALL = "skip_without_ball"


class SwingEventStatus(StrEnum):
    """Availability status for one detected or skipped swing event."""

    DETECTED = "detected"
    ESTIMATED = "estimated"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


class SwingMetricName(StrEnum):
    """Kinematic metrics for baseline-driven swing evaluation v2."""

    NORMALIZED_STANCE_WIDTH = "normalized_stance_width"
    TORSO_FORWARD_TILT = "torso_forward_tilt"
    TORSO_TILT_PRESERVATION = "torso_tilt_preservation"
    GRIP_LOADING_VECTOR = "grip_loading_vector"
    REAR_KNEE_SWAY = "rear_knee_sway"
    HEAD_TRANSLATION_RATIO = "head_translation_ratio"
    EARLY_CONNECTION_ANGLE = "early_connection_angle"
    LEAD_KNEE_BLOCKING_INDEX = "lead_knee_blocking_index"
    HIP_SHOULDER_SEPARATION_TIMING = "hip_shoulder_separation_timing"
    ESTIMATED_ATTACK_ANGLE = "estimated_attack_angle"
    FOLLOW_THROUGH_POSTURE_BALANCE = "follow_through_posture_balance"


@dataclass(frozen=True)
class SwingEventDetectionConfig:
    """Configuration for automatic swing event detection."""

    impact_detection_policy: SwingImpactDetectionPolicy = (
        SwingImpactDetectionPolicy.BODY_POSE_ESTIMATED
    )
    handedness: SwingHandedness = SwingHandedness.UNKNOWN


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
    frame_quality: SwingFrameQualityDiagnostics | None = None
    active_window: SwingActiveWindowDiagnostics | None = None
    phase_fallback_reasons: Mapping[SwingPhase, str] | None = None
    phase_statuses: Mapping[SwingPhase, SwingEventStatus] | None = None

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

    def fallback_reason_for(self, phase: SwingPhase) -> str | None:
        """Return a phase-specific fallback reason when available."""
        if self.phase_fallback_reasons is None:
            return None
        return self.phase_fallback_reasons.get(phase)

    def status_for(self, phase: SwingPhase) -> SwingEventStatus:
        """Return availability status for one phase."""
        if self.phase_statuses is None:
            return SwingEventStatus.DETECTED
        return self.phase_statuses.get(phase, SwingEventStatus.DETECTED)

    def is_available_for(self, phase: SwingPhase) -> bool:
        """Return whether a phase is available as detected or estimated evidence."""
        return self.status_for(phase) in {
            SwingEventStatus.DETECTED,
            SwingEventStatus.ESTIMATED,
        }


@dataclass(frozen=True)
class SwingMetricValue:
    """Raw metric value before rule evaluation."""

    name: SwingMetricName
    value: float | None
    confidence: float
    evidence_frames: tuple[int, ...]
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SwingMeasurementSpace:
    """Coordinate space used for geometry calculations."""

    frame_width: int | None = None
    frame_height: int | None = None

    def __post_init__(self) -> None:
        if (self.frame_width is None) != (self.frame_height is None):
            msg = "frame_width and frame_height must be provided together"
            raise ValueError(msg)
        if self.frame_width is not None and self.frame_width <= 0:
            msg = "frame_width must be greater than 0"
            raise ValueError(msg)
        if self.frame_height is not None and self.frame_height <= 0:
            msg = "frame_height must be greater than 0"
            raise ValueError(msg)

    @classmethod
    def from_dimensions(
        cls,
        *,
        frame_width: int | None,
        frame_height: int | None,
    ) -> SwingMeasurementSpace:
        """Create a measurement space from optional frame dimensions."""
        if frame_width is None and frame_height is None:
            return cls()
        return cls(frame_width=frame_width, frame_height=frame_height)

    @property
    def has_frame_dimensions(self) -> bool:
        """Return whether video dimensions are available for aspect-aware math."""
        return self.frame_width is not None and self.frame_height is not None

    def point(self, point: Point2D) -> Point2D:
        """Return a point in the measurement coordinate space."""
        if self.frame_width is None or self.frame_height is None:
            return point
        return Point2D(x=point.x * self.frame_width, y=point.y * self.frame_height)

    def distance(self, start: Point2D, end: Point2D) -> float:
        """Return Euclidean distance in the measurement coordinate space."""
        measured_start = self.point(start)
        measured_end = self.point(end)
        return math.dist((measured_start.x, measured_start.y), (measured_end.x, measured_end.y))

    def horizontal_distance(self, start: Point2D, end: Point2D) -> float:
        """Return absolute horizontal distance in the measurement coordinate space."""
        return abs(self.horizontal_delta(start, end))

    def horizontal_delta(self, start: Point2D, end: Point2D) -> float:
        """Return signed horizontal delta in the measurement coordinate space."""
        measured_start = self.point(start)
        measured_end = self.point(end)
        return measured_end.x - measured_start.x

    def vector_angle_degrees(self, start: Point2D, end: Point2D) -> float:
        """Return vector angle in the measurement coordinate space."""
        measured_start = self.point(start)
        measured_end = self.point(end)
        return vector_angle_degrees(measured_start, measured_end)

    def angle_between_vectors_degrees(
        self,
        first_start: Point2D,
        first_end: Point2D,
        second_start: Point2D,
        second_end: Point2D,
    ) -> float:
        """Return vector angle difference in the measurement coordinate space."""
        return angle_between_vectors_degrees(
            self.point(first_start),
            self.point(first_end),
            self.point(second_start),
            self.point(second_end),
        )

    def joint_angle_degrees(self, first: Point2D, middle: Point2D, last: Point2D) -> float:
        """Return joint angle in the measurement coordinate space."""
        return joint_angle_degrees(self.point(first), self.point(middle), self.point(last))


@dataclass(frozen=True)
class _DetectedPhasePositions:
    positions: tuple[int, int, int, int, int]
    sequence_confidence: float
    phase_confidences: Mapping[SwingPhase, float]
    detection_methods: Mapping[SwingPhase, str]
    fallback_reasons: Mapping[SwingPhase, str]
    phase_statuses: Mapping[SwingPhase, SwingEventStatus]
    limitations: tuple[str, ...]
    frame_quality: SwingFrameQualityDiagnostics
    active_window: SwingActiveWindowDiagnostics


@dataclass(frozen=True)
class _LeadLegLiftAnalysis:
    lead_side: BodySide | None
    onset_position: int | None
    peak_position: int | None
    max_lift_ratio: float
    has_lift: bool
    fallback_reason: str | None = None


@dataclass(frozen=True)
class _StrideSelection:
    position: int
    fallback_reason: str | None
    detection_method: str
    lift: _LeadLegLiftAnalysis


@dataclass(frozen=True)
class SwingFrameQuality:
    """Swing-specific frame quality classification used for phase detection."""

    frame_index: int
    status: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SwingFrameQualityDiagnostics:
    """Summary of frame quality before swing phase detection."""

    total_frame_count: int
    usable_frame_count: int
    weak_frame_count: int
    rejected_frame_count: int
    weak_frame_indexes: tuple[int, ...]
    rejected_frame_indexes: tuple[int, ...]
    reasons_by_frame: Mapping[int, tuple[str, ...]]


@dataclass(frozen=True)
class SwingActiveWindowDiagnostics:
    """Detected active swing window in original frame indexes."""

    start_frame_index: int
    end_frame_index: int
    peak_motion_frame_index: int
    confidence: float
    fallback_reason: str | None = None


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
    *,
    frame_width: int | None = None,
    frame_height: int | None = None,
    event_config: SwingEventDetectionConfig | None = None,
) -> SwingPhaseFrames:
    """Return provided phases or detect representative event frames from pose motion."""
    if not frames:
        raise ValueError("At least one pose frame is required for swing phase detection.")

    measurement_space = SwingMeasurementSpace.from_dimensions(
        frame_width=frame_width,
        frame_height=frame_height,
    )
    ordered_frames = tuple(sorted(frames, key=lambda frame: frame.frame_index))
    detection_config = event_config or SwingEventDetectionConfig()
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
            phase_statuses=_phase_statuses_for_impact_policy(detection_config),
        )

    if len(ordered_frames) < 5:
        selected = _spread_frame_indexes(ordered_frames, 5)
        impact_statuses = _phase_statuses_for_impact_policy(detection_config)
        impact_method, impact_reason = _impact_policy_metadata(detection_config)
        fallback_reasons = {
            phase: "Automatic phase fallback used fewer than five unique frames."
            for phase in SwingPhase
        }
        fallback_reasons.update({SwingPhase.IMPACT: impact_reason} if impact_reason else {})
        detection_methods = {phase: "short_sequence_fallback" for phase in SwingPhase}
        if impact_method is not None:
            detection_methods[SwingPhase.IMPACT] = impact_method
        return SwingPhaseFrames(
            setup=selected[0],
            stride=selected[1],
            foot_strike=selected[2],
            impact=selected[3],
            follow_through=selected[4],
            confidence=0.4,
            limitations=("Automatic phase fallback used fewer than five unique frames.",),
            phase_confidences={phase: 0.4 for phase in SwingPhase},
            detection_methods=detection_methods,
            phase_fallback_reasons=fallback_reasons,
            phase_statuses=impact_statuses,
        )

    detected = _detect_motion_aware_phase_positions(
        ordered_frames,
        measurement_space,
        detection_config,
    )
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
        frame_quality=detected.frame_quality,
        active_window=detected.active_window,
        phase_fallback_reasons=detected.fallback_reasons,
        phase_statuses=detected.phase_statuses,
    )


def calculate_swing_metrics(
    frames: Sequence[PoseFrame],
    phases: SwingPhaseFrames,
    handedness: SwingHandedness,
    *,
    min_keypoint_confidence: float = 0.2,
    frame_width: int | None = None,
    frame_height: int | None = None,
) -> tuple[SwingMetricValue, ...]:
    """Calculate raw v2 baseline swing metrics from pose observations."""
    frame_by_index = {frame.frame_index: frame for frame in frames}
    measurement_space = SwingMeasurementSpace.from_dimensions(
        frame_width=frame_width,
        frame_height=frame_height,
    )
    sides = resolve_body_sides(handedness)
    limitations = (sides.limitation,) if sides.limitation else ()
    setup = frame_by_index[phases.setup]
    stride = frame_by_index[phases.stride]
    foot_strike = frame_by_index[phases.foot_strike]
    impact = frame_by_index[phases.impact]
    follow_through = frame_by_index[phases.follow_through]
    impact_unavailable_reason = _impact_unavailable_metric_reason(phases)
    no_ball_fallback_reason = _no_ball_metric_fallback_reason(phases)
    torso_tilt_preservation = (
        _missing_metric(
            SwingMetricName.TORSO_TILT_PRESERVATION,
            impact_unavailable_reason,
            (setup.frame_index, impact.frame_index),
        )
        if impact_unavailable_reason is not None
        else _torso_tilt_preservation(
            setup,
            impact,
            min_keypoint_confidence,
            limitations,
            measurement_space,
        )
    )
    head_translation_ratio = (
        _limited_metric(
            _head_translation_ratio(
                setup,
                foot_strike,
                min_keypoint_confidence,
                measurement_space,
            ),
            no_ball_fallback_reason,
            confidence_multiplier=0.75,
        )
        if no_ball_fallback_reason is not None
        else _head_translation_ratio(setup, impact, min_keypoint_confidence, measurement_space)
    )
    lead_knee_blocking_index = (
        _missing_metric(
            SwingMetricName.LEAD_KNEE_BLOCKING_INDEX,
            impact_unavailable_reason,
            (foot_strike.frame_index, impact.frame_index),
        )
        if impact_unavailable_reason is not None
        else _lead_knee_blocking_index(
            foot_strike,
            impact,
            sides,
            min_keypoint_confidence,
            measurement_space,
        )
    )
    estimated_attack_angle = (
        _missing_metric(
            SwingMetricName.ESTIMATED_ATTACK_ANGLE,
            impact_unavailable_reason,
            (phases.foot_strike, phases.impact, phases.follow_through),
        )
        if impact_unavailable_reason is not None
        else _estimated_attack_angle(frames, phases, min_keypoint_confidence, measurement_space)
    )
    follow_through_posture_balance = (
        _limited_metric(
            _follow_through_posture_balance(
                foot_strike,
                follow_through,
                min_keypoint_confidence,
                measurement_space,
            ),
            no_ball_fallback_reason,
            confidence_multiplier=0.75,
        )
        if no_ball_fallback_reason is not None
        else _follow_through_posture_balance(
            impact,
            follow_through,
            min_keypoint_confidence,
            measurement_space,
        )
    )

    return (
        _normalized_stance_width(setup, min_keypoint_confidence, limitations, measurement_space),
        _torso_forward_tilt(setup, min_keypoint_confidence, limitations, measurement_space),
        torso_tilt_preservation,
        _grip_loading_vector(setup, sides, min_keypoint_confidence, limitations, measurement_space),
        _rear_knee_sway(
            setup,
            stride,
            sides,
            min_keypoint_confidence,
            limitations,
            measurement_space,
        ),
        head_translation_ratio,
        _early_connection_angle(
            foot_strike,
            sides,
            min_keypoint_confidence,
            limitations,
            measurement_space,
        ),
        lead_knee_blocking_index,
        _hip_shoulder_separation_timing(frames, min_keypoint_confidence, measurement_space),
        estimated_attack_angle,
        follow_through_posture_balance,
    )


def _impact_unavailable_metric_reason(phases: SwingPhaseFrames) -> str | None:
    if phases.is_available_for(SwingPhase.IMPACT):
        return None
    reason = phases.fallback_reason_for(SwingPhase.IMPACT)
    if reason is not None:
        return f"Impact-dependent metric was not evaluated. {reason}"
    return (
        "Impact-dependent metric was not evaluated because impact was not available "
        "as detected or estimated evidence."
    )


def _no_ball_metric_fallback_reason(phases: SwingPhaseFrames) -> str | None:
    if phases.is_available_for(SwingPhase.IMPACT):
        return None
    reason = phases.fallback_reason_for(SwingPhase.IMPACT)
    if reason is not None:
        return (
            "Impact was not available, so this non-contact metric used a no-ball "
            f"fallback anchor. {reason}"
        )
    return (
        "Impact was not available, so this non-contact metric used a no-ball fallback "
        "anchor instead of a body-pose contact proxy."
    )


def _limited_metric(
    metric: SwingMetricValue,
    limitation: str | None,
    *,
    confidence_multiplier: float,
) -> SwingMetricValue:
    if limitation is None:
        return metric
    if metric.value is None:
        return SwingMetricValue(
            name=metric.name,
            value=None,
            confidence=metric.confidence,
            evidence_frames=metric.evidence_frames,
            limitations=metric.limitations + (limitation,),
        )
    return SwingMetricValue(
        name=metric.name,
        value=metric.value,
        confidence=max(0.0, min(1.0, metric.confidence * confidence_multiplier)),
        evidence_frames=metric.evidence_frames,
        limitations=metric.limitations + (limitation,),
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


def torso_length(
    frame: PoseFrame,
    *,
    min_confidence: float = 0.2,
    measurement_space: SwingMeasurementSpace | None = None,
) -> float | None:
    """Return a scale value from shoulder and hip midpoints."""
    measurement_space = measurement_space or SwingMeasurementSpace()
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
    length = measurement_space.distance(shoulder.point, hip.point)
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


def _phase_statuses_for_impact_policy(
    config: SwingEventDetectionConfig,
) -> dict[SwingPhase, SwingEventStatus]:
    statuses = {phase: SwingEventStatus.DETECTED for phase in SwingPhase}
    if config.impact_detection_policy == SwingImpactDetectionPolicy.BODY_POSE_ESTIMATED:
        statuses[SwingPhase.IMPACT] = SwingEventStatus.ESTIMATED
    elif config.impact_detection_policy == SwingImpactDetectionPolicy.REQUIRE_BALL_CONTACT:
        statuses[SwingPhase.IMPACT] = SwingEventStatus.UNAVAILABLE
    elif config.impact_detection_policy == SwingImpactDetectionPolicy.SKIP_WITHOUT_BALL:
        statuses[SwingPhase.IMPACT] = SwingEventStatus.SKIPPED
    return statuses


def _impact_policy_metadata(
    config: SwingEventDetectionConfig,
) -> tuple[str | None, str | None]:
    if config.impact_detection_policy == SwingImpactDetectionPolicy.REQUIRE_BALL_CONTACT:
        return (
            "ball_contact_required_unavailable",
            "Impact was marked unavailable because ball/contact detection is required but "
            "no contact detector or ball evidence is available.",
        )
    if config.impact_detection_policy == SwingImpactDetectionPolicy.SKIP_WITHOUT_BALL:
        return (
            "impact_skipped_without_ball",
            "Impact was skipped because no ball/contact evidence is available.",
        )
    return None, None


def _detect_motion_aware_phase_positions(
    frames: Sequence[PoseFrame],
    measurement_space: SwingMeasurementSpace,
    event_config: SwingEventDetectionConfig,
) -> _DetectedPhasePositions:
    frame_quality = _classify_swing_frame_quality(frames, measurement_space)
    analysis_frames = _phase_candidate_frames(frames, frame_quality)
    used_rejected_fallback = False
    if len(analysis_frames) < 5:
        analysis_frames = tuple(frames)
        used_rejected_fallback = True
    frame_positions = {id(frame): position for position, frame in enumerate(frames)}
    movement_scores = _movement_scores(analysis_frames, measurement_space)
    smoothed_scores = _smoothed_scores(movement_scores)
    active_window = _active_swing_window(analysis_frames, smoothed_scores)
    window_frames = _frames_in_active_window(analysis_frames, active_window)
    setup_analysis_position, setup_fallback_reason = _setup_position_before_active_window(
        analysis_frames,
        active_window,
        measurement_space,
    )
    window_scores = _movement_scores(window_frames, measurement_space)
    preliminary_impact_window_position = _impact_position(
        window_frames,
        window_scores,
        measurement_space,
    )
    preliminary_impact_frame = window_frames[preliminary_impact_window_position]
    preliminary_impact_position = analysis_frames.index(preliminary_impact_frame)
    phase_statuses = _phase_statuses_for_impact_policy(event_config)
    stride_selection = _stride_position(
        analysis_frames,
        movement_scores,
        setup_analysis_position,
        preliminary_impact_position,
        measurement_space,
        setup_uncertain=setup_fallback_reason is not None,
        handedness=event_config.handedness,
    )
    analysis_stride_position = stride_selection.position
    stride_fallback_reason = stride_selection.fallback_reason
    analysis_foot_strike_position, foot_strike_fallback_reason = _foot_strike_position(
        analysis_frames,
        setup_position=setup_analysis_position,
        stride_position=analysis_stride_position,
        impact_position=preliminary_impact_position,
        measurement_space=measurement_space,
        lift_analysis=stride_selection.lift,
    )
    analysis_impact_position, estimated_impact_fallback_reason = _refined_impact_position(
        analysis_frames,
        movement_scores,
        foot_strike_position=analysis_foot_strike_position,
        preliminary_impact_position=preliminary_impact_position,
        measurement_space=measurement_space,
        active_window=active_window,
        handedness=event_config.handedness,
    )
    follow_analysis_position, follow_fallback_reason = _follow_through_position(
        analysis_frames,
        impact_position=analysis_impact_position,
        foot_strike_position=analysis_foot_strike_position,
        movement_scores=movement_scores,
        measurement_space=measurement_space,
        active_window=active_window,
        impact_available=phase_statuses[SwingPhase.IMPACT]
        in {SwingEventStatus.DETECTED, SwingEventStatus.ESTIMATED},
    )
    raw_analysis_positions = (
        setup_analysis_position,
        analysis_stride_position,
        analysis_foot_strike_position,
        analysis_impact_position,
        follow_analysis_position,
    )
    repaired_analysis_positions = _ordered_unique_positions(
        raw_analysis_positions,
        max_position=len(analysis_frames) - 1,
    )
    positions = (
        frame_positions[id(analysis_frames[repaired_analysis_positions[0]])],
        frame_positions[id(analysis_frames[repaired_analysis_positions[1]])],
        frame_positions[id(analysis_frames[repaired_analysis_positions[2]])],
        frame_positions[id(analysis_frames[repaired_analysis_positions[3]])],
        frame_positions[id(analysis_frames[repaired_analysis_positions[4]])],
    )
    cue_count = sum(1 for score in smoothed_scores if score > _legacy_rate_threshold(0.02))
    quality_ratio = frame_quality.usable_frame_count / max(1, frame_quality.total_frame_count)
    confidence = 0.84 if cue_count >= 2 and active_window.fallback_reason is None else 0.58
    confidence = round(max(0.35, min(0.9, confidence * max(0.55, quality_ratio))), 3)
    phase_confidences = {
        SwingPhase.SETUP: min(0.9, confidence + 0.05),
        SwingPhase.STRIDE: confidence,
        SwingPhase.FOOT_STRIKE: max(0.45, confidence - 0.05),
        SwingPhase.IMPACT: confidence,
        SwingPhase.FOLLOW_THROUGH: max(0.45, confidence - 0.05),
    }
    detection_methods = {
        SwingPhase.SETUP: "stable_pre_motion_window",
        SwingPhase.STRIDE: stride_selection.detection_method,
        SwingPhase.FOOT_STRIKE: "lead_foot_plant_window",
        SwingPhase.IMPACT: "estimated_body_motion_contact_window",
        SwingPhase.FOLLOW_THROUGH: "post_impact_extension_window",
    }
    fallback_reasons: dict[SwingPhase, str] = {}
    limitations: list[str] = [
        "Impact is an estimated impact window from body-pose motion cues; bat/ball "
        "contact is not detected."
    ]
    impact_method, impact_fallback_reason = _impact_policy_metadata(event_config)
    if impact_method is not None:
        detection_methods[SwingPhase.IMPACT] = impact_method
    if impact_fallback_reason is not None:
        fallback_reasons[SwingPhase.IMPACT] = impact_fallback_reason
        limitations.append(impact_fallback_reason)
        phase_confidences[SwingPhase.IMPACT] = 0.0
    phase_fallbacks = {
        SwingPhase.SETUP: setup_fallback_reason,
        SwingPhase.STRIDE: stride_fallback_reason,
        SwingPhase.FOOT_STRIKE: foot_strike_fallback_reason,
        SwingPhase.IMPACT: estimated_impact_fallback_reason
        if impact_fallback_reason is None
        else None,
        SwingPhase.FOLLOW_THROUGH: follow_fallback_reason,
    }
    for phase, reason in phase_fallbacks.items():
        if reason is None:
            continue
        fallback_reasons[phase] = reason
        limitations.append(reason)
        phase_confidences[phase] = max(
            0.35,
            phase_confidences[phase] - _phase_fallback_confidence_penalty(phase, reason),
        )
    if frame_quality.rejected_frame_count or frame_quality.weak_frame_count:
        limitations.append("Automatic phase detection ignored or down-weighted weak pose frame(s).")
    if used_rejected_fallback:
        reason = (
            "Fewer than five quality-accepted pose frames were available; automatic phase "
            "detection used the full ordered pose sequence with lower confidence."
        )
        limitations.append(reason)
        fallback_reasons.update({phase: reason for phase in SwingPhase})
    if active_window.fallback_reason:
        limitations.append(active_window.fallback_reason)
        fallback_reasons.update({phase: active_window.fallback_reason for phase in SwingPhase})
    if cue_count < 2:
        reason = (
            "Automatic phase detection found weak motion cues and used conservative "
            "ordered event selection."
        )
        limitations.append(reason)
        fallback_reasons.update({phase: reason for phase in SwingPhase})
    repaired_phases = _ordering_repair_reasons(raw_analysis_positions, repaired_analysis_positions)
    if repaired_phases:
        reason = (
            "Automatic phase ordering required conservative repair because one or more "
            "event candidates were not sequential."
        )
        limitations.append(reason)
        for phase in repaired_phases:
            fallback_reasons.setdefault(phase, reason)
    if impact_fallback_reason is not None:
        fallback_reasons[SwingPhase.IMPACT] = impact_fallback_reason
    return _DetectedPhasePositions(
        positions=positions,
        sequence_confidence=confidence,
        phase_confidences=phase_confidences,
        detection_methods=detection_methods,
        fallback_reasons=fallback_reasons,
        phase_statuses=phase_statuses,
        limitations=tuple(limitations),
        frame_quality=frame_quality,
        active_window=active_window,
    )


def _phase_fallback_confidence_penalty(phase: SwingPhase, reason: str) -> float:
    if phase == SwingPhase.STRIDE and "no sustained lead-leg lift" in reason:
        return 0.1
    return 0.2


def _classify_swing_frame_quality(
    frames: Sequence[PoseFrame],
    measurement_space: SwingMeasurementSpace,
) -> SwingFrameQualityDiagnostics:
    required = (
        PoseKeypointName.NOSE,
        PoseKeypointName.LEFT_SHOULDER,
        PoseKeypointName.RIGHT_SHOULDER,
        PoseKeypointName.LEFT_WRIST,
        PoseKeypointName.RIGHT_WRIST,
        PoseKeypointName.LEFT_HIP,
        PoseKeypointName.RIGHT_HIP,
        PoseKeypointName.LEFT_KNEE,
        PoseKeypointName.RIGHT_KNEE,
        PoseKeypointName.LEFT_ANKLE,
        PoseKeypointName.RIGHT_ANKLE,
    )
    qualities: list[SwingFrameQuality] = []
    previous_scale: float | None = None
    for frame in frames:
        reasons: list[str] = []
        present = [name for name in required if frame.get(name, min_confidence=0.1) is not None]
        coverage = len(present) / len(required)
        keypoints = tuple(frame.keypoints.values())
        confidences = [keypoint.confidence for keypoint in keypoints]
        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        min_confidence = min(confidences) if confidences else 0.0
        out_of_frame_ratio = (
            sum(1 for keypoint in keypoints if keypoint.out_of_frame) / len(keypoints)
            if keypoints
            else 1.0
        )
        scale = torso_length(frame, min_confidence=0.1, measurement_space=measurement_space)
        if coverage < 0.75:
            reasons.append("required_landmark_coverage_low")
        if mean_confidence < 0.45 or min_confidence < 0.15:
            reasons.append("landmark_confidence_low")
        if scale is None:
            reasons.append("torso_scale_missing")
        elif previous_scale is not None:
            ratio = scale / max(previous_scale, 0.01)
            if ratio > 1.8 or ratio < 0.55:
                reasons.append("body_scale_jump")
        if scale is not None:
            previous_scale = scale
        if out_of_frame_ratio > 0.25:
            reasons.append("many_landmarks_out_of_frame")
        if any(keypoint.interpolated for keypoint in keypoints):
            reasons.append("contains_interpolated_landmarks")
        missing_motion_group = (
            _grip_point(frame, 0.1) is None
            or all(
                frame.get(side_keypoint(side, "ankle"), min_confidence=0.1) is None
                for side in (BodySide.LEFT, BodySide.RIGHT)
            )
            or _side_to_side_vector(frame, "hip", 0.1) is None
            or _side_to_side_vector(frame, "shoulder", 0.1) is None
        )
        if missing_motion_group:
            reasons.append("phase_motion_keypoints_missing")

        score = max(0.0, min(1.0, coverage * 0.55 + mean_confidence * 0.35))
        score -= min(0.35, out_of_frame_ratio * 0.5)
        if scale is None or missing_motion_group:
            score -= 0.2
        score = round(max(0.0, min(1.0, score)), 3)
        if not keypoints or coverage < 0.45 or mean_confidence < 0.2 or scale is None:
            status = "rejected"
        elif reasons:
            status = "weak"
        else:
            status = "usable"
        qualities.append(
            SwingFrameQuality(
                frame_index=frame.frame_index,
                status=status,
                score=score,
                reasons=tuple(dict.fromkeys(reasons)),
            )
        )

    weak = tuple(quality.frame_index for quality in qualities if quality.status == "weak")
    rejected = tuple(quality.frame_index for quality in qualities if quality.status == "rejected")
    return SwingFrameQualityDiagnostics(
        total_frame_count=len(frames),
        usable_frame_count=sum(1 for quality in qualities if quality.status == "usable"),
        weak_frame_count=len(weak),
        rejected_frame_count=len(rejected),
        weak_frame_indexes=weak,
        rejected_frame_indexes=rejected,
        reasons_by_frame={
            quality.frame_index: quality.reasons for quality in qualities if quality.reasons
        },
    )


def _phase_candidate_frames(
    frames: Sequence[PoseFrame],
    diagnostics: SwingFrameQualityDiagnostics,
) -> tuple[PoseFrame, ...]:
    rejected = set(diagnostics.rejected_frame_indexes)
    candidates = tuple(frame for frame in frames if frame.frame_index not in rejected)
    return candidates or tuple(frames)


def _smoothed_scores(scores: Sequence[float]) -> tuple[float, ...]:
    if len(scores) < 3:
        return tuple(scores)
    smoothed: list[float] = []
    for index, _score in enumerate(scores):
        start = max(0, index - 1)
        end = min(len(scores), index + 2)
        window = scores[start:end]
        smoothed.append(sum(window) / len(window))
    return tuple(smoothed)


def _active_swing_window(
    frames: Sequence[PoseFrame],
    scores: Sequence[float],
) -> SwingActiveWindowDiagnostics:
    if not frames:
        return SwingActiveWindowDiagnostics(
            start_frame_index=0,
            end_frame_index=0,
            peak_motion_frame_index=0,
            confidence=0.0,
            fallback_reason="No pose frames were available for active swing window detection.",
        )
    if not scores or max(scores) <= _legacy_rate_threshold(0.02):
        return SwingActiveWindowDiagnostics(
            start_frame_index=frames[0].frame_index,
            end_frame_index=frames[-1].frame_index,
            peak_motion_frame_index=frames[min(len(frames) - 1, len(frames) // 2)].frame_index,
            confidence=0.35,
            fallback_reason=(
                "Active swing window detection found weak motion cues and used the full "
                "pose sequence."
            ),
        )
    peak_position = max(range(len(scores)), key=lambda position: scores[position])
    threshold = max(_legacy_rate_threshold(0.02), max(scores) * 0.18)
    active_positions = [position for position, score in enumerate(scores) if score >= threshold]
    start = max(0, min(active_positions) - 1)
    end = min(len(frames) - 1, max(active_positions) + 1)
    if end - start + 1 < min(5, len(frames)):
        needed = min(5, len(frames)) - (end - start + 1)
        start = max(0, start - ((needed + 1) // 2))
        end = min(len(frames) - 1, end + needed)
    active_ratio = (end - start + 1) / len(frames)
    confidence = round(max(0.45, min(0.9, 1.0 - active_ratio * 0.2)), 3)
    return SwingActiveWindowDiagnostics(
        start_frame_index=frames[start].frame_index,
        end_frame_index=frames[end].frame_index,
        peak_motion_frame_index=frames[peak_position].frame_index,
        confidence=confidence,
    )


def _frames_in_active_window(
    frames: Sequence[PoseFrame],
    active_window: SwingActiveWindowDiagnostics,
) -> tuple[PoseFrame, ...]:
    selected = tuple(
        frame
        for frame in frames
        if active_window.start_frame_index <= frame.frame_index <= active_window.end_frame_index
    )
    return selected or tuple(frames)


def _setup_position_before_active_window(
    frames: Sequence[PoseFrame],
    active_window: SwingActiveWindowDiagnostics,
    measurement_space: SwingMeasurementSpace,
) -> tuple[int, str | None]:
    pre_motion_positions = [
        position
        for position, frame in enumerate(frames)
        if frame.frame_index < active_window.start_frame_index
    ]
    early_limit = max(1, min(len(frames), max(3, round(len(frames) * 0.35))))
    early_positions = tuple(range(early_limit))
    if pre_motion_positions:
        candidate_positions = tuple(
            position for position in pre_motion_positions if position < early_limit
        )
        if not candidate_positions:
            candidate_positions = tuple(pre_motion_positions[: min(len(pre_motion_positions), 8)])
        candidate_frames = tuple(frames[position] for position in candidate_positions)
        local_position = _setup_position(candidate_frames, measurement_space)
        return candidate_positions[local_position], None

    candidate_frames = tuple(frames[position] for position in early_positions)
    setup_position = _setup_position(candidate_frames, measurement_space)
    reason = (
        "Setup may be unavailable or late because motion cues were already active in the "
        "first usable pose frames."
    )
    return early_positions[setup_position], reason


def _setup_position(
    frames: Sequence[PoseFrame],
    measurement_space: SwingMeasurementSpace,
) -> int:
    stable_limit = max(1, min(len(frames), 6))
    movement_scores = _movement_scores(frames[: stable_limit + 1], measurement_space)
    if not movement_scores:
        return 0
    return min(range(len(movement_scores)), key=lambda index: (movement_scores[index], index))


def _impact_position(
    frames: Sequence[PoseFrame],
    movement_scores: Sequence[float],
    measurement_space: SwingMeasurementSpace,
) -> int:
    if not movement_scores:
        return min(len(frames) - 2, max(1, round(len(frames) * 0.7)))
    start = max(1, round(len(frames) * 0.45))
    end = max(start + 1, len(frames) - 1)
    candidate_positions = range(start, end)
    return max(
        candidate_positions,
        key=lambda position: _impact_candidate_score(
            frames,
            movement_scores,
            position,
            measurement_space,
        ),
    )


def _refined_impact_position(
    frames: Sequence[PoseFrame],
    movement_scores: Sequence[float],
    *,
    foot_strike_position: int,
    preliminary_impact_position: int,
    measurement_space: SwingMeasurementSpace,
    active_window: SwingActiveWindowDiagnostics,
    handedness: SwingHandedness,
) -> tuple[int, str | None]:
    if len(frames) < 3:
        return preliminary_impact_position, None

    start = min(len(frames) - 1, max(foot_strike_position + 1, 1))
    active_end_position = _active_window_end_position(frames, active_window)
    end = min(len(frames) - 2, max(start, active_end_position))
    if start > end:
        fallback_position = min(
            len(frames) - 1,
            max(foot_strike_position + 1, preliminary_impact_position),
        )
        return fallback_position, (
            "Estimated impact used a conservative fallback because no post-foot-strike "
            "contact window was available."
        )

    candidate_positions = tuple(range(start, end + 1))
    best_position = max(
        candidate_positions,
        key=lambda position: (
            _refined_impact_candidate_score(
                frames,
                movement_scores,
                position=position,
                foot_strike_position=foot_strike_position,
                measurement_space=measurement_space,
                handedness=handedness,
            ),
            -abs(position - preliminary_impact_position),
            -position,
        ),
    )
    best_score = _refined_impact_candidate_score(
        frames,
        movement_scores,
        position=best_position,
        foot_strike_position=foot_strike_position,
        measurement_space=measurement_space,
        handedness=handedness,
    )
    if best_score < 0.12:
        return best_position, (
            "Estimated impact has lower confidence because post-foot-strike contact-zone "
            "body-pose cues were weak."
        )
    return best_position, None


def _active_window_end_position(
    frames: Sequence[PoseFrame],
    active_window: SwingActiveWindowDiagnostics,
) -> int:
    positions = [
        position
        for position, frame in enumerate(frames)
        if frame.frame_index <= active_window.end_frame_index
    ]
    return max(positions, default=len(frames) - 1)


def _refined_impact_candidate_score(
    frames: Sequence[PoseFrame],
    movement_scores: Sequence[float],
    *,
    position: int,
    foot_strike_position: int,
    measurement_space: SwingMeasurementSpace,
    handedness: SwingHandedness,
) -> float:
    base = _impact_candidate_score(frames, movement_scores, position, measurement_space)
    contact_zone = _grip_contact_zone_score(frames[position], measurement_space)
    bracing = _lead_side_bracing_score(
        frames,
        foot_strike_position=foot_strike_position,
        position=position,
        handedness=handedness,
        measurement_space=measurement_space,
    )
    rotation = _rotation_magnitude(frames[position], measurement_space)
    movement = movement_scores[position] if position < len(movement_scores) else 0.0
    previous_movement = movement_scores[position - 1] if position > 0 else movement
    next_movement = (
        movement_scores[position + 1] if position + 1 < len(movement_scores) else movement
    )
    transition = max(0.0, movement - previous_movement) + max(0.0, movement - next_movement)
    post_strike_progress = min(1.0, max(0.0, (position - foot_strike_position) / 3.0))
    score = (
        base * 0.55
        + contact_zone * 0.22
        + bracing * 0.08
        + rotation * 0.07
        + transition * 0.05
        + post_strike_progress * 0.03
    )
    if contact_zone < 0.2:
        score *= 0.35
    elif contact_zone < 0.45 and position <= foot_strike_position + 1:
        score *= 0.7
    if movement < _legacy_rate_threshold(0.02) and contact_zone < 0.5:
        score *= 0.6
    if (
        next_movement < movement * 0.35
        and contact_zone < 0.55
        and position > foot_strike_position + 2
    ):
        score *= 0.7
    return score


def _lead_side_bracing_score(
    frames: Sequence[PoseFrame],
    *,
    foot_strike_position: int,
    position: int,
    handedness: SwingHandedness,
    measurement_space: SwingMeasurementSpace,
) -> float:
    sides = resolve_body_sides(handedness)
    foot_angle = _side_knee_angle(
        frames[foot_strike_position],
        sides.lead,
        min_confidence=0.1,
        measurement_space=measurement_space,
    )
    impact_angle = _side_knee_angle(
        frames[position],
        sides.lead,
        min_confidence=0.1,
        measurement_space=measurement_space,
    )
    if foot_angle is None or impact_angle is None:
        return 0.0
    angle_change = impact_angle[0] - foot_angle[0]
    collapse_penalty = max(0.0, -angle_change / 30.0)
    extension_bonus = max(0.0, angle_change / 25.0)
    return max(0.0, min(1.0, 0.55 + extension_bonus - collapse_penalty))


def _impact_candidate_score(
    frames: Sequence[PoseFrame],
    movement_scores: Sequence[float],
    position: int,
    measurement_space: SwingMeasurementSpace,
) -> float:
    movement = movement_scores[position] if position < len(movement_scores) else 0.0
    previous = movement_scores[position - 1] if position > 0 else movement
    next_score = movement_scores[position + 1] if position + 1 < len(movement_scores) else movement
    acceleration = max(0.0, movement - previous)
    deceleration = max(0.0, movement - next_score)
    grip_forward = _grip_contact_zone_score(frames[position], measurement_space)
    rotation = _rotation_magnitude(frames[position], measurement_space)
    contact_weighted_movement = movement * grip_forward
    return (
        contact_weighted_movement * 0.45
        + acceleration * grip_forward * 0.15
        + deceleration * grip_forward * 0.15
        + grip_forward * 0.15
        + rotation * 0.10
    )


def _grip_contact_zone_score(
    frame: PoseFrame,
    measurement_space: SwingMeasurementSpace,
) -> float:
    grip = _grip_point(frame, 0.1)
    shoulder = _midpoint_keypoint(
        frame,
        PoseKeypointName.LEFT_SHOULDER,
        PoseKeypointName.RIGHT_SHOULDER,
        min_confidence=0.1,
    )
    scale = torso_length(frame, min_confidence=0.1, measurement_space=measurement_space) or 0.25
    if grip is None or shoulder is None:
        return 0.0
    forward_ratio = measurement_space.horizontal_distance(grip.point, shoulder.point) / max(
        scale,
        0.01,
    )
    if forward_ratio <= 0.35:
        return max(0.0, forward_ratio / 0.35 * 0.65)
    if forward_ratio <= 1.4:
        return max(0.0, 1.0 - abs(forward_ratio - 0.8) / 1.2)
    if forward_ratio <= 2.4:
        return max(0.0, 0.5 - (forward_ratio - 1.4) * 0.45)
    return max(0.0, 0.05 - (forward_ratio - 2.4) * 0.05)


def _rotation_magnitude(
    frame: PoseFrame,
    measurement_space: SwingMeasurementSpace,
) -> float:
    values: list[float] = []
    for part in ("hip", "shoulder"):
        vector = _side_to_side_vector(frame, part, 0.1)
        if vector is None:
            continue
        angle = measurement_space.vector_angle_degrees(vector[0].point, vector[1].point)
        values.append(min(1.0, angle_difference_degrees(angle, 0.0) / 45.0))
    return max(values, default=0.0)


def _stride_position(
    frames: Sequence[PoseFrame],
    movement_scores: Sequence[float],
    setup_position: int,
    impact_position: int,
    measurement_space: SwingMeasurementSpace,
    *,
    setup_uncertain: bool = False,
    handedness: SwingHandedness = SwingHandedness.UNKNOWN,
) -> _StrideSelection:
    lift = _lead_leg_lift_analysis(
        frames,
        setup_position=setup_position,
        impact_position=impact_position,
        measurement_space=measurement_space,
        handedness=handedness,
    )
    if impact_position - setup_position <= 2:
        return _StrideSelection(
            position=min(len(frames) - 4, setup_position + 1),
            fallback_reason=(
                "Stride confidence was capped because setup and estimated impact were too close."
            ),
            detection_method="lower_body_load_sparse_fallback",
            lift=lift,
        )
    if lift.has_lift and lift.peak_position is not None:
        return _StrideSelection(
            position=lift.peak_position,
            fallback_reason=(
                "Stride confidence was capped because setup may be unavailable or late."
                if setup_uncertain
                else None
            ),
            detection_method="lead_leg_lift_peak",
            lift=lift,
        )
    minimum_separation = 2 if impact_position - setup_position >= 4 else 1
    start = min(impact_position - 1, setup_position + minimum_separation)
    candidates = range(start, impact_position)
    scores = {
        position: _stride_candidate_score(
            frames,
            setup_position=setup_position,
            position=position,
            movement_score=movement_scores[position] if position < len(movement_scores) else 0.0,
            measurement_space=measurement_space,
        )
        for position in candidates
    }
    fallback_reason = (
        "Stride confidence was capped because setup may be unavailable or late."
        if setup_uncertain
        else None
    )
    for position in candidates:
        if scores[position] >= _legacy_rate_threshold(0.018):
            return _StrideSelection(
                position=position,
                fallback_reason=fallback_reason or lift.fallback_reason,
                detection_method="lower_body_load_no_leg_lift_fallback",
                lift=lift,
            )
    fallback_position = max(start, round((setup_position + impact_position) * 0.4))
    reason = (
        "Stride onset used a conservative fallback because sustained lower-body loading was weak."
    )
    return _StrideSelection(
        position=fallback_position,
        fallback_reason=fallback_reason or lift.fallback_reason or reason,
        detection_method="lower_body_load_no_leg_lift_fallback",
        lift=lift,
    )


def _lead_leg_lift_analysis(
    frames: Sequence[PoseFrame],
    *,
    setup_position: int,
    impact_position: int,
    measurement_space: SwingMeasurementSpace,
    handedness: SwingHandedness,
) -> _LeadLegLiftAnalysis:
    search_positions = tuple(range(setup_position + 1, max(setup_position + 1, impact_position)))
    if not search_positions:
        return _LeadLegLiftAnalysis(
            lead_side=None,
            onset_position=None,
            peak_position=None,
            max_lift_ratio=0.0,
            has_lift=False,
            fallback_reason="Stride leg lift could not be evaluated from the available frames.",
        )
    preferred_side = (
        resolve_body_sides(handedness).lead if handedness != SwingHandedness.UNKNOWN else None
    )
    side_scores = {
        side: _lead_leg_lift_scores(
            frames,
            setup_position=setup_position,
            positions=search_positions,
            side=side,
            measurement_space=measurement_space,
        )
        for side in (BodySide.LEFT, BodySide.RIGHT)
    }
    if preferred_side is not None and max(side_scores[preferred_side].values(), default=0.0) > 0.02:
        lead_side = preferred_side
    else:
        lead_side = max(
            side_scores,
            key=lambda side: max(side_scores[side].values(), default=0.0),
        )
    scores = side_scores[lead_side]
    max_lift = max(scores.values(), default=0.0)
    peak_position = max(scores, key=lambda position: scores[position]) if scores else None
    has_lift = max_lift >= 0.055
    onset_position = None
    if has_lift:
        for position in search_positions:
            future_peak = max(
                (scores[future] for future in search_positions if future >= position),
                default=0.0,
            )
            if scores.get(position, 0.0) >= 0.035 and future_peak >= 0.055:
                onset_position = position
                break
    fallback_reason = None
    if not has_lift:
        fallback_reason = (
            "Stride used a no-stride lower-body-load fallback because no sustained "
            "lead-leg lift was detected."
        )
    return _LeadLegLiftAnalysis(
        lead_side=lead_side,
        onset_position=onset_position,
        peak_position=peak_position,
        max_lift_ratio=round(max_lift, 4),
        has_lift=has_lift,
        fallback_reason=fallback_reason,
    )


def _lead_leg_lift_scores(
    frames: Sequence[PoseFrame],
    *,
    setup_position: int,
    positions: Sequence[int],
    side: BodySide,
    measurement_space: SwingMeasurementSpace,
) -> dict[int, float]:
    setup = frames[setup_position]
    setup_ankle = setup.get(side_keypoint(side, "ankle"), min_confidence=0.1)
    setup_knee = setup.get(side_keypoint(side, "knee"), min_confidence=0.1)
    scores: dict[int, float] = {}
    if setup_ankle is None and setup_knee is None:
        return scores
    for position in positions:
        current = frames[position]
        scale = (
            torso_length(setup, min_confidence=0.1, measurement_space=measurement_space)
            or torso_length(current, min_confidence=0.1, measurement_space=measurement_space)
            or 0.25
        )
        values: list[float] = []
        current_ankle = current.get(side_keypoint(side, "ankle"), min_confidence=0.1)
        if setup_ankle is not None and current_ankle is not None:
            values.append(
                max(
                    0.0,
                    (
                        measurement_space.point(setup_ankle.point).y
                        - measurement_space.point(current_ankle.point).y
                    )
                    / max(scale, 0.01),
                )
            )
        current_knee = current.get(side_keypoint(side, "knee"), min_confidence=0.1)
        if setup_knee is not None and current_knee is not None:
            values.append(
                max(
                    0.0,
                    (
                        measurement_space.point(setup_knee.point).y
                        - measurement_space.point(current_knee.point).y
                    )
                    / max(scale, 0.01)
                    * 0.6,
                )
            )
        scores[position] = max(values, default=0.0)
    return scores


def _stride_candidate_score(
    frames: Sequence[PoseFrame],
    *,
    setup_position: int,
    position: int,
    movement_score: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    setup = frames[setup_position]
    previous = frames[max(setup_position, position - 1)]
    current = frames[position]
    scale = torso_length(setup, min_confidence=0.1, measurement_space=measurement_space)
    scale = scale or torso_length(current, min_confidence=0.1, measurement_space=measurement_space)
    scale = scale or 0.25
    ankle_load = _max_ankle_displacement(setup, current, scale, measurement_space)
    knee_load = _max_knee_displacement(setup, current, scale, measurement_space)
    hip_load = _hip_midpoint_displacement(setup, current, scale, measurement_space)
    head_controlled_move = _head_displacement(setup, current, scale, measurement_space)
    rotation = _rotation_change_rate(previous, current, measurement_space) / 45.0
    return (
        ankle_load * 0.38
        + knee_load * 0.20
        + hip_load * 0.20
        + head_controlled_move * 0.12
        + rotation * 0.07
    )


def _foot_strike_position(
    frames: Sequence[PoseFrame],
    *,
    setup_position: int,
    stride_position: int,
    impact_position: int,
    measurement_space: SwingMeasurementSpace,
    lift_analysis: _LeadLegLiftAnalysis,
) -> tuple[int, str | None]:
    if impact_position - stride_position <= 1:
        return max(stride_position, impact_position - 1), (
            "Foot strike used a conservative fallback because stride and impact were too close."
        )

    lead_side = lift_analysis.lead_side or _lead_ankle_side_from_stride(
        frames,
        setup_position=setup_position,
        stride_position=stride_position,
        impact_position=impact_position,
        measurement_space=measurement_space,
    )
    ankle_changes = _ankle_displacement_from_setup(
        frames,
        measurement_space,
        setup_position=setup_position,
        lead_side=lead_side,
    )
    ankle_velocities = _ankle_velocity_series(
        frames,
        measurement_space,
        lead_side=lead_side,
    )
    if lift_analysis.has_lift and lift_analysis.peak_position is not None:
        lift_scores = (
            _lead_leg_lift_scores(
                frames,
                setup_position=setup_position,
                positions=range(lift_analysis.peak_position + 1, impact_position),
                side=lead_side,
                measurement_space=measurement_space,
            )
            if lead_side is not None
            else {}
        )
        search_positions = tuple(range(lift_analysis.peak_position + 1, impact_position))
        for position in search_positions:
            returned_near_ground = lift_scores.get(position, 0.0) <= max(
                0.025,
                lift_analysis.max_lift_ratio * 0.35,
            )
            if returned_near_ground and _plant_persists(
                ankle_velocities, position, search_positions
            ):
                return position, None
        if search_positions:
            return max(
                search_positions,
                key=lambda position: _foot_strike_candidate_score(
                    ankle_changes,
                    ankle_velocities,
                    position,
                ),
            ), (
                "Foot strike used a lower-confidence plant fallback because lead-foot "
                "lift was visible but descent/plant stabilization was sparse."
            )
    search_positions = tuple(range(stride_position + 1, impact_position))
    for position in search_positions:
        if ankle_changes[position] >= 0.035 and _plant_persists(
            ankle_velocities, position, search_positions
        ):
            return position, None
    if any(ankle_changes[position] > 0.01 for position in search_positions):
        return max(
            search_positions,
            key=lambda position: _foot_strike_candidate_score(
                ankle_changes,
                ankle_velocities,
                position,
            ),
        ), ("Foot strike used a no-stride plant proxy because no prior lead-leg lift was detected.")
    return max(stride_position + 1, impact_position - 1), (
        "Foot strike was lower confidence because no prior lead-leg lift or clear plant "
        "was detected."
    )


def _plant_persists(
    ankle_velocities: Sequence[float],
    position: int,
    search_positions: Sequence[int],
) -> bool:
    next_velocity = (
        ankle_velocities[position + 1]
        if position + 1 < len(ankle_velocities)
        else ankle_velocities[position]
        if position < len(ankle_velocities)
        else 0.0
    )
    if next_velocity > _legacy_rate_threshold(0.04):
        return False
    if len(search_positions) < 3:
        return True
    check_positions = tuple(
        next_position
        for next_position in (position + 1, position + 2)
        if next_position in search_positions and next_position < len(ankle_velocities)
    )
    if not check_positions:
        return True
    return all(
        ankle_velocities[next_position] <= _legacy_rate_threshold(0.045)
        for next_position in check_positions
    )


def _foot_strike_candidate_score(
    ankle_changes: Sequence[float],
    ankle_velocities: Sequence[float],
    position: int,
) -> float:
    current_velocity = ankle_velocities[position] if position < len(ankle_velocities) else 0.0
    next_velocity = (
        ankle_velocities[position + 1] if position + 1 < len(ankle_velocities) else current_velocity
    )
    plant_deceleration = max(0.0, current_velocity - next_velocity)
    stability = max(0.0, 1.0 - next_velocity / _legacy_rate_threshold(0.04)) * min(
        ankle_changes[position],
        1.0,
    )
    return ankle_changes[position] * 0.35 + plant_deceleration * 0.45 + stability * 0.20


def _follow_through_position(
    frames: Sequence[PoseFrame],
    *,
    impact_position: int,
    foot_strike_position: int,
    movement_scores: Sequence[float],
    measurement_space: SwingMeasurementSpace,
    active_window: SwingActiveWindowDiagnostics,
    impact_available: bool,
) -> tuple[int, str | None]:
    reference_position = impact_position if impact_available else foot_strike_position
    start = max(reference_position + 1, foot_strike_position + 1)
    if start >= len(frames):
        return len(frames) - 1, (
            "Follow-through used the last available pose frame because no post-impact "
            "frames were available."
        )
    search_positions = _follow_through_search_positions(
        frames,
        start_position=start,
        reference_position=reference_position,
        active_window=active_window,
    )
    if not search_positions:
        return len(frames) - 1, (
            "Follow-through finish was outside the bounded post-swing search window."
        )
    scores = {
        position: _follow_through_candidate_score(
            frames,
            reference_position=reference_position,
            position=position,
            movement_scores=movement_scores,
            measurement_space=measurement_space,
        )
        for position in search_positions
    }
    best_score = max(scores.values())
    threshold = best_score * 0.92
    for position in search_positions:
        if scores[position] >= threshold:
            reason = None
            if position == search_positions[-1] and _movement_at(
                position, movement_scores
            ) > _legacy_rate_threshold(0.035):
                reason = (
                    "Follow-through finish may be outside the bounded swing window because "
                    "the last searched pose frame still showed motion."
                )
            return position, reason
    return max(search_positions, key=lambda position: scores[position]), None


def _follow_through_search_positions(
    frames: Sequence[PoseFrame],
    *,
    start_position: int,
    reference_position: int,
    active_window: SwingActiveWindowDiagnostics,
) -> tuple[int, ...]:
    active_end_position = max(
        (
            position
            for position, frame in enumerate(frames)
            if frame.frame_index <= active_window.end_frame_index
        ),
        default=len(frames) - 1,
    )
    bounded_end = min(len(frames) - 1, max(active_end_position + 2, start_position))
    reference_timestamp = frames[reference_position].timestamp_seconds
    if reference_timestamp is not None:
        timestamp_end_positions: list[int] = []
        for position in range(start_position, bounded_end + 1):
            timestamp = frames[position].timestamp_seconds
            if timestamp is None or timestamp <= reference_timestamp + 0.8:
                timestamp_end_positions.append(position)
        if timestamp_end_positions:
            bounded_end = min(bounded_end, max(timestamp_end_positions))
    else:
        bounded_end = min(bounded_end, reference_position + 12)
    return tuple(range(start_position, bounded_end + 1))


def _follow_through_candidate_score(
    frames: Sequence[PoseFrame],
    *,
    reference_position: int,
    position: int,
    movement_scores: Sequence[float],
    measurement_space: SwingMeasurementSpace,
) -> float:
    impact = frames[reference_position]
    current = frames[position]
    scale = torso_length(impact, min_confidence=0.1, measurement_space=measurement_space)
    scale = scale or torso_length(current, min_confidence=0.1, measurement_space=measurement_space)
    scale = scale or 0.25
    grip_extension = _grip_displacement(impact, current, scale, measurement_space)
    current_motion = movement_scores[position] if position < len(movement_scores) else 0.0
    previous_motion = movement_scores[position - 1] if position > 0 else current_motion
    deceleration = max(0.0, previous_motion - current_motion)
    rotation = _rotation_magnitude(current, measurement_space) * 0.08
    posture = _head_displacement(impact, current, scale, measurement_space)
    body_translation = max(
        posture, _hip_midpoint_displacement(impact, current, scale, measurement_space)
    )
    balance_penalty = min(0.35, posture * 0.15 + max(0.0, body_translation - 0.45) * 0.35)
    return grip_extension * 0.55 + deceleration * 0.30 + rotation - balance_penalty


def _movement_at(position: int, movement_scores: Sequence[float]) -> float:
    return movement_scores[position] if position < len(movement_scores) else 0.0


def _movement_scores(
    frames: Sequence[PoseFrame],
    measurement_space: SwingMeasurementSpace,
) -> tuple[float, ...]:
    if not frames:
        return ()
    scores = [0.0]
    for index in range(1, len(frames)):
        previous = frames[index - 1]
        current = frames[index]
        scale = torso_length(
            previous,
            min_confidence=0.1,
            measurement_space=measurement_space,
        ) or torso_length(
            current,
            min_confidence=0.1,
            measurement_space=measurement_space,
        )
        scale = scale or 0.25
        grip_score = _point_velocity_rate(previous, current, _grip_point, scale, measurement_space)
        ankle_score = _ankle_velocity_rate(previous, current, scale, measurement_space)
        rotation_score = _rotation_change_rate(previous, current, measurement_space) / 45.0
        scores.append(grip_score * 0.6 + ankle_score * 0.25 + rotation_score * 0.15)
    return tuple(scores)


def _point_velocity_rate(
    previous: PoseFrame,
    current: PoseFrame,
    getter: Callable[[PoseFrame, float], PoseKeypoint | None],
    scale: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    previous_point = getter(previous, 0.1)
    current_point = getter(current, 0.1)
    if previous_point is None or current_point is None:
        return 0.0
    delta_seconds = _timestamp_delta_seconds(previous, current)
    if delta_seconds is None:
        return 0.0
    distance = measurement_space.distance(previous_point.point, current_point.point)
    return distance / max(scale, 0.01) / delta_seconds


def _ankle_velocity_rate(
    previous: PoseFrame,
    current: PoseFrame,
    scale: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    delta_seconds = _timestamp_delta_seconds(previous, current)
    if delta_seconds is None:
        return 0.0
    values: list[float] = []
    for side in (BodySide.LEFT, BodySide.RIGHT):
        name = side_keypoint(side, "ankle")
        previous_point = previous.get(name, min_confidence=0.1)
        current_point = current.get(name, min_confidence=0.1)
        if previous_point is None or current_point is None:
            continue
        values.append(
            measurement_space.distance(previous_point.point, current_point.point)
            / max(scale, 0.01)
            / delta_seconds
        )
    return max(values, default=0.0)


def _ankle_velocity_series(
    frames: Sequence[PoseFrame],
    measurement_space: SwingMeasurementSpace,
    *,
    lead_side: BodySide | None = None,
) -> tuple[float, ...]:
    if not frames:
        return ()
    values = [0.0]
    for index in range(1, len(frames)):
        previous = frames[index - 1]
        current = frames[index]
        scale = (
            torso_length(previous, min_confidence=0.1, measurement_space=measurement_space)
            or torso_length(current, min_confidence=0.1, measurement_space=measurement_space)
            or 0.25
        )
        if lead_side is None:
            values.append(_ankle_velocity_rate(previous, current, scale, measurement_space))
            continue
        previous_point = previous.get(side_keypoint(lead_side, "ankle"), min_confidence=0.1)
        current_point = current.get(side_keypoint(lead_side, "ankle"), min_confidence=0.1)
        if previous_point is None or current_point is None:
            values.append(0.0)
            continue
        delta_seconds = _timestamp_delta_seconds(previous, current)
        if delta_seconds is None:
            values.append(0.0)
            continue
        values.append(
            measurement_space.distance(previous_point.point, current_point.point)
            / max(scale, 0.01)
            / delta_seconds
        )
    return tuple(values)


def _rotation_change_rate(
    previous: PoseFrame,
    current: PoseFrame,
    measurement_space: SwingMeasurementSpace,
) -> float:
    delta_seconds = _timestamp_delta_seconds(previous, current)
    if delta_seconds is None:
        return 0.0
    changes: list[float] = []
    for part in ("hip", "shoulder"):
        previous_vector = _side_to_side_vector(previous, part, 0.1)
        current_vector = _side_to_side_vector(current, part, 0.1)
        if previous_vector is None or current_vector is None:
            continue
        previous_angle = measurement_space.vector_angle_degrees(
            previous_vector[0].point,
            previous_vector[1].point,
        )
        current_angle = measurement_space.vector_angle_degrees(
            current_vector[0].point,
            current_vector[1].point,
        )
        changes.append(angle_difference_degrees(current_angle, previous_angle) / delta_seconds)
    return max(changes, default=0.0)


def _timestamp_delta_seconds(previous: PoseFrame, current: PoseFrame) -> float | None:
    if previous.timestamp_seconds is None or current.timestamp_seconds is None:
        return 1.0 / _REFERENCE_FPS
    delta = current.timestamp_seconds - previous.timestamp_seconds
    if not math.isfinite(delta) or delta < _MIN_VALID_DELTA_SECONDS:
        return None
    if delta > _SPARSE_DELTA_SECONDS:
        return None
    return delta


def _legacy_rate_threshold(value_per_30fps_frame: float) -> float:
    return value_per_30fps_frame * _REFERENCE_FPS


def _ankle_displacement_from_setup(
    frames: Sequence[PoseFrame],
    measurement_space: SwingMeasurementSpace,
    *,
    setup_position: int = 0,
    lead_side: BodySide | None = None,
) -> tuple[float, ...]:
    setup = frames[setup_position]
    values: list[float] = []
    for frame in frames:
        frame_values: list[float] = []
        scale = torso_length(
            setup,
            min_confidence=0.1,
            measurement_space=measurement_space,
        ) or torso_length(
            frame,
            min_confidence=0.1,
            measurement_space=measurement_space,
        )
        scale = scale or 0.25
        sides = (lead_side,) if lead_side is not None else (BodySide.LEFT, BodySide.RIGHT)
        for side in sides:
            name = side_keypoint(side, "ankle")
            setup_point = setup.get(name, min_confidence=0.1)
            frame_point = frame.get(name, min_confidence=0.1)
            if setup_point is None or frame_point is None:
                continue
            frame_values.append(
                measurement_space.horizontal_distance(frame_point.point, setup_point.point)
                / max(scale, 0.01)
            )
        values.append(max(frame_values, default=0.0))
    return tuple(values)


def _lead_ankle_side_from_stride(
    frames: Sequence[PoseFrame],
    *,
    setup_position: int,
    stride_position: int,
    impact_position: int,
    measurement_space: SwingMeasurementSpace,
) -> BodySide | None:
    setup = frames[setup_position]
    search_positions = range(stride_position + 1, max(stride_position + 2, impact_position))
    scores: dict[BodySide, float] = {}
    for side in (BodySide.LEFT, BodySide.RIGHT):
        setup_point = setup.get(side_keypoint(side, "ankle"), min_confidence=0.1)
        if setup_point is None:
            continue
        side_scores: list[float] = []
        for position in search_positions:
            if position >= len(frames):
                continue
            current_point = frames[position].get(side_keypoint(side, "ankle"), min_confidence=0.1)
            scale = (
                torso_length(setup, min_confidence=0.1, measurement_space=measurement_space)
                or torso_length(
                    frames[position],
                    min_confidence=0.1,
                    measurement_space=measurement_space,
                )
                or 0.25
            )
            if current_point is None:
                continue
            side_scores.append(
                measurement_space.horizontal_distance(current_point.point, setup_point.point)
                / max(scale, 0.01)
            )
        scores[side] = max(side_scores, default=0.0)
    if not scores or max(scores.values()) <= 0.0:
        return None
    return max(scores, key=lambda side: scores[side])


def _max_ankle_displacement(
    setup: PoseFrame,
    current: PoseFrame,
    scale: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    values: list[float] = []
    for side in (BodySide.LEFT, BodySide.RIGHT):
        setup_point = setup.get(side_keypoint(side, "ankle"), min_confidence=0.1)
        current_point = current.get(side_keypoint(side, "ankle"), min_confidence=0.1)
        if setup_point is None or current_point is None:
            continue
        values.append(
            measurement_space.horizontal_distance(setup_point.point, current_point.point)
            / max(scale, 0.01)
        )
    return max(values, default=0.0)


def _max_knee_displacement(
    setup: PoseFrame,
    current: PoseFrame,
    scale: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    values: list[float] = []
    for side in (BodySide.LEFT, BodySide.RIGHT):
        setup_point = setup.get(side_keypoint(side, "knee"), min_confidence=0.1)
        current_point = current.get(side_keypoint(side, "knee"), min_confidence=0.1)
        if setup_point is None or current_point is None:
            continue
        values.append(
            measurement_space.horizontal_distance(setup_point.point, current_point.point)
            / max(scale, 0.01)
        )
    return max(values, default=0.0)


def _hip_midpoint_displacement(
    setup: PoseFrame,
    current: PoseFrame,
    scale: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    setup_hip = _midpoint_keypoint(
        setup,
        PoseKeypointName.LEFT_HIP,
        PoseKeypointName.RIGHT_HIP,
        min_confidence=0.1,
    )
    current_hip = _midpoint_keypoint(
        current,
        PoseKeypointName.LEFT_HIP,
        PoseKeypointName.RIGHT_HIP,
        min_confidence=0.1,
    )
    if setup_hip is None or current_hip is None:
        return 0.0
    return measurement_space.distance(setup_hip.point, current_hip.point) / max(scale, 0.01)


def _head_displacement(
    setup: PoseFrame,
    current: PoseFrame,
    scale: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    setup_head = _head_keypoint(setup, 0.1)
    current_head = _head_keypoint(current, 0.1)
    if setup_head is None or current_head is None:
        return 0.0
    return measurement_space.distance(setup_head.point, current_head.point) / max(scale, 0.01)


def _grip_displacement(
    start: PoseFrame,
    current: PoseFrame,
    scale: float,
    measurement_space: SwingMeasurementSpace,
) -> float:
    start_grip = _grip_point(start, 0.1)
    current_grip = _grip_point(current, 0.1)
    if start_grip is None or current_grip is None:
        return 0.0
    return measurement_space.distance(start_grip.point, current_grip.point) / max(scale, 0.01)


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


def _ordering_repair_reasons(
    raw_positions: tuple[int, int, int, int, int],
    repaired_positions: tuple[int, int, int, int, int],
) -> tuple[SwingPhase, ...]:
    phases = tuple(SwingPhase)
    return tuple(
        phase
        for phase, raw_position, repaired_position in zip(
            phases,
            raw_positions,
            repaired_positions,
            strict=True,
        )
        if raw_position != repaired_position
    )


def _normalized_stance_width(
    frame: PoseFrame,
    min_confidence: float,
    base_limitations: tuple[str, ...],
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    left_ankle = frame.get(PoseKeypointName.LEFT_ANKLE, min_confidence=min_confidence)
    right_ankle = frame.get(PoseKeypointName.RIGHT_ANKLE, min_confidence=min_confidence)
    scale = torso_length(
        frame,
        min_confidence=min_confidence,
        measurement_space=measurement_space,
    )
    if left_ankle is None or right_ankle is None or scale is None:
        return _missing_metric(
            SwingMetricName.NORMALIZED_STANCE_WIDTH,
            "Required ankle or torso scale keypoints were missing.",
            (frame.frame_index,),
        )
    return SwingMetricValue(
        name=SwingMetricName.NORMALIZED_STANCE_WIDTH,
        value=measurement_space.horizontal_distance(left_ankle.point, right_ankle.point) / scale,
        confidence=min(left_ankle.confidence, right_ankle.confidence),
        evidence_frames=(frame.frame_index,),
        limitations=base_limitations,
    )


def _torso_forward_tilt(
    frame: PoseFrame,
    min_confidence: float,
    base_limitations: tuple[str, ...],
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    torso = _torso_vector(frame, min_confidence)
    if torso is None:
        return _missing_metric(
            SwingMetricName.TORSO_FORWARD_TILT,
            "Required torso keypoints were missing.",
            (frame.frame_index,),
        )
    angle = measurement_space.vector_angle_degrees(torso[0].point, torso[1].point)
    tilt = angle_difference_degrees(angle, -90.0)
    return SwingMetricValue(
        name=SwingMetricName.TORSO_FORWARD_TILT,
        value=tilt,
        confidence=min(torso[0].confidence, torso[1].confidence),
        evidence_frames=(frame.frame_index,),
        limitations=base_limitations,
    )


def _torso_tilt_preservation(
    setup: PoseFrame,
    impact: PoseFrame,
    min_confidence: float,
    base_limitations: tuple[str, ...],
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    setup_tilt = _torso_forward_tilt(setup, min_confidence, (), measurement_space)
    impact_tilt = _torso_forward_tilt(impact, min_confidence, (), measurement_space)
    if setup_tilt.value is None or impact_tilt.value is None:
        return _missing_metric(
            SwingMetricName.TORSO_TILT_PRESERVATION,
            "Required torso keypoints were missing at setup or impact.",
            (setup.frame_index, impact.frame_index),
        )
    return SwingMetricValue(
        name=SwingMetricName.TORSO_TILT_PRESERVATION,
        value=abs(impact_tilt.value - setup_tilt.value),
        confidence=min(setup_tilt.confidence, impact_tilt.confidence),
        evidence_frames=(setup.frame_index, impact.frame_index),
        limitations=base_limitations,
    )


def _grip_loading_vector(
    frame: PoseFrame,
    sides: NormalizedBodySides,
    min_confidence: float,
    base_limitations: tuple[str, ...],
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    grip = _grip_point(frame, min_confidence)
    rear_ankle = frame.get(side_keypoint(sides.rear, "ankle"), min_confidence=min_confidence)
    rear_heel = frame.get(side_keypoint(sides.rear, "heel"), min_confidence=min_confidence)
    rear_foot = frame.get(
        side_keypoint(sides.rear, "foot_index"),
        min_confidence=min_confidence,
    )
    rear_shoulder = frame.get(
        side_keypoint(sides.rear, "shoulder"),
        min_confidence=min_confidence,
    )
    head = _head_keypoint(frame, min_confidence)
    scale = torso_length(
        frame,
        min_confidence=min_confidence,
        measurement_space=measurement_space,
    )
    if grip is None or rear_ankle is None or rear_shoulder is None or head is None or scale is None:
        return _missing_metric(
            SwingMetricName.GRIP_LOADING_VECTOR,
            "Required grip, rear foot, shoulder, head, or torso scale keypoints were missing.",
            (frame.frame_index,),
        )

    support_points = [measurement_space.point(rear_ankle.point)]
    if rear_heel is not None:
        support_points.append(measurement_space.point(rear_heel.point))
    if rear_foot is not None:
        support_points.append(measurement_space.point(rear_foot.point))
    support_min_x = min(point.x for point in support_points)
    support_max_x = max(point.x for point in support_points)
    grip_point = measurement_space.point(grip.point)
    head_point = measurement_space.point(head.point)
    rear_shoulder_point = measurement_space.point(rear_shoulder.point)
    horizontal_excess = max(0.0, support_min_x - grip_point.x, grip_point.x - support_max_x)
    high_y = min(head_point.y, rear_shoulder_point.y)
    low_y = max(head_point.y, rear_shoulder_point.y)
    vertical_excess = max(0.0, high_y - grip_point.y, grip_point.y - low_y)
    return SwingMetricValue(
        name=SwingMetricName.GRIP_LOADING_VECTOR,
        value=max(horizontal_excess, vertical_excess) / scale,
        confidence=min(
            grip.confidence,
            rear_ankle.confidence,
            rear_shoulder.confidence,
            head.confidence,
        ),
        evidence_frames=(frame.frame_index,),
        limitations=base_limitations,
    )


def _rear_knee_sway(
    setup: PoseFrame,
    stride: PoseFrame,
    sides: NormalizedBodySides,
    min_confidence: float,
    base_limitations: tuple[str, ...],
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    setup_rear_ankle = setup.get(
        side_keypoint(sides.rear, "ankle"),
        min_confidence=min_confidence,
    )
    stride_rear_knee = stride.get(
        side_keypoint(sides.rear, "knee"),
        min_confidence=min_confidence,
    )
    scale = torso_length(
        setup,
        min_confidence=min_confidence,
        measurement_space=measurement_space,
    )
    if setup_rear_ankle is None or stride_rear_knee is None or scale is None:
        return _missing_metric(
            SwingMetricName.REAR_KNEE_SWAY,
            "Required rear knee, rear ankle, or torso scale keypoints were missing.",
            (setup.frame_index, stride.frame_index),
        )
    lead_ankle = setup.get(side_keypoint(sides.lead, "ankle"), min_confidence=min_confidence)
    forward_sign = (
        1.0 if lead_ankle is not None and lead_ankle.point.x >= setup_rear_ankle.point.x else -1.0
    )
    outward_distance = -forward_sign * measurement_space.horizontal_delta(
        setup_rear_ankle.point,
        stride_rear_knee.point,
    )
    return SwingMetricValue(
        name=SwingMetricName.REAR_KNEE_SWAY,
        value=max(0.0, outward_distance / scale),
        confidence=min(setup_rear_ankle.confidence, stride_rear_knee.confidence),
        evidence_frames=(setup.frame_index, stride.frame_index),
        limitations=base_limitations,
    )


def _early_connection_angle(
    frame: PoseFrame,
    sides: NormalizedBodySides,
    min_confidence: float,
    base_limitations: tuple[str, ...],
    measurement_space: SwingMeasurementSpace,
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
        value = measurement_space.angle_between_vectors_degrees(
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
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    foot_angle = _side_knee_angle(foot_strike, sides.lead, min_confidence, measurement_space)
    impact_angle = _side_knee_angle(impact, sides.lead, min_confidence, measurement_space)
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
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    setup_head = _head_keypoint(setup, min_confidence)
    impact_head = _head_keypoint(impact, min_confidence)
    scale = torso_length(
        setup,
        min_confidence=min_confidence,
        measurement_space=measurement_space,
    )
    if setup_head is None or impact_head is None or scale is None:
        return _missing_metric(
            SwingMetricName.HEAD_TRANSLATION_RATIO,
            "Required head or torso scale keypoints were missing.",
            (setup.frame_index, impact.frame_index),
        )
    return SwingMetricValue(
        name=SwingMetricName.HEAD_TRANSLATION_RATIO,
        value=measurement_space.horizontal_distance(impact_head.point, setup_head.point) / scale,
        confidence=min(setup_head.confidence, impact_head.confidence),
        evidence_frames=(setup.frame_index, impact.frame_index),
    )


def _estimated_attack_angle(
    frames: Sequence[PoseFrame],
    phases: SwingPhaseFrames,
    min_confidence: float,
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    frame_by_index = {frame.frame_index: frame for frame in frames}
    impact = frame_by_index[phases.impact]
    grip = _grip_point(impact, min_confidence)
    bat = impact.get(PoseKeypointName.BAT_TIP, min_confidence=min_confidence) or impact.get(
        PoseKeypointName.BAT_BARREL,
        min_confidence=min_confidence,
    )
    if grip is not None and bat is not None:
        angle = -measurement_space.vector_angle_degrees(grip.point, bat.point)
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
    angle = -measurement_space.vector_angle_degrees(grip_start.point, grip_end.point)
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
    measurement_space: SwingMeasurementSpace,
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
        hip_angles.append(
            (index, measurement_space.vector_angle_degrees(hips[0].point, hips[1].point))
        )
        shoulder_angles.append(
            (index, measurement_space.vector_angle_degrees(shoulders[0].point, shoulders[1].point))
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
        value=_timing_difference_milliseconds(frames[hip_onset], frames[shoulder_onset]),
        confidence=min(confidences),
        evidence_frames=(frames[hip_onset].frame_index, frames[shoulder_onset].frame_index),
    )


def _follow_through_posture_balance(
    impact: PoseFrame,
    follow_through: PoseFrame,
    min_confidence: float,
    measurement_space: SwingMeasurementSpace,
) -> SwingMetricValue:
    impact_tilt = _torso_forward_tilt(impact, min_confidence, (), measurement_space)
    follow_tilt = _torso_forward_tilt(follow_through, min_confidence, (), measurement_space)
    impact_head = _head_keypoint(impact, min_confidence)
    follow_head = _head_keypoint(follow_through, min_confidence)
    scale = torso_length(
        impact,
        min_confidence=min_confidence,
        measurement_space=measurement_space,
    )
    if (
        impact_tilt.value is None
        or follow_tilt.value is None
        or impact_head is None
        or follow_head is None
        or scale is None
    ):
        return _missing_metric(
            SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE,
            "Required torso, head, or torso scale keypoints were missing.",
            (impact.frame_index, follow_through.frame_index),
        )
    tilt_change = abs(follow_tilt.value - impact_tilt.value)
    head_drift = measurement_space.horizontal_distance(follow_head.point, impact_head.point) / scale
    return SwingMetricValue(
        name=SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE,
        value=tilt_change + (head_drift * 20.0),
        confidence=min(
            impact_tilt.confidence,
            follow_tilt.confidence,
            impact_head.confidence,
            follow_head.confidence,
        ),
        evidence_frames=(impact.frame_index, follow_through.frame_index),
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
    measurement_space: SwingMeasurementSpace,
) -> tuple[float, float] | None:
    hip = frame.get(side_keypoint(side, "hip"), min_confidence=min_confidence)
    knee = frame.get(side_keypoint(side, "knee"), min_confidence=min_confidence)
    ankle = frame.get(side_keypoint(side, "ankle"), min_confidence=min_confidence)
    if hip is None or knee is None or ankle is None:
        return None
    return measurement_space.joint_angle_degrees(hip.point, knee.point, ankle.point), min(
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


def _timing_difference_milliseconds(first: PoseFrame, second: PoseFrame) -> float:
    if first.timestamp_seconds is None or second.timestamp_seconds is None:
        return (second.frame_index - first.frame_index) / _REFERENCE_FPS * 1000.0
    return (second.timestamp_seconds - first.timestamp_seconds) * 1000.0
