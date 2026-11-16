import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_create_and_list_runs(client: AsyncClient):
    # 1. Create run
    payload = {
        "objective": "Investigate latest advancements in multimodal AI architectures.",
        "model": "gpt-4o-mini",
        "max_steps": 8,
        "max_tool_calls_per_step": 3,
        "token_budget": 40000,
        "timeout_seconds": 120.0,
    }
    create_resp = await client.post("/api/runs", json=payload)
    assert create_resp.status_code == 201
    run_data = create_resp.json()
    run_id = run_data["id"]
    assert run_data["objective"] == payload["objective"]
    assert run_data["max_steps"] == 8

    # 2. List runs
    list_resp = await client.get("/api/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1
    assert any(r["id"] == run_id for r in runs)

    # 3. Get run by ID
    get_resp = await client.get(f"/api/runs/{run_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == run_id
    assert "steps" in detail

    # 4. Cancel run
    cancel_resp = await client.post(f"/api/runs/{run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert "cancellation_requested" in cancel_resp.json()["status"] or "already_terminated" in cancel_resp.json()["status"]


@pytest.mark.asyncio
async def test_analytics_endpoint(client: AsyncClient):
    resp = await client.get("/api/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_runs" in data
    assert "success_rate_percent" in data
    assert "tool_usage_counts" in data
