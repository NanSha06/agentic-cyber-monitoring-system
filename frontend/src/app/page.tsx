"use client";
import { useEffect, useState } from "react";
import { api, Asset, Alert } from "@/lib/api";
import { useRiskStream } from "@/lib/ws";
import { RiskGauge } from "@/components/RiskGauge";
import { AlertFeed } from "@/components/AlertFeed";
import { ThreatHeatmap } from "@/components/ThreatHeatmap";
import { AssetTable } from "@/components/AssetTable";
import { Shield, Wifi, WifiOff, Activity } from "lucide-react";
import Link from "next/link";

export default function CommandCenter() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const { updates, connected } = useRiskStream();

  useEffect(() => {
    Promise.all([api.getAssets(), api.getAlerts()]).then(([a, al]) => {
      setAssets(a);
      setAlerts(al);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Merge live WebSocket updates into assets
  const liveAssets = assets.map((a) => {
    const upd = updates[a.asset_id];
    return upd ? { ...a, risk_score: upd.risk_score, risk_tier: upd.risk_tier as any } : a;
  });

  const critical = liveAssets.filter((a) => a.risk_tier === "CRITICAL").length;
  const urgent   = liveAssets.filter((a) => a.risk_tier === "URGENT").length;
  const avgRisk  = liveAssets.length
    ? Math.round(liveAssets.reduce((s, a) => s + a.risk_score, 0) / liveAssets.length)
    : 0;

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
            <span className="text-xs text-gray-500 border border-gray-700 px-2 py-0.5 rounded-full">V1</span>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <span className="font-semibold text-indigo-300">Command Center</span>
            <Link href="/assets" className="text-gray-400 hover:text-white transition-colors">Assets</Link>
            <Link href="/explain/demo" className="text-gray-400 hover:text-white transition-colors">Explain</Link>
            <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${connected ? "bg-green-900/50 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {connected ? "Live" : "Offline"}
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-screen-2xl mx-auto px-6 py-8 space-y-8">
        {/* ── KPI Bar ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Fleet Size",      value: liveAssets.length, color: "indigo" },
            { label: "Critical Assets", value: critical,           color: "red"    },
            { label: "Urgent Assets",   value: urgent,             color: "orange" },
            { label: "Avg Risk Score",  value: `${avgRisk}/100`,  color: "yellow" },
          ].map(({ label, value, color }) => (
            <div key={label} className={`bg-gray-900 border border-gray-800 rounded-2xl p-5`}>
              <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">{label}</div>
              <div className={`text-4xl font-bold text-${color}-400`}>{value}</div>
            </div>
          ))}
        </div>

        {/* ── Risk Gauges ── */}
        <section>
          <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Fleet Risk Overview
          </h2>
          {loading ? (
            <div className="text-gray-500 animate-pulse">Loading fleet data…</div>
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
