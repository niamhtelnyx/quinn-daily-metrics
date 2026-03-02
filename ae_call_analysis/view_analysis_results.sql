-- Query to view all 9 analysis prompt categories in readable format
-- Run with: cd ae_call_analysis && sqlite3 ae_call_analysis.db < view_analysis_results.sql

.mode column
.headers on
.width 15 50

SELECT 
    -- Call identification
    ar.call_id,
    c.prospect_name,
    c.title as call_title,
    
    -- 1. CORE TALKING POINTS & PAIN POINTS
    json_extract(ar.core_talking_points, '$') as "1_Core_Talking_Points",
    
    -- 2. TELNYX PRODUCTS DISCUSSED
    json_extract(ar.telnyx_products, '$') as "2_Telnyx_Products", 
    
    -- 3. USE CASES
    json_extract(ar.use_cases, '$') as "3_Use_Cases",
    
    -- 4. CONVERSATION FOCUS
    ar.conversation_focus_primary || ' + ' || 
    json_extract(ar.conversation_focus_secondary, '$') as "4_Conversation_Focus",
    
    -- 5. AE SENTIMENT (1-10)
    'Excitement: ' || ar.ae_excitement_level || 
    ', Confidence: ' || ar.ae_confidence_level ||
    ', Notes: ' || COALESCE(ar.ae_sentiment_notes, 'None') as "5_AE_Sentiment",
    
    -- 6. PROSPECT SENTIMENT (1-10)  
    'Interest: ' || ar.prospect_interest_level ||
    ', Engagement: ' || ar.prospect_engagement_level ||
    ', Signals: ' || json_extract(ar.prospect_buying_signals, '$') ||
    ', Concerns: ' || json_extract(ar.prospect_concerns, '$') as "6_Prospect_Sentiment",
    
    -- 7. NEXT STEPS CLASSIFICATION
    ar.next_steps_category || ' (' || ar.next_steps_probability || '% prob)' as "7_Next_Steps_Category",
    
    -- 8. SPECIFIC ACTIONS & TIMELINE
    json_extract(ar.next_steps_actions, '$') || 
    ' | Timeline: ' || COALESCE(ar.next_steps_timeline, 'TBD') as "8_Actions_Timeline",
    
    -- 9. ANALYSIS CONFIDENCE SCORE
    ar.analysis_confidence || '/10' as "9_Analysis_Confidence",
    
    -- BONUS: QUINN QUALIFICATION SCORING
    'Quality: ' || ar.quinn_qualification_quality || '/10, ' ||
    'Strengths: ' || json_extract(ar.quinn_strengths, '$') || ', ' ||
    'Missed: ' || json_extract(ar.quinn_missed_opportunities, '$') as "Quinn_Insights",
    
    -- METADATA
    ar.llm_model_used,
    ar.created_at
    
FROM analysis_results ar
JOIN calls c ON ar.call_id = c.id
ORDER BY ar.created_at DESC;