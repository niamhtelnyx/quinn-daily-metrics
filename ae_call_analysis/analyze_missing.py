#!/usr/bin/env python3
"""
Analyze calls that are missing analysis results
"""
import asyncio
import sys
import json
import os
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from database.database import get_db
from services.openai_client import OpenAIClient
from dataclasses import dataclass

@dataclass
class OpenAIConfig:
    api_key: str
    model: str = 'gpt-4o'
    max_tokens: int = 4096
    temperature: float = 0.1
    timeout: float = 120.0
    max_retries: int = 3

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

The simple_summary is for quick executive consumption. The detailed_analysis is for deep coaching dives."""


def prepare_storage_data(full_analysis: dict, detailed: dict, simple: dict) -> dict:
    """Prepare analysis data for database storage."""
    metadata = full_analysis.get('analysis_metadata', {})
    
    ae_sentiment = simple.get('ae_sentiment', {})
    prospect_sentiment = simple.get('prospect_sentiment', {})
    next_steps = simple.get('next_steps', {})
    quinn_insights = simple.get('quinn_insights', {})
    
    detailed_focus = detailed.get('conversation_focus', {})
    detailed_quinn = detailed.get('quinn_scoring', {})
    
    return {
        'analysis_version': '2.1-dual-output',
        'core_talking_points': simple.get('core_talking_points', []),
        'telnyx_products': simple.get('telnyx_products', []),
        'use_cases': simple.get('use_cases', []),
        'conversation_focus': {
            'primary': simple.get('conversation_focus', ''),
            'secondary': detailed_focus.get('secondary_focus', []),
            'time_distribution': {}
        },
        'ae_sentiment': {
            'excitement_level': ae_sentiment.get('excitement_level'),
            'confidence_level': ae_sentiment.get('confidence_level'),
            'engagement_level': detailed.get('sentiment_analysis', {}).get('ae_sentiment', 7),
            'notes': ''
        },
        'prospect_sentiment': {
            'excitement_level': prospect_sentiment.get('interest_level'),
            'confidence_level': prospect_sentiment.get('engagement_level'),
            'engagement_level': prospect_sentiment.get('engagement_level'),
            'buying_signals': prospect_sentiment.get('buying_signals', []),
            'concerns': []
        },
        'next_steps': {
            'category': next_steps.get('category', 'unclear'),
            'specific_actions': next_steps.get('specific_actions', []),
            'probability': detailed.get('next_steps', {}).get('commitment_level', 5),
            'timeline': detailed.get('next_steps', {}).get('timeline_details', '')
        },
        'quinn_insights': {
            'qualification_quality': quinn_insights.get('qualification_quality'),
            'discovery_effectiveness': detailed_quinn.get('need_clarity', 5),
            'relationship_building': detailed_quinn.get('champion_strength', 5),
            'product_positioning': detailed.get('telnyx_products', {}).get('product_fit_assessment', 5),
            'missed_opportunities': quinn_insights.get('missed_opportunities', []),
            'strengths': quinn_insights.get('strengths', [])
        },
        'analysis_metadata': {
            'analysis_confidence': simple.get('analysis_confidence', 7),
            'analysis_version': '2.1-dual-output',
            'llm_model_used': metadata.get('llm_model_used'),
            'processing_time_seconds': metadata.get('processing_time_seconds'),
            'token_usage': metadata.get('token_usage', {})
        },
        'detailed_analysis': detailed,
        'simple_summary': simple,
        'metadata': metadata
    }


async def analyze_call(call_id: int):
    """Analyze a specific call by call_id"""
    db = get_db()
    
    # Get call
    call = None
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM calls WHERE id = ?', (call_id,))
        call = cursor.fetchone()
    
    if not call:
        print(f'❌ Call {call_id} not found')
        return
    
    call = dict(call)
    print(f'📞 Analyzing: {call["title"]}')
    print(f'   Prospect: {call["prospect_name"]}')
    print(f'   Transcript: {len(call.get("transcript", "") or "")} chars')
    
    transcript = call.get('transcript', '') or ''
    if len(transcript) < 100:
        print('❌ Transcript too short')
        return
    
    # Initialize OpenAI client
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        print('❌ OPENAI_API_KEY not set')
        return
    
    config = OpenAIConfig(api_key=api_key)
    client = OpenAIClient(config)
    
    print('🤖 Running OpenAI dual analysis...')
    start_time = time.time()
    
    result = await client.analyze_call_transcript(transcript, SYSTEM_PROMPT)
    
    processing_time = time.time() - start_time
    print(f'✅ Analysis complete in {processing_time:.2f}s')
    print(f'   Model: {result.model}')
    print(f'   Tokens: {result.usage}')
    
    # Parse JSON
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
    
    detailed = analysis.get('detailed_analysis', {})
    simple = analysis.get('simple_summary', {})
    
    # Print quick summary
    print('\n📊 QUICK SUMMARY:')
    print(f'   Products: {simple.get("telnyx_products", [])}')
    print(f'   Focus: {simple.get("conversation_focus", "N/A")}')
    print(f'   Next Steps: {simple.get("next_steps", {}).get("category", "N/A")}')
    print(f'   Confidence: {simple.get("analysis_confidence", "N/A")}/10')
    
    # Store in database
    storage_data = prepare_storage_data(analysis, detailed, simple)
    result_id = db.insert_analysis_result(call_id, storage_data)
    db.mark_call_processed(call_id)
    
    print(f'\n💾 Stored with result_id: {result_id}')
    
    return {
        'call_id': call_id,
        'result_id': result_id,
        'model': result.model,
        'input_tokens': result.usage.get('input_tokens', 0),
        'output_tokens': result.usage.get('output_tokens', 0),
        'processing_time': processing_time,
        'simple_summary': simple
    }


async def main():
    # Analyze Zack M (call_id 8) - missing analysis
    result = await analyze_call(8)
    
    if result:
        print('\n' + '='*60)
        print('✅ BATCH 2 COMPLETION')
        print('='*60)
        print(f'Zack M analysis complete!')
        print(f'   Tokens: {result["input_tokens"]} in / {result["output_tokens"]} out')
        print(f'   Time: {result["processing_time"]:.2f}s')
        
        # Save result
        with open('zack_m_analysis.json', 'w') as f:
            json.dump(result, f, indent=2)


if __name__ == '__main__':
    asyncio.run(main())
