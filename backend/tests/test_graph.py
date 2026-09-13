from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from devops_agents.graph import graph, route_agent, supervisor
from devops_agents.models import RoutingDecision
from devops_agents.agents.kubernetes import kubernetes_agent
from devops_agents.agents.aws import aws_agent
from devops_agents.agents.linux import linux_agent


def test_kubernetes_route():
    state = {
        "messages": [HumanMessage(content="My Kubernetes pod is stuck in Pending")],
        "selected_agent": "kubernetes",
        "agent_response": "",
    }
    assert route_agent(state) == "kubernetes"


def test_aws_route():
    state = {
        "messages": [HumanMessage(content="My EC2 instance cannot access S3")],
        "selected_agent": "aws",
        "agent_response": "",
    }
    assert route_agent(state) == "aws"


def test_linux_route():
    state = {
        "messages": [HumanMessage(content="My Linux server is running out of disk")],
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


@patch("devops_agents.graph.supervisor_model")
def test_supervisor_node(mock_supervisor):
    mock_supervisor.invoke.return_value = RoutingDecision(
        agent="kubernetes", reason="Pod failure query"
    )
    state = {
        "messages": [HumanMessage(content="My pod is failing")],
        "selected_agent": "",
        "agent_response": "",
    }
    res = supervisor(state)
    assert res == {"selected_agent": "kubernetes"}


@patch("devops_agents.agents.kubernetes.model")
def test_kubernetes_agent_node(mock_k8s_model):
    mock_k8s_model.invoke.return_value = AIMessage(
        content="Check pod events with kubectl describe pod"
    )
    state = {
        "messages": [HumanMessage(content="Pod crash loop")],
        "selected_agent": "kubernetes",
        "agent_response": "",
    }
    res = kubernetes_agent(state)
    assert res["selected_agent"] == "kubernetes"
    assert res["agent_response"] == "Check pod events with kubectl describe pod"
    assert len(res["messages"]) == 1
    assert isinstance(res["messages"][0], AIMessage)
    assert res["messages"][0].content == "Check pod events with kubectl describe pod"


@patch("devops_agents.agents.aws.model")
def test_aws_agent_node(mock_aws_model):
    mock_aws_model.invoke.return_value = AIMessage(
        content="Check security group egress rules"
    )
    state = {
        "messages": [HumanMessage(content="EC2 network blocked")],
        "selected_agent": "aws",
        "agent_response": "",
    }
    res = aws_agent(state)
    assert res["selected_agent"] == "aws"
    assert res["agent_response"] == "Check security group egress rules"


@patch("devops_agents.agents.linux.model")
def test_linux_agent_node(mock_linux_model):
    mock_linux_model.invoke.return_value = AIMessage(
        content="Check memory usage with free -m"
    )
    state = {
        "messages": [HumanMessage(content="Out of memory error")],
        "selected_agent": "linux",
        "agent_response": "",
    }
    res = linux_agent(state)
    assert res["selected_agent"] == "linux"
    assert res["agent_response"] == "Check memory usage with free -m"


@patch("devops_agents.graph.supervisor_model")
@patch("devops_agents.agents.kubernetes.model")
def test_multi_turn_conversation_thread_persistence(mock_k8s_model, mock_supervisor_model):
    mock_supervisor_model.invoke.return_value = RoutingDecision(
        agent="kubernetes", reason="K8s query"
    )
    mock_k8s_model.invoke.side_effect = [
        AIMessage(content="payment-api has 3 failing pods."),
        AIMessage(content="The pod events indicate ImagePullBackOff."),
    ]

    config = {"configurable": {"thread_id": "thread-123"}}

    # Turn 1
    res1 = graph.invoke(
        {"messages": [HumanMessage(content="What pods are failing?")]},
        config=config,
    )
    assert res1["selected_agent"] == "kubernetes"
    assert res1["agent_response"] == "payment-api has 3 failing pods."

    # Turn 2
    res2 = graph.invoke(
        {"messages": [HumanMessage(content="Why?")]},
        config=config,
    )
    assert res2["selected_agent"] == "kubernetes"
    assert res2["agent_response"] == "The pod events indicate ImagePullBackOff."

    # Check conversation history saved in checkpointer
    saved_state = graph.get_state(config)
    messages = saved_state.values["messages"]
    assert len(messages) == 4
    assert messages[0].content == "What pods are failing?"
    assert messages[1].content == "payment-api has 3 failing pods."
    assert messages[2].content == "Why?"
    assert messages[3].content == "The pod events indicate ImagePullBackOff."


@patch("devops_agents.graph.supervisor_model")
@patch("devops_agents.agents.aws.model")
@patch("devops_agents.agents.linux.model")
def test_thread_isolation(mock_linux_model, mock_aws_model, mock_supervisor_model):
    mock_supervisor_model.invoke.side_effect = [
        RoutingDecision(agent="aws", reason="AWS query"),
        RoutingDecision(agent="linux", reason="Linux query"),
    ]
    mock_aws_model.invoke.return_value = AIMessage(content="S3 bucket response")
    mock_linux_model.invoke.return_value = AIMessage(content="Linux uptime response")

    config_a = {"configurable": {"thread_id": "thread-A"}}
    config_b = {"configurable": {"thread_id": "thread-B"}}

    graph.invoke(
        {"messages": [HumanMessage(content="AWS S3 error")]},
        config=config_a,
    )
    graph.invoke(
        {"messages": [HumanMessage(content="Linux reboot error")]},
        config=config_b,
    )

    state_a = graph.get_state(config_a).values["messages"]
    state_b = graph.get_state(config_b).values["messages"]

    assert len(state_a) == 2
    assert state_a[0].content == "AWS S3 error"
    assert state_a[1].content == "S3 bucket response"

    assert len(state_b) == 2
    assert state_b[0].content == "Linux reboot error"
    assert state_b[1].content == "Linux uptime response"
