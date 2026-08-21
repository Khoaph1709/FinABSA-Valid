from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

LABELS = {"positive", "neutral", "negative"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default="data/cafef_oct2022/model_inputs_strict.csv")
    parser.add_argument("--predictions", default="data/cafef_oct2022/model_predictions.csv")
    parser.add_argument("--outdir", default="data/cafef_oct2022/analysis")
    args = parser.parse_args()

    inputs = pd.read_csv(args.inputs).fillna("")
    preds = pd.read_csv(args.predictions).fillna("")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    required_in = {"sample_id", "article_id", "ticker", "published_at", "input_text"}
    required_pred = {"sample_id", "classification_output", "raw_model_output"}
    missing_in = required_in - set(inputs.columns)
    missing_pred = required_pred - set(preds.columns)
    if missing_in or missing_pred:
        raise ValueError(f"missing input columns={missing_in}; prediction columns={missing_pred}")

    input_ids = set(inputs["sample_id"])
    pred_ids = set(preds["sample_id"])
    report = {
        "input_rows": len(inputs),
        "prediction_rows": len(preds),
        "missing_predictions": len(input_ids - pred_ids),
        "unexpected_predictions": len(pred_ids - input_ids),
        "duplicate_input_ids": int(inputs["sample_id"].duplicated().sum()),
        "duplicate_prediction_ids": int(preds["sample_id"].duplicated().sum()),
    }
    preds["label"] = preds["classification_output"].astype(str).str.lower().str.strip()
    report["unknown_labels"] = int((~preds["label"].isin(LABELS)).sum())
    report["label_counts"] = preds["label"].value_counts(dropna=False).to_dict()
    pd.Series(report, dtype="object").to_json(outdir / "prediction_validation.json", force_ascii=False, indent=2)

    merged = inputs.merge(
        preds[[c for c in preds.columns if c not in inputs.columns or c in ["sample_id", "classification_output", "raw_model_output", "label", "positive_prob", "neutral_prob", "negative_prob", "sentiment_score", "model_name"]]],
        on="sample_id", how="left", suffixes=("", "_prediction"), validate="one_to_one",
    )
    merged["label"] = merged["label"].where(merged["label"].isin(LABELS), "unknown")
    score_map = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
    merged["sentiment_score"] = merged["label"].map(score_map)
    merged["published_at_dt"] = pd.to_datetime(merged["published_at"], errors="coerce", utc=True)
    merged["published_date"] = merged["published_at_dt"].dt.tz_convert(None).dt.date
    merged.to_csv(outdir / "article_ticker_sentiment.csv", index=False)

    valid = merged[merged["label"].isin(LABELS)].copy()
    # This file is genuinely ticker-day aggregate data. Do not align it to
    # article-level rows by position; downstream code joins on ticker/date.
    aggregate = (
        valid.groupby(["ticker", "published_date"], dropna=False)
        .agg(
            sentiment_score=("sentiment_score", "mean"),
            article_count=("article_id", "nunique"),
            positive_count=("label", lambda x: int((x == "positive").sum())),
            neutral_count=("label", lambda x: int((x == "neutral").sum())),
            negative_count=("label", lambda x: int((x == "negative").sum())),
        )
        .reset_index()
    )
    aggregate["negative_share"] = aggregate["negative_count"] / aggregate["article_count"].clip(lower=1)
    aggregate["positive_share"] = aggregate["positive_count"] / aggregate["article_count"].clip(lower=1)
    aggregate["neutral_share"] = aggregate["neutral_count"] / aggregate["article_count"].clip(lower=1)
    aggregate.to_csv(outdir / "article_ticker_day_sentiment.csv", index=False)
    print(f"validation={outdir / 'prediction_validation.json'}")
    print(f"article_ticker_rows={len(merged)} aggregate_rows={len(aggregate)}")
    print(pd.Series(report, dtype="object").to_string())


if __name__ == "__main__":
    main()
