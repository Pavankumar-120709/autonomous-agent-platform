import asyncio
import pytest
from app.services.agent_runner import AgentRunner
from app.services.run_service import RunService
from app.schemas.run import RunCreateRequest
from app.models.run import RunStatus


@pytest.mark.asyncio
async def test_end_to_end_agent_execution(db_session):
    req = RunCreateRequest(
        objective="Investigate quantum computing milestones and record findings in notes.",
        model="gpt-4o-mini",
        max_steps=12,
        max_tool_calls_per_step=2,
        token_budget=30000,
        timeout_seconds=60.0,
    )

    run = await RunService.create_and_start_run(req)
    assert run.id is not None

    # Wait for the workflow to complete
    max_wait_seconds = 15
    start_t = asyncio.get_event_loop().time()
    completed = False

    while (asyncio.get_event_loop().time() - start_t) < max_wait_seconds:
        r = await RunService.get_run_by_id(run.id)
        if r and r.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.TIMED_OUT, RunStatus.BUDGET_EXHAUSTED):
            completed = True
            break
        await asyncio.sleep(0.3)

    assert completed is True, "Agent run did not finish within timeout"

    final_run = await RunService.get_run_by_id(run.id)
    assert final_run is not None
    assert final_run.status == RunStatus.COMPLETED
    assert final_run.step_count > 0
    assert final_run.final_response is not None
    assert "summary" in final_run.final_response

    # Verify steps were recorded
    steps = await RunService.get_run_steps(run.id)
    assert len(steps) >= 3
    node_names = [s.node_name for s in steps]
    assert "PLAN" in node_names
    assert "FINALIZE" in node_names

    # Verify tool executions were persisted
    assert len(final_run.tool_executions) >= 1
    tool_names = [t.tool_name for t in final_run.tool_executions]
    assert any(t in ("calculator", "structured_notes", "web_search", "webpage_reader") for t in tool_names)
