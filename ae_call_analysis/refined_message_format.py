#!/usr/bin/env python3
"""
Refined Call Intelligence Message Format
Uses actual analysis data structure for real insights
"""

def generate_refined_call_alert(call_data, analysis_data):
    """Generate refined Slack message using real analysis insights"""
    
    # Extract real data points
    prospect_name = call_data.get('prospect_name', 'Unknown')
    ae_name = call_data.get('ae_name', '[AE TBD]')
    call_date = call_data.get('call_date', '2026-02-27')[:10]
    
    # Performance scores
    interest = analysis_data.get('prospect_interest_level', 0)
    ae_excitement = analysis_data.get('ae_excitement_level', 0) 
    quinn_quality = analysis_data.get('quinn_qualification_quality', 0)
    confidence = analysis_data.get('analysis_confidence', 0)
    
    # Core insights
    pain_points = analysis_data.get('core_talking_points', [])
    use_cases = analysis_data.get('use_cases', [])
    products = analysis_data.get('telnyx_products', [])
    focus = analysis_data.get('conversation_focus_primary', 'unknown')
    
    # Buying signals and concerns
    buying_signals = analysis_data.get('prospect_buying_signals', [])
    concerns = analysis_data.get('prospect_concerns', [])
    
    # Next steps
    next_category = analysis_data.get('next_steps_category', 'unknown')
    next_actions = analysis_data.get('next_steps_actions', [])
    
    # Quinn insights
    quinn_missed = analysis_data.get('quinn_missed_opportunities', [])
    quinn_strengths = analysis_data.get('quinn_strengths', [])
    
    # Priority determination
    priority_emoji = "🔥" if interest >= 8 else "⚡" if interest >= 6 else "📞"
    urgency_flag = "🚨 HIGH PRIORITY" if interest >= 8 and ae_excitement >= 8 else ""
    
    message = f"""## {priority_emoji} **CALL INTELLIGENCE ALERT** {urgency_flag}

**🆕 QUALIFICATION CALL ANALYZED**
**Prospect:** {prospect_name} | **AE:** {ae_name} | **Date:** {call_date}

---

### **📊 PERFORMANCE SCORES**
🔥 **Interest:** {interest}/10 | 🎯 **AE Excitement:** {ae_excitement}/10 | 📋 **Quinn Quality:** {quinn_quality}/10 | ✅ **Confidence:** {confidence}/10

---

### **💡 REAL CALL INSIGHTS**

**🔴 Pain Points Identified:**"""
    
    for pain in pain_points[:3]:  # Top 3 pain points
        message += f"\n• {pain}"
    
    if not pain_points:
        message += "\n• No specific pain points identified"
    
    message += f"""

**🎯 Use Cases Discussed:**"""
    
    for use_case in use_cases[:3]:  # Top 3 use cases
        message += f"\n• {use_case}"
    
    if not use_cases:
        message += "\n• General telephony discussion"
    
    message += f"""

**💡 Telnyx Products in Play:**"""
    
    for product in products[:3]:  # Top 3 products
        message += f"\n• {product}"
    
    if not products:
        message += "\n• General Telnyx services"
    
    message += f"""

**🗣️ Conversation Style:** {focus.title()} ({get_focus_insight(focus)})"""
    
    if buying_signals:
        message += f"""

**📈 Buying Signals Detected:**"""
        for signal in buying_signals[:3]:
            message += f"\n• {signal}"
    
    if concerns:
        message += f"""

**⚠️ Prospect Concerns:**"""
        for concern in concerns[:3]:
            message += f"\n• {concern}"
    
    message += f"""

---

### **🚀 NEXT STEPS ANALYSIS**
**Category:** {next_category.replace('_', ' ').title()}"""
    
    if next_actions:
        message += f"\n**Specific Actions:**"
        for action in next_actions[:3]:
            message += f"\n• {action}"
    
    message += f"""

---

### **📋 QUINN QUALIFICATION REVIEW**
**Overall Quality:** {quinn_quality}/10"""
    
    if quinn_strengths:
        message += f"\n**✅ AE Strengths:**"
        for strength in quinn_strengths[:2]:
            message += f"\n• {strength}"
    
    if quinn_missed:
        message += f"\n**⚠️ Missed Opportunities:**"
        for missed in quinn_missed[:2]:
            message += f"\n• {missed}"
    
    message += f"""

---

### **🎯 STAKEHOLDER ACTIONS**

{generate_stakeholder_insights(analysis_data, call_data)}

---

### **🔗 QUICK ACCESS**
📞 Fellow Recording | 📋 Salesforce Contact | 📊 Full Analysis Report

_Call ID: {call_data.get('id', 'N/A')} | Quinn: {quinn_quality}/10 | Focus: {focus.title()} | {get_timeline_insight(next_category)}_"""

    return message

def get_focus_insight(focus):
    """Get insight about conversation focus"""
    insights = {
        'discovery': 'AE uncovering needs',
        'demo': 'Product demonstration mode', 
        'pricing': 'Commercial discussion',
        'technical': 'Technical deep-dive',
        'closing': 'Moving to decision',
        'objection_handling': 'Addressing concerns'
    }
    return insights.get(focus, 'General discussion')

def get_timeline_insight(next_category):
    """Get timeline insight from next steps"""
    timelines = {
        'moving_forward': 'Active progression',
        'follow_up_scheduled': 'Scheduled continuation',
        'evaluation': 'Evaluation phase',
        'stalled': 'Pipeline risk',
        'lost': 'Deal closed-lost'
    }
    return timelines.get(next_category, 'Status unclear')

def generate_stakeholder_insights(analysis_data, call_data):
    """Generate specific insights for each stakeholder"""
    
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
    mkt_insight = f"📊 Pain point trend: {primary_pain.split('.')[0].lower()}"
    
    # Product insight  
    primary_product = products[0] if products else "core telephony"
    prod_insight = f"🔧 Product interest: {primary_product}"
    
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

# Test with real data
if __name__ == "__main__":
    # Sample data structure matching database
    sample_call = {
        'id': 8,
        'prospect_name': 'Zack M',
        'ae_name': 'Sales Rep',
        'call_date': '2026-02-27'
    }
    
    sample_analysis = {
        'prospect_interest_level': 7,
        'ae_excitement_level': 8,
        'quinn_qualification_quality': 7,
        'analysis_confidence': 8,
        'core_talking_points': [
            'Unreliable call connectivity with Cloud Talk',
            'Missed calls affecting revenue and brand image', 
            'Need for reliable telephony solution'
        ],
        'use_cases': [
            'Handling healthcare inquiries via calls',
            'Improving call reliability and customer trust'
        ],
        'telnyx_products': [
            'Telnyx telephony services',
            'Integration with Respond IO'
        ],
        'conversation_focus_primary': 'discovery',
        'prospect_buying_signals': [
            'Open to changing phone numbers',
            'Seeking stable telephony solution'
        ],
        'prospect_concerns': [],
        'next_steps_category': 'follow_up_scheduled',
        'next_steps_actions': [
            'Prospect to discuss with CEO about changing phone numbers',
            'Potential follow-up call with CEO'
        ],
        'quinn_missed_opportunities': [],
        'quinn_strengths': ['Good discovery of pain points']
    }
    
    message = generate_refined_call_alert(sample_call, sample_analysis)
    print(message)