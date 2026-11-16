import time
import logging
from typing import Any, Dict
from .state import AgentGraphState
from .limits import check_runtime_limits
from ..services.step_recorder import step_recorder
from ..models.step import StepStatus

logger = logging.getLogger("agent.observer")


async def observe_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    OBSERVE Node: Analyzes and distills the tool outputs into clear, factual observations.
    """
    run_id = state["run_id"]
    step_num = state["step_number"] + 1
    node_name = "OBSERVE"
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

    tool_results = state.get("tool_results", [])
    new_observations = []

    for item in tool_results:
        tool_name = item.get("tool_name")
        success = item.get("success")
        output = item.get("output")
        err = item.get("error")

        if not success:
            obs = f"Observation [{tool_name}]: Action failed with error: {err}"
        else:
            if tool_name == "web_search":
                res_list = output.get("results", []) if isinstance(output, dict) else []
                snippets = []
                for r in res_list[:3]:
                    snippets.append(f"- {r.get('title')}: {r.get('snippet')} (URL: {r.get('url')})")
                obs = f"Observation [web_search]: Found {len(res_list)} results.\n" + "\n".join(snippets)

            elif tool_name == "calculator":
                fmt = output.get("formatted", str(output)) if isinstance(output, dict) else str(output)
                obs = f"Observation [calculator]: Calculated {fmt}"

            elif tool_name == "webpage_reader":
                url = output.get("url") if isinstance(output, dict) else ""
                content = output.get("content", "") if isinstance(output, dict) else ""
                preview = content[:400] + "..." if len(content) > 400 else content
                obs = f"Observation [webpage_reader]: Extracted from {url}:\n{preview}"

            elif tool_name == "structured_notes":
                msg = output.get("message") if isinstance(output, dict) else str(output)
                obs = f"Observation [structured_notes]: {msg}"

            else:
                obs = f"Observation [{tool_name}]: {str(output)[:400]}"

        new_observations.append(obs)

    all_observations = list(state.get("observations", []))
    all_observations.extend(new_observations)

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    elapsed_total = time.time() - state["start_time"]
    rem_time = max(0.0, state["timeout_seconds"] - elapsed_total)
    rem_tokens = max(0, state["token_budget"] - state["total_tokens"])

    thought_summary = f"Synthesized {len(new_observations)} observation(s) from tool executions."

    await step_recorder.finish_step(
        step_id=step_id,
        run_id=run_id,
        step_number=step_num,
        node_name=node_name,
        status=StepStatus.COMPLETED,
        duration_ms=duration_ms,
        remaining_token_budget=rem_tokens,
        remaining_time_budget=rem_time,
        agent_decision="DECIDE",
        thought=thought_summary,
        metadata_json={"new_observations_count": len(new_observations)},
    )

    return {
        "step_number": step_num,
        "observations": all_observations,
        "decision": "DECIDE",
    }
