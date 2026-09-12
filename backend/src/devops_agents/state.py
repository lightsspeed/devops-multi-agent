from typing import TypedDict


class AgentState(TypedDict):
    user_query: str
    selected_agent: str
    agent_response: str