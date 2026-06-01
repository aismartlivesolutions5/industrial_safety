import type {
  DashboardOverview,
  RiskTrendRow,
  TopRiskyAsset,
  Asset,
  AssetLatest,
  TimeseriesPoint,
  LiveAlert,
  ExplainabilityData,
} from "@/types/api";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || "https://industrial-safety-1-ieju.onrender.com";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const getFallbackData = (path: string): unknown => {
  if (path === "/dashboard/overview") {
    return {
      total_assets: 0,
      normal_assets: 0,
      watch_assets: 0,
      high_assets: 0,
      critical_assets: 0,
      active_anomalies: 0,
      avg_anomaly_score: 0,
      avg_risk_score: 0,
      maintenance_due_assets: 0,
      last_updated: new Date().toISOString(),
    };
  }

  if (path === "/dashboard/risk_trend" || path === "/dashboard/top_risky_assets" || path === "/alerts/live") {
    return [];
  }

  if (path === "/chatbot/summary") {
    return { summary: "Safety summary is temporarily unavailable. Please retry in a few seconds." };
  }

  return null;
};

async function proxyRequest<T>(
  path: string,
  options?: { method?: string; body?: unknown }
): Promise<T> {
  const method = options?.method || "GET";
  const maxAttempts = 2;
  let lastMessage = "Request failed";

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers: { "Content-Type": "application/json" },
        ...(options?.body ? { body: JSON.stringify(options.body) } : {}),
      });

      if (res.ok) return (await res.json()) as T;

      lastMessage = `HTTP ${res.status}`;
      const isTransient = [502, 503, 504].includes(res.status);
      if (!isTransient || attempt === maxAttempts) break;
    } catch (err) {
      lastMessage = err instanceof Error ? err.message : "Network error";
      if (attempt === maxAttempts) break;
    }

    await sleep(1200 * attempt);
  }

  const fallback = getFallbackData(path);
  if (fallback !== null) {
    console.warn(`Using fallback data for ${path}: ${lastMessage}`);
    return fallback as T;
  }

  throw new Error(lastMessage);
}

const extractArray = <T>(value: unknown, keys: string[]): T[] => {
  if (Array.isArray(value)) return value as T[];
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    for (const key of keys) {
      if (Array.isArray(record[key])) return record[key] as T[];
    }
  }
  return [];
};

// Dashboard
export const fetchDashboardOverview = () =>
  proxyRequest<DashboardOverview>("/dashboard/overview");

export const fetchRiskTrend = async () => {
  const res = await proxyRequest<unknown>("/dashboard/risk_trend");
  return extractArray<RiskTrendRow>(res, ["rows", "data"]);
};

export const fetchTopRiskyAssets = async () => {
  const res = await proxyRequest<unknown>("/dashboard/top_risky_assets");
  return extractArray<TopRiskyAsset>(res, ["assets", "rows", "data"]);
};

export const fetchLiveAlerts = async () => {
  const res = await proxyRequest<unknown>("/alerts/live");
  return extractArray<LiveAlert>(res, ["alerts", "rows", "data"]);
};

// Assets
export const fetchAssets = async () => {
  const res = await proxyRequest<unknown>("/assets");
  return extractArray<Asset>(res, ["assets", "rows", "data"]);
};

export const fetchAssetLatest = (assetId: string) =>
  proxyRequest<AssetLatest>(`/assets/${assetId}/latest`);

export const fetchAssetTimeseries = async (assetId: string, minutes = 60) => {
  const res = await proxyRequest<unknown>(`/assets/${assetId}/timeseries?minutes=${minutes}`);
  return extractArray<TimeseriesPoint>(res, ["rows", "points", "data"]);
};

// Explainability
export const fetchExplainability = (assetId: string) =>
  proxyRequest<ExplainabilityData>(`/explain/asset/${assetId}/latest`);

// Chatbot
export const fetchChatbotSummary = () =>
  proxyRequest<{ summary: string }>("/chatbot/summary", {
    method: "POST",
    body: { mode: "plant_overview" },
  });

export const askChatbot = (question: string) =>
  proxyRequest<{ answer: string }>("/chatbot/ask", {
    method: "POST",
    body: { question },
  });
