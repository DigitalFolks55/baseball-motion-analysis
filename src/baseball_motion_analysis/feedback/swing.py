"""User-facing swing feedback generation."""

from __future__ import annotations

from dataclasses import dataclass

from baseball_motion_analysis.analysis import (
    SwingAnalysisResult,
    SwingFaultResult,
    SwingFaultType,
    SwingSeverity,
)


@dataclass(frozen=True)
class SwingFeedbackReport:
    """Plain-language feedback report for one swing analysis."""

    summary: str
    good_points: tuple[str, ...]
    improvement_points: tuple[str, ...]
    drills_or_suggestions: tuple[str, ...]
    confidence: float
    limitations: tuple[str, ...]


def generate_swing_feedback(analysis: SwingAnalysisResult) -> SwingFeedbackReport:
    """Convert swing analysis into cautious user-facing feedback."""
    summary = (
        f"Based on the visible frames, this swing scored {analysis.overall_score:.1f}/100. "
        f"The result confidence is {analysis.confidence:.2f}."
    )
    good_points = analysis.good_points or (
        "No strong positive checkpoint was confirmed with high confidence in the visible frames.",
    )
    improvement_points = _improvement_points(analysis)
    drills = _drills(analysis.detected_faults)
    limitations = analysis.limitations or (
        "This is a 2D side-view rule-based evaluation and may miss 3D movement details.",
    )
    return SwingFeedbackReport(
        summary=summary,
        good_points=good_points,
        improvement_points=improvement_points,
        drills_or_suggestions=drills,
        confidence=analysis.confidence,
        limitations=limitations,
    )


def _improvement_points(analysis: SwingAnalysisResult) -> tuple[str, ...]:
    if analysis.detected_faults:
        return tuple(_fault_feedback(fault) for fault in analysis.detected_faults)

    weak_metrics = [
        metric
        for metric in analysis.metrics
        if metric.severity in {SwingSeverity.WARNING, SwingSeverity.SEVERE}
    ]
    if weak_metrics:
        return tuple(
            (
                f"{metric.name.value} may need attention. {metric.message} "
                f"Measured value: {metric.value}."
            )
            for metric in weak_metrics
        )
    return ("No major improvement point was detected from the available keypoints.",)


def _fault_feedback(fault: SwingFaultResult) -> str:
    messages = {
        SwingFaultType.DOOR_SWING_CASTING: (
            "Your hands may be getting away from your body early, which can create a "
            "wide swing path and later contact."
        ),
        SwingFaultType.FORWARD_AXIS_DRIFT_RUSHING: (
            "Your head or upper body may be moving forward early, which can make contact "
            "timing less stable."
        ),
        SwingFaultType.ARMS_ONLY_ONE_PIECE: (
            "Your hips and shoulders may be turning together, which can reduce the "
            "lower-body contribution to the swing."
        ),
        SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION: (
            "Your swing path may be getting too upward through contact, which can lead "
            "to undercut contact."
        ),
        SwingFaultType.COLLAPSED_LEAD_SIDE: (
            "Your front side may be soft at contact, which can let energy leak forward."
        ),
    }
    severity_text = "strongly" if fault.severity == SwingSeverity.SEVERE else "possibly"
    return f"{messages[fault.fault_type]} This was {severity_text} indicated by: {fault.evidence}"


def _drills(faults: tuple[SwingFaultResult, ...]) -> tuple[str, ...]:
    if not faults:
        return ("Keep using side-view video and compare the same checkpoints over time.",)
    drill_map = {
        SwingFaultType.DOOR_SWING_CASTING: (
            "Cross-arm rotation drill",
            "Inside-out tee drill",
        ),
        SwingFaultType.FORWARD_AXIS_DRIFT_RUSHING: (
            "5-second rear hip load hold drill",
            "Single-leg balance swing drill",
        ),
        SwingFaultType.ARMS_ONLY_ONE_PIECE: (
            "Chest-hugged bat swing drill",
            "Tee placement drill",
        ),
        SwingFaultType.EXCESSIVE_UPPER_SWING_EARLY_EXTENSION: (
            "High-grip freeze drill",
            "Hula-hoop swing-path drill",
        ),
        SwingFaultType.COLLAPSED_LEAD_SIDE: (
            "Firm lead-leg stop drill",
            "Single-leg swing drill",
        ),
    }
    drills: list[str] = []
    for fault in faults:
        drills.extend(drill_map[fault.fault_type])
    return tuple(dict.fromkeys(drills))
