#!/usr/bin/env python3
"""
Lấy mẫu ngẫu nhiên từ CSV, tokenize và lưu dưới dạng test_set.csv
(giống định dạng mà train.py tạo ra) để dùng với evaluate_model.py.
"""

import pandas as pd
import argparse
import os
from transformers import AutoTokenizer
from datasets import Dataset

def main():
    parser = argparse.ArgumentParser(
        description="Lấy mẫu từ CSV, tokenize và lưu thành file CSV với cột input_ids, labels"
    )
    parser.add_argument("--input_csv", default="/home/huylkq/repos/nlp/FinABSA-Valid/SEntFiN_tgt.csv", help="File CSV đầu vào (phải có cột input và output)")
    parser.add_argument("--frac", type=float, default=0.1, help="Tỷ lệ lấy mẫu (mặc định 0.1 = 10%)")
    parser.add_argument("--seed", type=int, default=42, help="Seed (mặc định 42)")
    parser.add_argument("--input_col", default="sentence", help="Tên cột chứa input (mặc định: sentence)")
    parser.add_argument("--output_col", default="sentiment", help="Tên cột chứa output (mặc định: sentiment)")
    parser.add_argument("--output_csv", default="/home/huylkq/repos/nlp/FinABSA-Valid/finabsa_10%.csv", help="File đầu ra (mặc định: tên gốc + '_test.csv')")
    parser.add_argument("--tokenizer_name", default="/home/huylkq/repos/nlp/FinABSA-Valid/MODEL/FinABSA", help="Tên tokenizer (mặc định: t5-large)")
    parser.add_argument("--max_input_length", type=int, default=64, help="Độ dài tối đa input")
    parser.add_argument("--max_output_length", type=int, default=20, help="Độ dài tối đa output")
    args = parser.parse_args()

    # Đọc file CSV
    try:
        df = pd.read_csv(args.input_csv)
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return

    # Kiểm tra cột
    if args.input_col not in df.columns:
        print(f"Lỗi: cột '{args.input_col}' không tồn tại. Các cột có: {list(df.columns)}")
        return
    if args.output_col not in df.columns:
        print(f"Lỗi: cột '{args.output_col}' không tồn tại. Các cột có: {list(df.columns)}")
        return

    # Lấy mẫu
    sampled_df = df.sample(frac=args.frac, random_state=args.seed)
    print(f"Lấy {len(sampled_df)} dòng (tương ứng {args.frac*100:.1f}%) từ {len(df)} dòng")

    # Tạo DataFrame với cột input và output
    data = pd.DataFrame({
        "input": sampled_df[args.input_col],
        "output": sampled_df[args.output_col]
    })

    # Tokenize
    print("Đang tokenize...")
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_name)

    def preprocess(examples):
        model_inputs = tokenizer(
            examples["input"],
            max_length=args.max_input_length,
            truncation=True
        )
        labels = tokenizer(
            examples["output"],
            max_length=args.max_output_length,
            truncation=True
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    dataset = Dataset.from_pandas(data)
    tokenized_dataset = dataset.map(preprocess, batched=True)

    # Tạo DataFrame kết quả với đúng các cột cần cho evaluate_model.py
    result_df = pd.DataFrame({
        "input": data["input"],
        "output": data["output"],
        "input_ids": tokenized_dataset["input_ids"],
        "labels": tokenized_dataset["labels"]
    })
    # Chuyển list thành chuỗi cách nhau khoảng trắng (như train.py đã làm)
    result_df["input_ids"] = result_df["input_ids"].apply(lambda x: " ".join(map(str, x)))
    result_df["labels"] = result_df["labels"].apply(lambda x: " ".join(map(str, x)))

    # Xác định tên file đầu ra
    if args.output_csv is None:
        base, ext = os.path.splitext(args.input_csv)
        args.output_csv = f"{base}_test{ext}"

    # Lưu
    result_df.to_csv(args.output_csv, index=False)
    print(f"Đã lưu file tokenized vào: {args.output_csv}")
    print("Bạn có thể dùng file này với evaluate_model.py (--test_csv " + args.output_csv + ")")

if __name__ == "__main__":
    main()