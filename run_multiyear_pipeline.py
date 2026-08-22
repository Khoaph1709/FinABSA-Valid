from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


PERIODS = ('2019-10', '2020-10', '2021-10', '2022-10')


def run(cmd: list[str], cwd: Path) -> None:
    print('$ ' + ' '.join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def read_add(path: Path, period: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame({'period': [period], 'status': [f'missing:{path.name}']})
    df = pd.read_csv(path)
    df.insert(0, 'period', period)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the FinABSA financial validation separately for each October period.')
    parser.add_argument('--repo', default='.')
    parser.add_argument('--data-root', default='data/cafef_multiyear')
    parser.add_argument('--predictions', required=True)
    parser.add_argument('--periods', default=','.join(PERIODS))
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    root = (repo / args.data_root).resolve() if not Path(args.data_root).is_absolute() else Path(args.data_root).resolve()
    predictions_path = Path(args.predictions).resolve()
    periods = [x.strip() for x in args.periods.split(',') if x.strip()]

    combined_inputs_path = root / 'model_inputs_strict.csv'
    combined_inputs = pd.read_csv(combined_inputs_path).fillna('')
    predictions = pd.read_csv(predictions_path).fillna('')
    required = {'sample_id', 'classification_output', 'raw_model_output'}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f'Prediction file is missing columns: {sorted(missing)}')
    if 'period' not in combined_inputs.columns:
        raise ValueError(f'{combined_inputs_path} must contain period')
    period_map = combined_inputs[['sample_id', 'period']].drop_duplicates('sample_id')
    if period_map['sample_id'].duplicated().any():
        raise ValueError('Combined strict input has duplicate sample_id values')
    predictions = predictions.merge(period_map, on='sample_id', how='left', validate='one_to_one', suffixes=('', '_input'))
    if predictions['period'].isna().any() or (predictions['period'].astype(str).str.strip() == '').any():
        bad = predictions.loc[predictions['period'].isna() | (predictions['period'].astype(str).str.strip() == ''), 'sample_id'].head(10).tolist()
        raise ValueError(f'Predictions contain sample IDs not found in combined strict inputs: {bad}')
    predictions['period'] = predictions['period'].astype(str)

    output_root = root / 'analysis_multiyear'
    output_root.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(root / 'model_predictions.csv', index=False)
    validation_rows = []
    for period in periods:
        period_dir = root / period
        input_path = period_dir / 'model_inputs_strict.csv'
        pred_path = period_dir / 'model_predictions.csv'
        analysis_dir = period_dir / 'analysis'
        period_inputs = pd.read_csv(input_path).fillna('')
        period_preds = predictions[predictions['period'] == period].drop(columns=['period'])
        expected_ids = set(period_inputs['sample_id'])
        actual_ids = set(period_preds['sample_id'])
        if expected_ids != actual_ids:
            raise ValueError(f'{period}: prediction/input mismatch; missing={len(expected_ids-actual_ids)}, unexpected={len(actual_ids-expected_ids)}')
        period_preds.to_csv(pred_path, index=False)
        year = period[:4]
        run([sys.executable, 'validate_predictions.py', '--inputs', str(input_path), '--predictions', str(pred_path), '--outdir', str(analysis_dir)], repo)
        run([sys.executable, 'run_experiments.py', '--sentiment', str(analysis_dir / 'article_ticker_sentiment.csv'), '--prices', str(period_dir / 'market_prices.csv'), '--outdir', str(analysis_dir), '--crisis-start', f'{year}-10-01', '--crisis-end', f'{year}-10-31'], repo)
        run([sys.executable, 'run_robustness.py', '--events', str(analysis_dir / 'event_observations.csv'), '--prices', str(period_dir / 'market_prices.csv'), '--out', str(analysis_dir / 'tables/robustness_summary.csv'), '--crisis-start', f'{year}-10-01', '--crisis-end', f'{year}-10-31'], repo)
        report_path = analysis_dir / 'prediction_validation.json'
        validation = json.loads(report_path.read_text(encoding='utf-8'))
        validation_rows.append({'period': period, **validation})

    table_names = [
        'event_summary_by_label.csv', 'car_tests.csv', 'news_day_control_tests.csv',
        'sentiment_group_tests.csv', 'panel_summary_by_label.csv', 'panel_regression_coefficients.csv',
        'robustness_summary.csv', 'daily_market_sentiment.csv', 'panel_regression_data.csv',
    ]
    for name in table_names:
        parts = [read_add(root / period / 'analysis' / 'tables' / name, period) for period in periods]
        pd.concat(parts, ignore_index=True).to_csv(output_root / name, index=False)
    market_parts = [read_add(root / period / 'analysis' / 'market_models.csv', period) for period in periods]
    pd.concat(market_parts, ignore_index=True).to_csv(output_root / 'market_models.csv', index=False)
    event_parts = [read_add(root / period / 'analysis' / 'event_observations.csv', period) for period in periods]
    pd.concat(event_parts, ignore_index=True).to_csv(output_root / 'event_observations.csv', index=False)
    validation_df = pd.DataFrame(validation_rows)
    validation_df.to_csv(output_root / 'prediction_validation_by_period.csv', index=False)

    summary = {
        'periods': periods,
        'prediction_rows': int(len(predictions)),
        'prediction_period_counts': predictions['period'].value_counts().sort_index().to_dict(),
        'validation': validation_rows,
        'tables': sorted(x.name for x in output_root.glob('*.csv')),
    }
    (output_root / 'multiyear_validation_manifest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    lines = [
        '# Multi-year FinABSA financial validation',
        '',
        'This report combines separate October event-study runs for 2019, 2020, 2021, and 2022. Each period uses its own May--December price window, its own VNINDEX market model, and its own October event window. Results are pooled here only for comparison; pooled inference requires an explicitly specified multi-period model.',
        '',
        '## Prediction validation by period',
        '',
        validation_df.to_markdown(index=False),
        '',
        '## Output tables',
        '',
    ]
    for name in sorted(x.name for x in output_root.glob('*.csv')):
        lines.append(f'- `{name}`')
    lines += ['', '## Interpretation note', '', 'The event-study, control, panel, and lag results are observational associations. They do not establish that news sentiment causes returns. The period-specific samples can differ in entity coverage and price availability, so cross-year comparisons should report sample sizes and coverage alongside estimates.']
    (output_root / 'multiyear_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
