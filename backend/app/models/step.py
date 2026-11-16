import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Text, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class StepStatus(str, enum.Enum):
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NodeName(str, enum.Enum):
    PLAN = "PLAN"
    EXECUTE_TOOL = "EXECUTE_TOOL"
    OBSERVE = "OBSERVE"
    DECIDE = "DECIDE"
    FINALIZE = "FINALIZE"


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, native_enum=False),
        default=StepStatus.STARTED,
        nullable=False
    )

    agent_decision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thought: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_tools: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    remaining_token_budget: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remaining_time_budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="steps")
    tool_executions: Mapped[List["ToolExecution"]] = relationship(
        "ToolExecution",
        back_populates="step",
        cascade="all, delete-orphan"
    )
