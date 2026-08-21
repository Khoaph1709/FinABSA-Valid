from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


LABEL_ORDER = ["negative", "neutral", "positive"]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def md_table(df: pd.DataFrame, digits: int = 4) -> str:
    if df.empty:
        return "_No data available._"
    view = df.copy()
    for col in view.select_dtypes(include="number").columns:
        view[col] = view[col].map(lambda x: f"{x:.{digits}f}" if pd.notna(x) else "")
    return view.to_markdown(index=False)


def parse_panel_meta(path: Path) -> dict[str, str]:
    meta: dict[str, str] = {}
    if not path.exists():
        return meta
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("="):
            key, value = line.split("=", 1)
            meta[key.strip()] = value.strip()
    return meta


def relative_image(image: Path, report_path: Path) -> str:
    return os.path.relpath(image.resolve(), report_path.parent.resolve()).replace(os.sep, "/")


def safe_float(value: Any) -> float | None:
    try:
        result = float(value)
        return result if np.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def generate_figures(analysis: Path, validation: dict[str, Any], summary: pd.DataFrame, daily: pd.DataFrame, group_tests: pd.DataFrame, robustness: pd.DataFrame, market_models: pd.DataFrame, panel: pd.DataFrame) -> dict[str, Path]:
    figures = analysis / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titlesize": 12, "axes.labelsize": 10})
    output: dict[str, Path] = {}

    counts = validation.get("label_counts", {}) if isinstance(validation, dict) else {}
    if not counts and not panel.empty and "label" in panel.columns:
        counts = panel["label"].value_counts().to_dict()
    count_df = pd.DataFrame({"label": LABEL_ORDER, "count": [int(counts.get(x, 0)) for x in LABEL_ORDER]})
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bars = ax.bar(count_df["label"], count_df["count"], color=["#d95f5f", "#7f8fa6", "#3b82c4"])
    ax.set_title("Prediction distribution by sentiment")
    ax.set_xlabel("Predicted sentiment")
    ax.set_ylabel("Number of predictions")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{int(bar.get_height())}", ha="center", va="bottom")
    fig.tight_layout()
    path = figures / "prediction_distribution.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    output["prediction_distribution"] = path

    if not daily.empty and "target_date" in daily.columns:
        plot_daily = daily.copy()
        plot_daily["target_date"] = pd.to_datetime(plot_daily["target_date"], errors="coerce")
        plot_daily = plot_daily.dropna(subset=["target_date"]).sort_values("target_date")
        fig, ax1 = plt.subplots(figsize=(11, 5.5))
        ax1.plot(plot_daily["target_date"], plot_daily["sentiment"], marker="o", color="#2563eb", label="Mean sentiment")
        ax1.axhline(0, color="#666", linewidth=0.7)
        ax1.set_ylabel("Mean sentiment score")
        ax2 = ax1.twinx()
        ax2.bar(plot_daily["target_date"], plot_daily["abnormal_return"], width=0.7, alpha=0.28, color="#dc2626", label="Mean abnormal return")
        ax2.set_ylabel("Mean abnormal return (%)")
        ax1.set_title("Sentiment and next-trading-day abnormal return")
        ax1.set_xlabel("Evaluation date")
        fig.autofmt_xdate()
        fig.tight_layout()
        path = figures / "sentiment_vs_abnormal_return.png"
        fig.savefig(path, dpi=220)
        plt.close(fig)
        output["daily_sentiment_ar"] = path

    if not summary.empty and {"label", "mean_abnormal_return"}.issubset(summary.columns):
        plot_summary = summary.set_index("label").reindex(LABEL_ORDER).reset_index()
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(plot_summary["label"], plot_summary["mean_abnormal_return"], color=["#d95f5f", "#7f8fa6", "#3b82c4"])
        ax.axhline(0, color="#333", linewidth=0.8)
        ax.set_title("Mean abnormal return by predicted sentiment")
        ax.set_xlabel("Predicted sentiment")
        ax.set_ylabel("Mean abnormal return (%)")
        for bar, n in zip(bars, plot_summary.get("events", pd.Series([0] * len(plot_summary)))):
            value = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, value, f"N={int(n)}", ha="center", va="bottom" if value >= 0 else "top")
        fig.tight_layout()
        path = figures / "abnormal_return_by_label.png"
        fig.savefig(path, dpi=220)
        plt.close(fig)
        output["ar_by_label"] = path

    if not group_tests.empty and {"comparison", "difference", "bootstrap_ci_low", "bootstrap_ci_high"}.issubset(group_tests.columns):
        gt = group_tests.dropna(subset=["difference"]).copy()
        if not gt.empty:
            fig, ax = plt.subplots(figsize=(9, 4.8))
            x = np.arange(len(gt))
            means = gt["difference"].to_numpy(dtype=float)
            lower = means - gt["bootstrap_ci_low"].to_numpy(dtype=float)
            upper = gt["bootstrap_ci_high"].to_numpy(dtype=float) - means
            ax.errorbar(x, means, yerr=[lower, upper], fmt="o", capsize=5, color="#111827")
            ax.axhline(0, color="#777", linewidth=0.8)
            ax.set_xticks(x, gt["comparison"].str.replace("_minus_", " − ", regex=False))
            ax.set_ylabel("Difference in mean abnormal return (%)")
            ax.set_title("Sentiment-group contrasts with bootstrap 95% CI")
            fig.tight_layout()
            path = figures / "sentiment_group_tests.png"
            fig.savefig(path, dpi=220)
            plt.close(fig)
            output["group_tests"] = path

    if not robustness.empty and {"lag", "mean_ar"}.issubset(robustness.columns):
        rb = robustness.dropna(subset=["lag", "mean_ar"]).sort_values("lag")
        if not rb.empty:
            fig, ax = plt.subplots(figsize=(8, 4.8))
            ax.plot(rb["lag"], rb["mean_ar"], marker="o", color="#7c3aed")
            ax.axhline(0, color="#777", linewidth=0.8)
            ax.set_xticks(rb["lag"])
            ax.set_xlabel("Lag after first tradable session")
            ax.set_ylabel("Mean abnormal return (%)")
            ax.set_title("Lag robustness")
            fig.tight_layout()
            path = figures / "robustness_lags.png"
            fig.savefig(path, dpi=220)
            plt.close(fig)
            output["robustness"] = path

    if not market_models.empty and "n_estimation" in market_models.columns:
        values = pd.to_numeric(market_models["n_estimation"], errors="coerce").dropna()
        if not values.empty:
            fig, ax = plt.subplots(figsize=(8, 4.8))
            ax.hist(values, bins=min(12, max(3, values.nunique())), color="#4f81bd", edgecolor="white")
            ax.set_title("Market-model estimation-window coverage")
            ax.set_xlabel("Number of estimation observations")
            ax.set_ylabel("Number of tickers")
            fig.tight_layout()
            path = figures / "market_model_coverage.png"
            fig.savefig(path, dpi=220)
            plt.close(fig)
            output["market_coverage"] = path

    return output


def make_pdf(markdown_text: str, pdf_path: Path) -> str | None:
    try:
        import markdown as markdown_lib
        from weasyprint import CSS, HTML

        body = markdown_lib.markdown(markdown_text, extensions=["tables", "fenced_code"])
        css = CSS(string="""
            @page { size: A4; margin: 16mm 15mm 16mm 15mm; }
            @font-face { font-family: ReportSans; src: url('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'); }
            body { font-family: ReportSans, 'DejaVu Sans', sans-serif; font-size: 9.5pt; line-height: 1.35; color: #1f2937; }
            h1 { color: #163a63; font-size: 21pt; margin-bottom: 5pt; }
            h2 { color: #214e7a; font-size: 14pt; border-bottom: 1px solid #d1d5db; padding-bottom: 3pt; margin-top: 16pt; }
            h3 { color: #214e7a; font-size: 11pt; }
            table { border-collapse: collapse; width: 100%; margin: 7pt 0 12pt 0; font-size: 7.5pt; }
            th { background: #1f4e79; color: white; font-weight: bold; }
            th, td { border: 0.5pt solid #9ca3af; padding: 3pt 4pt; vertical-align: top; }
            tr:nth-child(even) td { background: #f3f6fa; }
            img { max-width: 100%; height: auto; display: block; margin: 7pt auto 12pt auto; }
            blockquote { border-left: 3pt solid #9ca3af; padding-left: 8pt; color: #4b5563; }
            code { font-family: monospace; font-size: 8pt; }
        """)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=f"<html><head><meta charset='utf-8'></head><body>{body}</body></html>", base_url=str(pdf_path.parent.resolve())).write_pdf(str(pdf_path), stylesheets=[css])
        return None
    except Exception as exc:  # PDF is optional; Markdown remains the source of truth.
        return f"PDF generation failed: {type(exc).__name__}: {exc}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", default="data/cafef_oct2022/analysis")
    parser.add_argument("--out", default="report_generated.md")
    parser.add_argument("--pdf", default="report_generated.pdf")
    args = parser.parse_args()

    analysis = Path(args.analysis)
    out = Path(args.out)
    validation_path = analysis / "prediction_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.exists() else {}
    tables = analysis / "tables"
    summary = read_csv(tables / "event_summary_by_label.csv")
    daily = read_csv(tables / "daily_market_sentiment.csv")
    group_tests = read_csv(tables / "sentiment_group_tests.csv")
    panel_summary = read_csv(tables / "panel_summary_by_label.csv")
    robustness = read_csv(tables / "robustness_summary.csv")
    coef = read_csv(tables / "panel_regression_coefficients.csv")
    panel = read_csv(tables / "panel_regression_data.csv")
    market_models = read_csv(analysis / "market_models.csv")
    meta = parse_panel_meta(tables / "panel_regression.txt")
    figures = generate_figures(analysis, validation, summary, daily, group_tests, robustness, market_models, panel)

    if not coef.empty:
        term_col = "Unnamed: 0" if "Unnamed: 0" in coef.columns else coef.columns[0]
        coef = coef.rename(columns={term_col: "term"})
        coef = coef[coef["term"].isin({"Intercept", "sentiment_score", "negative_share", "positive_share", "log_article_count"})]

    label_counts = validation.get("label_counts", {}) if isinstance(validation, dict) else {}
    input_rows = validation.get("input_rows", "N/A")
    prediction_rows = validation.get("prediction_rows", "N/A")
    unknown = validation.get("unknown_labels", "N/A")
    panel_obs = meta.get("observations", len(panel) if not panel.empty else "N/A")
    panel_tickers = meta.get("unique_tickers", panel["ticker"].nunique() if not panel.empty and "ticker" in panel.columns else "N/A")
    panel_dates = meta.get("unique_dates", panel["target_date"].nunique() if not panel.empty and "target_date" in panel.columns else "N/A")

    lines: list[str] = []
    lines += [
        "# CafeF–FinABSA Validation Report",
        "",
        "> Báo cáo này được sinh tự động từ các file dữ liệu và kết quả trong repository. Kết quả downstream là association ngoài mẫu, không phải bằng chứng nhân quả hay khuyến nghị đầu tư.",
        "",
        "## 1. Executive summary",
        "",
        f"Pipeline đã xử lý **{input_rows}** dòng input và **{prediction_rows}** prediction; số label không parse được là **{unknown}**. Đơn vị inference là article–ticker, còn đơn vị panel là ticker–ngày để tránh lặp lại abnormal return khi có nhiều bài về cùng mã trong một ngày.",
        "",
        "Báo cáo này bao gồm validation prediction, phân bố sentiment, event-study summary, kiểm định chênh lệch giữa các nhóm sentiment, panel regression, lag robustness, market-model coverage và toàn bộ biểu đồ được sinh từ cùng các file intermediate.",
        "",
        "## 2. Prediction validation",
        "",
        md_table(pd.DataFrame([{"input_rows": input_rows, "prediction_rows": prediction_rows, "missing_predictions": validation.get("missing_predictions", "N/A"), "unexpected_predictions": validation.get("unexpected_predictions", "N/A"), "unknown_labels": unknown}])),
        "",
        "```json",
        json.dumps(validation, ensure_ascii=False, indent=2),
        "```",
        "",
        "### Prediction distribution",
        "",
        md_table(pd.DataFrame({"label": LABEL_ORDER, "count": [label_counts.get(x, 0) for x in LABEL_ORDER]})),
        "",
        "## 3. Data and market coverage",
        "",
        f"Số ngày aggregate: **{len(daily) if not daily.empty else 'N/A'}**. Số ticker có market model: **{len(market_models) if not market_models.empty else 'N/A'}**. Panel regression có **{panel_obs}** quan sát, **{panel_tickers}** ticker và **{panel_dates}** ngày; đơn vị là **{meta.get('unit', 'ticker-day')}**.",
        "",
        md_table(market_models.head(30)),
        "",
    ]
    if "market_coverage" in figures:
        lines += [f"![Market-model estimation coverage]({relative_image(figures['market_coverage'], out)})", ""]

    lines += ["## 4. Event-study results", "", md_table(summary), ""]
    if "ar_by_label" in figures:
        lines += [f"![Mean abnormal return by sentiment]({relative_image(figures['ar_by_label'], out)})", ""]
    if not panel_summary.empty:
        lines += ["### Panel-level summary", "", md_table(panel_summary), ""]

    lines += ["## 5. Statistical tests", ""]
    if group_tests.empty:
        lines += ["_No group-test output was available._", ""]
    else:
        lines += ["Các group tests dùng đơn vị ticker–ngày. `difference` là mean AR của group A trừ group B; p-value Welch là kiểm định tham khảo, permutation p-value không dựa trên giả định chuẩn, còn bootstrap CI thể hiện độ bất định của effect size.", "", md_table(group_tests), ""]
        if "group_tests" in figures:
            lines += [f"![Sentiment group contrasts]({relative_image(figures['group_tests'], out)})", ""]

    lines += ["## 6. Panel regression", "", f"Specification sử dụng ticker fixed effects và date fixed effects. Metadata: observations={panel_obs}, unique_tickers={panel_tickers}, unique_dates={panel_dates}.", "", md_table(coef), ""]

    lines += ["## 7. Robustness and sensitivity", ""]
    if robustness.empty:
        lines += ["_No robustness output was available._", ""]
    else:
        lines += ["Bảng dưới đây kiểm tra sự thay đổi của abnormal return khi dịch evaluation date theo các lag khác nhau. Đây là sensitivity analysis, không phải bằng chứng causal.", "", md_table(robustness), ""]
        if "robustness" in figures:
            lines += [f"![Lag robustness]({relative_image(figures['robustness'], out)})", ""]

    lines += ["## 8. Figures overview", ""]
    for title, key in [
        ("Prediction distribution", "prediction_distribution"),
        ("Daily sentiment and abnormal return", "daily_sentiment_ar"),
    ]:
        if key in figures:
            lines += [f"### {title}", "", f"![{title}]({relative_image(figures[key], out)})", ""]

    lines += [
        "## 9. Reproducibility and interpretation",
        "",
        "Các file trung gian quan trọng gồm `prediction_validation.json`, `article_ticker_sentiment.csv`, `article_ticker_day_sentiment.csv`, `event_observations.csv`, `panel_regression_data.csv`, `sentiment_group_tests.csv` và `robustness_summary.csv`. Không được ghép aggregate theo thứ tự dòng; pipeline dùng khóa `ticker + published_date`.",
        "",
        "Kết quả cần được diễn giải theo hướng: mô hình tạo ra một phân bố sentiment và các nhóm sentiment có abnormal return khác nhau trong mẫu quan sát. Nếu p-value hoặc confidence interval không ủng hộ effect, kết luận phù hợp là chưa có bằng chứng ổn định trong cửa sổ dữ liệu này. Kết quả không chứng minh tin tức gây ra biến động giá.",
        "",
        "## 10. Limitations",
        "",
        "CafeF chỉ là một nguồn tin; entity linking và timestamp có thể tạo measurement error. Phân bố nhãn có thể mất cân bằng. Market model phụ thuộc vào coverage và trạng thái adjusted/unadjusted của dữ liệu giá. Cửa sổ một tháng có statistical power hạn chế, nên các kiểm định bổ sung cần được xem là sensitivity analysis.",
        "",
        "## References",
        "",
        "[1]: https://github.com/Khoaph1709/FinABSA-Valid FinABSA-Valid repository",
        "[2]: https://cafef.vn/ CafeF",
        "[3]: https://github.com/thinh-vu/vnstock vnstock",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    markdown_text = "\n".join(lines)
    out.write_text(markdown_text, encoding="utf-8")
    pdf_error = make_pdf(markdown_text, Path(args.pdf)) if args.pdf else None
    print(f"saved_markdown={out}")
    if args.pdf:
        print(f"saved_pdf={args.pdf}" if pdf_error is None else pdf_error)
    print(f"figures_generated={len(figures)}")


if __name__ == "__main__":
    main()
