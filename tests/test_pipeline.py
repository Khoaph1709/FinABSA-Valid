from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from normalize_model_output import parse_label  # noqa: E402
from run_experiments import attach_day_aggregates, next_trading_day  # noqa: E402
from run_robustness import attach_lag_returns  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_compact_and_full_labels(self):
        cases = {
            "positive": "positive",
            "NEGATIVE": "negative",
            "neutral": "neutral",
            "POS": "positive",
            "neg": "negative",
            "NEU": "neutral",
            "The answer is POS.": "positive",
            "not a label": "unknown",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_label(raw), expected)

    def test_aggregate_join_uses_keys_not_row_order(self):
        sentiment = pd.DataFrame(
            {
                "sample_id": ["s2", "s1", "s3"],
                "article_id": ["a2", "a1", "a3"],
                "ticker": ["HPG", "HPG", "SSI"],
                "published_date": ["2022-10-02", "2022-10-01", "2022-10-01"],
                "label": ["positive", "negative", "neutral"],
                "sentiment_score": [1.0, -1.0, 0.0],
            }
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "article_ticker_sentiment.csv"
            agg_path = Path(td) / "article_ticker_day_sentiment.csv"
            sentiment.to_csv(path, index=False)
            aggregate = pd.DataFrame(
                {
                    "ticker": ["SSI", "HPG", "HPG"],
                    "published_date": ["2022-10-01", "2022-10-01", "2022-10-02"],
                    "article_count": [4, 7, 2],
                    "negative_share": [0.1, 0.8, 0.0],
                    "positive_share": [0.7, 0.1, 1.0],
                    "neutral_share": [0.2, 0.1, 0.0],
                }
            )
            aggregate.to_csv(agg_path, index=False)
            out = attach_day_aggregates(sentiment, str(path))
        self.assertEqual(out.loc[out.sample_id == "s1", "article_count"].iloc[0], 7)
        self.assertEqual(out.loc[out.sample_id == "s2", "article_count"].iloc[0], 2)
        self.assertEqual(out.loc[out.sample_id == "s3", "negative_share"].iloc[0], 0.1)

    def test_next_trading_day_is_strictly_after_publication(self):
        dates = np.array(pd.to_datetime(["2022-10-03", "2022-10-04", "2022-10-05"]).to_numpy(), dtype="datetime64[ns]")
        pub = pd.Series(pd.to_datetime(["2022-10-02", "2022-10-03", "2022-10-04"]))
        out = next_trading_day(pub, dates)
        self.assertEqual(str(out.iloc[0])[:10], "2022-10-03")
        self.assertEqual(str(out.iloc[1])[:10], "2022-10-04")
        self.assertEqual(str(out.iloc[2])[:10], "2022-10-05")

    def test_lag_output_has_expected_designs(self):
        prices = pd.DataFrame(
            {
                "ticker": ["VNINDEX"] * 6 + ["HPG"] * 6,
                "date": list(pd.date_range("2022-10-03", periods=6, freq="D")) * 2,
                "close": [100, 101, 99, 100, 102, 101, 50, 51, 50, 52, 51, 53],
            }
        )
        sentiment = pd.DataFrame(
            {
                "ticker": ["HPG", "HPG"],
                "target_date": ["2022-10-03", "2022-10-04"],
                "label": ["positive", "negative"],
            }
        )
        out = attach_lag_returns(sentiment, prices, "VNINDEX")
        self.assertEqual(out["design"].tolist(), ["lag_0", "lag_1", "lag_2", "lag_3", "lag_5", "lag_10"])
        self.assertTrue((out["n"] >= 0).all())


class CliContractTests(unittest.TestCase):
    def test_normalizer_accepts_label_column(self):
        inputs_path = ROOT / "data/cafef_oct2022/model_inputs_strict.csv"
        inputs = pd.read_csv(inputs_path)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            raw_path = td / "raw.csv"
            out_path = td / "normalized.csv"
            compact = (["pos", "neg", "neu"] * ((len(inputs) + 2) // 3))[: len(inputs)]
            pd.DataFrame({"sample_id": inputs["sample_id"], "label": compact}).to_csv(raw_path, index=False)
            completed = subprocess.run(
                [sys.executable, str(ROOT / "normalize_model_output.py"), "--raw", str(raw_path), "--inputs", str(inputs_path), "--out", str(out_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("unparsed= 0", completed.stdout)
            normalized = pd.read_csv(out_path)
            self.assertEqual(normalized["classification_output"].tolist()[:3], ["positive", "negative", "neutral"])
            self.assertTrue((normalized["inference_status"] == "ok").all())

    def test_validator_accepts_compact_labels_and_preserves_alignment(self):
        inputs_path = ROOT / "data/cafef_oct2022/model_inputs_strict.csv"
        inputs = pd.read_csv(inputs_path)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pred_path = td / "predictions.csv"
            outdir = td / "analysis"
            compact = (["POS", "neg", "NEU"] * ((len(inputs) + 2) // 3))[: len(inputs)]
            pd.DataFrame(
                {
                    "sample_id": inputs["sample_id"],
                    "raw_model_output": compact,
                    "classification_output": compact,
                }
            ).to_csv(pred_path, index=False)
            subprocess.run(
                [sys.executable, str(ROOT / "validate_predictions.py"), "--inputs", str(inputs_path), "--predictions", str(pred_path), "--outdir", str(outdir)],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads((outdir / "prediction_validation.json").read_text(encoding="utf-8"))
            self.assertEqual(report["unknown_labels"], 0)
            self.assertEqual(report["missing_predictions"], 0)
            article = pd.read_csv(outdir / "article_ticker_sentiment.csv")
            day = pd.read_csv(outdir / "article_ticker_day_sentiment.csv")
            self.assertEqual(len(article), len(inputs))
            self.assertEqual(day.duplicated(["ticker", "published_date"]).sum(), 0)
            self.assertTrue({"article_count", "negative_share", "positive_share"}.issubset(day.columns))

    def test_run_experiments_end_to_end_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            analysis = td / "analysis"
            sentiment_path = analysis / "article_ticker_sentiment.csv"
            prices_path = td / "market_prices.csv"
            dates = pd.date_range("2022-08-01", "2022-10-31", freq="D")
            prices = pd.DataFrame(
                {
                    "ticker": ["VNINDEX"] * len(dates) + ["HPG"] * len(dates),
                    "date": list(dates) * 2,
                    "close": list(100 + np.arange(len(dates)) * 0.2) + list(50 + np.arange(len(dates)) * 0.1),
                }
            )
            prices.to_csv(prices_path, index=False)
            events = pd.DataFrame(
                {
                    "sample_id": ["e1", "e2", "e3"],
                    "article_id": ["a1", "a2", "a3"],
                    "ticker": ["HPG"] * 3,
                    "published_date": ["2022-10-01", "2022-10-02", "2022-10-03"],
                    "label": ["negative", "neutral", "positive"],
                    "sentiment_score": [-1.0, 0.0, 1.0],
                }
            )
            aggregate = pd.DataFrame(
                {
                    "ticker": ["HPG"] * 3,
                    "published_date": ["2022-10-01", "2022-10-02", "2022-10-03"],
                    "article_count": [1, 1, 1],
                    "negative_share": [1.0, 0.0, 0.0],
                    "positive_share": [0.0, 0.0, 1.0],
                    "neutral_share": [0.0, 1.0, 0.0],
                }
            )
            analysis.mkdir(parents=True)
            events.to_csv(sentiment_path, index=False)
            aggregate.to_csv(analysis / "article_ticker_day_sentiment.csv", index=False)
            subprocess.run(
                [sys.executable, str(ROOT / "run_experiments.py"), "--sentiment", str(sentiment_path), "--prices", str(prices_path), "--outdir", str(analysis), "--crisis-start", "2022-10-01", "--crisis-end", "2022-10-31"],
                check=True,
                capture_output=True,
                text=True,
            )
            panel = pd.read_csv(analysis / "tables/panel_regression_data.csv")
            self.assertEqual(panel.duplicated(["ticker", "target_date"]).sum(), 0)
            self.assertTrue((analysis / "event_observations.csv").exists())
            self.assertTrue((analysis / "figures/sentiment_vs_abnormal_return.png").exists())
            self.assertTrue((analysis / "figures/abnormal_return_by_label.png").exists())
            report_md = td / "report_generated.md"
            report_pdf = td / "report_generated.pdf"
            subprocess.run(
                [sys.executable, str(ROOT / "build_report.py"), "--analysis", str(analysis), "--out", str(report_md), "--pdf", str(report_pdf)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(report_md.exists() and report_md.stat().st_size > 0)
            self.assertTrue(report_pdf.exists() and report_pdf.stat().st_size > 0)
            report_text = report_md.read_text(encoding="utf-8")
            self.assertIn("## 5. Statistical tests", report_text)
            self.assertIn("## 7. Robustness and sensitivity", report_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
