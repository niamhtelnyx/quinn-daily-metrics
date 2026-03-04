# Technical Architecture Planning Templates

*15-20 minute upfront design to avoid refinement cycles*

## 🏗️ Integration Architecture Checklist

### **Phase 1: Requirements (5 minutes)**
- [ ] **Data Sources**: What APIs/systems are involved?
- [ ] **Data Flow**: Source → Processing → Destination  
- [ ] **Volume**: How many records per day/hour?
- [ ] **Duplication**: How will duplicates be handled?
- [ ] **Failure Cases**: What happens when APIs are down?

### **Phase 2: Schema Design (5 minutes)**
- [ ] **Database Tables**: What entities need storage?
- [ ] **Unique Keys**: How to identify duplicates?
- [ ] **Indexes**: What queries will be frequent?
- [ ] **Versioning**: How to handle schema changes?

### **Phase 3: Processing Strategy (5 minutes)**
- [ ] **Processing Order**: Which source processes first?
- [ ] **Batch vs Real-time**: When to process data?
- [ ] **Error Handling**: Retry logic, fallbacks, alerts
- [ ] **Monitoring**: How to track success/failure rates?

### **Phase 4: Testing Strategy (5 minutes)**  
- [ ] **Test Data**: Real vs synthetic data sources
- [ ] **Integration Points**: API connectivity, auth validation
- [ ] **End-to-End**: Complete workflow validation
- [ ] **Performance**: Volume and latency testing

## 📋 Quick Architecture Template

```markdown
## System: [NAME]

### Data Flow
[Source] → [Processing] → [Destination]

### Key Components
- **Sources**: [API1, API2, etc.]
- **Storage**: [Database schema summary]
- **Processing**: [Main business logic]
- **Output**: [Where results go]

### Deduplication Strategy
- **Key**: [What makes records unique]
- **Logic**: [How duplicates are detected/handled]

### Error Handling
- **Retry Logic**: [When to retry, how many times]
- **Fallbacks**: [What happens when things fail]
- **Alerts**: [How failures are communicated]

### Testing Approach
- **Unit Tests**: [Key functions to test]
- **Integration**: [API connectivity validation] 
- **E2E**: [Complete workflow test cases]
```

## 🔧 Multi-API Integration Patterns

### **Pattern 1: Sequential Processing (Call Intelligence)**
```
Step 1: Process Google Drive (first, most complete)
Step 2: Process Fellow (add recording URLs)
Step 3: Process Salesforce (match to events)
Result: Zero duplication, complete data
```

### **Pattern 2: Parallel Processing + Merge**
```
Thread 1: Fetch from API_A → Store with source_id
Thread 2: Fetch from API_B → Store with source_id  
Merge: Combine by business key → Deduplicate
Result: Faster processing, complex merging
```

### **Pattern 3: Event-Driven Processing**
```
Trigger: New data arrives → Queue for processing
Worker: Process batches → Update targets
Monitor: Track queue depth + processing rates
Result: Scalable, handles volume spikes
```

## ⚠️ Common Architecture Pitfalls

### **❌ Skipping Deduplication Design**
- **Problem**: Build system, discover duplicates later
- **Solution**: Define dedup key in Phase 2

### **❌ No Processing Order Strategy**  
- **Problem**: Race conditions, data consistency issues
- **Solution**: Define processing sequence in Phase 3

### **❌ Missing Error Handling Design**
- **Problem**: Silent failures in production
- **Solution**: Plan retry/fallback logic in Phase 3

### **❌ Ad-hoc Testing Approach**
- **Problem**: Multiple test files, inconsistent validation
- **Solution**: Unified test framework in Phase 4

## 🎯 15-Minute Planning Session Example

**System**: Fellow → Salesforce Call Intelligence

**Phase 1 (Requirements)**:
- Sources: Fellow API, Google Drive, Salesforce
- Flow: Calls → Analysis → SF Enhancement  
- Volume: ~50 calls/day
- Dedup: By call date + attendee email
- Failures: Store for manual review

**Phase 2 (Schema)**:
- Table: calls (id, source_id, dedup_key, analysis_json, sf_event_id)
- Unique: dedup_key = {email}_{date}
- Index: source_id, dedup_key, created_at

**Phase 3 (Processing)**:
- Order: Google Drive first (complete analysis), Fellow second (add URLs)
- Timing: Every 30 minutes via cron
- Errors: Retry 3x, then store in failed_calls table

**Phase 4 (Testing)**:
- Test data: Last 7 days of real calls
- Integration: API auth validation script
- E2E: Process 1 known call end-to-end
- Performance: 50 calls in <5 minutes

**Result**: Clear implementation plan, reduced iterations