"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3, RefreshCw } from "lucide-react";
import AnalyticsView from "@/components/AnalyticsView";
import { fetchAnalytics } from "@/lib/api";
import { AnalyticsResponse } from "@/lib/types";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await fetchAnalytics();
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || "Failed to load platform analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-mono transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Playground
        </Link>

        <button
          onClick={loadData}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono bg-secondary text-foreground hover:bg-secondary/70 border border-border"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Metrics
        </button>
      </div>

      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
          <BarChart3 className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">Platform Observability & Metrics</h1>
          <p className="text-xs text-muted-foreground">
            Aggregate autonomous agent runs, token costs, latency, and tool failure analytics.
          </p>
        </div>
      </div>

      {loading && !analytics ? (
        <div className="py-20 text-center">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary mb-2" />
          <p className="text-xs text-muted-foreground font-mono">Aggregating platform metrics from database...</p>
        </div>
      ) : error || !analytics ? (
        <div className="p-4 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error || "Could not retrieve analytics."}
        </div>
      ) : (
        <AnalyticsView analytics={analytics} />
      )}
    </div>
  );
}
