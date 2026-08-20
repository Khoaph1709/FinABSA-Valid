from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

model = AutoModelForSeq2SeqLM.from_pretrained("amphora/FinABSA")
tokenizer = AutoTokenizer.from_pretrained("amphora/FinABSA")

# import pandas as pd

# df = pd.read_csv("SEntFiN_tgt.csv")

# correct = 0
# incorrect_lines = []

# for _, row in df.iterrows():
#     sentence = row["sentence"]
#     true_label = row["sentiment"]

#     inputs = tokenizer(sentence, return_tensors="pt")
#     output = model.generate(**inputs)
#     pred = tokenizer.decode(output[0], skip_special_tokens=True).strip().split()[-2][2:].lower()

#     if pred == true_label:
#         correct += 1
#     else:
#         incorrect_lines.append(f"{sentence}\ttrue={true_label}\tpred={pred}")

# accuracy = correct / len(df)
# print(f"Accuracy: {accuracy:.4f} ({correct}/{len(df)})")

# with open("incorrect_predictions.txt", "w", encoding="utf-8") as f:
#     f.write("\n".join(incorrect_lines))

input_str = "Telsa stocks dropped 42% while [TGT] rallied."
input = tokenizer(input_str, return_tensors="pt")
output = model.generate(**input)
print(tokenizer.decode(output[0]))