import argparse
import json
import socket
import threading
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import serial

from capture_vibration import (
    FEATURE_HEADERS,
    format_serial_error,
    parse_stream_line,
    prepare_stream,
)
from tcam_capture import decode_radiometric, get_single_response, save_png


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "sync_captures"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture Pico IMU/pulse and tCam-Mini frames on a shared host clock."
    )
    parser.add_argument("--imu-port", default="COM5", help="Serial port of the Pico.")
    parser.add_argument("--imu-baudrate", type=int, default=115200)
    parser.add_argument("--thermal-host", default="192.168.4.1")
    parser.add_argument("--thermal-port", type=int, default=5001)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--thermal-interval", type=float, default=1.0)
    parser.add_argument("--label", default="normal")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--soft-reset", action="store_true")
    parser.add_argument("--no-matrix", action="store_true")
    return parser.parse_args()


def rel_time(start_perf):
    return time.perf_counter() - start_perf


def capture_imu(ser, duration, start_perf, start_epoch, label, rows, raw_lines, errors):
    deadline = start_perf + duration

    while time.perf_counter() < deadline:
        try:
            line = ser.readline().decode("utf-8", errors="replace").strip()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"IMU read failed: {exc}")
            return

        if not line:
            continue

        host_elapsed_s = rel_time(start_perf)
        sample = parse_stream_line(line, label_override=label)
        raw_lines.append(line)
        if sample is None:
            continue

        sample.pop("raw_line", None)
        sample["host_epoch_s"] = start_epoch + host_elapsed_s
        sample["host_elapsed_s"] = host_elapsed_s
        rows.append(sample)


def capture_thermal(
    sock,
    duration,
    interval,
    start_perf,
    start_epoch,
    session_id,
    label,
    thermal_dir,
    no_matrix,
    rows,
    errors,
):
    frame_index = 0
    next_request_perf = start_perf

    while True:
        now = time.perf_counter()
        if now >= start_perf + duration:
            return
        if now < next_request_perf:
            time.sleep(min(0.05, next_request_perf - now))
            continue

        request_elapsed_s = rel_time(start_perf)
        try:
            packet = get_single_response(sock, {"cmd": "get_image"}, timeout=15)
            receive_elapsed_s = rel_time(start_perf)
            temp_c = decode_radiometric(packet)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Thermal capture failed: {exc}")
            return

        stem = f"frame_{frame_index:06d}"
        save_png(temp_c, thermal_dir / f"{stem}.png")
        if not no_matrix:
            pd.DataFrame(temp_c).to_csv(
                thermal_dir / f"{stem}_temp_c.csv",
                index=False,
                header=False,
            )

        rows.append(
            {
                "session_id": session_id,
                "label": label,
                "frame_index": frame_index,
                "host_epoch_s": start_epoch + receive_elapsed_s,
                "host_elapsed_s": receive_elapsed_s,
                "request_elapsed_s": request_elapsed_s,
                "capture_latency_s": receive_elapsed_s - request_elapsed_s,
                "width": int(temp_c.shape[1]),
                "height": int(temp_c.shape[0]),
                "temp_min_c": float(temp_c.min()),
                "temp_mean_c": float(temp_c.mean()),
                "temp_p95_c": thermal_p95(temp_c),
                "temp_max_c": float(temp_c.max()),
                "temp_center_c": float(
                    temp_c[temp_c.shape[0] // 2, temp_c.shape[1] // 2]
                ),
            }
        )
        frame_index += 1
        next_request_perf += max(0.05, interval)


def thermal_p95(temp_c):
    return float(pd.Series(temp_c.reshape(-1)).quantile(0.95))


def write_fused(imu, thermal, output_path):
    if imu.empty or thermal.empty:
        pd.DataFrame().to_csv(output_path, index=False)
        return pd.DataFrame()

    imu = imu.sort_values("host_elapsed_s").reset_index(drop=True)
    thermal = thermal.sort_values("host_elapsed_s").reset_index(drop=True)
    target_time = imu["host_elapsed_s"].to_numpy(dtype=float)
    source_time = thermal["host_elapsed_s"].to_numpy(dtype=float)

    fused = imu.copy()
    constant_columns = ["session_id", "label", "width", "height"]
    for column in constant_columns:
        if column in thermal:
            fused[f"thermal_{column}"] = thermal[column].iloc[0]

    numeric_columns = [
        column
        for column in thermal.columns
        if column
        not in {
            "session_id",
            "label",
            "host_epoch_s",
            "host_elapsed_s",
            "request_elapsed_s",
        }
        and pd.api.types.is_numeric_dtype(thermal[column])
    ]
    for column in numeric_columns:
        values = thermal[column].to_numpy(dtype=float)
        fused[f"thermal_{column}"] = np.interp(
            target_time,
            source_time,
            values,
            left=values[0],
            right=values[-1],
        )

    nearest_idx = np.searchsorted(source_time, target_time)
    nearest_errors = []
    for t, idx in zip(target_time, nearest_idx):
        candidates = []
        if idx < len(source_time):
            candidates.append(abs(source_time[idx] - t))
        if idx > 0:
            candidates.append(abs(source_time[idx - 1] - t))
        nearest_errors.append(min(candidates) if candidates else None)
    fused["thermal_nearest_frame_dt_s"] = nearest_errors
    fused["alignment_mode"] = "shared_host_elapsed_s_interpolation"
    fused.to_csv(output_path, index=False)
    return fused


def build_summary(imu, thermal, fused):
    summary = {
        "imu_rows": int(len(imu)),
        "thermal_frames": int(len(thermal)),
        "fused_rows": int(len(fused)),
        "alignment_mode": "shared_host_elapsed_s_interpolation",
    }
    if len(imu):
        summary.update(
            {
                "imu_duration_s": float(imu["host_elapsed_s"].iloc[-1] - imu["host_elapsed_s"].iloc[0]),
                "imu_sample_rate_hz": float(
                    len(imu)
                    / max(
                        1e-9,
                        imu["host_elapsed_s"].iloc[-1] - imu["host_elapsed_s"].iloc[0],
                    )
                ),
            }
        )
    if len(thermal):
        summary.update(
            {
                "thermal_duration_s": float(
                    thermal["host_elapsed_s"].iloc[-1]
                    - thermal["host_elapsed_s"].iloc[0]
                ),
                "thermal_interval_s_mean": float(
                    thermal["host_elapsed_s"].diff().dropna().mean()
                )
                if len(thermal) > 1
                else None,
                "thermal_interval_s_max": float(
                    thermal["host_elapsed_s"].diff().dropna().max()
                )
                if len(thermal) > 1
                else None,
            }
        )
    if len(fused) and "thermal_nearest_frame_dt_s" in fused:
        dt = pd.to_numeric(fused["thermal_nearest_frame_dt_s"], errors="coerce").dropna()
        summary.update(
            {
                "nearest_thermal_frame_dt_s_mean": float(dt.mean()),
                "nearest_thermal_frame_dt_s_p95": float(dt.quantile(0.95)),
                "nearest_thermal_frame_dt_s_max": float(dt.max()),
            }
        )
    return summary


def write_report_plot(imu, thermal, fused, output_path):
    fig, axes = plt.subplots(4, 1, figsize=(12, 12), constrained_layout=True)
    fig.suptitle("Senkron IMU + Pulse + tCam Testi", fontsize=16)

    if len(imu):
        axes[0].plot(imu["host_elapsed_s"], imu["acc_mag"], label="acc_mag")
        axes[0].plot(imu["host_elapsed_s"], imu["gyro_mag"], label="gyro_mag")
    axes[0].set_title("IMU ortak zaman ekseni")
    axes[0].set_ylabel("Magnitude")
    axes[0].legend(loc="upper right")
    axes[0].grid(alpha=0.3)

    if len(imu) and "pulse_rate_hz" in imu:
        axes[1].plot(imu["host_elapsed_s"], imu["pulse_rate_hz"], color="#16a34a")
    axes[1].set_title("Pulse hizi")
    axes[1].set_ylabel("Hz")
    axes[1].grid(alpha=0.3)

    if len(thermal):
        axes[2].plot(thermal["host_elapsed_s"], thermal["temp_mean_c"], label="mean")
        axes[2].plot(thermal["host_elapsed_s"], thermal["temp_max_c"], label="max")
    axes[2].set_title("Termal frame zamanlari")
    axes[2].set_ylabel("C")
    axes[2].legend(loc="upper right")
    axes[2].grid(alpha=0.3)

    if len(fused) and "thermal_nearest_frame_dt_s" in fused:
        axes[3].plot(
            fused["host_elapsed_s"],
            fused["thermal_nearest_frame_dt_s"],
            color="#9333ea",
        )
    axes[3].set_title("Her IMU orneginin en yakin termal frame farki")
    axes[3].set_xlabel("Ortak sure (s)")
    axes[3].set_ylabel("s")
    axes[3].grid(alpha=0.3)

    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main():
    args = parse_args()
    session_id = args.session_id or time.strftime("sync_%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / session_id
    thermal_dir = output_dir / "thermal"
    output_dir.mkdir(parents=True, exist_ok=True)
    thermal_dir.mkdir(parents=True, exist_ok=True)

    imu_rows = []
    thermal_rows = []
    raw_lines = []
    errors = []

    try:
        with serial.Serial(
            args.imu_port,
            args.imu_baudrate,
            timeout=0.25,
            write_timeout=1,
        ) as ser, socket.create_connection(
            (args.thermal_host, args.thermal_port), timeout=8
        ) as sock:
            time.sleep(1.0)
            raw_lines.extend(prepare_stream(ser, args.soft_reset))
            ser.reset_input_buffer()

            status = get_single_response(sock, {"cmd": "get_status"}, timeout=5)
            config = get_single_response(sock, {"cmd": "get_config"}, timeout=5)
            (output_dir / "status.json").write_text(
                json.dumps({"status": status, "config": config}, indent=2),
                encoding="utf-8",
            )
            ser.reset_input_buffer()

            start_perf = time.perf_counter()
            start_epoch = time.time()
            threads = [
                threading.Thread(
                    target=capture_imu,
                    args=(
                        ser,
                        args.duration,
                        start_perf,
                        start_epoch,
                        args.label,
                        imu_rows,
                        raw_lines,
                        errors,
                    ),
                    daemon=True,
                ),
                threading.Thread(
                    target=capture_thermal,
                    args=(
                        sock,
                        args.duration,
                        args.thermal_interval,
                        start_perf,
                        start_epoch,
                        session_id,
                        args.label,
                        thermal_dir,
                        args.no_matrix,
                        thermal_rows,
                        errors,
                    ),
                    daemon=True,
                ),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
    except serial.SerialException as exc:
        raise SystemExit(format_serial_error(args.imu_port, exc)) from exc

    if errors:
        (output_dir / "errors.json").write_text(
            json.dumps(errors, indent=2),
            encoding="utf-8",
        )

    imu = pd.DataFrame(imu_rows)
    thermal = pd.DataFrame(thermal_rows)
    if len(imu):
        preferred = ["host_epoch_s", "host_elapsed_s", *FEATURE_HEADERS]
        imu = imu[[column for column in preferred if column in imu.columns]]
    imu.to_csv(output_dir / "imu.csv", index=False)
    Path(output_dir / "imu_raw.log").write_text("\n".join(raw_lines), encoding="utf-8")
    thermal.to_csv(thermal_dir / "frames_summary.csv", index=False)

    fused = write_fused(imu, thermal, output_dir / "fused_imu_thermal.csv")
    summary = build_summary(imu, thermal, fused)
    summary["errors"] = errors
    summary["output_dir"] = str(output_dir)
    (output_dir / "sync_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    write_report_plot(imu, thermal, fused, output_dir / "sync_report.png")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
