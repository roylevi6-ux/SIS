"""Pydantic response/request schemas for the SIS API.

All models are re-exported here for convenient imports:
    from sis.api.schemas import AccountSummary, TranscriptItem, ...
"""

from __future__ import annotations

from .accounts import (
    AccountCreate,
    AccountDetail,
    AccountSummary,
    AccountUpdate,
    AssessmentDetail,
    ForecastResponse,
    ForecastUpdate,
)
from .admin import (
    ActionLogItem,
    ActionSummary,
    CalibrationCreate,
    CalibrationHistoryItem,
    CoachingCreate,
    CoachingItem,
    CoachingSummary,
    CROMetric,
    FeedbackPattern,
    ForecastDataItem,
    IncorporationCheck,
    PromptVersionCreate,
    PromptVersionItem,
    RepScorecard,
    UsageSummary,
)
from .analyses import (
    AgentAnalysisResponse,
    AnalysisHistoryItem,
    AnalysisRequest,
    AnalysisRunResponse,
    AnalysisStatusResponse,
    RerunResponse,
    ResynthesizeResponse,
)
from .chat import ChatMessage, ChatResponse
from .dashboard import (
    DealTrendDataPoint,
    DealTrendItem,
    DivergenceItem,
    PipelineDeal,
    PipelineInsight,
    PipelineInsightsResponse,
    PipelineOverviewResponse,
    PipelineSummary,
    PortfolioSummary,
    TeamRollupItem,
    TeamTrendItem,
)
from .feedback import (
    FeedbackCreate,
    FeedbackItem,
    FeedbackResolve,
    FeedbackSummary,
)
from .transcripts import TranscriptItem, TranscriptResponse, TranscriptUpload

__all__ = [
    # accounts
    "AccountCreate",
    "AccountDetail",
    "AccountSummary",
    "AccountUpdate",
    "AssessmentDetail",
    "ForecastResponse",
    "ForecastUpdate",
    # admin
    "ActionLogItem",
    "ActionSummary",
    "CalibrationCreate",
    "CalibrationHistoryItem",
    "CoachingCreate",
    "CoachingItem",
    "CoachingSummary",
    "CROMetric",
    "FeedbackPattern",
    "ForecastDataItem",
    "IncorporationCheck",
    "PromptVersionCreate",
    "PromptVersionItem",
    "RepScorecard",
    "UsageSummary",
    # analyses
    "AgentAnalysisResponse",
    "AnalysisHistoryItem",
    "AnalysisRequest",
    "AnalysisRunResponse",
    "AnalysisStatusResponse",
    "RerunResponse",
    "ResynthesizeResponse",
    # chat
    "ChatMessage",
    "ChatResponse",
    # dashboard
    "DealTrendDataPoint",
    "DealTrendItem",
    "DivergenceItem",
    "PipelineDeal",
    "PipelineInsight",
    "PipelineInsightsResponse",
    "PipelineOverviewResponse",
    "PipelineSummary",
    "PortfolioSummary",
    "TeamRollupItem",
    "TeamTrendItem",
    # feedback
    "FeedbackCreate",
    "FeedbackItem",
    "FeedbackResolve",
    "FeedbackSummary",
    # transcripts
    "TranscriptItem",
    "TranscriptResponse",
    "TranscriptUpload",
]
