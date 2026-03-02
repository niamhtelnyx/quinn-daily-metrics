-- AE Call Analysis System Database Schema
-- SQLite database for storing Fellow calls, Salesforce mappings, and analysis results

-- Core calls table - stores raw Fellow API data
CREATE TABLE calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fellow_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    call_date DATETIME NOT NULL,
    duration_minutes INTEGER,
    ae_name TEXT,
    prospect_name TEXT,
    prospect_company TEXT,
    transcript TEXT,
    fellow_ai_notes TEXT,
    raw_fellow_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- Salesforce mapping table - connects calls to SF opportunities
CREATE TABLE salesforce_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL,
    contact_id TEXT,
    contact_name TEXT,
    opportunity_id TEXT,
    quinn_active_latest DATETIME,
    contact_match_confidence INTEGER, -- 1-10 scale
    mapping_method TEXT, -- 'exact_match', 'fuzzy_match', 'manual'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_id) REFERENCES calls (id) ON DELETE CASCADE
);

-- Analysis results table - stores LLM-generated insights
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL,
    analysis_version TEXT DEFAULT '1.0',
    
    -- Core talking points
    core_talking_points JSON, -- Array of strings
    
    -- Product information
    telnyx_products JSON, -- Array of product names
    use_cases JSON, -- Array of use case strings
    
    -- Conversation focus
    conversation_focus_primary TEXT,
    conversation_focus_secondary JSON, -- Array of secondary focuses
    time_distribution JSON, -- {pricing: 30, technical: 45, etc.}
    
    -- Sentiment analysis
    ae_excitement_level INTEGER, -- 1-10
    ae_confidence_level INTEGER, -- 1-10
    ae_sentiment_notes TEXT,
    
    prospect_interest_level INTEGER, -- 1-10
    prospect_engagement_level INTEGER, -- 1-10
    prospect_buying_signals JSON, -- Array of signals
    prospect_concerns JSON, -- Array of concerns
    
    -- Next steps
    next_steps_category TEXT, -- 'moving_forward', 'self_service', 'unclear'
    next_steps_actions JSON, -- Array of specific actions
    next_steps_timeline TEXT,
    next_steps_probability INTEGER, -- 1-10
    
    -- Quinn insights for learning
    quinn_qualification_quality INTEGER, -- 1-10
    quinn_missed_opportunities JSON, -- Array of strings
    quinn_strengths JSON, -- Array of strings
    
    -- Metadata
    analysis_confidence INTEGER, -- 1-10
    llm_model_used TEXT,
    processing_time_seconds REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (call_id) REFERENCES calls (id) ON DELETE CASCADE
);

-- Slack notifications table - tracks what's been posted
CREATE TABLE slack_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL,
    channel TEXT NOT NULL,
    message_ts TEXT, -- Slack message timestamp for threading
    notification_type TEXT, -- 'summary', 'digest', 'alert'
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    message_preview TEXT, -- First 100 chars of message
    
    FOREIGN KEY (call_id) REFERENCES calls (id) ON DELETE CASCADE
);

-- Quinn learning feedback table - stores feedback for model improvement
CREATE TABLE quinn_learning_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id INTEGER NOT NULL,
    analysis_result_id INTEGER NOT NULL,
    feedback_type TEXT NOT NULL, -- 'correction', 'validation', 'additional_insight'
    feedback_data JSON, -- Structured feedback data
    provided_by TEXT, -- User who provided feedback
    feedback_source TEXT, -- 'manual', 'ae_review', 'manager_review'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (call_id) REFERENCES calls (id) ON DELETE CASCADE,
    FOREIGN KEY (analysis_result_id) REFERENCES analysis_results (id) ON DELETE CASCADE
);

-- Processing log table - tracks system operations
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL, -- 'fellow_fetch', 'salesforce_mapping', 'llm_analysis', 'slack_post'
    status TEXT NOT NULL, -- 'started', 'completed', 'failed', 'partial'
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    records_processed INTEGER DEFAULT 0,
    records_succeeded INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_details TEXT,
    metadata JSON, -- Additional operation-specific data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_calls_fellow_id ON calls(fellow_id);
CREATE INDEX idx_calls_date ON calls(call_date);
CREATE INDEX idx_calls_processed ON calls(processed);
CREATE INDEX idx_calls_ae_name ON calls(ae_name);

CREATE INDEX idx_sf_mappings_call_id ON salesforce_mappings(call_id);
CREATE INDEX idx_sf_mappings_contact_id ON salesforce_mappings(contact_id);
CREATE INDEX idx_sf_mappings_opportunity_id ON salesforce_mappings(opportunity_id);

CREATE INDEX idx_analysis_call_id ON analysis_results(call_id);
CREATE INDEX idx_analysis_version ON analysis_results(analysis_version);
CREATE INDEX idx_analysis_created ON analysis_results(created_at);

CREATE INDEX idx_slack_call_id ON slack_notifications(call_id);
CREATE INDEX idx_slack_channel ON slack_notifications(channel);
CREATE INDEX idx_slack_sent_at ON slack_notifications(sent_at);

CREATE INDEX idx_logs_operation ON processing_logs(operation_type);
CREATE INDEX idx_logs_status ON processing_logs(status);
CREATE INDEX idx_logs_start_time ON processing_logs(start_time);

-- Views for common queries

-- Unprocessed calls view
CREATE VIEW unprocessed_calls AS
SELECT 
    c.*,
    sm.contact_id,
    sm.opportunity_id,
    sm.contact_match_confidence
FROM calls c
LEFT JOIN salesforce_mappings sm ON c.id = sm.call_id
WHERE c.processed = FALSE;

-- Recent analysis summary view
CREATE VIEW recent_analysis_summary AS
SELECT 
    c.fellow_id,
    c.title,
    c.call_date,
    c.ae_name,
    c.prospect_company,
    ar.ae_excitement_level,
    ar.prospect_interest_level,
    ar.next_steps_category,
    ar.quinn_qualification_quality,
    ar.analysis_confidence,
    ar.created_at as analysis_date,
    sm.opportunity_id
FROM calls c
JOIN analysis_results ar ON c.id = ar.call_id
LEFT JOIN salesforce_mappings sm ON c.id = sm.call_id
ORDER BY c.call_date DESC;

-- Quinn learning insights view
CREATE VIEW quinn_learning_insights AS
SELECT 
    c.ae_name,
    AVG(ar.quinn_qualification_quality) as avg_qualification_quality,
    COUNT(*) as total_calls_analyzed,
    AVG(ar.prospect_interest_level) as avg_prospect_interest,
    AVG(ar.next_steps_probability) as avg_next_steps_probability,
    COUNT(CASE WHEN ar.next_steps_category = 'moving_forward' THEN 1 END) as moving_forward_count,
    COUNT(CASE WHEN ar.next_steps_category = 'self_service' THEN 1 END) as self_service_count
FROM calls c
JOIN analysis_results ar ON c.id = ar.call_id
WHERE c.call_date >= date('now', '-30 days')
GROUP BY c.ae_name
ORDER BY avg_qualification_quality DESC;