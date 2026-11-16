from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ..models.run import RunStatus
from .step import StepResponse
from .tool import ToolExecutionResponse


class FinalResponseSchema(BaseModel):
    summary: str
    key_findings: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    completion_status: str = "completed"
    confidence_score: Optional[float] = 1.0
    incomplete_reason: Optional[str] = None


class RunCreateRequest(BaseModel):
    objective: str = Field(..., min_length=3, max_length=5000, description="Task objective for the autonomous research agent.")
    model: str = Field(default="gpt-4o-mini", description="Configured LLM model to use.")
    max_steps: int = Field(default=12, ge=1, le=12, description="Maximum number of steps (bounded to max 12).")
    max_tool_calls_per_step: int = Field(default=4, ge=1, le=4, description="Maximum tool calls per step (bounded to max 4).")
    token_budget: int = Field(default=50000, ge=1000, le=200000, description="Total token budget for the run.")
    timeout_seconds: float = Field(default=180.0, ge=10.0, le=600.0, description="Wall-clock execution timeout in seconds.")

    @field_validator("objective")
    def validate_objective(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Objective cannot be empty.")
        return clean


class RunSummary(BaseModel):
    id: str
    objective: str
    model: str
    status: RunStatus
    max_steps: int
    step_count: int
    tool_call_count: int
    total_tokens: int
    estimated_cost: float
    duration_seconds: Optional[float] = None
    created_at: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RunDetail(BaseModel):
    id: str
    objective: str
    model: str
    status: RunStatus
    max_steps: int
    max_tool_calls_per_step: int
    token_budget: int
    timeout_seconds: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float
    step_count: int
    tool_call_count: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    final_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    steps: List[StepResponse] = []
    tool_executions: List[ToolExecutionResponse] = []

    model_config = ConfigDict(from_attributes=True)
