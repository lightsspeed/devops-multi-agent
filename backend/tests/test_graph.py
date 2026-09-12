import pytest
from pydantic import ValidationError

from devops_agents.models import RoutingDecision
from devops_agents.graph import route_agent


def test_kubernetes_route():
    state = {
        "user_query": "My Kubernetes pod is stuck in Pending",
        "selected_agent": "kubernetes",
        "agent_response": "",
    }

    assert route_agent(state) == "kubernetes"


def test_aws_route():
    state = {
        "user_query": "My EC2 instance cannot access S3",
        "selected_agent": "aws",
        "agent_response": "",
    }

    assert route_agent(state) == "aws"


def test_linux_route():
    state = {
        "user_query": "My Linux server is running out of disk",
        "selected_agent": "linux",
        "agent_response": "",
    }

    assert route_agent(state) == "linux"


def test_valid_routing_decision():
    decision = RoutingDecision(
        agent="kubernetes",
        reason="The issue is related to a Kubernetes Pod.",
    )

    assert decision.agent == "kubernetes"


def test_invalid_routing_decision():
    with pytest.raises(ValidationError):
        RoutingDecision(
            agent="database",
            reason="This should not be a valid agent.",
        )