// Types for the Industrial Safety API responses

export interface OverviewData {
  dashboard_meta_columns?: string[];
  dashboard_feature_columns?: string[];
  emergency_count: number;
  critical_count: number;
  anomaly_rate_pct: number;
  recent_alerts_count: number;
  top_alert_area?: string | null;
  top_alert_plant?: string | null;
  latest_dashboard_snapshot?: Record<string, unknown> | null;
  latest_dashboard_rows?: Record<string, unknown>[];
}

export interface Alert {
  timestamp: string;
  risk_label: string;
  anomaly_label: string;
  anomaly_score: number;
  cluster_id?: string;
  plant_id?: string;
  asset_id?: string;
  asset_type?: string;
}

export interface AlertsResponse {
  dashboard_meta_columns?: string[];
  dashboard_feature_columns?: string[];
  window_minutes?: number;
  count: number;
  filters?: {
    plant_id?: string | null;
    asset_id?: string | null;
    cluster_id?: string | null;
  };
  alerts: Alert[];
}

export interface PredictRequest {
  payload: Record<string, unknown>;
  explain?: boolean;
}

export interface PredictResponse {
  dashboard_meta_columns?: string[];
  dashboard_feature_columns?: string[];
  sensor_snapshot?: Record<string, unknown>;
  risk: {
    risk_class: number;
    risk_label: string;
    probabilities: Record<string, number>;
  };
  anomaly: {
    anomaly_label: string;
    is_anomaly: number;
    anomaly_score: number;
    decision_score: number;
    threshold: number;
  };
  explanations?: {
    mode: string;
    risk_label: string;
    top_reasons: Array<{
      feature: string;
      value: unknown;
      impact: number;
    }>;
  };
}

export interface ChatRequest {
  question: string;
  payload?: Record<string, unknown>;
}

export interface ChatResponse {
  dashboard_meta_columns?: string[];
  dashboard_feature_columns?: string[];
  question: string;
  sensor_snapshot?: Record<string, unknown> | null;
  answer: {
    mode: string;
    summary: string;
    risk_level: string;
    anomaly_status: string;
    top_drivers: unknown[];
    recommended_actions: unknown[];
  };
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  data?: ChatResponse["answer"];
  sensorSnapshot?: Record<string, unknown> | null;
  timestamp: Date;
}
