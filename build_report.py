from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def md_table(df: pd.DataFrame, digits: int = 4) -> str:
    if df.empty:
        return "_No data available._"
    view = df.copy()
    for col in view.select_dtypes(include="number").columns:
        view[col] = view[col].map(lambda x: f"{x:.{digits}f}" if pd.notna(x) else "")
    return view.to_markdown(index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", default="data/cafef_oct2022/analysis")
    parser.add_argument("--out", default="report_generated.md")
    args = parser.parse_args()
    analysis = Path(args.analysis)
    out = Path(args.out)

    validation = {}
    val_path = analysis / "prediction_validation.json"
    if val_path.exists():
        validation = json.loads(val_path.read_text(encoding="utf-8"))
    summary_path = analysis / "tables/event_summary_by_label.csv"
    summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
    daily_path = analysis / "tables/daily_market_sentiment.csv"
    daily = pd.read_csv(daily_path) if daily_path.exists() else pd.DataFrame()
    coef_path = analysis / "tables/panel_regression_coefficients.csv"
    coef = pd.read_csv(coef_path) if coef_path.exists() else pd.DataFrame()
    model_path = analysis / "market_models.csv"
    market_models = pd.read_csv(model_path) if model_path.exists() else pd.DataFrame()

    lines = []
    lines += ["# CafeF–FinABSA Validation Report", "", "> Báo cáo này được sinh tự động từ dữ liệu và kết quả trong repository. Các kết luận học thuật cần được kiểm tra lại sau khi model output hoàn tất.", ""]
    lines += ["## 1. Executive summary", "", f"Số dòng input: **{validation.get('input_rows', 'N/A')}**. Số dòng prediction: **{validation.get('prediction_rows', 'N/A')}**. Số nhãn chưa parse được: **{validation.get('unknown_labels', 'N/A')}**.", "", "Kết quả chính được thiết kế theo next-trading-day return và abnormal return dựa trên market model. Đây là kiểm định liên hệ ngoài mẫu, không phải bằng chứng nhân quả hay khuyến nghị đầu tư.", ""]
    lines += ["## 2. Prediction validation", "", "```json", json.dumps(validation, ensure_ascii=False, indent=2), "```", ""]
    lines += ["## 3. Event-study summary", "", md_table(summary), ""]
    lines += ["## 4. Panel regression", "", md_table(coef), ""]
    lines += ["## 5. Data coverage", "", f"Số ngày aggregate: **{len(daily)}**. Số ticker có market model: **{len(market_models)}**.", "", md_table(market_models.head(30)), ""]
    lines += ["## 6. Figures", "", "![Sentiment versus abnormal return](data/cafef_oct2022/analysis/figures/sentiment_vs_abnormal_return.png)", "", "![Abnormal return by label](data/cafef_oct2022/analysis/figures/abnormal_return_by_label.png)", ""]
    lines += ["## 7. Interpretation checklist", "", "1. Kiểm tra temporal leakage: bài sau giờ đóng cửa không được gán cho cùng phiên.", "2. Kiểm tra entity linking: kết quả chính nên dùng strict/high-confidence mapping.", "3. So sánh với baseline và placebo; không chỉ nhìn p-value.", "4. Báo cáo effect size và khoảng tin cậy.", "5. Nếu intrinsic sentiment tốt nhưng extrinsic không có tín hiệu, đó vẫn là kết quả hợp lệ của môn NLP.", "", "## 8. Limitations", "", "CafeF là một nguồn tin, không đại diện toàn bộ thông tin thị trường. Timestamp, entity linking, coverage của ticker và cờ adjusted price cần được kiểm tra thủ công. Kết quả quan sát không chứng minh bài báo gây ra lợi suất.", "", "## References", "", "[1]: https://github.com/Khoaph1709/FinABSA-Valid FinABSA-Valid repository", "[2]: https://cafef.vn/ CafeF", "[3]: https://github.com/thinh-vu/vnstock vnstock", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved={out}")


if __name__ == "__main__":
    main()
