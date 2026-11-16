"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCw, StopCircle } from "lucide-react";
import MetricsBar from "@/components/MetricsBar";
import ExecutionTimeline from "@/components/ExecutionTimeline";
import FinalAnswerPanel from "@/components/FinalAnswerPanel";
import { cancelRun, createRunEventSource, fetchRunById } from "@/lib/api";
import { RunDetail } from "@/lib/types";

export default function RunTracePage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await fetchRunById(runId);
      setRun(data);
      if (data.status === "RUNNING") {
        connectSSE();
      }
    } catch (e: any) {
      setError(e.message || "Failed to load run trace.");
    } finally {
      setLoading(false);
    }
  };

  const connectSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const sse = createRunEventSource(runId);
    eventSourceRef.current = sse;

    const refresh = async () => {
      try {
        const updated = await fetchRunById(runId);
        setRun(updated);
        if (updated.status !== "RUNNING") {
          sse.close();
        }
      } catch (err) {
        console.error(err);
      }
    };

    sse.addEventListener("step_started", refresh);
    sse.addEventListener("step_completed", refresh);
    sse.addEventListener("tool_completed", refresh);
    sse.addEventListener("tool_failed", refresh);
    sse.addEventListener("run_completed", refresh);
    sse.addEventListener("run_ended", refresh);
    sse.addEventListener("run_failed", refresh);
    sse.addEventListener("run_cancelled", refresh);

    sse.onerror = () => {
      refresh();
    };
  };

  useEffect(() => {
    if (runId) {
      loadData();
    }
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [runId]);

  const handleCancel = async () => {
    if (!runId) return;
    try {
      await cancelRun(runId);
      await loadData();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading && !run) {
    return (
      <div className="py-20 text-center">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary mb-2" />
        <p className="text-xs text-muted-foreground font-mono">Loading persisted execution trace...</p>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="py-16 text-center space-y-3">
        <p className="text-sm text-rose-400 font-semibold">{error || "Run not found."}</p>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-mono"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Return to Dashboard
        </Link>
      </div>
    );
  }

  const isRunning = run.status === "RUNNING";

  return (
    <div className="space-y-6">
      {/* Top back navigation */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-mono transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        <div className="flex items-center gap-3">
          {isRunning && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20"
            >
              <StopCircle className="w-4 h-4" /> Cancel Run
            </button>
          )}

          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono bg-secondary text-foreground hover:bg-secondary/70 border border-border"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      {/* Run Header */}
      <div className="bg-card border border-border rounded-lg p-5">
        <div className="text-xs font-mono text-muted-foreground uppercase tracking-wider mb-1">
          Objective
        </div>
        <h2 className="text-base font-bold text-foreground leading-relaxed">{run.objective}</h2>
        <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground font-mono flex-wrap">
          <span>Run ID: {run.id}</span>
          <span>&bull;</span>
          <span>Model: {run.model}</span>
          <span>&bull;</span>
          <span>Budget: {run.token_budget} tokens</span>
          <span>&bull;</span>
          <span>Timeout: {run.timeout_seconds}s</span>
        </div>
      </div>

      {/* Metrics */}
      <MetricsBar
        status={run.status}
        currentStep={run.step_count}
        maxSteps={run.max_steps}
        totalTokens={run.total_tokens}
        tokenBudget={run.token_budget}
        cost={run.estimated_cost}
        durationSeconds={run.duration_seconds}
        toolCallCount={run.tool_call_count}
      />

      {/* Final Answer (if ready) */}
      {run.final_response && (
        <FinalAnswerPanel
          finalResponse={run.final_response}
          status={run.status}
          totalTokens={run.total_tokens}
          cost={run.estimated_cost}
          stepCount={run.step_count}
        />
      )}

      {/* Timeline */}
      <div>
        <div className="text-xs font-mono uppercase text-muted-foreground font-semibold mb-3">
          Step-Level Execution Trace
        </div>
        <ExecutionTimeline steps={run.steps} activeStep={run.step_count} isRunning={isRunning} />
      </div>
    </div>
  );
}
