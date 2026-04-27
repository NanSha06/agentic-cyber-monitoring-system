"use client";
import { Alert } from "@/lib/api";
import { AlertTriangle, ShieldAlert, Info } from "lucide-react";
import Link from "next/link";

interface Props { alerts: Alert[] }

const TIER_ICON: Record<string, React.ReactNode> = {
  CRITICAL:    <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0" />,
  URGENT:      <AlertTriangle className="w-4 h-4 text-orange-400 flex-shrink-0" />,
  INVESTIGATE: <Info className="w-4 h-4 text-yellow-400 flex-shrink-0" />,
};

const TIER_BG: Record<string, string> = {
  CRITICAL:    "border-red-800/50 bg-red-950/30",
  URGENT:      "border-orange-800/50 bg-orange-950/30",
  INVESTIGATE: "border-yellow-800/50 bg-yellow-950/30",
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export function AlertFeed({ alerts }: Props) {
  const active = alerts.filter((a) => !a.resolved).slice(0, 8);

  if (!active.length) {
    return (
      <div className="text-center py-8 text-gray-600">
        <ShieldAlert className="w-8 h-8 mx-auto mb-2 opacity-30" />
        <p className="text-sm">No active alerts</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
      {active.map((a) => (
        <div key={a.alert_id}
             className={`flex items-start gap-3 p-3 rounded-lg border ${TIER_BG[a.risk_tier] ?? "border-gray-800"}`}>
          {TIER_ICON[a.risk_tier] ?? <Info className="w-4 h-4 text-gray-400 flex-shrink-0" />}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-gray-200 truncate">{a.asset_id}</span>
              <span className="text-xs text-gray-500 flex-shrink-0">{timeAgo(a.timestamp)}</span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5 truncate">{a.threat_type} · Score {a.risk_score}</div>
            {a.explanation_available && (
              <Link href={`/explain/${a.alert_id}`}
                    className="text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors">
                View explanation →
              </Link>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
