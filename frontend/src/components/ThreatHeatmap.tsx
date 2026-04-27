"use client";
import { Asset } from "@/lib/api";

interface Props { assets: Asset[] }

const THREAT_COLOR: Record<string, string> = {
  normal:      "bg-green-500",
  portscan:    "bg-yellow-500",
  dos:         "bg-orange-500",
  ddos:        "bg-red-500",
  bruteforce:  "bg-purple-500",
  botnet:      "bg-pink-500",
  web_attack:  "bg-blue-500",
  suspicious:  "bg-amber-500",
};

export function ThreatHeatmap({ assets }: Props) {
  const COLS = 4;
  const rows: Asset[][] = [];
  for (let i = 0; i < assets.length; i += COLS) {
    rows.push(assets.slice(i, i + COLS));
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 mb-3">
        {Object.entries(THREAT_COLOR).slice(0, 5).map(([name, cls]) => (
          <span key={name} className="flex items-center gap-1 text-[10px] text-gray-500">
            <span className={`w-2 h-2 rounded-sm ${cls}`} /> {name}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-1.5">
        {assets.map((a) => {
          const opacity = Math.round((a.risk_score / 100) * 9) / 10;
          const color   = THREAT_COLOR[a.threat_type] ?? "bg-gray-600";
          return (
            <div key={a.asset_id} title={`${a.asset_id} — ${a.threat_type} — ${a.risk_score}`}
                 className={`${color} rounded aspect-square flex items-center justify-center
                             text-[9px] font-bold text-black/70 cursor-pointer
                             hover:scale-110 transition-transform duration-150`}
                 style={{ opacity: 0.3 + opacity * 0.7 }}>
              {Math.round(a.risk_score)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
