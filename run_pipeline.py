from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-output", default="", help="Optional raw output file to normalize")
    parser.add_argument("--model", default="", help="Optional local/HuggingFace model to run directly")
    parser.add_argument("--skip-market", action="store_true")
    args = parser.parse_args()
    py = sys.executable
    inputs = Path("data/cafef_oct2022/model_inputs_strict.csv")
    predictions = Path("data/cafef_oct2022/model_predictions.csv")
    prices = Path("data/cafef_oct2022/market_prices.csv")
    if not inputs.exists():
        run([py, "prepare_model_inputs.py"])
    if args.model:
        run([py, "run_finabsa_on_cafef.py", "--model", args.model, "--input", str(inputs), "--output", str(predictions)])
    elif args.raw_output:
        run([py, "normalize_model_output.py", "--raw", args.raw_output, "--inputs", str(inputs), "--out", str(predictions)])
    elif not predictions.exists():
        raise SystemExit("Missing model output. Use --model CHECKPOINT or --raw YOUR_OUTPUT.csv first.")
    run([py, "validate_predictions.py"])
    if not args.skip_market:
        if not prices.exists():
            run([py, "download_market_data.py"])
        run([py, "run_experiments.py"])
        run([py, "run_robustness.py"])
    run([py, "build_report.py"])
    print("Pipeline completed. See report_generated.md and data/cafef_oct2022/analysis/")


if __name__ == "__main__":
    main()
