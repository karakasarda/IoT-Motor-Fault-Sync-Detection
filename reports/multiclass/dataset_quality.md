# Dataset Quality Report

Sessions: 44
Window rows: 6584

## Class Distribution

| label | sessions | duration_s | imu_rows |
| --- | --- | --- | --- |
| damping | 6 | 540 | 17363 |
| load | 8 | 720 | 23155 |
| mixed_anomaly | 4 | 359.9 | 11550 |
| normal | 12 | 1080 | 34770 |
| stall_risk | 6 | 540 | 17394 |
| vibration | 8 | 720 | 23060 |

## Window Counts

| window_size_s | damping | load | mixed_anomaly | normal | stall_risk | vibration |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 531 | 710 | 353 | 1059 | 530 | 707 |
| 5 | 207 | 278 | 137 | 411 | 206 | 275 |
| 10 | 99 | 134 | 65 | 195 | 98 | 131 |
| 15 | 63 | 86 | 41 | 123 | 62 | 83 |

## Quality Flags

| session_id | label | sync_p95_s | thermal_interval_max_s | last_edge_max_ms | thermal_max_c | flag_missing_file | flag_sync_p95_gt_0_75s | flag_thermal_gap_gt_2s | flag_edge_gap_gt_1000ms | flag_pulse_delta_low | flag_hot_gt_50c | flag_normal_outlier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| damping6 | damping | 0.4997 | 2.604 | 22 | 45.5 | False | False | True | False | False | False | False |
| load1 | load | 0.499 | 2.458 | 599 | 39.11 | False | False | True | False | False | False | False |
| load3 | load | 0.5456 | 2.691 | 6976 | 40.45 | False | False | True | True | False | False | False |
| load7 | load | 0.4963 | 2.038 | 39 | 39.99 | False | False | True | False | False | False | False |
| load8 | load | 0.502 | 2.362 | 120 | 50.33 | False | False | True | False | False | True | False |
| mixed_anomaly2 | mixed_anomaly | 0.4889 | 1.226 | 1167 | 40.52 | False | False | False | True | False | False | False |
| mixed_anomaly4 | mixed_anomaly | 0.5081 | 2.633 | 552 | 53.19 | False | False | True | False | False | True | False |
| normal10 | normal | 0.5001 | 2.152 | 19 | 45.29 | False | False | True | False | False | False | False |
| normal12 | normal | 0.5026 | 2.433 | 20 | 42.86 | False | False | True | False | False | False | False |
| normal3 | normal | 0.5242 | 2.405 | 18 | 38.39 | False | False | True | False | False | False | False |
| normal8 | normal | 0.5731 | 2.253 | 18 | 43.82 | False | False | True | False | False | False | False |
| stall_risk1 | stall_risk | 0.5415 | 2.621 | 428 | 40.11 | False | False | True | False | False | False | False |
| stall_risk2 | stall_risk | 0.5105 | 2.489 | 311 | 45.7 | False | False | True | False | False | False | False |
| stall_risk4 | stall_risk | 0.4962 | 2.029 | 430 | 46.38 | False | False | True | False | False | False | False |
| vibration3 | vibration | 0.5044 | 2.446 | 18 | 41.68 | False | False | True | False | False | False | False |
| vibration4 | vibration | 0.5057 | 2.739 | 328 | 44.04 | False | False | True | False | False | False | False |
| vibration7 | vibration | 0.5033 | 2.604 | 21 | 45.22 | False | False | True | False | False | False | False |
| vibration8 | vibration | 0.4999 | 2.352 | 22 | 44.09 | False | False | True | False | False | False | False |

## Session Summary

| session_id | label | duration_s | imu_rows | thermal_frames | sync_p95_s | gyro_mean | gyro_p95 | pulse_mean_hz | pulse_lt_20_pct | pulse_lt_45_pct | last_edge_max_ms | thermal_mean_c | thermal_max_c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| damping1 | damping | 89.97 | 2893 | 90 | 0.49 | 3.453 | 4.147 | 70.87 | 0.069 | 20.84 | 16 | 36.03 | 37.48 |
| damping2 | damping | 89.98 | 2892 | 90 | 0.493 | 3.594 | 4.127 | 104 | 0.069 | 0.069 | 18 | 39.7 | 41.29 |
| damping3 | damping | 90.01 | 2898 | 90 | 0.484 | 3.728 | 4.326 | 71.74 | 0.035 | 4.52 | 20 | 41.62 | 43.13 |
| damping4 | damping | 90 | 2901 | 90 | 0.485 | 3.642 | 4.172 | 62.98 | 0 | 2.172 | 19 | 40.76 | 42 |
| damping5 | damping | 90 | 2886 | 90 | 0.49 | 3.593 | 4.083 | 92.64 | 0.069 | 0.381 | 19 | 36.9 | 38.57 |
| damping6 | damping | 90.01 | 2893 | 90 | 0.5 | 3.38 | 3.953 | 61.62 | 0.104 | 0.104 | 22 | 42.97 | 45.5 |
| load1 | load | 89.98 | 2888 | 90 | 0.499 | 3.983 | 5.947 | 55.62 | 3.843 | 43.39 | 599 | 36.27 | 39.11 |
| load2 | load | 90.01 | 2894 | 90 | 0.494 | 3.844 | 5.027 | 61.97 | 21.94 | 38.32 | 191 | 37.61 | 39.32 |
| load3 | load | 90.02 | 2896 | 90 | 0.546 | 3.928 | 5.653 | 58.69 | 28.87 | 47.17 | 6976 | 38.03 | 40.45 |
| load4 | load | 90 | 2899 | 90 | 0.485 | 3.831 | 5.362 | 60.13 | 0.586 | 50.26 | 39 | 40.49 | 42.32 |
| load5 | load | 90.01 | 2899 | 90 | 0.488 | 3.625 | 4.8 | 57.77 | 8.52 | 45.57 | 69 | 42.33 | 44.7 |
| load6 | load | 89.99 | 2894 | 90 | 0.518 | 3.836 | 5.677 | 54.77 | 1.797 | 41.15 | 45 | 42.84 | 44.59 |
| load7 | load | 90.02 | 2893 | 90 | 0.496 | 3.913 | 5.711 | 56.7 | 0.138 | 64.92 | 39 | 38.12 | 39.99 |
| load8 | load | 90.01 | 2892 | 90 | 0.502 | 3.628 | 4.846 | 65.65 | 5.809 | 36.58 | 120 | 42.33 | 50.33 |
| mixed_anomaly1 | mixed_anomaly | 90 | 2886 | 90 | 0.489 | 5.735 | 16.33 | 56.82 | 10.64 | 23.87 | 755 | 41.36 | 43.08 |
| mixed_anomaly2 | mixed_anomaly | 89.98 | 2884 | 90 | 0.489 | 5.01 | 12.4 | 57.12 | 6.692 | 29.51 | 1167 | 39.1 | 40.52 |
| mixed_anomaly3 | mixed_anomaly | 89.98 | 2898 | 90 | 0.491 | 5.437 | 13.9 | 54.47 | 11.15 | 17.98 | 228 | 42.79 | 44.41 |
| mixed_anomaly4 | mixed_anomaly | 90 | 2882 | 90 | 0.508 | 5.907 | 16.91 | 57.41 | 8.917 | 12.21 | 552 | 46.74 | 53.19 |
| normal1 | normal | 90.02 | 2904 | 90 | 0.492 | 3.672 | 4.732 | 56.01 | 0 | 49.14 | 19 | 33.5 | 35 |
| normal10 | normal | 89.98 | 2894 | 90 | 0.5 | 3.377 | 4.795 | 70.66 | 0.069 | 0.069 | 19 | 42.64 | 45.29 |
| normal11 | normal | 90 | 2903 | 90 | 0.485 | 3.368 | 4.248 | 65.86 | 0 | 2.136 | 20 | 36.53 | 38.51 |
| normal12 | normal | 90.01 | 2895 | 90 | 0.503 | 3.432 | 5.028 | 69.64 | 0 | 0 | 20 | 40.48 | 42.86 |
| normal2 | normal | 90 | 2895 | 90 | 0.491 | 3.74 | 4.499 | 63.67 | 0.069 | 34.85 | 15 | 35.19 | 36.41 |
| normal3 | normal | 89.98 | 2896 | 90 | 0.524 | 3.427 | 4.666 | 51.94 | 0.069 | 54.73 | 18 | 33.55 | 38.39 |
| normal4 | normal | 89.98 | 2893 | 90 | 0.496 | 3.661 | 4.595 | 78.97 | 0 | 0 | 20 | 37.32 | 39.95 |
| normal5 | normal | 89.99 | 2892 | 90 | 0.498 | 3.569 | 4.757 | 103.8 | 0.104 | 0.104 | 20 | 39.83 | 42.13 |
| normal6 | normal | 89.99 | 2894 | 90 | 0.487 | 3.513 | 4.56 | 104.9 | 0.104 | 0.104 | 18 | 39.98 | 41.61 |
| normal7 | normal | 89.99 | 2899 | 90 | 0.502 | 3.441 | 4.577 | 105.9 | 0 | 0 | 18 | 40.89 | 43.32 |
| normal8 | normal | 90.01 | 2903 | 90 | 0.573 | 3.321 | 4.369 | 104.6 | 0 | 0 | 18 | 41.86 | 43.82 |
| normal9 | normal | 89.98 | 2902 | 90 | 0.49 | 3.325 | 4.264 | 104.3 | 0 | 0 | 18 | 39.68 | 42.08 |
| stall_risk1 | stall_risk | 90 | 2906 | 90 | 0.541 | 3.793 | 4.756 | 51.08 | 25.95 | 30.83 | 428 | 32.82 | 40.11 |
| stall_risk2 | stall_risk | 90 | 2895 | 90 | 0.51 | 3.755 | 4.737 | 62.77 | 30.95 | 37.82 | 311 | 38.37 | 45.7 |
| stall_risk3 | stall_risk | 89.99 | 2900 | 90 | 0.489 | 4.138 | 6.389 | 58.32 | 30.17 | 37.52 | 421 | 41.45 | 43.37 |
| stall_risk4 | stall_risk | 90.02 | 2900 | 90 | 0.496 | 3.616 | 4.828 | 78.47 | 16.59 | 19.38 | 430 | 43.29 | 46.38 |
| stall_risk5 | stall_risk | 90.02 | 2896 | 90 | 0.49 | 3.745 | 5.484 | 73.1 | 17.13 | 20.79 | 650 | 41.51 | 43.01 |
| stall_risk6 | stall_risk | 89.97 | 2897 | 90 | 0.488 | 3.506 | 5.153 | 56.44 | 12.91 | 20.47 | 173 | 45.91 | 47.77 |
| vibration1 | vibration | 89.99 | 2881 | 90 | 0.488 | 4.771 | 9.029 | 64.93 | 0 | 34.19 | 18 | 34.64 | 36.88 |
| vibration2 | vibration | 89.99 | 2869 | 90 | 0.49 | 5.596 | 15.4 | 77.53 | 0 | 18.23 | 20 | 37.33 | 38.77 |
| vibration3 | vibration | 90 | 2890 | 90 | 0.504 | 4.047 | 6.582 | 104.7 | 0.104 | 0.104 | 18 | 39.25 | 41.68 |
| vibration4 | vibration | 90.01 | 2897 | 90 | 0.506 | 4.112 | 5.684 | 106.2 | 0.656 | 0.967 | 328 | 40.56 | 44.03 |
| vibration5 | vibration | 90.01 | 2878 | 90 | 0.488 | 7.259 | 21.19 | 105.4 | 0.104 | 0.104 | 21 | 41.38 | 43.43 |
| vibration6 | vibration | 89.98 | 2855 | 90 | 0.495 | 10.83 | 33.39 | 94.31 | 0.035 | 0.911 | 21 | 41.24 | 43.04 |
| vibration7 | vibration | 89.98 | 2891 | 90 | 0.503 | 5.591 | 13 | 51 | 0.104 | 9.962 | 21 | 43.38 | 45.22 |
| vibration8 | vibration | 90 | 2899 | 90 | 0.5 | 5.14 | 11.67 | 58.8 | 0.138 | 5.761 | 22 | 41.11 | 44.09 |
