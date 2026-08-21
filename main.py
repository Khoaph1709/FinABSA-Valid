
from __future__ import annotations

import torch
import pandas as pd

from torch.utils.data import Dataset, DataLoader
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


# ============================================================
# Config
# ============================================================

MODEL_PATH = (
    "/run/user/1008/huylkq/MODEL/finabsa-other-masked/checkpoint-510"
)

# MODEL_PATH = (
#     "/home/huylkq/repos/nlp/FinABSA-Valid/MODEL/FinABSA"
# )

INPUT_PATH = "/home/huylkq/repos/nlp/FinABSA-Valid/SEntFiN_input.csv"
OUTPUT_PATH = "/home/huylkq/repos/nlp/FinABSA-Valid/SEntFiN_output.csv"



BATCH_SIZE = 256

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

import re


VALID_LABELS = ["positive", "negative", "neutral"]


def parse_prediction(text: str) -> str:
    text = str(text).lower().strip()

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Tìm tất cả sentiment label
    matches = []

    for label in VALID_LABELS:
        if label in text:
            matches.append(
                (text.rfind(label), label)
            )

    if not matches:
        return ""

    # Lấy label xuất hiện cuối cùng
    matches.sort()

    return matches[-1][1]
# ============================================================
# Dataset
# ============================================================

class SentimentDataset(Dataset):

    def __init__(
        self,
        sentences: list[str],
    ):
        self.sentences = sentences

    def __len__(self):
        return len(self.sentences)

    def __getitem__(self, idx):
        return self.sentences[idx]


# ============================================================
# Collator
# ============================================================

class Collator:

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, batch):

        return self.tokenizer(
            batch,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )


# ============================================================
# Load model
# ============================================================

print(f"Using device: {DEVICE}")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_PATH
)

model = model.to(DEVICE)
model.eval()


# ============================================================
# Load input prompts and expected output labels
# ============================================================

input_df = pd.read_csv(INPUT_PATH)
output_df = pd.read_csv(OUTPUT_PATH)

if len(input_df) != len(output_df):
    raise ValueError(
        "Input/output row counts do not match: "
        f"{len(input_df)} != {len(output_df)}"
    )

if "sentence" not in input_df.columns or "sentence" not in output_df.columns:
    raise ValueError("Both CSV files must contain a 'sentence' column")

sentences = input_df["sentence"].astype(str).tolist()

true_labels = (
    output_df["sentence"]
    .astype(str)
    .map(parse_prediction)
    .tolist()
)


dataset = SentimentDataset(sentences)

dataloader = DataLoader(
    dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    collate_fn=Collator(tokenizer),
)


# ============================================================
# Inference
# ============================================================

predictions = []

with torch.inference_mode():

    for batch_idx, inputs in enumerate(dataloader):

        # Move inputs to GPU
        inputs = {
            key: value.to(DEVICE)
            for key, value in inputs.items()
        }

        # Generate predictions
        outputs = model.generate(
            **inputs
        )

        # Decode entire batch
        decoded = tokenizer.batch_decode(
            outputs,
            skip_special_tokens=True,
        )

        # Same parsing logic as your original code
        batch_preds = []

        for text in decoded:
            # print(text)
            pred = parse_prediction(text)
            # print(pred)
            batch_preds.append(pred)

        predictions.extend(batch_preds)

        print(
            f"Batch {batch_idx + 1}/"
            f"{len(dataloader)}",
            end="\r",
        )


# ============================================================
# Evaluation
# ============================================================

correct = 0

incorrect_lines = []

for sentence, true_label, pred in zip(
    sentences,
    true_labels,
    predictions,
):

    if pred == true_label:
        correct += 1

    else:
        incorrect_lines.append(
            f"{sentence}\t"
            f"true={true_label}\t"
            f"pred={pred}"
        )


accuracy = correct / len(sentences)

print()
print(
    f"Accuracy: {accuracy:.4f} "
    f"({correct}/{len(sentences)})"
)


# ============================================================
# Save incorrect predictions
# ============================================================

with open(
    "incorrect_predictions.txt",
    "w",
    encoding="utf-8",
) as f:

    f.write(
        "\n".join(incorrect_lines)
    )

print(
    f"Saved {len(incorrect_lines)} "
    f"incorrect predictions to "
    f"incorrect_predictions.txt"
)

