"""
Analysis Prompts for AE Call Analysis
====================================

This module contains structured prompts for analyzing AE (Account Executive) calls
across 9 key dimensions plus Quinn qualification scoring.
"""

from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ConversationFocus(str, Enum):
    """Conversation focus categories"""
    DISCOVERY = "discovery"
    DEMO = "demo"
    PRICING = "pricing"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    RELATIONSHIP_BUILDING = "relationship_building"
    TECHNICAL_DEEP_DIVE = "technical_deep_dive"
    COMPETITIVE = "competitive"
    MIXED = "mixed"


class NextStepsCategory(str, Enum):
    """Next steps classification"""
    FOLLOW_UP_SCHEDULED = "follow_up_scheduled"
    DEMO_REQUESTED = "demo_requested"
    PROPOSAL_TO_SEND = "proposal_to_send"
    DECISION_MAKER_INTRO = "decision_maker_intro"
    TECHNICAL_VALIDATION = "technical_validation"
    PILOT_DISCUSSION = "pilot_discussion"
    CONTRACT_NEGOTIATION = "contract_negotiation"
    NO_CLEAR_NEXT_STEPS = "no_clear_next_steps"
    PROSPECT_TO_CONSIDER = "prospect_to_consider"
    LOST_OPPORTUNITY = "lost_opportunity"


# ============================================================================
# STRUCTURED OUTPUT SCHEMAS
# ============================================================================

class TalkingPointsAnalysis(BaseModel):
    """Core talking points and pain points analysis"""
    primary_pain_points: list[str] = Field(description="Main pain points discussed by prospect")
    ae_key_talking_points: list[str] = Field(description="Key talking points used by AE")
    pain_point_alignment: int = Field(ge=1, le=10, description="How well AE talking points aligned with pain points (1-10)")
    unaddressed_pain_points: list[str] = Field(description="Pain points mentioned but not adequately addressed")
    most_compelling_point: str = Field(description="Most compelling talking point or pain point discussed")


class TelnyxProductsAnalysis(BaseModel):
    """Telnyx products and features discussed"""
    products_discussed: list[str] = Field(description="Telnyx products mentioned in the call")
    features_highlighted: list[str] = Field(description="Specific features or capabilities discussed")
    technical_depth: int = Field(ge=1, le=10, description="Depth of technical discussion (1=surface, 10=deep technical)")
    competitor_mentions: list[str] = Field(description="Competing products or vendors mentioned")
    product_fit_assessment: int = Field(ge=1, le=10, description="How well discussed products fit prospect needs (1-10)")


class UseCasesAnalysis(BaseModel):
    """Use cases and business scenarios analysis"""
    primary_use_cases: list[str] = Field(description="Main use cases discussed")
    business_impact_areas: list[str] = Field(description="Business areas that would be impacted")
    quantified_benefits: list[str] = Field(description="Any quantified benefits or ROI mentioned")
    implementation_complexity: int = Field(ge=1, le=10, description="Perceived implementation complexity (1=simple, 10=complex)")
    use_case_specificity: int = Field(ge=1, le=10, description="How specific and detailed the use case discussion was (1-10)")


class ConversationFocusAnalysis(BaseModel):
    """Analysis of conversation focus and structure"""
    primary_focus: ConversationFocus = Field(description="Primary focus of the conversation")
    secondary_focus: Optional[ConversationFocus] = Field(description="Secondary focus if applicable")
    focus_effectiveness: int = Field(ge=1, le=10, description="How effectively the conversation stayed focused (1-10)")
    topic_transitions: int = Field(ge=1, le=10, description="Quality of transitions between topics (1-10)")
    conversation_control: int = Field(ge=1, le=10, description="How well AE controlled conversation flow (1-10)")


class SentimentAnalysis(BaseModel):
    """AE and prospect sentiment analysis"""
    ae_sentiment: int = Field(ge=1, le=10, description="AE sentiment/confidence level (1=low, 10=high)")
    prospect_sentiment: int = Field(ge=1, le=10, description="Prospect engagement/interest level (1=low, 10=high)")
    ae_sentiment_indicators: list[str] = Field(description="Specific indicators of AE sentiment")
    prospect_sentiment_indicators: list[str] = Field(description="Specific indicators of prospect sentiment")
    overall_call_energy: int = Field(ge=1, le=10, description="Overall energy and momentum of the call (1-10)")


class NextStepsAnalysis(BaseModel):
    """Next steps and follow-up analysis"""
    next_steps_category: NextStepsCategory = Field(description="Primary category of next steps")
    specific_actions: list[str] = Field(description="Specific actions committed to by each party")
    timeline_mentioned: bool = Field(description="Whether specific timelines were discussed")
    timeline_details: str = Field(description="Specific timeline details if mentioned")
    commitment_level: int = Field(ge=1, le=10, description="Level of commitment from prospect (1=low, 10=high)")
    ae_follow_up_quality: int = Field(ge=1, le=10, description="Quality of AE's follow-up planning (1-10)")


class ConfidenceAnalysis(BaseModel):
    """Analysis confidence and quality metrics"""
    transcript_quality: int = Field(ge=1, le=10, description="Quality of transcript for analysis (1=poor, 10=excellent)")
    analysis_confidence: int = Field(ge=1, le=10, description="Overall confidence in analysis accuracy (1-10)")
    missing_context: list[str] = Field(description="Key information that may be missing from transcript")
    ambiguous_areas: list[str] = Field(description="Areas where interpretation was unclear")
    data_reliability: int = Field(ge=1, le=10, description="Reliability of extracted data (1-10)")


class QuinnScoring(BaseModel):
    """Quinn qualification framework scoring"""
    need_clarity: int = Field(ge=1, le=10, description="Clarity of prospect's need (1=unclear, 10=crystal clear)")
    decision_authority: int = Field(ge=1, le=10, description="Level of decision-making authority (1=none, 10=final authority)")
    budget_availability: int = Field(ge=1, le=10, description="Budget availability and clarity (1=no budget, 10=confirmed budget)")
    timeline_urgency: int = Field(ge=1, le=10, description="Urgency of timeline (1=no timeline, 10=immediate need)")
    champion_strength: int = Field(ge=1, le=10, description="Strength of internal champion (1=none, 10=strong advocate)")
    competition_position: int = Field(ge=1, le=10, description="Competitive position (1=losing, 10=winning)")
    overall_qualification: int = Field(ge=1, le=10, description="Overall Quinn qualification score")
    qualification_notes: str = Field(description="Additional qualification insights")


class ComprehensiveAnalysis(BaseModel):
    """Complete analysis output containing all dimensions"""
    talking_points: TalkingPointsAnalysis
    telnyx_products: TelnyxProductsAnalysis
    use_cases: UseCasesAnalysis
    conversation_focus: ConversationFocusAnalysis
    sentiment: SentimentAnalysis
    next_steps: NextStepsAnalysis
    confidence: ConfidenceAnalysis
    quinn_scoring: QuinnScoring


# ============================================================================
# ANALYSIS PROMPTS
# ============================================================================

CORE_TALKING_POINTS_PROMPT = """
Analyze the call transcript for core talking points and pain points:

1. **Primary Pain Points**: Identify the main business pain points, challenges, or problems the prospect explicitly mentioned or implied.

2. **AE Key Talking Points**: Extract the key messages, value propositions, and talking points the AE used.

3. **Pain Point Alignment**: Assess how well the AE's talking points aligned with and addressed the prospect's pain points (1-10 scale).

4. **Unaddressed Pain Points**: Identify any pain points the prospect mentioned that the AE didn't adequately address.

5. **Most Compelling Point**: Determine the single most compelling talking point or pain point that emerged from the conversation.

Focus on:
- Explicit statements about problems or challenges
- Business impact discussions
- AE's response strategies
- Missed opportunities for better alignment

Return the analysis in the TalkingPointsAnalysis schema format.
"""

TELNYX_PRODUCTS_PROMPT = """
Analyze the Telnyx products and technical discussion:

1. **Products Discussed**: List all Telnyx products, services, or solutions mentioned by name.

2. **Features Highlighted**: Identify specific features, capabilities, or technical specifications discussed.

3. **Technical Depth**: Rate the depth of technical discussion (1=surface level mentions, 10=deep technical dive).

4. **Competitor Mentions**: Note any competing vendors, products, or solutions mentioned.

5. **Product Fit Assessment**: Evaluate how well the discussed products appear to fit the prospect's needs (1-10).

Look for:
- Product names and feature mentions
- Technical specifications or capabilities
- Competitive comparisons
- Integration discussions
- Implementation requirements

Return the analysis in the TelnyxProductsAnalysis schema format.
"""

USE_CASES_PROMPT = """
Analyze the business use cases and scenarios discussed:

1. **Primary Use Cases**: Identify the main business use cases or scenarios discussed.

2. **Business Impact Areas**: Determine which business areas would be affected by implementation.

3. **Quantified Benefits**: Extract any specific metrics, ROI figures, or quantified benefits mentioned.

4. **Implementation Complexity**: Assess the perceived complexity of implementation (1=simple, 10=highly complex).

5. **Use Case Specificity**: Rate how specific and detailed the use case discussion was (1-10).

Focus on:
- Concrete business scenarios
- Operational improvements
- Cost savings or revenue impact
- Implementation challenges
- Success metrics

Return the analysis in the UseCasesAnalysis schema format.
"""

CONVERSATION_FOCUS_PROMPT = """
Analyze the structure and focus of the conversation:

1. **Primary Focus**: Identify the main focus area from: discovery, demo, pricing, objection_handling, closing, relationship_building, technical_deep_dive, competitive, mixed.

2. **Secondary Focus**: If applicable, identify a secondary focus area.

3. **Focus Effectiveness**: Rate how well the conversation stayed focused and productive (1-10).

4. **Topic Transitions**: Evaluate the quality and smoothness of transitions between topics (1-10).

5. **Conversation Control**: Assess how well the AE controlled and guided the conversation flow (1-10).

Consider:
- Time spent on each topic
- Natural flow vs. jumping around
- AE's ability to guide discussion
- Prospect's engagement with different topics

Return the analysis in the ConversationFocusAnalysis schema format.
"""

SENTIMENT_ANALYSIS_PROMPT = """
Analyze the sentiment and engagement levels of both parties:

1. **AE Sentiment**: Rate the AE's confidence, enthusiasm, and positive sentiment (1=low/negative, 10=high/very positive).

2. **Prospect Sentiment**: Rate the prospect's interest, engagement, and positive sentiment (1=low/negative, 10=high/very positive).

3. **AE Sentiment Indicators**: Identify specific words, phrases, or behaviors indicating AE sentiment.

4. **Prospect Sentiment Indicators**: Identify specific indicators of prospect sentiment and engagement.

5. **Overall Call Energy**: Rate the overall energy, momentum, and positive atmosphere (1-10).

Look for:
- Tone and enthusiasm in language
- Questions and engagement level
- Positive vs. negative language
- Energy and momentum shifts
- Hesitation or confidence indicators

Return the analysis in the SentimentAnalysis schema format.
"""

NEXT_STEPS_PROMPT = """
Analyze the next steps and follow-up commitments:

1. **Next Steps Category**: Classify the primary next step from: follow_up_scheduled, demo_requested, proposal_to_send, decision_maker_intro, technical_validation, pilot_discussion, contract_negotiation, no_clear_next_steps, prospect_to_consider, lost_opportunity.

2. **Specific Actions**: List specific actions committed to by each party.

3. **Timeline Mentioned**: Determine if specific timelines were discussed.

4. **Timeline Details**: Capture specific timeline information if mentioned.

5. **Commitment Level**: Rate the prospect's level of commitment to next steps (1-10).

6. **AE Follow-up Quality**: Evaluate how well the AE planned and structured follow-up (1-10).

Focus on:
- Clear commitments from both sides
- Specific dates and deadlines
- Quality of follow-up planning
- Mutual agreement on next steps

Return the analysis in the NextStepsAnalysis schema format.
"""

CONFIDENCE_ANALYSIS_PROMPT = """
Assess the quality and reliability of the analysis:

1. **Transcript Quality**: Rate the quality of the transcript for analysis purposes (1=poor/unclear, 10=excellent/clear).

2. **Analysis Confidence**: Rate your overall confidence in the accuracy of the analysis (1-10).

3. **Missing Context**: Identify any key information that may be missing from the transcript.

4. **Ambiguous Areas**: Note areas where interpretation was unclear or uncertain.

5. **Data Reliability**: Rate the reliability of the extracted data and insights (1-10).

Consider:
- Audio quality and transcription accuracy
- Completeness of the conversation
- Cultural or contextual factors
- Technical jargon or unclear references

Return the analysis in the ConfidenceAnalysis schema format.
"""

QUINN_SCORING_PROMPT = """
Apply the Quinn qualification framework to score this opportunity:

1. **Need Clarity** (1-10): How clear and well-defined is the prospect's need?
   - 1-3: Vague or no clear need
   - 4-6: Some need identified but unclear
   - 7-8: Clear need with some details
   - 9-10: Crystal clear, urgent need

2. **Decision Authority** (1-10): What level of decision-making authority does the contact have?
   - 1-3: No decision authority, influencer only
   - 4-6: Some influence in decision process
   - 7-8: Significant decision influence
   - 9-10: Final decision authority

3. **Budget Availability** (1-10): How clear and available is the budget?
   - 1-3: No budget or budget unclear
   - 4-6: Budget may exist but unconfirmed
   - 7-8: Budget likely available
   - 9-10: Confirmed budget allocated

4. **Timeline Urgency** (1-10): How urgent is their timeline?
   - 1-3: No timeline or far future
   - 4-6: Loose timeline, not urgent
   - 7-8: Defined timeline, some urgency
   - 9-10: Immediate need, urgent timeline

5. **Champion Strength** (1-10): How strong is our internal champion?
   - 1-3: No champion or weak support
   - 4-6: Mild internal support
   - 7-8: Good internal advocate
   - 9-10: Strong champion pushing for us

6. **Competition Position** (1-10): What's our competitive position?
   - 1-3: Losing to competition or heavy competition
   - 4-6: Competitive but not leading
   - 7-8: Strong position vs. competition
   - 9-10: Clear leader or no competition

7. **Overall Qualification** (1-10): Overall opportunity qualification score.

8. **Qualification Notes**: Additional insights about the qualification.

Return the analysis in the QuinnScoring schema format.
"""


# ============================================================================
# COMPREHENSIVE ANALYSIS PROMPT
# ============================================================================

def build_comprehensive_analysis_prompt(transcript: str) -> str:
    """Build the complete analysis prompt for all dimensions"""
    return f"""
You are an expert AE call analyst. Analyze the following call transcript across all dimensions and provide a comprehensive analysis.

TRANSCRIPT:
{transcript}

ANALYSIS INSTRUCTIONS:
Analyze this call transcript thoroughly across all 9 dimensions plus Quinn qualification scoring. Be specific, objective, and provide actionable insights.

1. **TALKING POINTS & PAIN POINTS**: {CORE_TALKING_POINTS_PROMPT}

2. **TELNYX PRODUCTS**: {TELNYX_PRODUCTS_PROMPT}

3. **USE CASES**: {USE_CASES_PROMPT}

4. **CONVERSATION FOCUS**: {CONVERSATION_FOCUS_PROMPT}

5. **SENTIMENT ANALYSIS**: {SENTIMENT_ANALYSIS_PROMPT}

6. **NEXT STEPS**: {NEXT_STEPS_PROMPT}

7. **CONFIDENCE ANALYSIS**: {CONFIDENCE_ANALYSIS_PROMPT}

8. **QUINN SCORING**: {QUINN_SCORING_PROMPT}

Provide your complete analysis in the ComprehensiveAnalysis schema format, ensuring all fields are populated with accurate, insight-driven information based on the transcript content.

Focus on actionable insights that would help the AE improve future performance and the sales team understand opportunity quality and next steps.
"""


# ============================================================================
# INDIVIDUAL DIMENSION ANALYSIS FUNCTIONS
# ============================================================================

def build_talking_points_prompt(transcript: str) -> str:
    """Build prompt for talking points analysis"""
    return f"""
{CORE_TALKING_POINTS_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the TalkingPointsAnalysis schema format.
"""


def build_products_prompt(transcript: str) -> str:
    """Build prompt for Telnyx products analysis"""
    return f"""
{TELNYX_PRODUCTS_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the TelnyxProductsAnalysis schema format.
"""


def build_use_cases_prompt(transcript: str) -> str:
    """Build prompt for use cases analysis"""
    return f"""
{USE_CASES_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the UseCasesAnalysis schema format.
"""


def build_conversation_focus_prompt(transcript: str) -> str:
    """Build prompt for conversation focus analysis"""
    return f"""
{CONVERSATION_FOCUS_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the ConversationFocusAnalysis schema format.
"""


def build_sentiment_prompt(transcript: str) -> str:
    """Build prompt for sentiment analysis"""
    return f"""
{SENTIMENT_ANALYSIS_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the SentimentAnalysis schema format.
"""


def build_next_steps_prompt(transcript: str) -> str:
    """Build prompt for next steps analysis"""
    return f"""
{NEXT_STEPS_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the NextStepsAnalysis schema format.
"""


def build_confidence_prompt(transcript: str) -> str:
    """Build prompt for confidence analysis"""
    return f"""
{CONFIDENCE_ANALYSIS_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the ConfidenceAnalysis schema format.
"""


def build_quinn_scoring_prompt(transcript: str) -> str:
    """Build prompt for Quinn scoring"""
    return f"""
{QUINN_SCORING_PROMPT}

TRANSCRIPT:
{transcript}

Provide your analysis in the QuinnScoring schema format.
"""