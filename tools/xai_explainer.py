import argparse
import json
import math
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))

import joblib
import numpy as np
import pandas as pd

import modeling_features as mf


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURE_DATA = ROOT / "data" / "processed" / "window_features.csv"


def load_artifact(model_path):
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    artifact = joblib.load(path)
    required = {"model", "feature_columns", "window_size_s"}
    missing = required - set(artifact)
    if missing:
        raise ValueError(f"Model artifact is missing keys: {sorted(missing)}")
    return artifact


def to_float(value, default=None):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return value


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def model_classes(model, artifact):
    classes = list(getattr(model, "classes_", artifact.get("label_order", [])))
    return [str(label) for label in classes]


def predict_with_probabilities(artifact, x):
    model = artifact["model"]
    labels = model_classes(model, artifact)
    prediction = str(model.predict(x)[0])
    if not labels:
        labels = sorted(set(artifact.get("label_order", [prediction])) | {prediction})

    probabilities = {label: 0.0 for label in labels}
    if hasattr(model, "predict_proba"):
        raw = model.predict_proba(x)[0]
        for label, value in zip(model_classes(model, artifact), raw):
            probabilities[str(label)] = float(value)
    else:
        probabilities[prediction] = 1.0
    return prediction, probabilities


def load_feature_baseline(feature_data_path, artifact, source_label=mf.NORMAL_LABEL):
    columns = list(artifact["feature_columns"])
    path = Path(feature_data_path)
    if not path.exists():
        return pd.Series({column: 0.0 for column in columns}, dtype=float)

    data = pd.read_csv(path)
    if "window_size_s" in data:
        data = data[data["window_size_s"] == float(artifact["window_size_s"])]
    normal = data[data.get("source_label", "") == source_label] if "source_label" in data else data
    if normal.empty:
        normal = data

    baseline = {}
    for column in columns:
        if column in normal:
            value = pd.to_numeric(normal[column], errors="coerce").median()
            baseline[column] = to_float(value, 0.0)
        else:
            baseline[column] = 0.0
    return pd.Series(baseline, dtype=float)


def feature_family(feature):
    if "__" not in feature:
        return "other"
    return feature.split("__", 1)[0]


def global_feature_importance(artifact, top_n=25, importance_path=None):
    columns = list(artifact["feature_columns"])
    if importance_path and Path(importance_path).exists():
        table = pd.read_csv(importance_path)
        if "feature" in table:
            value_column = "plot_importance"
            if value_column not in table:
                value_column = "model_importance" if "model_importance" in table else "permutation_importance_mean"
            rows = table[["feature", value_column]].rename(columns={value_column: "importance"})
            rows = rows.sort_values("importance", ascending=False).head(top_n)
            return json_safe(rows.to_dict("records"))

    model = artifact["model"]
    model_step = model.named_steps.get("model") if hasattr(model, "named_steps") else model
    values = np.zeros(len(columns), dtype=float)
    source = "not_available"
    if hasattr(model_step, "feature_importances_"):
        values = np.asarray(model_step.feature_importances_, dtype=float)
        source = "tree_feature_importance"
    elif hasattr(model_step, "coef_"):
        values = np.mean(np.abs(np.asarray(model_step.coef_, dtype=float)), axis=0)
        source = "absolute_coefficient"

    rows = pd.DataFrame({"feature": columns, "importance": values})
    rows["family"] = rows["feature"].map(feature_family)
    rows["source"] = source
    return json_safe(rows.sort_values("importance", ascending=False).head(top_n).to_dict("records"))


def class_feature_effects(artifact, top_n=10):
    model = artifact["model"]
    model_step = model.named_steps.get("model") if hasattr(model, "named_steps") else model
    columns = list(artifact["feature_columns"])
    labels = model_classes(model, artifact)
    if not hasattr(model_step, "coef_"):
        return []

    coef = np.asarray(model_step.coef_, dtype=float)
    if coef.ndim == 1:
        coef = coef.reshape(1, -1)
    if len(labels) != coef.shape[0]:
        labels = artifact.get("label_order", labels)
    output = []
    for class_index, label in enumerate(labels[: coef.shape[0]]):
        rows = pd.DataFrame({"feature": columns, "effect": coef[class_index]})
        rows["abs_effect"] = rows["effect"].abs()
        rows = rows.sort_values("abs_effect", ascending=False).head(top_n)
        output.append(
            {
                "class_label": str(label),
                "top_effects": json_safe(rows[["feature", "effect"]].to_dict("records")),
            }
        )
    return output


def sensor_summary(window):
    def latest(column):
        if column not in window or window.empty:
            return None
        return to_float(pd.to_numeric(window[column], errors="coerce").iloc[-1])

    def mean(column):
        if column not in window or window.empty:
            return None
        return to_float(pd.to_numeric(window[column], errors="coerce").mean())

    def p95(column):
        if column not in window or window.empty:
            return None
        return to_float(pd.to_numeric(window[column], errors="coerce").quantile(0.95))

    duration = None
    sample_rate = None
    if "host_elapsed_s" in window and len(window) > 1:
        elapsed = pd.to_numeric(window["host_elapsed_s"], errors="coerce")
        duration = to_float(elapsed.max() - elapsed.min())
        if duration and duration > 0:
            sample_rate = len(window) / duration

    return json_safe(
        {
            "rows": int(len(window)),
            "duration_s": duration,
            "sample_rate_hz": sample_rate,
            "gyro_mag_latest": latest("gyro_mag"),
            "gyro_mag_mean": mean("gyro_mag"),
            "gyro_mag_p95": p95("gyro_mag"),
            "acc_mag_latest": latest("acc_mag"),
            "acc_mag_mean": mean("acc_mag"),
            "pulse_rate_hz_latest": latest("pulse_rate_hz"),
            "pulse_rate_hz_mean": mean("pulse_rate_hz"),
            "thermal_mean_c_latest": latest("thermal_temp_mean_c"),
            "thermal_mean_c_mean": mean("thermal_temp_mean_c"),
            "thermal_max_c_latest": latest("thermal_temp_max_c"),
        }
    )


def default_focus_label(artifact, prediction):
    if artifact.get("target") == "binary":
        return mf.ANOMALY_LABEL
    return prediction


def explain_window(window, artifact, baseline=None, focus_label=None, top_n=8, candidate_features=None):
    x, feature_row = mf.feature_row_for_model(window, artifact)
    prediction, probabilities = predict_with_probabilities(artifact, x)
    focus_label = str(focus_label or default_focus_label(artifact, prediction))
    focus_probability = float(probabilities.get(focus_label, 0.0))

    columns = list(artifact["feature_columns"])
    if baseline is None:
        baseline = pd.Series({column: 0.0 for column in columns}, dtype=float)

    values = feature_row.iloc[0].reindex(columns).astype(float)
    baseline = baseline.reindex(columns).fillna(0.0).astype(float)

    if candidate_features:
        selected = [feature for feature in candidate_features if feature in columns]
    else:
        selected = columns
    contributions = []
    for feature in selected:
        index = columns.index(feature)
        replaced = x.copy()
        replaced[0, index] = baseline.iloc[index]
        _, replaced_probs = predict_with_probabilities(artifact, replaced)
        replaced_focus_probability = float(replaced_probs.get(focus_label, 0.0))
        contribution = focus_probability - replaced_focus_probability
        delta = float(values.iloc[index] - baseline.iloc[index])
        contributions.append(
            {
                "feature": feature,
                "family": feature_family(feature),
                "value": float(values.iloc[index]),
                "normal_baseline": float(baseline.iloc[index]),
                "baseline_delta": delta,
                "focus_probability_delta": contribution,
                "direction": "raises_focus_probability" if contribution >= 0 else "lowers_focus_probability",
            }
        )

    contributions = sorted(contributions, key=lambda row: abs(row["focus_probability_delta"]), reverse=True)
    top_features = contributions[:top_n]
    confidence = max(probabilities.values()) if probabilities else 0.0
    contribution_mass = float(sum(abs(row["focus_probability_delta"]) for row in top_features))

    return json_safe(
        {
            "target": artifact.get("target", "unknown"),
            "model_name": artifact.get("model_name", "unknown"),
            "feature_set": artifact.get("feature_set", "unknown"),
            "window_size_s": float(artifact.get("window_size_s", 0.0)),
            "prediction": prediction,
            "focus_label": focus_label,
            "focus_probability": focus_probability,
            "probabilities": probabilities,
            "top_features": top_features,
            "sensor_summary": sensor_summary(window),
            "explanation_confidence": {
                "max_probability": float(confidence),
                "top_contribution_abs_sum": contribution_mass,
                "method": "baseline_replacement_probability_delta",
            },
        }
    )


def explain_session_latest(session_path, model_path, feature_data_path, top_n=8, focus_label=None):
    artifact = load_artifact(model_path)
    data = pd.read_csv(session_path)
    if "host_elapsed_s" not in data:
        raise ValueError("Session CSV must include host_elapsed_s.")
    data = data.sort_values("host_elapsed_s").reset_index(drop=True)
    window_size = float(artifact["window_size_s"])
    end = float(data["host_elapsed_s"].max())
    start = end - window_size
    window = data[data["host_elapsed_s"] >= start].copy()
    baseline = load_feature_baseline(feature_data_path, artifact)
    return explain_window(window, artifact, baseline=baseline, focus_label=focus_label, top_n=top_n)


def parse_args():
    parser = argparse.ArgumentParser(description="Explain a trained model decision for one synchronized session window.")
    parser.add_argument("--session", required=True, help="Path to fused_imu_thermal.csv.")
    parser.add_argument("--model", required=True, help="Path to a joblib model artifact.")
    parser.add_argument("--feature-data", default=str(DEFAULT_FEATURE_DATA))
    parser.add_argument("--focus-label", default=None)
    parser.add_argument("--top-n", type=int, default=8)
    return parser.parse_args()


def main():
    args = parse_args()
    explanation = explain_session_latest(
        args.session,
        args.model,
        args.feature_data,
        top_n=args.top_n,
        focus_label=args.focus_label,
    )
    print(json.dumps(explanation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
