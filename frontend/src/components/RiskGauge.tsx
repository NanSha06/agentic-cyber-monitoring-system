"use client";
import React from "react";

interface Props {
  assetId:  string;
  location: string;
  score:    number;
  tier:     string;
  soh:      number;
}

const TIER_CONFIG: Record<string, { bg: string; ring: string; text: string; glow: string }> = {
  NOMINAL:     { bg: "bg-green-950",  ring: "ring-green-500",  text: "text-green-400",  glow: "shadow-green-900/50"  },
  INVESTIGATE: { bg: "bg-yellow-950", ring: "ring-yellow-500", text: "text-yellow-400", glow: "shadow-yellow-900/50" },
  URGENT:      { bg: "bg-orange-950", ring: "ring-orange-500", text: "text-orange-400", glow: "shadow-orange-900/50" },
  CRITICAL:    { bg: "bg-red-950",    ring: "ring-red-500",    text: "text-red-400",    glow: "shadow-red-900/60"   },
};

export function RiskGauge({ assetId, location, score, tier, soh }: Props) {
  const cfg = TIER_CONFIG[tier] ?? TIER_CONFIG.NOMINAL;
  const radius = 28;
  const circ   = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;

  return (
    <div
      aria-label={`${assetId} risk ${Math.round(score)} ${tier}`}
      className={`${cfg.bg} ring-1 ${cfg.ring} rounded-xl p-3 flex flex-col items-center gap-1
                     shadow-lg ${cfg.glow} hover:scale-105 transition-transform duration-200 cursor-pointer`}>
      {/* SVG Arc */}
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={radius} fill="none" stroke="#1f2937" strokeWidth="5" />
        <circle
          cx="36" cy="36" r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="5"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${cfg.text} transition-all duration-500`}
          style={{ transform: "rotate(-90deg)", transformOrigin: "center" }}
        />
        <text x="36" y="40" textAnchor="middle"
              className={`${cfg.text} text-sm font-bold`}
              fill="currentColor" fontSize="14" fontWeight="bold">
          {Math.round(score)}
        </text>
      </svg>
      <div className="text-xs font-semibold text-gray-200 text-center leading-tight">{location}</div>
      <div className={`text-[9px] font-bold tracking-widest ${cfg.text} uppercase`}>{tier}</div>
      <div className="text-[9px] text-gray-500">SOH {soh}%</div>
    </div>
  );
}
