import argparse
import base64
import json
import socket
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "thermal_live"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture radiometric frames from a tCam-Mini over Wi-Fi."
    )
    parser.add_argument("--host", default="192.168.4.1", help="tCam-Mini IP address.")
    parser.add_argument("--port", type=int, default=5001, help="tCam-Mini TCP port.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder where capture outputs will be written.",
    )
    parser.add_argument("--session-id", default="", help="Optional session id.")
    parser.add_argument("--label", default="unknown", help="Frame label.")
    parser.add_argument("--count", type=int, default=1, help="Number of frames to capture.")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds to wait between frames when count > 1.",
    )
    parser.add_argument(
        "--no-matrix",
        action="store_true",
        help="Do not save per-frame temperature matrix CSV files.",
    )
    return parser.parse_args()


def recv_packet(sock, timeout):
    sock.settimeout(0.5)
    deadline = time.time() + timeout
    buf = b""

    while time.time() < deadline:
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            continue

        if not chunk:
            time.sleep(0.05)
            continue

        buf += chunk
        while True:
            start = buf.find(b"\x02")
            if start < 0:
                break
            stop = buf.find(b"\x03", start + 1)
            if stop < 0:
                break
            raw = buf[start + 1 : stop]
            return json.loads(raw.decode("utf-8"))

    raise RuntimeError("Timed out waiting for a tCam response packet.")


def send_cmd(sock, cmd, timeout):
    payload = b"\x02" + json.dumps(cmd, separators=(",", ":")).encode("utf-8") + b"\x03"
    sock.sendall(payload)
    return recv_packet(sock, timeout)


def get_single_response(sock, cmd, timeout=10):
    return send_cmd(sock, cmd, timeout)


def decode_radiometric(packet):
    radiometric = packet.get("radiometric")
    if not radiometric and isinstance(packet.get("image"), dict):
        radiometric = packet["image"].get("radiometric")
    if not radiometric:
        raise RuntimeError("Image packet does not contain radiometric data.")

    raw = base64.b64decode(radiometric)
    values = np.frombuffer(raw, dtype="<u2")
    if values.size == 160 * 120:
        frame = values.reshape((120, 160))
    elif values.size == 80 * 60:
        frame = values.reshape((60, 80))
    else:
        raise RuntimeError(f"Unexpected radiometric frame size: {values.size} values")

    # tCam-Mini Lepton 3.5 TLinear output is centi-Kelvin in radiometric mode.
    temp_c = frame.astype(np.float32) / 100.0 - 273.15
    return temp_c


def save_png(temp_c, path):
    low, high = np.percentile(temp_c, [2, 98])
    if high <= low:
        high = low + 1.0
    norm = np.clip((temp_c - low) / (high - low), 0, 1)
    gray = (norm * 255).astype(np.uint8)
    scaled = cv2.resize(gray, (640, 480), interpolation=cv2.INTER_CUBIC)
    color = cv2.applyColorMap(scaled, cv2.COLORMAP_INFERNO)
    cv2.imwrite(str(path), color)


def make_summary_row(session_id, label, frame_index, start_time, temp_c):
    return {
        "session_id": session_id,
        "label": label,
        "frame_index": frame_index,
        "time_s": time.time() - start_time,
        "width": temp_c.shape[1],
        "height": temp_c.shape[0],
        "temp_min_c": float(np.min(temp_c)),
        "temp_mean_c": float(np.mean(temp_c)),
        "temp_p95_c": float(np.percentile(temp_c, 95)),
        "temp_max_c": float(np.max(temp_c)),
        "temp_center_c": float(temp_c[temp_c.shape[0] // 2, temp_c.shape[1] // 2]),
    }


def main():
    args = parse_args()
    session_id = args.session_id or time.strftime("tcam_%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    start_time = time.time()
    with socket.create_connection((args.host, args.port), timeout=8) as sock:
        status = get_single_response(sock, {"cmd": "get_status"}, timeout=5)
        config = get_single_response(sock, {"cmd": "get_config"}, timeout=5)
        (output_dir / "status.json").write_text(
            json.dumps({"status": status, "config": config}, indent=2),
            encoding="utf-8",
        )

        for frame_index in range(args.count):
            packet = get_single_response(sock, {"cmd": "get_image"}, timeout=15)
            temp_c = decode_radiometric(packet)

            stem = f"frame_{frame_index:06d}"
            save_png(temp_c, output_dir / f"{stem}.png")
            if not args.no_matrix:
                pd.DataFrame(temp_c).to_csv(
                    output_dir / f"{stem}_temp_c.csv",
                    index=False,
                    header=False,
                )
            rows.append(
                make_summary_row(session_id, args.label, frame_index, start_time, temp_c)
            )

            if frame_index + 1 < args.count:
                time.sleep(max(0.0, args.interval))

    pd.DataFrame(rows).to_csv(output_dir / "frames_summary.csv", index=False)
    print(f"Saved {len(rows)} frame(s) to {output_dir}")


if __name__ == "__main__":
    main()
