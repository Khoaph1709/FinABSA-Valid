from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
)
from datasets import Dataset
import pandas as pd

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

split_dataset = dataset.train_test_split(test_size=0.2, seed=42)
split_dataset["train"].to_csv("train_raw.csv", index=False)
split_dataset["test"].to_csv("test_raw.csv", index=False)
tokenized_dataset = split_dataset.map(preprocess, batched=True)

data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

training_args = Seq2SeqTrainingArguments(
    output_dir="./finabsa-other-masked",
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    learning_rate=3e-4,
    eval_strategy="epoch",
    save_strategy="epoch",
    predict_with_generate=True,
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

trainer.save_model("./finabsa-other-masked-final")
tokenizer.save_pretrained("./finabsa-other-masked-final")