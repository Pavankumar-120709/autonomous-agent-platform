import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import select, update
from .state import AgentGraphState
from .llm_gateway import LLMGateway
from ..models.run import AgentRun, RunStatus
from ..models.step import StepStatus
from ..services.step_recorder import step_recorder
from ..services.event_bus import event_bus
from ..database import AsyncSessionLocal
from ..tools.structured_notes import get_run_notes, clear_run_notes

logger = logging.getLogger("agent.finalizer")


async def finalize_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    FINALIZE Node: Synthesizes observations and notes into the final structured answer,
    records execution metrics, and marks the run status in PostgreSQL.
    """
    run_id = state["run_id"]
    step_num = state["step_number"] + 1
    node_name = "FINALIZE"
    start_time = time.perf_counter()

    step_id = await step_recorder.create_step(run_id, step_num, node_name)

    # Determine status & incomplete reason
    run_status_str = state.get("status", "COMPLETED")
    is_incomplete = run_status_str in ("BUDGET_EXHAUSTED", "TIMED_OUT", "CANCELLED", "FAILED")
    decision_reason = state.get("decision_reason")

    # Gather notes from structured_notes store
    notes_store = get_run_notes(run_id)
    notes_text_parts = []
    for k, v in notes_store.items():
        notes_text_parts.append(f"[{v.category}] {k}: {v.content} (Sources: {', '.join(v.sources)})")
    saved_notes_str = "\n".join(notes_text_parts) if notes_text_parts else "None recorded."

    gateway = LLMGateway(model=state.get("model"))

    system_prompt = (
        "You are an expert research synthesizer. Given the objective, research observations, "
        "and recorded structured notes, produce a structured final answer. "
        "Provide thorough, high-quality synthesis. Include source citations whenever available. "
        "Respond strictly with a JSON object containing keys: "
        "'summary' (string), 'key_findings' (list of strings), 'sources' (list of URLs/citations), "
        "'completion_status' ('completed' or 'incomplete'), 'confidence_score' (float between 0 and 1), "
        "and 'incomplete_reason' (string or null)."
    )

    observations_text = "\n".join(state.get("observations", [])) or "No observations."
    user_prompt = (
        f"Objective: {state['objective']}\n"
        f"Execution Status: {run_status_str}\n"
        f"Limiting factor (if any): {decision_reason or 'None'}\n\n"
        f"Recorded Structured Notes:\n{saved_notes_str}\n\n"
        f"All Tool Observations:\n{observations_text}\n\n"
        "Produce a structured final answer."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    llm_resp = await gateway.call_llm(messages)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    parsed = llm_resp.parsed_json or {}
    summary = parsed.get("summary", f"Research completed for: {state['objective']}")
    key_findings = parsed.get("key_findings", ["Research steps executed and documented."])
    sources = parsed.get("sources", [])
    confidence = parsed.get("confidence_score", 0.9 if not is_incomplete else 0.6)
    completion_status = "incomplete" if is_incomplete else parsed.get("completion_status", "completed")

    final_payload = {
        "summary": summary,
        "key_findings": key_findings,
        "sources": sources,
        "completion_status": completion_status,
        "confidence_score": confidence,
        "incomplete_reason": decision_reason,
    }

    # Update cumulative tokens & cost
    new_total_tokens = state["total_tokens"] + llm_resp.total_tokens
    new_prompt_tokens = state["prompt_tokens"] + llm_resp.prompt_tokens
    new_comp_tokens = state["completion_tokens"] + llm_resp.completion_tokens
    new_cost = state["estimated_cost"] + llm_resp.cost_usd

    # Determine final database run status
    if state.get("is_cancelled", False):
        final_db_status = RunStatus.CANCELLED
    elif run_status_str == "TIMED_OUT":
        final_db_status = RunStatus.TIMED_OUT
    elif run_status_str == "BUDGET_EXHAUSTED":
        final_db_status = RunStatus.BUDGET_EXHAUSTED
    elif run_status_str == "FAILED":
        final_db_status = RunStatus.FAILED
    else:
        final_db_status = RunStatus.COMPLETED

    total_run_duration = time.time() - state["start_time"]

    # Finalize DB step
    await step_recorder.finish_step(
        step_id=step_id,
        run_id=run_id,
        step_number=step_num,
        node_name=node_name,
        status=StepStatus.COMPLETED,
        duration_ms=duration_ms,
        prompt_tokens=llm_resp.prompt_tokens,
        completion_tokens=llm_resp.completion_tokens,
        total_tokens=llm_resp.total_tokens,
        estimated_cost=llm_resp.cost_usd,
        remaining_token_budget=max(0, state["token_budget"] - new_total_tokens),
        remaining_time_budget=max(0.0, state["timeout_seconds"] - total_run_duration),
        agent_decision="END",
        thought=f"Synthesized final answer. Status: {final_db_status.value}.",
        metadata_json={"completion_status": completion_status},
    )

    # Update DB AgentRun row
    async with AsyncSessionLocal() as session:
        stmt = (
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(
                status=final_db_status,
                final_response=final_payload,
                total_tokens=new_total_tokens,
                prompt_tokens=new_prompt_tokens,
                completion_tokens=new_comp_tokens,
                estimated_cost=new_cost,
                step_count=step_num,
                end_time=datetime.now(timezone.utc),
                duration_seconds=round(total_run_duration, 2),
                error_message=decision_reason,
            )
        )
        await session.execute(stmt)
        await session.commit()

    # Emit final run completion event
    await event_bus.emit(
        run_id=run_id,
        event_type="run_completed" if final_db_status == RunStatus.COMPLETED else "run_ended",
        payload={
            "status": final_db_status.value,
            "final_response": final_payload,
            "total_tokens": new_total_tokens,
            "estimated_cost": new_cost,
            "duration_seconds": round(total_run_duration, 2),
            "step_count": step_num,
        },
    )

    # Clean up run notes
    clear_run_notes(run_id)

    return {
        "step_number": step_num,
        "final_response": final_payload,
        "decision": "END",
        "status": final_db_status.value,
        "total_tokens": new_total_tokens,
        "prompt_tokens": new_prompt_tokens,
        "completion_tokens": new_comp_tokens,
        "estimated_cost": new_cost,
    }
