"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AgentRunResponse, Alert, api } from "@/lib/api";
import { AgentTimeline } from "@/components/AgentTimeline";
import { ApprovalModal } from "@/components/ApprovalModal";
import { Activity, AlertTriangle, ArrowLeft, Bot, CheckCircle2, Play, Shield } from "lucide-react";

const HISTORY_KEY = "cyberbattery.v3.agentRuns";

function loadHistory(): AgentRunResponse[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(HISTORY_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(runs: AgentRunResponse[]) {
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(runs.slice(0, 20)));
}

function alertLabel(alert: Alert) {
  return `${alert.asset_id} · ${alert.risk_tier} · ${alert.risk_score}`;
}

export default function AuditPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [runs, setRuns] = useState<AgentRunResponse[]>(() => loadHistory());
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalRun, setApprovalRun] = useState<AgentRunResponse | null>(null);
  const [approvalNote, setApprovalNote] = useState<string | null>(null);

  useEffect(() => {
    api.getAlerts()
      .then((items) => {
        setAlerts(items);
        const critical = items.find((item) => item.risk_tier === "CRITICAL") ?? items[0];
        setSelectedAlertId(critical?.alert_id ?? "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load alerts"))
      .finally(() => setLoading(false));
  }, []);

  const selectedRun = useMemo(
    () => runs.find((run) => run.event_id === selectedEventId) ?? runs[0] ?? null,
    [runs, selectedEventId]
  );

  async function runPipeline(alertId = selectedAlertId) {
    if (!alertId) return;
    setRunning(true);
    setError(null);
    setApprovalNote(null);
    try {
      const result = await api.runAlertPipeline(alertId);
      const nextRuns = [result, ...runs.filter((run) => run.event_id !== result.event_id)];
      setRuns(nextRuns);
      saveHistory(nextRuns);
      setSelectedEventId(result.event_id);
      if (result.requires_human_approval) {
        setApprovalRun(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setRunning(false);
    }
  }

  function recordDecision(decision: "approved" | "rejected") {
    if (!approvalRun) return;
    setApprovalNote(`${decision === "approved" ? "Approved" : "Rejected"} event ${approvalRun.event_id.slice(0, 8)}`);
    setApprovalRun(null);
  }

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <Shield className="h-7 w-7 text-indigo-400" />
            <span className="text-lg font-bold tracking-tight">
              Cyber<span className="text-indigo-400">Battery</span> Intelligence
            </span>
            <span className="rounded-full border border-indigo-800 px-2 py-0.5 text-xs text-indigo-300">V3</span>
          </div>
          <div className="flex items-center gap-5 text-sm">
            <Link href="/" className="inline-flex items-center gap-2 text-gray-400 hover:text-white">
              <ArrowLeft className="h-4 w-4" /> Command Center
            </Link>
            <Link href="/copilot" className="text-gray-400 hover:text-white">AI Copilot</Link>
            <Link href="/assets" className="text-gray-400 hover:text-white">Assets</Link>
          </div>
        </div>
      </nav>

      <div className="mx-auto grid max-w-screen-2xl gap-6 px-6 py-8 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-6">
          <section className="rounded-lg border border-gray-800 bg-gray-900 p-5">
            <div className="mb-4 flex items-center gap-2">
              <Bot className="h-5 w-5 text-indigo-300" />
              <h1 className="text-base font-semibold">Autonomous Analysis</h1>
            </div>
            <label className="text-xs uppercase tracking-widest text-gray-500">Critical alert</label>
            <select
              value={selectedAlertId}
              onChange={(event) => setSelectedAlertId(event.target.value)}
              className="mt-2 w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-indigo-500"
              disabled={loading || running}
            >
              {alerts.map((alert) => (
                <option key={alert.alert_id} value={alert.alert_id}>
                  {alertLabel(alert)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => runPipeline()}
              disabled={!selectedAlertId || running}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-700"
            >
              <Play className="h-4 w-4" /> {running ? "Running Agents..." : "Run Analysis"}
            </button>
            {error && (
              <div className="mt-4 flex gap-2 rounded-md border border-red-900/60 bg-red-950/30 p-3 text-xs text-red-200">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {approvalNote && (
              <div className="mt-4 flex gap-2 rounded-md border border-green-900/60 bg-green-950/30 p-3 text-xs text-green-200">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                <span>{approvalNote}</span>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-gray-800 bg-gray-900 p-5">
            <div className="mb-4 flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-300" />
              <h2 className="text-base font-semibold">Recent Runs</h2>
            </div>
            <div className="space-y-2">
              {runs.length === 0 ? (
                <div className="rounded-md border border-gray-800 bg-gray-950 p-3 text-sm text-gray-500">
                  No V3 runs recorded in this browser yet.
                </div>
              ) : runs.map((run) => (
                <button
                  key={run.event_id}
                  type="button"
                  onClick={() => setSelectedEventId(run.event_id)}
                  className={`w-full rounded-md border p-3 text-left text-sm transition-colors ${
                    selectedRun?.event_id === run.event_id
                      ? "border-indigo-700 bg-indigo-950/30"
                      : "border-gray-800 bg-gray-950 hover:border-gray-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-gray-300">{run.event_id.slice(0, 8)}</span>
                    <span className={`text-xs ${run.requires_human_approval ? "text-red-300" : "text-green-300"}`}>
                      {run.requires_human_approval ? "approval" : "clear"}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">{run.alert_id}</div>
                </button>
              ))}
            </div>
          </section>
        </aside>

        <section className="rounded-lg border border-gray-800 bg-gray-900 p-6">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">Agent Timeline & Audit Trail</h2>
              <p className="mt-1 text-sm text-gray-500">
                Agent decisions are shown here now; Governance MCP persistence is the next backend step.
              </p>
            </div>
            {selectedRun?.requires_human_approval && (
              <button
                type="button"
                onClick={() => setApprovalRun(selectedRun)}
                className="rounded-md border border-red-800 bg-red-950/30 px-4 py-2 text-sm text-red-100 hover:bg-red-950/50"
              >
                Review Approval
              </button>
            )}
          </div>
          <AgentTimeline run={selectedRun} />
        </section>
      </div>

      <ApprovalModal
        run={approvalRun}
        open={approvalRun !== null}
        onOpenChange={(open) => !open && setApprovalRun(null)}
        onDecision={recordDecision}
      />
    </main>
  );
}
