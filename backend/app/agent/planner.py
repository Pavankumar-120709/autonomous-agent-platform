import time
import logging
from typing import Any, Dict
from .state import AgentGraphState
from .llm_gateway import LLMGateway
from .limits import check_runtime_limits
from ..services.step_recorder import step_recorder
from ..models.step import StepStatus

logger = logging.getLogger("agent.planner")


async def plan_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    PLAN Node: Formulates research plan and determines the initial action.
    """
    run_id = state["run_id"]
    step_num = state["step_number"] + 1
    node_name = "PLAN"
    start_time = time.perf_counter()

    # Step persistence
    step_id = await step_recorder.create_step(run_id, step_num, node_name)

    # Check bounds
    should_stop, reason, target_status = check_runtime_limits(state)
    if should_stop:
        await step_recorder.finish_step(
            step_id=step_id,
            run_id=run_id,
            step_number=step_num,
            node_name=node_name,
            status=StepStatus.COMPLETED,
            duration_ms=0.0,
            agent_decision="STOP_LIMIT",
            thought=reason,
            error_details=reason,
        )
        return {
            "step_number": step_num,
            "decision": "STOP_LIMIT",
            "decision_reason": reason,
            "status": target_status or "FAILED",
        }

    gateway = LLMGateway(model=state.get("model"))

    system_prompt = (
        "You are an expert autonomous research planner. Given a user objective, formulate a concise, "
        "step-by-step investigation plan and propose the first high-yield tool action. "
        "Available tools: web_search (find sources), webpage_reader (extract content), "
        "calculator (numerical math), structured_notes (save/retrieve insights). "
        "Respond strictly with a JSON object containing keys: 'plan' (string), 'planned_steps' (list of strings), "
        "'initial_thought' (string), and 'initial_tool' (object with 'tool_name' and 'args' or null)."
    )

    user_prompt = (
        f"Objective: {state['objective']}\n"
        "Generate an initial structured research plan to resolve this objective."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    llm_resp = await gateway.call_llm(messages)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    parsed = llm_resp.parsed_json or {}
    plan_text = parsed.get("plan", f"Investigate objective: {state['objective']}")
    planned_steps = parsed.get("planned_steps", ["Gather preliminary data", "Analyze and record findings"])
    thought = parsed.get("initial_thought", "Initial planning complete. Ready to execute first action.")

    # Determine initial tool
    initial_tool = parsed.get("initial_tool")
    selected_tools = []
    if initial_tool and isinstance(initial_tool, dict) and "tool_name" in initial_tool:
        selected_tools.append(initial_tool)
    else:
        # Default first tool: web search to gather preliminary facts on the objective
        selected_tools.append({"tool_name": "web_search", "args": {"query": state["objective"][:80], "max_results": 3}})

    # Limit to max tool calls
    selected_tools = selected_tools[:state.get("max_tool_calls_per_step", 4)]

    # Calculate remaining budgets
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
        agent_decision="EXECUTE_TOOL",
        thought=thought,
        selected_tools=selected_tools,
        metadata_json={"planned_steps": planned_steps},
    )

    return {
        "step_number": step_num,
        "plan": plan_text,
        "planned_steps": planned_steps,
        "current_thought": thought,
        "selected_tools": selected_tools,
        "decision": "EXECUTE_TOOL",
        "total_tokens": new_total_tokens,
        "prompt_tokens": new_prompt_tokens,
        "completion_tokens": new_comp_tokens,
        "estimated_cost": new_cost,
    }
