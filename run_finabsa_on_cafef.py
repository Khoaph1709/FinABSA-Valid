from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

LABEL_RE = re.compile(r"\b(POSITIVE|NEGATIVE|NEUTRAL|POS|NEG|NEU)\b", re.I)
LABEL_CANONICAL = {"positive": "positive", "pos": "positive", "negative": "negative", "neg": "negative", "neutral": "neutral", "neu": "neutral"}
LABEL_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


def parse_label(text: str) -> str:
    """
    Trích xuất nhãn sentiment (POSITIVE/NEGATIVE/NEUTRAL) từ câu văn bản.
    Tìm kiếm không phân biệt hoa/thường, hỗ trợ nhiều định dạng.
    """
    # Chuyển về chữ thường để so sánh dễ dàng
    text_lower = text.lower()
    
    # Tìm từ khóa sentiment
    if 'positive' in text_lower:
        return "POSITIVE"
    elif 'negative' in text_lower:
        return "NEGATIVE"
    elif 'neutral' in text_lower:
        return "NEUTRAL"
    elif 'pos' in text_lower:
        return "POSITIVE"
    elif 'neg' in text_lower:
        return "NEGATIVE"
    elif 'neu' in text_lower:
        return "NEUTRAL"

    else:
        # Nếu không tìm thấy, trả về NEUTRAL
        return "UNKNOWN"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FinABSA-compatible seq2seq model on CafeF target-masked rows")
    parser.add_argument("--model", required=True, help="HuggingFace model name or local checkpoint")
    parser.add_argument("--input", default="data/cafef_oct2022/model_inputs_strict.csv")
    parser.add_argument("--output", default="data/cafef_oct2022/model_predictions.csv")
    parser.add_argument("--mask-style", choices=["Target", "[TGT]"], default="Target")
    parser.add_argument("--max-input-length", type=int, default=64)
    parser.add_argument("--max-output-length", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--device", default="cuda", choices=["auto", "cpu", "cuda"])
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device == "auto":
        device = "cpu"
    input_df = pd.read_csv(args.input).fillna("")
    if "input_text" not in input_df.columns:
        raise ValueError("Input must contain input_text. Run prepare_model_inputs.py first.")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(device)
    # print(model)
    model.eval()

    records = []
    for start in range(0, len(input_df), args.batch_size):
        batch = input_df.iloc[start:start + args.batch_size]
        texts = batch["input_text"].tolist()
        if args.mask_style == "[TGT]":
            texts = [x.replace("Target", "[TGT]") for x in texts]
        inputs = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=args.max_input_length,
        ).to(device)
        with torch.no_grad():
            generated = model.generate(**inputs, max_length=args.max_output_length)
            # print(f"Generated: {generated}")
            decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)
            print(f"decoded: {decoded}")
        for (_, row), raw in zip(batch.iterrows(), decoded):
            label = parse_label(raw)
            print(f"Parsed label: {label}")
            records.append({
                "sample_id": row.get("sample_id", ""),
                "article_id": row.get("article_id", ""),
                "url": row.get("url", ""),
                "published_at": row.get("published_at", ""),
                "updated_at": row.get("updated_at", ""),
                "ticker": row.get("ticker", ""),
                "target_surface": row.get("target_surface", ""),
                "raw_title": row.get("raw_title", ""),
                "input_text": row.get("input_text", ""),
                "model_input_text": row.get("input_text", "") if args.mask_style == "Target" else row.get("input_text", "").replace("Target", "[TGT]"),
                "raw_model_output": raw,
                "classification_output": label,
                "positive_prob": "",
                "neutral_prob": "",
                "negative_prob": "",
                "sentiment_score": LABEL_SCORE.get(label, ""),
                "model_name": args.model,
                "mask_style": args.mask_style,
                "inference_status": "ok" if label != "unknown" else "unparsed",
            })

    out = pd.DataFrame(records)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"saved={args.output} rows={len(out)}")
    print(out["classification_output"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
