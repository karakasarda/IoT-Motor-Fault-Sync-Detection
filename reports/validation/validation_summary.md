# Hard Validation Summary

Model config: `15s`, `motion_only`, `random_forest`
Deploy status: **needs more validation**

## Acceptance Checks

| check | value | pass |
| --- | --- | --- |
| LOSO MCC >= 0.85 | 0.9944 | True |
| Normal false positive sessions <= 2 | 0 | True |
| Unseen anomaly family recall >= 0.75 | 0 | False |

## LOSO Aggregate

| windows | mcc | balanced_accuracy_present_classes | normal_recall | anomaly_recall | normal_false_positive_rate | anomaly_false_negative_rate | predicted_anomaly_frac |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 458 | 0.9944 | 0.9959 | 0.9919 | 1 | 0.0081 | 0 | 0.7336 |

## LOSO Session Results

| session_id | source_label | true_binary | alarm_label_majority | window_anomaly_votes | windows | mcc | balanced_accuracy_present_classes | normal_recall | anomaly_recall | normal_false_positive_rate | anomaly_false_negative_rate | predicted_anomaly_frac |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| damping1 | damping | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| damping2 | damping | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| damping3 | damping | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| damping4 | damping | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| damping5 | damping | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| damping6 | damping | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| load1 | load | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| load2 | load | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| load3 | load | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| load4 | load | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| load5 | load | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| load6 | load | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| load7 | load | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| load8 | load | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| mixed_anomaly1 | mixed_anomaly | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| mixed_anomaly2 | mixed_anomaly | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| mixed_anomaly3 | mixed_anomaly | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| mixed_anomaly4 | mixed_anomaly | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| normal1 | normal | normal | normal | 0 | 11 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal10 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal11 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal12 | normal | normal | normal | 1 | 11 | 0 | 0.9091 | 0.9091 |  | 0.0909 |  | 0.0909 |
| normal2 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal3 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal4 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal5 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal6 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal7 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal8 | normal | normal | normal | 0 | 11 | 0 | 1 | 1 |  | 0 |  | 0 |
| normal9 | normal | normal | normal | 0 | 10 | 0 | 1 | 1 |  | 0 |  | 0 |
| stall_risk1 | stall_risk | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| stall_risk2 | stall_risk | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| stall_risk3 | stall_risk | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| stall_risk4 | stall_risk | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| stall_risk5 | stall_risk | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| stall_risk6 | stall_risk | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration1 | vibration | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration2 | vibration | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration3 | vibration | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration4 | vibration | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration5 | vibration | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration6 | vibration | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration7 | vibration | anomaly | anomaly | 10 | 10 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration8 | vibration | anomaly | anomaly | 11 | 11 | 0 | 1 |  | 1 |  | 0 | 1 |

## Anomaly Family Holdout

| held_out_family | train_sessions | test_sessions | windows | mcc | balanced_accuracy_present_classes | normal_recall | anomaly_recall | normal_false_positive_rate | anomaly_false_negative_rate | predicted_anomaly_frac |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| damping | 38 | 6 | 63 | 0 | 0 |  | 0 |  | 1 | 0 |
| load | 36 | 8 | 86 | 0 | 1 |  | 1 |  | 0 | 1 |
| mixed_anomaly | 40 | 4 | 41 | 0 | 1 |  | 1 |  | 0 | 1 |
| stall_risk | 38 | 6 | 62 | 0 | 1 |  | 1 |  | 0 | 1 |
| vibration | 36 | 8 | 83 | 0 | 1 |  | 1 |  | 0 | 1 |

## Time Order Split

| train_sessions | test_sessions | train_session_ids | test_session_ids | windows | mcc | balanced_accuracy_present_classes | normal_recall | anomaly_recall | normal_false_positive_rate | anomaly_false_negative_rate | predicted_anomaly_frac |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 30 | 14 | normal1,vibration1,normal2,load1,normal3,damping1,vibration2,stall_risk1,normal4,load2,vibration3,normal5,damping2,load3,normal6,stall_risk2,vibration4,normal7,load4,damping3,normal8,vibration5,stall_risk3,load5,normal9,damping4,vibration6,mixed_anomaly1,normal10,load6 | stall_risk4,vibration7,normal11,damping5,load7,mixed_anomaly2,normal12,vibration8,stall_risk5,load8,damping6,mixed_anomaly3,stall_risk6,mixed_anomaly4 | 148 | 0.9721 | 0.9762 | 0.9524 | 1 | 0.0476 | 0 | 0.8649 |
