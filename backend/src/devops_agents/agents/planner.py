"""
Planner — Phase 7

Rule-based, zero-LLM-cost node that converts the supervisor's routing
decision into an ordered execution plan: plan = ["kubernetes", "aws", ...].

Design principles:
  - No additional Gemini / LLM call.
  - Uses simple keyword matching on the user query to detect cross-domain
    investigation needs (e.g. K8s + EC2, K8s + Linux).
  - Always produces at least one-item plan from `selected_agent`.
  - Respects the order: Kubernetes first (app layer), then AWS (infra layer),
    then Linux (OS layer), matching the natural investigation hierarchy.
"""

from langchain_core.messages import HumanMessage

from devops_agents.state import AgentState


# ---------------------------------------------------------------------------
# Keyword maps for cross-domain query detection
# ---------------------------------------------------------------------------

_KUBERNETES_SIGNALS = {
    "pod", "pods", "deployment", "deployments", "replicaset", "service",
    "ingress", "container", "kubectl", "crashloopbackoff", "imagepullbackoff",
    "pending", "evicted", "oomkilled", "kubernetes", "k8s", "namespace",
    "node", "nodes", "cluster", "helm", "daemonset", "statefulset",
}

_AWS_SIGNALS = {
    "ec2", "eks", "s3", "iam", "vpc", "cloudwatch", "alb", "elb",
    "auto scaling", "route53", "rds", "lambda", "aws", "instance",
    "security group", "subnet", "nat", "ebs", "ami",
}

_LINUX_SIGNALS = {
    "disk", "memory", "cpu", "process", "systemd", "journalctl",
    "filesystem", "mount", "swap", "uptime", "cron", "kernel",
    "linux", "os", "host", "ulimit", "inode", "load average",
}

_DOMAIN_ORDER = ["kubernetes", "aws", "linux"]


def _extract_user_query(state: AgentState) -> str:
    """Return the text of the most recent HumanMessage in state."""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            return (msg.content if isinstance(msg.content, str) else str(msg.content)).lower()
    return ""


def _detect_domains(query: str) -> list[str]:
    """
    Scan the query for domain keywords and return an ordered list of
    matching specialist names (kubernetes → aws → linux).
    """
    detected: set[str] = set()

    for token in _KUBERNETES_SIGNALS:
        if token in query:
            detected.add("kubernetes")
            break

    for token in _AWS_SIGNALS:
        if token in query:
            detected.add("aws")
            break

    for token in _LINUX_SIGNALS:
        if token in query:
            detected.add("linux")
            break

    # Return in canonical priority order
    return [d for d in _DOMAIN_ORDER if d in detected]


def planner(state: AgentState) -> dict:
    """
    Planner node.

    Returns:
        plan          — ordered list of specialist agent names
        plan_index    — always reset to 0 (start of plan)
        selected_agent — first specialist in the plan (used by route_to_specialist)

    Strategy:
        1. If the query clearly mentions multiple domains → multi-agent plan.
        2. Otherwise fall back to the supervisor's single routing decision.
    """
    supervisor_choice = state.get("selected_agent", "kubernetes")
    query = _extract_user_query(state)

    detected = _detect_domains(query)

    if len(detected) >= 2:
        # Cross-domain query: run at most 2 detected specialists in priority order
        plan = detected[:2]
    elif len(detected) == 1:
        # Single-domain detected from keywords — trust that over supervisor
        # only if supervisor also agrees, otherwise defer to supervisor
        if supervisor_choice in detected:
            plan = detected
        else:
            # Supervisor knows better for ambiguous queries
            plan = [supervisor_choice]
    else:
        # No keyword signals found — fall back to supervisor's choice
        plan = [supervisor_choice]

    return {
        "plan": plan,
        "plan_index": 0,
        "selected_agent": plan[0],
    }
