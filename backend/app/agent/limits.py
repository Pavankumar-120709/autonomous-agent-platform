import time
from typing import Dict, Optional, Tuple
from .state import AgentGraphState
from ..config import settings


class LimitExceededException(Exception):
    def __init__(self, reason: str, status: str):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def check_runtime_limits(state: AgentGraphState) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Checks all safety boundaries for the agent.
    Returns (should_terminate, reason, target_status).
    """
    # 1. Cancellation Check
    if state.get("is_cancelled", False):
        return True, "Execution was cancelled by the user.", "CANCELLED"

    # 2. Wall-clock execution timeout
    now = time.time()
    start_time = state.get("start_time", now)
    elapsed = now - start_time
    timeout_limit = state.get("timeout_seconds", settings.DEFAULT_WALL_CLOCK_TIMEOUT)
    if elapsed >= timeout_limit:
        return (
            True,
            f"Wall-clock execution timeout of {timeout_limit:.1f}s exceeded (elapsed: {elapsed:.1f}s).",
            "TIMED_OUT",
        )

    # 3. Maximum steps limit
    max_steps = min(state.get("max_steps", settings.MAX_STEPS_LIMIT), settings.MAX_STEPS_LIMIT)
    step_number = state.get("step_number", 0)
    if step_number >= max_steps:
        return (
            True,
            f"Maximum step budget of {max_steps} steps reached.",
            "BUDGET_EXHAUSTED",
        )

    # 4. Token budget check
    token_budget = state.get("token_budget", settings.DEFAULT_TOKEN_BUDGET)
    total_tokens = state.get("total_tokens", 0)
    if total_tokens >= token_budget:
        return (
            True,
            f"Token budget exhausted ({total_tokens}/{token_budget} tokens).",
            "BUDGET_EXHAUSTED",
        )

    # 5. Consecutive failures
    failures = state.get("consecutive_failures", 0)
    if failures >= settings.MAX_CONSECUTIVE_FAILURES:
        return (
            True,
            f"Halted due to {failures} consecutive tool/reasoning failures.",
            "FAILED",
        )

    # 6. Loop / Repeated Action Detection
    history = state.get("action_history", [])
    if len(history) >= 3:
        # Check if the last 3 actions are completely identical
        last_action = history[-1]
        if history[-2] == last_action and history[-3] == last_action:
            return (
                True,
                f"Loop detected: Agent repeated action '{last_action}' 3 consecutive times without progress.",
                "FAILED",
            )

    return False, None, None


def check_action_repetition(history: list, proposed_action: str) -> bool:
    """Returns True if the proposed action is already repeated excessively."""
    count = sum(1 for a in history[-4:] if a == proposed_action)
    return count >= 2
