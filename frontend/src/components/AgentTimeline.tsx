"use client";

import { AgentRunResponse, AgentTraceEntry } from "@/lib/api";
import { AlertCircle, CheckCircle2, Circle, Clock, FileText, ShieldCheck } from "lucide-react";

interface Props {
  run: AgentRunResponse | null;
  compact?: boolean;
}

const STATUS_CLS: Record<string, string> = {
  success:  "border-green-700/60 bg-green-950/30 text-green-300",
  fallback: "border-yellow-700/60 bg-yellow-950/30 text-yellow-300",
  blocked:  "border-red-700/60 bg-red-950/30 text-red-300",
  failed:   "border-red-700/60 bg-red-950/30 text-red-300",
  skipped:  "border-gray-700 bg-gray-900 text-gray-400",
};

function statusIcon(status: string) {
  if (status === "success") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "blocked" || status === "failed") return <AlertCircle className="h-4 w-4" />;
  if (status === "fallback") return <Clock className="h-4 w-4" />;
  return <Circle className="h-4 w-4" />;
}

function formatAgent(name: string) {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTime(iso: string) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(iso));
}

function renderResult(run: AgentRunResponse, agentName: string) {
  const output = run.outputs.find((item) => item.agent_name === agentName);
  if (!output) return null;

  if (agentName === "recommendation") {
    const actions = output.result.proposed_actions;
    const rows = Array.isArray(actions) ? actions.map(String) : [String(actions ?? "")].filter(Boolean);
    return (
      <ul className="mt-3 space-y-2 text-xs text-gray-300">
        {rows.map((action, index) => (
          <li key={`${agentName}-${index}`} className="leading-relaxed">{action}</li>
        ))}
      </ul>
    );
  }

  if (agentName === "diagnosis") {
    const factors = output.result.top_factors;
    if (!Array.isArray(factors) || factors.length === 0) return null;
    return (
      <div className="mt-3 grid gap-2">
        {factors.map((factor, index) => {
          const item = factor as { feature?: string; weight?: number };
          return (
            <div key={`${agentName}-${index}`} className="flex items-center justify-between rounded-md bg-gray-950/70 px-3 py-2 text-xs">
              <span className="text-gray-300">{item.feature ?? "factor"}</span>
              <span className="font-mono text-gray-400">{Number(item.weight ?? 0).toFixed(1)}</span>
            </div>
          );
        })}
      </div>
    );
  }

  if (agentName === "compliance") {
    return (
      <div className="mt-3 flex items-center gap-2 text-xs text-gray-300">
        <ShieldCheck className="h-3.5 w-3.5 text-indigo-300" />
        {String(output.result.decision ?? output.status)}
      </div>
    );
  }

  return null;
}

function TraceRow({ entry, run, compact }: { entry: AgentTraceEntry; run: AgentRunResponse; compact: boolean }) {
  return (
    <div className="relative flex gap-3">
      <div className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border ${STATUS_CLS[entry.status] ?? STATUS_CLS.skipped}`}>
        {statusIcon(entry.status)}
      </div>
      <div className="min-w-0 flex-1 border-b border-gray-800 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-semibold text-gray-100">{formatAgent(entry.agent_name)}</div>
            <div className="mt-0.5 text-xs text-gray-500">{entry.summary}</div>
          </div>
          <div className="text-xs text-gray-500">{formatTime(entry.finished_at)}</div>
        </div>
        {!compact && renderResult(run, entry.agent_name)}
      </div>
    </div>
  );
}

export function AgentTimeline({ run, compact = false }: Props) {
  if (!run) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-gray-800 bg-gray-950/60 p-4 text-sm text-gray-500">
        <FileText className="h-4 w-4" />
        No agent run selected
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-white">Event {run.event_id.slice(0, 8)}</div>
          <div className="text-xs text-gray-500">Backend: {run.bus_backend}</div>
        </div>
        <div className={`rounded-full border px-3 py-1 text-xs ${run.requires_human_approval ? STATUS_CLS.blocked : STATUS_CLS.success}`}>
          {run.requires_human_approval ? "Approval required" : "No approval required"}
        </div>
      </div>
      <div className="space-y-4">
        {run.trace.map((entry) => (
          <TraceRow key={`${run.event_id}-${entry.agent_name}`} entry={entry} run={run} compact={compact} />
        ))}
      </div>
    </div>
  );
}
