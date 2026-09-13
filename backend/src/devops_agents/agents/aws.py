from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from devops_agents.config import GEMINI_API_KEY, LLM_MODEL
from devops_agents.state import AgentState
from devops_agents.tools import AWS_TOOLS
from devops_agents.utils import extract_text


SYSTEM_PROMPT = """
You are a senior AWS cloud engineer.

Your responsibility is to analyze AWS infrastructure questions and incidents.

YOU HAVE LIVE READ-ONLY ACCESS TO AWS via tools:
- aws_describe_instances: describe EC2 instances in a region
- aws_list_s3_buckets: list S3 buckets in account
- aws_get_cloudwatch_alarms: get CloudWatch metric alarms in a region

MANDATORY INSTRUCTION:
When the user asks about AWS resources, EC2 instances, S3, or alarms, YOU MUST CALL THE APPROPRIATE TOOL FIRST to fetch real-time AWS data. NEVER claim you do not have access to AWS resources.

When providing your final answer:
1. Clearly state the facts returned by the tools.
2. Provide:
   - Likely cause
   - Evidence checked from tool output
   - AWS CLI / console checks
   - Recommended remediation (READ -> ANALYZE -> PROPOSE)
"""


model = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GEMINI_API_KEY,
)
model_with_tools = model.bind_tools(AWS_TOOLS)
tools_by_name = {t.name: t for t in AWS_TOOLS}


def aws_agent(state: AgentState) -> dict:
    messages = [("system", SYSTEM_PROMPT)] + list(state.get("messages", []))
    response = model_with_tools.invoke(messages)

    tool_outputs = []
    if hasattr(response, "tool_calls") and response.tool_calls:
        messages.append(response)
        for tool_call in response.tool_calls:
            t_name = tool_call.get("name")
            t_args = tool_call.get("args", {})
            t_id = tool_call.get("id", "call_1")

            tool_obj = tools_by_name.get(t_name)
            if tool_obj:
                out = tool_obj.invoke(t_args)
            else:
                out = f"Error: Tool '{t_name}' not available."

            out_str = str(out)
            tool_outputs.append(f"### Tool Execution Result (`{t_name}`)\n```text\n{out_str}\n```")
            messages.append(ToolMessage(content=out_str, tool_call_id=t_id))

        try:
            final_response = model.invoke(messages)
            text = extract_text(final_response.content)
        except Exception:
            text = ""

        if not text or len(text.strip()) == 0:
            text = "\n\n".join(tool_outputs)
    else:
        text = extract_text(response.content)
        if not text or len(text.strip()) == 0:
            out_str = tools_by_name["aws_describe_instances"].invoke({"region": "us-east-1"})
            text = f"### Live AWS Status (`aws_describe_instances`)\n```text\n{out_str}\n```"

    return {
        "selected_agent": "aws",
        "agent_response": text,
        "messages": [AIMessage(content=text)],
    }

