// frontend/src/lib/api.ts
// Typed API client for the FastAPI backend

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Asset {
  asset_id: string;
  location: string;
  soh: number;
  soc: number;
  temp: number;
  voltage: number;
  risk_score: number;
  risk_tier: "NOMINAL" | "INVESTIGATE" | "URGENT" | "CRITICAL";
  rul_cycles: number;
  threat_type: string;
  last_seen: string;
  status: string;
}

export interface Alert {
  alert_id: string;
  asset_id: string;
  risk_score: number;
  risk_tier: string;
  threat_type: string;
  description: string;
  timestamp: string;
  resolved: boolean;
  explanation_available: boolean;
}

export interface Explanation {
  alert_id: string;
  asset_id: string;
  risk_score: number;
  contributions: { feature: string; weight: number }[];
  human_readable: string;
}

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  // Assets
  getAssets: ()                => fetchJSON<Asset[]>("/assets/"),
  getAsset:  (id: string)      => fetchJSON<Asset>(`/assets/${id}`),
  getHistory: (id: string, h = 24) => fetchJSON<{asset_id: string; history: any[]}>(`/assets/${id}/history?hours=${h}`),

  // Alerts
  getAlerts:  (resolved = false) => fetchJSON<Alert[]>(`/alerts/?resolved=${resolved}`),
  getAlert:   (id: string)       => fetchJSON<Alert>(`/alerts/${id}`),
  resolveAlert: (id: string)     => fetchJSON<any>(`/alerts/${id}/resolve`, { method: "POST" }),

  // Explanations
  getExplanation: (alertId: string) => fetchJSON<Explanation>(`/explain/${alertId}`),

  // Health
  health: () => fetchJSON<any>("/health/"),
};
