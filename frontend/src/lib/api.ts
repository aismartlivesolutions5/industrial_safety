import type {
  OverviewData,
  AlertsResponse,
  Alert,
  PredictRequest,
  PredictResponse,
  ChatRequest,
  ChatResponse,
} from "@/types/api";

const BASE_URL = "/api";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options?: { method?: string; body?: unknown; params?: Record<string, string> }
): Promise<T> {
  const { method = "GET", body, params } = options || {};

  let url = `${BASE_URL}${path}`;
  if (params) url += `?${new URLSearchParams(params).toString()}`;

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Response transformers ──────────────────────────────────────────────────

function toSensorRow(a: Record<string, unknown>): Record<string, unknown> {
  return {
    timestamp: a.last_updated ?? a.timestamp,
    asset_id: a.asset_id,
    asset_type: a.asset_type ?? null,
    risk_label: a.risk_label ?? a.alert_level ?? "Normal",
    pressure_bar_g: a.boiler_pressure_bar,
    temp_c: a.boiler_temperature_c,
    lel_pct: a.lel_percent,
    voc_ppm: a.voc_ppm,
    vibration_rms_mm_s: a.vibration_rms,
    active_alarm_count: a.active_alarm_count,
  };
}

function toOverview(
  raw: Record<string, unknown>,
  assetRows: Record<string, unknown>[]
): OverviewData {
  const avgScore = Number(raw.avg_anomaly_score ?? 0);
  return {
    emergency_count: Number(raw.high_assets ?? 0),
    critical_count: Number(raw.critical_assets ?? 0),
    anomaly_rate_pct: Math.round(avgScore * 100),
    recent_alerts_count: Number(raw.active_anomalies ?? 0),
    top_alert_area: null,
    top_alert_plant: null,
    latest_dashboard_snapshot: assetRows[0] ?? undefined,
    latest_dashboard_rows: assetRows,
  };
}

function toAlerts(raw: Record<string, unknown>): AlertsResponse {
  const rawAlerts = (raw.alerts as Record<string, unknown>[]) ?? [];
  const alerts: Alert[] = rawAlerts.map((a) => ({
    timestamp: String(a.timestamp ?? ""),
    risk_label: String(a.risk_label ?? "Normal"),
    anomaly_label: String(a.alert_level ?? "Normal"),
    anomaly_score: Number(a.anomaly_score ?? 0),
    asset_id: String(a.asset_id ?? ""),
    plant_id: undefined,
    cluster_id: undefined,
    asset_type: undefined,
  }));
  return {
    count: alerts.length,
    alerts,
  };
}

function toAlertsFromHistory(raw: Record<string, unknown>): AlertsResponse {
  const rows = (raw.rows as Record<string, unknown>[]) ?? [];
  const alerts: Alert[] = rows.map((a) => ({
    timestamp: String(a.timestamp ?? a.start_time ?? ""),
    risk_label: String(a.risk_label ?? "Normal"),
    anomaly_label: String(a.alert_level ?? "Normal"),
    anomaly_score: Number(a.anomaly_score ?? 0),
    asset_id: String(a.asset_id ?? ""),
  }));
  return { count: alerts.length, alerts };
}

function toChat(question: string, raw: Record<string, unknown>): ChatResponse {
  return {
    question,
    sensor_snapshot: null,
    answer: {
      mode: "chatbot",
      summary: String(raw.answer ?? ""),
      risk_level: String(raw.related_alert_level ?? "Normal"),
      anomaly_status: String(raw.related_alert_level ?? "Normal"),
      top_drivers: [],
      recommended_actions: [],
    },
  };
}

// ── API surface ────────────────────────────────────────────────────────────

export const api = {
  getHealth: () =>
    request<{ status: string }>("/health"),

  getOverview: async () => {
    const [raw, topRaw] = await Promise.all([
      request<Record<string, unknown>>("/dashboard/overview"),
      request<Record<string, unknown>>("/dashboard/top_risky_assets?limit=6").catch(() => ({ assets: [] })),
    ]);

    const assetList = (topRaw.assets as Record<string, unknown>[]) ?? [];
    const assetRows = assetList.map(toSensorRow);

    return toOverview(raw, assetRows);
  },

  getRecentAlerts: async (windowMinutes = 60, topN = 20) => {
    const raw = await request<Record<string, unknown>>("/alerts/live", {
      params: { limit: String(topN) },
    });
    return toAlerts(raw);
  },

  getLast24hAlerts: async (topN = 20) => {
    const raw = await request<Record<string, unknown>>("/alerts/history", {
      params: { min_risk: "Watch" },
    });
    const result = toAlertsFromHistory(raw);
    result.alerts = result.alerts.slice(0, topN);
    result.count = result.alerts.length;
    return result;
  },

  predict: async (req: PredictRequest): Promise<PredictResponse> => {
    const p = req.payload as Record<string, unknown>;
    // Map simulator field names → backend field names + fill defaults
    const row = {
      boiler_pressure_bar: Number(p.pressure_bar_g ?? p.boiler_pressure_bar ?? 10.0),
      boiler_temperature_c: Number(p.temp_c ?? p.boiler_temperature_c ?? 160.0),
      voc_ppm: Number(p.voc_ppm ?? 20.0),
      nh3_ppm: Number(p.nh3_ppm ?? 2.0),
      h2s_ppm: Number(p.h2s_ppm ?? 1.0),
      lel_percent: Number(p.lel_pct ?? p.lel_percent ?? 5.0),
      vibration_rms: Number(p.vibration_rms_mm_s ?? p.vibration_rms ?? 1.5),
      active_alarm_count: Number(p.active_alarm_count ?? 0),
      days_since_last_maintenance: Number(p.days_since_last_maintenance ?? 10),
    };
    const raw = await request<Record<string, unknown>>("/explain/predict", {
      method: "POST",
      body: { ...row, return_shap: true, top_k: 4 },
    });
    // Map our backend's predict response to the expected shape
    const risk = (raw.risk as Record<string, unknown>) ?? {};
    const anomaly = (raw.anomaly as Record<string, unknown>) ?? {};
    const probas = (risk.probabilities as Record<string, number>) ?? {};
    return {
      risk: {
        risk_class: Number(risk.pred_class ?? risk.risk_class ?? 0),
        risk_label: String(risk.pred_label ?? risk.risk_label ?? "Normal"),
        probabilities: probas,
      },
      anomaly: {
        anomaly_label: String(anomaly.alert_level ?? "Normal"),
        is_anomaly: Number(anomaly.is_anomaly ?? 0),
        anomaly_score: Number(anomaly.anomaly_score ?? 0),
        decision_score: Number(anomaly.if_decision_score ?? 0),
        threshold: 0.72,
      },
    };
  },

  chat: async (req: ChatRequest): Promise<ChatResponse> => {
    const raw = await request<Record<string, unknown>>("/chatbot/ask", {
      method: "POST",
      body: { question: req.question },
    });
    return toChat(req.question, raw);
  },
};
