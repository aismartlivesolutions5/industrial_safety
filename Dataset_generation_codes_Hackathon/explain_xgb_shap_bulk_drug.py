# explain_xgb_shap_bulk_drug.py
# SHAP explainability for Bulk Drug Safety XGB model
# Fix: load Booster from MODEL_JSON (avoid joblib pickle custom class issue)

import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
import shap

RANDOM_STATE = 2025

MODEL_DIR   = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/models"
DATA_FILE   = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data/bulk_drug_factory_safety_90d_1min.csv"

MODEL_JSON  = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model.json")
META_JSON   = os.path.join(MODEL_DIR, "bulk_drug_safety_xgb_cpu_es_model_metadata.json")

OUT_GLOBAL  = os.path.join(MODEL_DIR, "bulk_drug_xgb_shap_global.json")
OUT_EXAMPLES= os.path.join(MODEL_DIR, "bulk_drug_xgb_shap_examples.json")

os.makedirs(MODEL_DIR, exist_ok=True)

def load_booster_and_meta():
    if not os.path.exists(MODEL_JSON):
        raise FileNotFoundError(f"Missing model json: {MODEL_JSON}")
    if not os.path.exists(META_JSON):
        raise FileNotFoundError(f"Missing metadata json: {META_JSON}")

    booster = xgb.Booster()
    booster.load_model(MODEL_JSON)

    with open(META_JSON, "r") as f:
        meta = json.load(f)

    features = meta["features"]
    class_mapping = meta.get("class_mapping", {})
    return booster, features, meta, class_mapping

def load_sample_data(features, n_samples=1000):
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Missing dataset file: {DATA_FILE}")

    df = pd.read_csv(DATA_FILE)
    # keep only required features
    X = df[features].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)

    if len(X) > n_samples:
        X = X.sample(n_samples, random_state=RANDOM_STATE)

    return X

def get_predicted_classes(booster, X, n_classes):
    dmat = xgb.DMatrix(X, feature_names=list(X.columns))
    pred = booster.predict(dmat)  # multiclass softprob -> flat or 2D depending on xgb
    pred = np.asarray(pred)

    if pred.ndim == 1:
        pred = pred.reshape(-1, n_classes)

    pred_class = np.argmax(pred, axis=1).astype(int)
    return pred_class, pred

def compute_shap_values(booster, X):
    explainer = shap.TreeExplainer(booster)
    sv = explainer.shap_values(X)

    # SHAP can return:
    # - list of arrays (n_classes) each (n_samples, n_features)
    # - array (n_samples, n_features, n_classes)
    # Normalize to (n_samples, n_features, n_classes)
    if isinstance(sv, list):
        arr = np.stack([np.asarray(a) for a in sv], axis=-1)
    else:
        arr = np.asarray(sv)
        if arr.ndim == 2:
            # binary sometimes returns (n_samples, n_features)
            arr = arr[:, :, None]
    return arr  # (n, f, c)

def top_reasons_for_sample(shap_cube, X, pred_class, top_k=5):
    # shap_cube: (n, f, c)
    reasons = []
    cols = list(X.columns)

    for i in range(len(X)):
        c = int(pred_class[i])
        v = shap_cube[i, :, c]  # (f,)
        idx = np.argsort(np.abs(v))[::-1][:top_k]

        reasons.append({
            "pred_class": c,
            "top_reasons": [
                {"feature": cols[j], "shap": float(v[j])}
                for j in idx
            ]
        })
    return reasons

def global_mean_abs_shap(shap_cube, X):
    # mean abs over samples and classes
    m = np.mean(np.abs(shap_cube), axis=(0, 2))  # (features,)
    return {feat: float(val) for feat, val in zip(X.columns, m)}

def main():
    booster, features, meta, class_mapping = load_booster_and_meta()

    # infer number of classes from metadata mapping if present
    if class_mapping:
        n_classes = len(class_mapping)
    else:
        # fallback: assume 4 (Normal/Watch/High/Critical)
        n_classes = 4

    X = load_sample_data(features, n_samples=500)  # keep it fast
    pred_class, _ = get_predicted_classes(booster, X, n_classes=n_classes)

    shap_cube = compute_shap_values(booster, X)  # (n,f,c)

    examples = top_reasons_for_sample(shap_cube, X, pred_class, top_k=4)
    global_imp = global_mean_abs_shap(shap_cube, X)

    with open(OUT_EXAMPLES, "w") as f:
        json.dump({"examples": examples[:10]}, f, indent=2)

    with open(OUT_GLOBAL, "w") as f:
        json.dump({
            "type": "multiclass",
            "global_mean_abs_shap": global_imp,
            "model_meta": meta
        }, f, indent=2)

    print("\n=== SHAP DONE ===")
    print("Saved examples :", OUT_EXAMPLES)
    print("Saved global   :", OUT_GLOBAL)

if __name__ == "__main__":
    main()
