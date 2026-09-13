"""
graph.py — Phase 7 LangGraph Orchestration

New pipeline:

    START
      └─► supervisor        (LLM routing decision — unchanged)
            └─► planner     (rule-based; builds ordered plan list)
                  └─► run_specialist   (executes plan[plan_index] specialist)
                        └─► advance_plan   (moves plan_index forward)
                              ├─(more specialists)─► run_specialist (loop)
                              └─(plan complete)───► reviewer
                                                       ├─(pass, no risk)──► END
                                                       ├─(pass, risky)────► human_gate → END
                                                       └─(fail, retry<1)──► run_specialist → ...

Sequential multi-agent execution:
  The planner outputs plan = ["kubernetes", "aws"] etc.
  run_specialist calls the agent at plan[plan_index].
  advance_plan increments plan_index.
  Once plan_index >= len(plan), routing goes to reviewer.

Retry guard:
  review_retry_count is capped at 1 by the Reviewer itself.
  The graph routes back to run_specialist only when review_passed=False
  AND review_retry_count <= 1 (enforced inside reviewer.py).
"""

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from devops_agents.agents.aws import aws_agent
from devops_agents.agents.kubernetes import kubernetes_agent
from devops_agents.agents.linux import linux_agent
from devops_agents.agents.planner import planner
from devops_agents.agents.reviewer import reviewer, _APPROVAL_BANNER
from devops_agents.config import GEMINI_API_KEY, LLM_MODEL
from devops_agents.models import RoutingDecision
from devops_agents.state import AgentState


# ---------------------------------------------------------------------------
# Supervisor (unchanged from Phase 6)
# ---------------------------------------------------------------------------

supervisor_model = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GEMINI_API_KEY,
).with_structured_output(RoutingDecision)


SUPERVISOR_PROMPT = """
You are the routing supervisor for a DevOps multi-agent system.

Your job is to select the most appropriate specialist.

Available specialists:

kubernetes
aws
linux

Routing rules:

KUBERNETES:
- Pods
- Deployments
- ReplicaSets
- Services
- Ingress
- Scheduling
- Nodes
- Kubernetes networking
- Kubernetes resources
- Container image pull errors / CrashLoopBackOff

AWS:
- EC2
- EKS infrastructure
- IAM
- VPC
- Security Groups
- S3
- CloudWatch
- Load Balancers
- Auto Scaling
- Route 53
- AWS infrastructure

LINUX:
- CPU
- Memory
- Disk
- Processes
- systemd
- Filesystems
- Linux permissions
- Linux networking
- Linux OS issues

Choose the specialist that is most appropriate for the user's query.

Also provide a short reason for your choice.
"""


def supervisor(state: AgentState) -> dict:
    latest_user_query = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            latest_user_query = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    if not latest_user_query and state.get("messages"):
        latest_user_query = str(state["messages"][-1].content)

    decision = supervisor_model.invoke(
        [
            ("system", SUPERVISOR_PROMPT),
            ("human", latest_user_query or "DevOps status check"),
        ]
    )

    agent_choice = decision.agent.lower()
    if agent_choice not in ["kubernetes", "aws", "linux"]:
        agent_choice = "kubernetes"

    return {
        "selected_agent": agent_choice,
    }


# ---------------------------------------------------------------------------
# Specialist dispatch
# ---------------------------------------------------------------------------

_SPECIALIST_MAP = {
    "kubernetes": kubernetes_agent,
    "aws": aws_agent,
    "linux": linux_agent,
}


def run_specialist(state: AgentState) -> dict:
    """
    Execute the specialist at plan[plan_index].
    Falls back to selected_agent if plan is missing.
    """
    plan = state.get("plan") or [state.get("selected_agent", "kubernetes")]
    idx = state.get("plan_index", 0)
    agent_name = plan[idx] if idx < len(plan) else plan[-1]

    agent_fn = _SPECIALIST_MAP.get(agent_name)
    if agent_fn is None:
        return {
            "agent_response": f"No specialist found for '{agent_name}'.",
            "selected_agent": agent_name,
        }

    # Prepare input state with accumulated findings and review notes context
    spec_state = dict(state)
    additional_context = []
    
    findings = list(state.get("investigation_findings") or [])
    if findings:
        context_str = "\n\n".join([f"### Previous Specialist Findings ({i+1})\n{f}" for i, f in enumerate(findings)])
        additional_context.append(f"ACCUMULATED INVESTIGATION CONTEXT:\n{context_str}")
        
    review_notes = state.get("review_notes", "")
    if review_notes and not state.get("review_passed", True):
        additional_context.append(f"REVIEWER FEEDBACK / REJECTION REASON:\n{review_notes}\nPlease improve your response to address this feedback.")

    if additional_context:
        combined_prompt_addon = "\n\n".join(additional_context)
        msgs = list(spec_state.get("messages", []))
        msgs.append(HumanMessage(content=f"[SYSTEM CONTEXT UPDATE]\n{combined_prompt_addon}"))
        spec_state["messages"] = msgs

    result = agent_fn(spec_state)
    result["selected_agent"] = agent_name
    
    # Manage investigation_findings accumulation / retry handling (D1 & D2)
    new_response = result.get("agent_response", "")
    current_findings = list(state.get("investigation_findings") or [])
    
    if not state.get("review_passed", True) and state.get("review_retry_count", 0) > 0 and len(current_findings) >= idx + 1:
        # Replacement on retry for the current specialist
        current_findings[idx] = f"[{agent_name.upper()} AGENT FINDINGS]\n{new_response}"
    else:
        # Appending new specialist finding
        current_findings.append(f"[{agent_name.upper()} AGENT FINDINGS]\n{new_response}")

    result["investigation_findings"] = current_findings
    
    # Format combined agent_response if multiple findings exist or if part of a multi-agent plan
    if len(current_findings) > 1:
        combined_resp = "# Correlated Multi-Agent Investigation Report\n\n" + "\n\n---\n\n".join(current_findings)
        result["agent_response"] = combined_resp
        
    return result


def advance_plan(state: AgentState) -> dict:
    """
    Increment plan_index after a specialist completes.
    The routing function will check whether more specialists remain.
    """
    return {"plan_index": state.get("plan_index", 0) + 1}


# ---------------------------------------------------------------------------
# Human gate (banner-only, Phase 7)
# ---------------------------------------------------------------------------

def human_gate(state: AgentState) -> dict:
    """
    Banner-only human approval gate (Phase 7).
    No interrupt() — simply ensures the approval banner is present
    and returns to END. Real interrupt-based approval is Phase 9.
    """
    response = state.get("agent_response", "")
    if "OPERATOR APPROVAL REQUIRED" not in response:
        response = response + _APPROVAL_BANNER
    return {"agent_response": response}


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_agent(state: AgentState) -> str:
    """Used by supervisor → planner routing (legacy hook kept for tests)."""
    return state["selected_agent"]


def route_after_advance(state: AgentState) -> str:
    """
    After advance_plan, decide whether to run the next specialist or review.
    """
    plan = state.get("plan") or []
    idx = state.get("plan_index", 0)
    if idx < len(plan):
        return "run_specialist"
    return "reviewer"


def route_after_reviewer(state: AgentState) -> str:
    """
    After reviewer:
        - Failed + retry budget remaining  → run_specialist (retry current agent)
        - Passed + risky                   → human_gate
        - Passed + clean                   → END
    """
    if not state.get("review_passed", True):
        # Reviewer already incremented review_retry_count and guarded the loop
        # Route back to the last specialist for one retry
        return "run_specialist"

    if state.get("requires_approval", False):
        return "human_gate"

    return END


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

builder = StateGraph(AgentState)

# Nodes
builder.add_node("supervisor", supervisor)
builder.add_node("planner", planner)
builder.add_node("run_specialist", run_specialist)
builder.add_node("advance_plan", advance_plan)
builder.add_node("reviewer", reviewer)
builder.add_node("human_gate", human_gate)

# Edges
builder.add_edge(START, "supervisor")
builder.add_edge("supervisor", "planner")
builder.add_edge("planner", "run_specialist")
builder.add_edge("run_specialist", "advance_plan")

builder.add_conditional_edges(
    "advance_plan",
    route_after_advance,
    {
        "run_specialist": "run_specialist",
        "reviewer": "reviewer",
    },
)

builder.add_conditional_edges(
    "reviewer",
    route_after_reviewer,
    {
        "run_specialist": "run_specialist",
        "human_gate": "human_gate",
        END: END,
    },
)

builder.add_edge("human_gate", END)

# Compile with memory checkpointer (InMemorySaver — Phase 10 will replace with PostgreSQL)
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)