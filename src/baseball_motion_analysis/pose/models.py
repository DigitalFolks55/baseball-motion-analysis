"""Stable pose observation models for motion analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class PoseKeypointName(StrEnum):
    """Canonical 2D keypoint names used by the analysis core."""

    NOSE = "nose"
    LEFT_EAR = "left_ear"
    RIGHT_EAR = "right_ear"
    LEFT_SHOULDER = "left_shoulder"
    RIGHT_SHOULDER = "right_shoulder"
    LEFT_ELBOW = "left_elbow"
    RIGHT_ELBOW = "right_elbow"
    LEFT_WRIST = "left_wrist"
    RIGHT_WRIST = "right_wrist"
    LEFT_HIP = "left_hip"
    RIGHT_HIP = "right_hip"
    LEFT_KNEE = "left_knee"
    RIGHT_KNEE = "right_knee"
    LEFT_ANKLE = "left_ankle"
    RIGHT_ANKLE = "right_ankle"
    LEFT_HEEL = "left_heel"
    RIGHT_HEEL = "right_heel"
    LEFT_FOOT_INDEX = "left_foot_index"
    RIGHT_FOOT_INDEX = "right_foot_index"
    BAT_TIP = "bat_tip"
    BAT_BARREL = "bat_barrel"


@dataclass(frozen=True)
class Point2D:
    """Normalized 2D coordinate."""

    x: float
    y: float


@dataclass(frozen=True)
class PoseKeypoint:
    """One detected keypoint and its confidence."""

    point: Point2D
    confidence: float = 1.0
    interpolated: bool = False
    smoothed: bool = False
    out_of_frame: bool = False


@dataclass(frozen=True)
class PoseFrame:
    """Pose observations for one sampled frame."""

    frame_index: int
    keypoints: Mapping[PoseKeypointName, PoseKeypoint]
    timestamp_seconds: float | None = None

    def get(
        self,
        name: PoseKeypointName,
        *,
        min_confidence: float = 0.0,
    ) -> PoseKeypoint | None:
        """Return a keypoint when present and above the minimum confidence."""
        keypoint = self.keypoints.get(name)
        if keypoint is None or keypoint.confidence < min_confidence:
            return None
        return keypoint
