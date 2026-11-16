import React from "react";
import { Clock, Coins, Layers, Activity, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { RunStatus } from "@/lib/types";
import { formatCost, formatDuration, formatNumber } from "@/lib/utils";

interface MetricsBarProps {
  status: RunStatus;
  currentStep: number;
  maxSteps: number;
  totalTokens: number;
  tokenBudget: number;
  cost: number;
  durationSeconds?: number | null;
  toolCallCount?: number;
}

export default function MetricsBar({
  status,
  currentStep,
  maxSteps,
  totalTokens,
  tokenBudget,
  cost,
  durationSeconds,
  toolCallCount = 0,
}: MetricsBarProps) {
  const getStatusBadge = () => {
    switch (status) {
      case "RUNNING":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
            <Activity className="w-3.5 h-3.5" /> RUNNING
          </span>
        );
      case "COMPLETED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> COMPLETED
          </span>
        );
      case "BUDGET_EXHAUSTED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <AlertTriangle className="w-3.5 h-3.5" /> BUDGET EXHAUSTED
          </span>
        );
      case "TIMED_OUT":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-400 border border-orange-500/30">
            <Clock className="w-3.5 h-3.5" /> TIMED OUT
          </span>
        );
      case "CANCELLED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5" /> CANCELLED
          </span>
        );
      case "FAILED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5" /> FAILED
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-muted text-muted-foreground border border-border">
            PENDING
          </span>
        );
    }
  };

  const tokenPercent = Math.min(100, Math.round((totalTokens / (tokenBudget || 50000)) * 100));

  return (
    <div className="bg-card border border-border rounded-lg p-4 grid grid-cols-2 md:grid-cols-5 gap-4">
      {/* Status */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono">Agent Status</span>
        <div className="flex items-center mt-0.5">{getStatusBadge()}</div>
      </div>

      {/* Step Budget */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono flex items-center gap-1">
          <Layers className="w-3.5 h-3.5" /> Step Bound
        </span>
        <div className="text-sm font-bold text-foreground">
          {currentStep} <span className="text-muted-foreground text-xs font-normal">/ {maxSteps} max</span>
        </div>
        <div className="w-full bg-secondary rounded-full h-1.5 mt-1 overflow-hidden">
          <div
            className="bg-primary h-1.5 transition-all duration-300"
            style={{ width: `${Math.min(100, (currentStep / maxSteps) * 100)}%` }}
          />
        </div>
      </div>

      {/* Token Consumption */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono flex items-center gap-1">
          <Coins className="w-3.5 h-3.5" /> Tokens Used
        </span>
        <div className="text-sm font-bold text-foreground">
          {formatNumber(totalTokens)}{" "}
          <span className="text-muted-foreground text-xs font-normal">/ {formatNumber(tokenBudget)}</span>
        </div>
        <div className="w-full bg-secondary rounded-full h-1.5 mt-1 overflow-hidden">
          <div
            className={`h-1.5 transition-all duration-300 ${
              tokenPercent > 90 ? "bg-rose-500" : tokenPercent > 70 ? "bg-amber-500" : "bg-emerald-500"
            }`}
            style={{ width: `${tokenPercent}%` }}
          />
        </div>
      </div>

      {/* Estimated Cost */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono">Est. Cost</span>
        <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">{formatCost(cost)}</div>
        <span className="text-[11px] text-muted-foreground">{toolCallCount} tool calls</span>
      </div>

      {/* Duration */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" /> Elapsed
        </span>
        <div className="text-sm font-bold text-foreground font-mono mt-0.5">
          {formatDuration(durationSeconds)}
        </div>
        <span className="text-[11px] text-muted-foreground">Wall-clock bounded</span>
      </div>
    </div>
  );
}
