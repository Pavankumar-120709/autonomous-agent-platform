import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Text, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini", nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False),
        default=RunStatus.PENDING,
        nullable=False,
        index=True
    )

    # Configured bounds
    max_steps: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    max_tool_calls_per_step: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    token_budget: Mapped[int] = mapped_column(Integer, default=50000, nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=180.0, nullable=False)

    # Runtime aggregates
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Final outputs and errors
    final_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cancellation flag
    is_cancelled: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    steps: Mapped[List["AgentStep"]] = relationship(
        "AgentStep",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStep.step_number"
    )
    tool_executions: Mapped[List["ToolExecution"]] = relationship(
        "ToolExecution",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ToolExecution.created_at"
    )
    events: Mapped[List["AgentEvent"]] = relationship(
        "AgentEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentEvent.created_at"
    )
