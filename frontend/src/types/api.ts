export interface DashboardOverview {
  total_assets: number;
  normal_assets: number;
  watch_assets: number;
  high_assets: number;
  critical_assets: number;
  active_anomalies: number;
  avg_anomaly_score: number;
  avg_risk_score: number;
  maintenance_due_assets: number;
  last_updated: string;
}

export interface RiskTrendRow {
  timestamp: string;
  avg_anomaly_score: number;
  avg_risk_score: number;
  critical_count: number;
  high_count: number;
  watch_count: number;
}

export interface TopRiskyAsset {
  asset_id: string;
  alert_level: string;
  risk_label: string;
  anomaly_score: number;
  risk_score: number;
  last_updated: string;
}

export interface Asset {
  asset_id: string;
  asset_type: string;
  alert_level: string;
  risk_label: string;
  anomaly_score: number;
  risk_score: number;
  last_updated: string;
}

export interface AssetLatest {
  asset_id: string;
  timestamp: string;
  alert_level: string;
  risk_label: string;
  anomaly_score: number;
  risk_score: number;
  boiler_pressure_bar: number;
  boiler_temperature_c: number;
  voc_ppm: number;
  nh3_ppm: number;
  h2s_ppm: number;
  lel_percent: number;
  vibration_rms: number;
  active_alarm_count: number;
  days_since_last_maintenance: number;
}

export interface TimeseriesPoint {
  timestamp: string;
  boiler_pressure_bar: number;
  boiler_temperature_c: number;
  voc_ppm: number;
  nh3_ppm: number;
  h2s_ppm: number;
  lel_percent: number;
  vibration_rms: number;
  anomaly_score: number;
  risk_score: number;
}

export interface LiveAlert {
  alert_id: string;
  asset_id: string;
  timestamp: string;
  alert_level: string;
  risk_label: string;
  anomaly_score: number;
  risk_score: number;
  reason: string;
  is_acknowledged: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ExplainabilityData {
  asset_id: string;
  timestamp: string;
  features: Record<string, number>;
  [key: string]: unknown;
}
