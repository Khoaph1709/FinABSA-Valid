from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
)
from datasets import Dataset
import argparse
import os
import pandas as pd
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "2,3"

parser = argparse.ArgumentParser(description="Train the FinABSA T5 model")
parser.add_argument("--epochs", type=float, default=8, help="Number of training epochs")
parser.add_argument("--batch-size", type=int, default=128, help="Train batch size per GPU")
parser.add_argument(
    "--eval-batch-size",
    type=int,
    default=None,
    help="Evaluation batch size per GPU (defaults to --batch-size)",
)
parser.add_argument("--num-gpus", type=int, default=1, help="Number of GPUs for distributed training")
parser.add_argument(
    "--output-dir",
    default="./MODEL",
    help="Directory for checkpoints and the final model",
)
parser.add_argument("--seed", type=int, default=42, help="Random seed for data split")
parser.add_argument(
    "--test-size",
    type=float,
    default=0.1,
    help="Fraction of the dataset reserved for evaluation",
)
args = parser.parse_args()

if args.eval_batch_size is None:
    args.eval_batch_size = args.batch_size

if (
    args.epochs <= 0
    or args.batch_size <= 0
    or args.eval_batch_size <= 0
    or args.num_gpus <= 0
    or not 0 < args.test_size < 1
):
    parser.error("epochs, batch sizes, num-gpus must be greater than zero and test-size must be between 0 and 1")

# Re-launch once under torchrun so --num-gpus works without a separate shell command.
if args.num_gpus > 1 and not os.environ.get("WORLD_SIZE"):
    command = [
        sys.executable,
        "-m",
        "torch.distributed.run",
        f"--nproc_per_node={args.num_gpus}",
        os.path.abspath(__file__),
        *sys.argv[1:],
    ]
    raise SystemExit(subprocess.run(command, check=False).returncode)

model_name = "t5-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

input_df = pd.read_csv("SEntFiN_input.csv")
output_df = pd.read_csv("SEntFiN_output.csv")

assert len(input_df) == len(output_df), "Input/output row counts don't match"

df = pd.DataFrame({
    "input": input_df["sentence"],
    "output": output_df["sentence"],
})

dataset = Dataset.from_pandas(df)

def preprocess(examples):
    model_inputs = tokenizer(examples["input"], max_length=64, truncation=True)
    labels = tokenizer(examples["output"], max_length=20, truncation=True)
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

split_dataset = dataset.train_test_split(test_size=args.test_size, seed=args.seed)
split_dataset["train"].to_csv("train_raw.csv", index=False)
split_dataset["test"].to_csv("test_raw.csv", index=False)
tokenized_dataset = split_dataset.map(preprocess, batched=True)

# Save the tokenized evaluation set for reproducible downstream analysis.
test_tokenized = tokenized_dataset["test"]
test_df = test_tokenized.to_pandas()
for col in ["input_ids", "labels"]:
    test_df[col] = test_df[col].apply(lambda values: " ".join(map(str, values)))
test_df[["input", "output", "input_ids", "labels"]].to_csv("test_set.csv", index=False)
print("Saved tokenized evaluation set to test_set.csv")

data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

training_args = Seq2SeqTrainingArguments(
    output_dir=args.output_dir,
    per_device_train_batch_size=args.batch_size,
    per_device_eval_batch_size=args.eval_batch_size,
    num_train_epochs=args.epochs,
    learning_rate=3e-4,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    eval_strategy="epoch",
    save_strategy="epoch",
    predict_with_generate=True,
    disable_tqdm=False,
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["test"],
    data_collator=data_collator,
    tokenizer=tokenizer,
)

trainer.train()

final_model_dir = os.path.join(args.output_dir, "finabsa-other-masked-final")
trainer.save_model(final_model_dir)
tokenizer.save_pretrained(final_model_dir)
