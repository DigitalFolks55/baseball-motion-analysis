"""Scoring, rule evaluation, and issue detection boundaries."""

from baseball_motion_analysis.analysis.swing import (
    SwingAnalysisConfig,
    SwingAnalysisResult,
    SwingFaultResult,
    SwingFaultType,
    SwingMetricResult,
    SwingPhaseScore,
    SwingSeverity,
    analyze_swing,
)

__all__ = [
    "SwingAnalysisConfig",
    "SwingAnalysisResult",
    "SwingFaultResult",
    "SwingFaultType",
    "SwingMetricResult",
    "SwingPhaseScore",
    "SwingSeverity",
    "analyze_swing",
]
