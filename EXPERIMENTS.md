# Complete validation experiments

## Main claims to test

The project must separate two claims. The first is an NLP claim: the target-masked model can classify Vietnamese financial sentiment for the selected entity. The second is a downstream claim: the resulting sentiment contains information associated with the next tradable-session return or abnormal return. A result supporting one claim does not automatically support the other.

## Experiment matrix

| ID | Experiment | Input | Outcome | Primary metric |
|---|---|---|---|---|
| E1 | Intrinsic classification | CafeF manually adjudicated sample | Gold sentiment | Macro-F1, balanced accuracy, MCC |
| E2 | Domain-shift comparison | SEntFiN benchmark vs CafeF sample | Sentiment label | Per-class F1 and error groups |
| E3 | Title vs context ablation | Headline vs context/full-body rows | Gold sentiment / extrinsic signal | Delta macro-F1 and delta IC |
| E4 | Entity-linking ablation | Strict vs full mapping | Gold sentiment / AR | Delta metrics and stability |
| E5 | Event study | Article–ticker events | AR/CAR | AAR, CAAR, bootstrap CI |
| E6 | Panel regression | Article–ticker–day panel | AR at t+1 | Coefficient, robust SE, CI |
| E7 | Lag analysis | Sentiment at t | Return t, t+1, t+2, t+3, t+5, t+10 | Mean AR and rank IC |
| E8 | Placebo time shift | Sentiment shifted +5/+10 sessions | AR | Near-zero placebo association |
| E9 | Permutation | Sentiment shuffled across tickers in day | AR | Null distribution |
| E10 | Sector/size split | Industry, VN30/non-VN30, liquidity | AR | Interaction or subgroup effect |

## E1: intrinsic classification

Create a 300–500 row annotation sample from `make_annotation_sample.py`. Two annotators independently label the target ticker and sentiment. A third person adjudicates conflicts. Keep `annotator_1_label`, `annotator_2_label`, `adjudicated_label`, `annotator_1_ticker`, `annotator_2_ticker`, `adjudicated_ticker` and notes.

Run `evaluate_intrinsic.py` only after `adjudicated_label` is filled. Report macro-F1 because class imbalance can make accuracy misleading. Also report the confusion matrix and examples of neutral-to-positive, neutral-to-negative and polarity-reversal errors.

## E2: domain shift

Compare performance on the original SEntFiN-compatible benchmark and the manually labelled CafeF sample. The purpose is not to claim the benchmark is invalid; it is to show how a model trained/evaluated on one distribution behaves on Vietnamese financial headlines with ticker entities and crisis-period vocabulary.

## E3: title/context ablation

The primary model input is headline-only because the repository’s training data consists of short titles and the training tokenizer uses a short sequence limit. A context/full-body variant can be created later by replacing `input_text` with a sentence window or truncated body. Report whether extra context improves sentiment accuracy or creates truncation/noise.

## E4: strict/full entity-linking ablation

Run the model on both `model_inputs_strict.csv` and `model_inputs.csv`. Use strict mapping for the primary market result. The full mapping estimates sensitivity to automatic ticker candidates. If a market result exists only in the broad mapping, downgrade the claim.

## E5: event study

For each article–ticker pair, set event time to the first tradable session after publication. Use the market model fitted on the pre-crisis estimation window. The primary window is `[0,+1]`; secondary windows are `[0,0]`, `[0,+3]` and, only when timestamp precision permits, `[-1,+1]`.

```text
r_i,t = alpha_i + beta_i r_m,t + epsilon_i,t
AR_i,t = r_i,t - (alpha_hat_i + beta_hat_i r_m,t)
CAR_i[a,b] = sum(AR_i,t for t in [a,b])
```

Report AAR/CAAR by predicted sentiment, negative/positive imbalance, systemic vs idiosyncratic topic and sector. Use bootstrap/permutation because events can cluster on the same day.

## E6: panel regression

The main specification is:

```text
AR_i,t+1 = alpha_i + delta_t
           + beta1 * sentiment_score_i,t
           + beta2 * negative_share_i,t
           + beta3 * positive_share_i,t
           + gamma * log(1 + article_count_i,t)
           + epsilon_i,t
```

Ticker fixed effects absorb time-invariant differences between companies. Date fixed effects absorb common market-day shocks. The coefficient is an association conditional on these controls, not a causal treatment effect. Use HC3 or clustered standard errors and report the number of tickers, dates and observations.

## E7: lag analysis

Run the same aggregation for evaluation lags 0, 1, 2, 3, 5 and 10 sessions. A plausible information reaction should be strongest at short lags and decay. Strong association at t−1 is a warning sign for leakage.

## E8: placebo time shift

Shift each event forward by 5 and 10 trading sessions and recompute the outcome join. The main signal should weaken. If the placebo is as strong as the main signal, the model may be capturing persistent ticker characteristics, a common trend or a data-join artifact.

## E9: permutation test

Within each date, randomly permute sentiment across tickers 1,000 times, recompute the mean abnormal-return difference between negative and positive groups, and compare the observed statistic to the null distribution. This controls for the daily article volume and market regime better than an unconditional random shuffle.

## E10: subgroup and interaction

Use industry, VN30/non-VN30, market capitalization and liquidity only when reference data is available and point-in-time consistent. Prefer a common regression with interactions to many tiny subgroup regressions. Report sample size in every subgroup table.

## Multiple testing and decision rule

Pre-specify one primary outcome: next-tradable-session abnormal return, and one primary window: `[0,+1]`. Treat other lags, sectors and topics as exploratory. Apply Benjamini–Hochberg within related families and report effect sizes with confidence intervals. Do not select the most favorable window after inspecting all results.

## Interpretation rules

A strong intrinsic result with no downstream signal is still a valid NLP result. It means sentiment classification and market predictability are different tasks, or that price already incorporates the information. A downstream association without intrinsic validation should not be presented as evidence that the model understands sentiment. A robust conclusion requires stable signs across strict mapping, at least two windows, one placebo and one baseline.
