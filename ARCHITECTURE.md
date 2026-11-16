# Comprehensive Architecture Specification

## 1. System Topology & Component Interactions

```mermaid
flowchart TB
    subgraph ClientLayer ["Client Presentation Layer (Next.js 14)"]
        UI["Developer Dashboard & Playground"]
        Timeline["Live Execution Timeline"]
        Panel["Final Answer & Citations Panel"]
        Analytics["Platform Observability & Metrics"]
        EventSource["EventSource Client (/api/runs/:id/events)"]
    end

    subgraph APILayer ["API & Ingestion Layer (FastAPI)"]
        Router["FastAPI REST Router"]
        RunController["Run Controller & Background Worker"]
        EventBus["In-Memory Event Bus & SSE Broadcaster"]
        Health["Health & Diagnostic Service"]
    end

    subgraph SecurityLayer ["Security & Sanitization Gates"]
        SSRF["SSRF Gate (DNS Resolution & CIDR Filter)"]
        AST["Safe AST Evaluator (No eval/exec)"]
        Sanitizer["HTML Cleaner & Prompt-Injection Wrapper"]
    end

    subgraph EngineLayer ["Agent Orchestration Layer (LangGraph)"]
        StateGraph["LangGraph State Machine (TypedDict State)"]
        PlannerNode["PLAN Node"]
        ExecutorNode["EXECUTE_TOOL Node"]
        ObserverNode["OBSERVE Node"]
        DeciderNode["DECIDE Node"]
        FinalizerNode["FINALIZE Node"]
        LimitsEngine["Bounds & Loop Detection Engine"]
        LLMGateway["LLM Gateway (Circuit Breaker & Retries)"]
    end

    subgraph ToolRegistryLayer ["Callable Tool Registry"]
        T1["web_search (DuckDuckGo + Fallback)"]
        T2["webpage_reader (Safe HTTP Transport)"]
        T3["calculator (AST Math Evaluator)"]
        T4["structured_notes (Session-Isolated Memory)"]
    end

    subgraph StorageLayer ["Persistence Layer (PostgreSQL 16)"]
        DB[(PostgreSQL Database)]
        T_Runs["agent_runs"]
        T_Steps["agent_steps"]
        T_Tools["tool_executions"]
        T_Events["agent_events"]
    end

    UI -->|"POST /api/runs"| Router
    UI -->|"GET /api/runs"| Router
    EventSource -->|"GET /api/runs/:id/events (SSE)"| EventBus
    Router --> RunController
    RunController -->|"Dispatch async task"| StateGraph
    RunController -->|"Publish events"| EventBus

    StateGraph --> PlannerNode
    PlannerNode --> LimitsEngine
    PlannerNode --> LLMGateway
    PlannerNode --> ExecutorNode
    ExecutorNode -->|"Validate args"| SecurityLayer
    SecurityLayer --> ToolRegistryLayer
    ToolRegistryLayer --> ObserverNode
    ObserverNode --> DeciderNode
    DeciderNode -->|"Loop or Finalize"| LimitsEngine
    DeciderNode --> LLMGateway
    DeciderNode -->|"Next action"| ExecutorNode
    DeciderNode -->|"Complete"| FinalizerNode
    FinalizerNode -->|"Persist final answer"| StorageLayer

    PlannerNode -.->|"Record step & tokens"| StorageLayer
    ExecutorNode -.->|"Record tool call audit"| StorageLayer
    ObserverNode -.->|"Record observation"| StorageLayer
    DeciderNode -.->|"Record decision"| StorageLayer
    FinalizerNode -.->|"Record status"| StorageLayer

    StorageLayer --> DB
    DB --- T_Runs
    DB --- T_Steps
    DB --- T_Tools
    DB --- T_Events
```

---

## 2. LangGraph State Machine Lifecycle

```mermaid
stateDiagram-v2
    [*] --> START
    START --> PLAN: Initialize run state & bounds
    
    state PLAN {
        [*] --> EvaluateObjective
        EvaluateObjective --> CheckBounds1: Step/Token/Timeout check
        CheckBounds1 --> FormulateSubGoals: Bounds OK
        CheckBounds1 --> BranchToFinalize1: Bounds Exceeded
        FormulateSubGoals --> SelectInitialTools
        SelectInitialTools --> [*]
    }

    PLAN --> EXECUTE_TOOL: Valid initial action
    PLAN --> FINALIZE: Limit triggered early

    state EXECUTE_TOOL {
        [*] --> ValidateArgsSchema
        ValidateArgsSchema --> CheckSSRF_AST
        CheckSSRF_AST --> DispatchAsyncTools: Max 4 tool calls
        DispatchAsyncTools --> RetryWithJitter: On transient network error
        RetryWithJitter --> RecordToolAudit
        RecordToolAudit --> UpdateActionHistory: Track signature for loop detection
        UpdateActionHistory --> [*]
    }

    EXECUTE_TOOL --> OBSERVE: Tool results ready
    EXECUTE_TOOL --> FINALIZE: Critical execution fault

    state OBSERVE {
        [*] --> ExtractRawData
        ExtractRawData --> SanitizeOutput
        SanitizeOutput --> DistillObservations
        DistillObservations --> UpdateRemainingBudgets
        UpdateRemainingBudgets --> [*]
    }

    OBSERVE --> DECIDE: Observations distilled

    state DECIDE {
        [*] --> CheckSafetyBounds: Max 12 steps / Budget / 3x Loop check
        CheckSafetyBounds --> RouteFinalize: Goal met OR limits reached
        CheckSafetyBounds --> CheckActionRepetition: Goal incomplete
        CheckActionRepetition --> FilterDuplicates
        FilterDuplicates --> SelectNextTools: Propose novel actions
        SelectNextTools --> [*]
    }

    DECIDE --> EXECUTE_TOOL: Next tools selected (Loop)
    DECIDE --> FINALIZE: Research completed or bounds reached

    state FINALIZE {
        [*] --> AggregateObservationsAndNotes
        AggregateObservationsAndNotes --> SynthesizeFinalAnswer
        SynthesizeFinalAnswer --> ExtractKeyFindings
        ExtractKeyFindings --> CompileSourceCitations
        CompileSourceCitations --> PersistRunStatus
        PersistRunStatus --> [*]
    }

    FINALIZE --> END
    END --> [*]
```

---

## 3. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant EBus as EventBus (SSE)
    participant Graph as LangGraph Engine
    participant Security as Security Gate
    participant Tools as Tool Registry
    participant LLM as OpenAI Gateway

    User->>API: POST /api/runs (objective, model, bounds)
    API->>DB: INSERT INTO agent_runs (status=PENDING)
    API->>API: Dispatch background asyncio task
    API-->>User: HTTP 201 Created (RunSummary)

    User->>API: GET /api/runs/{id}/events
    API->>EBus: Subscribe queue for run_id
    API-->>User: SSE Stream Connected (run_state)

    API->>Graph: Execute workflow(initial_state)
    Graph->>DB: UPDATE agent_runs (status=RUNNING)
    EBus-->>User: event: run_started

    rect rgb(25, 30, 45)
        Note over Graph,LLM: Step 1: PLAN Node
        Graph->>DB: INSERT INTO agent_steps (step 1, node=PLAN)
        EBus-->>User: event: step_started (PLAN)
        Graph->>LLM: Formulate structured research plan
        LLM-->>Graph: Plan + Planned steps + Initial tool
        Graph->>DB: UPDATE agent_steps (COMPLETED, thought, tokens, cost)
        EBus-->>User: event: step_completed
    end

    rect rgb(35, 30, 25)
        Note over Graph,Tools: Step 2: EXECUTE_TOOL Node
        Graph->>DB: INSERT INTO agent_steps (step 2, node=EXECUTE_TOOL)
        EBus-->>User: event: step_started (EXECUTE_TOOL)
        Graph->>Security: Validate target URL / AST math expression
        Security-->>Graph: Security clearance OK
        Graph->>Tools: Invoke web_search(query)
        Tools-->>Graph: Search results (URLs + Snippets)
        Graph->>DB: INSERT INTO tool_executions (tool_name, input, output, duration_ms)
        EBus-->>User: event: tool_completed
        Graph->>DB: UPDATE agent_steps (COMPLETED, duration_ms)
    end

    rect rgb(25, 35, 35)
        Note over Graph,DB: Step 3: OBSERVE Node
        Graph->>DB: INSERT INTO agent_steps (step 3, node=OBSERVE)
        EBus-->>User: event: step_started (OBSERVE)
        Graph->>Graph: Sanitize tool outputs & summarize findings
        Graph->>DB: UPDATE agent_steps (COMPLETED, observations)
    end

    rect rgb(35, 25, 45)
        Note over Graph,LLM: Step 4: DECIDE Node
        Graph->>DB: INSERT INTO agent_steps (step 4, node=DECIDE)
        EBus-->>User: event: step_started (DECIDE)
        Graph->>Graph: Check bounds (Step < 12, Budget OK, No loops)
        Graph->>LLM: Evaluate evidence sufficiency
        LLM-->>Graph: Decision: FINALIZE
        Graph->>DB: UPDATE agent_steps (COMPLETED, decision=FINALIZE)
    end

    rect rgb(25, 45, 30)
        Note over Graph,DB: Step 5: FINALIZE Node
        Graph->>DB: INSERT INTO agent_steps (step 5, node=FINALIZE)
        Graph->>LLM: Synthesize final answer, key findings & sources
        LLM-->>Graph: Structured final payload
        Graph->>DB: UPDATE agent_runs (status=COMPLETED, final_response, duration, total_cost)
        Graph->>DB: UPDATE agent_steps (COMPLETED)
        EBus-->>User: event: run_completed (final_response)
    end

    User->>User: Render FinalAnswerPanel & complete timeline
```

---

## 4. Database Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    agent_runs ||--o{ agent_steps : "contains"
    agent_runs ||--o{ tool_executions : "executes"
    agent_runs ||--o{ agent_events : "emits"
    agent_steps ||--o{ tool_executions : "groups"

    agent_runs {
        string id PK "UUID"
        text objective "User objective"
        string model "gpt-4o-mini / gpt-4o"
        string status "COMPLETED, FAILED, TIMED_OUT..."
        int max_steps "Default 12"
        int max_tool_calls_per_step "Default 4"
        int token_budget "Default 50000"
        float timeout_seconds "Default 180s"
        int total_tokens "Cumulative token consumption"
        int prompt_tokens "Prompt token usage"
        int completion_tokens "Output token usage"
        float estimated_cost "Estimated USD cost"
        int step_count "Executed steps"
        int tool_call_count "Executed tool calls"
        datetime start_time "Timestamp"
        datetime end_time "Timestamp"
        float duration_seconds "Wall-clock duration"
        json final_response "Structured final summary & sources"
        text error_message "Failure explanation if any"
        int is_cancelled "Cancellation flag"
        datetime created_at "Indexed"
        datetime updated_at "Timestamp"
    }

    agent_steps {
        string id PK "UUID"
        string run_id FK "References agent_runs.id"
        int step_number "1-indexed sequence"
        string node_name "PLAN, EXECUTE_TOOL, OBSERVE, DECIDE, FINALIZE"
        string status "STARTED, RUNNING, COMPLETED, FAILED"
        text agent_decision "Next transition action"
        text thought "State reasoning summary"
        json selected_tools "List of planned tool calls"
        float duration_ms "Step latency"
        int prompt_tokens "Step prompt tokens"
        int completion_tokens "Step completion tokens"
        int total_tokens "Step total tokens"
        float estimated_cost "Step USD cost"
        int remaining_token_budget "Tokens remaining"
        float remaining_time_budget "Seconds remaining"
        json metadata_json "Additional execution data"
        text error_details "Error text if failed"
        datetime created_at "Indexed"
    }

    tool_executions {
        string id PK "UUID"
        string run_id FK "References agent_runs.id"
        string step_id FK "References agent_steps.id"
        string tool_name "web_search, calculator, etc."
        json tool_input "Validated argument payload"
        json tool_output "Structured tool result"
        string status "SUCCESS, FAILURE, TIMEOUT, RETRY"
        float duration_ms "Execution latency"
        int retry_count "Retries attempted"
        text error_message "Failure details"
        json metadata_json "Telemetry metadata"
        datetime created_at "Indexed"
    }

    agent_events {
        string id PK "UUID"
        string run_id FK "References agent_runs.id"
        string event_type "step_started, tool_completed, etc."
        int step_number "Step number reference"
        json payload "Event payload for SSE"
        datetime created_at "Indexed"
    }
```
