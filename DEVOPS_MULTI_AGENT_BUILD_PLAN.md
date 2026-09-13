# DevOps Multi-Agent — Build Plan & Progress

## 1. Project Goal

Build a production-oriented **DevOps Multi-Agent system** using:

- Google Gemini
- LangGraph
- Python
- FastAPI
- React + Vite + TypeScript
- Tailwind CSS + shadcn/ui
- Kubernetes
- AWS
- Docker
- Terraform
- GitHub Actions
- Argo CD
- Prometheus + Grafana
- Loki
- OpenTelemetry
- PostgreSQL
- Eventually a microservice architecture

The system will act as a DevOps incident assistant that can understand a user's problem, route it to the correct specialist, use real infrastructure tools, maintain conversation context, and eventually operate as independently deployable services.

---

# 2. Target Architecture

## Current learning architecture

```text
React Frontend
      |
    HTTP
      |
   FastAPI
      |
 LangGraph
      |
 Supervisor
   /   |     K8s AWS Linux
```

## Final microservice architecture

```text
                         ┌──────────────────────┐
                         │   React + shadcn/ui  │
                         └──────────┬───────────┘
                                    │ HTTPS
                                    ▼
                         ┌──────────────────────┐
                         │      API Gateway     │
                         │       / FastAPI       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     Orchestrator      │
                         │      LangGraph        │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
             Kubernetes Agent   AWS Agent      Linux Agent
                    │               │                │
                    ▼               ▼                ▼
                 kubectl          AWS APIs       Linux tools

                    └───────────────┬────────────────┘
                                    ▼
                           PostgreSQL / Memory
                                    │
                                    ▼
                         Observability Platform
                  Prometheus / Grafana / Loki / OTel
```

---

# 3. Repository Structure

Target repository:

```text
DEVOPS_MULTI_AGENT/
├── backend/
│   ├── src/
│   │   └── devops_agents/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── state.py
│   │       ├── models.py
│   │       ├── graph.py
│   │       ├── main.py
│   │       ├── utils.py
│   │       └── agents/
│   │           ├── __init__.py
│   │           ├── kubernetes.py
│   │           ├── aws.py
│   │           └── linux.py
│   ├── tests/
│   ├── .env.example
│   ├── langgraph.json
│   └── pyproject.toml
│
├── frontend/
│   └── React/Vite application
│
├── docs/
│
├── .gitignore
├── README.md
└── VERSION
```

---

# 4. Development Principles

## Cost & LLM Usage Management

This project must be developed with **LLM cost awareness from day one**.

Rules:

- Do not perform heavy or repeated live Gemini API testing during development.
- Prefer unit tests with mocked/fake LLM responses for routing, state transitions, graph behavior, API behavior, and error handling.
- Use real Gemini calls only for small, deliberate smoke tests when validating actual model integration.
- Never put a Gemini API call inside a test suite that runs repeatedly unless the test is explicitly marked as a small live/integration test.
- Avoid large prompts and unnecessary conversation history.
- Track token usage and model latency where practical.
- Keep model selection configurable through `LLM_MODEL`.
- Add clear separation between unit tests and live LLM integration tests.
- Never instruct coding agents such as Antigravity to run heavy Gemini test suites, repeated live API calls, load tests, or large E2E tests.
- The user will perform deliberate real-world/live testing when required.

### Testing Cost Strategy

```text
Unit tests
   ↓
Mock LLM / deterministic responses
   ↓
Fast + free/near-free validation

Small integration smoke test
   ↓
1–few real Gemini calls
   ↓
Validate model/API integration

Manual real-world testing
   ↓
User-controlled
```

Future production cost controls should include:

- token budgets
- maximum conversation history
- summarization/compaction
- caching where appropriate
- model routing by task complexity
- rate limiting
- per-user/per-thread usage limits
- telemetry for token usage and cost
- retry limits
- timeout limits
- protection against runaway agent/tool loops

---

Keep the implementation:

- Simple
- Readable
- Human-written
- Production-minded
- Easy to troubleshoot
- Avoid unnecessary abstractions
- Avoid premature microservices
- Build one feature at a time
- Test each phase before moving forward

Git workflow:

```text
main
  |
  └── feature/<feature-name>
          |
          ├── implement
          ├── test
          ├── commit
          ├── push
          ├── PR
          └── merge
```

Use semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Examples:

```text
v0.2.0
v0.2.0
v0.3.0
```

Docker images will later use immutable version tags rather than relying on `latest`.

---

# 5. Phase-by-Phase Roadmap

## Phase 1 — Foundation

Status: COMPLETE

Version: `v0.2.0`

Implemented:

- Python project structure
- Google Gemini integration
- LangChain Google Gemini integration
- LangGraph `StateGraph`
- Supervisor
- Kubernetes agent
- AWS agent
- Linux agent
- Basic routing
- CLI application
- Basic tests
- Environment configuration

Architecture:

```text
User
 ↓
Supervisor
 ↓
Kubernetes / AWS / Linux
 ↓
Response
```

Git:

```text
feature/foundation-gemini-three-agents
```

Release:

```text
v0.2.0
```

---

## Phase 2 — Structured Agent Routing

Status: COMPLETE and MERGED

Version: `v0.2.0`

Implemented:

- Pydantic routing model
- `RoutingDecision`
- `Literal` based allowed agents
- Gemini structured output
- Deterministic routing contract
- Cleaner supervisor behavior
- Error handling improvements

Routing model:

```python
class RoutingDecision(BaseModel):
    agent: Literal["kubernetes", "aws", "linux"]
    reason: str
```

Git:

```text
feature/structured-agent-routing
```

Release:

```text
v0.2.0
```

---

# Phase 3 — Conversation State & Short-Term Memory

Status: IN PROGRESS

Planned version: `v0.3.0`

Goal:

Turn the current single-request system into a real multi-turn conversation.

Current work:

- Introduce LangGraph `messages`
- Use `HumanMessage` / `AIMessage`
- Make the supervisor consume message state
- Make specialist agents consume message state
- Add `InMemorySaver`
- Introduce `thread_id`
- Verify conversation persistence within a thread
- Verify separate threads remain isolated

Target:

```text
Thread: conversation-123

User:
"What pods are failing?"

Assistant:
"payment-api has 3 failing pods."

User:
"Why?"

Assistant:
"The pod events indicate..."
```

Important concepts to learn:

```text
State
  ↓
messages
  ↓
Reducers / add_messages
  ↓
Checkpoint
  ↓
thread_id
  ↓
Multi-turn conversation
```

Do NOT introduce PostgreSQL yet.

First understand LangGraph checkpointing using `InMemorySaver`.

After Phase 3:

```text
v0.3.0
```

---

# Phase 4 — Frontend

Goal:

Build the actual user interface.

Technology:

- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui

Features:

- Chat interface
- Message history
- Agent indicator
- Loading state
- Error state
- New conversation
- Conversation/thread ID handling
- Clean DevOps dashboard style
- Responsive layout

Target:

```text
Browser
   ↓
React
   ↓
FastAPI
```

Version:

```text
v0.4.0
```

---

# Phase 5 — FastAPI Backend

Status: COMPLETE

Version: `v0.5.0`

Goal:

Expose the LangGraph application through a clean API.

Endpoints initially:

```text
POST /chat
GET  /health
```

Potential later endpoints:

```text
GET    /conversations
GET    /conversations/{id}
DELETE /conversations/{id}
```

Implement:

- Request/response models
- Pydantic validation
- `thread_id`
- Request IDs
- Error handling
- Logging
- CORS
- Health endpoint

Architecture:

```text
React
 ↓
FastAPI
 ↓
LangGraph
```

Version:

```text
v0.5.0
```

---

# Phase 6 — Real DevOps Agent Tools

Goal:

Move from LLM-only answers to real infrastructure investigation.

## Kubernetes Agent

Potential tools:

```text
kubectl get pods
kubectl describe pod
kubectl get events
kubectl logs
kubectl get deployments
kubectl get services
kubectl get nodes
```

## AWS Agent

Potential tools:

```text
EC2
EKS
CloudWatch
IAM
S3
VPC
Security Groups
ELB
Auto Scaling
Route53
```

## Linux Agent

Potential tools:

```text
ps
top
free
df
du
systemctl
journalctl
ss
ip
```

Important security principle:

```text
READ
 ↓
ANALYZE
 ↓
PROPOSE
 ↓
OPTIONAL APPROVAL
 ↓
WRITE/REMEDIATION
```

Do not immediately allow destructive actions.

Version:

```text
v0.6.0
```

---

# Phase 7 — Advanced LangGraph Orchestration

Goal:

Move beyond simple supervisor → specialist routing.

Explore:

- Subgraphs
- Parallel execution
- Agent handoffs
- Planner
- Reviewer
- Tool selection
- Retry behavior
- State transitions
- Human approval
- Conditional execution
- Failure recovery

Potential architecture:

```text
                  Supervisor
                      |
                   Planner
                      |
             ┌────────┼────────┐
             ▼        ▼        ▼
            K8s      AWS      Linux
             │        │        │
             └────────┼────────┘
                      ▼
                   Reviewer
                      |
              ┌───────┴───────┐
              ▼               ▼
           Resolve          Human
```

Version:

```text
v0.7.0
```

---

# Phase 9 — Self-Healing / Controlled Remediation

Goal:

Turn the system from an incident **diagnosis assistant** into a controlled incident **remediation system**.

Self-healing is NOT simply:

```text
Alert → LLM → execute random command
```

The intended flow is:

```text
Detect
  ↓
Investigate
  ↓
Identify probable cause
  ↓
Generate remediation plan
  ↓
Validate safety / policy
  ↓
Approval gate (when required)
  ↓
Execute bounded remediation
  ↓
Verify outcome
  ↓
Rollback if verification fails
  ↓
Record audit trail
```

Examples:

```text
Kubernetes:
CrashLoopBackOff
    ↓
inspect pod/events/logs
    ↓
identify likely cause
    ↓
restart/rollback only when policy permits
    ↓
verify rollout

AWS:
unhealthy workload
    ↓
inspect CloudWatch/EC2/EKS state
    ↓
propose remediation
    ↓
approval/policy check
    ↓
execute allowed action
    ↓
verify recovery

Linux:
high disk usage
    ↓
inspect filesystem
    ↓
identify safe cleanup candidate
    ↓
approval/policy check
    ↓
bounded cleanup
    ↓
verify disk recovery
```

Safety requirements:

- Read-only investigation by default
- Explicit tool allowlists
- Action allowlists
- Human approval for risky operations
- Dry-run mode
- Timeouts
- Idempotent actions where possible
- Maximum retry/action limits
- Rollback strategy
- Post-action verification
- Full audit logging
- Never allow arbitrary shell commands from the LLM
- Never allow unrestricted AWS/Kubernetes destructive operations

This phase should teach:

- Agentic remediation
- Tool safety
- Policy enforcement
- Human-in-the-loop
- Idempotency
- Rollback
- Verification
- Incident automation
- Failure containment

Version:

```text
v0.2.0
```

---

# Phase 10 — Persistent Memory

Goal:

Replace development-only memory with production persistence.

Current:

```text
InMemorySaver
```

Production:

```text
PostgreSQL
```

Learn:

- LangGraph checkpoints
- Threads
- Checkpoint persistence
- Conversation retrieval
- Database-backed state
- Connection management
- Multi-user isolation
- Retention
- Database migrations

Architecture:

```text
LangGraph
    |
PostgreSQL
    |
Conversation checkpoints
```

Version:

```text
v0.2.0
```

---

# Phase 10 — Microservices

Only now split the application.

Target:

```text
services/
├── orchestrator/
├── kubernetes-agent/
├── aws-agent/
└── linux-agent/
```

Communication:

```text
Frontend
   ↓
API
   ↓
Orchestrator
   ├── HTTP → Kubernetes Agent
   ├── HTTP → AWS Agent
   └── HTTP → Linux Agent
```

Learn:

- Service boundaries
- API contracts
- HTTP communication
- Timeouts
- Retries
- Service discovery
- Authentication
- Failure isolation
- Distributed tracing

Version:

```text
v0.2.0
```

---

# Phase 11 — Docker & Container Engineering

Goal:

Containerize every service properly.

Learn:

- Dockerfiles
- Multi-stage builds
- Small images
- Non-root users
- Health checks
- `.dockerignore`
- Environment variables
- Secrets
- Image versioning
- Container networking
- Local Compose environment

Image naming:

```text
devops-multi-agent-orchestrator:0.9.0
devops-multi-agent-kubernetes-agent:0.9.0
devops-multi-agent-aws-agent:0.9.0
devops-multi-agent-linux-agent:0.9.0
```

Later:

```text
Docker Hub
```

Version:

```text
v0.10.0
```

---

# Phase 12 — CI/CD

Goal:

Build a production-style GitHub Actions pipeline.

Pipeline:

```text
Git Push / PR
     ↓
Lint
     ↓
Unit Tests
     ↓
Security Scan
     ↓
Docker Build
     ↓
Image Scan
     ↓
Docker Push
```

Tools:

- GitHub Actions
- Ruff
- Pytest
- Trivy
- Gitleaks
- Docker
- Docker Hub

Later:

```text
Terraform validation
Terraform plan
Terraform security checks
```

Version:

```text
v0.11.0
```

---

# Phase 13 — AWS Infrastructure with Terraform

Goal:

Create reproducible infrastructure.

Potential infrastructure:

```text
VPC
├── Public Subnets
├── Private Subnets
├── NAT
├── Security Groups
│
├── EKS
│
├── Load Balancer
│
├── S3
├── RDS/PostgreSQL
├── IAM
├── Route53
├── ACM
└── CloudWatch
```

Learn:

- Terraform modules
- Remote state
- S3 backend
- State locking
- IAM
- Variables
- Outputs
- Workspaces/environment strategy
- Plan/apply workflow
- CI validation
- Drift detection

Version:

```text
v0.12.0
```

---

# Phase 14 — Kubernetes Deployment

Goal:

Deploy the complete application to Kubernetes.

Learn:

- Deployments
- Services
- ConfigMaps
- Secrets
- Ingress
- ServiceAccounts
- RBAC
- HPA
- PDB
- Resource requests/limits
- Probes
- Storage
- Network policies

Later:

```text
EKS
```

DNS targets eventually include:

```text
app.example.com
api.example.com
grafana.example.com
prometheus.example.com
loki.example.com
argocd.example.com
```

Version:

```text
v0.13.0
```

---

# Phase 15 — Helm

Goal:

Package Kubernetes deployment cleanly.

Structure:

```text
helm/
└── devops-multi-agent/
    ├── Chart.yaml
    ├── values.yaml
    ├── values-dev.yaml
    ├── values-prod.yaml
    └── templates/
```

Learn:

- Templates
- Values
- Environment overrides
- Secrets
- ConfigMaps
- Dependencies
- Helm upgrades
- Rollbacks

Version:

```text
v0.14.0
```

---

# Phase 16 — Argo CD / GitOps

Goal:

Move deployment responsibility from CI to GitOps.

Architecture:

```text
Developer
   ↓
GitHub
   ↓
GitHub Actions
   ↓
Build + Push Image
   ↓
Update deployment configuration
   ↓
Git repository
   ↓
Argo CD
   ↓
EKS
```

Learn:

- Applications
- AppProjects
- Sync
- Auto-sync
- Self-heal
- Pruning
- Rollbacks
- GitOps repository structure

Version:

```text
v0.15.0
```

---

# Phase 17 — Observability

Goal:

Make the platform observable like a production system.

Metrics:

```text
Prometheus
   ↓
Grafana
```

Logs:

```text
Loki
   ↓
Grafana
```

Traces:

```text
OpenTelemetry
   ↓
Tempo / compatible backend
```

Track:

- Request latency
- Agent latency
- LLM latency
- Token usage
- Error rate
- Tool execution
- Routing decisions
- Kubernetes API failures
- AWS API failures
- Linux command failures
- Agent success rate

Version:

```text
v0.16.0
```

---

# Phase 18 — AI/LLM Observability

Goal:

Understand the AI system itself.

Track:

```text
User Request
    ↓
Routing
    ↓
LLM
    ↓
Tool
    ↓
Agent
    ↓
Response
```

Metrics:

- Token usage
- Model latency
- Cost
- Prompt failures
- Tool failures
- Routing accuracy
- Agent success rate
- Retry rate
- Hallucination/grounding signals

Potential tooling:

- LangSmith
- OpenTelemetry
- Prometheus
- Grafana

Version:

```text
v0.17.0
```

---

# Phase 19 — Security / DevSecOps

Implement:

- IAM least privilege
- Kubernetes RBAC
- Network policies
- Secrets management
- OIDC for GitHub Actions
- Trivy
- Gitleaks
- Terraform security scanning
- Container hardening
- Non-root containers
- API authentication
- Rate limiting
- Audit logs
- Human approval for dangerous actions

Version:

```text
v0.18.0
```

---

# Phase 20 — Reliability & Production Engineering

Learn and implement:

- Timeouts
- Retries
- Backoff
- Circuit breakers
- Idempotency
- Graceful shutdown
- Readiness/liveness
- Pod disruption budgets
- Autoscaling
- Failure recovery
- Disaster recovery
- Backup/restore
- Database resilience
- Multi-AZ architecture
- Cost optimization

Version:

```text
v0.19.0
```

---

# Phase 21 — Production Release

Final target:

```text
v1.0.0
```

Production architecture:

```text
                         Internet
                            │
                            ▼
                       Route 53
                            │
                            ▼
                         ACM/TLS
                            │
                            ▼
                     Load Balancer
                            │
                            ▼
                    ┌───────────────┐
                    │ React Frontend│
                    └───────┬───────┘
                            │
                            ▼
                       FastAPI API
                            │
                            ▼
                     Orchestrator
                      LangGraph
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           K8s Agent      AWS Agent     Linux Agent
              │             │             │
              └─────────────┼─────────────┘
                            │
                    PostgreSQL Memory
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
             Observability          Audit
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
   Prometheus   Loki      OTel
       │         │         │
       └─────────┼─────────┘
                 ▼
              Grafana
```

---

# 6. Current Git / Version State

Completed:

```text
v0.2.0  Phase 1
v0.2.0  Phase 2
```

Current branch:

```text
feature/langgraph-conversation-memory
```

Current work:

```text
Phase 3
Conversation State + Short-Term Memory
```

---

# 7. Current Phase 3 Implementation Plan

Implement in this exact order:

### Step 1
Add:

```python
messages: Annotated[list[BaseMessage], add_messages]
```

### Step 2
Change supervisor to read:

```python
state["messages"][-1]
```

### Step 3
Change Kubernetes/AWS/Linux agents to use message state.

### Step 4
Ensure agent responses are appended as `AIMessage`.

### Step 5
Run the existing tests and update them for the new state contract.

### Step 6
Add:

```python
InMemorySaver()
```

to graph compilation.

### Step 7
Invoke graph with:

```python
config = {
    "configurable": {
        "thread_id": "demo-123"
    }
}
```

### Step 8
Test two-turn conversation.

### Step 9
Test two different threads and verify isolation.

### Step 10
Clean up state and CLI code.

### Step 11
Commit:

```text
feat: add LangGraph conversation memory
```

### Step 12
Push branch and create PR.

### Step 13
Merge PR.

### Step 14
Release:

```text
v0.3.0
```

---

# 8. Phase 3 Success Criteria

Phase 3 is NOT complete until all of these work:

```text
[ ] Application starts
[ ] First message works
[ ] Second message can reference first message
[ ] Same thread preserves conversation state
[ ] Different thread does not see previous conversation
[ ] Checkpoints are actually created
[ ] Existing agent routing still works
[ ] Kubernetes routing works
[ ] AWS routing works
[ ] Linux routing works
[ ] Tests pass
[ ] Git working tree is clean
[ ] PR merged
[ ] v0.3.0 tagged
```

---

# 9. Important Future Rule

Do not jump directly to the final architecture.

We intentionally progress:

```text
Single Python application
        ↓
Stateful LangGraph
        ↓
Frontend + API
        ↓
Real DevOps tools
        ↓
Advanced orchestration
        ↓
Persistent memory
        ↓
Microservices
        ↓
Docker
        ↓
CI/CD
        ↓
Terraform
        ↓
Kubernetes
        ↓
Argo CD
        ↓
Observability
        ↓
Security
        ↓
Production
```

This lets the project demonstrate both:

1. AI/Agent engineering
2. Senior-level DevOps/Cloud engineering
