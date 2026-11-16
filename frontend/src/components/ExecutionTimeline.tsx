"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Terminal,
  Cpu,
  Search,
  BookOpen,
  Calculator,
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  Coins,
  ArrowRight,
} from "lucide-react";
import { StepResponse, ToolExecutionResponse } from "@/lib/types";
import { formatCost, formatDuration } from "@/lib/utils";

interface ExecutionTimelineProps {
  steps: StepResponse[];
  activeStep?: number;
  isRunning?: boolean;
}

export default function ExecutionTimeline({ steps, activeStep, isRunning }: ExecutionTimelineProps) {
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});

  const toggleTool = (id: string) => {
    setExpandedTools((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getToolIcon = (name: string) => {
    switch (name) {
      case "web_search":
        return <Search className="w-3.5 h-3.5 text-sky-400" />;
      case "webpage_reader":
        return <BookOpen className="w-3.5 h-3.5 text-amber-400" />;
      case "calculator":
        return <Calculator className="w-3.5 h-3.5 text-purple-400" />;
      case "structured_notes":
        return <FileText className="w-3.5 h-3.5 text-emerald-400" />;
      default:
        return <Terminal className="w-3.5 h-3.5 text-primary" />;
    }
  };

  const getNodeBadge = (nodeName: string) => {
    switch (nodeName) {
      case "PLAN":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "EXECUTE_TOOL":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "OBSERVE":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "DECIDE":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "FINALIZE":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      default:
        return "bg-secondary text-foreground border-border";
    }
  };

  if (steps.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-10 text-center">
        <Cpu className="w-8 h-8 text-muted-foreground mx-auto mb-3 animate-pulse" />
        <h4 className="text-sm font-semibold text-foreground">Waiting for execution to commence...</h4>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
          Agent decisions, tool invocations, observations, and telemetry will stream live into this timeline.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {steps.map((step, idx) => {
        const isCurrent = activeStep === step.step_number && isRunning;
        return (
          <div
            key={step.id || idx}
            className={`bg-card border rounded-lg transition-all ${
              isCurrent ? "border-primary ring-1 ring-primary/40 shadow-lg shadow-primary/5" : "border-border"
            }`}
          >
            {/* Header */}
            <div className="p-3.5 border-b border-border/60 flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-secondary text-foreground border border-border">
                  Step {step.step_number}
                </span>
                <span
                  className={`text-xs font-mono font-medium px-2 py-0.5 rounded border uppercase ${getNodeBadge(
                    step.node_name
                  )}`}
                >
                  {step.node_name}
                </span>

                {step.agent_decision && (
                  <span className="text-xs text-muted-foreground flex items-center gap-1 font-mono">
                    <ArrowRight className="w-3 h-3" /> {step.agent_decision}
                  </span>
                )}
              </div>

              {/* Telemetry info */}
              <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                {step.duration_ms > 0 && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-muted-foreground/70" />
                    {step.duration_ms.toFixed(1)}ms
                  </span>
                )}
                {step.total_tokens > 0 && (
                  <span className="flex items-center gap-1">
                    <Coins className="w-3 h-3 text-muted-foreground/70" />
                    {step.total_tokens} tok ({formatCost(step.estimated_cost)})
                  </span>
                )}
              </div>
            </div>

            {/* Step Body */}
            <div className="p-4 space-y-3">
              {/* Reasoning Summary */}
              {step.thought && (
                <div className="bg-secondary/40 border border-border/50 rounded-md p-3 text-xs leading-relaxed text-foreground/90">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider mb-1 font-semibold">
                    Reasoning & State Evaluation
                  </div>
                  <p className="whitespace-pre-wrap">{step.thought}</p>
                </div>
              )}

              {/* Error details if any */}
              {step.error_details && (
                <div className="bg-rose-500/10 border border-rose-500/30 rounded-md p-3 text-xs text-rose-300 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">Execution Notice: </span>
                    {step.error_details}
                  </div>
                </div>
              )}

              {/* Tool Executions list */}
              {step.tool_executions && step.tool_executions.length > 0 && (
                <div className="space-y-2 pt-1">
                  <div className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider font-semibold">
                    Tool Calls ({step.tool_executions.length})
                  </div>
                  {step.tool_executions.map((tool) => {
                    const isExpanded = !!expandedTools[tool.id];
                    return (
                      <div
                        key={tool.id}
                        className="border border-border/80 rounded-md bg-secondary/20 overflow-hidden text-xs"
                      >
                        {/* Tool Header */}
                        <button
                          onClick={() => toggleTool(tool.id)}
                          className="w-full px-3 py-2 flex items-center justify-between hover:bg-secondary/40 transition-colors text-left"
                        >
                          <div className="flex items-center gap-2">
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                            )}
                            <div className="flex items-center gap-1.5 font-mono font-medium text-foreground">
                              {getToolIcon(tool.tool_name)}
                              <span>{tool.tool_name}</span>
                            </div>

                            {tool.retry_count > 0 && (
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
                                {tool.retry_count} {tool.retry_count === 1 ? "retry" : "retries"}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-2.5 font-mono">
                            <span className="text-muted-foreground text-[11px]">{tool.duration_ms.toFixed(1)}ms</span>
                            {tool.status === "SUCCESS" ? (
                              <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                                <CheckCircle2 className="w-3.5 h-3.5" /> SUCCESS
                              </span>
                            ) : (
                              <span className="text-rose-400 flex items-center gap-1 text-[11px]">
                                <AlertCircle className="w-3.5 h-3.5" /> {tool.status}
                              </span>
                            )}
                          </div>
                        </button>

                        {/* Tool Expanded View */}
                        {isExpanded && (
                          <div className="p-3 border-t border-border/60 bg-black/30 space-y-2 font-mono text-[11px]">
                            {/* Input */}
                            <div>
                              <div className="text-muted-foreground uppercase text-[10px] mb-1">Input Parameters:</div>
                              <pre className="p-2 rounded bg-secondary/30 overflow-x-auto text-sky-300">
                                {JSON.stringify(tool.tool_input, null, 2)}
                              </pre>
                            </div>

                            {/* Output or Error */}
                            {tool.error_message ? (
                              <div>
                                <div className="text-rose-400 uppercase text-[10px] mb-1">Tool Error:</div>
                                <pre className="p-2 rounded bg-rose-950/30 text-rose-300 overflow-x-auto border border-rose-900/50">
                                  {tool.error_message}
                                </pre>
                              </div>
                            ) : (
                              <div>
                                <div className="text-muted-foreground uppercase text-[10px] mb-1">Tool Output:</div>
                                <pre className="p-2 rounded bg-secondary/30 overflow-x-auto text-emerald-300 max-h-56 overflow-y-auto">
                                  {JSON.stringify(tool.tool_output, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
