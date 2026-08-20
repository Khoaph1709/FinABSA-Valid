from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def attach_lag_returns(sentiment: pd.DataFrame, prices: pd.DataFrame, market_ticker: str) -> pd.DataFrame:
    p = prices.copy()
    p["date"] = pd.to_datetime(p["date"], errors="coerce").dt.normalize()
    p["close"] = pd.to_numeric(p["close"], errors="coerce")
    p = p.dropna(subset=["ticker", "date", "close"]).sort_values(["ticker", "date"])
    p["return"] = p.groupby("ticker")["close"].transform(lambda x: 100 * np.log(x / x.shift(1)))
    market = p[p["ticker"] == market_ticker][["date", "return"]].rename(columns={"return": "market_return"})
    p = p.merge(market, on="date", how="left")
    p["ar"] = p["return"] - p["market_return"]
    s = sentiment.copy()
    s["target_date"] = pd.to_datetime(s["target_date"], errors="coerce").dt.normalize()
    rows = []
    dates = sorted(p["date"].dropna().unique())
    for lag in [0, 1, 2, 3, 5, 10]:
        shifted = s.copy()
        # Target date already denotes the first tradable session after publication.
        idx = np.searchsorted(np.array(dates, dtype="datetime64[ns]"), shifted["target_date"].to_numpy(dtype="datetime64[ns]"), side="left")
        new_idx = idx + lag
        shifted["eval_date"] = [dates[i] if i < len(dates) else pd.NaT for i in new_idx]
        joined = shifted.merge(p[["ticker", "date", "return", "market_return", "ar"]], left_on=["ticker", "eval_date"], right_on=["ticker", "date"], how="left")
        crisis = joined[joined["eval_date"].between(pd.Timestamp("2022-10-01"), pd.Timestamp("2022-10-31"))]
        rows.append({
            "design": f"lag_{lag}", "lag": lag, "n": len(crisis),
            "mean_ar": crisis["ar"].mean(), "median_ar": crisis["ar"].median(),
            "negative_mean_ar": crisis.loc[crisis["label"] == "negative", "ar"].mean(),
            "neutral_mean_ar": crisis.loc[crisis["label"] == "neutral", "ar"].mean(),
            "positive_mean_ar": crisis.loc[crisis["label"] == "positive", "ar"].mean(),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="data/cafef_oct2022/analysis/event_observations.csv")
    parser.add_argument("--prices", default="data/cafef_oct2022/market_prices.csv")
    parser.add_argument("--out", default="data/cafef_oct2022/analysis/tables/robustness_summary.csv")
    args = parser.parse_args()
    events = pd.read_csv(args.events).fillna("")
    prices = pd.read_csv(args.prices).fillna("")
    market_candidates = {"VNINDEX", "VN-INDEX", "VN_INDEX", "VNINDEXHOSE"}
    market_ticker = next((x for x in market_candidates if x in set(prices["ticker"].astype(str).str.upper())), None)
    if market_ticker is None:
        raise ValueError("Cannot find VN-Index ticker in prices")
    events["label"] = events["label"].astype(str).str.lower()
    result = attach_lag_returns(events, prices, market_ticker)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
