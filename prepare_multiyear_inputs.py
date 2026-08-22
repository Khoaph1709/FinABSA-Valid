from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DEFAULT_ROOT = ROOT / "data" / "cafef_multiyear"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare per-period CafeF model inputs")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--years", default="2019,2020,2021,2022")
    parser.add_argument("--month", type=int, default=10)
    parser.add_argument("--aliases", default=str(ROOT / "data" / "entity_aliases.csv"))
    args = parser.parse_args()
    root = Path(args.data_root).expanduser().resolve()
    years = [int(x.strip()) for x in args.years.split(",") if x.strip()]
    summary = []
    for year in years:
        period = f"{year}-{args.month:02d}"
        period_root = root / period
        articles = period_root / "articles.csv"
        if not articles.exists():
            raise SystemExit(f"missing article file: {articles}")
        out = period_root / "model_inputs.csv"
        out_strict = period_root / "model_inputs_strict.csv"
        cmd = [sys.executable, str(ROOT / "prepare_model_inputs.py"), "--articles", str(articles), "--aliases", args.aliases, "--out", str(out), "--out-strict", str(out_strict)]
        subprocess.run(cmd, check=True)
        import pandas as pd
        full = pd.read_csv(out)
        strict = pd.read_csv(out_strict)
        summary.append({"period": period, "articles": len(pd.read_csv(articles)), "model_rows": len(full), "strict_rows": len(strict), "tickers_full": full["ticker"].nunique() if not full.empty else 0, "tickers_strict": strict["ticker"].nunique() if not strict.empty else 0})
    import pandas as pd
    pd.DataFrame(summary).to_csv(root / "model_input_summary.csv", index=False)
    print(pd.DataFrame(summary).to_string(index=False))
    print(f"saved={root / 'model_input_summary.csv'}")


if __name__ == "__main__":
    main()
