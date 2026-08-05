from baseball_motion_analysis.analysis import SwingFaultType, analyze_swing
from baseball_motion_analysis.feedback import generate_swing_feedback
from baseball_motion_analysis.motion import SwingHandedness
from unit.swing_test_helpers import GOOD_PHASES, good_swing_frames


def test_generate_swing_feedback_maps_fault_to_cautious_text_and_drills() -> None:
    analysis = analyze_swing(
        good_swing_frames(scenario="door_swing"),
        handedness=SwingHandedness.RIGHT_HANDED,
        phase_frames=GOOD_PHASES,
    )

    report = generate_swing_feedback(analysis)

    assert "Based on the visible frames" in report.summary
    assert any("may be getting away" in point for point in report.improvement_points)
    assert "Cross-arm rotation drill" in report.drills_or_suggestions
    assert "Inside-out tee drill" in report.drills_or_suggestions
    assert any(
        fault.fault_type == SwingFaultType.DOOR_SWING_CASTING for fault in analysis.detected_faults
    )
