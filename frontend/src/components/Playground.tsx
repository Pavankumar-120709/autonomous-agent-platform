"use client";

import React, { useState } from "react";
import { Play, Sliders, Shield, Zap, Sparkles, StopCircle, RefreshCw } from "lucide-react";
import { RunCreateRequest } from "@/lib/types";

interface PlaygroundProps {
  onStartRun: (config: RunCreateRequest) => Promise<void>;
  onCancelRun?: () => Promise<void>;
  isRunning?: boolean;
}

const PRESETS = [
  {
    title: "Quantum Milestones",
    objective: "Investigate quantum computing architectures, qubit technologies, and key experimental milestones.",
  },
  {
    title: "Financial Math",
    objective: "Calculate the compound return of $15,000 invested at 7.5% annual return over 20 years, and save the formulas in structured notes.",
  },
  {
    title: "Web Research & Verification",
    objective: "Discover the latest research on autonomous agent memory architectures and summarize the core design patterns.",
  },
];

export default function Playground({ onStartRun, onCancelRun, isRunning }: PlaygroundProps) {
  const [objective, setObjective] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [tokenBudget, setTokenBudget] = useState(50000);
  const [maxSteps, setMaxSteps] = useState(12);
  const [maxToolCalls, setMaxToolCalls] = useState(4);
  const [timeoutSeconds, setTimeoutSeconds] = useState(180);
  const [showConfig, setShowConfig] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim()) {
      setError("Please enter a research objective.");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await onStartRun({
        objective: objective.trim(),
        model,
        token_budget: Number(tokenBudget),
        max_steps: Number(maxSteps),
        max_tool_calls_per_step: Number(maxToolCalls),
        timeout_seconds: Number(timeoutSeconds),
      });
    } catch (err: any) {
      setError(err.message || "Failed to start agent run.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
      <div className="p-4 sm:p-5 border-b border-border bg-secondary/30 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-foreground flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" /> Autonomous Agent Playground
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Configure research objective and execution constraints.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowConfig(!showConfig)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-medium bg-secondary text-foreground hover:bg-secondary/70 border border-border transition-colors"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>{showConfig ? "Hide Bounds" : "Configure Bounds"}</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-4 sm:p-5 space-y-4">
        {error && (
          <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Objective Input */}
        <div>
          <label className="block text-xs font-mono text-muted-foreground uppercase tracking-wider mb-2 font-semibold">
            Agent Research Objective
          </label>
          <textarea
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            disabled={isRunning || submitting}
            placeholder="e.g. Research current commercial quantum processor architectures, compare their qubit coherence times, and compute the ratio difference."
            rows={3}
            className="w-full bg-secondary/30 border border-border rounded-md px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all disabled:opacity-50"
          />
        </div>

        {/* Preset chips */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="text-muted-foreground flex items-center gap-1 text-[11px] font-mono">
            <Sparkles className="w-3 h-3 text-amber-400" /> Presets:
          </span>
          {PRESETS.map((p) => (
            <button
              key={p.title}
              type="button"
              disabled={isRunning || submitting}
              onClick={() => setObjective(p.objective)}
              className="px-2.5 py-1 rounded bg-secondary/50 hover:bg-secondary text-foreground/80 hover:text-foreground text-[11px] border border-border/80 transition-colors disabled:opacity-50"
            >
              {p.title}
            </button>
          ))}
        </div>

        {/* Collapsible Bounded Configuration */}
        {showConfig && (
          <div className="p-4 rounded-md bg-secondary/20 border border-border/80 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            {/* Model */}
            <div>
              <label className="block font-mono text-muted-foreground uppercase text-[11px] mb-1 font-semibold">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={isRunning}
                className="w-full bg-secondary border border-border rounded px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="gpt-4o-mini">gpt-4o-mini (Fast & Efficient)</option>
                <option value="gpt-4o">gpt-4o (High Reasoning)</option>
                <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
              </select>
            </div>

            {/* Token Budget */}
            <div>
              <label className="block font-mono text-muted-foreground uppercase text-[11px] mb-1 font-semibold">
                Token Budget: {tokenBudget.toLocaleString()}
              </label>
              <input
                type="range"
                min="5000"
                max="100000"
                step="5000"
                value={tokenBudget}
                onChange={(e) => setTokenBudget(Number(e.target.value))}
                disabled={isRunning}
                className="w-full accent-primary"
              />
            </div>

            {/* Max Steps */}
            <div>
              <label className="block font-mono text-muted-foreground uppercase text-[11px] mb-1 font-semibold">
                Max Steps: {maxSteps} (Max 12)
              </label>
              <input
                type="range"
                min="3"
                max="12"
                step="1"
                value={maxSteps}
                onChange={(e) => setMaxSteps(Number(e.target.value))}
                disabled={isRunning}
                className="w-full accent-primary"
              />
            </div>

            {/* Execution Timeout */}
            <div>
              <label className="block font-mono text-muted-foreground uppercase text-[11px] mb-1 font-semibold">
                Timeout: {timeoutSeconds}s
              </label>
              <input
                type="range"
                min="30"
                max="300"
                step="15"
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                disabled={isRunning}
                className="w-full accent-primary"
              />
            </div>
          </div>
        )}

        {/* Buttons */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">Bounded: Max 12 steps, 4 tool calls/step, SSRF-protected.</span>
          </div>

          <div className="flex items-center gap-2">
            {isRunning && onCancelRun && (
              <button
                type="button"
                onClick={onCancelRun}
                className="flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20 transition-colors"
              >
                <StopCircle className="w-4 h-4" /> Cancel Execution
              </button>
            )}

            <button
              type="submit"
              disabled={isRunning || submitting || !objective.trim()}
              className="flex items-center gap-2 px-5 py-2 rounded-md text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all shadow-sm"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Dispatching...
                </>
              ) : isRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Running Agent...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" /> Start Autonomous Run
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
