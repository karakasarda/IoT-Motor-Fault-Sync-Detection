import argparse
import asyncio
import json
import math
import os
import socket
import sys
import time
from collections import deque
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))

import pandas as pd
import serial
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import modeling_features as mf
from capture_vibration import format_serial_error, parse_stream_line, prepare_stream
from llm_interpreter import generate_operator_summary, ollama_status
from tcam_capture import decode_radiometric, get_single_response
from xai_explainer import (
    explain_window,
    global_feature_importance,
    json_safe,
    load_artifact,
    load_feature_baseline,
    predict_with_probabilities,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINARY_MODEL = ROOT / "models" / "best_binary_model.joblib"
DEFAULT_MULTICLASS_MODEL = ROOT / "models" / "best_multiclass_model.joblib"
DEFAULT_FEATURE_DATA = ROOT / "data" / "processed" / "window_features.csv"
DEFAULT_DATA_DIR = ROOT / "data" / "sync_captures"


def parse_args():
    parser = argparse.ArgumentParser(description="Serve the live motor anomaly dashboard backend.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--imu-port", help="Serial port of the Pico, for live mode.")
    source.add_argument("--replay-session", help="Path to fused_imu_thermal.csv, for hardware-free replay.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--binary-model", default=str(DEFAULT_BINARY_MODEL))
    parser.add_argument("--multiclass-model", default=str(DEFAULT_MULTICLASS_MODEL))
    parser.add_argument("--feature-data", default=str(DEFAULT_FEATURE_DATA))
    parser.add_argument("--window-size", type=float, default=None)
    parser.add_argument("--step", type=float, default=1.0)
    parser.add_argument("--history-size", type=int, default=5)
    parser.add_argument("--alarm-threshold", type=int, default=3)
    parser.add_argument("--soft-reset", action="store_true")
    parser.add_argument("--thermal-host", default="192.168.4.1")
    parser.add_argument("--thermal-port", type=int, default=5001)
    parser.add_argument("--thermal-interval", type=float, default=1.0)
    parser.add_argument("--disable-thermal", action="store_true", help="Do not poll tCam in live mode.")
    parser.add_argument("--stopped-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stopped-gyro-std", type=float, default=0.22)
    parser.add_argument("--stopped-gyro-range", type=float, default=1.20)
    parser.add_argument("--stopped-acc-std", type=float, default=0.005)
    parser.add_argument("--stopped-acc-range", type=float, default=0.030)
    parser.add_argument("--review-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--review-anomaly-low", type=float, default=0.35)
    parser.add_argument("--review-anomaly-high", type=float, default=0.85)
    parser.add_argument("--multiclass-min-confidence", type=float, default=0.65)
    parser.add_argument("--ollama-model", default="llama3.1:8b")
    parser.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--llm-interval", type=float, default=5.0)
    parser.add_argument("--llm-timeout", type=float, default=75.0)
    parser.add_argument("--xai-interval", type=float, default=3.0)
    parser.add_argument("--telemetry-interval", type=float, default=0.25)
    parser.add_argument("--replay-speed", type=float, default=0.0, help="0 runs as fast as possible; 1 is realtime.")
    parser.add_argument("--once", action="store_true", help="Emit one replay prediction bundle as JSON and exit.")
    return parser.parse_args()


def safe_float(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def latest(window, column):
    if column not in window or window.empty:
        return None
    return safe_float(pd.to_numeric(window[column], errors="coerce").iloc[-1])


def mean(window, column):
    if column not in window or window.empty:
        return None
    return safe_float(pd.to_numeric(window[column], errors="coerce").mean())


def sample_rate(window):
    if "host_elapsed_s" not in window or len(window) < 2:
        return None
    elapsed = pd.to_numeric(window["host_elapsed_s"], errors="coerce")
    duration = safe_float(elapsed.max() - elapsed.min())
    if not duration or duration <= 0:
        return None
    return len(window) / duration


def std(window, column):
    if column not in window or window.empty:
        return None
    values = pd.to_numeric(window[column], errors="coerce").dropna()
    if values.empty:
        return None
    return safe_float(values.std(ddof=0))


def value_range(window, column):
    if column not in window or window.empty:
        return None
    values = pd.to_numeric(window[column], errors="coerce").dropna()
    if values.empty:
        return None
    return safe_float(values.max() - values.min())


def telemetry_payload(window, mode, t_s):
    server_epoch_s = time.time()
    return json_safe(
        {
            "mode": mode,
            "timestamp_s": safe_float(t_s),
            "server_epoch_ms": int(server_epoch_s * 1000),
            "server_time": time.strftime("%H:%M:%S", time.localtime(server_epoch_s)),
            "gyro_mag": latest(window, "gyro_mag"),
            "acc_mag": latest(window, "acc_mag"),
            "pulse_rate_hz": latest(window, "pulse_rate_hz"),
            "thermal_mean_c": latest(window, "thermal_temp_mean_c"),
            "thermal_max_c": latest(window, "thermal_temp_max_c"),
            "sample_rate_hz": sample_rate(window),
            "window_rows": int(len(window)),
            "gyro_mag_mean": mean(window, "gyro_mag"),
            "gyro_mag_std": std(window, "gyro_mag"),
            "gyro_mag_range": value_range(window, "gyro_mag"),
            "acc_mag_mean": mean(window, "acc_mag"),
            "acc_mag_std": std(window, "acc_mag"),
            "acc_mag_range": value_range(window, "acc_mag"),
            "pulse_rate_hz_mean": mean(window, "pulse_rate_hz"),
        }
    )


def prediction_for_artifact(window, artifact):
    if artifact is None:
        return None, {}, None
    x, feature_row = mf.feature_row_for_model(window, artifact)
    prediction, probabilities = predict_with_probabilities(artifact, x)
    label_order = [str(label) for label in artifact.get("label_order", probabilities.keys())]
    ordered = {label: float(probabilities.get(label, 0.0)) for label in label_order}
    return prediction, ordered, feature_row


def probabilities_for_artifact(window, artifact):
    prediction, probabilities, _ = prediction_for_artifact(window, artifact)
    return prediction, probabilities


def feature_value(feature_row, column):
    if feature_row is None or column not in feature_row:
        return None
    return safe_float(feature_row[column].iloc[0])


def motor_state_from_features(feature_row, args):
    metrics = {
        "gyro_mag_std": feature_value(feature_row, "motion__gyro_mag_std"),
        "gyro_mag_range": feature_value(feature_row, "motion__gyro_mag_range"),
        "acc_mag_std": feature_value(feature_row, "motion__acc_mag_std"),
        "acc_mag_range": feature_value(feature_row, "motion__acc_mag_range"),
        "pulse_rate_hz_mean": feature_value(feature_row, "pulse__rate_hz_mean"),
        "pulse_rate_zero_frac": feature_value(feature_row, "pulse__rate_zero_frac"),
    }
    thresholds = {
        "gyro_mag_std": float(args.stopped_gyro_std),
        "gyro_mag_range": float(args.stopped_gyro_range),
        "acc_mag_std": float(args.stopped_acc_std),
        "acc_mag_range": float(args.stopped_acc_range),
    }
    if not args.stopped_gate:
        return {"state": "running", "gate_enabled": False, "metrics": metrics, "thresholds": thresholds}

    checks = [
        metrics["gyro_mag_std"] is not None and metrics["gyro_mag_std"] < thresholds["gyro_mag_std"],
        metrics["gyro_mag_range"] is not None and metrics["gyro_mag_range"] < thresholds["gyro_mag_range"],
        metrics["acc_mag_std"] is not None and metrics["acc_mag_std"] < thresholds["acc_mag_std"],
        metrics["acc_mag_range"] is not None and metrics["acc_mag_range"] < thresholds["acc_mag_range"],
    ]
    stopped = all(checks)
    reason = (
        "motion variance below running-motor floor"
        if stopped
        else "motion variance within running/anomaly evaluation range"
    )
    return {
        "state": mf.STOPPED_LABEL if stopped else "running",
        "gate_enabled": True,
        "reason": reason,
        "metrics": metrics,
        "thresholds": thresholds,
    }


def review_policy(raw_binary_prediction, anomaly_probability, raw_multiclass_prediction, multiclass_probabilities, args):
    top_multiclass_probability = None
    if multiclass_probabilities:
        top_multiclass_probability = max(float(value or 0.0) for value in multiclass_probabilities.values())

    if not args.review_gate:
        return {
            "state": "model_decision",
            "gate_enabled": False,
            "reason": "review gate disabled",
            "top_multiclass_probability": top_multiclass_probability,
        }

    low = float(args.review_anomaly_low)
    high = float(args.review_anomaly_high)
    is_gap = (
        raw_binary_prediction == mf.ANOMALY_LABEL
        and anomaly_probability is not None
        and low <= float(anomaly_probability) < high
    )
    low_multiclass_confidence = (
        top_multiclass_probability is not None
        and top_multiclass_probability < float(args.multiclass_min_confidence)
    )
    if is_gap or low_multiclass_confidence:
        reasons = []
        if is_gap:
            reasons.append(
                f"binary anomaly probability {float(anomaly_probability):.2f} is between trained normal/anomaly bands"
            )
        if low_multiclass_confidence:
            reasons.append(
                f"multiclass top probability {top_multiclass_probability:.2f} is below confidence threshold"
            )
        return {
            "state": mf.REVIEW_LABEL,
            "gate_enabled": True,
            "reason": "; ".join(reasons),
            "anomaly_probability_low": low,
            "anomaly_probability_high": high,
            "multiclass_min_confidence": float(args.multiclass_min_confidence),
            "top_multiclass_probability": top_multiclass_probability,
        }
    return {
        "state": "model_decision",
        "gate_enabled": True,
        "reason": "model confidence accepted",
        "anomaly_probability_low": low,
        "anomaly_probability_high": high,
        "multiclass_min_confidence": float(args.multiclass_min_confidence),
        "top_multiclass_probability": top_multiclass_probability,
    }


def alarm_label(history, threshold):
    anomaly_votes = sum(label == mf.ANOMALY_LABEL for label in history)
    return mf.ANOMALY_LABEL if anomaly_votes >= threshold else mf.NORMAL_LABEL


def poll_thermal_once(host, port):
    with socket.create_connection((host, port), timeout=4) as sock:
        packet = get_single_response(sock, {"cmd": "get_image"}, timeout=8)
    temp_c = decode_radiometric(packet)
    return {
        "thermal_temp_min_c": float(temp_c.min()),
        "thermal_temp_mean_c": float(temp_c.mean()),
        "thermal_temp_p95_c": float(pd.Series(temp_c.reshape(-1)).quantile(0.95)),
        "thermal_temp_max_c": float(temp_c.max()),
        "thermal_temp_center_c": float(temp_c[temp_c.shape[0] // 2, temp_c.shape[1] // 2]),
    }


def validation_warnings():
    warnings = []
    path = ROOT / "reports" / "validation" / "anomaly_family_holdout.csv"
    if path.exists():
        try:
            data = pd.read_csv(path)
            recall_cols = [c for c in data.columns if c.endswith("recall") or c == "recall"]
            if "heldout_family" in data and recall_cols:
                recall_col = recall_cols[0]
                weak = data[pd.to_numeric(data[recall_col], errors="coerce").fillna(0) < 0.75]
                for _, row in weak.iterrows():
                    warnings.append(
                        f"{row['heldout_family']} family holdout recall is below live acceptance threshold."
                    )
        except Exception as exc:
            warnings.append(f"Validation warning read failed: {exc}")
    if not warnings:
        warnings.append("Controlled prototype: independent new-day field validation is still required.")
    return warnings


class DashboardRuntime:
    def __init__(self, args):
        self.args = args
        self.binary_artifact = load_artifact(args.binary_model)
        self.multiclass_artifact = None
        self.multiclass_error = None
        if args.multiclass_model and Path(args.multiclass_model).exists():
            try:
                self.multiclass_artifact = load_artifact(args.multiclass_model)
            except Exception as exc:
                self.multiclass_error = str(exc)
        else:
            self.multiclass_error = f"Multiclass model not found: {args.multiclass_model}"
        self.binary_baseline = load_feature_baseline(args.feature_data, self.binary_artifact)
        self.multiclass_baseline = (
            load_feature_baseline(args.feature_data, self.multiclass_artifact)
            if self.multiclass_artifact is not None
            else None
        )
        self.binary_global_features = global_feature_importance(self.binary_artifact, top_n=16)
        self.binary_xai_candidates = [row["feature"] for row in self.binary_global_features]
        self.multiclass_global_features = (
            global_feature_importance(self.multiclass_artifact, top_n=12)
            if self.multiclass_artifact is not None
            else []
        )
        self.multiclass_xai_candidates = [row["feature"] for row in self.multiclass_global_features]
        self.history = deque(maxlen=args.history_size)
        self.last_llm_time = 0.0
        self.cached_llm = None
        self.last_xai_time = 0.0
        self.cached_xai = None
        self.warnings = validation_warnings()
        self.subscribers = set()
        self.live_task = None
        self.latest_live_error = None
        self.latest_status_event = None

    @property
    def window_size(self):
        return float(self.args.window_size or self.binary_artifact["window_size_s"])

    def status_payload(self, mode, last_error=None):
        if last_error is not None:
            self.latest_live_error = last_error
        server_epoch_s = time.time()
        ollama = ollama_status(
            endpoint=self.args.ollama_endpoint,
            model=self.args.ollama_model,
            timeout=1.0,
        )
        return json_safe(
            {
                "mode": mode,
                "server_epoch_ms": int(server_epoch_s * 1000),
                "server_time": time.strftime("%H:%M:%S", time.localtime(server_epoch_s)),
                "connected_clients": len(self.subscribers),
                "serial_port": self.args.imu_port,
                "thermal_host": self.args.thermal_host,
                "thermal_enabled": not self.args.disable_thermal,
                "binary_model_loaded": True,
                "binary_model": {
                    "path": str(self.args.binary_model),
                    "model_name": self.binary_artifact.get("model_name"),
                    "feature_set": self.binary_artifact.get("feature_set"),
                    "window_size_s": self.binary_artifact.get("window_size_s"),
                },
                "multiclass_model_loaded": self.multiclass_artifact is not None,
                "multiclass_error": self.multiclass_error,
                "ollama": ollama,
                "ollama_model": self.args.ollama_model,
                "validation_warnings": self.warnings,
                "last_error": last_error,
            }
        )

    def subscribe(self):
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        if self.latest_status_event is not None:
            try:
                queue.put_nowait(self.latest_status_event)
            except asyncio.QueueFull:
                pass
        return queue

    def unsubscribe(self, queue):
        self.subscribers.discard(queue)

    def publish(self, event_type, payload):
        event = {"type": event_type, "payload": json_safe(payload)}
        if event_type == "status":
            self.latest_status_event = event
        for queue in list(self.subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def ensure_live_task(self):
        if self.live_task is None or self.live_task.done():
            self.live_task = asyncio.create_task(live_producer(self))

    def build_prediction_only(self, window, mode, t_s):
        binary_prediction, binary_probabilities, feature_row = prediction_for_artifact(window, self.binary_artifact)
        motor_state = motor_state_from_features(feature_row, self.args)
        raw_binary_prediction = binary_prediction
        raw_anomaly_probability = binary_probabilities.get(mf.ANOMALY_LABEL)
        anomaly_probability = raw_anomaly_probability

        multiclass_prediction = None
        multiclass_probabilities = {}
        raw_multiclass_prediction = None
        raw_multiclass_probability = None
        if motor_state["state"] == mf.STOPPED_LABEL:
            binary_prediction = mf.STOPPED_LABEL
            alarm = mf.STOPPED_LABEL
            anomaly_probability = None
            multiclass_prediction = "not_running"
            self.history.append(mf.STOPPED_LABEL)
        else:
            if self.multiclass_artifact is not None:
                raw_multiclass_prediction, multiclass_probabilities = probabilities_for_artifact(
                    window,
                    self.multiclass_artifact,
                )
                raw_multiclass_probability = (
                    float(multiclass_probabilities.get(raw_multiclass_prediction, 0.0))
                    if raw_multiclass_prediction is not None
                    else None
                )
                multiclass_prediction = raw_multiclass_prediction
            decision_policy = review_policy(
                raw_binary_prediction,
                raw_anomaly_probability,
                raw_multiclass_prediction,
                multiclass_probabilities,
                self.args,
            )
            if decision_policy["state"] == mf.REVIEW_LABEL:
                binary_prediction = mf.REVIEW_LABEL
                alarm = mf.REVIEW_LABEL
                if raw_multiclass_prediction is not None:
                    multiclass_prediction = "uncertain"
                self.history.append(mf.REVIEW_LABEL)
            else:
                self.history.append(binary_prediction)
                alarm = alarm_label(self.history, self.args.alarm_threshold)
        if motor_state["state"] == mf.STOPPED_LABEL:
            decision_policy = {
                "state": mf.STOPPED_LABEL,
                "gate_enabled": True,
                "reason": motor_state.get("reason"),
            }

        prediction = json_safe(
            {
                "binary_prediction": binary_prediction,
                "alarm": alarm,
                "anomaly_probability": anomaly_probability,
                "model_binary_prediction": raw_binary_prediction,
                "model_anomaly_probability": raw_anomaly_probability,
                "model_multiclass_prediction": raw_multiclass_prediction,
                "model_multiclass_probability": raw_multiclass_probability,
                "binary_probabilities": binary_probabilities,
                "multiclass_prediction": multiclass_prediction,
                "multiclass_probabilities": multiclass_probabilities,
                "motor_state": motor_state,
                "decision_policy": decision_policy,
                "history": list(self.history),
                "alarm_rule": f"{self.args.alarm_threshold}/{self.args.history_size}",
                "window_size_s": self.window_size,
            }
        )
        return {"telemetry": telemetry_payload(window, mode, t_s), "prediction": prediction}

    def build_xai_bundle(self, window, multiclass_prediction):
        now = time.perf_counter()
        if self.cached_xai is not None and now - self.last_xai_time < self.args.xai_interval:
            return self.cached_xai

        xai = explain_window(
            window,
            self.binary_artifact,
            baseline=self.binary_baseline,
            focus_label=mf.ANOMALY_LABEL,
            top_n=5,
            candidate_features=self.binary_xai_candidates[:5],
        )
        multiclass_xai = None
        if self.multiclass_artifact is not None and self.multiclass_baseline is not None:
            multiclass_xai = explain_window(
                window,
                self.multiclass_artifact,
                baseline=self.multiclass_baseline,
                focus_label=multiclass_prediction,
                top_n=3,
                candidate_features=self.multiclass_xai_candidates[:3],
            )
        self.cached_xai = {
            "binary": xai,
            "multiclass": multiclass_xai,
            "global_top_features": self.binary_global_features[:12],
        }
        self.last_xai_time = now
        return self.cached_xai

    def build_prediction_bundle(self, window, mode, t_s, allow_llm=True):
        fast = self.build_prediction_only(window, mode, t_s)
        prediction = fast["prediction"]
        xai_bundle = self.build_xai_bundle(window, prediction.get("multiclass_prediction"))
        llm_summary = self.cached_llm
        if allow_llm:
            llm_summary = self.build_llm_summary(prediction, xai_bundle["binary"])

        return {
            "telemetry": fast["telemetry"],
            "prediction": prediction,
            "xai": xai_bundle,
            "llm_summary": llm_summary,
        }

    def build_llm_summary(self, prediction, binary_xai):
        now = time.perf_counter()
        if self.cached_llm is not None and now - self.last_llm_time < self.args.llm_interval:
            return self.cached_llm
        llm_payload = {
            "binary_prediction": prediction,
            "multiclass_probabilities": prediction.get("multiclass_probabilities", {}),
            "xai_top_features": binary_xai["top_features"],
            "sensor_summary": binary_xai["sensor_summary"],
            "validation_warnings": self.warnings,
        }
        llm_summary = generate_operator_summary(
            llm_payload,
            model=self.args.ollama_model,
            endpoint=self.args.ollama_endpoint,
            timeout=float(self.args.llm_timeout),
        )
        self.cached_llm = llm_summary
        self.last_llm_time = now
        return llm_summary


async def send_event(websocket, event_type, payload):
    await websocket.send_json({"type": event_type, "payload": json_safe(payload)})


def stopped_xai_bundle(prediction):
    motor_state = prediction.get("motor_state", {}) or {}
    metrics = motor_state.get("metrics", {}) or {}
    thresholds = motor_state.get("thresholds", {}) or {}
    rows = []
    for key in ["gyro_mag_std", "gyro_mag_range", "acc_mag_std", "acc_mag_range"]:
        rows.append(
            {
                "feature": f"motor_state__{key}",
                "family": "motor_state",
                "value": metrics.get(key),
                "normal_baseline": thresholds.get(key),
                "baseline_delta": None
                if metrics.get(key) is None or thresholds.get(key) is None
                else float(metrics[key]) - float(thresholds[key]),
                "focus_probability_delta": 0.0,
                "direction": "below_running_threshold",
            }
        )
    xai = {
        "target": "motor_state_gate",
        "model_name": "pre_model_stopped_gate",
        "feature_set": "motion_variance",
        "window_size_s": prediction.get("window_size_s"),
        "prediction": mf.STOPPED_LABEL,
        "focus_label": mf.STOPPED_LABEL,
        "focus_probability": None,
        "probabilities": {},
        "top_features": rows,
        "sensor_summary": metrics,
        "explanation_confidence": {
            "max_probability": None,
            "top_contribution_abs_sum": 0.0,
            "method": "stopped_gate_motion_threshold",
        },
    }
    return {"binary": xai, "multiclass": None, "global_top_features": []}


async def publish_explanations(runtime, frame, prediction):
    if (prediction.get("motor_state") or {}).get("state") == mf.STOPPED_LABEL:
        xai = stopped_xai_bundle(prediction)
        runtime.cached_xai = xai
        runtime.last_xai_time = time.perf_counter()
        runtime.publish("xai", xai)
        llm_summary = await asyncio.to_thread(
            runtime.build_llm_summary,
            prediction,
            xai["binary"],
        )
        runtime.publish("llm_summary", llm_summary)
        return

    xai = await asyncio.to_thread(
        runtime.build_xai_bundle,
        frame,
        prediction.get("multiclass_prediction"),
    )
    runtime.publish("xai", xai)
    llm_summary = await asyncio.to_thread(
        runtime.build_llm_summary,
        prediction,
        xai["binary"],
    )
    runtime.publish("llm_summary", llm_summary)


async def build_prediction_async(runtime, frame, mode, t_s):
    bundle = await asyncio.to_thread(runtime.build_prediction_only, frame, mode, t_s)
    return frame, bundle


def read_sessions():
    rows = []
    if not DEFAULT_DATA_DIR.exists():
        return rows
    for session_dir in sorted(DEFAULT_DATA_DIR.iterdir()):
        if not session_dir.is_dir():
            continue
        summary_path = session_dir / "sync_summary.json"
        summary = {}
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                summary = {}
        fused_path = session_dir / "fused_imu_thermal.csv"
        label = session_dir.name.rstrip("0123456789")
        if fused_path.exists():
            try:
                label = pd.read_csv(fused_path, usecols=["label"])["label"].mode().iloc[0]
            except Exception:
                pass
        rows.append(
            {
                "session_id": session_dir.name,
                "label": str(label),
                "imu_rows": summary.get("imu_rows"),
                "thermal_frames": summary.get("thermal_frames"),
                "fused_rows": summary.get("fused_rows"),
                "sync_p95_s": summary.get("nearest_thermal_frame_dt_s_p95"),
                "thermal_interval_s_max": summary.get("thermal_interval_s_max"),
            }
        )
    return json_safe(rows)


def read_validation():
    validation_dir = ROOT / "reports" / "validation"
    output = {"summary_markdown": "", "loso": [], "family_holdout": [], "time_order": []}
    summary_path = validation_dir / "validation_summary.md"
    if summary_path.exists():
        output["summary_markdown"] = summary_path.read_text(encoding="utf-8")
    for key, filename in [
        ("loso", "loso_results.csv"),
        ("family_holdout", "anomaly_family_holdout.csv"),
        ("time_order", "time_order_split.csv"),
    ]:
        path = validation_dir / filename
        if path.exists():
            output[key] = pd.read_csv(path).head(200).to_dict("records")
    return json_safe(output)


def read_modeling():
    output = {"binary": [], "multiclass": []}
    for key, path in [
        ("binary", ROOT / "reports" / "modeling" / "experiment_results.csv"),
        ("multiclass", ROOT / "reports" / "multiclass" / "experiment_results.csv"),
    ]:
        if path.exists():
            data = pd.read_csv(path)
            data = data[data["split_type"] == "group_cv"].sort_values("mcc", ascending=False).head(30)
            output[key] = data.to_dict("records")
    return json_safe(output)


async def stream_replay(websocket, runtime):
    args = runtime.args
    data = pd.read_csv(args.replay_session)
    if "host_elapsed_s" not in data:
        await send_event(websocket, "status", runtime.status_payload("replay", "Replay CSV must include host_elapsed_s."))
        return

    data = data.sort_values("host_elapsed_s").reset_index(drop=True)
    t0 = float(data["host_elapsed_s"].iloc[0])
    t_end = float(data["host_elapsed_s"].iloc[-1])
    start = t0
    last_emit = time.perf_counter()
    await send_event(websocket, "status", runtime.status_payload("replay"))

    while start + runtime.window_size <= t_end + 1e-9:
        end = start + runtime.window_size
        window = data[(data["host_elapsed_s"] >= start) & (data["host_elapsed_s"] < end)].copy()
        if len(window) >= max(8, int(runtime.window_size * 10)):
            bundle = runtime.build_prediction_only(window, "replay", end - t0)
            await send_event(websocket, "telemetry", bundle["telemetry"])
            await send_event(websocket, "prediction", bundle["prediction"])
            if runtime.cached_xai is None or time.perf_counter() - runtime.last_xai_time >= runtime.args.xai_interval:
                xai = await asyncio.to_thread(
                    runtime.build_xai_bundle,
                    window,
                    bundle["prediction"].get("multiclass_prediction"),
                )
                await send_event(websocket, "xai", xai)
                llm_summary = await asyncio.to_thread(
                    runtime.build_llm_summary,
                    bundle["prediction"],
                    xai["binary"],
                )
                await send_event(websocket, "llm_summary", llm_summary)
        if args.replay_speed > 0:
            elapsed = time.perf_counter() - last_emit
            await asyncio.sleep(max(0.0, (args.step / args.replay_speed) - elapsed))
            last_emit = time.perf_counter()
        else:
            await asyncio.sleep(0.05)
        start += args.step

    await send_event(websocket, "status", runtime.status_payload("replay", "Replay completed."))


async def live_producer(runtime):
    args = runtime.args
    rows = []
    latest_thermal = {}
    next_prediction_s = runtime.window_size
    telemetry_interval = max(0.05, float(args.telemetry_interval))
    next_telemetry_s = telemetry_interval
    next_thermal_s = max(0.2, args.thermal_interval)
    thermal_task = None
    explanation_task = None
    prediction_task = None
    runtime.publish("status", runtime.status_payload("live"))

    while True:
        try:
            with serial.Serial(args.imu_port, args.baudrate, timeout=0.05, write_timeout=1) as ser:
                await asyncio.sleep(1.0)
                prepare_stream(ser, args.soft_reset)
                ser.reset_input_buffer()
                start_perf = time.perf_counter()
                rows = []
                next_prediction_s = runtime.window_size
                telemetry_interval = max(0.05, float(args.telemetry_interval))
                next_telemetry_s = telemetry_interval
                next_thermal_s = max(0.2, args.thermal_interval)
                thermal_task = None
                explanation_task = None
                prediction_task = None
                runtime.latest_live_error = None
                runtime.publish("status", runtime.status_payload("live"))
                while True:
                    now_s = time.perf_counter() - start_perf
                    try:
                        line_bytes = await asyncio.to_thread(ser.readline)
                        line = line_bytes.decode("utf-8", errors="replace").strip()
                    except Exception as exc:
                        runtime.publish("status", runtime.status_payload("live", f"IMU read failed: {exc}"))
                        break

                    if prediction_task is not None and prediction_task.done():
                        try:
                            prediction_frame, prediction_bundle = prediction_task.result()
                            runtime.publish("prediction", prediction_bundle["prediction"])
                            xai_due = (
                                runtime.cached_xai is None
                                or time.perf_counter() - runtime.last_xai_time >= runtime.args.xai_interval
                            )
                            task_done = explanation_task is None or explanation_task.done()
                            if xai_due and task_done:
                                explanation_task = asyncio.create_task(
                                    publish_explanations(
                                        runtime,
                                        prediction_frame.copy(),
                                        prediction_bundle["prediction"],
                                    )
                                )
                        except Exception as exc:
                            runtime.publish("status", runtime.status_payload("live", f"Prediction failed: {exc}"))
                        prediction_task = None

                    if line:
                        sample = parse_stream_line(line, label_override="live")
                        if sample is not None:
                            sample.pop("raw_line", None)
                            sample["host_elapsed_s"] = now_s
                            sample.update(latest_thermal)
                            rows.append(sample)

                    if thermal_task is not None and thermal_task.done():
                        try:
                            latest_thermal = thermal_task.result()
                            next_thermal_s = now_s + max(0.2, args.thermal_interval)
                        except Exception as exc:
                            runtime.publish("status", runtime.status_payload("live", f"Thermal poll failed: {exc}"))
                            next_thermal_s = now_s + max(30.0, args.thermal_interval)
                        thermal_task = None

                    if now_s >= next_telemetry_s:
                        frame = pd.DataFrame(rows)
                        if not frame.empty:
                            frame = frame[frame["host_elapsed_s"] >= max(0.0, now_s - runtime.window_size)].copy()
                            rows = frame.to_dict("records")
                            runtime.publish("telemetry", telemetry_payload(frame, "live", now_s))
                        next_telemetry_s = now_s + telemetry_interval

                    if not args.disable_thermal and now_s >= next_thermal_s and thermal_task is None:
                        thermal_task = asyncio.create_task(
                            asyncio.to_thread(
                                poll_thermal_once,
                                args.thermal_host,
                                args.thermal_port,
                            )
                        )
                        next_thermal_s = now_s + max(30.0, args.thermal_interval)

                    if now_s >= next_prediction_s:
                        frame = pd.DataFrame(rows)
                        if not frame.empty:
                            frame = frame[frame["host_elapsed_s"] >= now_s - runtime.window_size].copy()
                            rows = frame.to_dict("records")
                            if prediction_task is None and len(frame) >= max(8, int(runtime.window_size * 10)):
                                prediction_task = asyncio.create_task(
                                    build_prediction_async(runtime, frame.copy(), "live", now_s)
                                )
                        next_prediction_s = now_s + args.step
                    await asyncio.sleep(0.01)
        except serial.SerialException as exc:
            runtime.publish("status", runtime.status_payload("live", format_serial_error(args.imu_port, exc)))
            await asyncio.sleep(3.0)
        except asyncio.CancelledError:
            return


async def stream_live(websocket, runtime):
    queue = runtime.subscribe()
    runtime.ensure_live_task()
    await send_event(websocket, "status", runtime.status_payload("live", runtime.latest_live_error))
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    finally:
        runtime.unsubscribe(queue)


def create_app(runtime):
    app = FastAPI(title="IoT Motor Fault Live Dashboard")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        mode = "replay" if runtime.args.replay_session else "live"
        return runtime.status_payload(mode)

    @app.get("/api/sessions")
    def sessions():
        return read_sessions()

    @app.get("/api/validation")
    def validation():
        return read_validation()

    @app.get("/api/modeling")
    def modeling():
        return read_modeling()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:
            if runtime.args.replay_session:
                await stream_replay(websocket, runtime)
            elif runtime.args.imu_port:
                await stream_live(websocket, runtime)
            else:
                await send_event(websocket, "status", runtime.status_payload("idle", "No --imu-port or --replay-session provided."))
                while True:
                    await asyncio.sleep(5.0)
        except WebSocketDisconnect:
            return

    static_dir = ROOT / "dashboard" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="dashboard")
    return app


def once_payload(args):
    if not args.replay_session:
        raise SystemExit("--once requires --replay-session")
    args.llm_interval = 0.0
    runtime = DashboardRuntime(args)
    data = pd.read_csv(args.replay_session).sort_values("host_elapsed_s").reset_index(drop=True)
    t0 = float(data["host_elapsed_s"].iloc[0])
    t_end = float(data["host_elapsed_s"].iloc[-1])
    start = t0
    last_bundle = None
    while start + runtime.window_size <= t_end + 1e-9:
        end = start + runtime.window_size
        window = data[(data["host_elapsed_s"] >= start) & (data["host_elapsed_s"] < end)].copy()
        if len(window) >= max(8, int(runtime.window_size * 10)):
            bundle = runtime.build_prediction_bundle(window, "replay", end - t0, allow_llm=True)
            bundle["status"] = runtime.status_payload("replay_once")
            last_bundle = bundle
            if len(runtime.history) >= args.alarm_threshold:
                return json_safe(bundle)
        start += args.step
    if last_bundle is not None:
        return json_safe(last_bundle)
    raise SystemExit("No valid replay window found.")


def main():
    args = parse_args()
    if args.alarm_threshold > args.history_size:
        raise SystemExit("--alarm-threshold cannot be greater than --history-size")
    if args.once:
        print(json.dumps(once_payload(args), indent=2, ensure_ascii=False))
        return 0

    runtime = DashboardRuntime(args)
    app = create_app(runtime)
    print(
        f"Serving dashboard backend on http://{args.host}:{args.port} "
        f"mode={'replay' if args.replay_session else 'live' if args.imu_port else 'idle'}",
        flush=True,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
