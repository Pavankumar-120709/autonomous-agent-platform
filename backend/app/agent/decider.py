import json
import logging
import time
from typing import Any, Dict
from .state import AgentGraphState
from .llm_gateway import LLMGateway
from .limits import check_runtime_limits, check_action_repetition
from ..services.step_recorder import step_recorder
from ..models.step import StepStatus

logger = logging.getLogger("agent.decider")


async def decide_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    DECIDE Node: Reasons over prior observations and determines whether to
    execute another tool step or proceed to FINALIZE.
    """
    run_id = state["run_id"]
    step_num = state["step_number"] + 1
    node_name = "DECIDE"
    start_time = time.perf_counter()

    step_id = await step_recorder.create_step(run_id, step_num, node_name)

    # Safety limits check
    should_stop, reason, target_status = check_runtime_limits(state)
    if should_stop:
        logger.info(f"Decider bounds check triggered termination: {reason}")
        # Route directly to FINALIZE to synthesize partial findings cleanly
        await step_recorder.finish_step(
            step_id=step_id,
            run_id=run_id,
            step_number=step_num,
            node_name=node_name,
            status=StepStatus.COMPLETED,
            duration_ms=0.0,
            agent_decision="FINALIZE",
            thought=f"Terminating tool cycle: {reason}. Transitioning to FINALIZE for synthesis.",
            error_details=reason,
        )
        return {
            "step_number": step_num,
            "decision": "FINALIZE",
            "decision_reason": reason,
            "status": target_status or "BUDGET_EXHAUSTED",
        }

    gateway = LLMGateway(model=state.get("model"))

    system_prompt = (
        "You are an autonomous decision engine evaluating research progress. "
        "Review the original objective, the research plan, and the accumulated observations. "
        "Decide whether to execute more tools or finalize the research. "
        "Available tools: web_search, webpage_reader, calculator, structured_notes. "
        "Rules: "
        "1. If you have enough verified facts to thoroughly answer the objective, decide 'FINALIZE'. "
        "2. Never repeat the exact same search or reading step. "
        "3. Limit tool_calls to at most 4 items. "
        "Respond strictly with a JSON object: "
        "{ 'decision': 'EXECUTE_TOOL' | 'FINALIZE', 'thought': 'reasoning summary', 'tool_calls': [{'tool_name': '...', 'args': {...}}] }"
    )

    observations_text = "\n".join(state.get("observations", [])[-5:]) or "No observations yet."
    user_prompt = (
        f"Objective: {state['objective']}\n"
        f"Plan: {state.get('plan')}\n"
        f"Step Number: {step_num} / {state.get('max_steps', 12)}\n"
        f"Recent Observations:\n{observations_text}\n\n"
        "Decide the next action."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    llm_resp = await gateway.call_llm(messages)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    parsed = llm_resp.parsed_json or {}
    decision = parsed.get("decision", "FINALIZE").upper()
    thought = parsed.get("thought", "Evaluating evidence sufficiency.")
    raw_tool_calls = parsed.get("tool_calls", [])

    if decision not in ("EXECUTE_TOOL", "FINALIZE"):
        decision = "FINALIZE"

    # Validate tool calls and check for repetition
    filtered_tool_calls = []
    if decision == "EXECUTE_TOOL":
        for tc in raw_tool_calls:
            t_name = tc.get("tool_name")
            t_args = tc.get("args", {})
            sig = f"{t_name}:{json.dumps(t_args, sort_keys=True)}"

            if check_action_repetition(state.get("action_history", []), sig):
                logger.warning(f"Decider proposed repeated action '{sig}'. Skipping.")
                continue

            filtered_tool_calls.append(tc)

        if not filtered_tool_calls:
            # If all proposed tool calls were duplicates or empty, finalize
            logger.info("No novel tool calls proposed. Transitioning to FINALIZE.")
            decision = "FINALIZE"
            thought += " (All proposed actions were already explored; finalizing)."

    max_calls = state.get("max_tool_calls_per_step", 4)
    filtered_tool_calls = filtered_tool_calls[:max_calls]

    # Calculate token budgets
    new_total_tokens = state["total_tokens"] + llm_resp.total_tokens
    new_prompt_tokens = state["prompt_tokens"] + llm_resp.prompt_tokens
    new_comp_tokens = state["completion_tokens"] + llm_resp.completion_tokens
    new_cost = state["estimated_cost"] + llm_resp.cost_usd
    rem_tokens = max(0, state["token_budget"] - new_total_tokens)
    elapsed_total = time.time() - state["start_time"]
    rem_time = max(0.0, state["timeout_seconds"] - elapsed_total)

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
        remaining_token_budget=rem_tokens,
        remaining_time_budget=rem_time,
        agent_decision=decision,
        thought=thought,
        selected_tools=filtered_tool_calls if decision == "EXECUTE_TOOL" else None,
        metadata_json={"decision": decision, "tool_count": len(filtered_tool_calls)},
    )

    return {
        "step_number": step_num,
        "decision": decision,
        "current_thought": thought,
        "selected_tools": filtered_tool_calls,
        "total_tokens": new_total_tokens,
        "prompt_tokens": new_prompt_tokens,
        "completion_tokens": new_comp_tokens,
        "estimated_cost": new_cost,
    }
