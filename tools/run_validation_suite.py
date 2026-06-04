import argparse
import os
import re
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import matthews_corrcoef

import modeling_features as mf
from run_modeling_pipeline import markdown_table, model_catalog


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "sync_captures"
DEFAULT_REPORT_DIR = ROOT / "reports" / "validation"
DEFAULT_COLLECTION_PLAN = ROOT / "docs" / "data_collection_plan.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run hard validation checks for the binary motor anomaly model."
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--target", choices=["binary"], default="binary")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--window-size", type=float, default=15.0)
    parser.add_argument("--feature-set", default="motion_only")
    parser.add_argument("--model", default="random_forest")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    return parser.parse_args()


def binary_metrics(y_true, y_pred):
    true = pd.Series(y_true).astype(str).reset_index(drop=True)
    pred = pd.Series(y_pred).astype(str).reset_index(drop=True)
    normal_mask = true == mf.NORMAL_LABEL
    anomaly_mask = true == mf.ANOMALY_LABEL
    normal_recall = float((pred[normal_mask] == mf.NORMAL_LABEL).mean()) if normal_mask.any() else np.nan
    anomaly_recall = float((pred[anomaly_mask] == mf.ANOMALY_LABEL).mean()) if anomaly_mask.any() else np.nan
    normal_fp_rate = float((pred[normal_mask] == mf.ANOMALY_LABEL).mean()) if normal_mask.any() else np.nan
    anomaly_fn_rate = float((pred[anomaly_mask] == mf.NORMAL_LABEL).mean()) if anomaly_mask.any() else np.nan
    present_recalls = [v for v in [normal_recall, anomaly_recall] if not np.isnan(v)]
    return {
        "windows": int(len(true)),
        "mcc": float(matthews_corrcoef(true, pred)) if true.nunique() > 1 or pred.nunique() > 1 else 0.0,
        "balanced_accuracy_present_classes": float(np.mean(present_recalls)) if present_recalls else np.nan,
        "normal_recall": normal_recall,
        "anomaly_recall": anomaly_recall,
        "normal_false_positive_rate": normal_fp_rate,
        "anomaly_false_negative_rate": anomaly_fn_rate,
        "predicted_anomaly_frac": float((pred == mf.ANOMALY_LABEL).mean()) if len(pred) else np.nan,
    }


def train_predict(train_data, test_data, feature_columns, model_name, seed):
    estimator = clone(model_catalog(seed)[model_name])
    x_train = train_data[feature_columns].to_numpy(dtype=float)
    y_train = train_data["binary_label"].astype(str).to_numpy()
    x_test = test_data[feature_columns].to_numpy(dtype=float)
    estimator.fit(x_train, y_train)
    return estimator.predict(x_test)


def load_feature_data(data_dir, window_size):
    records = mf.load_sessions(data_dir)
    features = mf.build_window_features(records, [window_size]).copy()
    return features[features["window_size_s"] == float(window_size)].reset_index(drop=True)


def run_loso(feature_data, feature_columns, model_name, seed):
    rows = []
    prediction_frames = []
    for session_id in sorted(feature_data["session_id"].unique()):
        test = feature_data[feature_data["session_id"] == session_id].copy()
        train = feature_data[feature_data["session_id"] != session_id].copy()
        pred = train_predict(train, test, feature_columns, model_name, seed)
        metrics = binary_metrics(test["binary_label"], pred)
        row = {
            "session_id": session_id,
            "source_label": str(test["source_label"].iloc[0]),
            "true_binary": str(test["binary_label"].iloc[0]),
            "alarm_label_majority": mf.ANOMALY_LABEL if metrics["predicted_anomaly_frac"] >= 0.5 else mf.NORMAL_LABEL,
            "window_anomaly_votes": int((pd.Series(pred) == mf.ANOMALY_LABEL).sum()),
            **metrics,
        }
        rows.append(row)
        prediction_frames.append(
            pd.DataFrame(
                {
                    "session_id": session_id,
                    "source_label": test["source_label"].to_numpy(),
                    "true_binary": test["binary_label"].to_numpy(),
                    "pred_binary": pred,
                }
            )
        )
    predictions = pd.concat(prediction_frames, ignore_index=True)
    return pd.DataFrame(rows), predictions


def run_family_holdout(feature_data, feature_columns, model_name, seed):
    rows = []
    families = sorted([label for label in feature_data["source_label"].unique() if label != mf.NORMAL_LABEL])
    for family in families:
        train = feature_data[feature_data["source_label"] != family].copy()
        test = feature_data[feature_data["source_label"] == family].copy()
        pred = train_predict(train, test, feature_columns, model_name, seed)
        metrics = binary_metrics(test["binary_label"], pred)
        rows.append(
            {
                "held_out_family": family,
                "train_sessions": int(train["session_id"].nunique()),
                "test_sessions": int(test["session_id"].nunique()),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def session_order_from_plan(plan_path):
    if not Path(plan_path).exists():
        return {}
    text = Path(plan_path).read_text(encoding="utf-8")
    ordered = re.findall(r"--session-id\s+([A-Za-z0-9_\\-]+)", text)
    return {session_id: index for index, session_id in enumerate(ordered)}


def run_time_order_split(feature_data, feature_columns, model_name, seed):
    order = session_order_from_plan(DEFAULT_COLLECTION_PLAN)
    sessions = sorted(
        feature_data["session_id"].unique(),
        key=lambda session_id: order.get(session_id, 10_000),
    )
    split_at = max(1, int(len(sessions) * 0.70))
    train_sessions = set(sessions[:split_at])
    test_sessions = set(sessions[split_at:])
    train = feature_data[feature_data["session_id"].isin(train_sessions)].copy()
    test = feature_data[feature_data["session_id"].isin(test_sessions)].copy()
    pred = train_predict(train, test, feature_columns, model_name, seed)
    metrics = binary_metrics(test["binary_label"], pred)
    return pd.DataFrame(
        [
            {
                "train_sessions": len(train_sessions),
                "test_sessions": len(test_sessions),
                "train_session_ids": ",".join(sessions[:split_at]),
                "test_session_ids": ",".join(sessions[split_at:]),
                **metrics,
            }
        ]
    )


def write_summary(loso, loso_predictions, family, time_order, output_path, args):
    aggregate = binary_metrics(loso_predictions["true_binary"], loso_predictions["pred_binary"])
    normal_session_fp = int(
        (
            (loso["true_binary"] == mf.NORMAL_LABEL)
            & (loso["alarm_label_majority"] == mf.ANOMALY_LABEL)
        ).sum()
    )
    min_family_recall = float(family["anomaly_recall"].min()) if len(family) else np.nan
    pass_loso = aggregate["mcc"] >= 0.85
    pass_normal_fp = normal_session_fp <= 2
    pass_family = min_family_recall >= 0.75
    deploy_status = "candidate" if pass_loso and pass_normal_fp and pass_family else "needs more validation"

    lines = [
        "# Hard Validation Summary",
        "",
        f"Model config: `{args.window_size:g}s`, `{args.feature_set}`, `{args.model}`",
        f"Deploy status: **{deploy_status}**",
        "",
        "## Acceptance Checks",
        "",
        markdown_table(
            pd.DataFrame(
                [
                    {"check": "LOSO MCC >= 0.85", "value": round(aggregate["mcc"], 4), "pass": pass_loso},
                    {"check": "Normal false positive sessions <= 2", "value": normal_session_fp, "pass": pass_normal_fp},
                    {"check": "Unseen anomaly family recall >= 0.75", "value": round(min_family_recall, 4), "pass": pass_family},
                ]
            )
        ),
        "",
        "## LOSO Aggregate",
        "",
        markdown_table(pd.DataFrame([aggregate]).round(4)),
        "",
        "## LOSO Session Results",
        "",
        markdown_table(loso.round(4)),
        "",
        "## Anomaly Family Holdout",
        "",
        markdown_table(family.round(4)),
        "",
        "## Time Order Split",
        "",
        markdown_table(time_order.round(4)),
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    feature_data = load_feature_data(args.data_dir, args.window_size)
    feature_columns = mf.feature_sets(feature_data)[args.feature_set]
    if not feature_columns:
        raise SystemExit(f"No columns found for feature set {args.feature_set}")

    loso, loso_predictions = run_loso(feature_data, feature_columns, args.model, args.seed)
    family = run_family_holdout(feature_data, feature_columns, args.model, args.seed)
    time_order = run_time_order_split(feature_data, feature_columns, args.model, args.seed)

    loso.to_csv(report_dir / "loso_results.csv", index=False)
    family.to_csv(report_dir / "anomaly_family_holdout.csv", index=False)
    time_order.to_csv(report_dir / "time_order_split.csv", index=False)
    write_summary(loso, loso_predictions, family, time_order, report_dir / "validation_summary.md", args)

    aggregate = binary_metrics(loso_predictions["true_binary"], loso_predictions["pred_binary"])
    print(
        {
            "windows": int(len(feature_data)),
            "sessions": int(feature_data["session_id"].nunique()),
            "loso_mcc": round(aggregate["mcc"], 4),
            "normal_false_positive_sessions": int(
                (
                    (loso["true_binary"] == mf.NORMAL_LABEL)
                    & (loso["alarm_label_majority"] == mf.ANOMALY_LABEL)
                ).sum()
            ),
            "min_family_recall": round(float(family["anomaly_recall"].min()), 4),
            "report_dir": str(report_dir),
        }
    )


if __name__ == "__main__":
    main()
