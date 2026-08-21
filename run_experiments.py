from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def fit_market_model(prices: pd.DataFrame, market: pd.DataFrame, crisis_start: pd.Timestamp) -> pd.DataFrame:
    market = market[["date", "return"]].rename(columns={"return": "market_return"})
    rows = []
    for ticker, grp in prices.groupby("ticker"):
        train = grp[grp["date"] < crisis_start].merge(market, on="date", how="inner").dropna()
        if len(train) < 20:
            rows.append({"ticker": ticker, "alpha": 0.0, "beta": 1.0, "n_estimation": len(train), "model_status": "fallback"})
            continue
        x = train["market_return"].to_numpy(dtype=float)
        y = train["return"].to_numpy(dtype=float)
        beta, alpha = np.polyfit(x, y, 1)
        rows.append({"ticker": ticker, "alpha": float(alpha), "beta": float(beta), "n_estimation": len(train), "model_status": "market_model"})
    return pd.DataFrame(rows)


def add_returns(prices: pd.DataFrame) -> pd.DataFrame:
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.normalize()
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices = prices.dropna(subset=["ticker", "date", "close"]).sort_values(["ticker", "date"])
    prices["return"] = prices.groupby("ticker")["close"].transform(lambda x: 100 * np.log(x / x.shift(1)))
    return prices


def next_trading_day(pub_dates: pd.Series, trading_dates: np.ndarray) -> pd.Series:
    values = pd.to_datetime(pub_dates, errors="coerce").dt.normalize().astype("datetime64[ns]").to_numpy()
    idx = np.searchsorted(trading_dates, values, side="right")
    result = np.full(len(values), np.datetime64("NaT"), dtype="datetime64[ns]")
    valid = idx < len(trading_dates)
    result[valid] = trading_dates[idx[valid]]
    return pd.Series(result, index=pub_dates.index)


def attach_day_aggregates(sentiment: pd.DataFrame, sentiment_path: str) -> pd.DataFrame:
    """Attach ticker-day features by keys, never by row position."""
    s = sentiment.copy()
    s["ticker"] = s["ticker"].astype(str).str.upper().str.strip()
    s["published_date_key"] = pd.to_datetime(s["published_date"], errors="coerce").dt.normalize()
    aggregate_path = Path(sentiment_path).with_name("article_ticker_day_sentiment.csv")
    if aggregate_path.exists():
        day = pd.read_csv(aggregate_path).fillna("")
        day["ticker"] = day["ticker"].astype(str).str.upper().str.strip()
        day["published_date_key"] = pd.to_datetime(day["published_date"], errors="coerce").dt.normalize()
        keep = ["ticker", "published_date_key", "article_count", "negative_share", "positive_share", "neutral_share"]
        missing = [c for c in keep if c not in day.columns]
        if missing:
            raise ValueError(f"Aggregate file {aggregate_path} is missing columns: {missing}")
        day = day[keep].drop_duplicates(["ticker", "published_date_key"])
        s = s.merge(day, on=["ticker", "published_date_key"], how="left", validate="many_to_one")
    else:
        valid = s[s["label"].isin({"positive", "neutral", "negative"})].copy()
        day = valid.groupby(["ticker", "published_date_key"], dropna=False).agg(
            article_count=("article_id", "nunique"),
            negative_share=("label", lambda x: float((x == "negative").mean())),
            positive_share=("label", lambda x: float((x == "positive").mean())),
            neutral_share=("label", lambda x: float((x == "neutral").mean())),
        ).reset_index()
        s = s.merge(day, on=["ticker", "published_date_key"], how="left", validate="many_to_one")
    s["article_count"] = pd.to_numeric(s["article_count"], errors="coerce").fillna(1)
    for col in ["negative_share", "positive_share", "neutral_share"]:
        s[col] = pd.to_numeric(s[col], errors="coerce").fillna(0)
    return s.drop(columns=["published_date_key"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentiment", default="data/cafef_oct2022/analysis/article_ticker_sentiment.csv")
    parser.add_argument("--prices", default="data/cafef_oct2022/market_prices.csv")
    parser.add_argument("--outdir", default="data/cafef_oct2022/analysis")
    parser.add_argument("--crisis-start", default="2022-10-01")
    parser.add_argument("--crisis-end", default="2022-10-31")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)
    sentiment = pd.read_csv(args.sentiment).fillna("")
    prices = add_returns(pd.read_csv(args.prices).fillna(""))
    prices["ticker"] = prices["ticker"].astype(str).str.upper().str.strip()
    sentiment["ticker"] = sentiment["ticker"].astype(str).str.upper().str.strip()
    sentiment["published_date"] = pd.to_datetime(sentiment["published_date"], errors="coerce").dt.normalize()
    required_sentiment = {"sample_id", "article_id", "ticker", "published_date", "label", "sentiment_score"}
    missing_sentiment = required_sentiment - set(sentiment.columns)
    if missing_sentiment:
        raise ValueError(f"Sentiment file is missing columns: {sorted(missing_sentiment)}")
    sentiment = attach_day_aggregates(sentiment, args.sentiment)

    market_candidates = ["VNINDEX", "VN-INDEX", "VN_INDEX", "VNINDEXHOSE"]
    market_ticker = next((x for x in market_candidates if x in set(prices["ticker"])), None)
    if market_ticker is None:
        raise ValueError(f"No VN-Index series found. Available tickers: {sorted(prices.ticker.unique())[:30]}")
    market = prices[prices["ticker"] == market_ticker][["date", "return"]].copy()
    trading_dates = np.array(sorted(market["date"].dropna().unique()), dtype="datetime64[ns]")

    sentiment["target_date"] = next_trading_day(sentiment["published_date"], trading_dates)
    sentiment["sentiment_score"] = pd.to_numeric(sentiment["sentiment_score"], errors="coerce")
    sentiment = sentiment.dropna(subset=["target_date", "ticker"])

    ticker_prices = prices[prices["ticker"] != market_ticker].copy()
    models = fit_market_model(ticker_prices, market, pd.Timestamp(args.crisis_start))
    ticker_prices = ticker_prices.merge(models, on="ticker", how="left")
    ticker_prices = ticker_prices.merge(market.rename(columns={"return": "market_return"}), on="date", how="left")
    ticker_prices["expected_return"] = ticker_prices["alpha"] + ticker_prices["beta"] * ticker_prices["market_return"]
    ticker_prices["abnormal_return"] = ticker_prices["return"] - ticker_prices["expected_return"]

    events = sentiment.merge(
        ticker_prices[["ticker", "date", "return", "market_return", "expected_return", "abnormal_return"]],
        left_on=["ticker", "target_date"], right_on=["ticker", "date"], how="left",
    )
    crisis_start = pd.Timestamp(args.crisis_start)
    crisis_end = pd.Timestamp(args.crisis_end)
    events["in_crisis"] = events["target_date"].between(crisis_start, crisis_end)
    events["log_article_count"] = np.log1p(events["article_count"])
    events.to_csv(outdir / "event_observations.csv", index=False)
    models.to_csv(outdir / "market_models.csv", index=False)

    crisis = events[events["in_crisis"]].copy()
    summary = crisis.groupby("label", dropna=False).agg(
        events=("sample_id", "count"),
        mean_sentiment=("sentiment_score", "mean"),
        mean_return=("return", "mean"),
        mean_abnormal_return=("abnormal_return", "mean"),
        median_abnormal_return=("abnormal_return", "median"),
        mean_article_count=("article_count", "mean"),
    ).reset_index()
    summary.to_csv(outdir / "tables/event_summary_by_label.csv", index=False)
    # Build a genuine ticker-day panel before regression. The event table can
    # contain multiple articles for the same ticker-day, but the market outcome
    # is one return per ticker-day and must not be repeated in the regression.
    panel = (
        crisis.groupby(["ticker", "target_date"], as_index=False)
        .agg(
            sentiment_score=("sentiment_score", "mean"),
            negative_share=("negative_share", "first"),
            positive_share=("positive_share", "first"),
            neutral_share=("neutral_share", "first"),
            article_count=("article_id", "nunique"),
            **{"return": ("return", "first")},
            market_return=("market_return", "first"),
            expected_return=("expected_return", "first"),
            abnormal_return=("abnormal_return", "first"),
            event_rows=("sample_id", "count"),
        )
    )
    panel["log_article_count"] = np.log1p(panel["article_count"])
    panel.to_csv(outdir / "tables/panel_regression_data.csv", index=False)

    # Primary panel regression with ticker and date fixed effects.
    regression_path = outdir / "tables/panel_regression.txt"
    reg = panel.dropna(subset=["abnormal_return", "sentiment_score"]).copy()
    with regression_path.open("w", encoding="utf-8") as fh:
        fh.write(
            f"market_ticker={market_ticker}\n"
            f"observations={len(reg)}\n"
            f"event_rows={len(crisis)}\n"
            f"unique_tickers={reg['ticker'].nunique()}\n"
            f"unique_dates={reg['target_date'].nunique()}\n"
            "unit=ticker-day\n"
        )
        try:
            import statsmodels.formula.api as smf
            if len(reg) >= 20 and reg["ticker"].nunique() >= 2 and reg["target_date"].nunique() >= 2:
                model = smf.ols(
                    "abnormal_return ~ sentiment_score + negative_share + positive_share + log_article_count + C(ticker) + C(target_date)",
                    data=reg,
                ).fit(cov_type="HC3")
                fh.write(model.summary().as_text())
                coef = model.params.to_frame("coef")
                coef["std_err"] = model.bse
                coef["p_value"] = model.pvalues
                coef.to_csv(outdir / "tables/panel_regression_coefficients.csv")
            else:
                fh.write("Not enough observations for fixed-effect regression.\n")
        except Exception as exc:
            fh.write(f"Regression failed: {type(exc).__name__}: {exc}\n")

    # Descriptive daily figure uses the ticker-day panel, so a ticker with many
    # articles does not receive extra weight in the market-return bars.
    sns.set_theme(style="whitegrid")
    daily = panel.groupby("target_date", as_index=False).agg(
        sentiment=("sentiment_score", "mean"), abnormal_return=("abnormal_return", "mean"),
        market_return=("market_return", "mean"), articles=("article_count", "sum"),
        tickers=("ticker", "nunique"),
    )
    daily.to_csv(outdir / "tables/daily_market_sentiment.csv", index=False)
    if not daily.empty:
        fig, ax1 = plt.subplots(figsize=(11, 5.5))
        ax1.plot(daily["target_date"], daily["sentiment"], marker="o", label="Mean sentiment score", color="#2563eb")
        ax1.set_ylabel("Sentiment score")
        ax2 = ax1.twinx()
        ax2.bar(daily["target_date"], daily["abnormal_return"], alpha=0.28, color="#dc2626", label="Mean abnormal return")
        ax2.set_ylabel("Abnormal return (%)")
        ax1.set_title("CafeF sentiment and next-trading-day abnormal return")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(outdir / "figures/sentiment_vs_abnormal_return.png", dpi=180)
        plt.close(fig)

    if not summary.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=summary, x="label", y="mean_abnormal_return", ax=ax, order=["negative", "neutral", "positive"])
        ax.set_title("Mean abnormal return by predicted sentiment")
        ax.set_ylabel("Mean abnormal return (%)")
        fig.tight_layout()
        fig.savefig(outdir / "figures/abnormal_return_by_label.png", dpi=180)
        plt.close(fig)

    print(f"events={len(events)} crisis_events={len(crisis)} market={market_ticker}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
