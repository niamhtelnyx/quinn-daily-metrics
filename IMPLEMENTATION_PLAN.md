# Service Order Specialist - A2A Implementation Plan

*Based on Telnyx Agent Architecture Document*

## Architecture Learning Summary

### Core Principles (Section 1)
- **A2A for agent communication** - Use A2A protocol for all agent-to-agent interaction
- **Pragmatic tool access** - Use existing APIs (sf CLI, REST) instead of waiting for MCP
- **Markdown everywhere** - All knowledge in markdown files for direct agent consumption
- **Telnyx-native first** - Use Telnyx Storage, AI APIs, WireGuard mesh
- **Observable by default** - Built-in audit trails for financial operations

### Technology Stack (Section 2)
- **Runtime**: Clawdbot in Kubernetes
- **Networking**: WireGuard mesh (encrypted, zero-trust)
- **Discovery**: a2a-discovery + Consul
- **Storage**: Telnyx Storage (knowledge), PostgreSQL (audit logs)
- **Secrets**: Vault (infrastructure), 1Password (human credentials)
- **Observability**: OpenTelemetry → Telnyx AI Obs

### A2A Protocol Requirements (Section 3)
- **Agent Card**: `/.well-known/agent.json` with skills, auth, supported modes
- **Task Lifecycle**: submitted → working → completed/failed (with proper state transitions)
- **Error Handling**: Structured errors with code, category, message, source chain
- **Headers**: A2A-Version, X-A2A-Timeout, X-A2A-Idempotency-Key on all requests
- **Conformance**: Must pass A2A conformance suite before production deployment

### Discovery & Registry (Section 4)
- **Registration**: Register with a2a-discovery on startup (persistent agents get Consul too)
- **Metadata**: Include team, owner, capabilities, resource class for proper discovery
- **Health**: Consul health checks every 10s, heartbeat to maintain active status
- **Ephemeral Strategy**: Short sub-agents use parent routing, don't register in Consul

### Inter-Agent Communication (Section 5)
- **Discovery First**: Query a2a-discovery before communicating with other agents
- **Direct A2A**: Point-to-point communication, no message queues needed
- **Large Payloads**: Store in Telnyx Storage, reference URIs in A2A messages
- **Hierarchy**: Planner/Worker separation, 2-level max, avoid coordination bottlenecks

### Knowledge Access (Section 6)
- **Direct Reading**: Access markdown files directly from Telnyx Storage
- **Work Claims**: Redis atomic claims to prevent duplicate service order processing
- **Classification**: Respect confidential/restricted access controls
- **Domain Embeddings**: Start with Telnyx AI, evaluate financial-specific models later

### Lifecycle Management (Section 7)
- **Agent Type**: Persistent (indefinite lifetime, standard resource class)
- **States**: ACTIVE → IDLE → SUSPENDED → TERMINATING → TERMINATED
- **Sub-Agent Spawning**: Can spawn workers for complex operations (max depth 2)
- **Model Selection**: GPT for planning, Claude for interactive, domain-specific for embeddings
- **Cleanup**: Proper task completion, workspace archiving, deregistration on termination

### Governance & Safety (Section 8)
- **Permission Level**: L3 Team Member (operate assigned agents, spawn approved templates)
- **Spawn Authorization**: Template approval + quota checks + cost projection + rate limits
- **Team Quotas**: Max agents, monthly budget, resource class limits enforced
- **Audit Trail**: All financial operations logged immutably (Kafka → Telnyx Storage)
- **Runaway Prevention**: Cost tracking, action repetition detection, circuit breakers
- **Secret Management**: Vault for infrastructure (dynamic DB creds), 1Password for shared (API keys)

### Infrastructure (Section 9)
- **Deployment**: EKS Kubernetes with namespace isolation (team-revenue-ops namespace)
- **Resource Class**: Standard (1.0 CPU, 2GB RAM, 10GB storage, ~$0.07/hr)
- **Networking**: WireGuard mesh IP for encrypted A2A communication + K8s network policies
- **Workspace**: Hybrid model (private PVC + shared team knowledge + global knowledge FUSE)
- **Core Services**: Access to agent-platform namespace (Registry, a2a-discovery, Consul, Vault)
- **Telnyx Integration**: Native Storage, AI APIs, Voice/Messaging capabilities

### Team Onboarding (Section 10)
- **Prerequisites**: Team namespace, team lead agent, quota allocation, Vault + 1Password vaults
- **Week 1**: Setup namespace, training, deploy first agent with python-agentic-service-template
- **Week 2**: Configure A2A skills, set up knowledge corpus, deploy production agents, test inter-agent comms
- **Team Pattern**: Customer-facing with data isolation (scoped customer data permissions)
- **Local Development**: docker-compose stack for testing A2A communication locally
- **Responsibilities**: Agent ownership, cost management, template compliance, incident response

### Security Model (Section 11)
- **Defense in Depth**: 5-layer security (Network → Identity → Authorization → Audit → Containment)
- **Network Security**: WireGuard mesh, K8s network policies, namespace isolation, TLS everywhere
- **Identity & Auth**: Agent UUID, Vault tokens, A2A bearer auth, mTLS certificates
- **Authorization**: RBAC (L3 permissions), scoped Vault policies, team quotas, spawn depth limits
- **Audit & Monitoring**: Immutable logs via Kafka, OpenTelemetry traces, cost tracking, action logging
- **Containment**: Container isolation, resource limits, circuit breakers, auto-quarantine on anomalies
- **Zero-Trust**: No implicit trust, least privilege, assume breach, continuous verification

### Implementation Roadmap (Section 12)
- **Phase 1: Foundation (Weeks 1-2)** - Core infrastructure, a2a-discovery, basic templates, 10-20 agents
- **Phase 2: Scale (Weeks 3-4)** - Governance engine, team quotas, knowledge sharing, 100+ agents  
- **Phase 3: Production (Weeks 5-8)** - Self-service provisioning, 1000+ agents, performance optimization
- **Phase 4: Innovation (Ongoing)** - Multi-agent reasoning, agent marketplace, cross-company federation
- **Service Order Specialist Timing**: Can deploy in Phase 2 (Week 3-4) when governance and quotas are ready
- **Dependencies**: a2a-discovery (Week 1), governance engine (Week 3), team quotas (Week 3)

## Implementation Roadmap

### Phase 1: Core A2A Compliance
**Goal**: Basic A2A-compliant agent that can be discovered and communicated with

**Tasks**:
- [ ] Create proper Agent Card at `/.well-known/agent.json`
- [ ] Implement A2A endpoints: SendMessage, StreamMessage, GetTask, ListTasks, CancelTask  
- [ ] Full task lifecycle state management
- [ ] Structured error responses with proper categories
- [ ] Required headers support (A2A-Version, timeouts, idempotency)
- [ ] Pass A2A conformance suite in CI

**Files**: `agent_card.py`, `a2a_service.py`

### Phase 2: Service Integration  
**Goal**: Connect to Salesforce, Commitment Manager, and core service order operations

**Tasks**:
- [ ] Salesforce integration via `sf` CLI
- [ ] Commitment Manager REST API client
- [ ] PDF processing for service order extraction
- [ ] Core service order workflows (lookup, update, approve, terminate)
- [ ] Safety validations for financial operations

**Files**: `salesforce_client.py`, `commitment_manager_client.py`, `pdf_processor.py`, `service_order_workflows.py`

### Phase 3: Discovery & Knowledge
**Goal**: Register for discovery and access shared knowledge

**Tasks**:
- [ ] Register with a2a-discovery on startup
- [ ] Consul health checks and heartbeat maintenance
- [ ] Access service order policies from Telnyx Storage knowledge corpus
- [ ] Implement work claim registry (Redis) to prevent duplicate processing
- [ ] Respect data classification (confidential service orders, restricted PII)

**Files**: `discovery_client.py`, `knowledge_access.py`, `work_claims.py`

### Phase 4: Inter-Agent Coordination
**Goal**: Communicate with other agents for complex workflows

**Tasks**:
- [ ] Discover and communicate with billing specialists
- [ ] Discover and communicate with customer data agents  
- [ ] Delegate complex calculations to appropriate specialists
- [ ] Handle error propagation in multi-agent workflows
- [ ] Use Telnyx Storage for large payload sharing

**Files**: `inter_agent_client.py`, `delegation_workflows.py`

### Phase 5: Lifecycle & Deployment
**Goal**: Production-ready EKS deployment with proper lifecycle management

**Tasks**:
- [ ] EKS deployment in team-revenue-ops namespace
- [ ] Standard resource class configuration (1.0 CPU, 2GB RAM, 10GB storage)
- [ ] Network policies for team isolation + agent-platform access
- [ ] Hybrid workspace setup (private PVC + shared knowledge mounts)
- [ ] WireGuard mesh IP assignment for A2A communication
- [ ] Template definition for agent spawning
- [ ] Sub-agent spawning capability for complex operations
- [ ] Health monitoring and zombie detection
- [ ] Auto-cleanup for ephemeral sub-agents

**Files**: `deployment/k8s/`, `deployment/network-policy.yaml`, `deployment/pvc.yaml`, `templates/`, `lifecycle_manager.py`

### Phase 6: Governance & Safety
**Goal**: Add governance controls and safety guardrails for financial operations

**Tasks**:
- [ ] Configure L3 Team Member permissions for service order operations
- [ ] Set up team quotas (max agents, monthly budget, resource class limits)
- [ ] Implement comprehensive audit logging for all financial operations
- [ ] Add cost tracking and budget enforcement for service order workflows
- [ ] Configure runaway prevention (action repetition detection, circuit breakers)
- [ ] Set up Vault integration for dynamic database credentials
- [ ] Configure 1Password access for shared API keys (Salesforce, Commitment Manager)
- [ ] Implement spawn authorization checks for sub-agents
- [ ] Add rate limiting on A2A endpoints to prevent abuse
- [ ] Configure circuit breaker for auto-suspension if multiple guardrails triggered

**Files**: `governance.py`, `audit_logger.py`, `cost_tracker.py`, `secrets_manager.py`

### Phase 7: Team Onboarding & Deployment
**Goal**: Complete the official onboarding process to deploy production agent

**Week 1 Tasks**:
- [ ] Request team-revenue-ops namespace and quotas from platform admin (via #agent-platform)
- [ ] Complete agent architecture training (self-serve documentation)
- [ ] Verify team vault provisioning in 1Password
- [ ] Deploy first agent using python-agentic-service-template (A2A built in)
- [ ] Verify agent registers with a2a-discovery and appears in fleet dashboard

**Week 2 Tasks**:
- [ ] Configure A2A skills definition (what our agent can do for others)
- [ ] Set up team-specific knowledge corpus (service order policies in Markdown)
- [ ] Deploy 2-3 production agents for testing
- [ ] Configure alerts and monitoring via observability dashboards
- [ ] Test inter-agent communication via a2a-inspector

**Ongoing Tasks**:
- [ ] Set up local development environment (docker-compose stack)
- [ ] Establish incident response procedures for agent issues
- [ ] Quarterly agent fleet review and cleanup
- [ ] Cost monitoring and proactive budget management

**Files**: `docker-compose.local.yml`, `deployment/onboarding-checklist.md`

### Phase 8: Security Implementation
**Goal**: Implement comprehensive security controls for financial operations

**Network Security Tasks**:
- [ ] Configure WireGuard mesh networking for encrypted A2A communication
- [ ] Implement K8s network policies for namespace isolation + agent-platform access
- [ ] Enforce TLS on all endpoints (A2A, health checks, API calls)
- [ ] Set up proper egress controls (no direct internet for sensitive operations)

**Identity & Authentication Tasks**:
- [ ] Generate unique agent UUID for identity management
- [ ] Configure Vault token authentication with appropriate TTL
- [ ] Implement A2A bearer token authentication on all endpoints
- [ ] Set up mTLS certificates for service-to-service communication

**Authorization & Access Control Tasks**:
- [ ] Configure L3 (Team Member) RBAC permissions
- [ ] Create scoped Vault policies for team-revenue-ops access only
- [ ] Implement team quota enforcement (agents, budget, resources)
- [ ] Set spawn depth limits (max 2 levels for sub-agents)

**Audit & Monitoring Tasks**:
- [ ] Implement immutable audit logging for all financial operations
- [ ] Configure OpenTelemetry tracing for full request chains
- [ ] Set up cost tracking and budget alerts
- [ ] Log all sensitive operations (approve, terminate, commitment changes)

**Containment & Protection Tasks**:
- [ ] Implement input sanitization for prompt injection protection
- [ ] Create GUARDRAILS.md for financial operation safety checks
- [ ] Configure circuit breakers and auto-quarantine on anomaly detection
- [ ] Set up resource limits and container isolation
- [ ] Implement action approval workflow for high-risk operations

**Files**: `security/`, `security/guardrails.md`, `security/threat_detection.py`, `security/input_sanitizer.py`

## Service Order Specialist Deployment Timeline

### Pre-Phase 1: Development (Weeks -2 to 0)
**Goal**: Build and test Service Order Specialist locally while waiting for infrastructure

**Development Tasks**:
- [ ] Complete Phases 1-4 (A2A compliance, service integration, knowledge access, inter-agent communication)
- [ ] Build docker-compose local development stack
- [ ] Test A2A communication with mock agents
- [ ] Validate Salesforce integration via sf CLI
- [ ] Test commitment manager API integration
- [ ] Build comprehensive test suite

### Phase 1 Deployment (Weeks 1-2)
**Goal**: Deploy basic version when core infrastructure is ready

**Available Infrastructure**: a2a-discovery, Agent Registry, K8s namespaces, Vault, 1Password Connect
**Ready to Deploy**: Basic Service Order Specialist with A2A compliance

**Deployment Tasks**:
- [ ] Deploy to team-revenue-ops namespace
- [ ] Register with a2a-discovery
- [ ] Verify A2A endpoints working
- [ ] Test basic service order operations
- [ ] Validate Agent Card discovery by other agents

### Phase 2 Integration (Weeks 3-4) 
**Goal**: Add governance and knowledge sharing when available

**Available Infrastructure**: Governance engine, team quotas, cost tracking, knowledge corpus
**Ready to Add**: Full security controls, budget enforcement, knowledge access

**Integration Tasks**:
- [ ] Configure team quotas and cost tracking
- [ ] Set up knowledge corpus access (service order policies)
- [ ] Implement work claim registry for duplicate prevention
- [ ] Enable spawn governance for sub-agents
- [ ] Add comprehensive audit logging

### Phase 3 Production (Weeks 5-8)
**Goal**: Full production deployment with self-service capabilities

**Available Infrastructure**: Self-service provisioning, advanced monitoring, anomaly detection
**Ready to Scale**: Multiple Service Order Specialists, advanced features

**Production Tasks**:
- [ ] Enable self-service spawning for other teams
- [ ] Add advanced anomaly detection
- [ ] Implement voice capabilities for customer communication
- [ ] Set up performance monitoring and optimization
- [ ] Configure disaster recovery procedures

### Phase 4 Innovation (Ongoing)
**Goal**: Advanced multi-agent service order workflows

**Innovation Tasks**:
- [ ] Multi-agent service order processing coordination
- [ ] Customer-facing service order chatbots
- [ ] Automated Rev Ops approval workflows
- [ ] Cross-team service order analytics
- [ ] AI-optimized commitment recommendations

## Service Order Specialist Configuration

```yaml
# Agent Profile
agent_type: "persistent"
lifetime: "indefinite" 
resource_class: "standard"
max_spawn_depth: 2
auto_terminate_idle: "30m"
team: "revenue-ops"
cost_center: "revenue-ops"

# Governance & Safety
permission_level: "L3"  # Team Member
approved_templates: ["sub-agent-worker", "service-order-task-agent"]
team_quotas:
  max_agents: 5
  monthly_budget_usd: 1000
  resource_classes: ["nano", "micro", "standard"]
runaway_prevention:
  max_cost_per_hour: 10.0
  max_actions_per_5min: 100
  circuit_breaker_threshold: 3

# Model Configuration  
model_config:
  planner: "gpt-5.2"      # Precision for financial operations
  worker: "claude-opus"   # Fast interactive responses
  embeddings: "telnyx-ai" # General purpose, evaluate domain-specific later

# A2A Skills
a2a_skills:
  - "process-service-order-change"
  - "validate-commitment-terms" 
  - "extract-service-order-pdf"
  - "salesforce-service-order-lookup"

# Capabilities
capabilities:
  - "salesforce-integration"
  - "commitment-manager-api"
  - "pdf-processing"
  - "financial-validation"
  - "audit-logging"

# Secret Management
secrets:
  vault_integration: true
  vault_policies: ["secret/data/team/revenue-ops/*", "database/creds/salesforce-ro"]
  onepassword_vaults: ["Shared-Agent-Global", "Team-revenue-ops", "Agent-{uuid}"]
  
# Audit Configuration  
audit:
  log_all_actions: true
  retention_days: 90
  compliance_archive_years: 7
  sensitive_operations: ["approve", "terminate", "commitment_change"]

# Infrastructure Configuration
deployment:
  cluster: "telnyx-agents-eks"
  namespace: "team-revenue-ops"  
  resource_class: "standard"    # 1.0 CPU, 2GB RAM, 10GB storage, ~$0.07/hr
  networking:
    wireguard_mesh: true
    network_policy: "team-isolation"
    allowed_egress: ["agent-platform", "external-apis"]
  workspace:
    model: "hybrid"
    private_pvc: "10Gi"          # Service order processing workspace
    shared_team_mount: "readonly" # Team knowledge and procedures  
    global_knowledge_mount: "readonly" # Telnyx Storage FUSE mount
  core_services_access:
    - "agent-registry"
    - "a2a-discovery" 
    - "consul"
    - "vault"
    - "onepassword-connect"
    - "knowledge-api"

# Team Onboarding Configuration
onboarding:
  team_pattern: "customer-facing"  # Requires data isolation
  prerequisites:
    namespace: "team-revenue-ops"
    team_lead: "niamh@telnyx.com" 
    quotas:
      persistent_agents: 5
      total_agents: 20
      monthly_budget_usd: 1000
      resource_classes: ["nano", "micro", "standard"]
  data_isolation:
    customer_scoped_permissions: true
    allowed_data_access: ["customer-data:read:by-org-id", "salesforce:service-orders:read-write"]
  knowledge_corpus:
    location: "telnyx-storage://team-revenue-ops/knowledge/"
    markdown_files: ["service-order-policies.md", "rev-ops-procedures.md", "billing-validation-rules.md"]

# Security Configuration (Defense in Depth)
security:
  # Layer 1: Network Security
  network:
    wireguard_mesh: true
    tls_everywhere: true
    network_policy_isolation: true
    egress_restrictions: ["agent-platform", "salesforce.com", "api.telnyx.com"]
    
  # Layer 2: Identity & Authentication  
  identity:
    agent_uuid: "auto-generated"
    vault_auth: true
    vault_token_ttl: "24h"
    a2a_bearer_auth: true
    mtls_enabled: true
    
  # Layer 3: Authorization
  authorization:
    rbac_level: "L3"  # Team Member
    vault_policies: ["secret/data/team/revenue-ops/*"]
    scoped_permissions: ["customer-data:read:by-org-id", "salesforce:service-orders:read-write"]
    spawn_depth_limit: 2
    
  # Layer 4: Audit & Monitoring
  audit:
    immutable_logging: true
    opentelemetry_tracing: true
    cost_tracking: true
    sensitive_operation_logging: ["approve", "terminate", "commitment_change"]
    audit_retention_days: 90
    
  # Layer 5: Containment & Protection
  containment:
    input_sanitization: true
    guardrails_file: "security/GUARDRAILS.md"
    circuit_breakers: true
    auto_quarantine: true
    resource_limits: "standard"
    container_isolation: true
    
# Threat-Specific Mitigations
threat_mitigations:
  prompt_injection:
    input_sanitization: true
    action_approval_required: ["approve", "terminate", "large_commitment_changes"]
  data_exfiltration:
    network_policies: true
    storage_acls: true  
    no_direct_internet_egress: true
  secret_leakage:
    vault_only: true  # Never env vars
    auto_rotating_tokens: true
    namespace_scoping: true
  runaway_operations:
    rate_limits: true
    depth_limits: true
    team_quotas: true
    circuit_breakers: true
```

## Key Architecture Files

1. **`agent_card.py`** - A2A-compliant Agent Card definition
2. **`a2a_service.py`** - Full A2A protocol implementation  
3. **`service_order_workflows.py`** - Core service order business logic
4. **`salesforce_client.py`** - Salesforce integration via sf CLI
5. **`commitment_manager_client.py`** - Commitment Manager REST API
6. **`knowledge_access.py`** - Markdown knowledge reading + work claims
7. **`inter_agent_client.py`** - A2A communication with other agents
8. **`governance.py`** - Permission checks, quota enforcement, spawn authorization
9. **`audit_logger.py`** - Immutable audit trail for all financial operations
10. **`cost_tracker.py`** - Real-time cost monitoring and budget enforcement
11. **`secrets_manager.py`** - Vault + 1Password integration for secure credential access
12. **`deployment/k8s/deployment.yaml`** - EKS deployment configuration
13. **`deployment/k8s/network-policy.yaml`** - Team isolation + agent-platform access
14. **`deployment/k8s/pvc.yaml`** - Persistent volume claims for hybrid workspace
15. **`deployment/k8s/service.yaml`** - Kubernetes service for A2A endpoints
16. **`docker-compose.local.yml`** - Local development stack with A2A discovery and Vault
17. **`deployment/onboarding-checklist.md`** - Team onboarding process checklist
18. **`security/GUARDRAILS.md`** - Financial operation safety checks and approval workflows
19. **`security/threat_detection.py`** - Anomaly detection and auto-quarantine logic
20. **`security/input_sanitizer.py`** - Prompt injection protection for user inputs
21. **`security/rbac.py`** - Role-based access control and permission enforcement

## Implementation Summary

**Architecture Review Complete**: All 12 sections of the Telnyx Agent Architecture analyzed ✅

**Key Findings**:
- **Ready to start development now**: Build A2A-compliant agent using existing patterns
- **Infrastructure timeline**: Core services available Week 1, governance Week 3, production Week 5-8
- **Deployment strategy**: Phased approach aligned with infrastructure rollout
- **Security model**: Enterprise-grade financial operations safety built-in
- **Cost efficiency**: Standard resource class (~$0.07/hr) with team budget controls

**Next Steps**:
1. **Start Phase 1-4 development** using local docker-compose stack
2. **Request team-revenue-ops namespace** from platform admin (Week 1)
3. **Deploy basic version** when a2a-discovery available (Week 1-2)  
4. **Add governance controls** when available (Week 3-4)
5. **Scale to production** with self-service capabilities (Week 5-8)

**Expected Timeline**: 2 weeks development + 4-6 weeks infrastructure-dependent deployment = **6-8 weeks to production Service Order Specialist** 🚀