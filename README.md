# Autonomous Agent Platform with Bounded Tool Calling & Step-Level Logging

A production-grade Autonomous Research Agent platform engineered end-to-end with **LangGraph**, **FastAPI**, **PostgreSQL**, **Alembic**, and **Next.js**.

The agent accepts an objective, creates a structured research plan, calls bounded tools, observes outputs, reasons iteratively, and synthesizes a verified final answer. Every execution step, tool call, token count, cost, and decision is persisted to PostgreSQL and streamed live via Server-Sent Events (SSE).

---

## Key Features

1. **Autonomous LangGraph State Machine:**
   `START → PLAN → EXECUTE TOOL → OBSERVE → DECIDE → (EXECUTE TOOL / FINALIZE) → END`
   - Real state transitions with dynamic tool dispatching.
   - Loop and repeated-action detection.
   - Max 12 steps per run, max 4 tool calls per step.
   - Token budget bounding and wall-clock execution timeouts.

2. **Genuine Callable Tools:**
   - **Web Search Tool (`web_search`):** Real-time web discovery with DuckDuckGo.
   - **Webpage Reader Tool (`webpage_reader`):** Content extraction with strict SSRF defense (blocking private, loopback, and cloud metadata IPs) and prompt-injection defense delimiters.
   - **Safe Calculator Tool (`calculator`):** Python AST-based mathematical evaluator (no `eval()` or `exec()`), safe operators, functions, and overflow protection.
   - **Structured Notes Tool (`structured_notes`):** Session-isolated key-value research findings store with tags and citations.

3. **Reliability & Resilience:**
   - Exponential backoff with jitter on transient failures.
   - Circuit breaker pattern for provider outages.
   - Malformed LLM JSON recovery and bounded repair.
   - Cooperative cancellation and partial research synthesis on budget exhaustion.

4. **Step-Level Observability:**
   - PostgreSQL persistence of `AgentRun`, `AgentStep`, `ToolExecution`, and `AgentEvent`.
   - Real-time SSE streaming for live frontend tracing.
   - Token consumption, cost estimation, and tool reliability metrics.

5. **Developer Dashboard (Next.js & Tailwind CSS):**
   - **Playground:** Enter objectives, configure bounds, dispatch runs.
   - **Live Execution Timeline:** Visual node flow, reasoning summaries, expandable tool inputs/outputs, retries, and errors.
   - **Run History:** Filterable historical runs table with deep-dive trace inspection.
   - **Platform Analytics:** Total runs, success rate, cost, latency, and tool reliability statistics.

---

## Architecture Diagram

```
                 +-----------------------+
                 |       Frontend        |
                 | Next.js / Tailwind UI |
                 +-----------+-----------+
                             | REST & SSE (/events)
                             v
                 +-----------------------+
                 |    FastAPI Backend    |
                 +-----------+-----------+
                             |
             +---------------+---------------+
             |                               |
             v                               v
    +-----------------+             +-----------------+
    |    LangGraph    |             |   PostgreSQL    |
    |  State Machine  | <---------> |  Persistence    |
    +--------+--------+             +-----------------+
             |
             v
    +-------------------------------------------------+
    |                  Agent Tools                    |
    |  - web_search        - webpage_reader (SSRF)    |
    |  - calculator (AST)  - structured_notes         |
    +-------------------------------------------------+
```

---

## Quick Start with Docker Compose

To launch the complete platform (PostgreSQL + FastAPI Backend + Next.js Frontend) in one command:

```bash
docker compose up --build
```

- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database:** PostgreSQL on `localhost:5432`

---

## Manual Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL (or SQLite for automated local testing)

### 2. Backend Setup
```bash
# Navigate to backend and create virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) in your browser.

---

## Running Automated Tests

Run the full pytest suite covering SSRF defense, AST calculator safety, tool reliability, state machine limits, API endpoints, and end-to-end agent execution:

```bash
# In backend directory or workspace root
$env:PYTHONPATH="backend"
pytest backend/tests -v
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/runs` | Creates and dispatches an autonomous agent run |
| `GET` | `/api/runs` | Lists historical runs with pagination |
| `GET` | `/api/runs/{id}` | Retrieves full run details, steps, and tool executions |
| `GET` | `/api/runs/{id}/steps` | Retrieves execution step timeline |
| `GET` | `/api/runs/{id}/events` | SSE live stream of agent steps and tool events |
| `POST` | `/api/runs/{id}/cancel` | Cooperatively cancels an active run |
| `GET` | `/api/analytics` | Aggregated platform metrics and tool performance |
| `GET` | `/api/health` | Health check endpoint |
