import asyncio
import pytest
from app.tools.base import BaseTool
from pydantic import BaseModel
from app.agent.llm_gateway import CircuitBreaker, extract_json_from_text


class SlowInput(BaseModel):
    delay: float


class SlowTool(BaseTool):
    name = "slow_tool"
    description = "Test tool that delays."
    args_schema = SlowInput
    timeout_seconds = 0.2

    async def _run(self, delay: float):
        await asyncio.sleep(delay)
        return {"status": "finished"}


@pytest.mark.asyncio
async def test_tool_execution_timeout():
    tool = SlowTool()
    res = await tool.execute(delay=1.0)
    assert res.success is False
    assert "timed out after 0.2 seconds" in res.error
    assert res.metadata.get("timeout_occurred") is True


def test_circuit_breaker_behavior():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    assert cb.allow_request() is True

    # Record 2 failures -> still closed
    cb.record_failure()
    cb.record_failure()
    assert cb.allow_request() is True
    assert cb.state == "CLOSED"

    # 3rd failure -> trips to OPEN
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False

    # After recovery timeout -> HALF_OPEN
    import time
    time.sleep(0.15)
    assert cb.allow_request() is True
    assert cb.state == "HALF_OPEN"

    # Success restores to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0


def test_malformed_llm_json_recovery():
    # 1. Markdown code block
    raw1 = "Here is the response:\n```json\n{\"decision\": \"FINALIZE\", \"thought\": \"ready\"}\n```"
    p1 = extract_json_from_text(raw1)
    assert p1 == {"decision": "FINALIZE", "thought": "ready"}

    # 2. Text with JSON embedded
    raw2 = "Thought: analyzing data... {\"plan\": \"test\", \"steps\": [1, 2]}"
    p2 = extract_json_from_text(raw2)
    assert p2 == {"plan": "test", "steps": [1, 2]}

    # 3. Direct clean JSON
    raw3 = '{"summary": "All good"}'
    p3 = extract_json_from_text(raw3)
    assert p3 == {"summary": "All good"}
