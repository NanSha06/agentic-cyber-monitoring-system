"use client";
import { Asset } from "@/lib/api";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

interface Props { assets: Asset[] }

const TIER_BADGE: Record<string, string> = {
  NOMINAL:     "bg-green-900/60  text-green-400  border border-green-700",
  INVESTIGATE: "bg-yellow-900/60 text-yellow-400 border border-yellow-700",
  URGENT:      "bg-orange-900/60 text-orange-400 border border-orange-700",
  CRITICAL:    "bg-red-900/60    text-red-400    border border-red-700 animate-pulse",
};

export function AssetTable({ assets }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-widest text-gray-600 border-b border-gray-800">
            {["Asset", "Location", "SOH", "SOC", "Temp", "Voltage", "Risk", "Tier", "Threat", "RUL", ""].map((h) => (
              <th key={h} className="text-left py-2 px-3 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => (
            <tr key={a.asset_id}
                className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
              <td className="py-2.5 px-3 font-mono text-indigo-300 text-xs">{a.asset_id}</td>
              <td className="py-2.5 px-3 text-gray-300">{a.location}</td>
              <td className={`py-2.5 px-3 font-semibold ${a.soh < 70 ? "text-red-400" : "text-green-400"}`}>
                {a.soh}%
              </td>
              <td className="py-2.5 px-3 text-gray-400">{a.soc}%</td>
              <td className={`py-2.5 px-3 ${a.temp > 40 ? "text-orange-400" : "text-gray-400"}`}>
                {a.temp}°C
              </td>
              <td className="py-2.5 px-3 text-gray-400">{a.voltage}V</td>
              <td className="py-2.5 px-3 font-bold text-white">{a.risk_score}</td>
              <td className="py-2.5 px-3">
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${TIER_BADGE[a.risk_tier] ?? ""}`}>
                  {a.risk_tier}
                </span>
              </td>
              <td className="py-2.5 px-3 text-gray-400 text-xs">{a.threat_type}</td>
              <td className="py-2.5 px-3 text-gray-400">{a.rul_cycles}</td>
              <td className="py-2.5 px-3">
                <Link href={`/assets/${a.asset_id}`}
                      className="text-gray-600 hover:text-indigo-400 transition-colors">
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
