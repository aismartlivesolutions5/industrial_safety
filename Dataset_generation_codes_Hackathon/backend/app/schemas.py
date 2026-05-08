from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ----------------------------
# Generic / common responses
# ----------------------------
class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    version: str


class MessageResponse(BaseModel):
    message: str


# ----------------------------
# Meta / model info
# ----------------------------
class XGBMetaResponse(BaseModel):
    model_json: str
    metadata: str
    features: List[str]
    class_mapping: Dict[str, str]
    trained_at: Optional[str] = None
    xgboost_version: Optional[str] = None


class ISOForestMetaResponse(BaseModel):
    model_dir: str
    assets: List[str]


class ModelsMetaResponse(BaseModel):
    xgb: XGBMetaResponse
    isolation_forest: ISOForestMetaResponse


class ThresholdsResponse(BaseModel):
    threshold_config: Dict[str, Any]


# ----------------------------
# Dashboard
# ----------------------------
class DashboardOverviewResponse(BaseModel):
    total_assets: int
    normal_assets: int
    watch_assets: int
    high_assets: int
    critical_assets: int
    active_anomalies: int
    avg_anomaly_score: float
    avg_risk_score: float
    maintenance_due_assets: int
    last_updated: Optional[str] = None


class DashboardTrendPoint(BaseModel):
    timestamp: str
    avg_anomaly_score: float
    avg_risk_score: float
    critical_count: int
    high_count: int
    watch_count: int


class DashboardTrendResponse(BaseModel):
    rows: List[DashboardTrendPoint]
    count: int


# ----------------------------
# Assets
# ----------------------------
class AssetListItem(BaseModel):
    asset_id: str
    asset_type: Optional[str] = None
    alert_level: Optional[str] = None
    risk_label: Optional[str] = None
    anomaly_score: Optional[float] = None
    risk_score: Optional[float] = None
    last_updated: Optional[str] = None


class AssetListResponse(BaseModel):
    assets: List[AssetListItem]
    count: int


class AssetLatestResponse(BaseModel):
    asset_id: str
    timestamp: str
    alert_level: Optional[str] = None
    risk_label: Optional[str] = None
    anomaly_score: Optional[float] = None
    risk_score: Optional[float] = None

    boiler_pressure_bar: Optional[float] = None
    boiler_temperature_c: Optional[float] = None
    voc_ppm: Optional[float] = None
    nh3_ppm: Optional[float] = None
    h2s_ppm: Optional[float] = None
    lel_percent: Optional[float] = None
    vibration_rms: Optional[float] = None
    active_alarm_count: Optional[float] = None
    days_since_last_maintenance: Optional[float] = None


class TimeSeriesRow(BaseModel):
    timestamp: str
    asset_id: Optional[str] = None

    boiler_pressure_bar: Optional[float] = None
    boiler_temperature_c: Optional[float] = None
    voc_ppm: Optional[float] = None
    nh3_ppm: Optional[float] = None
    h2s_ppm: Optional[float] = None
    lel_percent: Optional[float] = None
    vibration_rms: Optional[float] = None
    active_alarm_count: Optional[float] = None
    days_since_last_maintenance: Optional[float] = None

    anomaly_score: Optional[float] = None
    risk_score: Optional[float] = None
    alert_level: Optional[str] = None
    risk_label: Optional[str] = None


class AssetTimeSeriesResponse(BaseModel):
    rows: List[TimeSeriesRow]
    count: int


# ----------------------------
# Alerts
# ----------------------------
class AlertItem(BaseModel):
    alert_id: str
    asset_id: str
    timestamp: str
    alert_level: str
    risk_label: Optional[str] = None
    anomaly_score: Optional[float] = None
    risk_score: Optional[float] = None
    reason: str
    is_acknowledged: bool = False


class LiveAlertsResponse(BaseModel):
    alerts: List[AlertItem]
    count: int
    unread_count: int
    last_updated: Optional[str] = None


# ----------------------------
# Chatbot
# ----------------------------
class ChatbotSummaryRequest(BaseModel):
    mode: str = Field(default="plant_overview", examples=["plant_overview", "shift_handover"])


class ChatbotSummaryResponse(BaseModel):
    summary: str


class ChatbotAskRequest(BaseModel):
    question: str = Field(..., examples=["Why is BOILER_A1 critical?"])


class ChatbotAskResponse(BaseModel):
    answer: str
    related_asset: Optional[str] = None
    related_alert_level: Optional[str] = None


# ----------------------------
# Prediction / anomaly / SHAP
# ----------------------------
class RiskRequest(BaseModel):
    asset_id: str = Field(..., examples=["BOILER_A1"])
    boiler_pressure_bar: float
    boiler_temperature_c: float
    voc_ppm: float
    nh3_ppm: float
    h2s_ppm: float
    lel_percent: float
    vibration_rms: float
    active_alarm_count: float
    days_since_last_maintenance: float
    return_shap: bool = False
    top_k: int = 4


class RiskPredictionResponse(BaseModel):
    asset_id: str
    pred_class: int
    pred_label: str
    proba: List[float]
    top_reasons: Optional[List[Dict[str, Any]]] = None
    top_reasons_error: Optional[str] = None


class WindowRow(BaseModel):
    timestamp: str
    boiler_pressure_bar: float
    boiler_temperature_c: float
    voc_ppm: float
    nh3_ppm: float
    h2s_ppm: float
    lel_percent: float
    vibration_rms: float
    active_alarm_count: float
    days_since_last_maintenance: float


class AnomalyRequest(BaseModel):
    asset_id: str
    rows: List[WindowRow]
    top_k: int = 4


class AnomalyDetectionResponse(BaseModel):
    asset_id: str
    timestamp: str
    if_decision_score: float
    anomaly_score: float
    is_anomaly: int
    anom_count_15m: int
    anom_count_30m: int
    alert_level: str


class ShapRequest(BaseModel):
    row: Dict[str, float]
    top_k: int = 4


class ShapExplainResponse(BaseModel):
    pred_class: int
    proba: List[float]
    top_reasons: List[Dict[str, Any]]


# ----------------------------
# Daily analytics / events / audit
# ----------------------------
class DailyAnalyticsResponse(BaseModel):
    rows: List[Dict[str, Any]]
    count: int


class HighRiskEventsResponse(BaseModel):
    rows: List[Dict[str, Any]]
    count: int


class AuditReportResponse(BaseModel):
    range: Dict[str, Optional[str]]
    rows: int
    alert_distribution: Dict[str, float]
    risk_distribution: Dict[str, float]
    top_assets_by_critical_minutes: Dict[str, int]
    global_shap: Optional[Dict[str, Any]] = None