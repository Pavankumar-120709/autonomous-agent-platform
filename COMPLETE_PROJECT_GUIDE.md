# Complete Architectural & Codebase Guide: Autonomous Agent Platform

This document provides a comprehensive, end-to-end breakdown of the **Autonomous AI Agent Platform with Bounded Tool Calling & Step-Level Logging**. It covers the design philosophy, state machine mechanics, safety and reliability mechanisms, database schema, tool implementations, real-time observability, and frontend developer interface.

---

## Table of Contents

1. [Executive Overview & Philosophy](#1-executive-overview--philosophy)
2. [End-to-End System Topology](#2-end-to-end-system-topology)
3. [LangGraph State Machine Engine](#3-langgraph-state-machine-engine)
4. [Safety, Bounds & Reliability Engineering](#4-safety-bounds--reliability-engineering)
5. [The 4 Genuine Callable Tools](#5-the-4-genuine-callable-tools)
6. [Database Schema & Step-Level Persistence](#6-database-schema--step-level-persistence)
7. [Real-Time Streaming & Observability (SSE)](#7-real-time-streaming--observability-sse)
8. [REST API Specifications](#8-rest-api-specifications)
9. [Frontend Developer Dashboard (Next.js)](#9-frontend-developer-dashboard-nextjs)
10. [Automated Verification & Test Suite](#10-automated-verification--test-suite)
11. [Setup, Deployment & Environment Variables](#11-setup-deployment--environment-variables)

---

## 1. Executive Overview & Philosophy

Most AI agent demonstrations rely on simple prompt-chaining scripts or unbounded LLM loops. Such architectures suffer from four critical production flaws:
1. **Unbounded Execution:** Runaway loops that consume thousands of dollars in tokens when an LLM fails to reach a stop token.
2. **Security Vulnerabilities:** Blind tool calling allowing Server-Side Request Forgery (SSRF) into cloud metadata endpoints or arbitrary code execution via unsafe math evaluators.
3. **Observability Blind Spots:** Outputting only the final string, hiding intermediate reasoning, latency, retries, and tool failure diagnostics.
4. **Fragile Error Handling:** Crashing completely on transient 429/503 network errors or malformed JSON payloads.

This platform was built from first principles to solve these challenges:
- **Bounded Autonomy:** Execution is strictly constrained by a 12-step limit, 4 tool calls per step, token budgets, and wall-clock execution timeouts.
- **Stateful Finite State Machine:** Implemented using **LangGraph**, giving deterministic control over transitions (`PLAN → EXECUTE_TOOL → OBSERVE → DECIDE → FINALIZE`).
- **Comprehensive Step Persistence:** Every transition, decision, tool input, output, retry, and token cost is permanently recorded in **PostgreSQL**.
- **Hardened Security:** Built-in SSRF IP validation, AST-based safe math parsing, and prompt injection sandboxing.

---

## 2. End-to-End System Topology

```
+-----------------------------------------------------------------------------------+
|                                 USER / BROWSER                                    |
|              Next.js 14 Dashboard (Playground, Timeline, Analytics)                |
+------------------------------------------+----------------------------------------+
                                           | HTTP Requests & Server-Sent Events (SSE)
                                           v
+-----------------------------------------------------------------------------------+
|                               FASTAPI BACKEND                                     |
|                                                                                   |
|  +------------------------+  +--------------------------+  +--------------------+ |
|  |     API Endpoints      |  |        Event Bus         |  |   Run Controller   | |
|  | /runs, /steps, /events |  | In-Memory Queue + Async  |  | Background Workers | |
|  +-----------+------------+  +------------+-------------+  +---------+----------+ |
+--------------|----------------------------|--------------------------|------------+
               |                            |                          |
               v                            v                          v
+-----------------------------+ +---------------------------+ +---------------------+
|        DATABASE LAYER       | |      LANGGRAPH ENGINE     | |    SECURITY GATES   |
|         PostgreSQL          | |        State Graph        | |  SSRF Validator     |
|   - agent_runs              | |  START -> PLAN            | |  HTML Sanitizer     |
|   - agent_steps             | |  -> EXECUTE_TOOL          | |  AST Math Checker   |
|   - tool_executions         | |  -> OBSERVE -> DECIDE     | |  Delimiter Box      |
|   - agent_events            | |  -> FINALIZE -> END       | +----------+----------+
+-----------------------------+ +-------------+-------------+            |
                                              |                          |
                                              v                          v
+-----------------------------------------------------------------------------------+
|                                 TOOL REGISTRY                                     |
|                                                                                   |
|  1. web_search        - Live search with DuckDuckGo & HTML parser fallback        |
|  2. webpage_reader    - SSRF-safe reader with prompt-injection defense           |
|  3. calculator        - Safe AST math evaluator (no eval/exec)                    |
|  4. structured_notes  - Session-scoped key/value research memory                 |
+-----------------------------------------------------------------------------------+
```

---

## 3. LangGraph State Machine Engine

The agent execution is governed by a compiled `StateGraph` located in `backend/app/agent/graph.py`.

### State Definition (`AgentGraphState`)
The agent's state is modeled as an immutable TypedDict:
```python
class AgentGraphState(TypedDict):
    run_id: str
    objective: str
    model: str
    max_steps: int
    max_tool_calls_per_step: int
    token_budget: int
    timeout_seconds: float
    start_time: float

    step_number: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float
    consecutive_failures: int

    plan: Optional[str]
    planned_steps: List[str]
    current_thought: Optional[str]

    selected_tools: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    action_history: List[str]
    observations: List[str]

    decision: str  # "EXECUTE_TOOL", "FINALIZE", "STOP_LIMIT", "STOP_ERROR", "STOP_CANCELLED"
    decision_reason: Optional[str]

    final_response: Optional[Dict[str, Any]]
    error_message: Optional[str]
    status: str
    is_cancelled: bool
```

### The 5 Nodes and Their Transitions

1. **`PLAN` (`plan_node`):**
   - Evaluates the user objective.
   - Produces a high-level research plan and ordered sub-goals.
   - Proposes initial tool calls.
   - If limits or cancellation are active, branches directly to `FINALIZE`. Otherwise transitions to `EXECUTE_TOOL`.

2. **`EXECUTE_TOOL` (`execute_tool_node`):**
   - Takes up to 4 selected tools from state.
   - Instantiates tools scoped to the current `run_id`.
   - Executes with timeout bounds and retry jitter on transient network errors.
   - Logs tool invocations in the `tool_executions` table with execution duration in milliseconds.
   - Records action signatures for loop detection.
   - Transitions to `OBSERVE`.

3. **`OBSERVE` (`observe_node`):**
   - Synthesizes raw tool outputs into structured, factual observations.
   - Sanitizes and truncates excessive output to preserve context length.
   - Appends entries to `observations`.
   - Updates remaining wall-clock and token budgets.
   - Transitions to `DECIDE`.

4. **`DECIDE` (`decide_node`):**
   - Analyzes accumulated observations against the objective.
   - Checks safety limits (steps, tokens, wall-clock, consecutive failures, loop detection).
   - If sufficient evidence exists OR a limit is triggered: selects `FINALIZE`.
   - If more research is needed: selects up to 4 next tool actions (filtering out duplicate actions) and routes back to `EXECUTE_TOOL`.

5. **`FINALIZE` (`finalize_node`):**
   - Synthesizes all gathered evidence and structured notes into a final answer.
   - Extracts structured key findings, verified citations, and a confidence score.
   - Handles partial completions gracefully (e.g. if stopped by token budget).
   - Updates the database `AgentRun` status (`COMPLETED`, `BUDGET_EXHAUSTED`, `TIMED_OUT`, `CANCELLED`, `FAILED`).
   - Transitions to `END`.

---

## 4. Safety, Bounds & Reliability Engineering

### A. Execution Bounds
- **Step Cap:** Hard-bounded to a maximum of 12 steps per run.
- **Tool Fan-Out Cap:** Maximum 4 tool calls per step.
- **Token Budget:** Configurable per run (default: 50,000 tokens). Token consumption is tracked across every step and prompts are priced according to configured model rates:
  - `gpt-4o-mini`: \$0.15 / 1M prompt, \$0.60 / 1M completion.
  - `gpt-4o`: \$2.50 / 1M prompt, \$10.00 / 1M completion.
- **Wall-Clock Timeout:** Defaults to 180 seconds. A background timer verifies elapsed time on every node transition.

### B. Loop & Repetition Detection
Located in `backend/app/agent/limits.py`:
- Generates canonical action signatures: `tool_name:sorted_json_args`.
- **Duplicate Action Filter:** Prevents selecting actions that have already been executed twice recently without new findings.
- **Loop Circuit Breaker:** If the agent executes the exact same action 3 consecutive times without progress, execution halts immediately with `FAILED: Loop detected`.

### C. Transient Retry Policy with Backoff & Jitter
- Applied to both tool executions and LLM network requests.
- **Rule:** Only transient errors (timeouts, rate limits, 502/503/504 errors) are retried. Input validation errors (e.g. 400 Bad Request, math syntax errors) fail immediately without wasting budget.
- Backoff formula: `wait_time = (2 ** attempt) + uniform(0.1, 0.5)`. Max 2 retries.

### D. Provider Circuit Breaker
Located in `backend/app/agent/llm_gateway.py`:
- Tracks consecutive provider failures.
- If 5 consecutive requests fail, the circuit breaker trips to `OPEN` for 30 seconds.
- Rejects requests immediately during the outage rather than hanging on long timeouts.
- Transitions to `HALF_OPEN` to test recovery before resuming normal traffic.

### E. Malformed JSON Recovery
LLMs occasionally return JSON wrapped in markdown tags or with slight syntax flaws. The parser (`extract_json_from_text`) applies multi-tier recovery:
1. Standard `json.loads`.
2. Regular expression extraction of markdown code blocks (` ```json ... ``` `).
3. First outer brace matching (`{ ... }`).
4. Bounded repair retry prompt if necessary.

---

## 5. The 4 Genuine Callable Tools

All tools inherit from `BaseTool` (`backend/app/tools/base.py`) providing:
- Strict Pydantic input/output schemas.
- Execution timeout bounding.
- Error handling and structured results (`ToolResult`).
- Granular telemetry (`duration_ms`, `input_size_bytes`, `output_size_bytes`).
- Automatic OpenAI function-calling schema generation (`get_openai_tool_schema()`).

### 1. Web Search Tool (`web_search`)
- **File:** `backend/app/tools/web_search.py`
- **Capability:** Queries live web search engines using `duckduckgo_search`.
- **Fallback Mechanism:** If the search library throttles, falls back to a custom asynchronous HTTP parser querying the DuckDuckGo HTML endpoint.
- **Output:** Structured list of `SearchItem(title, url, snippet)`.

### 2. Webpage Reader Tool (`webpage_reader`)
- **File:** `backend/app/tools/webpage_reader.py`
- **SSRF Defense (`backend/app/security/ssrf.py`):**
  - Enforces URL scheme (`http`, `https`).
  - Resolves domain to IP addresses via `socket.getaddrinfo`.
  - Blocks all IPv4/IPv6 private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`).
  - Blocks link-local and cloud metadata IPs (`169.254.169.254`, `metadata.google.internal`).
  - Implements `SafeRedirectTransport` ensuring every redirect hop re-validates against SSRF rules.
- **HTML Sanitization:** Strips `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`.
- **Prompt Injection Sandboxing:** Wraps extracted text with clear delimiters instructing the agent to treat content strictly as untrusted factual input.

### 3. Safe Calculator Tool (`calculator`)
- **File:** `backend/app/tools/calculator.py`
- **Security:** Evaluates mathematical expressions using Python's `ast` (Abstract Syntax Tree). **Completely avoids `eval()` and `exec()`.**
- **Node Whitelist:** Allows only `Expression`, `BinOp`, `UnaryOp`, `Constant`, `Call`, and `Name`.
- **Allowed Operations:** `+`, `-`, `*`, `/`, `//`, `%`, `**`.
- **Allowed Functions:** `sqrt`, `cbrt`, `pow`, `abs`, `round`, `sin`, `cos`, `tan`, `log`, `log2`, `log10`, `exp`, `ceil`, `floor`, `factorial`.
- **Allowed Constants:** `pi`, `e`, `tau`.
- **DoS Guards:** Exponent limit (`<= 1000.0`), factorial limit (`<= 100`), AST node limit (`<= 200`), division-by-zero detection.

### 4. Structured Notes Tool (`structured_notes`)
- **File:** `backend/app/tools/structured_notes.py`
- **Capability:** Serves as the agent's short-term memory during a run.
- **Actions:**
  - `save`: Stores a finding with key, content, category, and source citations.
  - `get`: Retrieves a specific note by key.
  - `list`: Lists all recorded notes for the run.
  - `delete`: Removes an obsolete note.
- **Session Isolation:** Notes are strictly partitioned by `run_id`.

---

## 6. Database Schema & Step-Level Persistence

The database layer is built with **SQLAlchemy 2.0 (Async)** and migrated using **Alembic**.

```
+--------------------+        1:N         +--------------------+
|     agent_runs     | -----------------> |    agent_steps     |
| (Run metadata,     |                    | (Step number, node,|
|  bounds, totals)   |                    |  thought, tokens)  |
+--------------------+                    +--------------------+
          |                                         |
          | 1:N                                     | 1:N
          v                                         v
+--------------------+                    +--------------------+
|    agent_events    |                    |  tool_executions   |
| (Audit trail & SSE |                    | (Inputs, outputs,  |
|  event records)    |                    |  latency, retries) |
+--------------------+                    +--------------------+
```

### Table Details

1. **`agent_runs`**:
   - `id`: UUID primary key.
   - `objective`: Full task description.
   - `model`: Configured LLM identifier.
   - `status`: Enum (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMED_OUT`, `BUDGET_EXHAUSTED`).
   - Bounds: `max_steps`, `max_tool_calls_per_step`, `token_budget`, `timeout_seconds`.
   - Aggregates: `total_tokens`, `prompt_tokens`, `completion_tokens`, `estimated_cost`, `step_count`, `tool_call_count`.
   - Timestamps: `start_time`, `end_time`, `duration_seconds`, `created_at`, `updated_at`.
   - `final_response`: Structured JSON containing summary, key findings, and sources.

2. **`agent_steps`**:
   - `id`: UUID primary key.
   - `run_id`: Foreign key referencing `agent_runs.id`.
   - `step_number`: Sequential integer index.
   - `node_name`: LangGraph node name (`PLAN`, `EXECUTE_TOOL`, `OBSERVE`, `DECIDE`, `FINALIZE`).
   - `status`: Enum (`STARTED`, `RUNNING`, `COMPLETED`, `FAILED`).
   - `agent_decision`: Next planned transition.
   - `thought`: Natural language reasoning summary.
   - `duration_ms`: Step execution latency.
   - `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost`.
   - `remaining_token_budget`, `remaining_time_budget`.

3. **`tool_executions`**:
   - `id`: UUID primary key.
   - `run_id`: Foreign key referencing `agent_runs.id`.
   - `step_id`: Foreign key referencing `agent_steps.id`.
   - `tool_name`: Name of invoked tool.
   - `tool_input`: JSON argument payload.
   - `tool_output`: JSON result payload.
   - `status`: Enum (`SUCCESS`, `FAILURE`, `TIMEOUT`, `RETRY`).
   - `duration_ms`: Tool execution time in milliseconds.
   - `retry_count`: Number of retries attempted.
   - `error_message`: Full error text if failed.

4. **`agent_events`**:
   - `id`: UUID primary key.
   - `run_id`: Foreign key referencing `agent_runs.id`.
   - `event_type`: Event identifier (`step_started`, `tool_completed`, `run_completed`, etc.).
   - `payload`: Event data JSON.
   - `created_at`: Timestamp.

---

## 7. Real-Time Streaming & Observability (SSE)

Real-time tracing is handled via an asynchronous **EventBus** (`backend/app/services/event_bus.py`) and Server-Sent Events (SSE).

### Streaming Workflow
1. When a client visits `/runs/[id]` or triggers a run on the playground, the frontend opens an EventSource connection to `GET /api/runs/{run_id}/events`.
2. The endpoint subscribes an `asyncio.Queue` to the in-memory EventBus for that `run_id`.
3. As the LangGraph agent moves through nodes and executes tools, typed events are pushed to the queue:
   - `step_started`: Broadcasts step index and node name.
   - `tool_started` / `tool_completed` / `tool_failed`: Broadcasts tool name, inputs, latency, and outputs.
   - `step_completed`: Broadcasts updated token counters and costs.
   - `run_completed`: Broadcasts the final synthesized answer.
4. The SSE stream automatically emits keep-alive pings (`{"ping": true}`) every 15 seconds to prevent proxy timeouts.

---

## 8. REST API Specifications

The FastAPI application provides structured REST endpoints with OpenAPI documentation available at `/docs`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/runs` | Creates a new agent run and dispatches the background workflow. Validates bounds with Pydantic. |
| `GET` | `/api/runs` | Lists historical runs with pagination (`skip`, `limit`). |
| `GET` | `/api/runs/{id}` | Retrieves run details, aggregated metrics, final answer, steps, and tool executions. |
| `GET` | `/api/runs/{id}/steps` | Returns ordered step-by-step ledger for a run. |
| `GET` | `/api/runs/{id}/events` | SSE streaming endpoint for real-time trace updates. |
| `POST` | `/api/runs/{id}/cancel` | Triggers early cooperative cancellation. |
| `GET` | `/api/analytics` | Aggregated platform metrics: success rate, average duration, token usage, cost, and tool reliability statistics. |
| `GET` | `/api/health` | Health check verifying database connection status. |

---

## 9. Frontend Developer Dashboard (Next.js)

The frontend is built using **Next.js 14**, **TypeScript**, and **Tailwind CSS**. It follows developer-tool design principles (clean, dark theme, high information density, responsive).

### Component Structure

- **`Navbar.tsx`:** Global navigation, branding, and status indicators.
- **`Playground.tsx`:**
  - Objective input area with one-click preset buttons.
  - Collapsible bounding configuration (Model, Token Budget, Max Steps, Timeout).
  - Dispatch and cancellation controls.
- **`MetricsBar.tsx`:**
  - Visual status pill (pulsing amber for `RUNNING`, emerald for `COMPLETED`, purple for `BUDGET_EXHAUSTED`).
  - Progress bars for Step Bounds and Token Budget.
  - Live estimated cost counter in USD.
  - Wall-clock elapsed duration.
- **`ExecutionTimeline.tsx`:**
  - Vertical execution sequence of nodes (`PLAN`, `EXECUTE_TOOL`, `OBSERVE`, `DECIDE`, `FINALIZE`).
  - Reasoning summaries showing state evaluation.
  - Tool execution cards with expandable inputs/outputs JSON viewers and duration badges.
- **`FinalAnswerPanel.tsx`:**
  - Executive research summary.
  - Bulleted key verified findings.
  - Clickable external source URL pills.
  - Confidence scoring badge.
- **`RunHistoryTable.tsx`:**
  - Search and status filter (All, Completed, Running, Budget Exhausted, Failed, Cancelled).
  - Overview of past runs with quick links to deep-dive trace inspection.
- **`AnalyticsView.tsx`:**
  - Platform-level metric cards (Total runs, success rate, cost, latency).
  - Status breakdown chart.
  - Token split (Prompt vs Completion).
  - Tool reliability table showing invocations, failures, and success percentages.

---

## 10. Automated Verification & Test Suite

The backend includes 23 automated tests executed via `pytest backend/tests -v`.

```
================================== TEST MATRIX ==================================
Category             Test Name                                             Status
---------------------------------------------------------------------------------
Security (SSRF)      test_ssrf_rejects_localhost_and_loopback              PASSED
Security (SSRF)      test_ssrf_rejects_private_and_cloud_metadata          PASSED
Security (SSRF)      test_ssrf_rejects_invalid_schemes                     PASSED
Security (SSRF)      test_ssrf_accepts_valid_public_url                    PASSED
Math Safety (AST)    test_calculator_basic_operations                      PASSED
Math Safety (AST)    test_calculator_advanced_math_and_constants           PASSED
Math Safety (AST)    test_calculator_blocks_arbitrary_code_execution       PASSED
Math Safety (AST)    test_calculator_handles_zero_division_and_overflow    PASSED
Tool Lifecycle       test_structured_notes_lifecycle                       PASSED
Sanitizer            test_html_sanitizer_and_injection_wrapper             PASSED
Tool Validation      test_web_search_validation                            PASSED
Registry             test_tool_registry                                    PASSED
Reliability          test_tool_execution_timeout                           PASSED
Reliability          test_circuit_breaker_behavior                         PASSED
Reliability          test_malformed_llm_json_recovery                      PASSED
Agent Bounds         test_step_budget_limit                                PASSED
Agent Bounds         test_token_budget_limit                               PASSED
Agent Bounds         test_loop_detection_limit                             PASSED
Agent Bounds         test_repeated_action_detection                       PASSED
REST API             test_health_endpoint                                  PASSED
REST API             test_create_and_list_runs                             PASSED
REST API             test_analytics_endpoint                               PASSED
End-to-End Agent     test_end_to_end_agent_execution                       PASSED
=================================================================================
Total: 23 passed, 0 failed in 13.52s
```

---

## 11. Setup, Deployment & Environment Variables

### Environment Variables (`.env`)

```ini
# Database Connection (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_platform
DATABASE_SYNC_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/agent_platform

# OpenAI Configuration (Optional: fallback deterministic engine runs if omitted)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=
DEFAULT_MODEL=gpt-4o-mini

# Execution Constraints
MAX_STEPS_LIMIT=12
MAX_TOOL_CALLS_PER_STEP=4
DEFAULT_TOKEN_BUDGET=50000
DEFAULT_WALL_CLOCK_TIMEOUT=180.0
MAX_CONSECUTIVE_FAILURES=3
MAX_TOOL_RETRIES=2

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Running with Docker Compose
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

### Running Locally (Without Docker)
```bash
# 1. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 2. Frontend
cd frontend
npm install
npm run dev
```

---

## Conclusion

This platform demonstrates robust agent engineering:
- **Never loops indefinitely:** Strictly bounded by step budgets, token budgets, and loop detection.
- **Never leaks or breaks security:** SSRF is blocked at the network resolution layer, and code execution is blocked at the AST parsing layer.
- **Never hides failures:** Every step, reasoning path, tool invocation, and retry is permanently recorded in PostgreSQL and viewable in real-time.
