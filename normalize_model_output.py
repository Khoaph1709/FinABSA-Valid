from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

LABEL_RE = re.compile(r"\b(POSITIVE|NEGATIVE|NEUTRAL|POS|NEG|NEU)\b", re.I)
LABEL_ALIASES = {"positive": "positive", "negative": "negative", "neutral": "neutral", "pos": "positive", "neg": "negative", "neu": "neutral"}
SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


def parse_label(text: str) -> str:
    matches = LABEL_RE.findall(str(text))
    return LABEL_ALIASES.get(matches[-1].lower(), "unknown") if matches else "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default="data/cafef_oct2022/model_inputs_strict.csv")
    parser.add_argument("--raw", required=True, help="Model output CSV or one prediction per line")
    parser.add_argument("--out", default="data/cafef_oct2022/model_predictions.csv")
    args = parser.parse_args()

    inputs = pd.read_csv(args.inputs).fillna("")
    raw_path = Path(args.raw)
    try:
        raw = pd.read_csv(raw_path).fillna("")
    except Exception:
        raw = pd.DataFrame({"raw_model_output": raw_path.read_text(encoding="utf-8").splitlines()})

    if "sample_id" in raw.columns:
        raw_text_col = next((c for c in ["raw_model_output", "sentence", "output", "prediction", "text", "classification_output"] if c in raw.columns), None)
        if raw_text_col is None:
            raise ValueError(f"Could not identify prediction text column. Columns: {list(raw.columns)}")
        pred = raw[["sample_id", raw_text_col]].rename(columns={raw_text_col: "raw_model_output"})
        merged = inputs.merge(pred, on="sample_id", how="left", validate="one_to_one")
    else:
        raw_text_col = next((c for c in ["raw_model_output", "sentence", "output", "prediction", "text", "classification_output"] if c in raw.columns), raw.columns[0])
        if len(raw) != len(inputs):
            raise ValueError(f"Row-order adapter requires equal rows: inputs={len(inputs)} raw={len(raw)}")
        merged = inputs.copy()
        merged["raw_model_output"] = raw[raw_text_col].tolist()
        merged["alignment_method"] = "row_order"

    merged["classification_output"] = merged["raw_model_output"].map(parse_label)
    merged["sentiment_score"] = merged["classification_output"].map(SCORE)
    merged["inference_status"] = merged["classification_output"].map(lambda x: "ok" if x in SCORE else "unparsed")
    merged["model_name"] = merged.get("model_name", "external_model")
    merged.to_csv(args.out, index=False)
    print(f"saved={args.out} rows={len(merged)}")
    print(merged["classification_output"].value_counts(dropna=False).to_string())
    print("unparsed=", int((merged["inference_status"] != "ok").sum()))


if __name__ == "__main__":
    main()
