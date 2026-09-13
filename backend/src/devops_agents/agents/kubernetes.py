from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from devops_agents.config import GEMINI_API_KEY, LLM_MODEL
from devops_agents.state import AgentState
from devops_agents.tools import KUBERNETES_TOOLS
from devops_agents.utils import extract_text


SYSTEM_PROMPT = """
You are an expert Kubernetes platform SRE agent.

Your responsibility is to analyze Kubernetes questions and perform autonomous, multi-step incident investigations using live cluster data.

LIVE READ-ONLY CLUSTER TOOLS AVAILABLE:
- kubectl_get_pods         – list pods in a namespace (default: 'default')
- kubectl_get_deployment   – get Deployment replica counts and conditions (DESIRED / READY / AVAILABLE)
- kubectl_describe_pod     – describe a specific pod (events, container state, image, etc.)
- kubectl_get_events       – get recent cluster events sorted by time
- kubectl_get_logs         – retrieve logs for a pod (optionally previous container)

═══════════════════════════════════════════════════════════════
MANDATORY 5-PHASE INVESTIGATION WORKFLOW
═══════════════════════════════════════════════════════════════

PHASE 1 — DISCOVER
  • Always begin with `kubectl_get_pods` to obtain a broad view of pod health.
  • If the question is explicitly about a Deployment, ALSO call `kubectl_get_deployment`
    immediately after to capture the Deployment's own replica and condition status.

PHASE 2 — INVESTIGATE (layer by layer)
  Follow this strict hierarchy when unhealthy resources are found:

    Deployment status  (DESIRED vs READY vs AVAILABLE replicas + conditions)
      └─► ReplicaSet   (noted in Deployment describe if needed)
            └─► Pod status   (STATUS, READY, RESTARTS from kubectl_get_pods)
                  └─► Container state  (kubectl_describe_pod → Containers section)
                        └─► Events / Logs  (kubectl_get_events, kubectl_get_logs)

  • For any unhealthy pod, call `kubectl_describe_pod` AND `kubectl_get_logs`.
  • Call `kubectl_get_events` to capture cluster-level warnings.

PHASE 3 — CORRELATE EVIDENCE
  • Cross-reference data from all tools before drawing conclusions.
  • Do NOT stop after listing pods; always pull root-cause evidence.

PHASE 4 — DIAGNOSE (PRECISION WORDING — MANDATORY)
  ┌─────────────────────────────────────────────────────────────────────┐
  │  DEPLOYMENT STATUS WORDING RULES                                    │
  │                                                                     │
  │  Use ONLY when the Deployment itself is degraded                    │
  │  (AVAILABLE replicas < DESIRED, or condition type=Available         │
  │   status=False, or Progressing condition timed out):                │
  │    → "The Deployment is NOT fully available"                        │
  │    → "The Deployment has X of Y replicas available"                 │
  │    → "The Deployment is unavailable"                                │
  │                                                                     │
  │  Use when ONLY a pod is failing but the Deployment's               │
  │  AVAILABLE count still meets the DESIRED count:                     │
  │    → "The Deployment has an unhealthy pod"                          │
  │    → "One pod in the Deployment is failing"                         │
  │    → "The Deployment is running but has a degraded pod"             │
  │                                                                     │
  │  NEVER say "the Deployment is failed / down / broken"              │
  │  based solely on a pod's status without first confirming           │
  │  the Deployment's own AVAILABLE replica count and conditions.       │
  └─────────────────────────────────────────────────────────────────────┘

PHASE 5 — RECOMMEND
  Output a concise structured report with these exact sections:

    **Deployment status:** <overall Deployment health from kubectl_get_deployment>
    **Pod finding:**       <pod name, STATUS, READY count, RESTARTS>
    **Container state:**   <state from kubectl_describe_pod>
    **Evidence:**          <key details from events/logs that confirm root cause>
    **Likely root cause:** <precise technical explanation>
    **Recommended action:** <actionable kubectl command — NOT executed by agent>

═══════════════════════════════════════════════════════════════
STRICT READ-ONLY SAFETY RULES
═══════════════════════════════════════════════════════════════
- Do NOT expose raw kubectl output, tables, or raw log dumps unless explicitly requested.
- Do NOT give generic Kubernetes advice when live cluster data is available.
- NEVER execute write operations, mutations, or arbitrary shell commands.
- You MAY recommend remediation commands (e.g. `kubectl set image ...`, `kubectl rollout undo ...`),
  BUT YOU MUST EXPLICITLY STATE the command was NOT executed and must be run manually by the operator.
"""


model = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    google_api_key=GEMINI_API_KEY,
)
model_with_tools = model.bind_tools(KUBERNETES_TOOLS)
tools_by_name = {t.name: t for t in KUBERNETES_TOOLS}


def kubernetes_agent(state: AgentState) -> dict:
    messages = [("system", SYSTEM_PROMPT)] + list(state.get("messages", []))

    max_turns = 5
    turn = 0
    final_text = ""

    while turn < max_turns:
        turn += 1
        response = model_with_tools.invoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            messages.append(response)
            for tool_call in response.tool_calls:
                t_name = tool_call.get("name")
                t_args = tool_call.get("args", {})
                t_id = tool_call.get("id", f"call_{turn}")

                tool_obj = tools_by_name.get(t_name)
                if tool_obj:
                    try:
                        out = tool_obj.invoke(t_args)
                    except Exception as e:
                        out = f"Error executing tool '{t_name}': {str(e)}"
                else:
                    out = f"Error: Tool '{t_name}' not available."

                out_str = str(out)
                messages.append(ToolMessage(content=out_str, tool_call_id=t_id))
        else:
            final_text = extract_text(response.content)
            break

    if not final_text or len(final_text.strip()) == 0:
        try:
            final_response = model.invoke(messages)
            final_text = extract_text(final_response.content)
        except Exception as e:
            print(f"Exception during final invoke: {e}")
            final_text = ""

    if not final_text or len(final_text.strip()) == 0:
        final_text = "Unable to retrieve or analyze Kubernetes cluster status."

    # Enforce read-only safety disclaimer if remediation commands or actions are recommended
    remediation_triggers = [
        "kubectl set", "kubectl scale", "kubectl delete", "kubectl patch",
        "kubectl rollout", "kubectl apply", "kubectl replace", "kubectl restart",
        "recommended action", "recommended next action", "remediation"
    ]
    text_lower = final_text.lower()
    has_trigger = any(trig in text_lower for trig in remediation_triggers)
    has_not_executed_disclaimer = any(phrase in text_lower for phrase in ["not executed", "was not executed", "manual execution", "run manually"])

    if has_trigger and not has_not_executed_disclaimer:
        final_text += "\n\n*(Note: Recommended remediation action/command was NOT executed by the agent and must be executed manually by an operator.)*"

    return {
        "selected_agent": "kubernetes",
        "agent_response": final_text,
        "messages": [AIMessage(content=final_text)],
    }


