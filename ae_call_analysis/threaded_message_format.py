#!/usr/bin/env python3
"""
Threaded Call Intelligence Message Format
Main post: Quick summary for channel visibility
Thread: Detailed analysis for deep dive
"""

from datetime import datetime

def generate_summary_and_thread(call_data, analysis_data, sf_event=None, company_intelligence=None):
    """Generate both summary post and detailed thread content"""
    
    # Main post - Quick summary
    main_post = generate_main_summary(call_data, analysis_data, sf_event, company_intelligence)
    
    # Thread reply - Detailed analysis  
    thread_reply = generate_detailed_thread(call_data, analysis_data, sf_event, company_intelligence)
    
    return {
        'main_post': main_post,
        'thread_reply': thread_reply
    }

def generate_main_summary(call_data, analysis_data, sf_event=None, company_intelligence=None):
    """Generate quick summary for main channel post"""
    
    prospect = call_data.get('prospect_name', 'Unknown')
    ae_name = call_data.get('ae_name', '[AE from Fellow]')
    date = str(call_data.get('call_date', '2026-02-27'))[:10]
    
    interest = analysis_data.get('prospect_interest_level', 0)
    ae_excitement = analysis_data.get('ae_excitement_level', 0)
    quinn = analysis_data.get('quinn_qualification_quality', 0)
    
    # Priority emoji based on interest level
    priority_emoji = "🔥" if interest >= 8 else "⚡" if interest >= 6 else "📞"
    
    # Key pain point
    pain_points = analysis_data.get('core_talking_points', [])
    key_pain = pain_points[0] if pain_points else 'General discussion'
    
    # Next step category
    next_category = analysis_data.get('next_steps_category', 'follow_up').replace('_', ' ').title()
    
    # Products discussed
    products = analysis_data.get('telnyx_products', [])
    product_summary = products[0] if products else 'General services'
    
    # Salesforce status with optional link
    event_id = extract_salesforce_id(sf_event, 'event_id', ['id', 'Event_Id']) if sf_event else None
    if event_id:
        sf_base_url = "https://telnyx.lightning.force.com/lightning/r"
        event_url = f"{sf_base_url}/{event_id}/view"
        sf_status = f"[✅ Validated]({event_url})"
    elif sf_event:
        sf_status = "✅ Validated"
    else:
        sf_status = "⚠️ Pending"
    
    # Company intelligence line
    company_line = ""
    if company_intelligence and company_intelligence.get('business_insight'):
        company_line = f"\n**🏢 Company:** {company_intelligence['business_insight']}"
    
    main_post = f"""{priority_emoji} **CALL INTELLIGENCE ALERT**

**{prospect}** | **{ae_name}** | {date}{company_line}

**📊 Scores:** Interest {interest}/10 | AE {ae_excitement}/10 | Quinn {quinn}/10
**🔴 Key Pain:** {key_pain[:80]}{'...' if len(key_pain) > 80 else ''}
**💡 Product Focus:** {product_summary}
**🚀 Next Step:** {next_category}
**🔗 Salesforce:** {sf_status}

_See thread for full analysis and stakeholder actions_ 👇"""

    return main_post

def generate_detailed_thread(call_data, analysis_data, sf_event=None, company_intelligence=None):
    """Generate detailed analysis for thread reply"""
    
    prospect = call_data.get('prospect_name', 'Unknown')
    ae_name = call_data.get('ae_name', '[AE from Fellow]')
    
    interest = analysis_data.get('prospect_interest_level', 0)
    ae_excitement = analysis_data.get('ae_excitement_level', 0)
    quinn = analysis_data.get('quinn_qualification_quality', 0)
    confidence = analysis_data.get('analysis_confidence', 8)
    
    # Detailed insights
    pain_points = analysis_data.get('core_talking_points', [])
    use_cases = analysis_data.get('use_cases', [])
    products = analysis_data.get('telnyx_products', [])
    focus = analysis_data.get('conversation_focus_primary', 'discovery')
    buying_signals = analysis_data.get('prospect_buying_signals', [])
    concerns = analysis_data.get('prospect_concerns', [])
    next_category = analysis_data.get('next_steps_category', 'follow_up')
    next_actions = analysis_data.get('next_steps_actions', [])
    
    thread_content = f"""**📋 DETAILED CALL ANALYSIS: {prospect}**

**💡 COMPLETE INSIGHTS**"""

    # Add company intelligence section
    if company_intelligence:
        company_name = company_intelligence.get('company_name', 'Unknown')
        business_insight = company_intelligence.get('business_insight', '')
        website = company_intelligence.get('website', '')
        industry = company_intelligence.get('industry', '')
        employees = company_intelligence.get('employees')
        
        thread_content += f"""

**🏢 COMPANY INTELLIGENCE: {company_name}**
**Business:** {business_insight}"""
        
        if industry:
            thread_content += f"\n**Industry:** {industry}"
        if employees:
            thread_content += f"\n**Size:** {employees} employees"
        if website:
            thread_content += f"\n**Website:** {website}"

    thread_content += f"""

**🔴 All Pain Points:**"""
    
    for i, pain in enumerate(pain_points[:5], 1):
        thread_content += f"\n{i}. {pain}"
    
    if not pain_points:
        thread_content += "\n• No specific pain points identified"
    
    thread_content += f"""

**🎯 Use Cases Discussed:**"""
    
    for use_case in use_cases[:3]:
        thread_content += f"\n• {use_case}"
    
    if not use_cases:
        thread_content += "\n• General telephony discussion"
    
    thread_content += f"""

**💡 Telnyx Products:**"""
    
    for product in products[:4]:
        thread_content += f"\n• {product}"
    
    if not products:
        thread_content += "\n• General Telnyx services"
    
    thread_content += f"""

**🗣️ Conversation Style:** {focus.title().replace('_', ' ')}"""
    
    if buying_signals:
        thread_content += f"\n\n**📈 Buying Signals:**"
        for signal in buying_signals[:3]:
            thread_content += f"\n• {signal}"
    
    if concerns:
        thread_content += f"\n\n**⚠️ Prospect Concerns:**"
        for concern in concerns[:3]:
            thread_content += f"\n• {concern}"
    
    thread_content += f"""

**🚀 NEXT STEPS**
**Category:** {next_category.replace('_', ' ').title()}"""
    
    if next_actions:
        thread_content += f"\n**Actions:**"
        for action in next_actions[:3]:
            thread_content += f"\n• {action}"
    
    thread_content += f"""

**📋 QUINN REVIEW**
**Quality:** {quinn}/10"""
    
    # Add Quinn insights if available
    strengths = analysis_data.get('quinn_strengths', [])
    missed = analysis_data.get('quinn_missed_opportunities', [])
    
    if strengths:
        thread_content += f"\n**Strengths:** {', '.join(strengths[:2])}"
    if missed:
        thread_content += f"\n**Missed Opportunities:** {', '.join(missed[:2])}"
    
    # Stakeholder actions
    thread_content += f"""

**🎯 STAKEHOLDER ACTIONS**

{generate_stakeholder_insights(analysis_data, call_data)}"""
    
    # Salesforce validation with enhanced hyperlinked formatting
    if sf_event:
        thread_content += f"""

**🔗 SALESFORCE VALIDATION**
{generate_salesforce_links(sf_event)}

_✅ Fully validated via Salesforce event data_"""
    else:
        thread_content += f"""

**⚠️ SALESFORCE STATUS**
• **Event Lookup:** No matching Salesforce event found
• **AE Source:** Extracted from Fellow AI notes
• **Recommendation:** Verify event exists in Salesforce calendar

_Using Fellow data until Salesforce event available_"""
    
    # Processing summary
    thread_content += f"""

**🔄 PROCESSING PIPELINE**
✅ Fellow → {'✅ SF Event' if sf_event else '⚠️ SF Pending'} → ✅ OpenAI → ✅ Intelligence
_Generated: {datetime.now().strftime('%H:%M CST')}_"""
    
    return thread_content

def extract_salesforce_id(sf_event, id_key, fallback_keys=None):
    """
    Safely extract Salesforce ID from event data with fallback options.
    Handles both direct ID fields and nested structures.
    """
    if not sf_event:
        return None
    
    # Try primary key first
    if id_key in sf_event and sf_event[id_key]:
        return sf_event[id_key]
    
    # Try fallback keys
    if fallback_keys:
        for fallback_key in fallback_keys:
            if fallback_key in sf_event and sf_event[fallback_key]:
                return sf_event[fallback_key]
    
    return None

def generate_salesforce_links(sf_event):
    """Generate enhanced Salesforce links with emojis and descriptive text"""
    
    # Salesforce Lightning URL base
    sf_base_url = "https://telnyx.lightning.force.com/lightning/r"
    
    links = []
    
    # Event link
    event_id = extract_salesforce_id(sf_event, 'event_id', ['id', 'Event_Id'])
    if event_id:
        event_url = f"{sf_base_url}/{event_id}/view"
        links.append(f"• [📅 View Event]({event_url})")
    else:
        links.append("• 📅 Event: ID not available")
    
    # Contact link  
    contact_name = sf_event.get('contact_name', 'Unknown Contact')
    contact_id = extract_salesforce_id(sf_event, 'contact_id', ['Contact_Id', 'WhoId'])
    contact_email = sf_event.get('contact_email', '')
    
    if contact_id:
        contact_url = f"{sf_base_url}/{contact_id}/view"
        links.append(f"• [👤 {contact_name}]({contact_url})")
    else:
        # Gracefully handle missing contact ID
        email_suffix = f" ({contact_email})" if contact_email else ""
        links.append(f"• 👤 {contact_name}{email_suffix}")
    
    # Account link
    account_name = sf_event.get('account_name', 'Unknown Account')
    account_id = extract_salesforce_id(sf_event, 'account_id', ['Account_Id', 'WhatId'])
    
    if account_id:
        account_url = f"{sf_base_url}/{account_id}/view"
        links.append(f"• [🏢 {account_name} Account]({account_url})")
    else:
        # Gracefully handle missing account ID
        links.append(f"• 🏢 {account_name} Account")
    
    # AE links
    telnyx_attendees = sf_event.get('telnyx_attendees', [])
    if telnyx_attendees:
        ae_links = []
        for ae in telnyx_attendees:
            if ae and isinstance(ae, dict):
                # If AE data includes ID
                ae_name = ae.get('name', str(ae))
                ae_id = ae.get('id')
                if ae_id:
                    ae_url = f"{sf_base_url}/{ae_id}/view"
                    ae_links.append(f"[👨‍💼 {ae_name}]({ae_url})")
                else:
                    ae_links.append(f"👨‍💼 {ae_name}")
            elif ae:
                # If AE is just a string/name
                ae_links.append(f"👨‍💼 {str(ae)}")
        
        if ae_links:
            links.append(f"• **AEs:** {', '.join(ae_links)}")
    
    # Event date
    event_date = sf_event.get('start_datetime')
    if event_date:
        links.append(f"• 📅 **Date:** {event_date}")
    
    return '\n'.join(links)

def generate_stakeholder_insights(analysis_data, call_data):
    """Generate stakeholder-specific insights"""
    
    interest = analysis_data.get('prospect_interest_level', 0)
    ae_excitement = analysis_data.get('ae_excitement_level', 0)
    quinn_quality = analysis_data.get('quinn_qualification_quality', 0)
    pain_points = analysis_data.get('core_talking_points', [])
    products = analysis_data.get('telnyx_products', [])
    next_category = analysis_data.get('next_steps_category', '')
    
    # Sales Manager insight
    if ae_excitement >= 8 and quinn_quality >= 8:
        mgr_insight = "🌟 Excellent AE performance - use as coaching example"
    elif ae_excitement >= 7:
        mgr_insight = "✅ Good AE engagement - standard qualification"
    elif ae_excitement <= 5:
        mgr_insight = "⚠️ COACHING NEEDED - Low AE engagement detected"
    else:
        mgr_insight = "📈 Review AE discovery technique"
    
    # Marketing insight
    primary_pain = pain_points[0] if pain_points else "general needs"
    mkt_insight = f"📊 Pain trend: {primary_pain.split('.')[0][:50].lower()}..."
    
    # Product insight  
    primary_product = products[0] if products else "core telephony"
    prod_insight = f"🔧 Interest in: {primary_product[:40]}..."
    
    # Executive insight
    if interest >= 8 and 'moving_forward' in next_category:
        exec_insight = "🎯 HOT OPPORTUNITY - Fast-track recommended"
    elif interest >= 7:
        exec_insight = "📈 Qualified prospect - standard progression"
    elif 'stalled' in next_category:
        exec_insight = "⚠️ Pipeline risk - intervention may be needed"
    else:
        exec_insight = "📊 Standard qualification - monitor progression"
    
    return f"""**📈 Sales Manager:** {mgr_insight}
**🎨 Marketing:** {mkt_insight}
**🛠 Product:** {prod_insight}
**👑 Executive:** {exec_insight}"""

def demo_enhanced_salesforce_formatting():
    """Demo the enhanced Salesforce hyperlinked formatting"""
    
    # Sample data with complete Salesforce event info
    sample_call = {
        'id': 4,
        'prospect_name': 'Nick Mihalovich',
        'ae_name': 'Rob Messier',
        'call_date': '2026-02-27'
    }
    
    sample_analysis = {
        'prospect_interest_level': 8,
        'ae_excitement_level': 9,
        'quinn_qualification_quality': 8,
        'analysis_confidence': 9,
        'core_talking_points': [
            'Need for reliable voice solutions',
            'International calling requirements',
            'Integration with existing systems'
        ],
        'use_cases': [
            'Customer support telephony',
            'International business communications'
        ],
        'telnyx_products': [
            'Voice API',
            'SIP Trunking',
            'International Calling'
        ],
        'conversation_focus_primary': 'technical_discovery',
        'prospect_buying_signals': [
            'Ready to start implementation',
            'Budget approved for Q1'
        ],
        'next_steps_category': 'moving_forward',
        'next_steps_actions': [
            'Technical integration call scheduled',
            'Contract review with legal team'
        ]
    }
    
    # Enhanced Salesforce event with complete ID information
    sample_sf_event = {
        'event_id': '00UQk00000OMYzhMAH',
        'contact_name': 'Nick Mihalovich',
        'contact_id': '003Qk00000jw4fsIAA',
        'contact_email': 'nick@rhema-web.com',
        'account_name': 'Rhema Web',
        'account_id': '001Qk00000Xyz123ABC',
        'telnyx_attendees': [
            {'name': 'Rob Messier', 'id': '0058Z000009m5ktQAA'},
            {'name': 'Sarah Johnson', 'id': '0058Z000009m5ktBBB'}
        ],
        'start_datetime': '2026-02-27 14:00:00'
    }
    
    # Demo with complete Salesforce data
    messages_with_sf = generate_summary_and_thread(sample_call, sample_analysis, sample_sf_event)
    
    print("=" * 80)
    print("🔗 ENHANCED SALESFORCE FORMATTING DEMO")
    print("=" * 80)
    
    print("\n📧 MAIN CHANNEL POST (with hyperlinked Salesforce status):")
    print("-" * 60)
    print(messages_with_sf['main_post'])
    
    print("\n🧵 THREAD REPLY (with enhanced Salesforce links):")
    print("-" * 60)
    print(messages_with_sf['thread_reply'])
    
    # Demo graceful handling of missing IDs
    print("\n" + "=" * 80)
    print("🛡️ GRACEFUL DEGRADATION DEMO (Missing IDs)")
    print("=" * 80)
    
    incomplete_sf_event = {
        'event_id': '00UQk00000OMYzhMAH',
        'contact_name': 'Nick Mihalovich',
        # contact_id missing
        'contact_email': 'nick@rhema-web.com',
        'account_name': 'Rhema Web',
        # account_id missing
        'telnyx_attendees': ['Rob Messier'],  # Simple string format
        'start_datetime': '2026-02-27 14:00:00'
    }
    
    messages_partial = generate_summary_and_thread(sample_call, sample_analysis, incomplete_sf_event)
    
    print("\n📧 Main post (with partial data):")
    print("-" * 40)
    print(messages_partial['main_post'])
    
    print("\n🧵 Thread Salesforce section (graceful degradation):")
    print("-" * 40)
    # Extract just the Salesforce section for clarity
    sf_section = generate_salesforce_links(incomplete_sf_event)
    print("**🔗 SALESFORCE VALIDATION**")
    print(sf_section)
    print("\n_✅ Fully validated via Salesforce event data_")
    
    print("\n" + "=" * 80)
    print("✅ ENHANCEMENT COMPLETE")
    print("=" * 80)
    print("🎯 Key Improvements:")
    print("   • Raw Salesforce IDs replaced with hyperlinked text")
    print("   • Emoji icons added for visual appeal")
    print("   • Proper Salesforce Lightning URLs generated")
    print("   • Graceful handling of missing IDs")
    print("   • Backward compatibility maintained")
    print("   • Descriptive link text (not just 'View')")
    print("\n🚀 Ready for deployment!")

def demo_threaded_format():
    """Legacy demo function for backward compatibility"""
    demo_enhanced_salesforce_formatting()

if __name__ == "__main__":
    demo_threaded_format()