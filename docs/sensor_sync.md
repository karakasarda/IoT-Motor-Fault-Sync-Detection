# Sensor Synchronization Notes

The old capture flow started Pico and thermal capture from separate commands. That was not reliable for time alignment because Pico `time_ms` is device uptime and tCam `time_s` is local script runtime.

The v2 flow uses `tools/capture_sync_imu_tcam.py`. It starts both capture loops in one Python process and writes a shared `host_elapsed_s` timestamp into both streams.

Model training should use:

- IMU/pulse features from `imu.csv`
- thermal features from `thermal/frames_summary.csv`
- aligned features from `fused_imu_thermal.csv`

Do not train directly on raw `pulse_count`; use per-window pulse deltas, `pulse_rate_hz`, RPM, speed stability, and jitter features.

