from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix, f1_score, matthews_corrcoef


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default="data/cafef_oct2022/annotation_sample.csv")
    parser.add_argument("--predictions", default="data/cafef_oct2022/model_predictions.csv")
    parser.add_argument("--gold-column", default="adjudicated_label")
    parser.add_argument("--outdir", default="data/cafef_oct2022/analysis/intrinsic")
    args = parser.parse_args()

    gold = pd.read_csv(args.gold).fillna("")
    pred = pd.read_csv(args.predictions).fillna("")
    df = gold[["sample_id", args.gold_column]].merge(pred[["sample_id", "classification_output"]], on="sample_id", how="inner")
    df[args.gold_column] = df[args.gold_column].astype(str).str.lower().str.strip()
    df["classification_output"] = df["classification_output"].astype(str).str.lower().str.strip()
    df = df[df[args.gold_column].isin(["positive", "neutral", "negative"]) & df["classification_output"].isin(["positive", "neutral", "negative"])]
    if df.empty:
        raise ValueError("No valid adjudicated labels. Fill annotation_sample.csv first.")
    labels = ["negative", "neutral", "positive"]
    y_true, y_pred = df[args.gold_column], df["classification_output"]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    metrics = {
        "n": len(df),
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0),
        "mcc": matthews_corrcoef(y_true, y_pred),
    }
    pd.DataFrame([metrics]).to_csv(outdir / "metrics.csv", index=False)
    pd.DataFrame(classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)).T.to_csv(outdir / "classification_report.csv")
    pd.DataFrame(confusion_matrix(y_true, y_pred, labels=labels), index=labels, columns=labels).to_csv(outdir / "confusion_matrix.csv")
    print(pd.Series(metrics).to_string())


if __name__ == "__main__":
    main()
