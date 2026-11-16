from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from ..database import AsyncSessionLocal
from ..models.run import AgentRun, RunStatus
from ..models.step import AgentStep
from ..schemas.run import RunCreateRequest, RunDetail, RunSummary
from ..schemas.step import StepResponse
from .agent_runner import AgentRunner


class RunService:
    @staticmethod
    async def create_and_start_run(req: RunCreateRequest) -> AgentRun:
        async with AsyncSessionLocal() as session:
            run = AgentRun(
                objective=req.objective,
                model=req.model,
                max_steps=req.max_steps,
                max_tool_calls_per_step=req.max_tool_calls_per_step,
                token_budget=req.token_budget,
                timeout_seconds=req.timeout_seconds,
                status=RunStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

            # Dispatch background worker
            AgentRunner.dispatch_run(
                run_id=run.id,
                objective=run.objective,
                model=run.model,
                max_steps=run.max_steps,
                max_tool_calls_per_step=run.max_tool_calls_per_step,
                token_budget=run.token_budget,
                timeout_seconds=run.timeout_seconds,
            )

            return run

    @staticmethod
    async def get_run_by_id(run_id: str) -> Optional[AgentRun]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AgentRun)
                .where(AgentRun.id == run_id)
                .options(
                    selectinload(AgentRun.steps).selectinload(AgentStep.tool_executions),
                    selectinload(AgentRun.tool_executions),
                )
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    @staticmethod
    async def list_runs(skip: int = 0, limit: int = 50) -> List[AgentRun]:
        async with AsyncSessionLocal() as session:
            stmt = select(AgentRun).order_by(desc(AgentRun.created_at)).offset(skip).limit(limit)
            res = await session.execute(stmt)
            return list(res.scalars().all())

    @staticmethod
    async def get_run_steps(run_id: str) -> List[AgentStep]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AgentStep)
                .where(AgentStep.run_id == run_id)
                .options(selectinload(AgentStep.tool_executions))
                .order_by(AgentStep.step_number)
            )
            res = await session.execute(stmt)
            return list(res.scalars().all())

    @staticmethod
    async def cancel_run(run_id: str) -> bool:
        return await AgentRunner.cancel_run(run_id)
