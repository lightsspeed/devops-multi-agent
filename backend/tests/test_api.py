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
    assert json_data["version"] == "0.5.0"


@patch("devops_agents.graph.supervisor_model")
@patch("devops_agents.agents.kubernetes.model")
def test_chat_endpoint_auto_thread_id(mock_k8s_model, mock_supervisor_model):
    mock_supervisor_model.invoke.return_value = RoutingDecision(
        agent="kubernetes", reason="K8s pod failure query"
    )
    mock_k8s_model.invoke.return_value = AIMessage(
        content="Pod CrashLoopBackOff: check container logs"
    )

    response = client.post("/chat", json={"message": "My pod keeps crashing"})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["selected_agent"] == "kubernetes"
    assert json_data["response"] == "Pod CrashLoopBackOff: check container logs"
    assert "thread_id" in json_data and len(json_data["thread_id"]) > 0


@patch("devops_agents.graph.supervisor_model")
@patch("devops_agents.agents.aws.model")
def test_chat_endpoint_with_custom_thread_id(mock_aws_model, mock_supervisor_model):
    mock_supervisor_model.invoke.return_value = RoutingDecision(
        agent="aws", reason="EC2 query"
    )
    mock_aws_model.invoke.return_value = AIMessage(
        content="EC2 instance state is running"
    )

    custom_thread = "test-thread-999"
    response = client.post(
        "/chat",
        json={"message": "What is my EC2 status?", "thread_id": custom_thread},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["selected_agent"] == "aws"
    assert json_data["thread_id"] == custom_thread
    assert json_data["response"] == "EC2 instance state is running"


def test_chat_endpoint_invalid_payload():
    response = client.post("/chat", json={})
    assert response.status_code == 422

    response_empty = client.post("/chat", json={"message": ""})
    assert response_empty.status_code == 422
