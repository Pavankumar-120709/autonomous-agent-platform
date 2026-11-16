import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from ..database import AsyncSessionLocal
from ..models.run import AgentRun, RunStatus
from ..models.step import AgentStep, StepStatus
from ..models.tool_execution import ToolExecution, ToolStatus
from .event_bus import event_bus

logger = logging.getLogger("agent.step_recorder")


class StepRecorder:
    @staticmethod
    async def create_step(
        run_id: str,
        step_number: int,
        node_name: str,
    ) -> str:
        async with AsyncSessionLocal() as session:
            step = AgentStep(
                run_id=run_id,
                step_number=step_number,
                node_name=node_name,
                status=StepStatus.RUNNING,
                created_at=datetime.now(timezone.utc),
            )
            session.add(step)
            await session.commit()
            await session.refresh(step)

            await event_bus.emit(
                run_id=run_id,
                event_type="step_started",
                payload={"step_id": step.id, "step_number": step_number, "node_name": node_name},
                step_number=step_number,
            )
            return step.id

    @staticmethod
    async def finish_step(
        step_id: str,
        run_id: str,
        step_number: int,
        node_name: str,
        status: StepStatus,
        duration_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost: float = 0.0,
        remaining_token_budget: int = 0,
        remaining_time_budget: float = 0.0,
        agent_decision: Optional[str] = None,
        thought: Optional[str] = None,
        selected_tools: Optional[List[Any]] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None,
    ):
        async with AsyncSessionLocal() as session:
            stmt = (
                update(AgentStep)
                .where(AgentStep.id == step_id)
                .values(
                    status=status,
                    duration_ms=round(duration_ms, 2),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=round(estimated_cost, 6),
                    remaining_token_budget=remaining_token_budget,
                    remaining_time_budget=round(remaining_time_budget, 2),
                    agent_decision=agent_decision,
                    thought=thought,
                    selected_tools=selected_tools,
                    metadata_json=metadata_json,
                    error_details=error_details,
                )
            )
            await session.execute(stmt)

            # Update run cumulative totals
            run_stmt = select(AgentRun).where(AgentRun.id == run_id)
            res = await session.execute(run_stmt)
            run = res.scalar_one_or_none()
            if run:
                run.total_tokens += total_tokens
                run.prompt_tokens += prompt_tokens
                run.completion_tokens += completion_tokens
                run.estimated_cost += estimated_cost
                run.step_count = max(run.step_count, step_number)

            await session.commit()

            await event_bus.emit(
                run_id=run_id,
                event_type="step_completed" if status == StepStatus.COMPLETED else "step_failed",
                payload={
                    "step_id": step_id,
                    "step_number": step_number,
                    "node_name": node_name,
                    "status": status.value,
                    "duration_ms": duration_ms,
                    "total_tokens": total_tokens,
                    "estimated_cost": estimated_cost,
                    "decision": agent_decision,
                    "thought": thought,
                },
                step_number=step_number,
            )

    @staticmethod
    async def record_tool_execution(
        run_id: str,
        step_id: Optional[str],
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Optional[Dict[str, Any]],
        status: ToolStatus,
        duration_ms: float,
        retry_count: int = 0,
        error_message: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> str:
        async with AsyncSessionLocal() as session:
            tool_exec = ToolExecution(
                run_id=run_id,
                step_id=step_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                status=status,
                duration_ms=round(duration_ms, 2),
                retry_count=retry_count,
                error_message=error_message,
                metadata_json=metadata_json,
                created_at=datetime.now(timezone.utc),
            )
            session.add(tool_exec)

            # Increment tool count in run
            run_stmt = select(AgentRun).where(AgentRun.id == run_id)
            res = await session.execute(run_stmt)
            run = res.scalar_one_or_none()
            if run:
                run.tool_call_count += 1

            await session.commit()
            await session.refresh(tool_exec)

            event_type = "tool_completed" if status == ToolStatus.SUCCESS else "tool_failed"
            await event_bus.emit(
                run_id=run_id,
                event_type=event_type,
                payload={
                    "tool_execution_id": tool_exec.id,
                    "tool_name": tool_name,
                    "status": status.value,
                    "duration_ms": duration_ms,
                    "retry_count": retry_count,
                    "error": error_message,
                    "input": tool_input,
                    "output": tool_output,
                },
            )
            return tool_exec.id


step_recorder = StepRecorder()
