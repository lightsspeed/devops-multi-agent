from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from devops_agents.agents.aws import aws_agent
from devops_agents.agents.kubernetes import kubernetes_agent
from devops_agents.agents.linux import linux_agent
from devops_agents.config import GEMINI_API_KEY, LLM_MODEL
from devops_agents.state import AgentState
from devops_agents.utils import extract_text


supervisor_model = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GEMINI_API_KEY,
)


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

Return ONLY ONE of these exact values:

kubernetes
aws
linux
"""


def supervisor(state: AgentState) -> dict:
    response = supervisor_model.invoke(
        [
            ("system", SUPERVISOR_PROMPT),
            ("human", state["user_query"]),
        ]
    )

    selected_agent = extract_text(response.content).lower()

    valid_agents = {
        "kubernetes",
        "aws",
        "linux",
    }

    if selected_agent not in valid_agents:
        raise ValueError(
            f"Supervisor returned invalid agent: {selected_agent}"
        )

    return {
        "selected_agent": selected_agent,
    }


def route_agent(state: AgentState) -> str:
    return state["selected_agent"]


builder = StateGraph(AgentState)


# Nodes
builder.add_node("supervisor", supervisor)
builder.add_node("kubernetes", kubernetes_agent)
builder.add_node("aws", aws_agent)
builder.add_node("linux", linux_agent)


# START → Supervisor
builder.add_edge(
    START,
    "supervisor",
)


# Supervisor → selected specialist
builder.add_conditional_edges(
    "supervisor",
    route_agent,
    {
        "kubernetes": "kubernetes",
        "aws": "aws",
        "linux": "linux",
    },
)


# Specialist → END
builder.add_edge(
    "kubernetes",
    END,
)

builder.add_edge(
    "aws",
    END,
)

builder.add_edge(
    "linux",
    END,
)


# Compile
graph = builder.compile()