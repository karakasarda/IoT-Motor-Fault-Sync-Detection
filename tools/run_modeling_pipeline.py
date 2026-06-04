import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "sync_captures"
DEFAULT_FEATURE_PATH = ROOT / "data" / "processed" / "window_features.csv"
DEFAULT_REPORT_DIR = ROOT / "reports" / "modeling"
DEFAULT_MODEL_PATH = ROOT / "models" / "best_binary_model.joblib"

NORMAL_LABEL = "normal"
ANOMALY_LABEL = "anomaly"
BINARY_ORDER = [NORMAL_LABEL, ANOMALY_LABEL]
ANOMALY_SOURCE_LABELS = {"vibration", "load", "damping", "stall_risk", "mixed_anomaly"}


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    label: str
    fused_path: Path
    summary_path: Path
    thermal_summary_path: Path
    imu_path: Path
    summary: dict


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build window features, train binary motor anomaly models, and write reports."
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--target", choices=["binary", "multiclass"], default="binary")
    parser.add_argument("--windows", nargs="+", type=float, default=[2, 5, 10, 15])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--feature-output", default=str(DEFAULT_FEATURE_PATH))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--model-output", default=str(DEFAULT_MODEL_PATH))
    return parser.parse_args()


def load_sessions(data_dir):
    records = []
    for session_dir in sorted(Path(data_dir).iterdir()):
        if not session_dir.is_dir():
            continue
        fused_path = session_dir / "fused_imu_thermal.csv"
        summary_path = session_dir / "sync_summary.json"
        thermal_summary_path = session_dir / "thermal" / "frames_summary.csv"
        imu_path = session_dir / "imu.csv"
        if not fused_path.exists():
            continue
        summary = {}
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        label = infer_label(fused_path, summary)
        records.append(
            SessionRecord(
                session_id=session_dir.name,
                label=label,
                fused_path=fused_path,
                summary_path=summary_path,
                thermal_summary_path=thermal_summary_path,
                imu_path=imu_path,
                summary=summary,
            )
        )
    if not records:
        raise SystemExit(f"No fused_imu_thermal.csv files found under {data_dir}")
    return records


def infer_label(fused_path, summary):
    try:
        labels = pd.read_csv(fused_path, usecols=["label"])["label"].dropna()
        if not labels.empty:
            return str(labels.mode().iloc[0])
    except Exception:
        pass
    output_dir = summary.get("output_dir", "")
    if output_dir:
        return Path(output_dir).name.rstrip("0123456789")
    return fused_path.parent.name.rstrip("0123456789")


def safe_std(series):
    return float(series.std(ddof=0)) if len(series) else 0.0


def safe_slope(time_s, values):
    if len(values) < 2:
        return 0.0
    x = np.asarray(time_s, dtype=float)
    y = np.asarray(values, dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return 0.0
    if float(np.nanmax(x) - np.nanmin(x)) <= 1e-9:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def add_stats(features, prefix, series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        for stat in ["mean", "std", "min", "p05", "p25", "p50", "p75", "p95", "max", "range", "rms"]:
            features[f"{prefix}_{stat}"] = 0.0
        return
    arr = values.to_numpy(dtype=float)
    features[f"{prefix}_mean"] = float(np.mean(arr))
    features[f"{prefix}_std"] = safe_std(values)
    features[f"{prefix}_min"] = float(np.min(arr))
    features[f"{prefix}_p05"] = float(np.quantile(arr, 0.05))
    features[f"{prefix}_p25"] = float(np.quantile(arr, 0.25))
    features[f"{prefix}_p50"] = float(np.quantile(arr, 0.50))
    features[f"{prefix}_p75"] = float(np.quantile(arr, 0.75))
    features[f"{prefix}_p95"] = float(np.quantile(arr, 0.95))
    features[f"{prefix}_max"] = float(np.max(arr))
    features[f"{prefix}_range"] = float(np.max(arr) - np.min(arr))
    features[f"{prefix}_rms"] = float(np.sqrt(np.mean(arr * arr)))


def window_features(window, session_id, source_label, window_size, start_s, end_s):
    features = {
        "session_id": session_id,
        "source_label": source_label,
        "binary_label": NORMAL_LABEL if source_label == NORMAL_LABEL else ANOMALY_LABEL,
        "window_size_s": float(window_size),
        "window_start_s": float(start_s),
        "window_end_s": float(end_s),
        "row_count": int(len(window)),
    }

    motion_columns = ["ax", "ay", "az", "gx", "gy", "gz", "acc_mag", "gyro_mag"]
    for column in motion_columns:
        if column in window:
            add_stats(features, f"motion__{column}", window[column])
            features[f"motion__{column}_slope"] = safe_slope(window["host_elapsed_s"], window[column])

    if "gyro_mag" in window:
        gyro = pd.to_numeric(window["gyro_mag"], errors="coerce").fillna(0)
        for threshold in [4, 6, 8, 10, 20, 30]:
            features[f"motion__gyro_mag_gt_{threshold}_frac"] = float((gyro > threshold).mean())
    if "acc_mag" in window:
        acc = pd.to_numeric(window["acc_mag"], errors="coerce").fillna(0)
        for threshold in [1.08, 1.12, 1.20, 1.50]:
            features[f"motion__acc_mag_gt_{threshold}_frac"] = float((acc > threshold).mean())

    if "pulse_rate_hz" in window:
        add_stats(features, "pulse__rate_hz", window["pulse_rate_hz"])
        rate = pd.to_numeric(window["pulse_rate_hz"], errors="coerce").fillna(0)
        for threshold in [20, 30, 45, 60]:
            features[f"pulse__rate_lt_{threshold}_frac"] = float((rate < threshold).mean())
        features["pulse__rate_zero_frac"] = float((rate <= 0).mean())
        features["pulse__rate_slope"] = safe_slope(window["host_elapsed_s"], rate)
    if "last_edge_dt_ms" in window:
        add_stats(features, "pulse__last_edge_dt_ms", window["last_edge_dt_ms"])
        edge = pd.to_numeric(window["last_edge_dt_ms"], errors="coerce").fillna(0)
        for threshold in [50, 100, 250, 500, 1000]:
            features[f"pulse__edge_gt_{threshold}_frac"] = float((edge > threshold).mean())
    if "state" in window:
        state = pd.to_numeric(window["state"], errors="coerce").fillna(0)
        features["pulse__state_high_frac"] = float((state > 0).mean())
    for column in ["pulse_count", "edge_count", "rise_count", "fall_count"]:
        if column in window:
            values = pd.to_numeric(window[column], errors="coerce").dropna()
            features[f"pulse__{column}_delta"] = float(values.iloc[-1] - values.iloc[0]) if len(values) else 0.0

    thermal_columns = [
        "thermal_temp_min_c",
        "thermal_temp_mean_c",
        "thermal_temp_p95_c",
        "thermal_temp_max_c",
        "thermal_temp_center_c",
    ]
    for column in thermal_columns:
        if column in window:
            add_stats(features, f"thermal__{column.replace('thermal_', '')}", window[column])
            values = pd.to_numeric(window[column], errors="coerce")
            valid = values.dropna()
            features[f"thermal__{column.replace('thermal_', '')}_delta"] = (
                float(valid.iloc[-1] - valid.iloc[0]) if len(valid) else 0.0
            )
            features[f"thermal__{column.replace('thermal_', '')}_slope"] = safe_slope(
                window.loc[valid.index, "host_elapsed_s"],
                valid,
            )

    return features


def build_window_features(records, windows):
    rows = []
    for record in records:
        data = pd.read_csv(record.fused_path)
        if "host_elapsed_s" not in data:
            continue
        data = data.sort_values("host_elapsed_s").reset_index(drop=True)
        data["host_elapsed_s"] = pd.to_numeric(data["host_elapsed_s"], errors="coerce")
        data = data.dropna(subset=["host_elapsed_s"])
        if data.empty:
            continue
        t0 = float(data["host_elapsed_s"].iloc[0])
        t_end = float(data["host_elapsed_s"].iloc[-1])
        for window_size in windows:
            step = window_size / 2.0
            start = t0
            while start + window_size <= t_end + 1e-9:
                end = start + window_size
                window = data[(data["host_elapsed_s"] >= start) & (data["host_elapsed_s"] < end)]
                if len(window) >= max(8, int(window_size * 10)):
                    rows.append(window_features(window, record.session_id, record.label, window_size, start - t0, end - t0))
                start += step
    features = pd.DataFrame(rows)
    if features.empty:
        raise SystemExit("No windows could be extracted from the input data.")
    numeric_cols = features.select_dtypes(include=[np.number]).columns
    features[numeric_cols] = features[numeric_cols].replace([np.inf, -np.inf], np.nan)
    if features[numeric_cols].isna().any().any():
        features[numeric_cols] = features[numeric_cols].fillna(features[numeric_cols].median(numeric_only=True)).fillna(0.0)
    return features


def quality_report(records):
    rows = []
    for record in records:
        row = {
            "session_id": record.session_id,
            "label": record.label,
            "has_fused": record.fused_path.exists(),
            "has_imu": record.imu_path.exists(),
            "has_thermal_summary": record.thermal_summary_path.exists(),
            "has_sync_summary": record.summary_path.exists(),
            "imu_rows": record.summary.get("imu_rows", 0),
            "thermal_frames": record.summary.get("thermal_frames", 0),
            "fused_rows": record.summary.get("fused_rows", 0),
            "sync_p95_s": record.summary.get("nearest_thermal_frame_dt_s_p95", np.nan),
            "sync_max_s": record.summary.get("nearest_thermal_frame_dt_s_max", np.nan),
            "thermal_interval_max_s": record.summary.get("thermal_interval_s_max", np.nan),
            "errors": "; ".join(record.summary.get("errors", [])),
        }
        try:
            df = pd.read_csv(
                record.fused_path,
                usecols=lambda c: c
                in [
                    "host_elapsed_s",
                    "gyro_mag",
                    "acc_mag",
                    "pulse_count",
                    "pulse_rate_hz",
                    "last_edge_dt_ms",
                    "thermal_temp_mean_c",
                    "thermal_temp_max_c",
                ],
            )
            row["nan_cells"] = int(df.isna().sum().sum())
            row["duration_s"] = float(df["host_elapsed_s"].max() - df["host_elapsed_s"].min())
            row["gyro_mean"] = float(df["gyro_mag"].mean()) if "gyro_mag" in df else np.nan
            row["gyro_p95"] = float(df["gyro_mag"].quantile(0.95)) if "gyro_mag" in df else np.nan
            row["pulse_mean_hz"] = float(df["pulse_rate_hz"].mean()) if "pulse_rate_hz" in df else np.nan
            row["pulse_lt_20_pct"] = float((df["pulse_rate_hz"] < 20).mean() * 100) if "pulse_rate_hz" in df else np.nan
            row["pulse_lt_45_pct"] = float((df["pulse_rate_hz"] < 45).mean() * 100) if "pulse_rate_hz" in df else np.nan
            row["last_edge_max_ms"] = float(df["last_edge_dt_ms"].max()) if "last_edge_dt_ms" in df else np.nan
            row["pulse_count_delta"] = (
                float(df["pulse_count"].iloc[-1] - df["pulse_count"].iloc[0]) if "pulse_count" in df and len(df) else np.nan
            )
            row["thermal_mean_c"] = float(df["thermal_temp_mean_c"].mean()) if "thermal_temp_mean_c" in df else np.nan
            row["thermal_max_c"] = float(df["thermal_temp_max_c"].max()) if "thermal_temp_max_c" in df else np.nan
        except Exception as exc:
            row["read_error"] = str(exc)
        rows.append(row)

    quality = pd.DataFrame(rows)
    quality["flag_missing_file"] = ~(quality["has_fused"] & quality["has_imu"] & quality["has_thermal_summary"] & quality["has_sync_summary"])
    quality["flag_sync_p95_gt_0_75s"] = quality["sync_p95_s"].fillna(99) > 0.75
    quality["flag_thermal_gap_gt_2s"] = quality["thermal_interval_max_s"].fillna(0) > 2.0
    quality["flag_edge_gap_gt_1000ms"] = quality["last_edge_max_ms"].fillna(0) > 1000
    quality["flag_pulse_delta_low"] = quality["pulse_count_delta"].fillna(0) < 100
    quality["flag_hot_gt_50c"] = quality["thermal_max_c"].fillna(0) > 50

    normal = quality[quality["label"] == NORMAL_LABEL].copy()
    quality["flag_normal_outlier"] = False
    if len(normal) >= 3:
        for metric in ["gyro_mean", "pulse_mean_hz", "thermal_mean_c"]:
            median = float(normal[metric].median())
            mad = float(np.median(np.abs(normal[metric] - median)))
            if mad <= 1e-9:
                continue
            score = np.abs((quality[metric] - median) / (1.4826 * mad))
            quality.loc[(quality["label"] == NORMAL_LABEL) & (score > 3.5), "flag_normal_outlier"] = True
    return quality


def write_quality_markdown(quality, feature_data, output_path):
    class_summary = (
        quality.groupby("label")
        .agg(sessions=("session_id", "count"), duration_s=("duration_s", "sum"), imu_rows=("imu_rows", "sum"))
        .round(2)
        .reset_index()
    )
    window_counts = feature_data.groupby(["window_size_s", "source_label"]).size().unstack(fill_value=0).astype(int).reset_index()
    lines = [
        "# Dataset Quality Report",
        "",
        f"Sessions: {len(quality)}",
        f"Window rows: {len(feature_data)}",
        "",
        "## Class Distribution",
        "",
        markdown_table(class_summary),
        "",
        "## Window Counts",
        "",
        markdown_table(window_counts),
        "",
        "## Quality Flags",
        "",
    ]
    flag_cols = [c for c in quality.columns if c.startswith("flag_")]
    flagged = quality[quality[flag_cols].any(axis=1)].copy()
    if flagged.empty:
        lines.append("No sessions triggered quality flags.")
    else:
        display_cols = ["session_id", "label", "sync_p95_s", "thermal_interval_max_s", "last_edge_max_ms", "thermal_max_c", *flag_cols]
        lines.append(markdown_table(flagged[display_cols]))
    lines.extend(
        [
            "",
            "## Session Summary",
            "",
            quality[
                [
                    "session_id",
                    "label",
                    "duration_s",
                    "imu_rows",
                    "thermal_frames",
                    "sync_p95_s",
                    "gyro_mean",
                    "gyro_p95",
                    "pulse_mean_hz",
                    "pulse_lt_20_pct",
                    "pulse_lt_45_pct",
                    "last_edge_max_ms",
                    "thermal_mean_c",
                    "thermal_max_c",
                ]
            ]
            .round(3)
            .pipe(markdown_table),
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def markdown_table(df):
    frame = df.copy()
    if isinstance(frame, pd.Series):
        frame = frame.reset_index()
    frame = frame.reset_index(drop=True)
    columns = [str(c) for c in frame.columns]

    def fmt(value):
        if pd.isna(value):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.4g}"
        return str(value)

    rows = [[fmt(value) for value in row] for row in frame.to_numpy()]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def model_catalog(seed):
    return {
        "dummy_most_frequent": Pipeline([("imputer", SimpleImputer()), ("model", DummyClassifier(strategy="most_frequent"))]),
        "logistic_regression": Pipeline(
            [
                ("imputer", SimpleImputer()),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=5000, class_weight="balanced", random_state=seed)),
            ]
        ),
        "svm_rbf": Pipeline(
            [
                ("imputer", SimpleImputer()),
                ("scaler", StandardScaler()),
                ("model", SVC(kernel="rbf", C=3.0, gamma="scale", class_weight="balanced", random_state=seed)),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer()),
                ("model", RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=seed, n_jobs=-1)),
            ]
        ),
        "extra_trees": Pipeline(
            [
                ("imputer", SimpleImputer()),
                ("model", ExtraTreesClassifier(n_estimators=400, class_weight="balanced", random_state=seed, n_jobs=-1)),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer()),
                ("model", HistGradientBoostingClassifier(random_state=seed, max_iter=250)),
            ]
        ),
        "knn": Pipeline(
            [
                ("imputer", SimpleImputer()),
                ("scaler", StandardScaler()),
                ("model", KNeighborsClassifier(n_neighbors=5, weights="distance")),
            ]
        ),
    }


def feature_sets(feature_data):
    motion = [c for c in feature_data.columns if c.startswith("motion__")]
    pulse = [c for c in feature_data.columns if c.startswith("pulse__")]
    thermal = [c for c in feature_data.columns if c.startswith("thermal__")]
    return {
        "motion_only": motion,
        "pulse_only": pulse,
        "thermal_only": thermal,
        "motion_pulse": motion + pulse,
        "motion_pulse_thermal": motion + pulse + thermal,
    }


def target_column(target):
    return "binary_label" if target == "binary" else "source_label"


def label_order(y, target):
    if target == "binary":
        return BINARY_ORDER
    return sorted(pd.Series(y).unique().tolist())


def metric_dict(y_true, y_pred, target):
    labels = label_order(y_true, target)
    result = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "mcc": matthews_corrcoef(y_true, y_pred),
    }
    if target == "binary":
        result["normal_recall"] = recall_score(y_true, y_pred, labels=labels, pos_label=NORMAL_LABEL, average="binary", zero_division=0)
        result["anomaly_recall"] = recall_score(y_true, y_pred, labels=labels, pos_label=ANOMALY_LABEL, average="binary", zero_division=0)
        result["f1_anomaly"] = f1_score(y_true, y_pred, labels=labels, pos_label=ANOMALY_LABEL, average="binary", zero_division=0)
    return result


def evaluate_group_cv(data, features, estimator, target, seed):
    y = data[target_column(target)].astype(str).to_numpy()
    groups = data["session_id"].astype(str).to_numpy()
    X = data[features].to_numpy(dtype=float)
    group_labels = data[["session_id", target_column(target)]].drop_duplicates()
    class_group_counts = group_labels[target_column(target)].value_counts()
    n_splits = int(min(5, class_group_counts.min()))
    if n_splits < 2:
        raise ValueError("Not enough grouped sessions for cross-validation.")
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    predictions = pd.DataFrame(
        {
            "row_index": data.index.to_numpy(),
            "session_id": data["session_id"].to_numpy(),
            "source_label": data["source_label"].to_numpy(),
            "true_label": y,
            "pred_label": "",
        }
    )
    fold_scores = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(X, y, groups), start=1):
        model = clone(estimator)
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[test_idx])
        predictions.loc[test_idx, "pred_label"] = pred
        fold_score = metric_dict(y[test_idx], pred, target)
        fold_score["fold"] = fold
        fold_scores.append(fold_score)
    predictions["pred_label"] = predictions["pred_label"].astype(str)
    scores = metric_dict(predictions["true_label"], predictions["pred_label"], target)
    scores["folds"] = n_splits
    scores["fold_mcc_mean"] = float(np.mean([f["mcc"] for f in fold_scores]))
    scores["fold_mcc_std"] = float(np.std([f["mcc"] for f in fold_scores], ddof=0))
    return scores, predictions


def evaluate_random_split(data, features, estimator, target, seed):
    y = data[target_column(target)].astype(str).to_numpy()
    X = data[features].to_numpy(dtype=float)
    indices = np.arange(len(data))
    train_idx, test_idx = train_test_split(indices, test_size=0.25, random_state=seed, stratify=y)
    model = clone(estimator)
    model.fit(X[train_idx], y[train_idx])
    pred = model.predict(X[test_idx])
    scores = metric_dict(y[test_idx], pred, target)
    scores["folds"] = 1
    scores["fold_mcc_mean"] = scores["mcc"]
    scores["fold_mcc_std"] = 0.0
    predictions = pd.DataFrame(
        {
            "row_index": data.index.to_numpy()[test_idx],
            "session_id": data["session_id"].to_numpy()[test_idx],
            "source_label": data["source_label"].to_numpy()[test_idx],
            "true_label": y[test_idx],
            "pred_label": pred,
        }
    )
    return scores, predictions


def plot_confusion(y_true, y_pred, labels, title, output_path):
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(6, 5))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def run_experiments(feature_data, target, windows, seed, report_dir):
    catalog = model_catalog(seed)
    sets = feature_sets(feature_data)
    result_rows = []
    predictions_by_key = {}
    for window_size in windows:
        window_data = feature_data[feature_data["window_size_s"] == float(window_size)].reset_index(drop=True)
        if window_data.empty:
            continue
        for feature_set_name, columns in sets.items():
            if not columns:
                continue
            for model_name, estimator in catalog.items():
                for split_type in ["group_cv", "random_window_leakage_diagnostic"]:
                    if split_type == "group_cv":
                        scores, predictions = evaluate_group_cv(window_data, columns, estimator, target, seed)
                    else:
                        scores, predictions = evaluate_random_split(window_data, columns, estimator, target, seed)
                    row = {
                        "target": target,
                        "window_size_s": float(window_size),
                        "feature_set": feature_set_name,
                        "model": model_name,
                        "split_type": split_type,
                        "n_windows": int(len(window_data)),
                        "n_features": int(len(columns)),
                        **scores,
                    }
                    result_rows.append(row)
                    predictions_by_key[(float(window_size), feature_set_name, model_name, split_type)] = predictions

    results = pd.DataFrame(result_rows)
    group_results = results[results["split_type"] == "group_cv"].copy()
    group_results = group_results.sort_values(
        ["window_size_s", "mcc", "balanced_accuracy", "anomaly_recall", "f1_macro"],
        ascending=[True, False, False, False, False],
    )
    labels = label_order(feature_data[target_column(target)], target)
    for window_size, window_results in group_results.groupby("window_size_s"):
        best = window_results.iloc[0]
        key = (float(window_size), best["feature_set"], best["model"], "group_cv")
        predictions = predictions_by_key[key]
        suffix = format_window_suffix(window_size)
        plot_confusion(
            predictions["true_label"],
            predictions["pred_label"],
            labels,
            f"Best group-CV confusion matrix ({window_size:g}s)",
            report_dir / f"confusion_matrix_window_{suffix}.png",
        )
        (report_dir / f"classification_report_window_{suffix}.txt").write_text(
            classification_report(predictions["true_label"], predictions["pred_label"], labels=labels, zero_division=0),
            encoding="utf-8",
        )

    best = group_results.sort_values(
        ["mcc", "balanced_accuracy", "anomaly_recall", "f1_macro"],
        ascending=[False, False, False, False],
    ).iloc[0]
    best_key = (float(best["window_size_s"]), best["feature_set"], best["model"], "group_cv")
    best_predictions = predictions_by_key[best_key]
    return results, best, best_predictions


def format_window_suffix(window_size):
    if float(window_size).is_integer():
        return f"{int(window_size)}s"
    return f"{str(window_size).replace('.', '_')}s"


def train_final_model(feature_data, best, target, seed, model_path):
    sets = feature_sets(feature_data)
    columns = sets[best["feature_set"]]
    data = feature_data[feature_data["window_size_s"] == float(best["window_size_s"])].reset_index(drop=True)
    y = data[target_column(target)].astype(str).to_numpy()
    X = data[columns].to_numpy(dtype=float)
    estimator = clone(model_catalog(seed)[best["model"]])
    estimator.fit(X, y)
    artifact = {
        "model": estimator,
        "feature_columns": columns,
        "target": target,
        "label_order": label_order(y, target),
        "window_size_s": float(best["window_size_s"]),
        "feature_set": best["feature_set"],
        "model_name": best["model"],
        "selection_metric": "mcc",
        "selection_scores": best.to_dict(),
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    return artifact, data, columns


def write_feature_importance(feature_data, best, target, seed, columns, report_dir):
    data = feature_data[feature_data["window_size_s"] == float(best["window_size_s"])].reset_index(drop=True)
    y = data[target_column(target)].astype(str).to_numpy()
    groups = data["session_id"].astype(str).to_numpy()
    X = data[columns].to_numpy(dtype=float)
    group_labels = data[["session_id", target_column(target)]].drop_duplicates()
    n_splits = int(min(5, group_labels[target_column(target)].value_counts().min()))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    model = clone(model_catalog(seed)[best["model"]])
    model.fit(X[train_idx], y[train_idx])
    scoring = "f1_macro"
    importance = permutation_importance(
        model,
        X[test_idx],
        y[test_idx],
        scoring=scoring,
        n_repeats=15,
        random_state=seed,
        n_jobs=-1,
    )
    model_step = model.named_steps.get("model")
    native_importance = np.full(len(columns), np.nan)
    native_importance_label = "not_available"
    if hasattr(model_step, "feature_importances_"):
        native_importance = np.asarray(model_step.feature_importances_, dtype=float)
        native_importance_label = "tree_feature_importance"
    elif hasattr(model_step, "coef_"):
        native_importance = np.mean(np.abs(np.asarray(model_step.coef_, dtype=float)), axis=0)
        native_importance_label = "absolute_coefficient"

    importance_df = pd.DataFrame(
        {
            "feature": columns,
            "permutation_importance_mean": importance.importances_mean,
            "permutation_importance_std": importance.importances_std,
            "model_importance": native_importance,
        }
    )
    if np.isfinite(native_importance).any() and float(np.nansum(np.abs(native_importance))) > 0:
        importance_df["plot_importance"] = importance_df["model_importance"]
        plot_label = native_importance_label
    else:
        importance_df["plot_importance"] = importance_df["permutation_importance_mean"]
        plot_label = "permutation_importance"
    importance_df = importance_df.sort_values("plot_importance", ascending=False)
    importance_df.to_csv(report_dir / "feature_importance_best_binary.csv", index=False)

    top = importance_df.head(25).iloc[::-1]
    plt.figure(figsize=(10, max(5, len(top) * 0.32)))
    xerr = top["permutation_importance_std"] if plot_label == "permutation_importance" else None
    plt.barh(top["feature"], top["plot_importance"], xerr=xerr, color="#2563eb")
    plt.xlabel(plot_label)
    plt.title("Best binary model feature importance")
    plt.tight_layout()
    plt.savefig(report_dir / "feature_importance_best_binary.png", dpi=180)
    plt.close()
    return importance_df


def write_modeling_summary(results, best, best_predictions, target, report_dir, model_path):
    group_results = results[results["split_type"] == "group_cv"].copy()
    random_results = results[results["split_type"] == "random_window_leakage_diagnostic"].copy()
    dummy_best = group_results[group_results["model"] == "dummy_most_frequent"]["mcc"].max()
    deployable = bool(best["mcc"] > dummy_best)
    labels = label_order(best_predictions["true_label"], target)
    lines = [
        "# Modeling Summary",
        "",
        "## Best Group-CV Model",
        "",
        markdown_table(pd.DataFrame([best]).round(4)),
        "",
        f"Saved model artifact: `{model_path}`",
        f"Deploy status: {'candidate' if deployable else 'prototype only - did not beat dummy MCC baseline'}",
        "",
        "## Best Model Classification Report",
        "",
        "```text",
        classification_report(best_predictions["true_label"], best_predictions["pred_label"], labels=labels, zero_division=0),
        "```",
        "",
        "## Group-CV Top Results",
        "",
        group_results.sort_values(["mcc", "balanced_accuracy", "anomaly_recall", "f1_macro"], ascending=False)
        .head(20)
        .round(4)
        .pipe(markdown_table),
        "",
        "## Leakage Diagnostic Top Results",
        "",
        "These rows use random window splits and are diagnostic only. They must not be used for model selection.",
        "",
        random_results.sort_values(["mcc", "balanced_accuracy", "anomaly_recall", "f1_macro"], ascending=False)
        .head(20)
        .round(4)
        .pipe(markdown_table),
        "",
    ]
    (report_dir / "modeling_summary.md").write_text("\n".join(lines), encoding="utf-8")
    (report_dir / "classification_report_best_binary.txt").write_text(
        classification_report(best_predictions["true_label"], best_predictions["pred_label"], labels=labels, zero_division=0),
        encoding="utf-8",
    )


def main():
    args = parse_args()
    data_dir = Path(args.data_dir)
    feature_output = Path(args.feature_output)
    report_dir = Path(args.report_dir)
    model_path = Path(args.model_output)
    report_dir.mkdir(parents=True, exist_ok=True)
    feature_output.parent.mkdir(parents=True, exist_ok=True)

    windows = [float(w) for w in args.windows]
    records = load_sessions(data_dir)
    feature_data = build_window_features(records, windows).copy()
    if args.target == "multiclass":
        feature_data["target_label"] = feature_data["source_label"]
    else:
        feature_data["target_label"] = feature_data["binary_label"]
    feature_data.to_csv(feature_output, index=False)

    quality = quality_report(records)
    quality.to_csv(report_dir / "dataset_quality.csv", index=False)
    write_quality_markdown(quality, feature_data, report_dir / "dataset_quality.md")

    results, best, best_predictions = run_experiments(feature_data, args.target, windows, args.seed, report_dir)
    results.sort_values(["split_type", "window_size_s", "feature_set", "model"]).to_csv(report_dir / "experiment_results.csv", index=False)

    labels = label_order(best_predictions["true_label"], args.target)
    plot_confusion(
        best_predictions["true_label"],
        best_predictions["pred_label"],
        labels,
        "Best binary model group-CV confusion matrix",
        report_dir / "confusion_matrix_best_binary.png",
    )
    artifact, _, columns = train_final_model(feature_data, best, args.target, args.seed, model_path)
    write_feature_importance(feature_data, best, args.target, args.seed, columns, report_dir)
    write_modeling_summary(results, best, best_predictions, args.target, report_dir, model_path)

    print(json.dumps(
        {
            "sessions": len(records),
            "windows": len(feature_data),
            "target": args.target,
            "best": {
                "window_size_s": float(best["window_size_s"]),
                "feature_set": best["feature_set"],
                "model": best["model"],
                "mcc": float(best["mcc"]),
                "balanced_accuracy": float(best["balanced_accuracy"]),
                "anomaly_recall": float(best.get("anomaly_recall", math.nan)),
                "f1_macro": float(best["f1_macro"]),
            },
            "feature_output": str(feature_output),
            "report_dir": str(report_dir),
            "model_output": str(model_path),
            "model_artifact_keys": sorted(artifact.keys()),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
