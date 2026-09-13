import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from devops_agents.graph import graph
from devops_agents.utils import extract_text

app = FastAPI(
    title="DevOps Multi-Agent API",
    version="0.5.0",
    description="REST API for DevOps incident assistant multi-agent system",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question or incident query")
    thread_id: Optional[str] = Field(
        default=None, description="Optional conversation thread ID for session state tracking"
    )


class ChatResponse(BaseModel):
    response: str
    selected_agent: str
    thread_id: str


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version="0.5.0")


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    thread_id = payload.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = graph.invoke(
            {
                "messages": [HumanMessage(content=payload.message)],
            },
            config=config,
        )

        agent_name = result.get("selected_agent", "unknown")
        raw_response = result.get("agent_response", "")
        response_text = extract_text(raw_response)

        return ChatResponse(
            response=response_text,
            selected_agent=agent_name,
            thread_id=thread_id,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the request: {str(exc)}",
        )
