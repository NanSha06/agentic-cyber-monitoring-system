"use client";
import { useEffect, useState } from "react";
import { api, Asset, Alert } from "@/lib/api";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Battery, Thermometer, Zap, Shield } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";

export default function AssetDetail() {
  const params   = useParams();
  const assetId  = params.id as string;
  const [asset, setAsset]     = useState<Asset | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [alerts, setAlerts]   = useState<Alert[]>([]);

  useEffect(() => {
    Promise.all([
      api.getAsset(assetId),
      api.getHistory(assetId, 6),
      api.getAlerts(false),
    ]).then(([a, h, al]) => {
      setAsset(a);
      setHistory(h.history.slice(-60));     // last 60 points
      setAlerts(al.filter((x: Alert) => x.asset_id === assetId));
    }).catch(console.error);
  }, [assetId]);

  if (!asset) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500 animate-pulse">
        Loading asset…
      </div>
    );
  }

  const tierColor: Record<string, string> = {
    NOMINAL: "text-green-400", INVESTIGATE: "text-yellow-400",
    URGENT: "text-orange-400", CRITICAL: "text-red-400",
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white pb-16">
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50 px-6 py-3">
        <div className="max-w-screen-xl mx-auto flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm">
            <ArrowLeft className="w-4 h-4" /> Command Center
          </Link>
          <span className="text-gray-600">/</span>
          <span className="font-mono text-indigo-300 text-sm">{assetId}</span>
        </div>
      </nav>

      <div className="max-w-screen-xl mx-auto px-6 py-8 space-y-8">
        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">{asset.location}</h1>
            <p className="text-sm text-gray-500 font-mono">{assetId}</p>
          </div>
          <div className={`text-right`}>
            <div className={`text-5xl font-black ${tierColor[asset.risk_tier] ?? "text-white"}`}>
              {asset.risk_score}
            </div>
            <div className={`text-xs font-bold tracking-widest ${tierColor[asset.risk_tier]}`}>
              {asset.risk_tier}
            </div>
          </div>
        </div>

        {/* ── KPI Cards ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: Battery,     label: "State of Health", value: `${asset.soh}%`,    color: "green"  },
            { icon: Zap,         label: "State of Charge", value: `${asset.soc}%`,    color: "indigo" },
            { icon: Thermometer, label: "Temperature",     value: `${asset.temp}°C`,  color: "orange" },
            { icon: Shield,      label: "RUL Cycles",      value: asset.rul_cycles,   color: "blue"   },
          ].map(({ icon: Icon, label, value, color }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-4 h-4 text-${color}-400`} />
                <span className="text-xs text-gray-500">{label}</span>
              </div>
              <div className={`text-3xl font-bold text-${color}-400`}>{value}</div>
            </div>
          ))}
        </div>

        {/* ── Time Series Charts ── */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4">Battery Telemetry (6h)</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={history} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                     tick={{ fill: "#6b7280", fontSize: 10 }} tickLine={false} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                       labelStyle={{ color: "#9ca3af" }} itemStyle={{ color: "#e5e7eb" }} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
              <Line type="monotone" dataKey="voltage" stroke="#818cf8" strokeWidth={2} dot={false} name="Voltage (V)" />
              <Line type="monotone" dataKey="temp"    stroke="#fb923c" strokeWidth={2} dot={false} name="Temp (°C)" />
              <Line type="monotone" dataKey="soc"     stroke="#34d399" strokeWidth={2} dot={false} name="SOC (%)" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* ── Asset Alerts ── */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4">Recent Alerts</h2>
          {alerts.length === 0 ? (
            <p className="text-gray-600 text-sm">No alerts for this asset</p>
          ) : (
            <div className="space-y-2">
              {alerts.slice(0, 5).map((a) => (
                <div key={a.alert_id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                  <div>
                    <span className="text-sm text-gray-200">{a.threat_type}</span>
                    <span className="ml-2 text-xs text-gray-500">{new Date(a.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-white">{a.risk_score}</span>
                    {a.explanation_available && (
                      <Link href={`/explain/${a.alert_id}`}
                            className="text-xs text-indigo-400 hover:text-indigo-300">Explain →</Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
