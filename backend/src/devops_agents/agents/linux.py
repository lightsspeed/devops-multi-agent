from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from devops_agents.config import GEMINI_API_KEY, LLM_MODEL
from devops_agents.state import AgentState
from devops_agents.tools import LINUX_TOOLS
from devops_agents.utils import extract_text


SYSTEM_PROMPT = """
You are a senior Linux SRE.

Your responsibility is to analyze Linux infrastructure and operating system incidents.

YOU HAVE LIVE READ-ONLY ACCESS TO LINUX SYSTEM INSPECTION via tools:
- linux_system_status: check memory (free), disk (df), and uptime
- linux_check_process: check if a process is running
- linux_check_logs: check systemd service logs (journalctl)

MANDATORY INSTRUCTION:
When the user asks about Linux memory, disk, processes, or logs, YOU MUST CALL THE APPROPRIATE TOOL FIRST to fetch real-time system data.

When providing your final answer:
1. Clearly state the facts returned by the tools.
2. Provide:
   - Likely cause
   - Evidence checked from tool output
   - Linux commands
   - Recommended remediation (READ -> ANALYZE -> PROPOSE)
"""


model = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GEMINI_API_KEY,
)
model_with_tools = model.bind_tools(LINUX_TOOLS)
tools_by_name = {t.name: t for t in LINUX_TOOLS}


def linux_agent(state: AgentState) -> dict:
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
            out_str = tools_by_name["linux_system_status"].invoke({})
            text = f"### Live System Status (`linux_system_status`)\n```text\n{out_str}\n```"

    return {
        "selected_agent": "linux",
        "agent_response": text,
        "messages": [AIMessage(content=text)],
    }

