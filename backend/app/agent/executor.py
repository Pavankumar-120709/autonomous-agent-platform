import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List
from .state import AgentGraphState
from .limits import check_runtime_limits
from ..tools.registry import create_tool_registry
from ..models.tool_execution import ToolStatus
from ..models.step import StepStatus
from ..services.step_recorder import step_recorder

logger = logging.getLogger("agent.executor")


async def execute_tool_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    EXECUTE_TOOL Node: Executes pending tool calls safely with bounded retries,
    timing, and step-level persistence.
    """
    run_id = state["run_id"]
    step_num = state["step_number"] + 1
    node_name = "EXECUTE_TOOL"
    start_time = time.perf_counter()

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

    registry = create_tool_registry(run_id)
    selected_tools = state.get("selected_tools", [])
    max_tools = state.get("max_tool_calls_per_step", 4)
    tools_to_run = selected_tools[:max_tools]

    executed_results = []
    action_history = list(state.get("action_history", []))
    any_success = False

    for item in tools_to_run:
        tool_name = item.get("tool_name", "")
        args = item.get("args", {})

        action_signature = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        action_history.append(action_signature)

        tool = registry.get_tool(tool_name)
        if not tool:
            err_msg = f"Tool '{tool_name}' not found in registry."
            await step_recorder.record_tool_execution(
                run_id=run_id,
                step_id=step_id,
                tool_name=tool_name,
                tool_input=args,
                tool_output=None,
                status=ToolStatus.FAILURE,
                duration_ms=0.0,
                error_message=err_msg,
            )
            executed_results.append({
                "tool_name": tool_name,
                "input": args,
                "success": False,
                "error": err_msg,
                "output": None,
            })
            continue

        # Execute with retry policy (retry only transient network/timeout errors, max 2 retries)
        max_tool_retries = 2
        retry_count = 0
        final_result = None

        while retry_count <= max_tool_retries:
            res = await tool.execute(**args)
            if res.success:
                final_result = res
                any_success = True
                break

            # Check if failure is transient
            is_transient = "timeout" in (res.error or "").lower() or "connection" in (res.error or "").lower()
            if not is_transient or retry_count == max_tool_retries:
                final_result = res
                break

            retry_count += 1
            backoff = (1.5 ** retry_count) + random.uniform(0.1, 0.4)
            logger.info(f"Retrying tool '{tool_name}' (attempt {retry_count}) in {backoff:.2f}s...")
            await asyncio.sleep(backoff)

        status_enum = ToolStatus.SUCCESS if final_result.success else ToolStatus.FAILURE
        if "timed out" in (final_result.error or "").lower():
            status_enum = ToolStatus.TIMEOUT

        output_data = final_result.data if final_result.success else None
        if hasattr(output_data, "model_dump"):
            output_dict = output_data.model_dump()
        elif isinstance(output_data, dict):
            output_dict = output_data
        else:
            output_dict = {"result": output_data}

        await step_recorder.record_tool_execution(
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            tool_input=args,
            tool_output=output_dict,
            status=status_enum,
            duration_ms=final_result.execution_time_ms,
            retry_count=retry_count,
            error_message=final_result.error,
            metadata_json=final_result.metadata,
        )

        executed_results.append({
            "tool_name": tool_name,
            "input": args,
            "success": final_result.success,
            "error": final_result.error,
            "output": output_dict,
            "execution_time_ms": final_result.execution_time_ms,
        })

    duration_ms = (time.perf_counter() - start_time) * 1000.0

    # Failure tracking
    consecutive_failures = state.get("consecutive_failures", 0)
    if not any_success and executed_results:
        consecutive_failures += 1
    else:
        consecutive_failures = 0

    elapsed_total = time.time() - state["start_time"]
    rem_time = max(0.0, state["timeout_seconds"] - elapsed_total)
    rem_tokens = max(0, state["token_budget"] - state["total_tokens"])

    thought_summary = f"Executed {len(executed_results)} tool action(s). Success: {any_success}."
    await step_recorder.finish_step(
        step_id=step_id,
        run_id=run_id,
        step_number=step_num,
        node_name=node_name,
        status=StepStatus.COMPLETED,
        duration_ms=duration_ms,
        remaining_token_budget=rem_tokens,
        remaining_time_budget=rem_time,
        agent_decision="OBSERVE",
        thought=thought_summary,
        selected_tools=tools_to_run,
        metadata_json={"executed_count": len(executed_results), "any_success": any_success},
    )

    return {
        "step_number": step_num,
        "tool_results": executed_results,
        "action_history": action_history,
        "consecutive_failures": consecutive_failures,
        "decision": "OBSERVE",
    }
