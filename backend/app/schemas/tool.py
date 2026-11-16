from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict
from ..models.tool_execution import ToolStatus


class ToolExecutionResponse(BaseModel):
    id: str
    run_id: str
    step_id: Optional[str] = None
    tool_name: str
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    status: ToolStatus
    duration_ms: float
    retry_count: int
    error_message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolCallItem(BaseModel):
    id: str
    tool_name: str
    args: Dict[str, Any]
