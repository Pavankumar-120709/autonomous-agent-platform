import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class ToolStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    RETRY = "RETRY"


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_steps.id", ondelete="CASCADE"), nullable=True, index=True)

    tool_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tool_input: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[ToolStatus] = mapped_column(
        Enum(ToolStatus, native_enum=False),
        default=ToolStatus.SUCCESS,
        nullable=False,
        index=True
    )

    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_executions")
    step: Mapped[Optional["AgentStep"]] = relationship("AgentStep", back_populates="tool_executions")
