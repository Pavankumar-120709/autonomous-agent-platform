from typing import Dict
from sqlalchemy import select, func
from ..database import AsyncSessionLocal
from ..models.run import AgentRun, RunStatus
from ..models.tool_execution import ToolExecution, ToolStatus
from ..schemas.common import AnalyticsResponse


class AnalyticsService:
    @staticmethod
    async def get_analytics() -> AnalyticsResponse:
        async with AsyncSessionLocal() as session:
            # 1. Total runs and breakdown by status
            runs_stmt = select(AgentRun.status, func.count(AgentRun.id)).group_by(AgentRun.status)
            runs_res = await session.execute(runs_stmt)
            status_counts = dict(runs_res.all())

            total_runs = sum(status_counts.values())
            completed_runs = status_counts.get(RunStatus.COMPLETED, 0)
            failed_runs = status_counts.get(RunStatus.FAILED, 0)
            cancelled_runs = status_counts.get(RunStatus.CANCELLED, 0)
            timed_out_runs = status_counts.get(RunStatus.TIMED_OUT, 0)
            budget_exhausted_runs = status_counts.get(RunStatus.BUDGET_EXHAUSTED, 0)

            success_rate = (completed_runs / total_runs * 100.0) if total_runs > 0 else 0.0

            # 2. Averages & cumulative totals
            aggregates_stmt = select(
                func.avg(AgentRun.duration_seconds),
                func.avg(AgentRun.step_count),
                func.avg(AgentRun.tool_call_count),
                func.sum(AgentRun.total_tokens),
                func.sum(AgentRun.prompt_tokens),
                func.sum(AgentRun.completion_tokens),
                func.sum(AgentRun.estimated_cost),
            )
            agg_res = await session.execute(aggregates_stmt)
            avg_duration, avg_steps, avg_tools, sum_tokens, sum_prompt, sum_comp, sum_cost = agg_res.one()

            # 3. Tool execution breakdowns
            tools_usage_stmt = select(
                ToolExecution.tool_name,
                func.count(ToolExecution.id)
            ).group_by(ToolExecution.tool_name)
            tu_res = await session.execute(tools_usage_stmt)
            tool_usage_counts = dict(tu_res.all())

            tools_fail_stmt = select(
                ToolExecution.tool_name,
                func.count(ToolExecution.id)
            ).where(ToolExecution.status != ToolStatus.SUCCESS).group_by(ToolExecution.tool_name)
            tf_res = await session.execute(tools_fail_stmt)
            tool_failure_counts = dict(tf_res.all())

            tool_success_rates: Dict[str, float] = {}
            for t_name, total_calls in tool_usage_counts.items():
                fails = tool_failure_counts.get(t_name, 0)
                rate = ((total_calls - fails) / total_calls * 100.0) if total_calls > 0 else 0.0
                tool_success_rates[t_name] = round(rate, 1)

            return AnalyticsResponse(
                total_runs=total_runs,
                completed_runs=completed_runs,
                failed_runs=failed_runs,
                cancelled_runs=cancelled_runs,
                timed_out_runs=timed_out_runs,
                budget_exhausted_runs=budget_exhausted_runs,
                success_rate_percent=round(success_rate, 1),
                avg_duration_seconds=round(avg_duration or 0.0, 2),
                avg_steps_per_run=round(avg_steps or 0.0, 1),
                avg_tool_calls_per_run=round(avg_tools or 0.0, 1),
                total_tokens_consumed=sum_tokens or 0,
                total_prompt_tokens=sum_prompt or 0,
                total_completion_tokens=sum_comp or 0,
                estimated_total_cost_usd=round(sum_cost or 0.0, 6),
                tool_usage_counts=tool_usage_counts,
                tool_failure_counts=tool_failure_counts,
                tool_success_rates=tool_success_rates,
            )
