import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


NORMAL_LABEL = "normal"
ANOMALY_LABEL = "anomaly"
STOPPED_LABEL = "stopped"
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
        records.append(
            SessionRecord(
                session_id=session_dir.name,
                label=infer_label(fused_path, summary),
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
    stats = ["mean", "std", "min", "p05", "p25", "p50", "p75", "p95", "max", "range", "rms"]
    if values.empty:
        for stat in stats:
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
            clean_name = column.replace("thermal_", "")
            add_stats(features, f"thermal__{clean_name}", window[column])
            values = pd.to_numeric(window[column], errors="coerce")
            valid = values.dropna()
            features[f"thermal__{clean_name}_delta"] = float(valid.iloc[-1] - valid.iloc[0]) if len(valid) else 0.0
            features[f"thermal__{clean_name}_slope"] = safe_slope(window.loc[valid.index, "host_elapsed_s"], valid)

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
    return clean_feature_frame(features)


def clean_feature_frame(features):
    features = features.copy()
    numeric_cols = features.select_dtypes(include=[np.number]).columns
    features[numeric_cols] = features[numeric_cols].replace([np.inf, -np.inf], np.nan)
    if features[numeric_cols].isna().any().any():
        features[numeric_cols] = features[numeric_cols].fillna(features[numeric_cols].median(numeric_only=True)).fillna(0.0)
    return features


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


def feature_row_for_model(window, artifact, session_id="live", source_label="live"):
    window_size = float(artifact.get("window_size_s", window["host_elapsed_s"].max() - window["host_elapsed_s"].min()))
    start_s = float(window["host_elapsed_s"].min())
    end_s = float(window["host_elapsed_s"].max())
    row = pd.DataFrame([window_features(window, session_id, source_label, window_size, start_s, end_s)])
    row = clean_feature_frame(row)
    feature_columns = artifact["feature_columns"]
    for column in feature_columns:
        if column not in row:
            row[column] = 0.0
    return row[feature_columns].to_numpy(dtype=float), row
