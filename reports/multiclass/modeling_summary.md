# Modeling Summary

## Best Group-CV Model

| target | window_size_s | feature_set | model | split_type | n_windows | n_features | accuracy | balanced_accuracy | precision_macro | recall_macro | f1_macro | mcc | folds | fold_mcc_mean | fold_mcc_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multiclass | 15 | motion_pulse | random_forest | group_cv | 458 | 144 | 0.9148 | 0.896 | 0.9006 | 0.896 | 0.8978 | 0.8955 | 4 | 0.8926 | 0.0522 |

Saved model artifact: `models\best_multiclass_model.joblib`
Deploy status: candidate

## Best Model Classification Report

```text
               precision    recall  f1-score   support

      damping       1.00      1.00      1.00        63
         load       0.81      0.85      0.83        86
mixed_anomaly       0.85      0.83      0.84        41
       normal       0.99      1.00      1.00       123
   stall_risk       0.79      0.71      0.75        62
    vibration       0.96      0.99      0.98        83

     accuracy                           0.91       458
    macro avg       0.90      0.90      0.90       458
 weighted avg       0.91      0.91      0.91       458

```

## Group-CV Top Results

| target | window_size_s | feature_set | model | split_type | n_windows | n_features | accuracy | balanced_accuracy | precision_macro | recall_macro | f1_macro | mcc | folds | fold_mcc_mean | fold_mcc_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multiclass | 15 | motion_pulse | random_forest | group_cv | 458 | 144 | 0.9148 | 0.896 | 0.9006 | 0.896 | 0.8978 | 0.8955 | 4 | 0.8926 | 0.0522 |
| multiclass | 15 | motion_pulse_thermal | random_forest | group_cv | 458 | 209 | 0.9061 | 0.8823 | 0.8929 | 0.8823 | 0.8864 | 0.8849 | 4 | 0.882 | 0.0587 |
| multiclass | 15 | motion_pulse | extra_trees | group_cv | 458 | 144 | 0.893 | 0.8729 | 0.8831 | 0.8729 | 0.8755 | 0.8695 | 4 | 0.8629 | 0.0556 |
| multiclass | 15 | motion_pulse | logistic_regression | group_cv | 458 | 144 | 0.8428 | 0.8403 | 0.8421 | 0.8403 | 0.8367 | 0.8094 | 4 | 0.8051 | 0.0632 |
| multiclass | 15 | motion_pulse_thermal | hist_gradient_boosting | group_cv | 458 | 209 | 0.8253 | 0.7958 | 0.8063 | 0.7958 | 0.7984 | 0.7859 | 4 | 0.7788 | 0.0523 |
| multiclass | 15 | motion_pulse | hist_gradient_boosting | group_cv | 458 | 144 | 0.8231 | 0.8023 | 0.81 | 0.8023 | 0.8035 | 0.7837 | 4 | 0.7751 | 0.0335 |
| multiclass | 15 | motion_only | logistic_regression | group_cv | 458 | 106 | 0.821 | 0.8098 | 0.8072 | 0.8098 | 0.8049 | 0.7823 | 4 | 0.7792 | 0.0206 |
| multiclass | 10 | motion_pulse_thermal | random_forest | group_cv | 722 | 209 | 0.8158 | 0.7799 | 0.78 | 0.7799 | 0.7712 | 0.777 | 4 | 0.7793 | 0.1068 |
| multiclass | 10 | motion_pulse | extra_trees | group_cv | 722 | 144 | 0.8116 | 0.7769 | 0.7838 | 0.7769 | 0.7675 | 0.7731 | 4 | 0.778 | 0.0946 |
| multiclass | 10 | motion_pulse | random_forest | group_cv | 722 | 144 | 0.8089 | 0.7704 | 0.7727 | 0.7704 | 0.7567 | 0.7706 | 4 | 0.7778 | 0.0972 |
| multiclass | 15 | motion_pulse_thermal | extra_trees | group_cv | 458 | 209 | 0.8122 | 0.7608 | 0.7807 | 0.7608 | 0.7658 | 0.7701 | 4 | 0.7707 | 0.111 |
| multiclass | 10 | motion_pulse | hist_gradient_boosting | group_cv | 722 | 144 | 0.8019 | 0.7748 | 0.7756 | 0.7748 | 0.7682 | 0.7595 | 4 | 0.7593 | 0.1005 |
| multiclass | 10 | motion_pulse_thermal | hist_gradient_boosting | group_cv | 722 | 209 | 0.8019 | 0.7683 | 0.7711 | 0.7683 | 0.7647 | 0.7588 | 4 | 0.7604 | 0.0971 |
| multiclass | 15 | motion_only | svm_rbf | group_cv | 458 | 106 | 0.8013 | 0.7665 | 0.7705 | 0.7665 | 0.7654 | 0.7574 | 4 | 0.7519 | 0.0643 |
| multiclass | 15 | motion_pulse | svm_rbf | group_cv | 458 | 144 | 0.7991 | 0.782 | 0.7837 | 0.782 | 0.7815 | 0.7549 | 4 | 0.7525 | 0.1038 |
| multiclass | 15 | motion_only | extra_trees | group_cv | 458 | 106 | 0.7969 | 0.7426 | 0.7695 | 0.7426 | 0.7474 | 0.7507 | 4 | 0.7571 | 0.0742 |
| multiclass | 15 | motion_pulse_thermal | logistic_regression | group_cv | 458 | 209 | 0.7948 | 0.791 | 0.7932 | 0.791 | 0.7844 | 0.7506 | 4 | 0.7452 | 0.0505 |
| multiclass | 15 | motion_only | hist_gradient_boosting | group_cv | 458 | 106 | 0.7882 | 0.7611 | 0.7713 | 0.7611 | 0.7647 | 0.7404 | 4 | 0.7322 | 0.0493 |
| multiclass | 15 | motion_only | random_forest | group_cv | 458 | 106 | 0.7838 | 0.7288 | 0.7653 | 0.7288 | 0.7342 | 0.7348 | 4 | 0.7436 | 0.0985 |
| multiclass | 10 | motion_pulse | logistic_regression | group_cv | 722 | 144 | 0.7798 | 0.7626 | 0.7695 | 0.7626 | 0.7569 | 0.7339 | 4 | 0.724 | 0.1365 |

## Leakage Diagnostic Top Results

These rows use random window splits and are diagnostic only. They must not be used for model selection.

| target | window_size_s | feature_set | model | split_type | n_windows | n_features | accuracy | balanced_accuracy | precision_macro | recall_macro | f1_macro | mcc | folds | fold_mcc_mean | fold_mcc_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multiclass | 15 | motion_pulse_thermal | extra_trees | random_window_leakage_diagnostic | 458 | 209 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| multiclass | 15 | motion_only | extra_trees | random_window_leakage_diagnostic | 458 | 106 | 0.9913 | 0.9889 | 0.9848 | 0.9889 | 0.9863 | 0.9894 | 1 | 0.9894 | 0 |
| multiclass | 15 | motion_pulse | extra_trees | random_window_leakage_diagnostic | 458 | 144 | 0.9913 | 0.9889 | 0.9928 | 0.9889 | 0.9905 | 0.9894 | 1 | 0.9894 | 0 |
| multiclass | 15 | motion_pulse | hist_gradient_boosting | random_window_leakage_diagnostic | 458 | 144 | 0.9913 | 0.9889 | 0.9928 | 0.9889 | 0.9905 | 0.9894 | 1 | 0.9894 | 0 |
| multiclass | 15 | motion_pulse | logistic_regression | random_window_leakage_diagnostic | 458 | 144 | 0.9913 | 0.9921 | 0.9948 | 0.9921 | 0.9933 | 0.9894 | 1 | 0.9894 | 0 |
| multiclass | 15 | motion_pulse | svm_rbf | random_window_leakage_diagnostic | 458 | 144 | 0.9913 | 0.9921 | 0.9948 | 0.9921 | 0.9933 | 0.9894 | 1 | 0.9894 | 0 |
| multiclass | 10 | motion_pulse_thermal | extra_trees | random_window_leakage_diagnostic | 722 | 209 | 0.9834 | 0.9757 | 0.9799 | 0.9757 | 0.9774 | 0.9797 | 1 | 0.9797 | 0 |
| multiclass | 15 | motion_pulse_thermal | logistic_regression | random_window_leakage_diagnostic | 458 | 209 | 0.9826 | 0.9841 | 0.9899 | 0.9841 | 0.9865 | 0.9789 | 1 | 0.9789 | 0 |
| multiclass | 15 | motion_pulse_thermal | hist_gradient_boosting | random_window_leakage_diagnostic | 458 | 209 | 0.9826 | 0.9778 | 0.9776 | 0.9778 | 0.9765 | 0.9789 | 1 | 0.9789 | 0 |
| multiclass | 10 | motion_pulse_thermal | hist_gradient_boosting | random_window_leakage_diagnostic | 722 | 209 | 0.9779 | 0.9694 | 0.9772 | 0.9694 | 0.9723 | 0.973 | 1 | 0.973 | 0 |
| multiclass | 10 | motion_pulse_thermal | random_forest | random_window_leakage_diagnostic | 722 | 209 | 0.9779 | 0.9653 | 0.9746 | 0.9653 | 0.9693 | 0.973 | 1 | 0.973 | 0 |
| multiclass | 15 | motion_pulse | random_forest | random_window_leakage_diagnostic | 458 | 144 | 0.9739 | 0.9667 | 0.971 | 0.9667 | 0.9663 | 0.9685 | 1 | 0.9685 | 0 |
| multiclass | 15 | motion_pulse_thermal | random_forest | random_window_leakage_diagnostic | 458 | 209 | 0.9739 | 0.9667 | 0.97 | 0.9667 | 0.966 | 0.9684 | 1 | 0.9684 | 0 |
| multiclass | 10 | motion_pulse | random_forest | random_window_leakage_diagnostic | 722 | 144 | 0.9724 | 0.9638 | 0.963 | 0.9638 | 0.963 | 0.9662 | 1 | 0.9662 | 0 |
| multiclass | 10 | motion_pulse | extra_trees | random_window_leakage_diagnostic | 722 | 144 | 0.9724 | 0.9604 | 0.9672 | 0.9604 | 0.9635 | 0.9661 | 1 | 0.9661 | 0 |
| multiclass | 10 | motion_pulse | hist_gradient_boosting | random_window_leakage_diagnostic | 722 | 144 | 0.9669 | 0.9589 | 0.9559 | 0.9589 | 0.9572 | 0.9593 | 1 | 0.9593 | 0 |
| multiclass | 2 | motion_pulse_thermal | extra_trees | random_window_leakage_diagnostic | 3890 | 209 | 0.9661 | 0.9528 | 0.9604 | 0.9528 | 0.9561 | 0.9584 | 1 | 0.9584 | 0 |
| multiclass | 15 | motion_only | svm_rbf | random_window_leakage_diagnostic | 458 | 106 | 0.9652 | 0.9599 | 0.9554 | 0.9599 | 0.9568 | 0.9576 | 1 | 0.9576 | 0 |
| multiclass | 15 | motion_pulse_thermal | svm_rbf | random_window_leakage_diagnostic | 458 | 209 | 0.9652 | 0.9599 | 0.9711 | 0.9599 | 0.9646 | 0.9575 | 1 | 0.9575 | 0 |
| multiclass | 2 | motion_pulse_thermal | hist_gradient_boosting | random_window_leakage_diagnostic | 3890 | 209 | 0.9651 | 0.9595 | 0.9592 | 0.9595 | 0.9591 | 0.9571 | 1 | 0.9571 | 0 |
