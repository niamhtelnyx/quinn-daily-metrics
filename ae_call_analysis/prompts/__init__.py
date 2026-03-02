"""
Analysis Prompts Package
========================

This package contains structured prompts and schemas for analyzing AE calls
across multiple dimensions including Quinn qualification scoring.
"""

from .analysis_prompts import (
    # Schemas
    TalkingPointsAnalysis,
    TelnyxProductsAnalysis,
    UseCasesAnalysis,
    ConversationFocusAnalysis,
    SentimentAnalysis,
    NextStepsAnalysis,
    ConfidenceAnalysis,
    QuinnScoring,
    ComprehensiveAnalysis,
    
    # Enums
    ConversationFocus,
    NextStepsCategory,
    
    # Prompt builders
    build_comprehensive_analysis_prompt,
    build_talking_points_prompt,
    build_products_prompt,
    build_use_cases_prompt,
    build_conversation_focus_prompt,
    build_sentiment_prompt,
    build_next_steps_prompt,
    build_confidence_prompt,
    build_quinn_scoring_prompt,
)

__all__ = [
    # Schemas
    "TalkingPointsAnalysis",
    "TelnyxProductsAnalysis", 
    "UseCasesAnalysis",
    "ConversationFocusAnalysis",
    "SentimentAnalysis",
    "NextStepsAnalysis",
    "ConfidenceAnalysis",
    "QuinnScoring",
    "ComprehensiveAnalysis",
    
    # Enums
    "ConversationFocus",
    "NextStepsCategory",
    
    # Prompt builders
    "build_comprehensive_analysis_prompt",
    "build_talking_points_prompt",
    "build_products_prompt",
    "build_use_cases_prompt",
    "build_conversation_focus_prompt",
    "build_sentiment_prompt",
    "build_next_steps_prompt",
    "build_confidence_prompt",
    "build_quinn_scoring_prompt",
]