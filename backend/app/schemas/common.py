from typing import Any, Dict, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    database: str
    active_runs: int = 0


class AnalyticsResponse(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    cancelled_runs: int
    timed_out_runs: int
    budget_exhausted_runs: int
    success_rate_percent: float
    avg_duration_seconds: float
    avg_steps_per_run: float
    avg_tool_calls_per_run: float
    total_tokens_consumed: int
    total_prompt_tokens: int
    total_completion_tokens: int
    estimated_total_cost_usd: float
    tool_usage_counts: Dict[str, int]
    tool_failure_counts: Dict[str, int]
    tool_success_rates: Dict[str, float]
