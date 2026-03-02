"""
Models module for AE Call Analysis System
Contains Pydantic schemas for data validation and structured analysis output
"""

from .analysis_schema import (
    CallAnalysisResult,
    TelnyxProduct, 
    ConversationFocusCategory,
    NextStepsCategory,
    SentimentScore,
    ConversationFocus,
    NextStepsAnalysis,
    QuinnAnalysis,
    QuinnInsight,
    AnalysisMetadata,
    validate_analysis_result,
    create_fallback_analysis
)

__all__ = [
    'CallAnalysisResult',
    'TelnyxProduct', 
    'ConversationFocusCategory',
    'NextStepsCategory', 
    'SentimentScore',
    'ConversationFocus',
    'NextStepsAnalysis',
    'QuinnAnalysis',
    'QuinnInsight',
    'AnalysisMetadata',
    'validate_analysis_result',
    'create_fallback_analysis'
]