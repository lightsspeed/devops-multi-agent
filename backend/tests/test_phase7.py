"""
Phase 7 — Advanced LangGraph Orchestration Tests

All tests use mocked LLM calls.  Zero Gemini API usage.

Tests cover:
    - Planner: single-domain plan, cross-domain plan, supervisor fallback
    - Reviewer: passes good response, rejects short response, rejects missing
      diagnosis, detects risky operations, max-one-retry guard
    - Human gate: appends approval banner
    - Graph integration: full pipeline with Planner + Reviewer
    - Multi-agent sequential plan execution
"""

from unittest.mock import patch, MagicMock
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from devops_agents.agents.planner import planner, _detect_domains
from devops_agents.agents.reviewer import (
    reviewer,
    _has_diagnosis_evidence,
    _detect_risky_operations,
    _MIN_RESPONSE_CHARS,
)
from devops_agents.graph import (
    graph,
    run_specialist,
    advance_plan,
    human_gate,
    route_after_advance,
    route_after_reviewer,
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

    def test_cross_domain_all_three(self):
        result = _detect_domains("kubernetes pods failing on ec2 with high disk usage on linux host")
        assert result == ["kubernetes", "aws", "linux"]

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
# Reviewer tests
# ═══════════════════════════════════════════════════════════════════════════


class TestReviewerHelpers:
    """Test reviewer helper functions."""

    def test_diagnosis_evidence_detected(self):
        assert _has_diagnosis_evidence("The likely root cause is a missing image tag.")

    def test_diagnosis_evidence_missing(self):
        assert not _has_diagnosis_evidence("Everything looks fine, no issues found.")

    def test_risky_kubectl_delete_detected(self):
        assert _detect_risky_operations("Run kubectl delete pod my-pod-xyz")

    def test_risky_kubectl_scale_detected(self):
        assert _detect_risky_operations("kubectl scale deployment/app --replicas=0")

    def test_risky_kubectl_set_image_detected(self):
        assert _detect_risky_operations("kubectl set image deployment/app container=image:v2")

    def test_risky_kubectl_rollout_detected(self):
        assert _detect_risky_operations("kubectl rollout undo deployment/app")

    def test_safe_response_not_flagged(self):
        assert not _detect_risky_operations(
            "The pod is in CrashLoopBackOff. Root cause: missing config."
        )

    def test_risky_terraform_detected(self):
        assert _detect_risky_operations("Run terraform apply to provision the fix.")


class TestReviewerNode:
    """Test the reviewer node function."""

    def _good_response(self):
        return (
            "**Deployment status:** 3/3 replicas available.\n"
            "**Pod finding:** payment-api-7d8f9 (STATUS=Running, READY=1/1, RESTARTS=0)\n"
            "**Container state:** Running since 2h ago.\n"
            "**Evidence:** Events show normal scheduling.\n"
            "**Likely root cause:** No issue detected.\n"
            "**Recommended action:** No action needed."
        )

    def test_passes_good_response(self):
        state = {
            "agent_response": self._good_response(),
            "review_retry_count": 0,
        }
        result = reviewer(state)
        assert result["review_passed"] is True
        assert result["requires_approval"] is False

    def test_rejects_short_response_first_try(self):
        state = {
            "agent_response": "ok",
            "review_retry_count": 0,
        }
        result = reviewer(state)
        assert result["review_passed"] is False
        assert result["review_retry_count"] == 1

    def test_accepts_short_response_after_retry(self):
        """Max 1 retry — must accept even short responses after that."""
        state = {
            "agent_response": "ok",
            "review_retry_count": 1,
        }
        result = reviewer(state)
        assert result["review_passed"] is True
        assert result["review_retry_count"] == 1

    def test_rejects_missing_diagnosis_first_try(self):
        long_generic = "A" * 100  # Long enough, but no diagnosis signals
        state = {
            "agent_response": long_generic,
            "review_retry_count": 0,
        }
        result = reviewer(state)
        assert result["review_passed"] is False
        assert "diagnosis evidence" in result["review_notes"].lower()
        assert result["review_retry_count"] == 1

    def test_accepts_missing_diagnosis_after_retry(self):
        long_generic = "A" * 100
        state = {
            "agent_response": long_generic,
            "review_retry_count": 1,
        }
        result = reviewer(state)
        assert result["review_passed"] is True

    def test_detects_risky_operation(self):
        response = (
            "The pod is failing due to an incorrect image tag. "
            "Likely root cause: typo in the image tag. "
            "Evidence: ImagePullBackOff in events. "
            "Recommended action: kubectl set image deployment/app container=correct:v1.0"
        )
        state = {
            "agent_response": response,
            "review_retry_count": 0,
        }
        result = reviewer(state)
        assert result["review_passed"] is True
        assert result["requires_approval"] is True
        assert "OPERATOR APPROVAL REQUIRED" in result["agent_response"]

    def test_max_one_retry_guard(self):
        """Reviewer must NEVER set review_retry_count > 1 for a failed response."""
        state = {
            "agent_response": "tiny",
            "review_retry_count": 1,
        }
        result = reviewer(state)
        # Even though response is terrible, it must pass (max retries reached)
        assert result["review_passed"] is True
        assert result["review_retry_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Human gate tests
# ═══════════════════════════════════════════════════════════════════════════


class TestHumanGate:

    def test_appends_banner_when_missing(self):
        state = {"agent_response": "Some response without banner"}
        result = human_gate(state)
        assert "OPERATOR APPROVAL REQUIRED" in result["agent_response"]

    def test_does_not_duplicate_banner(self):
        state = {"agent_response": "Response\n⚠️  **OPERATOR APPROVAL REQUIRED**\nAlready here."}
        result = human_gate(state)
        assert result["agent_response"].count("OPERATOR APPROVAL REQUIRED") == 1


# ═══════════════════════════════════════════════════════════════════════════
# Routing function tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRoutingFunctions:

    def test_route_after_advance_more_specialists(self):
        state = {"plan": ["kubernetes", "aws"], "plan_index": 1}
        assert route_after_advance(state) == "run_specialist"

    def test_route_after_advance_plan_complete(self):
        state = {"plan": ["kubernetes"], "plan_index": 1}
        assert route_after_advance(state) == "reviewer"

    def test_route_after_reviewer_pass_clean(self):
        state = {"review_passed": True, "requires_approval": False}
        assert route_after_reviewer(state) == "__end__"

    def test_route_after_reviewer_pass_risky(self):
        state = {"review_passed": True, "requires_approval": True}
        assert route_after_reviewer(state) == "human_gate"

    def test_route_after_reviewer_fail_retry(self):
        state = {"review_passed": False, "requires_approval": False}
        assert route_after_reviewer(state) == "run_specialist"


# ═══════════════════════════════════════════════════════════════════════════
# Advance plan tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAdvancePlan:

    def test_increments_plan_index(self):
        state = {"plan_index": 0}
        result = advance_plan(state)
        assert result["plan_index"] == 1

    def test_increments_from_existing(self):
        state = {"plan_index": 2}
        result = advance_plan(state)
        assert result["plan_index"] == 3


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
# Full graph integration tests (mocked LLM, no Gemini)
# ═══════════════════════════════════════════════════════════════════════════


class TestFullGraphPipeline:

    @patch("devops_agents.graph.supervisor_model")
    @patch("devops_agents.agents.kubernetes.model_with_tools")
    def test_single_agent_pipeline_clean_pass(self, mock_k8s_model, mock_supervisor):
        """Supervisor → Planner (1 agent) → K8s → Reviewer → END"""
        mock_supervisor.invoke.return_value = RoutingDecision(
            agent="kubernetes", reason="K8s query"
        )
        response_text = (
            "**Deployment status:** 3/3 replicas available.\n"
            "**Pod finding:** app-7d8f9 (STATUS=Running, READY=1/1)\n"
            "**Evidence:** Events show normal scheduling.\n"
            "**Likely root cause:** No issue found.\n"
            "**Recommended action:** No action needed."
        )
        mock_k8s_model.invoke.return_value = AIMessage(content=response_text)

        config = {"configurable": {"thread_id": "phase7-clean-test"}}
        result = graph.invoke(
            {"messages": [HumanMessage(content="Check my pods")]},
            config=config,
        )

        assert result["selected_agent"] == "kubernetes"
        assert result["review_passed"] is True
        assert result["requires_approval"] is False
        assert response_text in result["agent_response"]

    @patch("devops_agents.graph.supervisor_model")
    @patch("devops_agents.agents.kubernetes.model_with_tools")
    def test_single_agent_pipeline_risky_response(self, mock_k8s_model, mock_supervisor):
        """Supervisor → Planner → K8s → Reviewer (risky) → Human Gate → END"""
        mock_supervisor.invoke.return_value = RoutingDecision(
            agent="kubernetes", reason="K8s query"
        )
        response_text = (
            "The pod is failing due to a wrong image tag. "
            "Likely root cause: typo in image name. "
            "Evidence: ImagePullBackOff in events and describe output. "
            "Recommended action: kubectl set image deployment/app container=correct:v1.0"
        )
        mock_k8s_model.invoke.return_value = AIMessage(content=response_text)

        config = {"configurable": {"thread_id": "phase7-risky-test"}}
        result = graph.invoke(
            {"messages": [HumanMessage(content="Why is my pod failing?")]},
            config=config,
        )

        assert result["selected_agent"] == "kubernetes"
        assert result["review_passed"] is True
        assert result["requires_approval"] is True
        assert "OPERATOR APPROVAL REQUIRED" in result["agent_response"]

    @patch("devops_agents.graph.supervisor_model")
    @patch("devops_agents.agents.kubernetes.model_with_tools")
    @patch("devops_agents.agents.aws.model_with_tools")
    def test_multi_agent_sequential_plan(self, mock_aws_model, mock_k8s_model, mock_supervisor):
        """Cross-domain: Planner produces ["kubernetes", "aws"], both run sequentially."""
        mock_supervisor.invoke.return_value = RoutingDecision(
            agent="kubernetes", reason="K8s + EC2 query"
        )
        k8s_response = (
            "Pod payment-api is CrashLoopBackOff. "
            "Likely root cause: container OOMKilled. "
            "Evidence: kubectl describe shows exit code 137."
        )
        aws_response = (
            "EC2 instance i-12345 is running. "
            "Evidence: DescribeInstances shows healthy state. "
            "Likely cause: no EC2 issue detected."
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

        # The last specialist to run sets selected_agent
        assert result["selected_agent"] == "aws"
        assert result["review_passed"] is True
        # The plan should have been both agents
        assert result["plan"] == ["kubernetes", "aws"]

    @patch("devops_agents.graph.supervisor_model")
    @patch("devops_agents.agents.kubernetes.model_with_tools")
    def test_reviewer_retry_then_accept(self, mock_k8s_model, mock_supervisor):
        """First response is too short → retry → second response is good → pass."""
        mock_supervisor.invoke.return_value = RoutingDecision(
            agent="kubernetes", reason="K8s query"
        )
        short_response = "ok"
        good_response = (
            "**Deployment status:** 2/3 replicas available.\n"
            "**Pod finding:** app-abc123 (STATUS=CrashLoopBackOff, READY=0/1, RESTARTS=15)\n"
            "**Evidence:** OOMKilled exit code 137 in container state.\n"
            "**Likely root cause:** Memory limit too low for application.\n"
            "**Recommended action:** Increase memory limit in deployment spec."
        )
        # First call returns short, second call returns good
        mock_k8s_model.invoke.side_effect = [
            AIMessage(content=short_response),
            AIMessage(content=good_response),
        ]

        config = {"configurable": {"thread_id": "phase7-retry-test"}}
        result = graph.invoke(
            {"messages": [HumanMessage(content="What pods are failing?")]},
            config=config,
        )

        assert result["review_passed"] is True
        assert result["review_retry_count"] >= 1
        assert good_response in result["agent_response"]


# ═══════════════════════════════════════════════════════════════════════════
# Defects D1 & D2 Fix Verification Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDefectFixes:
    """Verify D1 (Multi-agent context preservation) and D2 (Reviewer retry context passing)."""

    @patch.dict("devops_agents.graph._SPECIALIST_MAP", {
        "kubernetes": MagicMock(return_value={
            "agent_response": "K8s pod app-123 in CrashLoopBackOff. Root cause: OOMKilled.",
            "selected_agent": "kubernetes",
        }),
        "aws": MagicMock(return_value={
            "agent_response": "EC2 instance i-abc12345 memory usage at 98%. Likely cause: resource exhaustion.",
            "selected_agent": "aws",
        }),
    })
    def test_d1_multi_agent_context_preservation(self):
        state = {
            "messages": [HumanMessage(content="Check failing pod on ec2")],
            "plan": ["kubernetes", "aws"],
            "plan_index": 0,
            "selected_agent": "kubernetes",
            "agent_response": "",
            "investigation_findings": [],
        }

        # Step 1: Run Kubernetes specialist
        res1 = run_specialist(state)
        assert len(res1["investigation_findings"]) == 1
        assert "[KUBERNETES AGENT FINDINGS]" in res1["investigation_findings"][0]

        # Advance plan
        adv1 = advance_plan(state)
        state.update(res1)
        state.update(adv1)

        # Step 2: Run AWS specialist
        res2 = run_specialist(state)
        assert len(res2["investigation_findings"]) == 2
        assert "[AWS AGENT FINDINGS]" in res2["investigation_findings"][1]

        # Verify combined report preserves BOTH findings
        assert "# Correlated Multi-Agent Investigation Report" in res2["agent_response"]
        assert "K8s pod app-123" in res2["agent_response"]
        assert "EC2 instance i-abc12345" in res2["agent_response"]

        # Verify AWS agent received K8s context in input state messages
        from devops_agents.graph import _SPECIALIST_MAP
        called_state = _SPECIALIST_MAP["aws"].call_args[0][0]
        context_msg = [m for m in called_state.get("messages", []) if "ACCUMULATED INVESTIGATION CONTEXT" in getattr(m, "content", "")]
        assert len(context_msg) == 1
        assert "K8s pod app-123" in context_msg[0].content

    def test_d2_reviewer_retry_context_passed(self):
        mock_k8s = MagicMock(return_value={
            "agent_response": "Improved response: Deployment status is healthy, Pod finding shows app-123 failing. Root cause: ImagePullBackOff.",
            "selected_agent": "kubernetes",
        })
        with patch.dict("devops_agents.graph._SPECIALIST_MAP", {"kubernetes": mock_k8s}):
            state = {
                "messages": [HumanMessage(content="Check failing pod")],
                "plan": ["kubernetes"],
                "plan_index": 0,
                "selected_agent": "kubernetes",
                "agent_response": "Short answer",
                "review_passed": False,
                "review_notes": "Response lacks diagnosis evidence (root cause / evidence sections missing). Requesting retry.",
                "review_retry_count": 1,
                "investigation_findings": ["Short answer"],
            }

            res = run_specialist(state)

            # Verify specialist call received review notes feedback
            called_state = mock_k8s.call_args[0][0]
            feedback_msg = [m for m in called_state.get("messages", []) if "REVIEWER FEEDBACK" in getattr(m, "content", "")]
            assert len(feedback_msg) == 1
            assert "Response lacks diagnosis evidence" in feedback_msg[0].content

            # Verify finding was replaced rather than appended on retry
            assert len(res["investigation_findings"]) == 1
            assert "Improved response" in res["investigation_findings"][0]

