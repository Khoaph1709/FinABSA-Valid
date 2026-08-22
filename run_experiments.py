from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


LABEL_ORDER = ["negative", "neutral", "positive"]


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


def welch_permutation_bootstrap(panel: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    """Compare panel abnormal returns across sentiment groups.

    The unit is one ticker-day, matching the market outcome. Permutation and
    bootstrap use a fixed RNG seed for reproducibility.
    """
    from scipy import stats

    rows = []
    comparisons = [("positive", "neutral"), ("negative", "neutral"), ("positive", "negative")]
    rng = np.random.default_rng(2026)
    for label_a, label_b in comparisons:
        a = panel.loc[panel["label"] == label_a, "abnormal_return"].dropna().to_numpy(dtype=float)
        b = panel.loc[panel["label"] == label_b, "abnormal_return"].dropna().to_numpy(dtype=float)
        row = {"comparison": f"{label_a}_minus_{label_b}", "group_a": label_a, "group_b": label_b, "n_a": len(a), "n_b": len(b)}
        if len(a) < 2 or len(b) < 2:
            row.update({"mean_a": np.nan, "mean_b": np.nan, "difference": np.nan, "welch_t": np.nan, "welch_p": np.nan, "permutation_p": np.nan, "bootstrap_ci_low": np.nan, "bootstrap_ci_high": np.nan})
            rows.append(row)
            continue
        observed = float(a.mean() - b.mean())
        std_a = float(np.std(a, ddof=1))
        std_b = float(np.std(b, ddof=1))
        if np.isclose(std_a, 0.0) and np.isclose(std_b, 0.0):
            welch_t = 0.0 if np.isclose(observed, 0.0) else float(np.sign(observed) * np.inf)
            welch_p = 1.0 if np.isclose(observed, 0.0) else 0.0
        else:
            welch = stats.ttest_ind(a, b, equal_var=False, nan_policy="omit")
            welch_t, welch_p = float(welch.statistic), float(welch.pvalue)
        pooled = np.concatenate([a, b])
        n_a = len(a)
        perm_diffs = np.empty(5000, dtype=float)
        for i in range(len(perm_diffs)):
            shuffled = rng.permutation(pooled)
            perm_diffs[i] = shuffled[:n_a].mean() - shuffled[n_a:].mean()
        permutation_p = float((np.sum(np.abs(perm_diffs) >= abs(observed)) + 1) / (len(perm_diffs) + 1))
        boot_diffs = np.empty(5000, dtype=float)
        for i in range(len(boot_diffs)):
            boot_diffs[i] = rng.choice(a, len(a), replace=True).mean() - rng.choice(b, len(b), replace=True).mean()
        ci_low, ci_high = np.percentile(boot_diffs, [2.5, 97.5])
        row.update({"mean_a": float(a.mean()), "mean_b": float(b.mean()), "difference": observed, "welch_t": welch_t, "welch_p": welch_p, "permutation_p": permutation_p, "bootstrap_ci_low": float(ci_low), "bootstrap_ci_high": float(ci_high)})
        rows.append(row)
    result = pd.DataFrame(rows)
    result.to_csv(outdir / "tables/sentiment_group_tests.csv", index=False)
    return result


def _bootstrap_mean_ci(values: np.ndarray, rng: np.random.Generator, n_boot: int = 5000) -> tuple[float, float]:
    if len(values) < 2:
        return (np.nan, np.nan)
    means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        means[i] = rng.choice(values, len(values), replace=True).mean()
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def _sign_flip_pvalue(values: np.ndarray, rng: np.random.Generator, n_perm: int = 5000) -> float:
    if len(values) < 2:
        return np.nan
    observed = abs(float(values.mean()))
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_perm, len(values)))
    perm_means = (signs * values[None, :]).mean(axis=1)
    return float((np.sum(np.abs(perm_means) >= observed) + 1) / (n_perm + 1))


def build_car_analysis(events: pd.DataFrame, prices: pd.DataFrame, outdir: Path, crisis_start: pd.Timestamp, crisis_end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build event-window CARs and tests using ticker-day abnormal returns."""
    from scipy import stats

    p = prices.copy()
    p["date"] = pd.to_datetime(p["date"], errors="coerce").dt.normalize()
    p["ticker"] = p["ticker"].astype(str).str.upper().str.strip()
    p["abnormal_return"] = pd.to_numeric(p["abnormal_return"], errors="coerce")
    p = p.dropna(subset=["ticker", "date", "abnormal_return"]).sort_values(["ticker", "date"])
    windows = {"0_0": 0, "0_1": 1, "0_3": 3}
    event_units = events.dropna(subset=["ticker", "target_date"]).copy()
    event_units["ticker"] = event_units["ticker"].astype(str).str.upper().str.strip()
    event_units["target_date"] = pd.to_datetime(event_units["target_date"], errors="coerce").dt.normalize()
    event_units = event_units.groupby(["ticker", "target_date"], as_index=False).agg(
        sample_id=("sample_id", "first"), article_count=("article_id", "nunique"),
        label=("label", lambda x: x.value_counts().index[0] if len(x) else "unknown"),
        sentiment_score=("sentiment_score", "mean"),
    )
    rows = []
    for _, event in event_units.iterrows():
        ticker = str(event["ticker"]).upper().strip()
        target = pd.Timestamp(event["target_date"]).normalize()
        grp = p[p["ticker"] == ticker].reset_index(drop=True)
        dates = grp["date"].to_numpy(dtype="datetime64[ns]")
        start = int(np.searchsorted(dates, np.datetime64(target), side="left"))
        if start >= len(grp) or dates[start] != np.datetime64(target):
            continue
        ars = grp["abnormal_return"].to_numpy(dtype=float)
        row = {"sample_id": event.get("sample_id", ""), "article_count": event.get("article_count", 1), "ticker": ticker, "target_date": target, "label": event.get("label", "unknown"), "sentiment_score": event.get("sentiment_score", np.nan)}
        for window, end_offset in windows.items():
            end = start + end_offset + 1
            values = ars[start:end]
            row[f"car_{window}"] = float(values.sum()) if len(values) == end_offset + 1 and np.isfinite(values).all() else np.nan
        rows.append(row)
    car_events = pd.DataFrame(rows)
    car_events.to_csv(outdir / "car_event_rows.csv", index=False)

    test_rows = []
    rng = np.random.default_rng(2026)
    groups = [("all", car_events)] + [(label, car_events[car_events["label"] == label]) for label in LABEL_ORDER]
    for window in windows:
        col = f"car_{window}"
        for group, subset in groups:
            values = pd.to_numeric(subset[col], errors="coerce").dropna().to_numpy(dtype=float) if col in subset else np.array([], dtype=float)
            result = {"window": f"[0,+{windows[window]}]", "window_key": window, "group": group, "n": len(values), "mean_car": np.nan, "median_car": np.nan, "t_stat": np.nan, "t_p": np.nan, "sign_flip_p": np.nan, "bootstrap_ci_low": np.nan, "bootstrap_ci_high": np.nan}
            if len(values) >= 2:
                std = float(np.std(values, ddof=1))
                if np.isclose(std, 0.0):
                    t_stat = 0.0 if np.isclose(float(values.mean()), 0.0) else float(np.sign(values.mean()) * np.inf)
                    t_p = 1.0 if np.isclose(float(values.mean()), 0.0) else 0.0
                else:
                    ttest = stats.ttest_1samp(values, 0.0, nan_policy="omit")
                    t_stat, t_p = float(ttest.statistic), float(ttest.pvalue)
                ci_low, ci_high = _bootstrap_mean_ci(values, rng)
                result.update({"mean_car": float(values.mean()), "median_car": float(np.median(values)), "t_stat": t_stat, "t_p": t_p, "sign_flip_p": _sign_flip_pvalue(values, rng), "bootstrap_ci_low": ci_low, "bootstrap_ci_high": ci_high})
            test_rows.append(result)
    car_tests = pd.DataFrame(test_rows)
    car_tests.to_csv(outdir / "tables/car_tests.csv", index=False)
    return car_events, car_tests


def build_news_day_control(events: pd.DataFrame, prices: pd.DataFrame, outdir: Path, crisis_start: pd.Timestamp, crisis_end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare abnormal returns on news days versus eligible non-news days."""
    from scipy import stats

    event_base = events.dropna(subset=["ticker", "target_date"]).copy()
    event_base["ticker"] = event_base["ticker"].astype(str).str.upper().str.strip()
    event_base["target_date"] = pd.to_datetime(event_base["target_date"], errors="coerce").dt.normalize()
    event_base = event_base.dropna(subset=["target_date"])
    panel = event_base.groupby(["ticker", "target_date"], as_index=False).agg(
        sentiment_score=("sentiment_score", "mean"),
        article_count=("article_id", "nunique"),
        label=("label", lambda x: x.value_counts().index[0] if len(x) else "unknown"),
    )
    p = prices.copy()
    p["ticker"] = p["ticker"].astype(str).str.upper().str.strip()
    p["date"] = pd.to_datetime(p["date"], errors="coerce").dt.normalize()
    p["abnormal_return"] = pd.to_numeric(p["abnormal_return"], errors="coerce")
    eligible = set(event_base["ticker"].unique())
    control = p[p["ticker"].isin(eligible) & p["date"].between(crisis_start, crisis_end)].copy()
    control = control[["ticker", "date", "abnormal_return"]].rename(columns={"date": "target_date"})
    control = control.merge(panel, on=["ticker", "target_date"], how="left", validate="one_to_one")
    control["news_event"] = control["label"].notna().astype(int)
    control["label"] = control["label"].fillna("no_news")
    control["sentiment_score"] = pd.to_numeric(control["sentiment_score"], errors="coerce")
    control["article_count"] = pd.to_numeric(control["article_count"], errors="coerce").fillna(0)
    control.to_csv(outdir / "tables/news_day_control.csv", index=False)

    news = control.loc[control["news_event"] == 1, "abnormal_return"].dropna().to_numpy(dtype=float)
    no_news = control.loc[control["news_event"] == 0, "abnormal_return"].dropna().to_numpy(dtype=float)
    row = {"comparison": "news_day_minus_no_news_day", "n_news": len(news), "n_no_news": len(no_news), "mean_news_ar": np.nan, "mean_no_news_ar": np.nan, "difference": np.nan, "welch_t": np.nan, "welch_p": np.nan, "permutation_p": np.nan, "bootstrap_ci_low": np.nan, "bootstrap_ci_high": np.nan}
    if len(news) >= 2 and len(no_news) >= 2:
        rng = np.random.default_rng(2027)
        observed = float(news.mean() - no_news.mean())
        std_news = float(np.std(news, ddof=1))
        std_no_news = float(np.std(no_news, ddof=1))
        if np.isclose(std_news, 0.0) and np.isclose(std_no_news, 0.0):
            welch_t = 0.0 if np.isclose(observed, 0.0) else float(np.sign(observed) * np.inf)
            welch_p = 1.0 if np.isclose(observed, 0.0) else 0.0
        else:
            welch = stats.ttest_ind(news, no_news, equal_var=False, nan_policy="omit")
            welch_t, welch_p = float(welch.statistic), float(welch.pvalue)
        pooled = np.concatenate([news, no_news])
        perm = np.empty(5000, dtype=float)
        for i in range(len(perm)):
            shuffled = rng.permutation(pooled)
            perm[i] = shuffled[: len(news)].mean() - shuffled[len(news):].mean()
        boot = np.empty(5000, dtype=float)
        for i in range(len(boot)):
            boot[i] = rng.choice(news, len(news), replace=True).mean() - rng.choice(no_news, len(no_news), replace=True).mean()
        ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
        row.update({"mean_news_ar": float(news.mean()), "mean_no_news_ar": float(no_news.mean()), "difference": observed, "welch_t": welch_t, "welch_p": welch_p, "permutation_p": float((np.sum(np.abs(perm) >= abs(observed)) + 1) / (len(perm) + 1)), "bootstrap_ci_low": float(ci_low), "bootstrap_ci_high": float(ci_high)})
    tests = pd.DataFrame([row])
    tests.to_csv(outdir / "tables/news_day_control_tests.csv", index=False)
    return control, tests


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
    crisis_start = pd.Timestamp(args.crisis_start)
    crisis_end = pd.Timestamp(args.crisis_end)
    car_events, car_tests = build_car_analysis(events[events["in_crisis"]].copy(), ticker_prices, outdir, crisis_start, crisis_end)
    control, control_tests = build_news_day_control(events, ticker_prices, outdir, crisis_start, crisis_end)
    # Build a genuine ticker-day panel before regression. The event table can
    # contain multiple articles for the same ticker-day, but the market outcome
    # is one return per ticker-day and must not be repeated in the regression.
    panel = (
        crisis.groupby(["ticker", "target_date"], as_index=False)
        .agg(
            label=("label", lambda x: x.value_counts().index[0] if len(x) else "unknown"),
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
    panel_summary = panel.groupby("label", dropna=False).agg(
        panel_events=("sample_id", "count") if "sample_id" in panel.columns else ("ticker", "count"),
        mean_sentiment=("sentiment_score", "mean"),
        mean_abnormal_return=("abnormal_return", "mean"),
        median_abnormal_return=("abnormal_return", "median"),
        mean_article_count=("article_count", "mean"),
        mean_event_rows=("event_rows", "mean"),
    ).reset_index()
    panel_summary.to_csv(outdir / "tables/panel_summary_by_label.csv", index=False)
    welch_permutation_bootstrap(panel, outdir)

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
