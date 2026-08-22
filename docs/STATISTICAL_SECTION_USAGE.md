# How to integrate the statistical validation section

The completed section is `statistical_validation_multiyear.tex`. It is a section fragment, not a standalone document. Put it in the same directory as the main report and include it after the model/related-work sections:

```latex
\input{statistical_validation_multiyear.tex}
```

The main preamble should load:

```latex
\usepackage{amsmath,amssymb,booktabs,graphicx,longtable,array,hyperref}
```

The section expects the following files in four period-specific directories next to `main.tex`:

```text
2019-10/analysis/figures/abnormal_return_by_label.png
2019-10/analysis/figures/sentiment_vs_abnormal_return.png
2020-10/analysis/figures/abnormal_return_by_label.png
2020-10/analysis/figures/sentiment_vs_abnormal_return.png
2021-10/analysis/figures/abnormal_return_by_label.png
2021-10/analysis/figures/sentiment_vs_abnormal_return.png
2022-10/analysis/figures/abnormal_return_by_label.png
2022-10/analysis/figures/sentiment_vs_abnormal_return.png
```

The two figures are shown as four-panel composites: one panel for each October period. The paths are intentionally relative to the directory containing `main.tex`; do not prepend `data/cafef_multiyear/` unless your own report is stored inside that directory.

Compile the main document with XeLaTeX or LuaLaTeX if the main report contains Vietnamese text. The section itself contains no `\begin{document}` or `\end{document}` and should not be compiled as a separate document.

All values in the section are from the completed `model_predictions(1).csv` multi-year run. The supporting numerical tables are under `data/cafef_multiyear/analysis_multiyear/`, including:

- `car_primary_all.csv`
- `news_day_control_tests.csv`
- `sentiment_group_tests.csv`
- `panel_key_coefficients.csv`
- `robustness_summary.csv`
- `prediction_validation_clean.csv`
- `multiyear_validation_tables.xlsx`

The section does not claim intrinsic accuracy, calibration, or out-of-time return forecasting because the current artifacts do not contain independently annotated gold labels, valid class probabilities, or a separate return-forecasting benchmark.
