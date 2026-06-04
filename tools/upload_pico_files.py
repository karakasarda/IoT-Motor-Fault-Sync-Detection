import argparse
import time
from pathlib import Path

import serial
from serial import SerialException


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload local MicroPython files to a connected Pico over raw REPL."
    )
    parser.add_argument("--port", default="COM10", help="Serial port of the Pico")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baudrate")
    parser.add_argument(
        "--source-dir",
        default=str(Path(__file__).resolve().parents[1] / "pico" / "imu_stream"),
        help="Folder that contains MicroPython source files",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=["main.py", "mpu6050.py"],
        help="Files to upload from the source directory",
    )
    parser.add_argument(
        "--soft-reset",
        action="store_true",
        help="Restart the Pico after uploading the files",
    )
    return parser.parse_args()


def enter_raw_repl(ser):
    ser.write(b"\x03\x03")
    ser.flush()
    time.sleep(0.3)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(b"\x01")
    ser.flush()
    time.sleep(0.3)
    intro = ser.read(512).decode("utf-8", errors="replace")
    if "raw REPL" not in intro:
        raise RuntimeError("Could not enter raw REPL. Close other serial tools first.")


def exit_raw_repl(ser):
    ser.write(b"\x02")
    ser.flush()
    time.sleep(0.2)


def exec_raw(ser, script):
    ser.write(script.encode("utf-8"))
    ser.write(b"\x04")
    ser.flush()
    time.sleep(0.3)
    response = ser.read(4096).decode("utf-8", errors="replace")
    if "Traceback" in response:
        raise RuntimeError(response.strip())
    return response


def upload_file(ser, remote_name, content):
    exec_raw(
        ser,
        "f = open({!r}, 'w')\n"
        "f.write('')\n"
        "f.close()\n".format(remote_name),
    )

    chunk_size = 512
    for idx in range(0, len(content), chunk_size):
        chunk = content[idx : idx + chunk_size]
        exec_raw(
            ser,
            "f = open({!r}, 'a')\n"
            "f.write({!r})\n"
            "f.close()\n".format(remote_name, chunk),
        )


def main():
    args = parse_args()
    source_dir = Path(args.source_dir)

    with serial.Serial(
        args.port,
        args.baudrate,
        timeout=0.5,
        write_timeout=1,
    ) as ser:
        enter_raw_repl(ser)

        for file_name in args.files:
            content = (source_dir / file_name).read_text(encoding="utf-8")
            upload_file(ser, file_name, content)
            print(f"Uploaded {file_name}")

        if args.soft_reset:
            try:
                exec_raw(ser, "import machine\nmachine.reset()\n")
            except SerialException:
                pass
        else:
            exit_raw_repl(ser)


if __name__ == "__main__":
    main()
