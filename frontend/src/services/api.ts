export interface ChatRequest {
  message: string;
  thread_id?: string;
}

export interface ChatResponse {
  response: string;
  selected_agent: 'kubernetes' | 'aws' | 'linux' | string;
  thread_id: string;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface SessionMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  selected_agent?: string;
  timestamp: string;
}

export interface SessionResponse {
  session_id: string;
  messages: SessionMessage[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) {
      throw new Error(`Health check failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error('Health check error:', err);
    throw err;
  }
}

export async function createSession(): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE_URL}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to create session with status ${res.status}`);
  }

  return await res.json();
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Session '${sessionId}' not found (${res.status})`);
  }

  return await res.json();
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server responded with status ${res.status}`);
  }

  return await res.json();
}
