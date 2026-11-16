"use client";

import React, { useEffect, useRef, useState } from "react";
import Playground from "@/components/Playground";
import MetricsBar from "@/components/MetricsBar";
import ExecutionTimeline from "@/components/ExecutionTimeline";
import FinalAnswerPanel from "@/components/FinalAnswerPanel";
import RunHistoryTable from "@/components/RunHistoryTable";
import {
  cancelRun,
  createRun,
  createRunEventSource,
  fetchRunById,
  fetchRuns,
} from "@/lib/api";
import { RunCreateRequest, RunDetail, RunSummary, StepResponse } from "@/lib/types";

export default function DashboardPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRunDetail, setActiveRunDetail] = useState<RunDetail | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Load runs on mount
  const loadRuns = async () => {
    try {
      const data = await fetchRuns(0, 30);
      setRuns(data);
      if (!activeRunId && data.length > 0) {
        // Load most recent run details by default
        loadRunDetail(data[0].id);
      }
    } catch (e) {
      console.error("Failed to load runs:", e);
    }
  };

  const loadRunDetail = async (id: string) => {
    try {
      const detail = await fetchRunById(id);
      setActiveRunId(id);
      setActiveRunDetail(detail);
      setIsRunning(detail.status === "RUNNING");
    } catch (e) {
      console.error(`Failed to load run detail ${id}:`, e);
    }
  };

  useEffect(() => {
    loadRuns();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Connect to SSE for an active run
  const connectSSE = (runId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const sse = createRunEventSource(runId);
    eventSourceRef.current = sse;

    sse.addEventListener("step_started", (e: MessageEvent) => {
      loadRunDetail(runId);
    });

    sse.addEventListener("step_completed", (e: MessageEvent) => {
      loadRunDetail(runId);
    });

    sse.addEventListener("tool_completed", (e: MessageEvent) => {
      loadRunDetail(runId);
    });

    sse.addEventListener("tool_failed", (e: MessageEvent) => {
      loadRunDetail(runId);
    });

    sse.addEventListener("run_completed", (e: MessageEvent) => {
      setIsRunning(false);
      loadRunDetail(runId);
      loadRuns();
      sse.close();
    });

    sse.addEventListener("run_ended", (e: MessageEvent) => {
      setIsRunning(false);
      loadRunDetail(runId);
      loadRuns();
      sse.close();
    });

    sse.addEventListener("run_failed", (e: MessageEvent) => {
      setIsRunning(false);
      loadRunDetail(runId);
      loadRuns();
      sse.close();
    });

    sse.addEventListener("run_cancelled", (e: MessageEvent) => {
      setIsRunning(false);
      loadRunDetail(runId);
      loadRuns();
      sse.close();
    });

    sse.onerror = () => {
      // Re-fetch in case of network disconnect
      loadRunDetail(runId);
    };
  };

  const handleStartRun = async (config: RunCreateRequest) => {
    const newRun = await createRun(config);
    setActiveRunId(newRun.id);
    setIsRunning(true);
    await loadRunDetail(newRun.id);
    await loadRuns();
    connectSSE(newRun.id);
  };

  const handleCancelRun = async () => {
    if (!activeRunId) return;
    try {
      await cancelRun(activeRunId);
      await loadRunDetail(activeRunId);
    } catch (e) {
      console.error("Cancel error:", e);
    }
  };

  return (
    <div className="space-y-8">
      {/* 1. Playground */}
      <section>
        <Playground onStartRun={handleStartRun} onCancelRun={handleCancelRun} isRunning={isRunning} />
      </section>

      {/* 2. Live Execution & Trace View */}
      {activeRunDetail && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider font-mono text-muted-foreground">
              Active Run Inspection: <span className="text-foreground">{activeRunDetail.id}</span>
            </h3>
            <span className="text-xs text-muted-foreground font-mono">
              Model: {activeRunDetail.model}
            </span>
          </div>

          {/* Metrics Header */}
          <MetricsBar
            status={activeRunDetail.status}
            currentStep={activeRunDetail.step_count}
            maxSteps={activeRunDetail.max_steps}
            totalTokens={activeRunDetail.total_tokens}
            tokenBudget={activeRunDetail.token_budget}
            cost={activeRunDetail.estimated_cost}
            durationSeconds={activeRunDetail.duration_seconds}
            toolCallCount={activeRunDetail.tool_call_count}
          />

          {/* Final Answer (if available) */}
          {activeRunDetail.final_response && (
            <FinalAnswerPanel
              finalResponse={activeRunDetail.final_response}
              status={activeRunDetail.status}
              totalTokens={activeRunDetail.total_tokens}
              cost={activeRunDetail.estimated_cost}
              stepCount={activeRunDetail.step_count}
            />
          )}

          {/* Step Timeline */}
          <div>
            <div className="text-xs font-mono uppercase text-muted-foreground font-semibold mb-3">
              Step Execution Timeline & Tool Calls
            </div>
            <ExecutionTimeline
              steps={activeRunDetail.steps}
              activeStep={activeRunDetail.step_count}
              isRunning={isRunning}
            />
          </div>
        </section>
      )}

      {/* 3. History Section */}
      <section id="history" className="pt-2">
        <RunHistoryTable
          runs={runs}
          selectedRunId={activeRunId || undefined}
          onSelectRun={(id) => {
            loadRunDetail(id);
            if (activeRunDetail?.status === "RUNNING") {
              connectSSE(id);
            }
          }}
        />
      </section>
    </div>
  );
}
