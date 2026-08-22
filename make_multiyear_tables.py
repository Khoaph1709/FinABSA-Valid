from __future__ import annotations

import argparse
import re
from pathlib import Path
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='data/cafef_multiyear')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out = root / 'analysis_multiyear'
    tables = {}
    for name in ['prediction_validation_by_period','event_summary_by_label','car_tests','news_day_control_tests','sentiment_group_tests','panel_summary_by_label','panel_regression_coefficients','robustness_summary','daily_market_sentiment','market_models','event_observations','panel_regression_data']:
        path = out / f'{name}.csv'
        if path.exists():
            tables[name] = pd.read_csv(path)
    if 'car_tests' in tables:
        car = tables['car_tests']
        tables['car_primary_all'] = car[car['group'].astype(str).str.lower().eq('all')].copy()
        tables['car_primary_all'].to_csv(out / 'car_primary_all.csv', index=False)
    if 'panel_regression_coefficients' in tables:
        panel = tables['panel_regression_coefficients']
        key = panel.iloc[:, 1].astype(str).isin(['sentiment_score','negative_share','positive_share','log_article_count','Intercept'])
        tables['panel_key_coefficients'] = panel[key].copy()
        tables['panel_key_coefficients'].to_csv(out / 'panel_key_coefficients.csv', index=False)
    if 'prediction_validation_by_period' in tables:
        val = tables['prediction_validation_by_period'].copy()
        count_rows = []
        for _, row in val.iterrows():
            counts = row.get('label_counts', {})
            if isinstance(counts, str):
                import ast
                try: counts = ast.literal_eval(counts)
                except Exception: counts = {}
            count_rows.append({'period': row['period'], 'input_rows': row['input_rows'], 'prediction_rows': row['prediction_rows'], 'neutral': counts.get('neutral', 0), 'positive': counts.get('positive', 0), 'negative': counts.get('negative', 0), 'missing_predictions': row['missing_predictions'], 'unexpected_predictions': row['unexpected_predictions'], 'unknown_labels': row['unknown_labels']})
        tables['prediction_validation_clean'] = pd.DataFrame(count_rows)
        tables['prediction_validation_clean'].to_csv(out / 'prediction_validation_clean.csv', index=False)
    sheets = {}
    for name, df in tables.items():
        safe = name[:31]
        clean = df.copy()
        for col in clean.select_dtypes(include=['object']).columns:
            clean[col] = clean[col].map(lambda value: re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value)) if pd.notna(value) else value)
        sheets[safe] = clean
    excel = out / 'multiyear_validation_tables.xlsx'
    with pd.ExcelWriter(excel, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            ws.freeze_panes = 'A2'
            for col in ws.columns:
                max_len = max(len(str(x.value)) if x.value is not None else 0 for x in col[:200])
                ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 2, 10), 32)
    print(f'saved={excel}')
    print('summary_sheets=' + ','.join(sorted(sheets)))


if __name__ == '__main__':
    main()
