"use client";
import { useEffect, useState } from "react";
import { api, Asset } from "@/lib/api";
import { AssetTable } from "@/components/AssetTable";
import { Shield, ArrowLeft } from "lucide-react";
import Link from "next/link";

const MOCK_ASSETS: Asset[] = Array.from({ length: 12 }, (_, i) => ({
  asset_id:    `BATTERY-${String(i + 1).padStart(3, "0")}`,
  location:    `Tower-${i + 1}`,
  soh:         +(70 + Math.random() * 30).toFixed(1),
  soc:         +(20 + Math.random() * 80).toFixed(1),
  temp:        +(18 + Math.random() * 30).toFixed(1),
  voltage:     +(3.2 + Math.random()).toFixed(2),
  risk_score:  +(5  + Math.random() * 90).toFixed(1),
  risk_tier:   (["NOMINAL","INVESTIGATE","URGENT","CRITICAL"] as const)[Math.floor(Math.random()*4)],
  rul_cycles:  Math.floor(50 + Math.random() * 750),
  threat_type: ["normal","normal","portscan","dos"][Math.floor(Math.random()*4)],
  last_seen:   new Date().toISOString(),
  status:      "online",
}));

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAssets()
      .then((a) => { setAssets(a); setLoading(false); })
      .catch(() => { setAssets(MOCK_ASSETS); setLoading(false); });
  }, []);

  return (
    <main className="min-h-screen bg-gray-950 text-white pb-16">
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50 px-6 py-3">
        <div className="max-w-screen-xl mx-auto flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm">
            <ArrowLeft className="w-4 h-4" /> Command Center
          </Link>
          <span className="text-gray-600">/</span>
          <span className="flex items-center gap-1.5 text-gray-300 text-sm">
            <Shield className="w-4 h-4" /> Asset Registry
          </span>
        </div>
      </nav>

      <div className="max-w-screen-xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Asset Registry</h1>
          <p className="text-sm text-gray-500 mt-1">{assets.length} monitored battery assets</p>
        </div>

        {/* Summary bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {(["CRITICAL","URGENT","INVESTIGATE","NOMINAL"] as const).map((tier) => {
            const cls: Record<string,string> = {
              CRITICAL:"text-red-400 border-red-800/50 bg-red-950/30",
              URGENT:"text-orange-400 border-orange-800/50 bg-orange-950/30",
              INVESTIGATE:"text-yellow-400 border-yellow-800/50 bg-yellow-950/30",
              NOMINAL:"text-green-400 border-green-800/50 bg-green-950/30",
            };
            const count = assets.filter((a) => a.risk_tier === tier).length;
            return (
              <div key={tier} className={`border rounded-xl p-4 ${cls[tier]}`}>
                <div className="text-xs uppercase tracking-widest opacity-70 mb-1">{tier}</div>
                <div className="text-3xl font-bold">{count}</div>
              </div>
            );
          })}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          {loading ? (
            <div className="space-y-3">
              {Array.from({length: 8}).map((_,i) => (
                <div key={i} className="h-8 bg-gray-800 rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <AssetTable assets={assets} />
          )}
        </div>
      </div>
    </main>
  );
}
