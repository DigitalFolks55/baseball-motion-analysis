import math

import pytest

from baseball_motion_analysis.motion import (
    BodySide,
    SwingEventDetectionConfig,
    SwingEventStatus,
    SwingHandedness,
    SwingImpactDetectionPolicy,
    SwingMetricName,
    SwingPhase,
    angle_between_vectors_degrees,
    angle_difference_degrees,
    calculate_swing_metrics,
    detect_swing_phases,
    joint_angle_degrees,
    resolve_body_sides,
)
from baseball_motion_analysis.pose import Point2D, PoseFrame, PoseKeypoint, PoseKeypointName
from unit.swing_test_helpers import GOOD_PHASES, aspect_sensitive_swing_frames, good_swing_frames


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
    assert phases.detection_method_for(SwingPhase.IMPACT) == "estimated_body_motion_contact_window"
    assert phases.confidence_for(SwingPhase.IMPACT) == pytest.approx(phases.confidence)
    assert any("estimated impact window" in limitation for limitation in phases.limitations)
    assert phases.frame_quality is not None
    assert phases.active_window is not None


def test_detect_swing_phases_exposes_impact_policy_statuses() -> None:
    frames = good_swing_frames()

    estimated = detect_swing_phases(frames)
    skipped = detect_swing_phases(
        frames,
        event_config=SwingEventDetectionConfig(
            impact_detection_policy=SwingImpactDetectionPolicy.SKIP_WITHOUT_BALL,
        ),
    )
    unavailable = detect_swing_phases(
        frames,
        event_config=SwingEventDetectionConfig(
            impact_detection_policy=SwingImpactDetectionPolicy.REQUIRE_BALL_CONTACT,
        ),
    )

    assert estimated.status_for(SwingPhase.IMPACT) == SwingEventStatus.ESTIMATED
    assert skipped.status_for(SwingPhase.IMPACT) == SwingEventStatus.SKIPPED
    assert skipped.confidence_for(SwingPhase.IMPACT) == pytest.approx(0.0)
    assert skipped.detection_method_for(SwingPhase.IMPACT) == "impact_skipped_without_ball"
    assert "skipped" in (skipped.fallback_reason_for(SwingPhase.IMPACT) or "").lower()
    assert unavailable.status_for(SwingPhase.IMPACT) == SwingEventStatus.UNAVAILABLE
    assert unavailable.confidence_for(SwingPhase.IMPACT) == pytest.approx(0.0)
    assert (
        unavailable.detection_method_for(SwingPhase.IMPACT) == "ball_contact_required_unavailable"
    )


def test_detect_swing_phases_ignores_weak_frames_and_detects_active_window() -> None:
    base = good_swing_frames()
    idle_start = tuple(
        _copy_frame(frame, frame.frame_index) for frame in [base[0], base[0], base[0]]
    )
    swing = tuple(_copy_frame(frame, index + 3) for index, frame in enumerate(base))
    idle_end = tuple(_copy_frame(base[-1], index + 8) for index in range(3))
    weak = PoseFrame(frame_index=5, timestamp_seconds=5 / 30.0, keypoints={})
    frames = idle_start + swing[:2] + (weak,) + swing[3:] + idle_end

    phases = detect_swing_phases(frames)

    assert phases.frame_quality is not None
    assert phases.frame_quality.rejected_frame_indexes == (5,)
    assert phases.active_window is not None
    assert phases.active_window.start_frame_index > 0
    assert phases.active_window.end_frame_index < frames[-1].frame_index
    assert phases.setup < phases.active_window.start_frame_index
    assert phases.foot_strike != 5
    assert phases.impact != 5
    assert any("weak pose frame" in limitation for limitation in phases.limitations)


def test_detect_swing_phases_uses_constraints_beyond_early_wrist_velocity_for_impact() -> None:
    frames = _early_wrist_spike_then_real_impact_frames()

    phases = detect_swing_phases(frames)

    assert phases.impact == 4
    assert phases.detection_method_for(SwingPhase.IMPACT) == "estimated_body_motion_contact_window"


def test_detect_swing_phases_does_not_treat_wrist_waggle_as_stride() -> None:
    frames = _wrist_waggle_before_lower_body_stride_frames()

    phases = detect_swing_phases(frames)

    assert phases.stride >= 2
    assert phases.stride - phases.setup >= 2
    assert phases.detection_method_for(SwingPhase.STRIDE) in {
        "lead_leg_lift_peak",
        "lower_body_load_no_leg_lift_fallback",
    }


def test_detect_swing_phases_uses_lead_leg_lift_peak_for_stride() -> None:
    frames = _leg_lift_stride_then_plant_frames()

    phases = detect_swing_phases(
        frames, event_config=SwingEventDetectionConfig(handedness=SwingHandedness.RIGHT_HANDED)
    )

    assert phases.stride == 3
    assert phases.detection_method_for(SwingPhase.STRIDE) == "lead_leg_lift_peak"
    assert phases.fallback_reason_for(SwingPhase.STRIDE) is None


def test_detect_swing_phases_marks_no_lift_stride_as_lower_confidence_fallback() -> None:
    frames = _lead_foot_plant_then_late_slide_frames()

    phases = detect_swing_phases(frames)

    assert phases.detection_method_for(SwingPhase.STRIDE) == "lower_body_load_no_leg_lift_fallback"
    assert "no sustained lead-leg lift" in (phases.fallback_reason_for(SwingPhase.STRIDE) or "")
    assert phases.confidence_for(SwingPhase.STRIDE) < phases.confidence
    assert phases.confidence_for(SwingPhase.STRIDE) > 0.65


def test_detect_swing_phases_uses_setup_baseline_and_plant_for_foot_strike() -> None:
    frames = _lead_foot_plant_then_late_slide_frames()

    phases = detect_swing_phases(frames)

    assert phases.setup == 0
    assert phases.foot_strike == 3
    assert phases.impact > phases.foot_strike
    assert phases.detection_method_for(SwingPhase.FOOT_STRIKE) == "lead_foot_plant_window"


def test_detect_swing_phases_selects_foot_strike_after_prior_leg_lift() -> None:
    frames = _leg_lift_stride_then_plant_frames()

    phases = detect_swing_phases(
        frames, event_config=SwingEventDetectionConfig(handedness=SwingHandedness.RIGHT_HANDED)
    )

    assert phases.stride == 3
    assert phases.foot_strike == 5
    assert phases.foot_strike > phases.stride
    assert phases.fallback_reason_for(SwingPhase.FOOT_STRIKE) is None


def test_detect_swing_phases_downgrades_foot_strike_without_prior_leg_lift() -> None:
    frames = _lead_foot_plant_then_late_slide_frames()

    phases = detect_swing_phases(frames)

    assert phases.foot_strike > phases.stride
    assert "no prior lead-leg lift" in (phases.fallback_reason_for(SwingPhase.FOOT_STRIKE) or "")
    assert phases.confidence_for(SwingPhase.FOOT_STRIKE) < phases.confidence


def test_detect_swing_phases_selects_semantic_follow_through_after_impact() -> None:
    frames = _delayed_extension_follow_through_frames()

    phases = detect_swing_phases(frames)

    assert phases.impact == 4
    assert phases.follow_through > phases.impact + 1
    assert phases.detection_method_for(SwingPhase.FOLLOW_THROUGH) == "post_impact_extension_window"


def test_detect_swing_phases_follow_through_ignores_idle_reset_frames() -> None:
    frames = _follow_through_then_idle_reset_frames()

    phases = detect_swing_phases(frames)

    assert phases.follow_through < frames[-1].frame_index
    assert phases.follow_through <= 8


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

    assert metrics[SwingMetricName.NORMALIZED_STANCE_WIDTH].value == pytest.approx(1.2, abs=0.01)
    assert metrics[SwingMetricName.TORSO_FORWARD_TILT].value == pytest.approx(25.02, abs=0.1)
    assert metrics[SwingMetricName.TORSO_TILT_PRESERVATION].value == pytest.approx(1.07, abs=0.1)
    assert metrics[SwingMetricName.GRIP_LOADING_VECTOR].value == pytest.approx(0.0)
    assert metrics[SwingMetricName.REAR_KNEE_SWAY].value == pytest.approx(0.0)
    assert metrics[SwingMetricName.HEAD_TRANSLATION_RATIO].value == pytest.approx(0.0)
    assert metrics[SwingMetricName.EARLY_CONNECTION_ANGLE].value == pytest.approx(95.04, abs=0.1)
    assert metrics[SwingMetricName.LEAD_KNEE_BLOCKING_INDEX].value == pytest.approx(0.0)
    assert metrics[SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING].value == pytest.approx(1.0)
    assert metrics[SwingMetricName.ESTIMATED_ATTACK_ANGLE].value == pytest.approx(10.0, abs=0.1)
    assert metrics[SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE].value == pytest.approx(0.0)
    assert all(math.isfinite(metric.value or 0.0) for metric in metrics.values())


def test_calculate_swing_metrics_restores_non_contact_fallbacks_without_ball_contact() -> None:
    frames = good_swing_frames()
    phases = detect_swing_phases(
        frames,
        GOOD_PHASES,
        event_config=SwingEventDetectionConfig(
            impact_detection_policy=SwingImpactDetectionPolicy.SKIP_WITHOUT_BALL,
        ),
    )

    metrics = {
        metric.name: metric
        for metric in calculate_swing_metrics(frames, phases, SwingHandedness.RIGHT_HANDED)
    }

    for metric_name in {
        SwingMetricName.TORSO_TILT_PRESERVATION,
        SwingMetricName.LEAD_KNEE_BLOCKING_INDEX,
        SwingMetricName.ESTIMATED_ATTACK_ANGLE,
    }:
        metric = metrics[metric_name]
        assert metric.value is None
        assert metric.confidence == pytest.approx(0.0)
        assert any("Impact-dependent metric" in limitation for limitation in metric.limitations)

    head_translation = metrics[SwingMetricName.HEAD_TRANSLATION_RATIO]
    follow_through = metrics[SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE]

    assert head_translation.value is not None
    assert head_translation.confidence == pytest.approx(0.75)
    assert head_translation.evidence_frames == (0, 2)
    assert any(
        "no-ball fallback anchor" in limitation for limitation in head_translation.limitations
    )
    assert follow_through.value is not None
    assert follow_through.confidence == pytest.approx(0.75)
    assert follow_through.evidence_frames == (2, 4)
    assert any("no-ball fallback anchor" in limitation for limitation in follow_through.limitations)


def test_calculate_swing_metrics_uses_aspect_aware_geometry_for_non_square_frames() -> None:
    frames = aspect_sensitive_swing_frames()

    aspect_metrics = {
        metric.name: metric
        for metric in calculate_swing_metrics(
            frames,
            detect_swing_phases(frames, GOOD_PHASES),
            SwingHandedness.RIGHT_HANDED,
            frame_width=1920,
            frame_height=1080,
        )
    }
    raw_fallback_metrics = {
        metric.name: metric
        for metric in calculate_swing_metrics(
            frames,
            detect_swing_phases(frames, GOOD_PHASES),
            SwingHandedness.RIGHT_HANDED,
        )
    }

    assert aspect_metrics[SwingMetricName.NORMALIZED_STANCE_WIDTH].value == pytest.approx(
        1.0264,
        abs=0.001,
    )
    assert raw_fallback_metrics[SwingMetricName.NORMALIZED_STANCE_WIDTH].value != pytest.approx(
        aspect_metrics[SwingMetricName.NORMALIZED_STANCE_WIDTH].value,
    )
    assert aspect_metrics[SwingMetricName.TORSO_FORWARD_TILT].value == pytest.approx(30.0)
    assert raw_fallback_metrics[SwingMetricName.TORSO_FORWARD_TILT].value != pytest.approx(30.0)
    assert aspect_metrics[SwingMetricName.HEAD_TRANSLATION_RATIO].value == pytest.approx(
        0.2566,
        abs=0.001,
    )
    assert raw_fallback_metrics[SwingMetricName.HEAD_TRANSLATION_RATIO].value != pytest.approx(
        aspect_metrics[SwingMetricName.HEAD_TRANSLATION_RATIO].value,
    )
    assert aspect_metrics[SwingMetricName.ESTIMATED_ATTACK_ANGLE].value == pytest.approx(10.0)
    assert raw_fallback_metrics[SwingMetricName.ESTIMATED_ATTACK_ANGLE].value != pytest.approx(
        10.0,
    )


def test_calculate_swing_metrics_requires_width_and_height_together() -> None:
    frames = aspect_sensitive_swing_frames()

    with pytest.raises(ValueError, match="frame_width and frame_height"):
        calculate_swing_metrics(
            frames,
            detect_swing_phases(frames, GOOD_PHASES),
            SwingHandedness.RIGHT_HANDED,
            frame_width=1920,
        )


def _copy_frame(frame: PoseFrame, frame_index: int) -> PoseFrame:
    return PoseFrame(
        frame_index=frame_index,
        timestamp_seconds=frame_index / 30.0,
        keypoints=frame.keypoints,
    )


def _early_wrist_spike_then_real_impact_frames() -> tuple[PoseFrame, ...]:
    frames: list[PoseFrame] = []
    for frame_index in range(7):
        wrist_x = 0.2
        shoulder_y = 0.4
        hip_y = 0.7
        if frame_index == 1:
            wrist_x = 1.2
        elif frame_index == 2:
            wrist_x = 0.25
        elif frame_index >= 4:
            wrist_x = 0.82 + (frame_index - 4) * 0.04
            shoulder_y = 0.3
            hip_y = 0.68
        keypoints = {
            PoseKeypointName.NOSE: PoseKeypoint(Point2D(0.5, 0.2)),
            PoseKeypointName.LEFT_SHOULDER: PoseKeypoint(Point2D(0.65, shoulder_y)),
            PoseKeypointName.RIGHT_SHOULDER: PoseKeypoint(Point2D(0.35, shoulder_y + 0.02)),
            PoseKeypointName.LEFT_WRIST: PoseKeypoint(Point2D(wrist_x, 0.5)),
            PoseKeypointName.RIGHT_WRIST: PoseKeypoint(Point2D(wrist_x - 0.1, 0.52)),
            PoseKeypointName.LEFT_HIP: PoseKeypoint(Point2D(0.62, hip_y)),
            PoseKeypointName.RIGHT_HIP: PoseKeypoint(Point2D(0.38, hip_y + 0.02)),
            PoseKeypointName.LEFT_KNEE: PoseKeypoint(Point2D(0.62, 0.82)),
            PoseKeypointName.RIGHT_KNEE: PoseKeypoint(Point2D(0.38, 0.82)),
            PoseKeypointName.LEFT_ANKLE: PoseKeypoint(Point2D(0.65, 0.96)),
            PoseKeypointName.RIGHT_ANKLE: PoseKeypoint(Point2D(0.35, 0.96)),
        }
        frames.append(PoseFrame(frame_index=frame_index, keypoints=keypoints))
    return tuple(frames)


def _wrist_waggle_before_lower_body_stride_frames() -> tuple[PoseFrame, ...]:
    frames: list[PoseFrame] = []
    for frame_index in range(7):
        left_ankle_x = 0.65
        left_knee_x = 0.64
        hip_x = 0.5
        wrist_x = 0.25
        if frame_index == 1:
            wrist_x = 0.75
        elif frame_index >= 2:
            left_ankle_x = 0.70 + min(frame_index - 2, 2) * 0.03
            left_knee_x = 0.69 + min(frame_index - 2, 2) * 0.02
            hip_x = 0.51 + min(frame_index - 2, 2) * 0.015
        if frame_index >= 4:
            wrist_x = 0.95 + (frame_index - 4) * 0.12
        frames.append(
            _phase_test_frame(
                frame_index,
                left_ankle_x=left_ankle_x,
                left_knee_x=left_knee_x,
                hip_mid_x=hip_x,
                grip_x=wrist_x,
            )
        )
    return tuple(frames)


def _lead_foot_plant_then_late_slide_frames() -> tuple[PoseFrame, ...]:
    frames: list[PoseFrame] = []
    for frame_index in range(7):
        left_ankle_x = 0.65
        left_knee_x = 0.64
        grip_x = 0.25
        shoulder_tilt = 0.0
        if frame_index == 1:
            left_ankle_x = 0.68
            left_knee_x = 0.66
        elif frame_index == 2:
            left_ankle_x = 0.76
            left_knee_x = 0.70
        elif frame_index == 3:
            left_ankle_x = 0.82
            left_knee_x = 0.72
        elif frame_index >= 4:
            left_ankle_x = 0.90
            left_knee_x = 0.73
        if frame_index >= 4:
            grip_x = 0.95 + (frame_index - 4) * 0.10
            shoulder_tilt = -0.05
        frames.append(
            _phase_test_frame(
                frame_index,
                left_ankle_x=left_ankle_x,
                left_knee_x=left_knee_x,
                grip_x=grip_x,
                shoulder_tilt=shoulder_tilt,
            )
        )
    return tuple(frames)


def _delayed_extension_follow_through_frames() -> tuple[PoseFrame, ...]:
    frames: list[PoseFrame] = []
    for frame_index in range(8):
        progress = min(1.0, frame_index / 5)
        grip_x = 0.25 + progress * 0.95
        left_ankle_x = 0.65 + min(frame_index, 3) * 0.03
        if frame_index >= 6:
            grip_x = 1.55
        frames.append(
            _phase_test_frame(
                frame_index,
                left_ankle_x=left_ankle_x,
                left_knee_x=0.64 + min(frame_index, 3) * 0.02,
                grip_x=grip_x,
                shoulder_tilt=-0.04 if frame_index >= 3 else 0.0,
            )
        )
    return tuple(frames)


def _leg_lift_stride_then_plant_frames() -> tuple[PoseFrame, ...]:
    frames: list[PoseFrame] = []
    for frame_index in range(9):
        left_ankle_x = 0.65
        left_ankle_y = 0.96
        left_knee_x = 0.64
        left_knee_y = 0.83
        grip_x = 0.25
        shoulder_tilt = 0.0
        if frame_index == 1:
            left_ankle_x = 0.67
        elif frame_index == 2:
            left_ankle_x = 0.69
            left_ankle_y = 0.90
            left_knee_x = 0.66
            left_knee_y = 0.80
        elif frame_index == 3:
            left_ankle_x = 0.71
            left_ankle_y = 0.84
            left_knee_x = 0.68
            left_knee_y = 0.78
        elif frame_index == 4:
            left_ankle_x = 0.75
            left_ankle_y = 0.90
            left_knee_x = 0.70
            left_knee_y = 0.80
        elif frame_index >= 5:
            left_ankle_x = 0.80
            left_ankle_y = 0.96
            left_knee_x = 0.72
            left_knee_y = 0.83
        if frame_index >= 6:
            grip_x = 0.88 + (frame_index - 6) * 0.10
            shoulder_tilt = -0.04
        frames.append(
            _phase_test_frame(
                frame_index,
                left_ankle_x=left_ankle_x,
                left_ankle_y=left_ankle_y,
                left_knee_x=left_knee_x,
                left_knee_y=left_knee_y,
                grip_x=grip_x,
                shoulder_tilt=shoulder_tilt,
            )
        )
    return tuple(frames)


def _follow_through_then_idle_reset_frames() -> tuple[PoseFrame, ...]:
    frames: list[PoseFrame] = []
    for frame_index in range(12):
        grip_x = 0.25 + min(frame_index, 7) * 0.14
        left_ankle_x = 0.65 + min(frame_index, 5) * 0.03
        left_ankle_y = 0.96
        left_knee_y = 0.83
        hip_mid_x = 0.5
        if frame_index in {2, 3}:
            left_ankle_y = 0.86 if frame_index == 3 else 0.90
            left_knee_y = 0.79
        if frame_index >= 8:
            hip_mid_x = 0.65 + (frame_index - 8) * 0.04
            grip_x = 1.35
        frames.append(
            _phase_test_frame(
                frame_index,
                left_ankle_x=left_ankle_x,
                left_ankle_y=left_ankle_y,
                left_knee_x=0.64 + min(frame_index, 5) * 0.02,
                left_knee_y=left_knee_y,
                grip_x=grip_x,
                hip_mid_x=hip_mid_x,
                shoulder_tilt=-0.04 if 4 <= frame_index <= 8 else 0.0,
            )
        )
    return tuple(frames)


def _phase_test_frame(
    frame_index: int,
    *,
    left_ankle_x: float,
    left_knee_x: float,
    grip_x: float,
    left_ankle_y: float = 0.96,
    left_knee_y: float = 0.83,
    hip_mid_x: float = 0.5,
    shoulder_tilt: float = 0.0,
) -> PoseFrame:
    left_wrist = Point2D(grip_x + 0.04, 0.48)
    right_wrist = Point2D(grip_x - 0.04, 0.50)
    return PoseFrame(
        frame_index=frame_index,
        timestamp_seconds=frame_index / 30.0,
        keypoints={
            PoseKeypointName.NOSE: PoseKeypoint(Point2D(0.5, 0.2)),
            PoseKeypointName.LEFT_SHOULDER: PoseKeypoint(Point2D(0.62, 0.40 + shoulder_tilt)),
            PoseKeypointName.RIGHT_SHOULDER: PoseKeypoint(Point2D(0.38, 0.40)),
            PoseKeypointName.LEFT_WRIST: PoseKeypoint(left_wrist),
            PoseKeypointName.RIGHT_WRIST: PoseKeypoint(right_wrist),
            PoseKeypointName.LEFT_HIP: PoseKeypoint(Point2D(hip_mid_x + 0.10, 0.68)),
            PoseKeypointName.RIGHT_HIP: PoseKeypoint(Point2D(hip_mid_x - 0.10, 0.68)),
            PoseKeypointName.LEFT_KNEE: PoseKeypoint(Point2D(left_knee_x, left_knee_y)),
            PoseKeypointName.RIGHT_KNEE: PoseKeypoint(Point2D(0.40, 0.83)),
            PoseKeypointName.LEFT_ANKLE: PoseKeypoint(Point2D(left_ankle_x, left_ankle_y)),
            PoseKeypointName.RIGHT_ANKLE: PoseKeypoint(Point2D(0.36, 0.96)),
        },
    )
