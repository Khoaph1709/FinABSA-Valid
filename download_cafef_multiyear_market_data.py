from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from download_market_data import get_ohlcv

ROOT = Path(__file__).parent
DEFAULT_ROOT = ROOT / "data" / "cafef_multiyear"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download stock and index prices for comparable October CafeF samples")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--years", default="2019,2020,2021,2022")
    parser.add_argument("--month", type=int, default=10)
    parser.add_argument("--start-month", type=int, default=5, help="Price window start month; default May")
    parser.add_argument("--end-month", type=int, default=12, help="Price window end month; default December")
    parser.add_argument("--sleep", type=float, default=4.2)
    parser.add_argument("--rate-limit-wait", type=float, default=45.0)
    args = parser.parse_args()
    years = [int(x.strip()) for x in args.years.split(",") if x.strip()]
    root = Path(args.data_root)
    cache_root = root / "market_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    all_rows: list[pd.DataFrame] = []
    errors: dict[str, str] = {}
    manifest_rows: list[dict] = []

    for year in years:
        period = f"{year}-{args.month:02d}"
        input_path = root / period / "model_inputs_strict.csv"
        if not input_path.exists():
            print(f"{period}: missing {input_path}; run multiyear model-input preparation first")
            continue
        inputs = pd.read_csv(input_path).fillna("")
        tickers = sorted({str(x).upper().strip() for x in inputs.get("ticker", []) if str(x).strip()})
        tickers += [x for x in ["VNINDEX", "VN30"] if x not in tickers]
        start = f"{year}-{args.start_month:02d}-01"
        end = f"{year}-{args.end_month:02d}-31"
        period_dir = root / period
        period_dir.mkdir(parents=True, exist_ok=True)
        period_rows: list[pd.DataFrame] = []
        for idx, ticker in enumerate(tickers, start=1):
            cache_path = cache_root / f"{ticker}_{start}_{end}.csv"
            try:
                if cache_path.exists():
                    df = pd.read_csv(cache_path).fillna("")
                    source_status = "cache"
                else:
                    last_error = None
                    df = None
                    for attempt in range(5):
                        try:
                            df = get_ohlcv(ticker, start=start, end=end)
                            break
                        except BaseException as exc:
                            last_error = exc
                            message = str(exc).lower()
                            is_rate_limit = isinstance(exc, SystemExit) or "rate limit" in message or "rate-limit" in message
                            if is_rate_limit and attempt < 4:
                                print(f"{period} {ticker}: rate limit; waiting {args.rate_limit_wait}s before retry {attempt + 1}/4", flush=True)
                                time.sleep(args.rate_limit_wait)
                            else:
                                break
                    if df is None:
                        raise last_error
                    df.to_csv(cache_path, index=False)
                    source_status = "downloaded"
                if not df.empty:
                    df["period"] = period
                    df["price_window_start"] = start
                    df["price_window_end"] = end
                    period_rows.append(df)
                    all_rows.append(df)
                manifest_rows.append({"period": period, "ticker": ticker, "start": start, "end": end, "rows": len(df), "status": source_status})
                print(f"{period} {idx}/{len(tickers)} {ticker}: {len(df)} rows ({source_status})", flush=True)
            except Exception as exc:
                errors[f"{period}:{ticker}"] = repr(exc)
                manifest_rows.append({"period": period, "ticker": ticker, "start": start, "end": end, "rows": 0, "status": f"error:{type(exc).__name__}"})
                print(f"{period} {idx}/{len(tickers)} {ticker}: ERROR {exc}", flush=True)
            time.sleep(args.sleep)
        if period_rows:
            pd.concat(period_rows, ignore_index=True).drop_duplicates(["ticker", "date"]).to_csv(period_dir / "market_prices.csv", index=False)
            print(f"saved={period_dir / 'market_prices.csv'} rows={sum(len(x) for x in period_rows)}", flush=True)

    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True).drop_duplicates(["ticker", "date"])
        combined.to_csv(root / "market_prices.csv", index=False)
        print(f"saved={root / 'market_prices.csv'} rows={len(combined)}", flush=True)
    pd.DataFrame(manifest_rows).to_csv(root / "market_download_manifest.csv", index=False)
    (root / "market_download_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={root / 'market_download_manifest.csv'} errors={len(errors)}", flush=True)


if __name__ == "__main__":
    main()
