# 🚀 Service Order Specialist Agent (A2A-Compliant)

A specialized AI agent built on the **Telnyx Agent Architecture** for handling Service Order operations, Salesforce integration, and commitment management. **Fully compliant with the A2A (Agent-to-Agent) Protocol** for seamless integration with the Telnyx agent mesh.

## ✅ **Current Status: Phase 1 Complete!**

**A2A Protocol Compliance**: Full implementation with Agent Card, task lifecycle, authentication ✅  
**Salesforce Integration**: Real sf CLI integration with service order lookup and org ID validation ✅  
**Production Ready**: Docker, K8s configs, local development stack, comprehensive testing ✅  

**🎯 Ready for deployment when Telnyx infrastructure (a2a-discovery, agent registry) comes online!**

## 🎯 Purpose

This agent was created to:
- **Isolate service order work** in dedicated sessions with clean context
- **Provide direct access** to ops teams via Slack app (no routing through general assistants)
- **Enable A2A discovery** so other agents can leverage service order expertise
- **Apply specialized safety checks** for financial/billing operations
- **Streamline service order workflows** with dedicated tools and validation

## 🚀 Capabilities

### Core Skills (A2A Discoverable)

1. **Process Service Order Changes**
   - Customer commitment modifications
   - Contract date shifts  
   - Billing adjustments
   - Full validation and safety checks

2. **Validate Commitment Terms**
   - Compliance checking
   - Overlap detection
   - Contract term analysis

3. **Extract Service Order from PDF**
   - Parse service order documents
   - Extract structured contract data
   - Return JSON for further processing

4. **Salesforce Service Order Lookup**
   - Query existing service orders
   - Status analysis and reporting
   - Organization ID validation

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

## 📋 Usage Examples

### Direct Slack Usage (Ops Teams)

```
# Look up a customer's service orders
@service-order-specialist lookup Qomon service orders

# Process a commitment change  
@service-order-specialist update Acme Corp start date to 2026-02-01

# Validate proposed terms
@service-order-specialist validate org c4499f9b-6ffd-4b60-9224-5b70ae0b1b04 commitment changes

# Extract data from uploaded PDF
@service-order-specialist extract this service order PDF
```

### A2A Integration (Other Agents)

```python
import httpx
from telnyx_agent_sdk import A2AClient

# Discover the service order specialist via a2a-discovery
discovery_response = httpx.get(
    "https://a2a-discovery.internal.telnyx.com/v1/agents/discover",
    params={"skill": "process-service-order-change"}
)
agents = discovery_response.json()["agents"]
specialist = agents[0]  # Get the first available specialist

# Use A2A client to send message 
a2a_client = A2AClient(auth_token="your_telnyx_agent_token")
response = await a2a_client.send_message(
    agent_url=specialist["url"],
    skill="process-service-order-change",
    payload={
        "customer_name": "ACME Corp", 
        "org_id": "c4499f9b-6ffd-4b60-9224-5b70ae0b1b04",
        "action": "update_dates",
        "new_start_date": "2026-02-01",
        "validation_required": True,
        "reason": "Customer requested date change"
    },
    requester_agent="my-agent-id"
)

# Handle A2A response
if response.state == "completed":
    print(f"Success: {response.result}")
elif response.state == "failed":
    print(f"Error: {response.error}")
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

### Built-in Safeguards

- **Customer/Org ID validation** - Always verify customer matches org ID
- **Overlap detection** - Check for conflicting commitments  
- **Rev Ops approval workflow** - Never bypass approval requirements
- **Webhook validation** - Verify all Commitment Manager responses
- **Permission scoping** - Least privilege access to resources

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

---

**Maintainer**: niamh@telnyx.com  
**Team**: platform  
**Status**: Ready for Phase 1 deployment 🚀