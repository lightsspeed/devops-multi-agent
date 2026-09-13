from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from devops_agents.config import GEMINI_API_KEY, LLM_MODEL
from devops_agents.state import AgentState
from devops_agents.utils import extract_text


SYSTEM_PROMPT = """
You are a senior Kubernetes platform engineer.

Your responsibility is to analyze Kubernetes-related
questions and incidents.

Focus on:

- Pods
- Deployments
- ReplicaSets
- Services
- Ingress
- Nodes
- Scheduling
- Resource requests and limits
- Probes
- Networking
- Kubernetes events

IMPORTANT:

You do not currently have access to a real Kubernetes cluster.

Never claim that you inspected a real cluster.

Clearly distinguish between:
- facts provided by the user
- likely causes
- evidence that should be collected

When answering an incident, provide:

1. Likely cause
2. Evidence to check
3. Troubleshooting commands
4. Possible remediation
5. Verification steps
"""


model = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GEMINI_API_KEY,
)


def kubernetes_agent(state: AgentState) -> dict:
    response = model.invoke(
        [("system", SYSTEM_PROMPT)] + list(state.get("messages", []))
    )
    text = extract_text(response.content)

    return {
        "selected_agent": "kubernetes",
        "agent_response": text,
        "messages": [AIMessage(content=text)],
    }