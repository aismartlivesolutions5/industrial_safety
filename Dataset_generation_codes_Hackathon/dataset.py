# train_bulk_drug_safety_xgb.py
# -- coding: utf-8 --
"""
Bulk Drug Factory Safety - XGBoost Risk Classifier (CPU) + Robustness + SHAP

Updated per your request:
- Saves model + json + metadata + shap into:
  /teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/models
"""

import os, json, joblib, shap, logging, warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple, Dict

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("bulk_drug_train_xgb")

# ===================== CONFIG =====================
RANDOM_STATE = 2025

# Your dataset file (same folder as script OR set absolute path)
DATA_FILE = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data/bulk_drug_factory_safety_90d_1min.csv"

# Save folder you provided
MODEL_DIR = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/models"
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_FILE = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model.pkl")
MODEL_JSON = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model.json")
META_JSON  = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model_metadata.json")
SHAP_JSON  = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model_shap.json")

ES_ROUNDS = 100
N_SEARCH_ITERS = 20

# ---------- Noise/Augmentation (TRAIN ONLY) ----------
AUGMENT_FACTOR         = 2
MULT_NOISE_STD         = 0.12
ADD_NOISE_STD          = 0.08
GLOBAL_SHIFT_RANGE     = (-0.04, 0.06)
GLOBAL_SCALE_RANGE     = (0.92, 1.10)
FEATURE_DROPOUT_P      = 0.015
SPIKE_PROB             = 0.008
SPIKE_MULT_RANGE       = (1.4, 2.6)

# Robustness test (on test split copy)
ROB_MULT_NOISE_STD     = 0.10
ROB_ADD_NOISE_STD      = 0.06
ROB_GLOBAL_SHIFT_RANGE = (0.02, 0.08)
ROB_GLOBAL_SCALE_RANGE = (0.95, 1.08)
# -----------------------------------------------------

# NEW SENSOR + CONTEXT FEATURES
FEATURES = [
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

CLASS_MAP = {0: "Normal", 1: "Watch", 2: "High Risk", 3: "Critical"}

NONNEG_HINTS = [
    "pressure", "temp", "voc", "nh3", "h2s", "lel",
    "vibration", "alarm", "days", "count", "ppm", "percent", "bar", "c"
]

# ===================== THRESHOLD LABELING (PoC defaults) =====================
TH = {
    "voc_ppm":   {"watch": 50,  "high": 100, "critical": 300},
    "nh3_ppm":   {"watch": 25,  "high": 50,  "critical": 100},
    "h2s_ppm":   {"watch": 10,  "high": 20,  "critical": 50},
    "lel_percent": {"watch": 5, "high": 10,  "critical": 20},

    "vibration_rms": {"watch": 2.8, "high": 4.5, "critical": 7.1},
    "active_alarm_count": {"watch": 2, "high": 4, "critical": 6},
    "days_since_last_maintenance": {"watch": 30, "high": 60, "critical": 90},

    # Baseline-relative logic (since design limits are not present in dataset)
    "boiler_pressure_bar": {"watch": 1.05, "high": 1.10, "critical": 1.15, "mode": "ratio_vs_baseline"},
    "boiler_temperature_c": {"watch": 10,  "high": 20,  "critical": 30,   "mode": "delta_vs_baseline"},
}

def label_from_thresholds(df: pd.DataFrame) -> pd.Series:
    """
    Create 4-class labels using thresholds:
    - 3 (Critical): any 'critical' breach
    - 2 (High Risk): any 'high' breach
    - 1 (Watch): any 'watch' breach
    - 0 (Normal): none
    Boiler:
      - pressure uses ratio vs baseline median
      - temperature uses delta vs baseline median
    """
    if "asset_id" in df.columns:
        bp_base = df.groupby("asset_id")["boiler_pressure_bar"].transform("median")
        bt_base = df.groupby("asset_id")["boiler_temperature_c"].transform("median")
    else:
        bp_base = df["boiler_pressure_bar"].median()
        bt_base = df["boiler_temperature_c"].median()

    pressure_ratio = df["boiler_pressure_bar"] / (bp_base + 1e-9)
    temp_delta = df["boiler_temperature_c"] - bt_base

    y = np.zeros(len(df), dtype=np.int32)

    def upgrade(mask, level):
        nonlocal y
        y = np.where(mask, np.maximum(y, level), y)

    # Watch
    upgrade(df["voc_ppm"] >= TH["voc_ppm"]["watch"], 1)
    upgrade(df["nh3_ppm"] >= TH["nh3_ppm"]["watch"], 1)
    upgrade(df["h2s_ppm"] >= TH["h2s_ppm"]["watch"], 1)
    upgrade(df["lel_percent"] >= TH["lel_percent"]["watch"], 1)
    upgrade(df["vibration_rms"] >= TH["vibration_rms"]["watch"], 1)
    upgrade(df["active_alarm_count"] >= TH["active_alarm_count"]["watch"], 1)
    upgrade(df["days_since_last_maintenance"] >= TH["days_since_last_maintenance"]["watch"], 1)
    upgrade(pressure_ratio >= TH["boiler_pressure_bar"]["watch"], 1)
    upgrade(temp_delta >= TH["boiler_temperature_c"]["watch"], 1)

    # High Risk
    upgrade(df["voc_ppm"] >= TH["voc_ppm"]["high"], 2)
    upgrade(df["nh3_ppm"] >= TH["nh3_ppm"]["high"], 2)
    upgrade(df["h2s_ppm"] >= TH["h2s_ppm"]["high"], 2)
    upgrade(df["lel_percent"] >= TH["lel_percent"]["high"], 2)
    upgrade(df["vibration_rms"] >= TH["vibration_rms"]["high"], 2)
    upgrade(df["active_alarm_count"] >= TH["active_alarm_count"]["high"], 2)
    upgrade(df["days_since_last_maintenance"] >= TH["days_since_last_maintenance"]["high"], 2)
    upgrade(pressure_ratio >= TH["boiler_pressure_bar"]["high"], 2)
    upgrade(temp_delta >= TH["boiler_temperature_c"]["high"], 2)

    # Critical
    upgrade(df["voc_ppm"] >= TH["voc_ppm"]["critical"], 3)
    upgrade(df["nh3_ppm"] >= TH["nh3_ppm"]["critical"], 3)
    upgrade(df["h2s_ppm"] >= TH["h2s_ppm"]["critical"], 3)
    upgrade(df["lel_percent"] >= TH["lel_percent"]["critical"], 3)
    upgrade(df["vibration_rms"] >= TH["vibration_rms"]["critical"], 3)
    upgrade(df["active_alarm_count"] >= TH["active_alarm_count"]["critical"], 3)
    upgrade(df["days_since_last_maintenance"] >= TH["days_since_last_maintenance"]["critical"], 3)
    upgrade(pressure_ratio >= TH["boiler_pressure_bar"]["critical"], 3)
    upgrade(temp_delta >= TH["boiler_temperature_c"]["critical"], 3)

    return pd.Series(y, name="label")

# ===================== Split & Utils =====================
def time_based_split(X, y, ts, test_ratio=0.2, val_ratio_within_train=0.2):
    order = np.argsort(pd.to_datetime(ts).values)
    X, y, ts = X.iloc[order], y.iloc[order], ts.iloc[order]
    n = len(X)
    n_test = int(n * test_ratio)

    X_trv, y_trv = X.iloc[: n - n_test], y.iloc[: n - n_test]
    X_te,  y_te  = X.iloc[n - n_test :], y.iloc[n - n_test :]

    n_val = int(len(X_trv) * val_ratio_within_train)
    X_tr, y_tr = X_trv.iloc[: len(X_trv) - n_val], y_trv.iloc[: len(X_trv) - n_val]
    X_val, y_val = X_trv.iloc[len(X_trv) - n_val :], y_trv.iloc[len(X_trv) - n_val :]
    return X_tr, y_tr, X_val, y_val, X_te, y_te

def _clamp_nonneg(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        cl = c.lower()
        if any(k in cl for k in NONNEG_HINTS):
            df[c] = np.maximum(df[c], 0.0)
    return df

def augment_with_noise(X: pd.DataFrame, y: pd.Series, factor: int, seed: int) -> Tuple[pd.DataFrame, pd.Series]:
    if factor <= 0:
        return X, y
    rng = np.random.default_rng(seed + 777)
    Xs = [X]
    ys = [y]

    X_np = X.values.astype(np.float32)
    n, d = X_np.shape
    feat_std = np.std(X_np, axis=0, ddof=1)
    feat_std[feat_std == 0] = 1.0

    for _ in range(factor):
        Z = X_np.copy()
        Z *= rng.normal(loc=1.0, scale=MULT_NOISE_STD, size=(n, d)).astype(np.float32)
        Z += rng.normal(loc=0.0, scale=ADD_NOISE_STD, size=(n, d)).astype(np.float32) * feat_std

        scales = rng.uniform(GLOBAL_SCALE_RANGE[0], GLOBAL_SCALE_RANGE[1], size=(n, 1)).astype(np.float32)
        shifts = rng.uniform(GLOBAL_SHIFT_RANGE[0], GLOBAL_SHIFT_RANGE[1], size=(n, 1)).astype(np.float32)
        Z = Z * scales + Z * shifts

        spikes = rng.random((n, d)) < SPIKE_PROB
        spike_mult = rng.uniform(SPIKE_MULT_RANGE[0], SPIKE_MULT_RANGE[1], size=(n, d)).astype(np.float32)
        Z = np.where(spikes, Z * spike_mult, Z)

        drops = rng.random((n, d)) < FEATURE_DROPOUT_P
        Z = np.where(drops, 0.0, Z)

        X_aug = _clamp_nonneg(pd.DataFrame(Z, columns=X.columns))
        Xs.append(X_aug)
        ys.append(y.copy())

    X_all = pd.concat(Xs, axis=0).reset_index(drop=True)
    y_all = pd.concat(ys, axis=0).reset_index(drop=True)
    return X_all, y_all

def noisy_copy_for_robustness(X: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 31337)
    A = X.values.astype(np.float32)
    n, d = A.shape

    feat_std = np.std(A, axis=0, ddof=1)
    feat_std[feat_std == 0] = 1.0

    mult = rng.normal(loc=1.0, scale=ROB_MULT_NOISE_STD, size=(n, d)).astype(np.float32)
    add  = rng.normal(loc=0.0, scale=ROB_ADD_NOISE_STD, size=(n, d)).astype(np.float32)
    scales = rng.uniform(ROB_GLOBAL_SCALE_RANGE[0], ROB_GLOBAL_SCALE_RANGE[1], size=(n, 1)).astype(np.float32)
    shifts = rng.uniform(ROB_GLOBAL_SHIFT_RANGE[0], ROB_GLOBAL_SHIFT_RANGE[1], size=(n, 1)).astype(np.float32)

    Z = A * mult + (add * feat_std)
    Z = Z * scales + Z * shifts
    return _clamp_nonneg(pd.DataFrame(Z, columns=X.columns))

# ===================== Model Wrapper =====================
class BoosterModel:
    def __init__(self, booster: xgb.Booster, classes_: np.ndarray, best_iteration: int | None):
        self.booster = booster
        self.classes_ = np.array(sorted(classes_.tolist()))
        self.best_iteration_ = best_iteration

    def _iteration_range(self):
        if self.best_iteration_ is None:
            return None
        return (0, int(self.best_iteration_) + 1)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        d = xgb.DMatrix(X)
        proba = self.booster.predict(d, iteration_range=self._iteration_range())
        return proba

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        proba = self.predict_proba(X)
        idx = np.argmax(proba, axis=1)
        return self.classes_[idx]

# ===================== Main =====================
def main():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Dataset file not found: {DATA_FILE}\n"
            "Put CSV in same folder as this script OR update DATA_FILE."
        )

    df = pd.read_csv(DATA_FILE)

    if "timestamp" not in df.columns:
        raise ValueError("Dataset must contain 'timestamp' column for time-based split.")

    # Drop AI output cols if they exist (safe)
    for c in ["anomaly_score", "final_risk_score", "risk_label"]:
        if c in df.columns:
            df.drop(columns=[c], inplace=True)

    # Validate feature columns
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Convert types
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for c in FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["timestamp"] + FEATURES).reset_index(drop=True)

    # Create labels
    y = label_from_thresholds(df).astype(int)
    X = df[FEATURES].copy().astype(np.float32)
    ts = df["timestamp"]

    # Split
    X_tr, y_tr, X_val, y_val, X_te, y_te = time_based_split(X, y, ts)

    log.info(f"Train dist: {dict(zip(*np.unique(y_tr, return_counts=True)))}")
    log.info(f"Test  dist: {dict(zip(*np.unique(y_te, return_counts=True)))}")

    # Augment
    X_tr_aug, y_tr_aug = augment_with_noise(X_tr, y_tr, factor=AUGMENT_FACTOR, seed=RANDOM_STATE)
    log.info(f"Augmented TRAIN: {X_tr.shape[0]} -> {X_tr_aug.shape[0]} rows")

    # Class weights
    classes = np.unique(y_tr_aug)
    cw = compute_class_weight("balanced", classes=classes, y=y_tr_aug)
    class_weight_map = {int(c): float(w) for c, w in zip(classes, cw)}
    sw_tr = y_tr_aug.map(class_weight_map).astype(np.float32).values

    # Search
    base = xgb.XGBClassifier(
        objective="multi:softprob",
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbosity=0,
    )
    param_dist = {
        "n_estimators":       [400, 700, 1000],
        "max_depth":          [3, 4, 6, 8],
        "learning_rate":      [0.03, 0.05, 0.08],
        "subsample":          [0.7, 0.85, 1.0],
        "colsample_bytree":   [0.7, 0.85, 1.0],
        "reg_lambda":         [1.0, 1.8, 3.0],
        "min_child_weight":   [2, 4, 6],
        "gamma":              [0.0, 0.1, 0.2],
    }
    search = RandomizedSearchCV(
        base, param_distributions=param_dist, n_iter=N_SEARCH_ITERS,
        scoring="f1_macro", n_jobs=-1, verbose=2, random_state=RANDOM_STATE
    )
    search.fit(X_tr_aug, y_tr_aug, sample_weight=sw_tr)

    best = search.best_estimator_
    log.info(f"Best params: {search.best_params_} | Best CV f1_macro: {search.best_score_:.4f}")

    # Train booster with early stopping
    dtrain = xgb.DMatrix(X_tr_aug, label=y_tr_aug.values, weight=sw_tr)
    dvalid = xgb.DMatrix(X_val, label=y_val.values)

    params = best.get_xgb_params()
    params.pop("n_estimators", None)
    params["objective"] = "multi:softprob"
    params["eval_metric"] = "mlogloss"
    params["num_class"] = int(y.max() + 1)
    params["tree_method"] = "hist"

    num_boost_round = int(best.get_params().get("n_estimators", 700))
    booster = xgb.train(
        params=params,
        dtrain=dtrain,
        num_boost_round=num_boost_round,
        evals=[(dvalid, "valid")],
        early_stopping_rounds=ES_ROUNDS,
        verbose_eval=False
    )
    best_iteration = getattr(booster, "best_iteration", None)
    model = BoosterModel(booster=booster, classes_=np.arange(int(y.max() + 1)), best_iteration=best_iteration)

    # Eval clean
    y_hat = model.predict(X_te)
    acc = accuracy_score(y_te, y_hat)
    f1w = f1_score(y_te, y_hat, average="weighted")
    f1m = f1_score(y_te, y_hat, average="macro")

    print("\n=== CLEAN TEST ===")
    print(f"Acc={acc:.4f} | F1_weighted={f1w:.4f} | F1_macro={f1m:.4f}")
    print(classification_report(y_te, y_hat, target_names=[CLASS_MAP[i] for i in sorted(CLASS_MAP)], zero_division=0))
    print("Confusion matrix:\n", confusion_matrix(y_te, y_hat))

    # Eval robust
    X_te_noisy = noisy_copy_for_robustness(X_te, seed=RANDOM_STATE)
    y_hat_rob = model.predict(X_te_noisy)
    acc_r = accuracy_score(y_te, y_hat_rob)
    f1w_r = f1_score(y_te, y_hat_rob, average="weighted")
    f1m_r = f1_score(y_te, y_hat_rob, average="macro")

    print("\n=== ROBUSTNESS TEST ===")
    print(f"Acc={acc_r:.4f} | F1_weighted={f1w_r:.4f} | F1_macro={f1m_r:.4f}")
    print(classification_report(y_te, y_hat_rob, target_names=[CLASS_MAP[i] for i in sorted(CLASS_MAP)], zero_division=0))
    print("Confusion matrix:\n", confusion_matrix(y_te, y_hat_rob))

    # SHAP
    shap_imp: Dict[str, float] = {}
    try:
        X_shap = X_tr.sample(min(1000, len(X_tr)), random_state=RANDOM_STATE)
        expl = shap.TreeExplainer(booster)
        sv = expl.shap_values(X_shap)

        if isinstance(sv, list):
            arrs = [np.abs(np.asarray(s, dtype=float)) for s in sv]
            sv_abs = np.mean(arrs, axis=0)
        else:
            sv_abs = np.abs(np.asarray(sv, dtype=float))

        imp = sv_abs.mean(axis=0)
        shap_imp = {feat: float(val) for feat, val in zip(FEATURES, imp.tolist())}
    except Exception as e:
        log.warning(f"SHAP failed: {e}")
        shap_imp = {}

    # Save
    meta = {
        "name": "XGB Bulk Drug Safety Risk Classifier (CPU, early-stopping, threshold-labeled, noise-aug)",
        "xgboost_version": xgb.__version__,
        "trained_at": datetime.now().isoformat(),
        "features": FEATURES,
        "class_mapping": CLASS_MAP,
        "metrics": {
            "clean_test_accuracy": float(acc),
            "clean_test_f1_weighted": float(f1w),
            "clean_test_f1_macro": float(f1m),
            "robust_test_accuracy": float(acc_r),
            "robust_test_f1_weighted": float(f1w_r),
            "robust_test_f1_macro": float(f1m_r),
            "search_best_score": float(search.best_score_),
        },
        "best_params": search.best_params_,
        "best_iteration": int(best_iteration) if best_iteration is not None else None,
        "threshold_config": TH,
    }

    pkg = {"pipeline": model, "booster": booster, "features": FEATURES, "metadata": meta}

    joblib.dump(pkg, MODEL_FILE)
    booster.save_model(MODEL_JSON)
    with open(META_JSON, "w") as f:
        json.dump(meta, f, indent=2)
    with open(SHAP_JSON, "w") as f:
        json.dump(shap_imp, f, indent=2)

    print("\n=== SAVED OUTPUTS ===")
    print("Model PKL:", MODEL_FILE)
    print("Model JSON:", MODEL_JSON)
    print("Metadata :", META_JSON)
    print("SHAP JSON:", SHAP_JSON)

if __name__ == "__main__":
    main()
