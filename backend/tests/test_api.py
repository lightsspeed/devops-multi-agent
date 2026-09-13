from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from devops_agents.api import app
from devops_agents.models import RoutingDecision

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert json_data["version"] == "0.6.0"


@patch("devops_agents.graph.supervisor_model")
@patch("devops_agents.agents.kubernetes.model_with_tools")
def test_chat_endpoint_auto_thread_id(mock_k8s_model, mock_supervisor_model):
    mock_supervisor_model.invoke.return_value = RoutingDecision(
        agent="kubernetes", reason="K8s pod failure query"
    )
    k8s_response = (
        "Pod CrashLoopBackOff: check container logs. "
        "Root cause: application exits immediately on startup due to missing environment variable. "
        "Evidence: kubectl describe pod shows OOMKilled exit code 137."
    )
    mock_k8s_model.invoke.return_value = AIMessage(content=k8s_response)

    response = client.post("/chat", json={"message": "My pod keeps crashing"})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["selected_agent"] == "kubernetes"
    assert k8s_response in json_data["response"]
    assert "thread_id" in json_data and len(json_data["thread_id"]) > 0


@patch("devops_agents.graph.supervisor_model")
@patch("devops_agents.agents.aws.model_with_tools")
def test_chat_endpoint_with_custom_thread_id(mock_aws_model, mock_supervisor_model):
    mock_supervisor_model.invoke.return_value = RoutingDecision(
        agent="aws", reason="EC2 query"
    )
    aws_response = (
        "EC2 instance state is running. Evidence: DescribeInstances returned state=running. "
        "Likely cause: security group blocks outbound on port 443. "
        "Recommended action: review security group egress rules."
    )
    mock_aws_model.invoke.return_value = AIMessage(content=aws_response)

    custom_thread = "test-thread-999"
    response = client.post(
        "/chat",
        json={"message": "What is my EC2 status?", "thread_id": custom_thread},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["selected_agent"] == "aws"
    assert json_data["thread_id"] == custom_thread
    assert aws_response in json_data["response"]


def test_chat_endpoint_invalid_payload():
    response = client.post("/chat", json={})
    assert response.status_code == 422

    response_empty = client.post("/chat", json={"message": ""})
    assert response_empty.status_code == 422


def test_create_and_get_session_endpoints():
    # 1. Create a new session
    res_create = client.post("/sessions")
    assert res_create.status_code == 200
    create_data = res_create.json()
    session_id = create_data["session_id"]
    assert session_id.startswith("session-")
    assert create_data["messages"] == []

    # 2. Get the created session (empty)
    res_get = client.get(f"/sessions/{session_id}")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["session_id"] == session_id
    assert get_data["messages"] == []


def test_get_nonexistent_session_returns_404():
    res = client.get("/sessions/nonexistent-session-999")
    assert res.status_code == 404


@patch("devops_agents.graph.supervisor_model")
@patch("devops_agents.agents.kubernetes.model_with_tools")
def test_refresh_reload_behavior_restores_messages(mock_k8s_model, mock_supervisor_model):
    import uuid
    mock_supervisor_model.invoke.return_value = RoutingDecision(
        agent="kubernetes", reason="K8s query"
    )
    k8s_response = (
        "Analyzed pods cleanly. Root cause: deployment has 0/3 replicas available. "
        "Evidence: kubectl describe deployment shows ProgressDeadlineExceeded condition."
    )
    mock_k8s_model.invoke.return_value = AIMessage(content=k8s_response)

    # Simulate Turn 1: user sends message with thread_id
    session_id = f"session-reload-test-{uuid.uuid4().hex[:8]}"
    chat_res = client.post("/chat", json={"message": "Show pod details", "thread_id": session_id})
    assert chat_res.status_code == 200

    # Simulate page refresh/reload: client calls GET /sessions/{session_id}
    restore_res = client.get(f"/sessions/{session_id}")
    assert restore_res.status_code == 200
    session_data = restore_res.json()
    assert session_data["session_id"] == session_id
    messages = session_data["messages"]
    assert len(messages) == 2
    assert messages[0]["sender"] == "user"
    assert messages[0]["text"] == "Show pod details"
    assert messages[1]["sender"] == "assistant"
    assert k8s_response in messages[1]["text"]


@patch("devops_agents.graph.supervisor_model")
def test_chat_endpoint_rate_limit_error(mock_supervisor_model):
    mock_supervisor_model.invoke.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for model gemini-3.6-flash")
    response = client.post("/chat", json={"message": "Test quota error"})
    assert response.status_code == 429
    assert "Gemini API quota or rate limit exceeded" in response.json()["detail"]


