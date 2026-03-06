#!/usr/bin/env python3
"""
Enhanced AI analysis with FULL content processing
Handles long transcripts up to 100k+ characters
"""

import os
import openai
from dotenv import load_dotenv
from content_parser import parse_meeting_name

def chunk_content(content, max_chunk_size=80000, overlap=2000):
    """
    Split very long content into overlapping chunks for analysis
    """
    if len(content) <= max_chunk_size:
        return [content]
    
    chunks = []
    start = 0
    
    while start < len(content):
        end = start + max_chunk_size
        
        # Try to break at sentence boundary
        if end < len(content):
            # Look for sentence ending in last 1000 chars
            chunk_end = content.rfind('.', end - 1000, end)
            if chunk_end == -1:
                chunk_end = content.rfind('\n', end - 500, end)
            if chunk_end != -1:
                end = chunk_end + 1
        
        chunk = content[start:end]
        chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(content):
            break
    
    return chunks

def analyze_single_chunk(content_chunk, meeting_name, chunk_number=1, total_chunks=1):
    """
    Analyze a single chunk of content
    """
    load_dotenv('.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    
    client = openai.OpenAI(api_key=api_key)
    
    prospect_name, company_name = parse_meeting_name(meeting_name)
    
    chunk_info = f" (Part {chunk_number} of {total_chunks})" if total_chunks > 1 else ""
    
    prompt = f"""Analyze this sales meeting content and extract key insights{chunk_info}:

MEETING: {meeting_name}
CONTENT LENGTH: {len(content_chunk):,} characters
CONTENT: {content_chunk}

Please provide detailed analysis:

1. COMPANY DESCRIPTION for "{company_name}" (the prospect/client, NOT Telnyx):
   - What specific business/industry is {company_name} in?
   - What products/services does {company_name} provide?
   - Who are their customers/target market?
   - What's their business model or revenue approach?
   - Geographic focus if mentioned
   - Format as detailed description (150-300 chars)

2. PAIN POINTS (all challenges/problems mentioned):
   - Technical challenges and limitations
   - Business problems and frustrations  
   - Implementation concerns
   - Cost or efficiency issues
   - Integration difficulties
   - Be specific and quote actual concerns when possible

3. TELNYX PRODUCTS DISCUSSED:
   - Which Telnyx APIs, services, or solutions were mentioned?
   - Specific use cases or applications discussed
   - Technical requirements or specifications
   - Volume or scale requirements mentioned

4. NEXT STEPS AND TIMELINE:
   - Specific follow-up actions planned
   - Technical evaluations or demos scheduled
   - Decision timelines and milestones
   - Who is responsible for what
   - Budget or procurement processes mentioned

5. KEY STAKEHOLDERS:
   - Names, titles, and email addresses mentioned
   - Decision makers and influencers identified
   - Technical contacts vs business contacts
   - External vendors or partners discussed

6. BUSINESS CONTEXT:
   - Current solutions they're using
   - Why they're evaluating new options
   - Success metrics or KPIs mentioned
   - Competitive alternatives discussed

Format as JSON:
{{
  "company_description": "detailed business description",
  "pain_points": ["specific pain point 1", "specific pain point 2", "..."],
  "products_discussed": ["Telnyx product 1", "Telnyx product 2", "..."],
  "next_steps": ["specific next step 1", "specific next step 2", "..."],
  "stakeholders": ["name <email@domain.com>", "name <email@domain.com>"],
  "business_context": ["current solution", "evaluation reason", "success metrics"],
  "technical_requirements": ["requirement 1", "requirement 2"],
  "timeline": ["milestone 1", "milestone 2"]
}}

Be comprehensive and specific. Extract actual quotes and details from the content."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use best model for comprehensive analysis
            messages=[
                {"role": "system", "content": "You are an expert sales intelligence analyst who extracts comprehensive, actionable insights from sales meeting transcripts. Focus on specific details, quotes, and business context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,  # Increased for detailed analysis
            temperature=0.2
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"  ⚠️ OpenAI API error for chunk {chunk_number}: {str(e)[:50]}")
        return None

def merge_chunk_analyses(chunk_results):
    """
    Merge analyses from multiple chunks into comprehensive insights
    """
    import json
    
    merged = {
        'company_description': '',
        'pain_points': [],
        'products_discussed': [],
        'next_steps': [],
        'stakeholders': [],
        'business_context': [],
        'technical_requirements': [],
        'timeline': []
    }
    
    company_descriptions = []
    
    for result in chunk_results:
        if not result:
            continue
            
        try:
            # Clean and parse JSON
            clean_result = result.strip()
            if clean_result.startswith('```json'):
                clean_result = clean_result[7:]
            if clean_result.startswith('```'):
                clean_result = clean_result[3:]
            if clean_result.endswith('```'):
                clean_result = clean_result[:-3]
            
            analysis = json.loads(clean_result)
            
            # Collect company descriptions
            if analysis.get('company_description'):
                company_descriptions.append(analysis['company_description'])
            
            # Merge lists, avoiding duplicates
            for key in ['pain_points', 'products_discussed', 'next_steps', 'stakeholders', 
                       'business_context', 'technical_requirements', 'timeline']:
                items = analysis.get(key, [])
                for item in items:
                    if item and item not in merged[key]:
                        merged[key].append(item)
                        
        except json.JSONDecodeError as e:
            print(f"  ⚠️ JSON parsing error: {str(e)[:50]}")
            continue
    
    # Use the most detailed company description
    if company_descriptions:
        merged['company_description'] = max(company_descriptions, key=len)
    
    return merged

def get_full_content_ai_analysis(content, meeting_name):
    """
    Analyze full meeting content, chunking if necessary
    Returns: (insights_dict, company_description)
    """
    
    print(f"  📊 Analyzing {len(content):,} characters with AI...")
    
    # Determine if we need to chunk
    max_single_analysis = 80000  # Conservative limit for single analysis
    
    if len(content) <= max_single_analysis:
        # Single analysis for shorter content
        print(f"  🤖 Single analysis (full content)")
        result = analyze_single_chunk(content, meeting_name)
        
        if result:
            try:
                import json
                clean_result = result.strip()
                if clean_result.startswith('```json'):
                    clean_result = clean_result[7:]
                if clean_result.startswith('```'):
                    clean_result = clean_result[3:]
                if clean_result.endswith('```'):
                    clean_result = clean_result[:-3]
                
                analysis = json.loads(clean_result)
                
                # Convert to our expected format
                insights = {
                    'pain_points': analysis.get('pain_points', [])[:5],
                    'products': analysis.get('products_discussed', [])[:3],
                    'next_steps': analysis.get('next_steps', [])[:5],
                    'attendees': analysis.get('stakeholders', [])[:5],
                    'business_context': analysis.get('business_context', [])[:3],
                    'technical_requirements': analysis.get('technical_requirements', [])[:3]
                }
                
                company_desc = analysis.get('company_description', 'technology company')
                
                return insights, company_desc
                
            except json.JSONDecodeError:
                print(f"  ⚠️ JSON parsing failed, using fallback")
                
    else:
        # Multi-chunk analysis for long content
        chunks = chunk_content(content, max_single_analysis)
        print(f"  🧩 Multi-chunk analysis ({len(chunks)} chunks)")
        
        chunk_results = []
        for i, chunk in enumerate(chunks, 1):
            print(f"    📄 Analyzing chunk {i}/{len(chunks)} ({len(chunk):,} chars)")
            result = analyze_single_chunk(chunk, meeting_name, i, len(chunks))
            chunk_results.append(result)
        
        # Merge results
        merged_analysis = merge_chunk_analyses(chunk_results)
        
        # Convert to our expected format
        insights = {
            'pain_points': merged_analysis['pain_points'][:5],
            'products': merged_analysis['products_discussed'][:3], 
            'next_steps': merged_analysis['next_steps'][:5],
            'attendees': merged_analysis['stakeholders'][:5],
            'business_context': merged_analysis['business_context'][:3],
            'technical_requirements': merged_analysis['technical_requirements'][:3]
        }
        
        company_desc = merged_analysis['company_description'] or 'technology company'
        
        return insights, company_desc
    
    # Fallback to old method
    from content_parser import extract_insights_from_content
    return extract_insights_from_content(content), "technology company"

# Test the enhanced analysis
def test_full_content_analysis():
    """Test with a realistic long transcript"""
    
    # Simulate a long meeting transcript
    test_content = """
    Meeting with Afranga team about their peer-to-peer lending platform for European investors.
    
    Present: John Smith (CEO, john@afranga.com), Sarah Johnson (CTO, sarah.tech@afranga.com)
    
    Discussion Overview:
    Afranga operates a crowdfunding platform that connects European retail investors with high-growth company loans. 
    Their platform allows investors to start with as little as 10 euros and build diversified loan portfolios.
    They focus on vetted companies primarily in Bulgaria and expanding across Eastern Europe.
    
    Key Pain Points Discussed:
    1. High payment processing fees are eating into investor returns (currently paying 3.2% per transaction)
    2. Settlement times are too slow - investors wait 3-5 business days for payouts
    3. SMS notifications for loan updates are unreliable with current provider
    4. Voice support for investor questions is expensive with current telecom provider
    5. Integration challenges with their existing CRM and loan management system
    
    Technical Requirements:
    - Need to process 50,000+ monthly transactions
    - Require instant settlement capabilities for investor confidence
    - Want automated SMS for loan status updates (principal payments, defaults, etc.)
    - Need call center capabilities for investor support in Bulgarian and English
    - API integration with their existing loan management platform
    
    Telnyx Solutions Discussed:
    - Voice API for cost-effective customer support center
    - SMS API for reliable loan notifications and investor updates
    - Payments API for reduced transaction costs and faster settlements
    - SIP trunking for their Sofia office (25 agents)
    
    Business Context:
    - Currently using Stripe for payments (too expensive at scale)
    - Using Twilio for SMS (delivery issues in Eastern Europe)
    - Manual voice support through local telecom (expensive, limited hours)
    - Processing about 2.8M euros monthly in loan investments
    - Target: 10M euros monthly by end of 2026
    - Success metrics: Transaction cost under 1.5%, settlement under 24 hours
    
    Next Steps Discussed:
    1. Technical demo of Payments API integration - scheduled for next Tuesday
    2. SMS delivery testing in Bulgaria and Romania markets
    3. Voice API trial with 5-agent pilot program
    4. Pricing proposal for 50k+ monthly transaction volume
    5. Integration timeline discussion with Sarah's development team
    6. Decision timeline: prototype by March 15, full implementation by April 30
    
    Competitive Context:
    - Evaluated Vonage (too expensive for voice)
    - Considered staying with Stripe (but costs prohibitive at target scale)
    - Looking at local Bulgarian providers (limited international capabilities)
    
    Budget and Procurement:
    - Budget approved for up to 50,000 euros annual communications spend
    - Procurement process requires 3 vendor quotes (Telnyx, Vonage, local provider)
    - Final decision by John Smith (CEO) with technical approval from Sarah Johnson
    - Implementation budget separate (100,000 euros approved for Q2)
    
    Decision Factors:
    - Cost savings vs current solutions (minimum 30% reduction required)
    - Reliability in Eastern European markets
    - API quality and developer experience
    - Support quality and response times
    - Regulatory compliance for financial services in EU
    """ * 5  # Multiply to create a longer transcript
    
    meeting_name = "Afranga Crowdfunding Platform -- Telnyx Integration Discussion"
    
    print("🧪 TESTING FULL CONTENT ANALYSIS")
    print("=" * 35)
    print(f"📊 Test content: {len(test_content):,} characters")
    
    insights, company_desc = get_full_content_ai_analysis(test_content, meeting_name)
    
    print(f"\n🏢 Company Description: {company_desc}")
    print(f"\n🔴 Pain Points Found: {len(insights['pain_points'])}")
    for i, pain in enumerate(insights['pain_points'], 1):
        print(f"  {i}. {pain}")
    
    print(f"\n💡 Products Discussed: {len(insights['products'])}")
    for product in insights['products']:
        print(f"  • {product}")
    
    print(f"\n🚀 Next Steps: {len(insights['next_steps'])}")
    for step in insights['next_steps']:
        print(f"  • {step}")

if __name__ == "__main__":
    test_full_content_analysis()