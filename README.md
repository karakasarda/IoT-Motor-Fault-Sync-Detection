# IoT Motor Fault Sync Detection

Clean v2 repository for synchronized motor fault data collection and model training.

This repository intentionally starts without the old prototype datasets, old models, or old reports. New data should be collected with a shared host clock so Pico IMU/pulse data and tCam-Mini thermal frames can be aligned correctly.

## Hardware

- Raspberry Pi Pico
- MPU6050-compatible IMU on I2C
- Pulse input on Pico GP22
- tCam-Mini thermal camera over Wi-Fi

## Setup

```powershell
cd D:\Projects\motor_anomali\IoT-Motor-Fault-Sync-Detection
python -m pip install -r requirements.txt
```

Upload Pico firmware:

```powershell
python tools\upload_pico_files.py --port COM5 --soft-reset
```

Connect to the tCam-Mini Wi-Fi network before thermal capture:

```powershell
netsh wlan connect name="tCam-Mini-0CF1"
```

## Synchronized Capture

Use this command shape for all new data:

```powershell
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal1
```

Each session is written to:

```text
data\sync_captures\<session-id>\
```

Important outputs:

- `imu.csv`: IMU + pulse rows with `host_elapsed_s`
- `thermal\frames_summary.csv`: thermal summary rows with `host_elapsed_s`
- `fused_imu_thermal.csv`: IMU rows with interpolated thermal features
- `sync_summary.json`: capture quality summary
- `sync_report.png`: quick visual check

Heavy raw thermal files are ignored by git:

- `thermal\frame_*.png`
- `thermal\frame_*_temp_c.csv`

## Data Policy

Only collect and train from `data\sync_captures`. Do not mix old prototype data into this repository.

For the full scenario order, use [docs/data_collection_plan.md](docs/data_collection_plan.md).

## Binary Modeling Pipeline

After collecting synchronized sessions, run the binary normal-vs-anomaly model sweep:

```powershell
python tools\run_modeling_pipeline.py --data-dir data\sync_captures --target binary --windows 2 5 10 15 --seed 42
```

The pipeline writes:

- `data\processed\window_features.csv`
- `reports\modeling\dataset_quality.md`
- `reports\modeling\experiment_results.csv`
- `reports\modeling\confusion_matrix_best_binary.png`
- `reports\modeling\feature_importance_best_binary.png`
- `reports\modeling\modeling_summary.md`
- `models\best_binary_model.joblib`

Model selection uses grouped cross-validation by `session_id`. Random window split results are written only as leakage diagnostics.
