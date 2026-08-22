# Multi-year CafeF–FinABSA dataset

This package contains comparable October samples for 2019, 2020, 2021, and 2022. The October window is held constant across years to reduce month-of-year confounding while preserving the original October 2022 design.

## Periods and coverage

| Period | Articles | Crawl OK | Full input rows | Strict input rows | Strict rows with a price window | Price rows | Price window |
|---|---:|---:|---:|---:|---:|---:|---|
| 2019-10 | 1,040 | 1,039 | 583 | 154 | 141 | 8,320 | 2019-05-01--2019-12-31 |
| 2020-10 | 1,115 | 1,115 | 657 | 182 | 168 | 9,449 | 2020-05-01--2020-12-31 |
| 2021-10 | 1,506 | 1,491 | 991 | 297 | 281 | 11,935 | 2021-05-01--2021-12-31 |
| 2022-10 | 1,472 | 1,457 | 509 | 206 | 206 | 9,182 | 2022-05-01--2022-12-31 |
| **Total** | **5,133** | — | **2,740** | **839** | **796** | **38,886** | — |

Prices were downloaded through vnstock using the user's API key. The key was not written to this repository, output files, manifests, or the report. The downloader uses per-period cache files and keeps a download manifest. Thirty-two candidate symbols failed price retrieval; these are non-standard/non-Vietnamese strings or endpoint failures and are not assigned synthetic prices. Forty-three strict input rows do not have a usable price window and are excluded from `model_inputs_strict_analysis_ready.csv`.

## Main files

- `articles.csv`: combined CafeF article table with a `period` column.
- `model_inputs.csv`: combined full article–ticker inputs with target masking and a `period` column.
- `model_inputs_strict.csv`: combined high-confidence inputs (`entity_confidence >= 0.95`).
- `model_inputs_strict_analysis_ready.csv`: strict inputs whose ticker has a corresponding price series in the same period.
- `market_prices.csv`: combined OHLCV series for all successfully retrieved tickers and VNINDEX/VN30, with `period`, `price_window_start`, and `price_window_end`.
- `market_download_manifest.csv`: per-period ticker download status and row count.
- `multiyear_manifest_summary.csv`: sitemap/article crawl summary.
- `model_input_summary.csv`: per-period model-input summary.
- `multiyear_data_quality_summary.csv`: quality and coverage checks.
- `multiyear_data_quality.json`: machine-readable quality report.
- `multiyear_dataset_manifest.json`: machine-readable package manifest.

## Model inference

Run the trained checkpoint separately for each period, preserving period-specific output files:

```bash
python3 run_finabsa_on_cafef.py \
  --model ./YOUR_CHECKPOINT \
  --input data/cafef_multiyear/2019-10/model_inputs_strict.csv \
  --output data/cafef_multiyear/2019-10/model_predictions.csv
```

Repeat for `2020-10`, `2021-10`, and `2022-10`. Do not use the same output path for multiple periods. The model inputs are unlabeled inference inputs; they are not supervised training data.

## Interpretation

The market window is May through December of the same year. This provides pre-October observations for estimating the market model and post-event observations for lag windows without using future years. The October event date is mapped to the next available trading date according to the existing pipeline's trading-date mapping rule. Financial results should be reported as associations, not causal effects, because news timing, entity linking, omitted events, and market-wide shocks remain potential confounders.
