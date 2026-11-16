"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, ExternalLink, Award, FileCheck, Layers } from "lucide-react";
import { FinalResponseSchema } from "@/lib/types";

interface FinalAnswerPanelProps {
  finalResponse?: FinalResponseSchema | null;
  status: string;
  totalTokens: number;
  cost: number;
  stepCount: number;
}

export default function FinalAnswerPanel({
  finalResponse,
  status,
  totalTokens,
  cost,
  stepCount,
}: FinalAnswerPanelProps) {
  if (!finalResponse) {
    return null;
  }

  const isCompleted = finalResponse.completion_status === "completed" && status === "COMPLETED";

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden shadow-xl">
      {/* Header */}
      <div className="bg-secondary/40 border-b border-border p-4 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <FileCheck className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-bold text-foreground">Final Synthesized Answer</h3>
        </div>

        <div className="flex items-center gap-2">
          {isCompleted ? (
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <CheckCircle2 className="w-3.5 h-3.5" /> Fully Completed
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">
              <AlertTriangle className="w-3.5 h-3.5" /> Partial Synthesis ({finalResponse.completion_status})
            </span>
          )}

          {finalResponse.confidence_score !== undefined && (
            <span className="flex items-center gap-1 text-xs font-mono text-muted-foreground bg-secondary px-2 py-0.5 rounded border border-border">
              <Award className="w-3.5 h-3.5 text-amber-400" />
              {(finalResponse.confidence_score * 100).toFixed(0)}% Confidence
            </span>
          )}
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Incomplete notice if any */}
        {finalResponse.incomplete_reason && (
          <div className="p-3 rounded-md bg-purple-500/10 border border-purple-500/30 text-xs text-purple-300">
            <span className="font-semibold">Notice:</span> {finalResponse.incomplete_reason}
          </div>
        )}

        {/* Executive Summary */}
        <div>
          <h4 className="text-xs font-mono uppercase text-muted-foreground tracking-wider mb-2 font-semibold">
            Synthesis Summary
          </h4>
          <div className="text-sm leading-relaxed text-foreground bg-secondary/20 p-4 rounded-md border border-border/60 whitespace-pre-wrap">
            {finalResponse.summary}
          </div>
        </div>

        {/* Key Findings */}
        {finalResponse.key_findings && finalResponse.key_findings.length > 0 && (
          <div>
            <h4 className="text-xs font-mono uppercase text-muted-foreground tracking-wider mb-2 font-semibold">
              Key Verified Findings ({finalResponse.key_findings.length})
            </h4>
            <ul className="space-y-2">
              {finalResponse.key_findings.map((finding, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-2.5 text-xs text-foreground/90 bg-secondary/15 p-2.5 rounded border border-border/40"
                >
                  <span className="text-primary font-bold font-mono mt-0.5">#{idx + 1}</span>
                  <span className="leading-relaxed">{finding}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Sources */}
        {finalResponse.sources && finalResponse.sources.length > 0 && (
          <div>
            <h4 className="text-xs font-mono uppercase text-muted-foreground tracking-wider mb-2 font-semibold">
              Referenced Sources ({finalResponse.sources.length})
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {finalResponse.sources.map((src, idx) => (
                <a
                  key={idx}
                  href={src}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between gap-2 p-2 rounded bg-secondary/30 hover:bg-secondary/60 border border-border text-xs font-mono text-sky-400 hover:text-sky-300 transition-colors"
                >
                  <span className="truncate">{src}</span>
                  <ExternalLink className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
