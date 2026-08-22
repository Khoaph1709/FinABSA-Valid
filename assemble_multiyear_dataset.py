from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='data/cafef_multiyear')
    parser.add_argument('--years', default='2019,2020,2021,2022')
    parser.add_argument('--month', type=int, default=10)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    years = [int(x.strip()) for x in args.years.split(',') if x.strip()]
    articles, full_inputs, strict_inputs, prices = [], [], [], []
    for year in years:
        period = f'{year}-{args.month:02d}'
        p = root / period
        articles.append(pd.read_csv(p / 'articles.csv').fillna('').assign(period=period))
        full_inputs.append(pd.read_csv(p / 'model_inputs.csv').fillna('').assign(period=period))
        strict_inputs.append(pd.read_csv(p / 'model_inputs_strict.csv').fillna('').assign(period=period))
        prices.append(pd.read_csv(p / 'market_prices.csv').fillna('').assign(period=period))
    articles_df = pd.concat(articles, ignore_index=True)
    full_df = pd.concat(full_inputs, ignore_index=True)
    strict_df = pd.concat(strict_inputs, ignore_index=True)
    prices_df = pd.concat(prices, ignore_index=True)
    # Retain period in the uniqueness key because the same ticker may occur in different years.
    strict_keys = set(zip(prices_df['period'].astype(str), prices_df['ticker'].astype(str).str.upper()))
    strict_df['has_price_window'] = [((p, str(t).upper()) in strict_keys) for p, t in zip(strict_df['period'], strict_df['ticker'])]
    for name, df in [('articles', articles_df), ('model_inputs', full_df), ('model_inputs_strict', strict_df), ('market_prices', prices_df)]:
        df.to_csv(root / f'{name}.csv', index=False)
    strict_df[strict_df['has_price_window']].to_csv(root / 'model_inputs_strict_analysis_ready.csv', index=False)
    manifest = pd.read_csv(root / 'market_download_manifest.csv').fillna('')
    manifest['has_price_data'] = manifest['rows'].astype(str).str.replace(r'[^0-9.-]', '', regex=True).replace('', '0').astype(float).gt(0)
    manifest.to_csv(root / 'market_download_manifest.csv', index=False)
    summary = {
        'periods': [f'{y}-{args.month:02d}' for y in years],
        'articles': int(len(articles_df)),
        'full_inputs': int(len(full_df)),
        'strict_inputs': int(len(strict_df)),
        'strict_analysis_ready': int(strict_df['has_price_window'].sum()),
        'strict_without_price': int((~strict_df['has_price_window']).sum()),
        'prices': int(len(prices_df)),
        'price_tickers': int(prices_df['ticker'].nunique()),
        'download_errors': int((~manifest['has_price_data']).sum()),
        'download_error_rows': manifest.loc[~manifest['has_price_data'], ['period', 'ticker', 'status']].to_dict(orient='records'),
    }
    (root / 'multiyear_dataset_manifest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f'saved={root}')


if __name__ == '__main__':
    main()
