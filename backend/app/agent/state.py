from typing import Any, Dict, List, Optional, TypedDict


class AgentGraphState(TypedDict):
    run_id: str
    objective: str
    model: str
    max_steps: int
    max_tool_calls_per_step: int
    token_budget: int
    timeout_seconds: float
    start_time: float

    step_number: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float
    consecutive_failures: int

    plan: Optional[str]
    planned_steps: List[str]
    current_thought: Optional[str]

    selected_tools: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    action_history: List[str]
    observations: List[str]

    decision: str  # "EXECUTE_TOOL", "FINALIZE", "STOP_LIMIT", "STOP_ERROR", "STOP_CANCELLED"
    decision_reason: Optional[str]

    final_response: Optional[Dict[str, Any]]
    error_message: Optional[str]
    status: str
    is_cancelled: bool
