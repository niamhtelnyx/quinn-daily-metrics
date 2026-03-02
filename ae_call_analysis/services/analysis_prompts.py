"""
Comprehensive analysis prompts for Telnyx sales call analysis
Implements structured prompts for all 9 analysis dimensions + Quinn scoring using Claude tool-use
"""

import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PromptConfig:
    """Configuration for prompt engineering"""
    max_transcript_length: int = 50000  # Claude context limit consideration
    include_examples: bool = True
    confidence_threshold: int = 7
    enable_chain_of_thought: bool = True

class TelnyxAnalysisPrompts:
    """Centralized prompt management for Telnyx call analysis"""
    
    def __init__(self, config: PromptConfig = None):
        self.config = config or PromptConfig()
        self.telnyx_products_knowledge = self._build_product_knowledge()
        self.quinn_scoring_methodology = self._build_quinn_methodology()
    
    def build_system_prompt(self) -> str:
        """Build comprehensive system prompt for Telnyx sales call analysis"""
        
        system_prompt = f"""You are an expert sales call analyzer specializing in Telnyx telecommunications products and services. Your role is to analyze sales conversations between Telnyx Account Executives (AEs) and prospects to extract actionable insights for sales coaching and pipeline management.

## TELNYX PRODUCT KNOWLEDGE

{self.telnyx_products_knowledge}

## ANALYSIS FRAMEWORK

You must analyze calls across 9 dimensions and provide Quinn qualification scoring:

### Core Analysis Dimensions:

1. **Talking Points** (ANALYSIS-01): Extract key discussion topics, pain points, and business needs mentioned by the prospect
2. **Product Identification** (ANALYSIS-02): Identify Telnyx products discussed or relevant to the conversation
3. **Use Cases** (ANALYSIS-03): Specific applications or business scenarios discussed
4. **Conversation Focus** (ANALYSIS-04): Primary topics and time distribution analysis
5. **AE Sentiment** (ANALYSIS-05): AE's excitement, confidence, and engagement levels (1-10)
6. **Prospect Sentiment** (ANALYSIS-06): Prospect's interest, engagement, and buying signals (1-10)
7. **Next Steps Analysis** (ANALYSIS-07/08): Categorization and probability assessment
8. **Analysis Quality** (ANALYSIS-09): Confidence in analysis accuracy (1-10)

### Quinn Qualification Scoring:

{self.quinn_scoring_methodology}

## ANALYSIS APPROACH

{'### Chain of Thought Process:' if self.config.enable_chain_of_thought else ''}
{'''
1. **Understand Context**: Read the entire transcript to understand the conversation flow
2. **Extract Information**: Systematically identify relevant information for each dimension
3. **Score Performance**: Apply consistent 1-10 scales based on evidence
4. **Validate Consistency**: Ensure scores align with observed behaviors and outcomes
5. **Provide Insights**: Generate actionable coaching recommendations
''' if self.config.enable_chain_of_thought else ''}

## OUTPUT REQUIREMENTS

You MUST use the provided `store_call_analysis` tool to structure your response. Provide:

- **Evidence-based scoring**: All scores (1-10) must be supported by specific examples from the transcript
- **Actionable insights**: Focus on specific, implementable coaching recommendations  
- **Consistent methodology**: Apply the same standards across all calls for reliable learning
- **Telnyx-specific context**: Leverage knowledge of our products, market, and sales process

## QUALITY STANDARDS

- **Thoroughness**: Address all 9 analysis dimensions completely
- **Accuracy**: Base all assessments on transcript evidence
- **Relevance**: Focus on insights that drive sales performance
- **Consistency**: Use standardized scoring approaches for reliable data

Be thorough but concise. Focus on insights that will help improve AE performance and prospect experience."""

        return system_prompt
    
    def _build_product_knowledge(self) -> str:
        """Build comprehensive Telnyx product knowledge section"""
        
        return """### Telnyx Product Portfolio:

**Voice Services:**
- SIP trunking and voice connectivity
- International calling and toll-free numbers
- Voice APIs and programmable voice
- Call routing, recording, and analytics
- WebRTC and browser-based calling

**Messaging Services:**
- SMS and MMS APIs
- International messaging
- Two-factor authentication and verification
- Bulk messaging and campaigns
- WhatsApp Business API

**Wireless/Connectivity:**
- IoT connectivity and SIM cards
- Private wireless networks
- Global roaming and data plans
- eSIM and programmable connectivity

**AI & Advanced Services:**
- Voice AI and conversational AI
- Speech recognition and synthesis
- Call analytics and insights
- Fraud detection and security

**Platform & Infrastructure:**
- Private network backbone
- Real-time communications platform
- Developer APIs and SDKs
- Enterprise integrations (Salesforce, Teams, etc.)

### Common Use Cases:
- Contact centers and customer service
- Sales and marketing communications
- IoT device connectivity
- Financial services and banking
- Healthcare communications
- E-commerce and marketplace platforms"""

    def _build_quinn_methodology(self) -> str:
        """Build Quinn qualification scoring methodology"""
        
        return """
1. **Qualification Quality** (1-10): Overall effectiveness in qualifying the opportunity
   - 9-10: Exceptional discovery, uncovered clear pain points, budget, timeline, and decision process
   - 7-8: Good qualification with most key areas covered effectively
   - 5-6: Basic qualification with some important areas missed
   - 3-4: Minimal qualification, significant gaps in discovery
   - 1-2: Poor qualification, little to no discovery conducted

2. **Discovery Effectiveness** (1-10): How well did the AE uncover prospect needs and pain points
   - Questions asked, listening skills, follow-up inquiries
   - Depth of understanding of prospect's current situation and challenges

3. **Relationship Building** (1-10): Rapport establishment and trust building
   - Personal connection, credibility establishment, communication style
   - Prospect engagement and comfort level

4. **Product Positioning** (1-10): How effectively products were positioned against prospect needs
   - Relevance of solutions discussed, customization to prospect needs
   - Competitive differentiation and value articulation

### Scoring Guidelines:
- **Use specific evidence**: Each score must cite specific examples from the transcript
- **Consider context**: Adjust for call type (intro, demo, negotiation)
- **Focus on improvement**: Identify specific areas for coaching and development
- **Benchmark consistency**: Apply the same standards across all AEs for fair comparison"""

    def get_tool_definition(self) -> Dict[str, Any]:
        """Get Claude tool definition for structured analysis output"""
        
        return {
            "name": "store_call_analysis",
            "description": "Store comprehensive Telnyx sales call analysis with structured insights and Quinn qualification scoring",
            "input_schema": {
                "type": "object",
                "properties": {
                    "core_talking_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 10,
                        "description": "Key discussion topics, pain points, and business needs mentioned by prospect"
                    },
                    "telnyx_products": {
                        "type": "array", 
                        "items": {
                            "type": "string",
                            "enum": ["voice", "messaging", "wireless", "voice_ai", "numbers", "storage", "verify", "connections"]
                        },
                        "description": "Telnyx products discussed or relevant to the conversation"
                    },
                    "use_cases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5,
                        "description": "Specific use cases or applications discussed"
                    },
                    "conversation_focus": {
                        "type": "object",
                        "properties": {
                            "primary": {
                                "type": "string",
                                "enum": ["product_overview", "pricing", "technical", "implementation", "use_cases", "competitive", "timeline", "decision_process"],
                                "description": "Primary conversation topic"
                            },
                            "secondary": {
                                "type": "array",
                                "items": {
                                    "type": "string", 
                                    "enum": ["product_overview", "pricing", "technical", "implementation", "use_cases", "competitive", "timeline", "decision_process"]
                                },
                                "maxItems": 3,
                                "description": "Secondary topics discussed"
                            },
                            "time_distribution": {
                                "type": "object",
                                "description": "Percentage time spent on each topic (should sum to ~100)",
                                "additionalProperties": {"type": "integer", "minimum": 0, "maximum": 100}
                            }
                        },
                        "required": ["primary", "time_distribution"]
                    },
                    "ae_sentiment": {
                        "type": "object",
                        "properties": {
                            "excitement_level": {"type": "integer", "minimum": 1, "maximum": 10, "description": "AE's excitement about the opportunity"},
                            "confidence_level": {"type": "integer", "minimum": 1, "maximum": 10, "description": "AE's confidence in the conversation"},
                            "engagement_level": {"type": "integer", "minimum": 1, "maximum": 10, "description": "AE's level of active engagement"},
                            "buying_signals": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 5,
                                "description": "Specific buying signals observed from AE perspective"
                            },
                            "concerns": {
                                "type": "array",
                                "items": {"type": "string"}, 
                                "maxItems": 5,
                                "description": "Concerns or hesitations expressed by AE"
                            },
                            "notes": {"type": "string", "maxLength": 500, "description": "Additional AE sentiment observations"}
                        },
                        "required": ["excitement_level", "confidence_level", "engagement_level"]
                    },
                    "prospect_sentiment": {
                        "type": "object", 
                        "properties": {
                            "excitement_level": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Prospect's excitement about Telnyx solutions"},
                            "confidence_level": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Prospect's confidence in Telnyx as a provider"},
                            "engagement_level": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Prospect's level of active engagement"},
                            "buying_signals": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 5,
                                "description": "Specific buying signals from prospect"
                            },
                            "concerns": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "maxItems": 5,
                                "description": "Concerns or objections raised by prospect"
                            },
                            "notes": {"type": "string", "maxLength": 500, "description": "Additional prospect sentiment observations"}
                        },
                        "required": ["excitement_level", "confidence_level", "engagement_level"]
                    },
                    "next_steps": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["moving_forward", "self_service", "unclear", "not_interested"],
                                "description": "Overall next steps category"
                            },
                            "specific_actions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": 5,
                                "description": "Specific action items identified"
                            },
                            "timeline": {"type": "string", "maxLength": 100, "description": "Expected timeline for next steps"},
                            "probability": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Probability of forward movement"},
                            "owner": {"type": "string", "maxLength": 100, "description": "Who is responsible for next steps"}
                        },
                        "required": ["category", "specific_actions", "probability"]
                    },
                    "quinn_insights": {
                        "type": "object",
                        "properties": {
                            "qualification_quality": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Overall qualification effectiveness"},
                            "discovery_effectiveness": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Effectiveness of need discovery"},
                            "relationship_building": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Rapport and relationship building"},
                            "product_positioning": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Product positioning effectiveness"},
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 5,
                                "description": "Key strengths demonstrated by AE"
                            },
                            "missed_opportunities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 5,
                                "description": "Opportunities for improvement"
                            },
                            "coaching_insights": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "area": {"type": "string", "maxLength": 100, "description": "Area of focus"},
                                        "observation": {"type": "string", "maxLength": 300, "description": "Specific observation"},
                                        "score": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Performance score"},
                                        "improvement_suggestion": {"type": "string", "maxLength": 200, "description": "Improvement suggestion"}
                                    },
                                    "required": ["area", "observation", "score"]
                                },
                                "maxItems": 3,
                                "description": "Specific coaching insights"
                            },
                            "overall_notes": {"type": "string", "maxLength": 500, "description": "Overall coaching notes"}
                        },
                        "required": ["qualification_quality", "discovery_effectiveness", "relationship_building", "product_positioning"]
                    },
                    "analysis_metadata": {
                        "type": "object",
                        "properties": {
                            "analysis_confidence": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Confidence in analysis quality"},
                            "transcript_quality_score": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Quality of source transcript"},
                            "speaker_identification_quality": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Speaker identification clarity"},
                            "confidence_factors": {
                                "type": "object",
                                "description": "Factors affecting confidence",
                                "additionalProperties": {"type": "boolean"}
                            },
                            "required_manual_review": {"type": "boolean", "description": "Whether manual review is recommended"},
                            "processing_notes": {"type": "string", "maxLength": 300, "description": "Additional processing notes"}
                        },
                        "required": ["analysis_confidence"]
                    }
                },
                "required": [
                    "core_talking_points", 
                    "telnyx_products", 
                    "conversation_focus",
                    "ae_sentiment", 
                    "prospect_sentiment", 
                    "next_steps", 
                    "quinn_insights",
                    "analysis_metadata"
                ]
            }
        }
    
    def build_analysis_prompt(self, transcript: str, call_metadata: Dict[str, Any] = None) -> str:
        """Build the analysis prompt for a specific call transcript"""
        
        # Truncate transcript if too long
        if len(transcript) > self.config.max_transcript_length:
            transcript = transcript[:self.config.max_transcript_length] + "\n\n[TRANSCRIPT TRUNCATED DUE TO LENGTH]"
        
        metadata_context = ""
        if call_metadata:
            metadata_context = f"""
## CALL CONTEXT
- Title: {call_metadata.get('title', 'N/A')}
- Date: {call_metadata.get('date', 'N/A')}
- AE: {call_metadata.get('ae_name', 'N/A')}
- Prospect: {call_metadata.get('prospect_name', 'N/A')}
- Company: {call_metadata.get('prospect_company', 'N/A')}
"""

        examples_section = ""
        if self.config.include_examples:
            examples_section = self._build_examples_section()

        prompt = f"""{metadata_context}

{examples_section}

## TRANSCRIPT TO ANALYZE

{transcript}

## ANALYSIS INSTRUCTIONS

Please analyze this Telnyx sales call transcript comprehensively using the store_call_analysis tool. Focus on:

1. **Extract key insights** across all 9 analysis dimensions
2. **Provide evidence-based scoring** (1-10 scales) with specific transcript citations  
3. **Generate actionable coaching insights** for Quinn learning system
4. **Ensure scoring consistency** for reliable machine learning training data
5. **Flag quality concerns** if transcript clarity or completeness affects confidence

Remember: Your analysis will be used for AE coaching and automated learning systems, so accuracy and consistency are critical."""

        return prompt
    
    def _build_examples_section(self) -> str:
        """Build few-shot examples section for prompt (if enabled)"""
        
        return """
## ANALYSIS EXAMPLES

### Example Analysis Format:

**Talking Points Extraction:**
- "Current phone system is unreliable during peak hours" → Pain Point: System reliability
- "Need to scale internationally next quarter" → Business Need: Global expansion
- "Budget approval process takes 6-8 weeks" → Process Insight: Decision timeline

**Sentiment Scoring Examples:**
- Prospect: "This sounds exactly like what we need!" → Interest Level: 9/10
- AE: "I'm confident we can solve this for you" → Confidence Level: 8/10
- Prospect: "We need to think about budget..." → Concern flagged

**Quinn Scoring Examples:**
- Great discovery: "What's driving the urgency to change providers?" → Discovery: 8/10
- Missed opportunity: Didn't ask about decision-making process → Opportunity noted
- Good positioning: Tied features directly to pain points → Positioning: 7/10

"""

    def build_confidence_assessment_prompt(self, analysis_result: Dict[str, Any], transcript: str) -> str:
        """Build prompt for confidence scoring assessment"""
        
        return f"""Please assess the confidence level of this analysis based on the following factors:

## ANALYSIS RESULT
{json.dumps(analysis_result, indent=2)}

## ORIGINAL TRANSCRIPT  
{transcript[:2000]}{'...' if len(transcript) > 2000 else ''}

## CONFIDENCE FACTORS TO EVALUATE

1. **Transcript Quality** (1-10):
   - Speaker identification clarity
   - Audio transcription accuracy
   - Conversation completeness

2. **Evidence Support** (1-10):
   - How well the analysis is supported by transcript evidence
   - Consistency between insights and observable data

3. **Analysis Completeness** (1-10): 
   - All required fields populated meaningfully
   - Comprehensive coverage of conversation content

4. **Internal Consistency** (1-10):
   - Sentiment scores align with next steps probability
   - Quinn scores reflect observed behaviors
   - Time distribution makes sense

Please provide an overall confidence score (1-10) and identify any factors that reduce confidence."""

# Utility functions for prompt management
def get_analysis_prompt_for_call(transcript: str, call_metadata: Dict[str, Any] = None) -> tuple[str, Dict[str, Any], str]:
    """
    Get complete prompt package for call analysis
    
    Returns:
        tuple: (system_prompt, tool_definition, user_prompt)
    """
    prompts = TelnyxAnalysisPrompts()
    
    system_prompt = prompts.build_system_prompt()
    tool_definition = prompts.get_tool_definition()
    user_prompt = prompts.build_analysis_prompt(transcript, call_metadata)
    
    return system_prompt, tool_definition, user_prompt

def validate_tool_response(tool_response: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean tool response before database storage"""
    
    logger.info("Validating tool response for database storage")
    
    # Add required metadata if missing
    if 'analysis_metadata' not in tool_response:
        tool_response['analysis_metadata'] = {
            'analysis_confidence': 7,
            'analysis_version': '2.0-claude-structured'
        }
    
    # Ensure all required fields have defaults
    required_defaults = {
        'use_cases': [],
        'telnyx_products': ['voice'],  # Default assumption
    }
    
    for field, default in required_defaults.items():
        if field not in tool_response or not tool_response[field]:
            tool_response[field] = default
    
    # Basic validation of required fields
    required_fields = [
        'core_talking_points', 'telnyx_products', 'conversation_focus',
        'ae_sentiment', 'prospect_sentiment', 'next_steps', 'quinn_insights',
        'analysis_metadata'
    ]
    
    validation_errors = []
    for field in required_fields:
        if field not in tool_response:
            validation_errors.append(f"Missing required field: {field}")
    
    # Validate nested objects have required keys
    if 'ae_sentiment' in tool_response:
        ae_required = ['excitement_level', 'confidence_level', 'engagement_level']
        for key in ae_required:
            if key not in tool_response['ae_sentiment']:
                validation_errors.append(f"Missing ae_sentiment.{key}")
    
    if 'prospect_sentiment' in tool_response:
        prospect_required = ['excitement_level', 'confidence_level', 'engagement_level']
        for key in prospect_required:
            if key not in tool_response['prospect_sentiment']:
                validation_errors.append(f"Missing prospect_sentiment.{key}")
    
    if 'next_steps' in tool_response:
        next_required = ['category', 'specific_actions', 'probability']
        for key in next_required:
            if key not in tool_response['next_steps']:
                validation_errors.append(f"Missing next_steps.{key}")
    
    if 'quinn_insights' in tool_response:
        quinn_required = ['qualification_quality', 'discovery_effectiveness', 'relationship_building', 'product_positioning']
        for key in quinn_required:
            if key not in tool_response['quinn_insights']:
                validation_errors.append(f"Missing quinn_insights.{key}")
    
    # If validation errors exist, add them to metadata but don't fail
    if validation_errors:
        logger.warning(f"Validation issues found: {validation_errors}")
        tool_response['analysis_metadata']['validation_issues'] = validation_errors
        tool_response['analysis_metadata']['required_manual_review'] = True
        tool_response['analysis_metadata']['analysis_confidence'] = min(
            tool_response['analysis_metadata'].get('analysis_confidence', 7), 5
        )
    else:
        logger.info("Tool response validation successful")
    
    return tool_response