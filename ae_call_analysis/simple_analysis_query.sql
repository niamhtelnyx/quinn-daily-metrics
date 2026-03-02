-- Simple query to see all 9 analysis prompt answers
-- Usage: cd ae_call_analysis && sqlite3 ae_call_analysis.db < simple_analysis_query.sql

.mode box
.headers on

SELECT 
    'Call ' || ar.call_id || ': ' || c.prospect_name as "Call",
    
    -- 9 Core Analysis Categories
    ar.core_talking_points as "1_Talking_Points",
    ar.telnyx_products as "2_Products", 
    ar.use_cases as "3_Use_Cases",
    ar.conversation_focus_primary as "4_Focus",
    ar.ae_excitement_level || '/10' as "5_AE_Sentiment",
    ar.prospect_interest_level || '/10' as "6_Prospect_Sentiment", 
    ar.next_steps_category as "7_Next_Steps",
    ar.next_steps_timeline as "8_Timeline",
    ar.analysis_confidence || '/10' as "9_Confidence",
    
    -- Bonus: Quinn Score
    ar.quinn_qualification_quality || '/10' as "Quinn_Score"
    
FROM analysis_results ar
JOIN calls c ON ar.call_id = c.id  
ORDER BY ar.created_at DESC;