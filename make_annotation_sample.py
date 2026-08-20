from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default="data/cafef_oct2022/model_inputs_strict.csv")
    parser.add_argument("--predictions", default="data/cafef_oct2022/model_predictions.csv")
    parser.add_argument("--out", default="data/cafef_oct2022/annotation_sample.csv")
    parser.add_argument("--n", type=int, default=300)
    args = parser.parse_args()

    inputs = pd.read_csv(args.inputs).fillna("")
    if Path(args.predictions).exists():
        pred = pd.read_csv(args.predictions).fillna("")
        cols = [c for c in ["sample_id", "classification_output", "sentiment_score"] if c in pred.columns]
        inputs = inputs.merge(pred[cols], on="sample_id", how="left")
    else:
        inputs["classification_output"] = ""
        inputs["sentiment_score"] = ""
    inputs["predicted_stratum"] = inputs["classification_output"].replace("", "unpredicted").fillna("unpredicted")
    per = max(1, args.n // max(1, inputs["predicted_stratum"].nunique()))
    sample = inputs.groupby("predicted_stratum", group_keys=False).apply(lambda x: x.sample(min(per, len(x)), random_state=42), include_groups=False).reset_index(drop=True)
    if len(sample) < args.n:
        remain = inputs.loc[~inputs["sample_id"].isin(sample["sample_id"])].sample(min(args.n - len(sample), len(inputs) - len(sample)), random_state=42)
        sample = pd.concat([sample, remain], ignore_index=True)
    keep = ["sample_id", "article_id", "url", "published_at", "ticker", "target_surface", "raw_title", "input_text", "classification_output", "sentiment_score"]
    for c in ["annotator_1_label", "annotator_2_label", "adjudicated_label", "annotator_1_ticker", "annotator_2_ticker", "adjudicated_ticker", "notes"]:
        sample[c] = ""
    sample[keep + ["annotator_1_label", "annotator_2_label", "adjudicated_label", "annotator_1_ticker", "annotator_2_ticker", "adjudicated_ticker", "notes"]].to_csv(args.out, index=False)
    print(f"saved={args.out} rows={len(sample)}")
    print(sample.assign(predicted_stratum=sample.get("classification_output", "").replace("", "unpredicted")).get("predicted_stratum", pd.Series(dtype=str)).value_counts().to_string())


if __name__ == "__main__":
    main()
