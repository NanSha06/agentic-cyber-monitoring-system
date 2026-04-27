// frontend/src/lib/ws.ts
// WebSocket hook for live risk score streaming

import { useEffect, useRef, useState } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export interface RiskUpdate {
  asset_id:   string;
  risk_score: number;
  risk_tier:  string;
  timestamp:  string;
}

export function useRiskStream() {
  const [updates, setUpdates] = useState<Record<string, RiskUpdate>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      try {
        const ws = new WebSocket(`${WS_URL}/ws/risk-stream`);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onclose = () => {
          setConnected(false);
          retryTimeout = setTimeout(connect, 3000);
        };
        ws.onerror = () => ws.close();

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            if (msg.type === "risk_update") {
              setUpdates((prev) => {
                const next = { ...prev };
                for (const upd of msg.data as RiskUpdate[]) {
                  next[upd.asset_id] = upd;
                }
                return next;
              });
            }
          } catch {}
        };
      } catch {}
    }

    connect();
    return () => {
      wsRef.current?.close();
      clearTimeout(retryTimeout);
    };
  }, []);

  return { updates, connected };
}
