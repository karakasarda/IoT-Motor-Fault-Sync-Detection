import argparse
import sys
import time
from collections import deque
from pathlib import Path

import joblib
import pandas as pd
import serial

import modeling_features as mf
from capture_vibration import format_serial_error, parse_stream_line, prepare_stream


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "models" / "best_binary_model.joblib"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a live or replay binary normal/anomaly alarm from rolling motor windows."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--imu-port", help="Serial port of the Pico, for live mode.")
    source.add_argument("--replay-session", help="Path to a fused_imu_thermal.csv file, for hardware-free replay.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--window-size", type=float, default=None)
    parser.add_argument("--step", type=float, default=1.0)
    parser.add_argument("--soft-reset", action="store_true")
    parser.add_argument("--duration", type=float, default=None, help="Optional live-mode duration in seconds.")
    parser.add_argument("--history-size", type=int, default=5)
    parser.add_argument("--alarm-threshold", type=int, default=3)
    parser.add_argument("--replay-speed", type=float, default=0.0, help="0 runs replay as fast as possible; 1 is realtime.")
    return parser.parse_args()


def load_artifact(model_path):
    path = Path(model_path)
    if not path.exists():
        raise SystemExit(
            f"Model artifact not found: {path}\n"
            "Run: python tools\\run_modeling_pipeline.py --data-dir data\\sync_captures --target binary --windows 2 5 10 15 --seed 42"
        )
    artifact = joblib.load(path)
    required = {"model", "feature_columns", "window_size_s"}
    missing = required - set(artifact)
    if missing:
        raise SystemExit(f"Model artifact is missing keys: {sorted(missing)}")
    return artifact


def predict_window(window, artifact):
    x, feature_row = mf.feature_row_for_model(window, artifact)
    model = artifact["model"]
    pred = str(model.predict(x)[0])
    anomaly_proba = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x)[0]
        classes = list(getattr(model, "classes_", artifact.get("label_order", [])))
        if mf.ANOMALY_LABEL in classes:
            anomaly_proba = float(proba[classes.index(mf.ANOMALY_LABEL)])
    return pred, anomaly_proba, feature_row


def alarm_label(history, threshold):
    return mf.ANOMALY_LABEL if sum(label == mf.ANOMALY_LABEL for label in history) >= threshold else mf.NORMAL_LABEL


def latest_value(window, column):
    if column not in window or window.empty:
        return float("nan")
    return float(pd.to_numeric(window[column], errors="coerce").iloc[-1])


def print_prediction(t_s, window, pred, anomaly_proba, history, alarm):
    gyro = latest_value(window, "gyro_mag")
    acc = latest_value(window, "acc_mag")
    pulse = latest_value(window, "pulse_rate_hz")
    proba_text = "na" if anomaly_proba is None else f"{anomaly_proba:.3f}"
    print(
        f"t={t_s:7.2f}s | gyro={gyro:7.3f} | acc={acc:6.3f} | pulse={pulse:7.2f}Hz "
        f"| pred={pred:7s} | p_anom={proba_text:>5s} | alarm={alarm:7s} | history={list(history)}",
        flush=True,
    )


def run_replay(args, artifact):
    data = pd.read_csv(args.replay_session)
    if "host_elapsed_s" not in data:
        raise SystemExit("Replay CSV must include host_elapsed_s.")
    data = data.sort_values("host_elapsed_s").reset_index(drop=True)
    window_size = float(args.window_size or artifact["window_size_s"])
    step = float(args.step)
    t0 = float(data["host_elapsed_s"].iloc[0])
    t_end = float(data["host_elapsed_s"].iloc[-1])
    history = deque(maxlen=args.history_size)
    counts = {mf.NORMAL_LABEL: 0, mf.ANOMALY_LABEL: 0}
    alarm_counts = {mf.NORMAL_LABEL: 0, mf.ANOMALY_LABEL: 0}
    predictions = 0
    start = t0
    last_emit = time.perf_counter()

    while start + window_size <= t_end + 1e-9:
        end = start + window_size
        window = data[(data["host_elapsed_s"] >= start) & (data["host_elapsed_s"] < end)].copy()
        if len(window) >= max(8, int(window_size * 10)):
            pred, anomaly_proba, _ = predict_window(window, artifact)
            history.append(pred)
            alarm = alarm_label(history, args.alarm_threshold)
            counts[pred] = counts.get(pred, 0) + 1
            alarm_counts[alarm] = alarm_counts.get(alarm, 0) + 1
            predictions += 1
            print_prediction(end - t0, window, pred, anomaly_proba, history, alarm)
        if args.replay_speed > 0:
            elapsed = time.perf_counter() - last_emit
            sleep_s = max(0.0, (step / args.replay_speed) - elapsed)
            time.sleep(sleep_s)
            last_emit = time.perf_counter()
        start += step

    print(
        {
            "mode": "replay",
            "session": str(args.replay_session),
            "predictions": predictions,
            "pred_counts": counts,
            "alarm_counts": alarm_counts,
        }
    )


def run_live(args, artifact):
    window_size = float(args.window_size or artifact["window_size_s"])
    step = float(args.step)
    history = deque(maxlen=args.history_size)
    rows = []
    next_prediction_s = window_size
    start_perf = None

    try:
        with serial.Serial(args.imu_port, args.baudrate, timeout=0.25, write_timeout=1) as ser:
            time.sleep(1.0)
            prepare_stream(ser, args.soft_reset)
            ser.reset_input_buffer()
            start_perf = time.perf_counter()
            print(
                f"Live binary alarm started on {args.imu_port}. "
                f"window={window_size:g}s step={step:g}s history={args.history_size}/{args.alarm_threshold}",
                flush=True,
            )
            while True:
                now_s = time.perf_counter() - start_perf
                if args.duration is not None and now_s >= args.duration:
                    print("Live duration reached; stopping.")
                    return
                try:
                    line = ser.readline().decode("utf-8", errors="replace").strip()
                except Exception as exc:
                    raise SystemExit(f"IMU read failed: {exc}") from exc
                if line:
                    sample = parse_stream_line(line, label_override="live")
                    if sample is not None:
                        sample.pop("raw_line", None)
                        sample["host_elapsed_s"] = now_s
                        rows.append(sample)

                if now_s >= next_prediction_s:
                    frame = pd.DataFrame(rows)
                    if not frame.empty:
                        frame = frame[frame["host_elapsed_s"] >= now_s - window_size].copy()
                        rows = frame.to_dict("records")
                        if len(frame) >= max(8, int(window_size * 10)):
                            pred, anomaly_proba, _ = predict_window(frame, artifact)
                            history.append(pred)
                            alarm = alarm_label(history, args.alarm_threshold)
                            print_prediction(now_s, frame, pred, anomaly_proba, history, alarm)
                    next_prediction_s += step
    except serial.SerialException as exc:
        raise SystemExit(format_serial_error(args.imu_port, exc)) from exc
    except KeyboardInterrupt:
        print("\nLive binary alarm stopped by user.")


def main():
    args = parse_args()
    if args.alarm_threshold > args.history_size:
        raise SystemExit("--alarm-threshold cannot be greater than --history-size")
    artifact = load_artifact(args.model)
    if args.replay_session:
        run_replay(args, artifact)
    else:
        run_live(args, artifact)


if __name__ == "__main__":
    sys.exit(main())
