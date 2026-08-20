# CafeF October 2022 Dataset Card

## Summary

This repository contains a reproducible one-month Vietnamese financial-news corpus collected from public CafeF sitemap URLs for October 2022. The selected period is used as a crisis-regime candidate and is not presented as a causal treatment period by itself.

## Current snapshot

| Asset | Description | Rows |
|---|---|---:|
| `sitemap_manifest.csv` | All CafeF `.chn` URLs found in six October 2022 sitemaps | 6,210 |
| `articles.csv` | Financially relevant articles fetched and parsed | 1,472 |
| `model_inputs.csv` | Article–ticker target-masked rows, full mapping | 525 |
| `model_inputs_strict.csv` | High-confidence mapping rows for primary analysis | 216 |

The full mapping includes automatic uppercase-ticker candidates that require review. The strict mapping keeps confidence at least 0.95, primarily based on the alias dictionary or contextual ticker rule. Both files are retained because strict mapping is safer for the main result while full mapping is useful for sensitivity analysis.

## Input contract

Each row in `model_inputs.csv` represents one article–ticker pair. The model receives `input_text`, which is a headline with the selected target replaced by `Target` and other detected entities replaced by `Other`. The model is expected to return one sentiment label: `positive`, `neutral`, or `negative`.

The model does **not** discover ticker. Entity linking happens before inference and is stored in `ticker`, `target_surface`, `entity_method` and `entity_confidence`.

## Provenance

Each article row retains URL, published timestamp, updated timestamp when available, raw HTML path, source hash, parse status and crawl status. Raw HTML is intentionally excluded from Git commits because it is large; it remains in the local data directory for reproducibility and audit.

## Recommended use

Use `model_inputs_strict.csv` for the primary model run and `model_inputs.csv` for broad robustness. After inference, normalize output into `model_predictions.csv`, validate row alignment, aggregate sentiment by article–ticker–day, then join the next tradable-session return.

## Limitations

Ticker extraction is partly rule-based and should be manually audited. CafeF coverage is not the same as the entire Vietnamese information set. Some articles may be updated after initial publication. A headline-only model may not capture full-body context, so title-only is the primary matched-domain experiment and body/context is a sensitivity branch.
