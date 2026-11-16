import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy import select, update
from ..agent.graph import agent_app
from ..agent.state import AgentGraphState
from ..database import AsyncSessionLocal
from ..models.run import AgentRun, RunStatus
from .event_bus import event_bus

logger = logging.getLogger("agent.runner")

# In-memory tracking of active tasks and cancellation flags
_ACTIVE_TASKS: Dict[str, asyncio.Task] = {}
_CANCELLED_RUNS: set = set()


class AgentRunner:
    @staticmethod
    def is_cancelled(run_id: str) -> bool:
        return run_id in _CANCELLED_RUNS

    @classmethod
    async def cancel_run(cls, run_id: str) -> bool:
        _CANCELLED_RUNS.add(run_id)

        # Update DB flag
        async with AsyncSessionLocal() as session:
            stmt = update(AgentRun).where(AgentRun.id == run_id).values(is_cancelled=True)
            await session.execute(stmt)
            await session.commit()

        await event_bus.emit(
            run_id=run_id,
            event_type="run_cancelled",
            payload={"message": "Cancellation requested by user."},
        )

        task = _ACTIVE_TASKS.get(run_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    @classmethod
    async def run_agent_workflow(
        cls,
        run_id: str,
        objective: str,
        model: str,
        max_steps: int,
        max_tool_calls_per_step: int,
        token_budget: int,
        timeout_seconds: float,
    ):
        logger.info(f"Starting agent run {run_id} with objective: '{objective[:80]}...'")

        # Update run status to RUNNING in DB
        async with AsyncSessionLocal() as session:
            stmt = (
                update(AgentRun)
                .where(AgentRun.id == run_id)
                .values(
                    status=RunStatus.RUNNING,
                    start_time=datetime.now(timezone.utc),
                )
            )
            await session.execute(stmt)
            await session.commit()

        await event_bus.emit(
            run_id=run_id,
            event_type="run_started",
            payload={"objective": objective, "model": model, "token_budget": token_budget},
        )

        initial_state: AgentGraphState = {
            "run_id": run_id,
            "objective": objective,
            "model": model,
            "max_steps": max_steps,
            "max_tool_calls_per_step": max_tool_calls_per_step,
            "token_budget": token_budget,
            "timeout_seconds": timeout_seconds,
            "start_time": time.time(),
            "step_number": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost": 0.0,
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
            "is_cancelled": cls.is_cancelled(run_id),
        }

        try:
            # LangGraph execution
            async for step_output in agent_app.astream(initial_state):
                if cls.is_cancelled(run_id):
                    logger.info(f"Run {run_id} detected cancellation signal during graph execution.")
                    break

            logger.info(f"Agent run {run_id} workflow completed successfully.")

        except asyncio.CancelledError:
            logger.warning(f"Agent run {run_id} task was cancelled.")
            async with AsyncSessionLocal() as session:
                stmt = (
                    update(AgentRun)
                    .where(AgentRun.id == run_id)
                    .values(
                        status=RunStatus.CANCELLED,
                        end_time=datetime.now(timezone.utc),
                        error_message="Cancelled by user.",
                    )
                )
                await session.execute(stmt)
                await session.commit()

        except Exception as exc:
            logger.error(f"Agent run {run_id} crashed with exception: {exc}", exc_info=True)
            async with AsyncSessionLocal() as session:
                stmt = (
                    update(AgentRun)
                    .where(AgentRun.id == run_id)
                    .values(
                        status=RunStatus.FAILED,
                        end_time=datetime.now(timezone.utc),
                        error_message=f"Fatal agent error: {type(exc).__name__}: {str(exc)}",
                    )
                )
                await session.execute(stmt)
                await session.commit()

            await event_bus.emit(
                run_id=run_id,
                event_type="run_failed",
                payload={"error": str(exc), "exception_type": type(exc).__name__},
            )

        finally:
            _ACTIVE_TASKS.pop(run_id, None)
            _CANCELLED_RUNS.discard(run_id)

    @classmethod
    def dispatch_run(
        cls,
        run_id: str,
        objective: str,
        model: str,
        max_steps: int,
        max_tool_calls_per_step: int,
        token_budget: int,
        timeout_seconds: float,
    ) -> asyncio.Task:
        task = asyncio.create_task(
            cls.run_agent_workflow(
                run_id=run_id,
                objective=objective,
                model=model,
                max_steps=max_steps,
                max_tool_calls_per_step=max_tool_calls_per_step,
                token_budget=token_budget,
                timeout_seconds=timeout_seconds,
            )
        )
        _ACTIVE_TASKS[run_id] = task
        return task
