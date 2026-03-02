"""
Pydantic models for structured LLM analysis output validation
Defines schemas matching PRD requirements (ANALYSIS-01 through ANALYSIS-09, QUINN-01 through QUINN-04)
"""

from typing import List, Dict, Optional, Literal, Any, Union
from pydantic import BaseModel, Field, validator, model_validator
from datetime import datetime
from enum import Enum

class TelnyxProduct(str, Enum):
    """Enumeration of Telnyx products for consistent identification"""
    VOICE = "voice"
    MESSAGING = "messaging" 
    WIRELESS = "wireless"
    VOICE_AI = "voice_ai"
    NUMBERS = "numbers"
    STORAGE = "storage"
    VERIFY = "verify"
    CONNECTIONS = "connections"

class ConversationFocusCategory(str, Enum):
    """Primary conversation focus categories"""
    PRODUCT_OVERVIEW = "product_overview"
    PRICING = "pricing"
    TECHNICAL = "technical"
    IMPLEMENTATION = "implementation"
    USE_CASES = "use_cases"
    COMPETITIVE = "competitive"
    TIMELINE = "timeline"
    DECISION_PROCESS = "decision_process"

class NextStepsCategory(str, Enum):
    """Next steps categories for follow-up classification"""
    MOVING_FORWARD = "moving_forward"
    SELF_SERVICE = "self_service"
    UNCLEAR = "unclear"
    NOT_INTERESTED = "not_interested"

class SentimentScore(BaseModel):
    """Sentiment scoring model (1-10 scale)"""
    excitement_level: int = Field(ge=1, le=10, description="Excitement/enthusiasm level")
    confidence_level: int = Field(ge=1, le=10, description="Confidence in the conversation")
    engagement_level: int = Field(ge=1, le=10, description="Level of active engagement")
    buying_signals: List[str] = Field(default_factory=list, max_items=5, description="Specific buying signals observed")
    concerns: List[str] = Field(default_factory=list, max_items=5, description="Concerns or objections raised")
    notes: Optional[str] = Field(max_length=500, description="Additional context or observations")

    @validator('buying_signals', 'concerns')
    def validate_signal_lists(cls, v):
        """Ensure signals and concerns are non-empty strings"""
        return [item.strip() for item in v if item and item.strip()]

class ConversationFocus(BaseModel):
    """Conversation focus analysis with time distribution"""
    primary: ConversationFocusCategory = Field(description="Primary conversation topic")
    secondary: List[ConversationFocusCategory] = Field(default_factory=list, max_items=3, description="Secondary topics discussed")
    time_distribution: Dict[str, int] = Field(description="Percentage time spent on each topic (must sum to 100)")
    
    @validator('time_distribution')
    def validate_time_distribution(cls, v):
        """Ensure time distribution sums to 100"""
        total = sum(v.values())
        if abs(total - 100) > 5:  # Allow 5% tolerance
            raise ValueError(f"Time distribution must sum to ~100%, got {total}%")
        return v

class NextStepsAnalysis(BaseModel):
    """Next steps analysis and probability assessment"""
    category: NextStepsCategory = Field(description="Overall next steps category")
    specific_actions: List[str] = Field(min_items=1, max_items=5, description="Specific action items identified")
    timeline: Optional[str] = Field(max_length=100, description="Expected timeline for next steps")
    probability: int = Field(ge=1, le=10, description="Probability of forward movement (1-10)")
    owner: Optional[str] = Field(max_length=100, description="Who is responsible for next steps")
    
    @validator('specific_actions')
    def validate_actions(cls, v):
        """Ensure actions are meaningful"""
        return [action.strip() for action in v if action and action.strip()]

class QuinnInsight(BaseModel):
    """Individual Quinn coaching insight"""
    area: str = Field(max_length=100, description="Area of focus (e.g., discovery, qualification)")
    observation: str = Field(max_length=300, description="Specific observation or insight")
    score: int = Field(ge=1, le=10, description="Performance score for this area")
    improvement_suggestion: Optional[str] = Field(max_length=200, description="Specific improvement suggestion")

class QuinnAnalysis(BaseModel):
    """Comprehensive Quinn qualification scoring and insights"""
    qualification_quality: int = Field(ge=1, le=10, description="Overall qualification effectiveness score")
    discovery_effectiveness: int = Field(ge=1, le=10, description="How well did AE uncover prospect needs")
    relationship_building: int = Field(ge=1, le=10, description="Rapport and relationship building skills")
    product_positioning: int = Field(ge=1, le=10, description="How well products were positioned")
    
    strengths: List[str] = Field(default_factory=list, max_items=5, description="Key strengths demonstrated")
    missed_opportunities: List[str] = Field(default_factory=list, max_items=5, description="Opportunities for improvement")
    coaching_insights: List[QuinnInsight] = Field(default_factory=list, max_items=3, description="Specific coaching insights")
    
    overall_notes: Optional[str] = Field(max_length=500, description="Overall coaching notes and observations")

    @validator('strengths', 'missed_opportunities')
    def validate_feedback_lists(cls, v):
        """Ensure feedback items are meaningful"""
        return [item.strip() for item in v if item and item.strip()]

class AnalysisMetadata(BaseModel):
    """Metadata about the analysis process"""
    analysis_version: str = Field(description="Version of analysis schema used")
    llm_model_used: str = Field(description="LLM model that performed the analysis")
    processing_time_seconds: float = Field(ge=0, description="Time taken to complete analysis")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")
    analysis_confidence: int = Field(ge=1, le=10, description="Overall confidence in analysis quality")
    confidence_factors: Dict[str, Any] = Field(default_factory=dict, description="Factors affecting confidence score")
    
    # Quality indicators
    transcript_quality_score: Optional[int] = Field(ge=1, le=10, description="Quality of source transcript")
    speaker_identification_quality: Optional[int] = Field(ge=1, le=10, description="How well speakers were identified")
    
    # Processing flags
    used_fallback_analysis: bool = Field(default=False, description="Whether fallback analysis was used")
    required_manual_review: bool = Field(default=False, description="Whether manual review is recommended")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Analysis creation timestamp")

class CallAnalysisResult(BaseModel):
    """Complete structured analysis result matching all PRD requirements"""
    
    # ANALYSIS-01: Core talking points extraction
    core_talking_points: List[str] = Field(
        min_items=1, 
        max_items=10, 
        description="Key discussion topics and pain points mentioned by prospect"
    )
    
    # ANALYSIS-02: Product identification
    telnyx_products: List[TelnyxProduct] = Field(
        default_factory=list,
        description="Telnyx products discussed or relevant to conversation"
    )
    
    # ANALYSIS-03: Use cases identification
    use_cases: List[str] = Field(
        default_factory=list,
        max_items=5,
        description="Specific use cases or applications discussed"
    )
    
    # ANALYSIS-04: Conversation focus analysis
    conversation_focus: ConversationFocus = Field(
        description="Primary topics and time distribution analysis"
    )
    
    # ANALYSIS-05: AE sentiment scoring
    ae_sentiment: SentimentScore = Field(
        description="AE's excitement, confidence, and engagement levels"
    )
    
    # ANALYSIS-06: Prospect sentiment scoring  
    prospect_sentiment: SentimentScore = Field(
        description="Prospect's interest, engagement, and buying signals"
    )
    
    # ANALYSIS-07 & 08: Next steps analysis
    next_steps: NextStepsAnalysis = Field(
        description="Next steps categorization and probability assessment"
    )
    
    # ANALYSIS-09 & QUINN-01-04: Quinn insights and scoring
    quinn_insights: QuinnAnalysis = Field(
        description="Comprehensive Quinn qualification scoring and coaching insights"
    )
    
    # Metadata and quality indicators
    analysis_metadata: AnalysisMetadata = Field(
        description="Analysis process metadata and quality indicators"
    )
    
    @validator('core_talking_points')
    def validate_talking_points(cls, v):
        """Ensure talking points are meaningful and non-duplicate"""
        cleaned = []
        seen = set()
        for point in v:
            cleaned_point = point.strip()
            if cleaned_point and cleaned_point.lower() not in seen:
                cleaned.append(cleaned_point)
                seen.add(cleaned_point.lower())
        
        if not cleaned:
            raise ValueError("At least one meaningful talking point must be provided")
        return cleaned[:10]  # Cap at 10 items
    
    @validator('use_cases')
    def validate_use_cases(cls, v):
        """Ensure use cases are specific and meaningful"""
        return [uc.strip() for uc in v if uc and uc.strip()][:5]
    
    @model_validator(mode='before')
    @classmethod
    def validate_analysis_consistency(cls, values):
        """Validate consistency across analysis dimensions"""
        
        # Ensure sentiment scores are reasonable relative to each other
        ae_sentiment = values.get('ae_sentiment')
        prospect_sentiment = values.get('prospect_sentiment')
        next_steps = values.get('next_steps')
        
        if ae_sentiment and prospect_sentiment and next_steps:
            # If both sentiment scores are high, probability should generally be higher
            avg_sentiment = (prospect_sentiment.interest_level + ae_sentiment.excitement_level) / 2
            probability = next_steps.probability
            
            # Warning for significant inconsistencies (not errors, just flags)
            if avg_sentiment >= 8 and probability <= 3:
                # High sentiment but very low probability - flag for review
                if 'analysis_metadata' in values:
                    values['analysis_metadata'].required_manual_review = True
                    values['analysis_metadata'].confidence_factors['sentiment_probability_mismatch'] = True
        
        return values
    
    def to_database_json(self) -> Dict[str, Any]:
        """Convert to JSON format suitable for database storage"""
        return self.dict(exclude_none=True, by_alias=True)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get high-level summary for reporting"""
        return {
            'talking_points_count': len(self.core_talking_points),
            'products_discussed': [p.value for p in self.telnyx_products],
            'primary_focus': self.conversation_focus.primary.value,
            'ae_excitement': self.ae_sentiment.excitement_level,
            'prospect_interest': self.prospect_sentiment.interest_level,
            'next_steps_category': self.next_steps.category.value,
            'next_steps_probability': self.next_steps.probability,
            'quinn_quality_score': self.quinn_insights.qualification_quality,
            'analysis_confidence': self.analysis_metadata.analysis_confidence,
            'requires_review': self.analysis_metadata.required_manual_review
        }
    
    def get_quinn_scorecard(self) -> Dict[str, int]:
        """Extract Quinn scoring for learning system"""
        return {
            'qualification_quality': self.quinn_insights.qualification_quality,
            'discovery_effectiveness': self.quinn_insights.discovery_effectiveness,
            'relationship_building': self.quinn_insights.relationship_building,
            'product_positioning': self.quinn_insights.product_positioning
        }

# Validation helper functions
def validate_analysis_result(data: Dict[str, Any]) -> CallAnalysisResult:
    """Validate and parse analysis result data"""
    try:
        return CallAnalysisResult(**data)
    except Exception as e:
        raise ValueError(f"Analysis result validation failed: {str(e)}")

def create_fallback_analysis(transcript: str, call_title: str) -> CallAnalysisResult:
    """Create fallback analysis when structured analysis fails"""
    return CallAnalysisResult(
        core_talking_points=["General product inquiry"],
        telnyx_products=[TelnyxProduct.VOICE],  # Default assumption
        use_cases=["Business communications"],
        conversation_focus=ConversationFocus(
            primary=ConversationFocusCategory.PRODUCT_OVERVIEW,
            secondary=[],
            time_distribution={"product_overview": 100}
        ),
        ae_sentiment=SentimentScore(
            excitement_level=5,
            confidence_level=5,
            engagement_level=5,
            notes="Fallback analysis - limited data"
        ),
        prospect_sentiment=SentimentScore(
            excitement_level=5,
            confidence_level=5,
            engagement_level=5,
            notes="Fallback analysis - limited data"
        ),
        next_steps=NextStepsAnalysis(
            category=NextStepsCategory.UNCLEAR,
            specific_actions=["Follow up with additional information"],
            probability=5
        ),
        quinn_insights=QuinnAnalysis(
            qualification_quality=5,
            discovery_effectiveness=5,
            relationship_building=5,
            product_positioning=5,
            overall_notes="Fallback analysis - manual review recommended"
        ),
        analysis_metadata=AnalysisMetadata(
            analysis_version="2.0-fallback",
            llm_model_used="fallback-system",
            processing_time_seconds=0.1,
            analysis_confidence=3,
            used_fallback_analysis=True,
            required_manual_review=True
        )
    )