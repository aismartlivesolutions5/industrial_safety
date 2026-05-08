# annotate_events_with_shap.py
# Adds SHAP-based explanations to high-risk events by merging events with MASTER rows (nearest timestamp)
# Fixes merge_asof sorting issue: MUST sort by [timestamp, asset_id]
# Loads XGB model from JSON (avoids BoosterModel pickle issues)

import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
import shap


# =========================
# PATHS
# =========================
MODEL_DIR = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/models"
DATA_DIR  = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data"

MODEL_JSON = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model.json")
MODEL_META = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model_metadata.json")

MASTER_CSV = os.path.join(DATA_DIR, "bulk_drug_factory_MASTER_scored.csv")
EVENTS_CSV = os.path.join(DATA_DIR, "high_risk_events.csv")

OUT_EVENTS_CSV     = os.path.join(DATA_DIR, "high_risk_events_with_shap.csv")
OUT_EVENTS_JSON    = os.path.join(DATA_DIR, "high_risk_events_with_shap.json")
OUT_SUMMARY_JSON   = os.path.join(DATA_DIR, "high_risk_events_shap_summary.json")

TIME_COL  = "timestamp"
ASSET_COL = "asset_id"

# merge tolerance (nearest row within this time gap)
MERGE_TOLERANCE = "5min"

TOP_K = 5  # top reasons per event


# =========================
# HELPERS
# =========================
def load_xgb_from_json():
    if not os.path.exists(MODEL_JSON):
        raise FileNotFoundError(f"Missing model json: {MODEL_JSON}")
    if not os.path.exists(MODEL_META):
        raise FileNotFoundError(f"Missing model metadata json: {MODEL_META}")

    with open(MODEL_META, "r") as f:
        meta = json.load(f)

    # metadata file format: {"name":..., "features":[...], "class_mapping": {...}, ...}
    features = meta.get("features", None)
    class_map = meta.get("class_mapping", {})

    if not features:
        raise ValueError("Model metadata missing 'features' list.")

    booster = xgb.Booster()
    booster.load_model(MODEL_JSON)

    return booster, features, meta, class_map


def ensure_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df[col] = pd.to_datetime(df[col], errors="coerce")
    bad = df[col].isna().sum()
    if bad > 0:
        df = df.dropna(subset=[col]).copy()
    return df


def merge_events_with_master(events: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    # IMPORTANT: merge_asof requires sorting by the "on" key first (timestamp),
    # not by asset first. So sort by [timestamp, asset_id].
    events = events.sort_values([TIME_COL, ASSET_COL]).reset_index(drop=True)
    master = master.sort_values([TIME_COL, ASSET_COL]).reset_index(drop=True)

    merged = pd.merge_asof(
        events,
        master,
        on=TIME_COL,
        by=ASSET_COL,
        direction="nearest",
        tolerance=pd.Timedelta(MERGE_TOLERANCE),
        suffixes=("_event", "")
    )
    return merged


def resolve_feature_frame(df: pd.DataFrame, features: list) -> pd.DataFrame:
    """
    After merging, sometimes master columns may get suffixes.
    This function maps required model feature names to actual columns in df.
    """
    col_map = {}
    for f in features:
        if f in df.columns:
            col_map[f] = f
        elif f"{f}_master" in df.columns:
            col_map[f] = f"{f}_master"
        elif f"{f}_m" in df.columns:
            col_map[f] = f"{f}_m"
        elif f"{f}_event" in df.columns:
            # fallback (not ideal, but avoids crash if you accidentally merged wrong)
            col_map[f] = f"{f}_event"
        else:
            col_map[f] = None

    missing = [k for k, v in col_map.items() if v is None]
    if missing:
        raise KeyError(
            f"These required model features are missing after merge: {missing}\n"
            f"Available columns sample: {list(df.columns)[:40]}"
        )

    X = df[[col_map[f] for f in features]].copy()
    X.columns = features
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)
    return X


def top_reasons(shap_row: np.ndarray, features: list, k: int = 5):
    idx = np.argsort(np.abs(shap_row))[::-1][:k]
    return [{"feature": features[i], "shap": float(shap_row[i])} for i in idx]


# =========================
# MAIN
# =========================
def main():
    print("=== Annotate Events With SHAP ===")
    print("Loading XGB JSON model + metadata...")
    booster, features, meta, class_map = load_xgb_from_json()

    if not os.path.exists(MASTER_CSV):
        raise FileNotFoundError(f"Missing MASTER CSV: {MASTER_CSV}")
    if not os.path.exists(EVENTS_CSV):
        raise FileNotFoundError(f"Missing EVENTS CSV: {EVENTS_CSV}")

    print("Loading events + master...")
    master = pd.read_csv(MASTER_CSV)
    events = pd.read_csv(EVENTS_CSV)

    if TIME_COL not in master.columns or ASSET_COL not in master.columns:
        raise KeyError(f"MASTER must contain columns: {TIME_COL}, {ASSET_COL}")

    if TIME_COL not in events.columns or ASSET_COL not in events.columns:
        raise KeyError(f"EVENTS must contain columns: {TIME_COL}, {ASSET_COL}")

    master = ensure_datetime(master, TIME_COL)
    events = ensure_datetime(events, TIME_COL)

    print("Merging events with MASTER rows (nearest timestamp)...")
    merged = merge_events_with_master(events, master)

    # how many failed to match (outside tolerance)
    # if timestamp match fails, merged master-side columns become NaN
    X = resolve_feature_frame(merged, features)
    unmatched = X.isna().all(axis=1).sum()
    if unmatched > 0:
        print(f"WARNING: {unmatched} events could not match MASTER within tolerance={MERGE_TOLERANCE}")

    # Predict (probabilities)
    dmat = xgb.DMatrix(X, feature_names=features)
    proba = booster.predict(dmat)
    if proba.ndim == 1:
        # binary fallback
        proba = np.vstack([1 - proba, proba]).T

    pred_class = np.argmax(proba, axis=1)
    pred_prob  = proba[np.arange(len(proba)), pred_class]

    def map_label(c):
        # class_map keys might be "0","1"... in json
        return class_map.get(str(int(c)), class_map.get(int(c), str(int(c))))

    merged["xgb_pred_class"] = pred_class.astype(int)
    merged["xgb_pred_label"] = [map_label(c) for c in pred_class]
    merged["xgb_pred_prob"] = pred_prob.astype(np.float32)

    # SHAP
    print("Computing SHAP values for merged events...")
    explainer = shap.TreeExplainer(booster)
    shap_vals = explainer.shap_values(X)

    # Normalize shap outputs into list[class] -> array[n, features]
    if isinstance(shap_vals, list):
        shap_by_class = shap_vals
    else:
        sv = np.asarray(shap_vals)
        if sv.ndim == 3:
            shap_by_class = [sv[:, :, c] for c in range(sv.shape[2])]
        else:
            shap_by_class = [sv]

    # Build per-event top reasons
    reasons = []
    for i in range(len(X)):
        c = int(pred_class[i])
        if c < len(shap_by_class):
            shap_row = np.asarray(shap_by_class[c][i], dtype=float)
        else:
            shap_row = np.asarray(shap_by_class[0][i], dtype=float)

        reasons.append(top_reasons(shap_row, features, k=TOP_K))

    merged["shap_top_reasons_json"] = [json.dumps(r, ensure_ascii=False) for r in reasons]

    # Save CSV
    keep_cols = (
        [TIME_COL, ASSET_COL] +
        ["xgb_pred_class", "xgb_pred_label", "xgb_pred_prob", "shap_top_reasons_json"]
    )
    # also keep useful event columns if present
    for c in ["alert_level", "risk_label", "event_type", "event_severity"]:
        if c in merged.columns and c not in keep_cols:
            keep_cols.insert(2, c)

    merged[keep_cols].to_csv(OUT_EVENTS_CSV, index=False)

    # Save JSON (full structured)
    out_json = merged[keep_cols].copy()
    out_json["shap_top_reasons"] = reasons
    out_json = out_json.drop(columns=["shap_top_reasons_json"])
    out_json.to_json(OUT_EVENTS_JSON, orient="records", indent=2)

    # Summary (counts + mean abs shap over events)
    # compute event-weighted shap for predicted class
    abs_sum = np.zeros(len(features), dtype=float)
    for i in range(len(X)):
        c = int(pred_class[i])
        arr = np.asarray(shap_by_class[c][i] if c < len(shap_by_class) else shap_by_class[0][i], dtype=float)
        abs_sum += np.abs(arr)
    mean_abs = abs_sum / max(len(X), 1)

    summary = {
        "num_events": int(len(X)),
        "merge_tolerance": MERGE_TOLERANCE,
        "topk": TOP_K,
        "pred_label_distribution": pd.Series(merged["xgb_pred_label"]).value_counts().to_dict(),
        "global_mean_abs_shap_on_events": {features[i]: float(mean_abs[i]) for i in range(len(features))}
    }

    with open(OUT_SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== DONE ===")
    print("Annotated Events CSV :", OUT_EVENTS_CSV)
    print("Annotated Events JSON:", OUT_EVENTS_JSON)
    print("Summary JSON         :", OUT_SUMMARY_JSON)
    print("Pred label dist      :", summary["pred_label_distribution"])


if __name__ == "__main__":
    main()
