import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from devops_agents.graph import graph
from devops_agents.storage import storage
from devops_agents.utils import extract_text

app = FastAPI(
    title="DevOps Multi-Agent API",
    version="0.6.0",
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


class SessionResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]] = []


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version="0.6.0")


@app.post("/sessions", response_model=SessionResponse)
def create_session() -> SessionResponse:
    session_id = storage.create_session()
    return SessionResponse(session_id=session_id, messages=[])


@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    if not storage.session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    messages = storage.get_session_messages(session_id)
    return SessionResponse(session_id=session_id, messages=messages)


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    session_id = payload.thread_id or str(uuid.uuid4())
    
    # Save user message to persistent storage
    storage.add_message(session_id=session_id, sender="user", text=payload.message)

    config = {"configurable": {"thread_id": session_id}}

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

        # Save assistant message to persistent storage
        storage.add_message(
            session_id=session_id,
            sender="assistant",
            text=response_text,
            selected_agent=agent_name,
        )

        return ChatResponse(
            response=response_text,
            selected_agent=agent_name,
            thread_id=session_id,
        )

    except Exception as exc:
        err_msg = str(exc)
        err_lower = err_msg.lower()
        if "429" in err_msg or "resource_exhausted" in err_lower or "quota" in err_lower or "rate limit" in err_lower or "rate_limit" in err_lower:
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota or rate limit exceeded (429 RESOURCE_EXHAUSTED). Please wait a few moments before retrying, or check your Gemini API key / quota settings.",
            )
        if "404" in err_msg or "not_found" in err_lower or "no longer available" in err_lower:
            raise HTTPException(
                status_code=404,
                detail=f"Gemini API model error (404 NOT_FOUND): {err_msg}. Please update LLM_MODEL in backend/.env to gemini-3.6-flash.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the request: {err_msg}",
        )

