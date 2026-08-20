from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# Path to your saved model (use highest epoch checkpoint if final folder wasn't created)
model_path = "./finabsa-other-masked-final"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

input_text = "Other shines on seasonal demand; Target dull"

inputs = tokenizer(input_text, return_tensors="pt")
outputs = model.generate(**inputs, max_length=20)
decoded_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

print("Output:", decoded_output)