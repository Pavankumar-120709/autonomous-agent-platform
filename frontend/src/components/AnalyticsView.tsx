"use client";

import React from "react";
import {
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Coins,
  TrendingUp,
  Cpu,
  Layers,
  Wrench,
} from "lucide-react";
import { AnalyticsResponse } from "@/lib/types";
import { formatCost, formatDuration, formatNumber } from "@/lib/utils";

interface AnalyticsViewProps {
  analytics: AnalyticsResponse;
}

export default function AnalyticsView({ analytics }: AnalyticsViewProps) {
  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Runs */}
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono uppercase">
            <span>Total Runs</span>
            <Layers className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-bold font-mono text-foreground mt-2">
            {formatNumber(analytics.total_runs)}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {analytics.completed_runs} completed ({analytics.success_rate_percent}%)
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono uppercase">
            <span>Success Rate</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">
            {analytics.success_rate_percent}%
          </div>
          <div className="w-full bg-secondary rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-emerald-500 h-1.5 transition-all duration-300"
              style={{ width: `${analytics.success_rate_percent}%` }}
            />
          </div>
        </div>

        {/* Total Tokens & Cost */}
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono uppercase">
            <span>Tokens & Cost</span>
            <Coins className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-foreground mt-2">
            {formatNumber(analytics.total_tokens_consumed)}
          </div>
          <div className="text-xs text-emerald-400 font-mono mt-1">
            {formatCost(analytics.estimated_total_cost_usd)} est. cost
          </div>
        </div>

        {/* Avg Duration */}
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono uppercase">
            <span>Avg Duration</span>
            <Clock className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-foreground mt-2">
            {formatDuration(analytics.avg_duration_seconds)}
          </div>
          <div className="text-xs text-muted-foreground mt-1 font-mono">
            {analytics.avg_steps_per_run} steps / {analytics.avg_tool_calls_per_run} tools avg
          </div>
        </div>
      </div>

      {/* Breakdown Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Status Breakdown */}
        <div className="bg-card border border-border rounded-lg p-5">
          <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-4 font-semibold flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-primary" /> Run Status Breakdown
          </h4>
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-foreground">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Completed
              </span>
              <span className="font-mono font-medium">{analytics.completed_runs}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-foreground">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500" /> Budget Exhausted
              </span>
              <span className="font-mono font-medium">{analytics.budget_exhausted_runs}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-foreground">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500" /> Timed Out
              </span>
              <span className="font-mono font-medium">{analytics.timed_out_runs}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-foreground">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Failed
              </span>
              <span className="font-mono font-medium">{analytics.failed_runs}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-foreground">
                <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground" /> Cancelled
              </span>
              <span className="font-mono font-medium">{analytics.cancelled_runs}</span>
            </div>
          </div>
        </div>

        {/* Token Split */}
        <div className="bg-card border border-border rounded-lg p-5">
          <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-4 font-semibold flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-primary" /> Token Consumption Split
          </h4>
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Prompt Tokens:</span>
              <span className="font-mono font-medium text-foreground">
                {formatNumber(analytics.total_prompt_tokens)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Completion Tokens:</span>
              <span className="font-mono font-medium text-foreground">
                {formatNumber(analytics.total_completion_tokens)}
              </span>
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-border">
              <span className="text-foreground font-semibold">Total Consumed:</span>
              <span className="font-mono font-bold text-primary">
                {formatNumber(analytics.total_tokens_consumed)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-foreground font-semibold">Total Billed Cost:</span>
              <span className="font-mono font-bold text-emerald-400">
                {formatCost(analytics.estimated_total_cost_usd)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tool Performance Breakdown Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="p-4 border-b border-border flex items-center gap-2">
          <Wrench className="w-4 h-4 text-primary" />
          <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground font-semibold">
            Tool Performance & Reliability Statistics
          </h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/30 border-b border-border/80 text-muted-foreground uppercase font-mono text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Tool Name</th>
                <th className="py-2.5 px-4">Total Invocations</th>
                <th className="py-2.5 px-4">Failures</th>
                <th className="py-2.5 px-4">Success Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {Object.keys(analytics.tool_usage_counts).length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-muted-foreground">
                    No tools executed yet.
                  </td>
                </tr>
              ) : (
                Object.entries(analytics.tool_usage_counts).map(([toolName, count]) => {
                  const fails = analytics.tool_failure_counts[toolName] || 0;
                  const rate = analytics.tool_success_rates[toolName] ?? 100.0;
                  return (
                    <tr key={toolName} className="hover:bg-secondary/20">
                      <td className="py-3 px-4 font-mono font-medium text-foreground">{toolName}</td>
                      <td className="py-3 px-4 font-mono">{count}</td>
                      <td className="py-3 px-4 font-mono text-rose-400">{fails}</td>
                      <td className="py-3 px-4 font-mono">
                        <span
                          className={`font-semibold ${
                            rate >= 90 ? "text-emerald-400" : rate >= 70 ? "text-amber-400" : "text-rose-400"
                          }`}
                        >
                          {rate}%
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
