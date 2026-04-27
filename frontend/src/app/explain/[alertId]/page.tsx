"use client";
import { useEffect, useState } from "react";
import { api, Explanation } from "@/lib/api";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, BarChart3 } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts";

export default function ExplainPage() {
  const params  = useParams();
  const alertId = params.alertId as string;
  const [exp, setExp]       = useState<Explanation | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getExplanation(alertId).then((e) => {
      setExp(e);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [alertId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500 animate-pulse">
        Loading explanation…
      </div>
    );
  }

  if (!exp) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500">
        Explanation not found for alert {alertId}
      </div>
    );
  }

  const chartData = exp.contributions.map((c) => ({
    name:   c.feature.replace(/_/g, " "),
    weight: c.weight,
  }));

  return (
    <main className="min-h-screen bg-gray-950 text-white pb-16">
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50 px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm">
            <ArrowLeft className="w-4 h-4" /> Command Center
          </Link>
          <span className="text-gray-600">/</span>
          <span className="flex items-center gap-1.5 text-gray-300 text-sm">
            <BarChart3 className="w-4 h-4" /> LIME Explanation
          </span>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-10 space-y-8">
        {/* ── Header ── */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-bold">Alert Explanation</h1>
              <p className="text-sm text-gray-500 font-mono mt-1">{exp.asset_id}</p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-black text-red-400">{exp.risk_score}</div>
              <div className="text-xs text-gray-500">Risk Score</div>
            </div>
          </div>
          <pre className="mt-4 text-xs text-gray-400 bg-gray-950 rounded-lg p-4 whitespace-pre-wrap font-mono leading-relaxed border border-gray-800">
            {exp.human_readable}
          </pre>
        </div>

        {/* ── LIME Bar Chart ── */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-sm uppercase tracking-widest text-gray-500 mb-4">Feature Contributions (LIME)</h2>
          <p className="text-xs text-gray-600 mb-4">
            Positive values push the risk score <strong className="text-red-400">higher</strong>;
            negative values push it <strong className="text-green-400">lower</strong>.
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 140 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#d1d5db", fontSize: 11 }} tickLine={false} axisLine={false} width={130} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                       formatter={(v: unknown) => [(v as number).toFixed(3), "Weight"]} />
              <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.weight > 0 ? "#f87171" : "#34d399"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* ── Raw JSON ── */}
        <details className="bg-gray-900 border border-gray-800 rounded-2xl p-4">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300 uppercase tracking-widest">
            Raw JSON Response
          </summary>
          <pre className="mt-3 text-xs text-gray-400 overflow-auto">{JSON.stringify(exp, null, 2)}</pre>
        </details>
      </div>
    </main>
  );
}
