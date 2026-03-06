---
name: api-integration
description: Streamlined patterns for building multi-API integrations with OAuth2 authentication, database persistence, and production deployment. Use when building systems that combine multiple external APIs (Salesforce, REST APIs, etc.) with authentication flows, data persistence, and automated processing pipelines.
---

# API Integration

## Overview

Provides battle-tested patterns for building production-ready multi-API integrations with OAuth2 flows, error handling, and automated processing pipelines. Based on successful deployment of Fellow → Salesforce call intelligence system.

## Quick Start

Use `scripts/api-health-check.sh` to validate all API credentials before starting any integration project.

## Core Integration Patterns

### 1. OAuth2 Authentication (Salesforce)

**Pattern**: When Salesforce CLI fails, use direct OAuth2 flow

```python
# Instead of broken: sf data query...
# Use working OAuth2 pattern:

import requests
import os

def get_salesforce_token():
    auth_url = "https://login.salesforce.com/services/oauth2/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': os.getenv('SF_CLIENT_ID'),
        'client_secret': os.getenv('SF_CLIENT_SECRET')
    }
    
    response = requests.post(auth_url, data=data)
    response.raise_for_status()
    return response.json()['access_token']

def query_salesforce(query, token):
    url = f"https://telnyx.my.salesforce.com/services/data/v59.0/query/"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {'q': query}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()
```

### 2. Multi-Service Data Pipeline

**Pattern**: API → Database → Analysis → Update

```python
# Standard pipeline structure
def run_integration_pipeline():
    # 1. Fetch from source API
    raw_data = fetch_from_source_api()
    
    # 2. Store in database with metadata
    store_with_metadata(raw_data)
    
    # 3. Analyze/process (AI, calculations, etc.)
    analyzed_data = process_data(raw_data)
    
    # 4. Update target system
    update_target_system(analyzed_data)
    
    # 5. Verify results
    verify_integration_success()
```

### 3. Database Schema for API Integrations

**Pattern**: Always include source tracking and processing status

```sql
CREATE TABLE api_integrations (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,           -- External API ID
    source_type TEXT NOT NULL,         -- 'fellow', 'drive', etc.
    raw_data TEXT,                     -- JSON blob
    processed_at TIMESTAMP,
    analysis_confidence REAL,
    target_updated BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Resources

### scripts/
- `api-health-check.sh` - Validate all configured API credentials
- `oauth2-template.py` - Salesforce OAuth2 authentication template
- `integration-pipeline.py` - Standard multi-API integration template

### references/  
- `testing-patterns.md` - Complete testing workflow for API integrations
- `api-examples.md` - Working code samples for common APIs and OAuth flows