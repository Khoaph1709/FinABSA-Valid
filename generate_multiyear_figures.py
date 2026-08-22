from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'cafef_multiyear' / 'analysis_multiyear'
IMG = ROOT / 'images'
IMG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.titlesize': 13, 'axes.labelsize': 11, 'figure.dpi': 160})
PERIOD_ORDER = ['2019-10', '2020-10', '2021-10', '2022-10']
COLORS = {'2019-10': '#2563eb', '2020-10': '#16a34a', '2021-10': '#d97706', '2022-10': '#dc2626'}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / name, dpi=220, bbox_inches='tight')
    plt.close(fig)


# 1. Aggregate CAR by period and window with percentile bootstrap intervals.
car = pd.read_csv(DATA / 'car_primary_all.csv')
car = car[car['period'].isin(PERIOD_ORDER)].copy()
car['window_label'] = car['window'].str.replace('[0,+0]', '[0,0]', regex=False).str.replace('[0,+1]', '[0,+1]', regex=False).str.replace('[0,+3]', '[0,+3]', regex=False)
fig, ax = plt.subplots(figsize=(9.5, 5.2))
for period in PERIOD_ORDER:
    d = car[car['period'] == period].copy()
    x = np.arange(len(d)) + (PERIOD_ORDER.index(period) - 1.5) * 0.17
    y = d['mean_car'].to_numpy()
    lo = y - d['bootstrap_ci_low'].to_numpy()
    hi = d['bootstrap_ci_high'].to_numpy() - y
    ax.errorbar(x, y, yerr=[lo, hi], fmt='o-', capsize=3, lw=1.5, ms=5, color=COLORS[period], label=period)
ax.axhline(0, color='black', lw=0.8)
ax.set_xticks(np.arange(3), ['[0,0]', '[0,+1]', '[0,+3]'])
ax.set_xlabel('Event window')
ax.set_ylabel('Mean CAR (percentage points)')
ax.set_title('Aggregate CAR by October period and event window')
ax.legend(title='Period', ncol=4, frameon=True)
save(fig, 'multiyear_car_by_period.png')

# 2. News-day control differences by period.
news = pd.read_csv(DATA / 'news_day_control_tests.csv')
news = news[news['period'].isin(PERIOD_ORDER)].copy().set_index('period').reindex(PERIOD_ORDER).reset_index()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
y = news['difference'].to_numpy()
lo = y - news['bootstrap_ci_low'].to_numpy()
hi = news['bootstrap_ci_high'].to_numpy() - y
ax.errorbar(np.arange(len(news)), y, yerr=[lo, hi], fmt='o', capsize=4, lw=2, ms=7, color='#0f766e')
ax.axhline(0, color='black', lw=0.8)
ax.set_xticks(np.arange(len(news)), PERIOD_ORDER)
ax.set_ylabel('News-day minus no-news-day AR (percentage points)')
ax.set_title('News-day control difference by period')
save(fig, 'multiyear_news_day_control.png')

# 3. Positive-minus-neutral group contrast by period.
groups = pd.read_csv(DATA / 'sentiment_group_tests.csv')
groups = groups[groups['comparison'].eq('positive_minus_neutral') & groups['period'].isin(PERIOD_ORDER)].copy().set_index('period').reindex(PERIOD_ORDER).reset_index()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
y = groups['difference'].to_numpy()
lo = y - groups['bootstrap_ci_low'].to_numpy()
hi = groups['bootstrap_ci_high'].to_numpy() - y
ax.errorbar(np.arange(len(groups)), y, yerr=[lo, hi], fmt='o', capsize=4, lw=2, ms=7, color='#7c3aed')
ax.axhline(0, color='black', lw=0.8)
ax.set_xticks(np.arange(len(groups)), PERIOD_ORDER)
ax.set_ylabel('Positive minus neutral AR (percentage points)')
ax.set_title('Positive--neutral abnormal-return contrast by period')
save(fig, 'multiyear_positive_neutral_contrast.png')

# 4. Overall lag robustness.
lag = pd.read_csv(DATA / 'robustness_summary.csv')
lag = lag[lag['period'].isin(PERIOD_ORDER)].copy()
fig, ax = plt.subplots(figsize=(9.5, 5.2))
for period in PERIOD_ORDER:
    d = lag[lag['period'] == period].sort_values('lag')
    ax.plot(d['lag'], d['mean_ar'], marker='o', lw=2, label=period, color=COLORS[period])
ax.axhline(0, color='black', lw=0.8)
ax.set_xticks([0, 1, 2, 3, 5, 10])
ax.set_xlabel('Lag after aligned event date (trading sessions)')
ax.set_ylabel('Mean abnormal return (percentage points)')
ax.set_title('Lag robustness of abnormal returns')
ax.legend(title='Period', ncol=4, frameon=True)
save(fig, 'multiyear_lag_robustness.png')

# 5. Prediction label composition.
val = pd.read_csv(DATA / 'prediction_validation_clean.csv').set_index('period').reindex(PERIOD_ORDER).reset_index()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
bottom = np.zeros(len(val))
for label, color in [('negative', '#dc2626'), ('neutral', '#64748b'), ('positive', '#16a34a')]:
    vals = val[label].to_numpy()
    ax.bar(val['period'], vals, bottom=bottom, label=label.capitalize(), color=color)
    bottom += vals
for i, total in enumerate(bottom):
    ax.text(i, total + max(bottom) * 0.015, f'{int(total)}', ha='center', va='bottom', fontsize=9)
ax.set_ylabel('Number of predictions')
ax.set_title('Prediction-label composition by October period')
ax.legend(ncol=3)
save(fig, 'multiyear_label_distribution.png')

# 6. Panel sentiment coefficient with approximate 95% Wald intervals.
panel = pd.read_csv(DATA / 'panel_key_coefficients.csv')
panel = panel[panel.iloc[:, 1].eq('sentiment_score')].set_index('period').reindex(PERIOD_ORDER).reset_index()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
y = panel['coef'].to_numpy()
err = 1.96 * panel['std_err'].to_numpy()
ax.errorbar(np.arange(len(panel)), y, yerr=err, fmt='o', capsize=4, lw=2, ms=7, color='#1d4ed8')
ax.axhline(0, color='black', lw=0.8)
ax.set_xticks(np.arange(len(panel)), PERIOD_ORDER)
ax.set_ylabel('Sentiment-score coefficient')
ax.set_title('Two-way fixed-effects sentiment coefficient by period')
ax.text(0.01, 0.02, 'Bars show coefficient +/- 1.96 standard errors; exploratory HC1 fallback where documented.', transform=ax.transAxes, fontsize=8, color='#4b5563')
save(fig, 'multiyear_panel_sentiment_coefficient.png')

print('generated=' + ','.join(sorted(x.name for x in IMG.glob('multiyear_*.png'))))
