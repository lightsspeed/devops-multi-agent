from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    selected_agent: str
    agent_response: str

    # Phase 7 — Planner / Reviewer fields
    plan: list[str]            # Ordered list of specialist agents to invoke
    plan_index: int            # Index of the next specialist to run in the plan
    review_passed: bool        # True when Reviewer approves the final response
    review_notes: str          # Reviewer feedback / rejection reason
    requires_approval: bool    # True when response recommends a risky operation
    review_retry_count: int    # Guards against uncontrolled retry loops (max 1)
    investigation_findings: list[str]  # Accumulated findings from each specialist (D1 fix)