# Synchronized Data Collection Plan

Run every command from the repository root:

```powershell
cd D:\Projects\motor_anomali\IoT-Motor-Fault-Sync-Detection
```

For every scenario:

1. Run the command.
2. Start the motor.
3. Apply the listed scenario for 90 seconds.
4. Stop the motor when the command finishes.
5. Wait for the listed break.

Use breaks seriously after `load`, `stall_risk`, and `mixed_anomaly`; otherwise thermal drift can make sessions look alike.

## Commands

```powershell
# 1 - Normal: motora hic dokunma
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal1
# Mola: 30 sn

# 2 - Vibration: 5-10 saniyede bir kisa hafif titresim ver
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration1
# Mola: 60 sn

# 3 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal2
# Mola: 30 sn

# 4 - Load: motoru durdurmadan 2-4 sn hafif zorla, birak, tekrar et
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load1
# Mola: 120 sn

# 5 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal3
# Mola: 30 sn

# 6 - Damping: govdeye/baglantiya bastirarak titresimi azalt, motoru durdurma
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label damping --session-id damping1
# Mola: 60 sn

# 7 - Vibration
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration2
# Mola: 60 sn

# 8 - Stall risk: 1-2 sn kisa tut, hemen birak; uzun sure kilitleme
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label stall_risk --session-id stall_risk1
# Mola: 180 sn

# 9 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal4
# Mola: 30 sn

# 10 - Load
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load2
# Mola: 120 sn

# 11 - Vibration
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration3
# Mola: 60 sn

# 12 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal5
# Mola: 30 sn

# 13 - Damping
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label damping --session-id damping2
# Mola: 60 sn

# 14 - Load
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load3
# Mola: 120 sn

# 15 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal6
# Mola: 30 sn

# 16 - Stall risk
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label stall_risk --session-id stall_risk2
# Mola: 180 sn

# 17 - Vibration
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration4
# Mola: 60 sn

# 18 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal7
# Mola: 30 sn

# 19 - Load
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load4
# Mola: 120 sn

# 20 - Damping
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label damping --session-id damping3
# Mola: 60 sn

# 21 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal8
# Mola: 30 sn

# 22 - Vibration
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration5
# Mola: 60 sn

# 23 - Stall risk
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label stall_risk --session-id stall_risk3
# Mola: 180 sn

# 24 - Load
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load5
# Mola: 120 sn

# 25 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal9
# Mola: 30 sn

# 26 - Damping
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label damping --session-id damping4
# Mola: 60 sn

# 27 - Vibration
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration6
# Mola: 60 sn

# 28 - Mixed anomaly: titresim + hafif yuk + kisa zorlama karisik uygula
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label mixed_anomaly --session-id mixed_anomaly1
# Mola: 180 sn

# 29 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal10
# Mola: 30 sn

# 30 - Load
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load6
# Mola: 120 sn

# 31 - Stall risk
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label stall_risk --session-id stall_risk4
# Mola: 180 sn

# 32 - Vibration
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration7
# Mola: 60 sn

# 33 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal11
# Mola: 30 sn

# 34 - Damping
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label damping --session-id damping5
# Mola: 60 sn

# 35 - Load
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load7
# Mola: 120 sn

# 36 - Mixed anomaly
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label mixed_anomaly --session-id mixed_anomaly2
# Mola: 180 sn

# 37 - Normal
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label normal --session-id normal12
# Mola: 30 sn

# 38 - Vibration
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label vibration --session-id vibration8
# Mola: 60 sn

# 39 - Stall risk
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label stall_risk --session-id stall_risk5
# Mola: 180 sn

# 40 - Load
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label load --session-id load8
# Mola: 120 sn

# 41 - Damping
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label damping --session-id damping6
# Mola: 60 sn

# 42 - Mixed anomaly
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label mixed_anomaly --session-id mixed_anomaly3
# Mola: 180 sn

# 43 - Stall risk
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label stall_risk --session-id stall_risk6
# Mola: 180 sn

# 44 - Mixed anomaly
python tools\capture_sync_imu_tcam.py --imu-port COM5 --duration 90 --thermal-interval 1.0 --soft-reset --label mixed_anomaly --session-id mixed_anomaly4
```

