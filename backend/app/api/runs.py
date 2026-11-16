import asyncio
import json
from typing import List
from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse
from ..schemas.run import RunCreateRequest, RunDetail, RunSummary
from ..schemas.step import StepResponse
from ..services.run_service import RunService
from ..services.event_bus import event_bus
from ..models.run import RunStatus

router = APIRouter(prefix="/runs", tags=["Agent Runs"])


@router.post("", response_model=RunSummary, status_code=201)
async def create_run(req: RunCreateRequest):
    """
    Creates and starts a new autonomous agent execution with explicit bounds.
    """
    run = await RunService.create_and_start_run(req)
    return run


@router.get("", response_model=List[RunSummary])
async def list_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Browse previous agent runs ordered by recency.
    """
    return await RunService.list_runs(skip=skip, limit=limit)


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: str):
    """
    Retrieve comprehensive details, metrics, and persisted steps for a specific run.
    """
    run = await RunService.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run with ID '{run_id}' not found.")
    return run


@router.get("/{run_id}/steps", response_model=List[StepResponse])
async def get_run_steps(run_id: str):
    """
    Retrieve step-by-step execution timeline for a run.
    """
    steps = await RunService.get_run_steps(run_id)
    return steps


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str):
    """
    Signals cooperative early cancellation of an active agent run.
    """
    run = await RunService.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run with ID '{run_id}' not found.")

    if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.TIMED_OUT):
        return {"status": "already_terminated", "run_id": run_id, "current_status": run.status.value}

    cancelled = await RunService.cancel_run(run_id)
    return {"status": "cancellation_requested", "run_id": run_id, "active_task_cancelled": cancelled}


@router.get("/{run_id}/events")
async def stream_run_events(run_id: str, request: Request):
    """
    Server-Sent Events (SSE) live execution trace endpoint.
    Streams real-time agent decisions, tool invocations, tokens, and outputs.
    """
    run = await RunService.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run with ID '{run_id}' not found.")

    queue = event_bus.subscribe(run_id)

    async def event_generator():
        # First send initial current state of run
        init_payload = {
            "run_id": run.id,
            "status": run.status.value,
            "total_tokens": run.total_tokens,
            "estimated_cost": run.estimated_cost,
            "step_count": run.step_count,
            "final_response": run.final_response,
        }
        yield {
            "event": "run_state",
            "data": json.dumps(init_payload),
        }

        # If already terminated, exit quickly
        if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.TIMED_OUT, RunStatus.BUDGET_EXHAUSTED):
            yield {
                "event": "run_completed",
                "data": json.dumps({"status": run.status.value, "final_response": run.final_response}),
            }
            return

        try:
            while True:
                # Check client disconnect
                if await request.is_disconnected():
                    break

                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "event": event_data.get("event_type", "message"),
                        "data": json.dumps(event_data),
                    }
                    if event_data.get("event_type") in ("run_completed", "run_ended", "run_failed", "run_cancelled"):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield {
                        "event": "ping",
                        "data": json.dumps({"ping": True}),
                    }
        finally:
            event_bus.unsubscribe(run_id, queue)

    return EventSourceResponse(event_generator())
