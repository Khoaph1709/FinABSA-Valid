from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd


def normalize_ohlcv(df: pd.DataFrame, ticker: str, source: str) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).lower().strip() for c in out.columns]
    aliases = {
        "time": "date", "datetime": "date", "trading_date": "date",
        "open_price": "open", "close_price": "close", "adj_close": "close",
        "volume_match": "volume", "vol": "volume",
    }
    out = out.rename(columns=aliases)
    if "date" not in out.columns:
        for col in out.columns:
            if "date" in col or "time" in col:
                out = out.rename(columns={col: "date"})
                break
    if "date" not in out.columns or "close" not in out.columns:
        raise ValueError(f"Cannot identify date/close columns for {ticker}: {list(out.columns)}")
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None)
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in out.columns:
            out[col] = pd.NA
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["ticker"] = ticker
    out["source"] = source
    out["adjusted_flag"] = "unknown"
    return out[["ticker", "date", "open", "high", "low", "close", "volume", "adjusted_flag", "source"]].dropna(subset=["date", "close"])


def get_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    from vnstock import Market
    market = Market()
    last_error = None
    try:
        result = market.equity(symbol=symbol).ohlcv(start=start, end=end, count=500)
        return normalize_ohlcv(result, symbol, "vnstock_market_equity_ohlcv")
    except Exception as exc:
        last_error = exc
    try:
        result = market.index(symbol=symbol).ohlcv(start=start, end=end, count=500)
        return normalize_ohlcv(result, symbol, "vnstock_market_index_ohlcv")
    except Exception as exc:
        last_error = exc
    raise RuntimeError(f"vnstock failed for {symbol}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default="data/cafef_oct2022/model_inputs_strict.csv")
    parser.add_argument("--out", default="data/cafef_oct2022/market_prices.csv")
    parser.add_argument("--errors", default="data/cafef_oct2022/market_download_errors.json")
    parser.add_argument("--cache-dir", default="data/cafef_oct2022/market_cache")
    parser.add_argument("--start", default="2022-05-01")
    parser.add_argument("--end", default="2022-12-31")
    parser.add_argument("--sleep", type=float, default=4.2)
    parser.add_argument("--rate-limit-wait", type=float, default=45.0)
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    inputs = pd.read_csv(args.inputs).fillna("")
    tickers = sorted({str(x).upper().strip() for x in inputs.get("ticker", []) if str(x).strip()})
    tickers += [x for x in ["VNINDEX", "VN30"] if x not in tickers]
    rows, errors = [], {}
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for idx, ticker in enumerate(tickers, start=1):
        cache_path = cache_dir / f"{ticker}_{args.start}_{args.end}.csv"
        if cache_path.exists():
            try:
                df = pd.read_csv(cache_path)
                rows.append(df)
                pd.concat(rows, ignore_index=True).drop_duplicates(["ticker", "date"]).to_csv(output_path, index=False)
                print(f"{idx}/{len(tickers)} {ticker}: cache {len(df)} rows")
                continue
            except Exception:
                cache_path.unlink(missing_ok=True)
        try:
            df = None
            last_exc = None
            for attempt in range(2):
                try:
                    df = get_ohlcv(ticker, args.start, args.end)
                    break
                except Exception as exc:
                    last_exc = exc
                    if "Rate limit" in str(exc) or "rate limit" in str(exc).lower():
                        print(f"{ticker}: rate limit; waiting {args.rate_limit_wait}s")
                        time.sleep(args.rate_limit_wait)
                    else:
                        break
            if df is None:
                raise last_exc
            df.to_csv(cache_path, index=False)
            rows.append(df)
            pd.concat(rows, ignore_index=True).drop_duplicates(["ticker", "date"]).to_csv(output_path, index=False)
            print(f"{idx}/{len(tickers)} {ticker}: {len(df)} rows")
        except Exception as exc:
            errors[ticker] = repr(exc)
            print(f"{idx}/{len(tickers)} {ticker}: ERROR {exc}")
        time.sleep(args.sleep)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    out.to_csv(output_path, index=False)
    Path(args.errors).write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={args.out} rows={len(out)} errors={len(errors)}")


if __name__ == "__main__":
    main()
