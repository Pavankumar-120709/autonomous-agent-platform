"use client";

import React, { useState } from "react";
import Link from "next/link";
import { History, ArrowUpRight, Search, Clock, Coins, CheckCircle2, AlertTriangle, XCircle, Activity } from "lucide-react";
import { RunStatus, RunSummary } from "@/lib/types";
import { formatCost, formatDuration, formatNumber, formatTimestamp } from "@/lib/utils";

interface RunHistoryTableProps {
  runs: RunSummary[];
  onSelectRun?: (runId: string) => void;
  selectedRunId?: string;
}

export default function RunHistoryTable({ runs, onSelectRun, selectedRunId }: RunHistoryTableProps) {
  const [filter, setFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");

  const filteredRuns = runs.filter((r) => {
    if (filter !== "ALL" && r.status !== filter) return false;
    if (search && !r.objective.toLowerCase().includes(search.toLowerCase()) && !r.id.includes(search)) {
      return false;
    }
    return true;
  });

  const getStatusBadge = (status: RunStatus) => {
    switch (status) {
      case "COMPLETED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">COMPLETED</span>;
      case "RUNNING":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">RUNNING</span>;
      case "BUDGET_EXHAUSTED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/30">BUDGET EXHAUSTED</span>;
      case "TIMED_OUT":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-orange-500/10 text-orange-400 border border-orange-500/30">TIMED OUT</span>;
      case "CANCELLED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30">CANCELLED</span>;
      case "FAILED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30">FAILED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-secondary text-muted-foreground border border-border">PENDING</span>;
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden shadow-sm">
      {/* Header and filters */}
      <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-bold text-foreground">Execution History</h3>
          <span className="text-xs text-muted-foreground font-mono">({filteredRuns.length})</span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search runs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-secondary/40 border border-border rounded pl-8 pr-3 py-1 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary w-40 sm:w-48"
            />
          </div>

          {/* Status Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-secondary/40 border border-border rounded px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="RUNNING">Running</option>
            <option value="BUDGET_EXHAUSTED">Budget Exhausted</option>
            <option value="TIMED_OUT">Timed Out</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-secondary/30 border-b border-border/80 text-muted-foreground uppercase font-mono text-[11px]">
            <tr>
              <th className="py-2.5 px-4">Run ID & Objective</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Steps</th>
              <th className="py-2.5 px-3">Tokens</th>
              <th className="py-2.5 px-3">Cost</th>
              <th className="py-2.5 px-3">Duration</th>
              <th className="py-2.5 px-3">Time</th>
              <th className="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {filteredRuns.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-muted-foreground">
                  No historical runs match the criteria.
                </td>
              </tr>
            ) : (
              filteredRuns.map((run) => {
                const isSelected = run.id === selectedRunId;
                return (
                  <tr
                    key={run.id}
                    onClick={() => onSelectRun && onSelectRun(run.id)}
                    className={`hover:bg-secondary/30 transition-colors cursor-pointer ${
                      isSelected ? "bg-primary/5 border-l-2 border-primary" : ""
                    }`}
                  >
                    <td className="py-3 px-4 max-w-xs sm:max-w-md">
                      <div className="font-mono text-[11px] text-muted-foreground truncate">{run.id}</div>
                      <div className="font-medium text-foreground truncate mt-0.5">{run.objective}</div>
                    </td>
                    <td className="py-3 px-3">{getStatusBadge(run.status)}</td>
                    <td className="py-3 px-3 font-mono">
                      {run.step_count} <span className="text-muted-foreground text-[10px]">/ {run.max_steps}</span>
                    </td>
                    <td className="py-3 px-3 font-mono">{formatNumber(run.total_tokens)}</td>
                    <td className="py-3 px-3 font-mono text-emerald-400">{formatCost(run.estimated_cost)}</td>
                    <td className="py-3 px-3 font-mono text-muted-foreground">
                      {formatDuration(run.duration_seconds)}
                    </td>
                    <td className="py-3 px-3 font-mono text-muted-foreground">
                      {formatTimestamp(run.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/runs/${run.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 text-primary hover:text-primary/80 font-mono text-xs"
                      >
                        Trace <ArrowUpRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
