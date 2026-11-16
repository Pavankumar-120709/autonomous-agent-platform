from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from ..models.step import StepStatus
from .tool import ToolExecutionResponse


class StepResponse(BaseModel):
    id: str
    run_id: str
    step_number: int
    node_name: str
    status: StepStatus
    agent_decision: Optional[str] = None
    thought: Optional[str] = None
    selected_tools: Optional[List[Any]] = None
    duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    remaining_token_budget: int
    remaining_time_budget: float
    metadata_json: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    created_at: datetime
    tool_executions: List[ToolExecutionResponse] = []

    model_config = ConfigDict(from_attributes=True)
