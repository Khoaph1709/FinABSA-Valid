from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default="data/cafef_oct2022/model_inputs_strict.csv")
    parser.add_argument("--prices", default="data/cafef_oct2022/market_prices.csv")
    parser.add_argument("--out", default="data/cafef_oct2022/market_coverage.csv")
    args = parser.parse_args()
    inputs = pd.read_csv(args.inputs).fillna("")
    prices = pd.read_csv(args.prices).fillna("")
    prices["ticker"] = prices["ticker"].astype(str).str.upper().str.strip()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    needed = sorted(set(inputs["ticker"].astype(str).str.upper().str.strip())) + ["VNINDEX", "VN30"]
    rows = []
    for ticker in sorted(set(needed)):
        x = prices[prices["ticker"] == ticker]
        rows.append({
            "ticker": ticker,
            "price_rows": len(x),
            "first_date": x["date"].min(),
            "last_date": x["date"].max(),
            "missing_close": int(pd.to_numeric(x.get("close", pd.Series(dtype=float)), errors="coerce").isna().sum()) if len(x) else 0,
            "status": "ok" if len(x) >= 20 else "insufficient",
        })
    result = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(result.to_string(index=False))
    print("coverage_ok=", int((result["status"] == "ok").sum()), "of", len(result))


if __name__ == "__main__":
    main()
