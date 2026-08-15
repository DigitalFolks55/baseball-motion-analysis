from baseball_motion_analysis.motion import SwingPhase
from baseball_motion_analysis.pose import Point2D, PoseFrame, PoseKeypoint, PoseKeypointName

GOOD_PHASES = {
    SwingPhase.SETUP: 0,
    SwingPhase.STRIDE: 1,
    SwingPhase.FOOT_STRIKE: 2,
    SwingPhase.IMPACT: 3,
    SwingPhase.FOLLOW_THROUGH: 4,
}


def good_swing_frames(
    *,
    scenario: str | None = None,
    remove_keypoints: set[PoseKeypointName] | None = None,
) -> tuple[PoseFrame, ...]:
    """Return a deterministic right-handed side-view swing fixture."""
    remove_keypoints = remove_keypoints or set()
    frames: list[PoseFrame] = []
    for frame_index in range(5):
        left_hip_y = 0.75
        right_hip_y = 0.75
        left_shoulder_y = 0.0
        right_shoulder_y = 0.0
        nose_x = 0.35
        left_wrist = Point2D(0.10, -0.10)
        right_wrist = Point2D(0.00, -0.10)
        left_knee = Point2D(1.0, 1.25)
        bat_angle = 10.0

        if frame_index >= 1:
            left_hip_y = 0.58
        if frame_index >= 2:
            left_shoulder_y = -0.10
            left_wrist = Point2D(1.22, -0.15)
            right_wrist = Point2D(0.95, -0.05)
        if frame_index >= 3:
            left_wrist = Point2D(1.2, 0.15)
            right_wrist = Point2D(1.0, 0.15)

        if scenario == "door_swing" and frame_index == 2:
            left_wrist = Point2D(2.0, 2.0)
        if scenario == "forward_drift" and frame_index >= 3:
            nose_x = 1.0
        if scenario == "arms_only" and frame_index >= 1:
            left_shoulder_y = -0.10
        if scenario == "upper_swing" and frame_index == 3:
            bat_angle = 25.0
        if scenario == "collapsed_lead_side" and frame_index == 3:
            left_knee = Point2D(1.25, 1.45)

        grip = Point2D((left_wrist.x + right_wrist.x) / 2.0, (left_wrist.y + right_wrist.y) / 2.0)
        bat_tip = Point2D(grip.x + 1.0, grip.y - _tan_degrees(bat_angle))
        keypoints = {
            PoseKeypointName.NOSE: _kp(nose_x, -0.35),
            PoseKeypointName.LEFT_SHOULDER: _kp(1.35, left_shoulder_y),
            PoseKeypointName.RIGHT_SHOULDER: _kp(0.35, right_shoulder_y),
            PoseKeypointName.LEFT_ELBOW: _kp(0.8, 0.25),
            PoseKeypointName.RIGHT_ELBOW: _kp(0.2, 0.25),
            PoseKeypointName.LEFT_WRIST: PoseKeypoint(left_wrist),
            PoseKeypointName.RIGHT_WRIST: PoseKeypoint(right_wrist),
            PoseKeypointName.LEFT_HIP: _kp(1.0, left_hip_y),
            PoseKeypointName.RIGHT_HIP: _kp(0.0, right_hip_y),
            PoseKeypointName.LEFT_KNEE: PoseKeypoint(left_knee),
            PoseKeypointName.RIGHT_KNEE: _kp(0.0, 1.25),
            PoseKeypointName.LEFT_ANKLE: _kp(0.993, 2.0),
            PoseKeypointName.RIGHT_ANKLE: _kp(0.0, 2.0),
            PoseKeypointName.RIGHT_HEEL: _kp(0.0, 2.0),
            PoseKeypointName.RIGHT_FOOT_INDEX: _kp(0.18, 2.0),
            PoseKeypointName.BAT_TIP: PoseKeypoint(bat_tip),
        }
        for name in remove_keypoints:
            keypoints.pop(name, None)
        frames.append(
            PoseFrame(
                frame_index=frame_index,
                timestamp_seconds=frame_index / 30.0,
                keypoints=keypoints,
            )
        )
    return tuple(frames)


def aspect_sensitive_swing_frames() -> tuple[PoseFrame, ...]:
    """Return MediaPipe-style normalized points that require aspect-aware geometry."""
    frames: list[PoseFrame] = []
    shoulder_mid_x = 0.5 + (_tan_degrees(30.0) * 0.3 * 1080.0 / 1920.0)
    grip = Point2D(0.5, 0.5)
    bat_tip = Point2D(
        grip.x + (200.0 / 1920.0),
        grip.y - (_tan_degrees(10.0) * 200.0 / 1080.0),
    )
    for frame_index in range(5):
        nose_x = 0.5 if frame_index < 3 else 0.55
        keypoints = {
            PoseKeypointName.NOSE: _kp(nose_x, 0.3),
            PoseKeypointName.LEFT_SHOULDER: _kp(shoulder_mid_x + 0.04, 0.4),
            PoseKeypointName.RIGHT_SHOULDER: _kp(shoulder_mid_x - 0.04, 0.4),
            PoseKeypointName.LEFT_WRIST: _kp(grip.x + 0.01, grip.y),
            PoseKeypointName.RIGHT_WRIST: _kp(grip.x - 0.01, grip.y),
            PoseKeypointName.LEFT_HIP: _kp(0.54, 0.7),
            PoseKeypointName.RIGHT_HIP: _kp(0.46, 0.7),
            PoseKeypointName.LEFT_ANKLE: _kp(0.6, 0.9),
            PoseKeypointName.RIGHT_ANKLE: _kp(0.4, 0.9),
            PoseKeypointName.BAT_TIP: PoseKeypoint(bat_tip),
        }
        frames.append(
            PoseFrame(
                frame_index=frame_index,
                timestamp_seconds=frame_index / 30.0,
                keypoints=keypoints,
            )
        )
    return tuple(frames)


def _kp(x: float, y: float) -> PoseKeypoint:
    return PoseKeypoint(Point2D(x=x, y=y), confidence=1.0)


def _tan_degrees(degrees: float) -> float:
    import math

    return math.tan(math.radians(degrees))
