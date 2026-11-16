import time
from app.agent.limits import check_runtime_limits, check_action_repetition
from app.agent.state import AgentGraphState


def test_step_budget_limit():
    state: AgentGraphState = {
        "run_id": "test",
        "objective": "test",
        "model": "gpt-4o-mini",
        "max_steps": 5,
        "max_tool_calls_per_step": 4,
        "token_budget": 50000,
        "timeout_seconds": 180.0,
        "start_time": time.time(),
        "step_number": 5,
        "total_tokens": 1000,
        "prompt_tokens": 500,
        "completion_tokens": 500,
        "estimated_cost": 0.01,
        "consecutive_failures": 0,
        "plan": None,
        "planned_steps": [],
        "current_thought": None,
        "selected_tools": [],
        "tool_results": [],
        "action_history": [],
        "observations": [],
        "decision": "PLAN",
        "decision_reason": None,
        "final_response": None,
        "error_message": None,
        "status": "RUNNING",
        "is_cancelled": False,
    }
    should_stop, reason, status = check_runtime_limits(state)
    assert should_stop is True
    assert "Maximum step budget" in reason
    assert status == "BUDGET_EXHAUSTED"


def test_token_budget_limit():
    state: AgentGraphState = {
        "run_id": "test",
        "objective": "test",
        "model": "gpt-4o-mini",
        "max_steps": 12,
        "max_tool_calls_per_step": 4,
        "token_budget": 1000,
        "timeout_seconds": 180.0,
        "start_time": time.time(),
        "step_number": 2,
        "total_tokens": 1500,  # exceeds 1000
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "estimated_cost": 0.01,
        "consecutive_failures": 0,
        "plan": None,
        "planned_steps": [],
        "current_thought": None,
        "selected_tools": [],
        "tool_results": [],
        "action_history": [],
        "observations": [],
        "decision": "PLAN",
        "decision_reason": None,
        "final_response": None,
        "error_message": None,
        "status": "RUNNING",
        "is_cancelled": False,
    }
    should_stop, reason, status = check_runtime_limits(state)
    assert should_stop is True
    assert "Token budget exhausted" in reason
    assert status == "BUDGET_EXHAUSTED"


def test_loop_detection_limit():
    repeated_sig = 'web_search:{"query": "quantum computing"}'
    state: AgentGraphState = {
        "run_id": "test",
        "objective": "test",
        "model": "gpt-4o-mini",
        "max_steps": 12,
        "max_tool_calls_per_step": 4,
        "token_budget": 50000,
        "timeout_seconds": 180.0,
        "start_time": time.time(),
        "step_number": 3,
        "total_tokens": 1000,
        "prompt_tokens": 500,
        "completion_tokens": 500,
        "estimated_cost": 0.01,
        "consecutive_failures": 0,
        "plan": None,
        "planned_steps": [],
        "current_thought": None,
        "selected_tools": [],
        "tool_results": [],
        "action_history": [repeated_sig, repeated_sig, repeated_sig],
        "observations": [],
        "decision": "PLAN",
        "decision_reason": None,
        "final_response": None,
        "error_message": None,
        "status": "RUNNING",
        "is_cancelled": False,
    }
    should_stop, reason, status = check_runtime_limits(state)
    assert should_stop is True
    assert "Loop detected" in reason


def test_repeated_action_detection():
    sig = 'calculator:{"expression": "2+2"}'
    history = [sig, "other:action", sig]
    assert check_action_repetition(history, sig) is True
    assert check_action_repetition(history, "different:action") is False
