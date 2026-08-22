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
    rows = []
    all_inputs = []
    all_prices = []
    all_errors = {}
    for year in [int(x) for x in args.years.split(',')]:
        period = f'{year}-{args.month:02d}'
        p = root / period
        articles = pd.read_csv(p / 'articles.csv').fillna('')
        full = pd.read_csv(p / 'model_inputs.csv').fillna('')
        strict = pd.read_csv(p / 'model_inputs_strict.csv').fillna('')
        prices = pd.read_csv(p / 'market_prices.csv').fillna('')
        errors_path = p / 'market_download_errors.json'
        errors = json.loads(errors_path.read_text()) if errors_path.exists() else {}
        global_manifest_path = root / 'market_download_manifest.csv'
        if global_manifest_path.exists():
            manifest_all = pd.read_csv(global_manifest_path).fillna('')
            period_manifest = manifest_all[manifest_all['period'].astype(str) == period]
            errors = {str(row['ticker']): str(row['status']) for _, row in period_manifest.iterrows() if str(row.get('status', '')).startswith('error:')}
        all_errors[period] = errors
        all_inputs.append(strict.assign(period=period))
        all_prices.append(prices.assign(period=period))
        pub = pd.to_datetime(articles['published_at'], errors='coerce') if 'published_at' in articles else pd.Series(dtype='datetime64[ns]')
        d = pd.to_datetime(prices['date'], errors='coerce') if 'date' in prices else pd.Series(dtype='datetime64[ns]')
        rows.append({
            'period': period,
            'article_rows': len(articles),
            'crawl_ok': int((articles.get('crawl_status', '') == 'ok').sum()) if 'crawl_status' in articles else None,
            'full_input_rows': len(full),
            'strict_input_rows': len(strict),
            'strict_tickers': strict['ticker'].nunique() if 'ticker' in strict else 0,
            'price_rows': len(prices),
            'price_tickers': prices['ticker'].nunique() if 'ticker' in prices else 0,
            'price_start': d.min().date().isoformat() if d.notna().any() else '',
            'price_end': d.max().date().isoformat() if d.notna().any() else '',
            'price_errors': len(errors),
            'published_min': pub.min().isoformat() if pub.notna().any() else '',
            'published_max': pub.max().isoformat() if pub.notna().any() else '',
        })
    summary = pd.DataFrame(rows)
    strict_all = pd.concat(all_inputs, ignore_index=True)
    price_all = pd.concat(all_prices, ignore_index=True)
    price_keys = set(zip(price_all['period'], price_all['ticker'].astype(str).str.upper()))
    strict_all['has_price'] = [((period, str(ticker).upper()) in price_keys) for period, ticker in zip(strict_all['period'], strict_all['ticker'])]
    summary['strict_rows_with_price'] = [int(strict_all.loc[strict_all.period == r.period, 'has_price'].sum()) for r in summary.itertuples()]
    summary['strict_rows_without_price'] = summary['strict_input_rows'] - summary['strict_rows_with_price']
    out = root / 'multiyear_data_quality_summary.csv'
    summary.to_csv(out, index=False)
    quality = {
        'period_summary': summary.to_dict(orient='records'),
        'total_articles': int(summary.article_rows.sum()),
        'total_strict_inputs': int(summary.strict_input_rows.sum()),
        'strict_rows_with_price': int(strict_all.has_price.sum()),
        'strict_rows_without_price': int((~strict_all.has_price).sum()),
        'total_price_rows': int(len(price_all)),
        'error_symbols_by_period': {k: sorted(v) for k, v in all_errors.items()},
    }
    (root / 'multiyear_data_quality.json').write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding='utf-8')
    print(summary.to_string(index=False))
    print(f'saved={out}')
    print(f"saved={root / 'multiyear_data_quality.json'}")
    print(f"strict_with_price={quality['strict_rows_with_price']} strict_without_price={quality['strict_rows_without_price']}")


if __name__ == '__main__':
    main()
