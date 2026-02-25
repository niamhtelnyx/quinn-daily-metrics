# 🚀 Service Order Specialist Agent (A2A-Compliant)

A specialized AI agent built on the **Telnyx Agent Architecture** for handling Service Order operations, Salesforce integration, and commitment management. **Fully compliant with the A2A (Agent-to-Agent) Protocol** for seamless integration with the Telnyx agent mesh.

## ✅ **Current Status: Phase 1 Complete!**

**A2A Protocol Compliance**: Full implementation with Agent Card, task lifecycle, authentication ✅  
**Salesforce Integration**: Real sf CLI integration with service order lookup and org ID validation ✅  
**Production Ready**: Docker, K8s configs, local development stack, comprehensive testing ✅  

**🎯 Ready for deployment when Telnyx infrastructure (a2a-discovery, agent registry) comes online!**

## 🎯 Purpose

This agent ensures **signed contracts are accurately reflected in both the Commitment Database and Salesforce** according to user specifications, with mandatory confirmation checkpoints throughout the process.

**Core Mission:**
- **Contract-to-System Accuracy** - Ensure signed service orders match exactly in both systems
- **Validation Checkpoints** - Require explicit user confirmation before any financial operations  
- **Overlap Detection** - Identify and resolve conflicts with existing commitments
- **End-to-End Verification** - Validate webhook delivery and database consistency
- **Audit Trail Logging** - Track every step for compliance and debugging

## 🚀 Complete Service Order Logging Workflow

### Full Contract Processing Pipeline (5 Phases + Checkpoints)

**PHASE 1: Discovery & Validation**
- **Customer Lookup** - Find existing service orders and customer data
- **Mission Control Account Resolution** - Map to organization IDs  
- **🛡️ CHECKPOINT**: Customer/Org ID validation before proceeding

**PHASE 2: Contract Analysis**  
- **PDF Extraction** - Parse signed contract into structured data
- **Commitment Type Detection** - Static vs Ramped commitment analysis
- **Overlap Detection** - Check conflicts with existing commitments
- **🛡️ CHECKPOINT**: Overlap resolution strategy confirmation

**PHASE 3: Service Order Creation**
- **Field Mapping** - Map contract terms to Salesforce fields
- **Validation Rules** - Apply business logic and picklist validation
- **🛡️ CHECKPOINT**: Service Order creation confirmation  
- **Record Creation** - Create Service_Order__c and Service_Order_Details__c records

**PHASE 4: Approval & Activation**
- **Stage Setting** - Mark contract as "Signed"
- **🛡️ CRITICAL CHECKPOINT**: Rev Ops approval confirmation (NEVER auto-approve)
- **Webhook Trigger** - Set Rev_Ops_Approved__c = true to fire MMC_webhook flow
- **Response Verification** - Check Chatter FeedItems for webhook success

**PHASE 5: End-to-End Validation**
- **Commitment Database Query** - Verify commitment created successfully  
- **Cross-System Validation** - Ensure Salesforce and CM data consistency
- **🛡️ CHECKPOINT**: Final audit trail approval
- **Summary Report** - Complete processing summary with IDs and status

### Core Skills (A2A Discoverable) - 8 Skills

1. **salesforce-service-order-lookup** - Customer discovery and existing SO analysis
2. **extract-service-order-pdf** - Contract parsing into structured data  
3. **validate-commitment-terms** - Overlap detection and compliance checking
4. **resolve-mission-control-account** - Organization ID mapping and validation
5. **create-service-order** - Salesforce record creation with field mapping
6. **process-service-order-change** - Approval workflow and webhook triggering
7. **commitment-database-query** - End-to-end validation with auto org ID resolution
8. **download-service-order-document** - Source document retrieval and verification

### Specialized Knowledge

- **Salesforce Service Order objects** (`Service_Order__c`, `Service_Order_Details__c`)
- **Commitment Manager API** integration and validation
- **Ramped vs Static commitments** handling
- **Rev Ops approval workflows** and webhook validation
- **Safety guardrails** for financial operations

### Channel Integration

- **Slack App**: Direct access for ops teams
- **A2A Protocol**: Discoverable by other agents  
- **HTTP API**: RESTful endpoints for external systems

## 🛠️ Development Setup

### Prerequisites
- Python 3.11+
- Docker (for containerization)
- Access to Telnyx APIs and Salesforce

### Quick Start

```bash
# Clone and setup
cd service-order-specialist
make bootstrap

# Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration

# Run locally
python agent.py

# Or run with Docker
make docker-build
make docker-run
```

## 🧪 **Quick Demo**

### Test the A2A Agent (Local Development)

```bash
# 1. Start the agent
cd service-order-specialist
source .venv/bin/activate
DEBUG=true TELNYX_AGENT_TOKEN=dev-token python a2a_service.py

# 2. Check Agent Card (A2A discovery)
curl http://localhost:8000/.well-known/agent.json

# 3. Test real Salesforce lookup
curl -X POST http://localhost:8000/a2a/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token" \
  -d '{
    "skill": "salesforce-service-order-lookup",
    "payload": {
      "customer_name": "Call Loop",
      "org_id": "c4499f9b-6ffd-4b60-9224-5b70ae0b1b04"
    },
    "mode": "sync"
  }'

# 4. Expected Response: Real Salesforce data with org ID validation! ✅
```

### What You'll See
```json
{
  "taskId": "uuid-here",
  "state": "completed",
  "result": {
    "lookup_successful": true,
    "customer": "Call Loop",
    "service_orders": [/* Real Salesforce SO data */],
    "org_id_validation": {
      "validation_passed": true,
      "provided_org_id": "c4499f9b-6ffd-4b60-9224-5b70ae0b1b04",
      "actual_org_id": "c4499f9b-6ffd-4b60-9224-5b70ae0b1b04"
    }
  }
}
```

### ✨ **NEW: Auto Organization ID Resolution**

Query commitments using **either** Salesforce Mission Control Account IDs **or** UUID organization IDs:

```bash
# Use Salesforce Mission Control Account ID (auto-resolves to UUID)
curl -X POST http://localhost:8000/a2a/tasks \
  -H "Authorization: Bearer dev-token" \
  -d '{
    "skill": "commitment-database-query",
    "payload": {
      "organization_id": "a0TQk00000TcP5CMAV",
      "include_cancelled": true,
      "format": "summary"
    },
    "mode": "sync"
  }'

# Use UUID organization ID directly  
curl -X POST http://localhost:8000/a2a/tasks \
  -H "Authorization: Bearer dev-token" \
  -d '{
    "skill": "commitment-database-query", 
    "payload": {
      "organization_id": "b156dd5f-9fd9-4829-a4e6-e8294cbc2ca8",
      "include_cancelled": true,
      "format": "summary"
    },
    "mode": "sync"
  }'
```

**Response includes auto-resolution details:**
```json
{
  "result": {
    "success": true,
    "organization_id": "b156dd5f-9fd9-4829-a4e6-e8294cbc2ca8",
    "total_commitments": 3,
    "active_count": 1,
    "cancelled_count": 2,
    "org_id_resolution": {
      "auto_resolved": true,
      "original_salesforce_id": "a0TQk00000TcP5CMAV", 
      "resolved_uuid_org_id": "b156dd5f-9fd9-4829-a4e6-e8294cbc2ca8",
      "mission_control_account": {
        "Id": "a0TQk00000TcP5CMAV",
        "Name": "MC-538508",
        "Organization_ID__c": "b156dd5f-9fd9-4829-a4e6-e8294cbc2ca8"
      }
    }
  }
}
```

## 📋 Usage Examples

### Complete Service Order Processing

```
# Full contract processing (E2E workflow)
@service-order-specialist process contract for:
Customer: epicleap.ai
Start Date: 2026-02-15  
Sales Rep: alaza
Commitment: $2500/month Static

# Expected response includes ALL checkpoints:
✅ Customer lookup and validation
🛡️ CHECKPOINT: Confirm customer/org ID match
✅ Overlap analysis (found 2 existing commitments)  
🛡️ CHECKPOINT: How to handle overlapping commitments?
✅ Contract extraction and field mapping
🛡️ CHECKPOINT: Confirm Service Order creation?
✅ Service Order created (ID: a1AQk000008XYZ)
🛡️ CRITICAL CHECKPOINT: Approve for Rev Ops? (REQUIRES EXPLICIT YES)
✅ Webhook fired (201 Created)
✅ Commitment database validation
🛡️ CHECKPOINT: Final audit trail acceptable?
✅ COMPLETE - Summary report attached
```

### Individual Operations (For Debugging)

```
# Look up customer's existing commitments
@service-order-specialist lookup epicleap.ai service orders

# Extract contract data only  
@service-order-specialist extract this service order PDF

# Validate overlap scenarios
@service-order-specialist check overlaps for epicleap.ai new $2500 commitment

# Query commitment database directly
@service-order-specialist query commitments for a0TQk00000TcP5CMAV
```

### A2A Integration (Other Agents)

```python
# Complete contract processing via A2A
response = await a2a_client.send_message(
    agent_url="http://service-order-specialist:8000",
    skill="process-complete-service-order",
    payload={
        "customer_name": "epicleap.ai",
        "contract_data": {
            "start_date": "2026-02-15",
            "commitment_amount": 2500,
            "sales_rep": "alaza", 
            "commitment_type": "Static"
        },
        "validation_checkpoints": True,  # Require confirmation at each phase
        "explicit_approval_required": True  # Never auto-approve
    },
    mode="interactive"  # Enables checkpoint confirmations
)

# Expected response includes checkpoint prompts:
{
  "state": "awaiting_confirmation",
  "checkpoint": "customer_validation", 
  "message": "Found epicleap.ai with 2 existing commitments. Proceed?",
  "data": {
    "existing_commitments": [...],
    "overlap_analysis": {...}
  }
}

# Individual skills for specific operations
skills = [
    "salesforce-service-order-lookup",
    "extract-service-order-pdf", 
    "validate-commitment-terms",
    "create-service-order",
    "process-service-order-change",
    "commitment-database-query"
]
```

### From Ninibot (Main Agent)

```python
# Ninibot can spawn or communicate with the specialist
response = sessions_spawn(
    task="Process service order change for ACME Corp",
    label="so-acme-corp"
)

# Or direct A2A communication
specialist_response = a2a_send(
    skill="process-service-order-change",
    payload=service_order_data
)
```

## 🔒 Security & Safety

### Built-in Safeguards & Mandatory Checkpoints

**🛡️ VALIDATION CHECKPOINTS** (Cannot be bypassed):
- **Customer/Org ID Validation** - Always verify customer matches org ID before any operations
- **Overlap Confirmation** - Require explicit approval for conflicting commitment scenarios
- **Service Order Creation** - Present complete field mapping for confirmation before creating records
- **🚨 CRITICAL: Rev Ops Approval** - **NEVER EVER** set Rev_Ops_Approved__c=true without explicit human "YES"
- **End-to-End Verification** - Validate webhook success and database consistency before completing

**FINANCIAL OPERATION CONTROLS**:
- **No Auto-Approval** - All financial operations require explicit human confirmation
- **Webhook Verification** - Check Chatter FeedItems for 201/204 responses after every approval/termination  
- **Cross-System Validation** - Verify Salesforce and Commitment Manager data match exactly
- **Audit Trail Logging** - Every step logged with timestamps, user confirmations, and system responses
- **Rollback Capability** - Can terminate commitments if validation fails post-approval

### Required Permissions

- **Salesforce**: Service Order read/write access
- **Commitment Manager**: Webhook API credentials
- **Slack**: Bot permissions for messaging
- **A2A**: Agent authentication token

## 🚀 Deployment

### Local Development
```bash
make docker-run
```

### Production Deployment
1. **Build and push** Docker image to registry
2. **Deploy to Kubernetes** with appropriate resource class
3. **Register with A2A Discovery** service
4. **Configure Slack app** with proper permissions
5. **Set up monitoring** and health checks

### Resource Requirements
- **Recommended**: `standard` resource class
- **Auto-terminate**: 30m idle (for ephemeral tasks)  
- **Max lifetime**: `indefinite` (for persistent ops support)

## 📊 Monitoring

### Health Checks
- `/.well-known/agent-card.json` - Agent card availability
- `/health` - Application health status
- A2A discovery registration status

### Key Metrics
- Request volume and latency
- Salesforce API call success rate
- Commitment Manager webhook success rate  
- Slack message processing time
- A2A skill invocation frequency

## 🔄 Integration with Main Agent (Ninibot)

This specialist agent works **alongside** Ninibot, not as a replacement:

- **Ninibot**: General purpose assistant, triages work, maintains relationships
- **Service Order Specialist**: Domain expert for service order operations

### Handoff Pattern

1. **User mentions service order work** → Ninibot detects
2. **Ninibot offers**: "Want me to spawn the service order specialist?"
3. **User approves** → Ninibot spawns specialist session
4. **Specialist handles** all service order complexity  
5. **Specialist reports back** when complete

### Direct Access Pattern

1. **Ops team needs service order work** → Direct Slack to specialist
2. **Specialist provides** expert domain knowledge immediately
3. **No routing overhead** through general assistant

## 🤝 Contributing

This agent is part of the Telnyx agent ecosystem. For changes:

1. Test locally with `make test`
2. Validate A2A skills with other agents  
3. Ensure safety checks are preserved
4. Update documentation for new capabilities

## 📚 Related Documentation

- **Service Order Operations**: `skills/service-order-ops/SKILL.md`
- **PDF Service Order Parser**: `skills/pdf-service-order-parser/SKILL.md`  
- **A2A Protocol**: Telnyx agent architecture docs
- **Deployment Guide**: Telnyx agent deployment patterns

## 📅 **Deployment Timeline**

| Phase | Timeline | Status | Description |
|-------|----------|---------|-------------|
| **Phase 1: Foundation** | Weeks 1-2 | 🔄 **Waiting for Infrastructure** | Deploy when a2a-discovery, agent registry ready |
| **Phase 2: Integration** | Weeks 3-4 | ⏳ Ready | Add governance, team quotas, knowledge access |  
| **Phase 3: Production** | Weeks 5-8 | ⏳ Ready | Self-service provisioning, advanced monitoring |
| **Phase 4: Innovation** | Ongoing | ⏳ Ready | Multi-agent workflows, customer-facing bots |

**Current Status**: ✅ **Ready for Phase 1 deployment** - waiting for Telnyx infrastructure

## 📈 **Recent Updates**

### v1.0.1 - Auto Organization ID Resolution (2026-02-25) ✨
- **NEW**: `commitment-database-query` skill with auto org ID resolution
- **Auto-detects** Salesforce Mission Control Account IDs (`a0TQk00000...`)
- **Auto-resolves** to UUID organization IDs for commitment queries
- **Backwards compatible** with existing UUID organization ID usage
- **Enhanced transparency** with resolution details in responses
- **Zero manual lookups** needed for Salesforce → Commitment Manager integration

### v1.0.0 - Foundation Release (2026-02-24)
- Full A2A Protocol compliance
- 8 core skills for service order management
- Safety blocks for financial operations
- Salesforce integration with real sf CLI
- Local development stack ready
- Production deployment configs

---

**Maintainer**: niamh@telnyx.com  
**Team**: platform  
**Status**: Ready for Phase 1 deployment 🚀