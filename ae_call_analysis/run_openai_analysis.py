#!/usr/bin/env python3
"""
Run OpenAI analysis on Ben Lewell call
Generates BOTH detailed analysis AND simple 9-category summary
"""
import asyncio
import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.database import get_db
from services.openai_client import OpenAIClient
from dataclasses import dataclass
from datetime import datetime

@dataclass
class OpenAIConfig:
    api_key: str
    model: str = 'gpt-4o'  # Use GPT-4o for 16k output tokens
    max_tokens: int = 4096  # Max for most models
    temperature: float = 0.1
    timeout: float = 120.0  # Increased timeout
    max_retries: int = 3

# =============================================================================
# DUAL OUTPUT SYSTEM PROMPT
# Generates BOTH detailed analysis AND simple 9-category summary
# =============================================================================

SYSTEM_PROMPT = """You are an expert sales call analyst. Analyze the provided sales call transcript and return TWO formats:

1. **detailed_analysis**: Rich, nested analysis with full insights (for deep dives)
2. **simple_summary**: Clean 9-category summary (for quick scans and dashboards)

Return your analysis as a JSON object with EXACTLY this structure:

{
    "detailed_analysis": {
        "core_talking_points": {
            "primary_pain_points": ["list of main pain points discussed"],
            "ae_key_talking_points": ["key talking points used by AE"],
            "pain_point_alignment": 8,
            "unaddressed_pain_points": ["pain points not adequately addressed"],
            "most_compelling_point": "single most compelling point"
        },
        "telnyx_products": {
            "products_discussed": ["list of Telnyx products mentioned"],
            "features_highlighted": ["specific features discussed"],
            "technical_depth": 7,
            "competitor_mentions": ["competing products mentioned"],
            "product_fit_assessment": 8
        },
        "use_cases": {
            "primary_use_cases": ["main business use cases"],
            "business_impact_areas": ["areas impacted by implementation"],
            "quantified_benefits": ["specific ROI or metrics mentioned"],
            "implementation_complexity": 5,
            "use_case_specificity": 7
        },
        "conversation_focus": {
            "primary_focus": "discovery|demo|pricing|objection_handling|closing|relationship_building|technical_deep_dive|competitive|mixed",
            "secondary_focus": "optional secondary focus",
            "focus_effectiveness": 8,
            "topic_transitions": 7,
            "conversation_control": 8
        },
        "sentiment_analysis": {
            "ae_sentiment": 8,
            "prospect_sentiment": 7,
            "ae_sentiment_indicators": ["specific indicators"],
            "prospect_sentiment_indicators": ["specific indicators"],
            "overall_call_energy": 7
        },
        "next_steps": {
            "next_steps_category": "follow_up_scheduled|demo_requested|proposal_to_send|decision_maker_intro|technical_validation|pilot_discussion|contract_negotiation|no_clear_next_steps|prospect_to_consider|lost_opportunity",
            "specific_actions": ["committed actions"],
            "timeline_mentioned": true,
            "timeline_details": "timeline specifics if mentioned",
            "commitment_level": 7,
            "ae_follow_up_quality": 8
        },
        "analysis_confidence": {
            "transcript_quality": 8,
            "analysis_confidence": 8,
            "missing_context": ["what might be missing"],
            "ambiguous_areas": ["unclear areas"],
            "data_reliability": 8
        },
        "quinn_scoring": {
            "need_clarity": 8,
            "decision_authority": 6,
            "budget_availability": 5,
            "timeline_urgency": 7,
            "champion_strength": 6,
            "competition_position": 7,
            "overall_qualification": 7,
            "qualification_notes": "additional insights"
        }
    },
    "simple_summary": {
        "core_talking_points": ["Key theme 1", "Pain point 1", "Business need 1"],
        "telnyx_products": ["voice", "messaging", "wireless", "voice_ai", "numbers", "storage", "verify", "connections"],
        "use_cases": ["Primary use case 1", "Secondary use case 2"],
        "conversation_focus": "primary focus area as simple string",
        "ae_sentiment": {
            "excitement_level": 8,
            "confidence_level": 7
        },
        "prospect_sentiment": {
            "interest_level": 7,
            "engagement_level": 8,
            "buying_signals": ["specific signal 1", "specific signal 2"]
        },
        "next_steps": {
            "category": "moving_forward|self_service|unclear|not_interested",
            "specific_actions": ["Action 1", "Action 2"]
        },
        "quinn_insights": {
            "qualification_quality": 7,
            "missed_opportunities": ["opportunity 1"],
            "strengths": ["strength 1", "strength 2"]
        },
        "analysis_confidence": 8
    },
    "analysis_metadata": {
        "analysis_timestamp": "ISO timestamp",
        "analysis_version": "2.1-dual-output",
        "analysis_confidence": 8
    }
}

## SIMPLE SUMMARY GUIDELINES:
- **core_talking_points**: 3-5 key themes/pain points as simple strings
- **telnyx_products**: Only include products ACTUALLY discussed (valid: voice, messaging, wireless, voice_ai, numbers, storage, verify, connections)
- **use_cases**: 2-3 specific business applications as simple strings
- **conversation_focus**: Single string describing primary focus (not nested object)
- **ae_sentiment**: Just excitement_level and confidence_level (1-10 each)
- **prospect_sentiment**: interest_level, engagement_level (1-10), plus buying_signals array
- **next_steps**: category as enum + specific_actions array
- **quinn_insights**: qualification_quality (1-10), missed_opportunities array, strengths array
- **analysis_confidence**: Single number 1-10

## DETAILED ANALYSIS GUIDELINES:
- All numeric scores should be 1-10 where 1 is lowest and 10 is highest
- Be specific and extract actual quotes or details from the transcript where possible
- If information is not available, use empty arrays or null values appropriately

The simple_summary is for quick executive consumption. The detailed_analysis is for deep coaching dives."""


async def run_analysis():
    db = get_db()
    
    # Get Ben Lewell call
    call_row = db.get_call_by_fellow_id('QdZdMHWoec')
    if not call_row:
        print('❌ Call not found')
        return
    
    # Convert sqlite3.Row to dict
    call = dict(call_row)
    
    print(f'✅ Found call: {call["title"]}')
    print(f'   Call ID: {call["id"]}')
    print(f'   Transcript length: {len(call.get("transcript", "") or "")} chars')
    
    transcript = call.get('transcript', '') or ''
    if not transcript or len(transcript) < 100:
        print('❌ Transcript too short or missing')
        return
    
    # Initialize OpenAI client
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        print('❌ OPENAI_API_KEY not set')
        return
    
    config = OpenAIConfig(api_key=api_key)
    client = OpenAIClient(config)
    
    print('\n🤖 Running OpenAI analysis (dual output mode)...')
    result = await client.analyze_call_transcript(transcript, SYSTEM_PROMPT)
    
    print(f'\n✅ Analysis complete!')
    print(f'   Model: {result.model}')
    print(f'   Tokens: {result.usage}')
    print(f'   Processing time: {result.processing_time:.2f}s')
    
    # Parse the JSON response
    try:
        content = result.content
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        analysis = json.loads(content.strip())
        
        # Add metadata
        analysis['analysis_metadata'] = analysis.get('analysis_metadata', {})
        analysis['analysis_metadata'].update({
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_version': '2.1-dual-output',
            'llm_model_used': result.model,
            'processing_time_seconds': result.processing_time,
            'token_usage': result.usage,
            'provider': 'openai'
        })
        
        # Extract both structures
        detailed = analysis.get('detailed_analysis', {})
        simple = analysis.get('simple_summary', {})
        
        print('\n' + '='*70)
        print('📊 DUAL OUTPUT ANALYSIS RESULTS')
        print('='*70)
        
        # =====================================================================
        # SIMPLE SUMMARY (Quick View)
        # =====================================================================
        print('\n' + '─'*70)
        print('📋 SIMPLE SUMMARY (9-Category Dashboard View)')
        print('─'*70)
        
        print('\n1️⃣  CORE TALKING POINTS:')
        for point in simple.get('core_talking_points', []):
            print(f'    • {point}')
        
        print(f'\n2️⃣  TELNYX PRODUCTS: {simple.get("telnyx_products", [])}')
        
        print('\n3️⃣  USE CASES:')
        for uc in simple.get('use_cases', []):
            print(f'    • {uc}')
        
        print(f'\n4️⃣  CONVERSATION FOCUS: {simple.get("conversation_focus", "N/A")}')
        
        ae_sent = simple.get('ae_sentiment', {})
        print(f'\n5️⃣  AE SENTIMENT:')
        print(f'    Excitement: {ae_sent.get("excitement_level", "N/A")}/10')
        print(f'    Confidence: {ae_sent.get("confidence_level", "N/A")}/10')
        
        prospect_sent = simple.get('prospect_sentiment', {})
        print(f'\n6️⃣  PROSPECT SENTIMENT:')
        print(f'    Interest: {prospect_sent.get("interest_level", "N/A")}/10')
        print(f'    Engagement: {prospect_sent.get("engagement_level", "N/A")}/10')
        print(f'    Buying Signals: {prospect_sent.get("buying_signals", [])}')
        
        ns = simple.get('next_steps', {})
        print(f'\n7️⃣  NEXT STEPS:')
        print(f'    Category: {ns.get("category", "N/A")}')
        print(f'    Actions: {ns.get("specific_actions", [])}')
        
        quinn = simple.get('quinn_insights', {})
        print(f'\n8️⃣  QUINN INSIGHTS:')
        print(f'    Qualification Quality: {quinn.get("qualification_quality", "N/A")}/10')
        print(f'    Strengths: {quinn.get("strengths", [])}')
        print(f'    Missed Opportunities: {quinn.get("missed_opportunities", [])}')
        
        print(f'\n9️⃣  ANALYSIS CONFIDENCE: {simple.get("analysis_confidence", "N/A")}/10')
        
        # =====================================================================
        # DETAILED ANALYSIS (Deep Dive)
        # =====================================================================
        print('\n' + '─'*70)
        print('🔬 DETAILED ANALYSIS (Deep Dive View)')
        print('─'*70)
        
        # Core talking points detail
        tp = detailed.get('core_talking_points', {})
        print('\n🎯 CORE TALKING POINTS (Detailed):')
        print(f'   Pain points: {tp.get("primary_pain_points", [])}')
        print(f'   AE talking points: {tp.get("ae_key_talking_points", [])}')
        print(f'   Pain point alignment: {tp.get("pain_point_alignment", "N/A")}/10')
        print(f'   Most compelling: {tp.get("most_compelling_point", "N/A")}')
        
        # Products detail
        prod = detailed.get('telnyx_products', {})
        print('\n📦 TELNYX PRODUCTS (Detailed):')
        print(f'   Products: {prod.get("products_discussed", [])}')
        print(f'   Features: {prod.get("features_highlighted", [])}')
        print(f'   Tech depth: {prod.get("technical_depth", "N/A")}/10')
        print(f'   Product fit: {prod.get("product_fit_assessment", "N/A")}/10')
        
        # Quinn scoring detail
        quinn_detail = detailed.get('quinn_scoring', {})
        print('\n📈 QUINN SCORING (Detailed):')
        print(f'   Need clarity: {quinn_detail.get("need_clarity", "N/A")}/10')
        print(f'   Decision authority: {quinn_detail.get("decision_authority", "N/A")}/10')
        print(f'   Budget availability: {quinn_detail.get("budget_availability", "N/A")}/10')
        print(f'   Timeline urgency: {quinn_detail.get("timeline_urgency", "N/A")}/10')
        print(f'   Champion strength: {quinn_detail.get("champion_strength", "N/A")}/10')
        print(f'   Competition position: {quinn_detail.get("competition_position", "N/A")}/10')
        print(f'   Overall qualification: {quinn_detail.get("overall_qualification", "N/A")}/10')
        print(f'   Notes: {quinn_detail.get("qualification_notes", "N/A")}')
        
        # Next steps detail
        ns_detail = detailed.get('next_steps', {})
        print('\n📋 NEXT STEPS (Detailed):')
        print(f'   Category: {ns_detail.get("next_steps_category", "N/A")}')
        print(f'   Actions: {ns_detail.get("specific_actions", [])}')
        print(f'   Timeline: {ns_detail.get("timeline_details", "N/A")}')
        print(f'   Commitment level: {ns_detail.get("commitment_level", "N/A")}/10')
        print(f'   AE follow-up quality: {ns_detail.get("ae_follow_up_quality", "N/A")}/10')
        
        # =====================================================================
        # STORAGE
        # =====================================================================
        print('\n' + '─'*70)
        print('💾 STORAGE')
        print('─'*70)
        
        # Prepare flattened storage format for existing schema compatibility
        storage_data = prepare_storage_data(analysis, detailed, simple)
        
        # Store in database
        result_id = db.insert_analysis_result(call['id'], storage_data)
        print(f'\n✅ Stored in database with ID: {result_id}')
        
        # Save full JSON (both formats)
        output_file = Path(__file__).parent / 'openai_analysis_result.json'
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f'📄 Full dual-output analysis saved to {output_file}')
        
        # Save simple summary separately for easy access
        simple_file = Path(__file__).parent / 'simple_summary.json'
        with open(simple_file, 'w') as f:
            json.dump(simple, f, indent=2)
        print(f'📄 Simple summary saved to {simple_file}')
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f'\n⚠️ JSON parse error: {e}')
        print(f'Raw response:\n{result.content[:1000]}...')
        return None


def prepare_storage_data(full_analysis: dict, detailed: dict, simple: dict) -> dict:
    """
    Prepare analysis data for database storage.
    Maps dual-output structure to existing schema while preserving both formats.
    """
    metadata = full_analysis.get('analysis_metadata', {})
    
    # Extract from simple summary (matching original PRD spec)
    ae_sentiment = simple.get('ae_sentiment', {})
    prospect_sentiment = simple.get('prospect_sentiment', {})
    next_steps = simple.get('next_steps', {})
    quinn_insights = simple.get('quinn_insights', {})
    
    # Extract from detailed for richer fields
    detailed_focus = detailed.get('conversation_focus', {})
    detailed_quinn = detailed.get('quinn_scoring', {})
    
    return {
        # Version indicator
        'analysis_version': '2.1-dual-output',
        
        # Simple summary fields (matching original PRD)
        'core_talking_points': simple.get('core_talking_points', []),
        'telnyx_products': simple.get('telnyx_products', []),
        'use_cases': simple.get('use_cases', []),
        
        # Conversation focus (from simple)
        'conversation_focus': {
            'primary': simple.get('conversation_focus', ''),
            'secondary': detailed_focus.get('secondary_focus', []),
            'time_distribution': {}
        },
        
        # AE sentiment (from simple)
        'ae_sentiment': {
            'excitement_level': ae_sentiment.get('excitement_level'),
            'confidence_level': ae_sentiment.get('confidence_level'),
            'engagement_level': detailed.get('sentiment_analysis', {}).get('ae_sentiment', 7),
            'notes': ''
        },
        
        # Prospect sentiment (from simple) 
        'prospect_sentiment': {
            'excitement_level': prospect_sentiment.get('interest_level'),
            'confidence_level': prospect_sentiment.get('engagement_level'),
            'engagement_level': prospect_sentiment.get('engagement_level'),
            'buying_signals': prospect_sentiment.get('buying_signals', []),
            'concerns': []
        },
        
        # Next steps (from simple)
        'next_steps': {
            'category': next_steps.get('category', 'unclear'),
            'specific_actions': next_steps.get('specific_actions', []),
            'probability': detailed.get('next_steps', {}).get('commitment_level', 5),
            'timeline': detailed.get('next_steps', {}).get('timeline_details', '')
        },
        
        # Quinn insights (from simple + detailed)
        'quinn_insights': {
            'qualification_quality': quinn_insights.get('qualification_quality'),
            'discovery_effectiveness': detailed_quinn.get('need_clarity', 5),
            'relationship_building': detailed_quinn.get('champion_strength', 5),
            'product_positioning': detailed.get('telnyx_products', {}).get('product_fit_assessment', 5),
            'missed_opportunities': quinn_insights.get('missed_opportunities', []),
            'strengths': quinn_insights.get('strengths', [])
        },
        
        # Metadata
        'analysis_metadata': {
            'analysis_confidence': simple.get('analysis_confidence', 7),
            'analysis_version': '2.1-dual-output',
            'llm_model_used': metadata.get('llm_model_used'),
            'processing_time_seconds': metadata.get('processing_time_seconds'),
            'token_usage': metadata.get('token_usage', {})
        },
        
        # Preserve full structures for retrieval
        'detailed_analysis': detailed,
        'simple_summary': simple,
        
        # Legacy metadata passthrough
        'metadata': metadata
    }


if __name__ == '__main__':
    asyncio.run(run_analysis())
