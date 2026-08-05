from pathlib import Path

from fastapi.testclient import TestClient

from baseball_motion_analysis.app.main import create_app
from baseball_motion_analysis.core.config import AppSettings
from baseball_motion_analysis.pose import PoseFrame
from unit.swing_test_helpers import GOOD_PHASES, good_swing_frames


def test_swing_analysis_api_returns_analysis_and_feedback(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    response = client.post("/api/v1/analysis/swing", json=_good_swing_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["overall_score"] > 90.0
    assert payload["analysis"]["handedness"] == "right_handed"
    assert payload["analysis"]["phase_scores"]
    assert payload["analysis"]["metrics"]
    assert "setup" in payload["analysis"]["phases"]
    assert payload["feedback"]["summary"]
    assert payload["feedback"]["good_points"]
    assert payload["feedback"]["improvement_points"]
    assert payload["feedback"]["drills_or_suggestions"]
    assert payload["feedback"]["limitations"]
    assert str(tmp_path) not in response.text


def test_swing_analysis_api_rejects_invalid_handedness(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))
    payload = _good_swing_payload()
    payload["handedness"] = "switch"

    response = client.post("/api/v1/analysis/swing", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_swing_handedness"
    assert str(tmp_path) not in response.text


def test_swing_analysis_api_rejects_unknown_keypoint_name(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))
    payload = _good_swing_payload()
    payload["frames"][0]["keypoints"]["front_hand"] = {"x": 0.1, "y": 0.2, "confidence": 1.0}

    response = client.post("/api/v1/analysis/swing", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_pose_keypoint"
    assert str(tmp_path) not in response.text


def test_swing_analysis_api_rejects_empty_frame_list(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    response = client.post(
        "/api/v1/analysis/swing",
        json={"frames": [], "handedness": "right_handed"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_pose_frame_list"


def test_swing_analysis_api_rejects_invalid_phase_frame_index(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))
    payload = _good_swing_payload()
    payload["phase_frames"]["impact"] = 99

    response = client.post("/api/v1/analysis/swing", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_swing_analysis_request"


def test_swing_analysis_api_rejects_non_numeric_keypoint_values(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))
    payload = _good_swing_payload()
    payload["frames"][0]["keypoints"]["nose"]["x"] = "far"

    response = client.post("/api/v1/analysis/swing", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_swing_analysis_request"


def _create_test_app(tmp_path: Path) -> object:
    settings = AppSettings(
        media_root=tmp_path / "media",
        database_path=tmp_path / "library.sqlite3",
    )
    return create_app(settings=settings)


def _good_swing_payload() -> dict[str, object]:
    return {
        "frames": [_pose_frame_to_payload(frame) for frame in good_swing_frames()],
        "handedness": "right_handed",
        "phase_frames": {phase.value: frame_index for phase, frame_index in GOOD_PHASES.items()},
    }


def _pose_frame_to_payload(frame: PoseFrame) -> dict[str, object]:
    return {
        "frame_index": frame.frame_index,
        "timestamp_seconds": frame.timestamp_seconds,
        "keypoints": {
            name.value: {
                "x": keypoint.point.x,
                "y": keypoint.point.y,
                "confidence": keypoint.confidence,
            }
            for name, keypoint in frame.keypoints.items()
        },
    }
