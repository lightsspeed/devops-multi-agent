"""
Reviewer — Phase 7

Rule-based quality gate.  Zero additional LLM calls.

Checks performed (in order):
    1. Minimum length — response must not be empty / suspiciously short.
    2. Required sections — response must contain at least some evidence of
       structured diagnosis output (not just a one-liner).
    3. Diagnosis evidence — response should mention root-cause or evidence
       language, indicating the agent actually investigated.
    4. Risky remediation detection — scans for kubectl/AWS write verbs and
       sets requires_approval = True; adds an approval banner.

review_passed = True  → response is good enough to return to the user
review_passed = False → trigger one retry (graph handles the max-1 guard
                        via review_retry_count)
"""

import re

from devops_agents.state import AgentState


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_RESPONSE_CHARS = 80

# Phrases that indicate the agent actually diagnosed something
_DIAGNOSIS_SIGNALS = [
    "root cause", "likely cause", "failure reason", "likely root cause",
    "evidence", "pod finding", "deployment status", "container state",
    "recommended", "recommendation",
    # Linux / AWS equivalents
    "likely cause", "evidence checked", "aws cli", "instance state",
    "disk usage", "memory usage", "cpu usage", "process",
]

# kubectl + AWS write verbs that would require operator approval
_RISKY_KUBECTL_PATTERNS = [
    r"\bkubectl\s+(?:delete|scale|set\s+image|rollout|apply|patch|replace|restart)\b",
]

_RISKY_AWS_PATTERNS = [
    r"\baws\s+(?:ec2|s3|iam|lambda|rds)\s+\S+(?:\s+--\S+)*",
    r"\bterraform\s+(?:apply|destroy)\b",
]

# Human-approval banner appended to any response that recommends risky actions
_APPROVAL_BANNER = (
    "\n\n---\n"
    "⚠️  **OPERATOR APPROVAL REQUIRED**\n"
    "The above recommendation includes infrastructure write operations.\n"
    "**The agent has NOT executed any command.**\n"
    "Review the proposed action carefully and execute it manually after approval.\n"
    "---"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_diagnosis_evidence(text: str) -> bool:
    lower = text.lower()
    return any(signal in lower for signal in _DIAGNOSIS_SIGNALS)


def _detect_risky_operations(text: str) -> bool:
    """Return True if response text contains risky write-operation recommendations."""
    for pattern in _RISKY_KUBECTL_PATTERNS + _RISKY_AWS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


# ---------------------------------------------------------------------------
# Reviewer node
# ---------------------------------------------------------------------------

def reviewer(state: AgentState) -> dict:
    """
    Reviewer node — validates agent_response quality and flags risky actions.

    Returns updated fields:
        review_passed       bool
        review_notes        str
        requires_approval   bool
        agent_response      str  (may be appended with approval banner)
    """
    response: str = state.get("agent_response", "")
    retry_count: int = state.get("review_retry_count", 0)

    # -----------------------------------------------------------------------
    # Quality checks
    # -----------------------------------------------------------------------

    # 1. Empty / too short
    if not response or len(response.strip()) < _MIN_RESPONSE_CHARS:
        if retry_count < 1:
            return {
                "review_passed": False,
                "review_notes": (
                    f"Response too short ({len(response.strip())} chars, "
                    f"minimum {_MIN_RESPONSE_CHARS}). Requesting retry."
                ),
                "requires_approval": False,
                "review_retry_count": retry_count + 1,
            }
        else:
            # Already retried once — accept what we have to avoid loops
            return {
                "review_passed": True,
                "review_notes": "Accepted after retry (response still short but max retries reached).",
                "requires_approval": False,
                "review_retry_count": retry_count,
            }

    # 2. Diagnosis evidence missing
    if not _has_diagnosis_evidence(response):
        if retry_count < 1:
            return {
                "review_passed": False,
                "review_notes": (
                    "Response lacks diagnosis evidence (root cause / evidence sections missing). "
                    "Requesting retry."
                ),
                "requires_approval": False,
                "review_retry_count": retry_count + 1,
            }
        else:
            return {
                "review_passed": True,
                "review_notes": "Accepted after retry (diagnosis evidence still missing but max retries reached).",
                "requires_approval": False,
                "review_retry_count": retry_count,
            }

    # -----------------------------------------------------------------------
    # Safety / risky action detection
    # -----------------------------------------------------------------------
    risky = _detect_risky_operations(response)

    if risky:
        # Append banner if not already present
        if "OPERATOR APPROVAL REQUIRED" not in response:
            response = response + _APPROVAL_BANNER

        return {
            "review_passed": True,
            "review_notes": "Response approved. Risky operation detected — approval banner added.",
            "requires_approval": True,
            "agent_response": response,
            "review_retry_count": retry_count,
        }

    # -----------------------------------------------------------------------
    # All checks passed
    # -----------------------------------------------------------------------
    return {
        "review_passed": True,
        "review_notes": "Response passed all quality and safety checks.",
        "requires_approval": False,
        "review_retry_count": retry_count,
    }
