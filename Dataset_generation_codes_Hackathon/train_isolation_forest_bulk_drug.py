# train_isolation_forest_bulk_drug.py
# Isolation Forest anomaly detection for Bulk Drug Factory Safety dataset
# - Per-asset IsolationForest + RobustScaler
# - Rolling features for time-series realism
# - Produces anomaly_score + alert_level with per-asset calibrated thresholds
# - Saves models to: /teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/models

import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler


# ==============================
# PATHS
# ==============================
DATA_FILE = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data/bulk_drug_factory_safety_90d_1min.csv"
MODEL_DIR = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/models"
OUT_CSV   = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data/bulk_drug_factory_with_if_anomalies.csv"
os.makedirs(MODEL_DIR, exist_ok=True)

RANDOM_STATE = 2025

# If True: load existing model pkl per asset if available (fast threshold tuning)
LOAD_EXISTING_MODELS = True

# ==============================
# SENSOR COLUMNS
# ==============================
BASE_FEATURES = [
    "boiler_pressure_bar",
    "boiler_temperature_c",
    "voc_ppm",
    "nh3_ppm",
    "h2s_ppm",
    "lel_percent",
    "vibration_rms",
    "active_alarm_count",
    "days_since_last_maintenance",
]

# ==============================
# FEATURE ENGINEERING
# ==============================
ROLL_WINDOWS = [5, 15, 60]  # minutes
SLOPE_WINDOW = 15           # minutes

# ==============================
# ANOMALY SCORE NORMALIZATION
# ==============================
# More conservative than 5/95. This reduces over-triggering.
P_LOW  = 1
P_HIGH = 99

# ==============================
# ALERT CALIBRATION (PER-ASSET)
# ==============================
# These quantiles define how rare each alert is per asset.
# Example: CRITICAL at 99.8% => only top 0.2% by anomaly_score
Q_WATCH = 0.97     # top 3%
Q_HIGH  = 0.992    # top 0.8%
Q_CRIT  = 0.998    # top 0.2%

# persistence windows (minutes)
PERSIST_15 = 15
PERSIST_30 = 30


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(df["timestamp"])
    df["hour"] = ts.dt.hour.astype(np.int16)
    df["dayofweek"] = ts.dt.dayofweek.astype(np.int16)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0).astype(np.float32)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0).astype(np.float32)
    return df


def rolling_features(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("timestamp").copy()

    for col in BASE_FEATURES:
        x = g[col].astype(np.float32)

        for w in ROLL_WINDOWS:
            g[f"{col}_rm{w}"] = x.rolling(window=w, min_periods=1).mean().astype(np.float32)
            g[f"{col}_rs{w}"] = x.rolling(window=w, min_periods=2).std().fillna(0.0).astype(np.float32)

        g[f"{col}_slope{SLOPE_WINDOW}"] = (x - x.shift(SLOPE_WINDOW)) / float(SLOPE_WINDOW)
        g[f"{col}_slope{SLOPE_WINDOW}"] = g[f"{col}_slope{SLOPE_WINDOW}"].fillna(0.0).astype(np.float32)

    return g


def build_training_matrix(df: pd.DataFrame):
    df = add_time_features(df)
    df = df.groupby("asset_id", group_keys=False).apply(rolling_features)

    feature_cols = []
    feature_cols.extend(BASE_FEATURES)
    feature_cols.extend(["hour_sin", "hour_cos", "dayofweek"])

    for col in BASE_FEATURES:
        for w in ROLL_WINDOWS:
            feature_cols.append(f"{col}_rm{w}")
            feature_cols.append(f"{col}_rs{w}")
        feature_cols.append(f"{col}_slope{SLOPE_WINDOW}")

    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return df, feature_cols


def score_to_0_1(if_decision_scores: np.ndarray) -> np.ndarray:
    """
    IsolationForest decision_function: higher => more normal.
    We invert to get anomaly_score: higher => more anomalous.
    Uses conservative percentiles (P_LOW/P_HIGH).
    """
    lo = np.percentile(if_decision_scores, P_LOW)
    hi = np.percentile(if_decision_scores, P_HIGH)

    if hi - lo < 1e-6:
        return np.zeros_like(if_decision_scores, dtype=np.float32)

    norm = (if_decision_scores - lo) / (hi - lo)
    norm = np.clip(norm, 0, 1)
    return (1.0 - norm).astype(np.float32)


def compute_thresholds_from_quantiles(anom_scores: np.ndarray):
    """
    Compute per-asset thresholds from anomaly_score distribution.
    """
    t_watch = float(np.quantile(anom_scores, Q_WATCH))
    t_high  = float(np.quantile(anom_scores, Q_HIGH))
    t_crit  = float(np.quantile(anom_scores, Q_CRIT))
    # safety ordering
    t_high = max(t_high, t_watch + 1e-6)
    t_crit = max(t_crit, t_high + 1e-6)
    return {"watch": t_watch, "high": t_high, "crit": t_crit}


def derive_alert_levels(g: pd.DataFrame, thr: dict) -> pd.DataFrame:
    g = g.sort_values("timestamp").copy()

    T_WATCH = thr["watch"]
    T_HIGH  = thr["high"]
    T_CRIT  = thr["crit"]

    g["is_anomaly"] = (g["anomaly_score"] >= T_WATCH).astype(np.int16)

    # persistence counters
    g["anom_count_15m"] = g["is_anomaly"].rolling(PERSIST_15, min_periods=1).sum().astype(np.float32)
    g["anom_count_30m"] = g["is_anomaly"].rolling(PERSIST_30, min_periods=1).sum().astype(np.float32)

    level = np.full(len(g), "Normal", dtype=object)

    # escalation logic: critical requires either very high score or sustained anomalies
    crit_mask = (g["anomaly_score"] >= T_CRIT) | ((g["anom_count_30m"] >= 18) & (g["anomaly_score"] >= T_HIGH))
    high_mask = (~crit_mask) & ((g["anomaly_score"] >= T_HIGH) | (g["anom_count_30m"] >= 10))
    watch_mask = (~crit_mask) & (~high_mask) & (g["anomaly_score"] >= T_WATCH)

    level[watch_mask.values] = "Watch"
    level[high_mask.values]  = "High"
    level[crit_mask.values]  = "Critical"

    g["alert_level"] = level
    return g


def train_or_load_per_asset(df: pd.DataFrame, feature_cols: list):
    models = {}
    thresholds = {}

    meta = {
        "model_type": "IsolationForest (per-asset) + RobustScaler",
        "features": feature_cols,
        "base_features": BASE_FEATURES,
        "rolling_windows": ROLL_WINDOWS,
        "slope_window": SLOPE_WINDOW,
        "random_state": RANDOM_STATE,
        "score_norm_percentiles": [P_LOW, P_HIGH],
        "alert_quantiles": {"watch": Q_WATCH, "high": Q_HIGH, "crit": Q_CRIT},
        "persistence_minutes": {"15m": PERSIST_15, "30m": PERSIST_30},
    }

    for asset, g in df.groupby("asset_id"):
        model_path = os.path.join(MODEL_DIR, f"isoforest_{asset}.pkl")

        if LOAD_EXISTING_MODELS and os.path.exists(model_path):
            pack = joblib.load(model_path)
            models[asset] = {"scaler": pack["scaler"], "model": pack["model"], "contamination": pack.get("contamination", None)}
        else:
            X = g[feature_cols].astype(np.float32).values
            scaler = RobustScaler()
            Xs = scaler.fit_transform(X)

            asset_name = str(asset).upper()
            contamination = 0.002 if "BOILER" in asset_name else 0.005

            model = IsolationForest(
                n_estimators=300,
                max_samples="auto",
                contamination=contamination,
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
            model.fit(Xs)

            models[asset] = {"scaler": scaler, "model": model, "contamination": contamination}
            joblib.dump(
                {"asset_id": asset, "scaler": scaler, "model": model, "meta": meta, "contamination": contamination},
                model_path
            )

    with open(os.path.join(MODEL_DIR, "isoforest_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    return models, thresholds


def apply_models(df: pd.DataFrame, feature_cols: list, models: dict) -> pd.DataFrame:
    out = []
    threshold_book = {}

    for asset, g in df.groupby("asset_id"):
        g = g.copy()
        pack = models[asset]
        scaler = pack["scaler"]
        model  = pack["model"]

        X = g[feature_cols].astype(np.float32).values
        Xs = scaler.transform(X)

        raw = model.decision_function(Xs).astype(np.float32)
        g["if_decision_score"] = raw
        g["anomaly_score"] = score_to_0_1(raw)

        # per-asset calibrated thresholds
        thr = compute_thresholds_from_quantiles(g["anomaly_score"].values)
        threshold_book[str(asset)] = thr

        g = derive_alert_levels(g, thr)
        out.append(g)

    df_out = pd.concat(out, axis=0, ignore_index=True)
    df_out.sort_values(["timestamp", "asset_id"], inplace=True)

    with open(os.path.join(MODEL_DIR, "isoforest_thresholds.json"), "w") as f:
        json.dump(threshold_book, f, indent=2)

    return df_out


def main():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Dataset file not found: {DATA_FILE}")

    df = pd.read_csv(DATA_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df_feat, feature_cols = build_training_matrix(df)

    models, _ = train_or_load_per_asset(df_feat, feature_cols)

    df_scored = apply_models(df_feat, feature_cols, models)

    keep_cols = (
        ["timestamp", "asset_id"]
        + BASE_FEATURES
        + ["if_decision_score", "anomaly_score", "is_anomaly", "anom_count_15m", "anom_count_30m", "alert_level"]
    )
    keep_cols = [c for c in keep_cols if c in df_scored.columns]
    df_scored[keep_cols].to_csv(OUT_CSV, index=False)

    summary = {
        "out_csv": OUT_CSV,
        "model_dir": MODEL_DIR,
        "rows": int(len(df_scored)),
        "assets": sorted([str(x) for x in df_scored["asset_id"].unique().tolist()]),
        "alert_distribution": df_scored["alert_level"].value_counts().to_dict(),
    }
    with open(os.path.join(MODEL_DIR, "isoforest_run_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== DONE ===")
    print("Scored Dataset:", OUT_CSV)
    print("Models saved in:", MODEL_DIR)
    print("Example alert levels:", df_scored["alert_level"].value_counts().to_dict())


if __name__ == "__main__":
    main()
