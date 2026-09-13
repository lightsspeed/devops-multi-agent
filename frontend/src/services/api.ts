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
