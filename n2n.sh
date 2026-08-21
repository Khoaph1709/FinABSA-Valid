# RUN OG model prediction (load from authors' checkpoint)
# python run_finabsa_on_cafef.py \
#   --model /home/huylkq/repos/nlp/FinABSA-Valid/MODEL/FinABSA \
#   --input data/cafef_oct2022/model_inputs_strict.csv \
#   --output data/cafef_oct2022/model_predictions.csv


# python normalize_model_output.py \
#   --raw /home/huylkq/repos/nlp/FinABSA-Valid/data/cafef_oct2022/model_predictions.csv \
#   --inputs data/cafef_oct2022/model_inputs.csv \
#   --out data/cafef_oct2022/model_predictions.csv


# python validate_predictions.py
# python download_market_data.py \
#   --inputs data/cafef_oct2022/model_inputs_strict.csv \
#   --start 2022-05-01 \
#   --end 2022-12-31 \
#   --sleep 8.0
python run_experiments.py
python run_robustness.py
python build_report.py

