"use client";
import { useEffect, useState } from "react";
import { api, Asset, Alert } from "@/lib/api";
import { useRiskStream } from "@/lib/ws";
import { RiskGauge } from "@/components/RiskGauge";
import { AlertFeed } from "@/components/AlertFeed";
import { ThreatHeatmap } from "@/components/ThreatHeatmap";
import { AssetTable } from "@/components/AssetTable";
import { Shield, Wifi, WifiOff, Activity, Bot, Database, ArrowRight } from "lucide-react";
import Link from "next/link";

// ── Mock data shown when the backend is offline ───────────────────────────────
const TIERS = ["NOMINAL","INVESTIGATE","URGENT","CRITICAL"] as const;
const THREATS = ["normal","normal","portscan","dos","ddos","bruteforce"];

const MOCK_ASSETS: Asset[] = Array.from({ length: 12 }, (_, i) => ({
  asset_id:    `BATTERY-${String(i + 1).padStart(3, "0")}`,
  location:    `Tower-${i + 1}`,
  soh:         +(70 + Math.random() * 30).toFixed(1),
  soc:         +(20 + Math.random() * 80).toFixed(1),
  temp:        +(18 + Math.random() * 30).toFixed(1),
  voltage:     +(3.2 + Math.random()).toFixed(2),
  risk_score:  +(5  + Math.random() * 90).toFixed(1),
  risk_tier:   TIERS[Math.floor(Math.random() * 4)],
  rul_cycles:  Math.floor(50 + Math.random() * 750),
  threat_type: THREATS[Math.floor(Math.random() * THREATS.length)],
  last_seen:   new Date().toISOString(),
  status:      "online",
}));

const MOCK_ALERTS: Alert[] = Array.from({ length: 8 }, (_, i) => ({
  alert_id:             `alert-${i}`,
  asset_id:             MOCK_ASSETS[i % 12].asset_id,
  risk_score:           +(45 + Math.random() * 55).toFixed(1),
  risk_tier:            ["INVESTIGATE","URGENT","CRITICAL"][Math.floor(Math.random()*3)],
  threat_type:          THREATS[Math.floor(Math.random() * THREATS.length)],
  description:          "Anomalous battery + network activity detected",
  timestamp:            new Date(Date.now() - i * 420_000).toISOString(),
  resolved:             false,
  explanation_available: true,
}));

// ── Static colour maps (prevents Tailwind from purging dynamic class strings) ─
const KPI_VALUE_CLS:  Record<string,string> = { indigo:"text-indigo-400", red:"text-red-400", orange:"text-orange-400", yellow:"text-yellow-400", green:"text-green-400" };

export default function CommandCenter() {
  const [assets, setAssets]   = useState<Asset[]>([]);
  const [alerts, setAlerts]   = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [copilotReady, setCopilotReady] = useState<boolean | null>(null);
  const { updates, connected } = useRiskStream();

  useEffect(() => {
    Promise.all([api.getAssets(), api.getAlerts()])
      .then(([a, al]) => { setAssets(a); setAlerts(al); setLoading(false); })
      .catch(() => {
        setAssets(MOCK_ASSETS);
        setAlerts(MOCK_ALERTS);
        setOffline(true);
        setLoading(false);
      });

    api.copilotStatus()
      .then((status) => setCopilotReady(status.ready))
      .catch(() => setCopilotReady(false));
  }, []);

  const liveAssets = assets.map((a) => {
    const upd = updates[a.asset_id];
    return upd ? { ...a, risk_score: upd.risk_score, risk_tier: upd.risk_tier as Asset["risk_tier"] } : a;
  });

  const critical = liveAssets.filter((a) => a.risk_tier === "CRITICAL").length;
  const urgent   = liveAssets.filter((a) => a.risk_tier === "URGENT").length;
  const avgRisk  = liveAssets.length
    ? Math.round(liveAssets.reduce((s, a) => s + a.risk_score, 0) / liveAssets.length)
    : 0;

  const kpis = [
    { label: "Fleet Size",      value: liveAssets.length, color: "indigo" },
    { label: "Critical Assets", value: critical,           color: "red"    },
    { label: "Urgent Assets",   value: urgent,             color: "orange" },
    { label: "Avg Risk Score",  value: `${avgRisk}/100`,  color: "yellow" },
    { label: "RAG Copilot",     value: copilotReady ? "Ready" : "Setup", color: copilotReady ? "green" : "orange" },
  ];

  return (
    <main className="min-h-screen bg-gray-950 text-white">
      {/* ── Top Nav ── */}
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-7 h-7 text-indigo-400" />
            <span className="text-lg font-bold tracking-tight">
              Cyber<span className="text-indigo-400">Battery</span> Intelligence
            </span>
            <span className="text-xs text-gray-500 border border-gray-700 px-2 py-0.5 rounded-full">V3</span>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <span className="font-semibold text-indigo-300">Command Center</span>
            <Link href="/audit" className="text-gray-400 hover:text-white transition-colors">Audit</Link>
            <Link href="/copilot" className="text-gray-400 hover:text-white transition-colors">AI Copilot</Link>
            <Link href="/assets" className="text-gray-400 hover:text-white transition-colors">Assets</Link>
            <Link href="/explain/demo" className="text-gray-400 hover:text-white transition-colors">Explain</Link>
            <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${
              connected ? "bg-green-900/50 text-green-400" : "bg-gray-800 text-gray-500"
            }`}>
              {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {connected ? "Live" : "Offline"}
            </div>
          </div>
        </div>
      </nav>

      {/* ── Offline banner ── */}
      {offline && (
        <div className="bg-amber-900/30 border-b border-amber-700/50 px-6 py-2 text-xs text-amber-400 text-center">
          ⚠ Backend offline — showing demo data.&nbsp;
          Start API: <code className="bg-black/30 px-1.5 py-0.5 rounded font-mono">uvicorn backend.main:app --reload --port 8000</code>
        </div>
      )}

      <div className="max-w-screen-2xl mx-auto px-6 py-8 space-y-8">
        {/* ── KPI Bar ── */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {kpis.map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
              <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">{label}</div>
              <div className={`text-4xl font-bold ${KPI_VALUE_CLS[color]}`}>{value}</div>
            </div>
          ))}
        </div>

        <section className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-indigo-900/50 border border-indigo-800/50 flex items-center justify-center flex-shrink-0">
                <Bot className="w-6 h-6 text-indigo-300" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">AI Copilot with RAG</h2>
                <p className="text-sm text-gray-400 mt-1 max-w-2xl">
                  Ask operational questions grounded in the local playbooks, OEM notes, CVE advisories, and incident procedures.
                </p>
                <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                  <Database className="w-3.5 h-3.5" />
                  {copilotReady === null
                    ? "Checking retrieval index..."
                    : copilotReady
                      ? "FAISS index and Gemini key are available"
                      : "Copilot backend is reachable, but the retrieval index or Gemini key is not ready"}
                </div>
              </div>
            </div>
            <Link
              href="/copilot"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
            >
              Open Copilot <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>

        {/* ── Risk Gauges ── */}
        <section>
          <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Fleet Risk Overview
          </h2>
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="bg-gray-900 rounded-xl h-28 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {liveAssets.map((a) => (
                <Link key={a.asset_id} href={`/assets/${a.asset_id}`}>
                  <RiskGauge
                    assetId={a.asset_id}
                    location={a.location}
                    score={a.risk_score}
                    tier={a.risk_tier}
                    soh={a.soh}
                  />
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* ── Bottom Grid: Heatmap + Alert Feed ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4">Threat Heatmap</h2>
            <ThreatHeatmap assets={liveAssets} />
          </section>
          <section className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4">Active Alerts</h2>
            <AlertFeed alerts={alerts} />
          </section>
        </div>

        {/* ── Full Asset Table ── */}
        <section className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4">Asset Registry</h2>
          <AssetTable assets={liveAssets} />
        </section>
      </div>
    </main>
  );
}
