from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from devops_agents.agents.kubernetes import kubernetes_agent


@patch("devops_agents.agents.kubernetes.tools_by_name")
@patch("devops_agents.agents.kubernetes.model_with_tools")
def test_kubernetes_agent_multi_turn_investigation(mock_model_with_tools, mock_tools_by_name):
    # Mock Turn 1: Model decides to call `kubectl_get_pods`
    ai_turn_1 = AIMessage(
        content="",
        tool_calls=[{"name": "kubectl_get_pods", "args": {"namespace": "default"}, "id": "call_1"}],
    )
    
    # Mock Turn 2: Model receives pod list (with ImagePullBackOff), decides to call `kubectl_describe_pod`
    ai_turn_2 = AIMessage(
        content="",
        tool_calls=[{"name": "kubectl_describe_pod", "args": {"pod_name": "nginx-faulty-79d5676bcd-x29t", "namespace": "default"}, "id": "call_2"}],
    )

    # Mock Turn 3: Model analyzes describe output and returns final incident analysis
    final_analysis = (
        "nginx-faulty-79d5676bcd-x29t is failing with ImagePullBackOff (0/1).\n"
        "Describe/events indicate the image cannot be pulled.\n"
        "Likely cause: invalid image name/tag or unavailable registry.\n"
        "Recommended action: verify the image reference and registry access."
    )
    ai_turn_3 = AIMessage(content=final_analysis)

    mock_model_with_tools.invoke.side_effect = [ai_turn_1, ai_turn_2, ai_turn_3]

    # Mock tool execution return values
    mock_get_pods_tool = MagicMock()
    mock_get_pods_tool.invoke.return_value = (
        "NAME                                READY   STATUS             RESTARTS   AGE\n"
        "nginx-faulty-79d5676bcd-x29t        0/1     ImagePullBackOff   0          5m\n"
    )

    mock_describe_tool = MagicMock()
    mock_describe_tool.invoke.return_value = (
        "Name:         nginx-faulty-79d5676bcd-x29t\n"
        "Events:\n"
        "  Type     Reason     Age                  From               Message\n"
        "  ----     ------     ----                 ----               -------\n"
        "  Warning  Failed     3m (x4 over 4m22s)   kubelet            Failed to pull image 'nginx:invalid-tag'\n"
    )

    mock_tools_by_name.get.side_effect = lambda name: {
        "kubectl_get_pods": mock_get_pods_tool,
        "kubectl_describe_pod": mock_describe_tool,
    }.get(name)

    state = {
        "messages": [HumanMessage(content="Which pods are now failing?")],
        "selected_agent": "kubernetes",
        "agent_response": "",
    }

    result = kubernetes_agent(state)

    assert result["selected_agent"] == "kubernetes"
    assert "Recommended action:" in result["agent_response"]
    assert "NOT executed" in result["agent_response"]
    assert mock_model_with_tools.invoke.call_count == 3
    assert mock_get_pods_tool.invoke.called
    assert mock_describe_tool.invoke.called


@patch("devops_agents.agents.kubernetes.tools_by_name")
@patch("devops_agents.agents.kubernetes.model_with_tools")
def test_kubernetes_agent_remediation_command_not_executed(mock_model_with_tools, mock_tools_by_name):
    # Model recommends `kubectl set image` command
    ai_response = AIMessage(
        content=(
            "Failing pod: payment-api (ImagePullBackOff, 0/1)\n"
            "Recommended action: Update image using command:\n"
            "kubectl set image deployment/payment-api payment-api=registry.example.com/payment:v2"
        )
    )
    mock_model_with_tools.invoke.return_value = ai_response

    state = {
        "messages": [HumanMessage(content="Fix payment-api pod image")],
        "selected_agent": "kubernetes",
        "agent_response": "",
    }

    result = kubernetes_agent(state)
    response_text = result["agent_response"]

    assert "kubectl set image" in response_text
    assert "NOT executed" in response_text

