from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    selected_agent: str
    agent_response: str

    # Phase 7 — Simplified Orchestration fields
    plan: list[str]                      # Ordered list of specialist agents to invoke (max 2)
    plan_index: int                      # Index of the current specialist in execution
    investigation_findings: list[str]    # Accumulated findings from each specialist