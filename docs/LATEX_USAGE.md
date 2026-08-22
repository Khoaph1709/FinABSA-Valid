# LaTeX validation section

`validation_section.tex` is a section fragment for the FinABSA–CafeF report. It is not a standalone document. Load the following packages in the main preamble:

```latex
\usepackage{amsmath,amssymb,booktabs,graphicx,longtable,array,ragged2e}
```

Place the figure files in a directory named `images/` relative to the main `.tex` file. The section references these filenames:

```text
prediction_distribution.png
abnormal_return_by_label.png
car_by_window.png
news_day_control.png
sentiment_group_tests.png
robustness_lags.png
market_model_coverage.png
sentiment_vs_abnormal_return.png
```

The numerical tables are written directly in LaTeX inside `validation_section.tex`; no CSV-to-LaTeX conversion is required. The section reports only analyses that were actually run on the submitted 208-row strict prediction file. Intrinsic gold-label evaluation, probability calibration, out-of-time return forecasting, detailed gold-label error analysis, and broad-linking robustness are explicitly marked as deferred because the required artifacts were not supplied.

To include the section in the main report:

```latex
\input{validation_section.tex}
```

The section uses the portable float placement option `[htbp]`, so no `float` package is required. The current workspace did not contain a LaTeX engine, so the section was checked with static structure validation rather than PDF compilation. The checker confirmed balanced LaTeX environments, eight existing figure references, nine tables, and no placeholders.
