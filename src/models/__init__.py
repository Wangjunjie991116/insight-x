"""Data models for Insight-X."""

from .result import (
    AnalysisResult,
    DataDictionary,
    ExecutionResult,
    Insight,
    Strategy,
)
from .task import AnalysisTask, TaskStatus

__all__ = [
    "AnalysisTask",
    "TaskStatus",
    "DataDictionary",
    "ExecutionResult",
    "Insight",
    "Strategy",
    "AnalysisResult",
]
