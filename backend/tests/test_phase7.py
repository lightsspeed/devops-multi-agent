"""
Phase 7 — Simplified LangGraph Orchestration Tests

All tests use mocked LLM calls. Zero Gemini API usage.

Tests cover:
    - Planner: single-domain plan, cross-domain plan (capped at max 2), supervisor fallback
    - Routing & Advance: route_after_advance proceeds to next specialist or END
    - Specialist Execution: single specialist and multi-specialist investigation report correlation
    - Full Graph Pipeline: START -> supervisor -> planner -> specialist(s) -> END
"""

from unittest.mock import patch, MagicMock
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from devops_agents.agents.planner import planner, _detect_domains
from devops_agents.graph import (
    graph,
    run_specialist,
    advance_plan,
    route_after_advance,
)
from devops_agents.models import RoutingDecision


# ═══════════════════════════════════════════════════════════════════════════
# Planner tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPlannerDomainDetection:
    """Test _detect_domains keyword matching."""

    def test_kubernetes_keywords(self):
        assert _detect_domains("my pods are failing in default namespace") == ["kubernetes"]

    def test_aws_keywords(self):
        assert _detect_domains("check my ec2 instances") == ["aws"]

    def test_linux_keywords(self):
        assert _detect_domains("disk is full on the linux host") == ["linux"]

    def test_cross_domain_kubernetes_aws(self):
        assert _detect_domains("check the failing pod and the underlying ec2 instance") == [
            "kubernetes", "aws"
        ]

    def test_cross_domain_kubernetes_linux(self):
        assert _detect_domains("pod is oomkilled, check host memory usage") == [
            "kubernetes", "linux"
        ]

    def test_cross_domain_capped_at_two(self):
        result = _detect_domains("kubernetes pods failing on ec2 with high disk usage on linux host")
        assert len(result) == 3
        # planner node function caps at max 2
        state = {
            "messages": [HumanMessage(content="kubernetes pods failing on ec2 with high disk usage on linux host")],
            "selected_agent": "kubernetes",
        }
        res = planner(state)
        assert len(res["plan"]) == 2
        assert res["plan"] == ["kubernetes", "aws"]

    def test_no_signals_returns_empty(self):
        assert _detect_domains("what is the weather today") == []


class TestPlannerNode:
    """Test the planner node function."""

    def test_single_agent_plan_from_supervisor(self):
        state = {
            "messages": [HumanMessage(content="My pod is failing")],
            "selected_agent": "kubernetes",
            "agent_response": "",
        }
        result = planner(state)
        assert result["plan"] == ["kubernetes"]
        assert result["plan_index"] == 0
        assert result["selected_agent"] == "kubernetes"

    def test_cross_domain_plan(self):
        state = {
            "messages": [HumanMessage(content="Check the failing k8s application and the underlying ec2")],
            "selected_agent": "kubernetes",
            "agent_response": "",
        }
        result = planner(state)
        assert result["plan"] == ["kubernetes", "aws"]
        assert result["plan_index"] == 0
        assert result["selected_agent"] == "kubernetes"

    def test_fallback_to_supervisor_when_no_keywords(self):
        state = {
            "messages": [HumanMessage(content="Something is broken")],
            "selected_agent": "aws",
            "agent_response": "",
        }
        result = planner(state)
        assert result["plan"] == ["aws"]
        assert result["selected_agent"] == "aws"

    def test_plan_always_non_empty(self):
        state = {
            "messages": [],
            "selected_agent": "linux",
            "agent_response": "",
        }
        result = planner(state)
        assert len(result["plan"]) >= 1
        assert result["plan_index"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# Routing function tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRoutingFunctions:

    def test_route_after_advance_more_specialists(self):
        state = {"plan": ["kubernetes", "aws"], "plan_index": 1}
        assert route_after_advance(state) == "run_specialist"

    def test_route_after_advance_plan_complete(self):
        state = {"plan": ["kubernetes"], "plan_index": 1}
        assert route_after_advance(state) == "__end__"


# ═══════════════════════════════════════════════════════════════════════════
# Advance plan tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAdvancePlan:

    def test_increments_plan_index(self):
        state = {"plan_index": 0}
        result = advance_plan(state)
        assert result["plan_index"] == 1

    def test_increments_from_existing(self):
        state = {"plan_index": 1}
        result = advance_plan(state)
        assert result["plan_index"] == 2


# ═══════════════════════════════════════════════════════════════════════════
# run_specialist tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRunSpecialist:

    @patch("devops_agents.agents.kubernetes.model_with_tools")
    def test_runs_kubernetes_specialist(self, mock_k8s_model):
        mock_k8s_model.invoke.return_value = AIMessage(
            content="K8s investigation result with root cause analysis."
        )
        state = {
            "messages": [HumanMessage(content="Check pods")],
            "plan": ["kubernetes"],
            "plan_index": 0,
            "selected_agent": "kubernetes",
            "agent_response": "",
        }
        result = run_specialist(state)
        assert result["selected_agent"] == "kubernetes"
        assert "K8s investigation" in result["agent_response"]

    def test_unknown_specialist_returns_error(self):
        state = {
            "messages": [HumanMessage(content="test")],
            "plan": ["database"],
            "plan_index": 0,
            "selected_agent": "database",
            "agent_response": "",
        }
        result = run_specialist(state)
        assert "No specialist found" in result["agent_response"]


# ═══════════════════════════════════════════════════════════════════════════
# Full graph integration tests (mocked LLM, zero Gemini API usage)
# ═══════════════════════════════════════════════════════════════════════════


class TestFullGraphPipeline:

    @patch("devops_agents.graph.supervisor_model")
    @patch("devops_agents.agents.kubernetes.model_with_tools")
    def test_single_agent_pipeline_execution(self, mock_k8s_model, mock_supervisor):
        """Supervisor → Planner (1 agent) → K8s → END"""
        mock_supervisor.invoke.return_value = RoutingDecision(
            agent="kubernetes", reason="K8s query"
        )
        response_text = (
            "**Deployment status:** 3/3 replicas available.\n"
            "**Pod finding:** app-7d8f9 (STATUS=Running, READY=1/1)\n"
            "**Evidence:** Events show normal scheduling."
        )
        mock_k8s_model.invoke.return_value = AIMessage(content=response_text)

        config = {"configurable": {"thread_id": "phase7-single-test"}}
        result = graph.invoke(
            {"messages": [HumanMessage(content="Check my pods")]},
            config=config,
        )

        assert result["selected_agent"] == "kubernetes"
        assert response_text in result["agent_response"]

    @patch("devops_agents.graph.supervisor_model")
    @patch("devops_agents.agents.kubernetes.model_with_tools")
    @patch("devops_agents.agents.aws.model_with_tools")
    def test_multi_agent_sequential_plan(self, mock_aws_model, mock_k8s_model, mock_supervisor):
        """Cross-domain: Planner produces ["kubernetes", "aws"], both run sequentially → END."""
        mock_supervisor.invoke.return_value = RoutingDecision(
            agent="kubernetes", reason="K8s + EC2 query"
        )
        k8s_response = (
            "Pod payment-api is CrashLoopBackOff. "
            "Likely root cause: container OOMKilled."
        )
        aws_response = (
            "EC2 instance i-12345 is running. "
            "Evidence: DescribeInstances shows healthy state."
        )
        mock_k8s_model.invoke.return_value = AIMessage(content=k8s_response)
        mock_aws_model.invoke.return_value = AIMessage(content=aws_response)

        config = {"configurable": {"thread_id": "phase7-multi-agent-test"}}
        result = graph.invoke(
            {"messages": [HumanMessage(
                content="Check the failing kubernetes pods and the underlying ec2 instances"
            )]},
            config=config,
        )

        assert result["selected_agent"] == "aws"
        assert result["plan"] == ["kubernetes", "aws"]
        assert "Correlated Multi-Agent Investigation Report" in result["agent_response"]
