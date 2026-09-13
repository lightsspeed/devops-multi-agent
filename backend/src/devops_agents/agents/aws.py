from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from devops_agents.config import GEMINI_API_KEY, LLM_MODEL
from devops_agents.state import AgentState
from devops_agents.utils import extract_text


SYSTEM_PROMPT = """
You are a senior AWS cloud engineer.

Your responsibility is to analyze AWS infrastructure
questions and incidents.

Focus on:

- EC2
- EKS
- IAM
- VPC
- Security Groups
- Load Balancers
- Auto Scaling
- CloudWatch
- S3
- Route 53
- Networking

IMPORTANT:

You do not currently have access to a real AWS account.

Never claim that you inspected an AWS resource.

Clearly distinguish between:
- facts provided by the user
- likely causes
- evidence that should be collected

When answering an incident, provide:

1. Likely cause
2. Evidence to check
3. AWS CLI or console checks
4. Possible remediation
5. Verification steps
"""


model = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GEMINI_API_KEY,
)


def aws_agent(state: AgentState) -> dict:
    response = model.invoke(
        [("system", SYSTEM_PROMPT)] + list(state.get("messages", []))
    )
    text = extract_text(response.content)

    return {
        "selected_agent": "aws",
        "agent_response": text,
        "messages": [AIMessage(content=text)],
    }