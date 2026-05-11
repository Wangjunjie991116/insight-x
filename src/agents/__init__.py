"""AI Agents for Insight-X."""

from .analysis_strategy import AnalysisStrategyAgent, AnalysisStrategyInput
from .base import AgentResult, BaseAgent
from .code_execution import CodeExecutionAgent, CodeExecutionInput
from .code_generation import CodeGenerationAgent, CodeGenerationInput
from .code_implementation import CodeImplementationAgent, CodeImplementationInput
from .code_optimization_analysis import CodeOptimizationAnalysisAgent, CodeOptimizationAnalysisInput
from .data_understanding import DataUnderstandingAgent
from .insight_generation import InsightGenerationAgent, InsightGenerationInput
from .tracking_strategy import TrackingStrategyAgent, TrackingStrategyInput

__all__ = [
    "BaseAgent",
    "AgentResult",
    # Agent 1: Data Understanding
    "DataUnderstandingAgent",
    # Agent 2: Analysis Strategy
    "AnalysisStrategyAgent",
    "AnalysisStrategyInput",
    # Agent 3: Code Generation
    "CodeGenerationAgent",
    "CodeGenerationInput",
    # Agent 4: Code Execution
    "CodeExecutionAgent",
    "CodeExecutionInput",
    # Agent 5: Insight Generation
    "InsightGenerationAgent",
    "InsightGenerationInput",
    # Agent 6-1: Code Optimization Analysis
    "CodeOptimizationAnalysisAgent",
    "CodeOptimizationAnalysisInput",
    # Agent 6-2: Tracking Strategy
    "TrackingStrategyAgent",
    "TrackingStrategyInput",
    # Agent 7: Code Implementation
    "CodeImplementationAgent",
    "CodeImplementationInput",
]
