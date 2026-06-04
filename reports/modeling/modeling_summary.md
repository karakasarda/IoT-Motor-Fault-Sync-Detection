# Modeling Summary

## Best Group-CV Model

| target | window_size_s | feature_set | model | split_type | n_windows | n_features | accuracy | balanced_accuracy | precision_macro | recall_macro | f1_macro | mcc | normal_recall | anomaly_recall | f1_anomaly | folds | fold_mcc_mean | fold_mcc_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| binary | 15 | motion_only | random_forest | group_cv | 458 | 106 | 0.9978 | 0.9959 | 0.9985 | 0.9959 | 0.9972 | 0.9944 | 0.9919 | 1 | 0.9985 | 5 | 0.9939 | 0.0123 |

Saved model artifact: `D:\Projects\motor_anomali\IoT-Motor-Fault-Sync-Detection\models\best_binary_model.joblib`
Deploy status: candidate

## Best Model Classification Report

```text
              precision    recall  f1-score   support

      normal       1.00      0.99      1.00       123
     anomaly       1.00      1.00      1.00       335

    accuracy                           1.00       458
   macro avg       1.00      1.00      1.00       458
weighted avg       1.00      1.00      1.00       458

```

## Group-CV Top Results

| target | window_size_s | feature_set | model | split_type | n_windows | n_features | accuracy | balanced_accuracy | precision_macro | recall_macro | f1_macro | mcc | normal_recall | anomaly_recall | f1_anomaly | folds | fold_mcc_mean | fold_mcc_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| binary | 15 | motion_only | random_forest | group_cv | 458 | 106 | 0.9978 | 0.9959 | 0.9985 | 0.9959 | 0.9972 | 0.9944 | 0.9919 | 1 | 0.9985 | 5 | 0.9939 | 0.0123 |
| binary | 15 | motion_pulse | random_forest | group_cv | 458 | 144 | 0.9978 | 0.9959 | 0.9985 | 0.9959 | 0.9972 | 0.9944 | 0.9919 | 1 | 0.9985 | 5 | 0.9939 | 0.0123 |
| binary | 15 | motion_pulse_thermal | random_forest | group_cv | 458 | 209 | 0.9978 | 0.9959 | 0.9985 | 0.9959 | 0.9972 | 0.9944 | 0.9919 | 1 | 0.9985 | 5 | 0.9939 | 0.0123 |
| binary | 10 | motion_pulse | random_forest | group_cv | 722 | 144 | 0.9945 | 0.9897 | 0.9962 | 0.9897 | 0.9929 | 0.986 | 0.9795 | 1 | 0.9962 | 5 | 0.986 | 0.0143 |
| binary | 10 | motion_only | random_forest | group_cv | 722 | 106 | 0.9931 | 0.9872 | 0.9953 | 0.9872 | 0.9911 | 0.9824 | 0.9744 | 1 | 0.9953 | 5 | 0.9819 | 0.0159 |
| binary | 10 | motion_pulse_thermal | random_forest | group_cv | 722 | 209 | 0.9875 | 0.9769 | 0.9916 | 0.9769 | 0.984 | 0.9684 | 0.9538 | 1 | 0.9915 | 5 | 0.9687 | 0.0213 |
| binary | 15 | motion_only | extra_trees | group_cv | 458 | 106 | 0.9825 | 0.9675 | 0.9883 | 0.9675 | 0.9773 | 0.9556 | 0.935 | 1 | 0.9882 | 5 | 0.9461 | 0.1079 |
| binary | 15 | motion_only | svm_rbf | group_cv | 458 | 106 | 0.976 | 0.9656 | 0.973 | 0.9656 | 0.9692 | 0.9385 | 0.9431 | 0.9881 | 0.9837 | 5 | 0.9483 | 0.0918 |
| binary | 15 | motion_pulse | extra_trees | group_cv | 458 | 144 | 0.9738 | 0.9512 | 0.9827 | 0.9512 | 0.9656 | 0.9334 | 0.9024 | 1 | 0.9824 | 5 | 0.9327 | 0.0848 |
| binary | 10 | motion_only | logistic_regression | group_cv | 722 | 106 | 0.9709 | 0.9785 | 0.9523 | 0.9785 | 0.9642 | 0.9304 | 0.9949 | 0.962 | 0.9797 | 5 | 0.9298 | 0.0709 |
| binary | 10 | motion_pulse | extra_trees | group_cv | 722 | 144 | 0.9723 | 0.9487 | 0.9817 | 0.9487 | 0.9637 | 0.9299 | 0.8974 | 1 | 0.9814 | 5 | 0.9191 | 0.1334 |
| binary | 10 | motion_only | extra_trees | group_cv | 722 | 106 | 0.964 | 0.9333 | 0.9765 | 0.9333 | 0.9522 | 0.9088 | 0.8667 | 1 | 0.9759 | 5 | 0.9012 | 0.1355 |
| binary | 15 | motion_pulse | svm_rbf | group_cv | 458 | 144 | 0.9629 | 0.9489 | 0.956 | 0.9489 | 0.9524 | 0.9049 | 0.9187 | 0.9791 | 0.9747 | 5 | 0.9047 | 0.0755 |
| binary | 15 | motion_only | hist_gradient_boosting | group_cv | 458 | 106 | 0.9629 | 0.936 | 0.9694 | 0.936 | 0.9511 | 0.9048 | 0.878 | 0.994 | 0.9751 | 5 | 0.9174 | 0.0901 |
| binary | 15 | motion_pulse | hist_gradient_boosting | group_cv | 458 | 144 | 0.9629 | 0.936 | 0.9694 | 0.936 | 0.9511 | 0.9048 | 0.878 | 0.994 | 0.9751 | 5 | 0.9174 | 0.0901 |
| binary | 15 | motion_pulse_thermal | hist_gradient_boosting | group_cv | 458 | 209 | 0.9629 | 0.936 | 0.9694 | 0.936 | 0.9511 | 0.9048 | 0.878 | 0.994 | 0.9751 | 5 | 0.9174 | 0.0901 |
| binary | 15 | motion_only | logistic_regression | group_cv | 458 | 106 | 0.9585 | 0.9716 | 0.9331 | 0.9716 | 0.9496 | 0.9039 | 1 | 0.9433 | 0.9708 | 5 | 0.9122 | 0.0859 |
| binary | 10 | motion_pulse | svm_rbf | group_cv | 722 | 144 | 0.9612 | 0.9508 | 0.9508 | 0.9508 | 0.9508 | 0.9016 | 0.9282 | 0.9734 | 0.9734 | 5 | 0.9046 | 0.0624 |
| binary | 10 | motion_only | svm_rbf | group_cv | 722 | 106 | 0.9612 | 0.9363 | 0.9648 | 0.9363 | 0.9493 | 0.9006 | 0.8821 | 0.9905 | 0.9739 | 5 | 0.9059 | 0.0985 |
| binary | 15 | motion_pulse_thermal | extra_trees | group_cv | 458 | 209 | 0.9585 | 0.9228 | 0.9732 | 0.9228 | 0.9444 | 0.8945 | 0.8455 | 1 | 0.9724 | 5 | 0.8906 | 0.1409 |

## Leakage Diagnostic Top Results

These rows use random window splits and are diagnostic only. They must not be used for model selection.

| target | window_size_s | feature_set | model | split_type | n_windows | n_features | accuracy | balanced_accuracy | precision_macro | recall_macro | f1_macro | mcc | normal_recall | anomaly_recall | f1_anomaly | folds | fold_mcc_mean | fold_mcc_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| binary | 5 | motion_only | extra_trees | random_window_leakage_diagnostic | 1514 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_only | svm_rbf | random_window_leakage_diagnostic | 722 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_only | random_forest | random_window_leakage_diagnostic | 722 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_only | extra_trees | random_window_leakage_diagnostic | 722 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_only | hist_gradient_boosting | random_window_leakage_diagnostic | 722 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_only | knn | random_window_leakage_diagnostic | 722 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse | logistic_regression | random_window_leakage_diagnostic | 722 | 144 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse | svm_rbf | random_window_leakage_diagnostic | 722 | 144 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse | random_forest | random_window_leakage_diagnostic | 722 | 144 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse | extra_trees | random_window_leakage_diagnostic | 722 | 144 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse | hist_gradient_boosting | random_window_leakage_diagnostic | 722 | 144 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse | knn | random_window_leakage_diagnostic | 722 | 144 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse_thermal | logistic_regression | random_window_leakage_diagnostic | 722 | 209 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse_thermal | random_forest | random_window_leakage_diagnostic | 722 | 209 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse_thermal | extra_trees | random_window_leakage_diagnostic | 722 | 209 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 10 | motion_pulse_thermal | hist_gradient_boosting | random_window_leakage_diagnostic | 722 | 209 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 15 | motion_only | logistic_regression | random_window_leakage_diagnostic | 458 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 15 | motion_only | svm_rbf | random_window_leakage_diagnostic | 458 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 15 | motion_only | extra_trees | random_window_leakage_diagnostic | 458 | 106 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| binary | 15 | motion_pulse | logistic_regression | random_window_leakage_diagnostic | 458 | 144 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
