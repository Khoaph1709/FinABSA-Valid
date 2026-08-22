
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# Styles
# ============================================================

styles = getSampleStyleSheet()

styles.add(
    ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=12,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportNote",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        leftIndent=10,
        rightIndent=10,
        borderWidth=0.5,
        borderColor=colors.grey,
        borderPadding=8,
        backColor=colors.HexColor("#FFF8E1"),
        spaceAfter=10,
    )
)

styles.add(
    ParagraphStyle(
        name="ReportBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        spaceAfter=6,
    )
)

styles.add(
    ParagraphStyle(
        name="FigureCaption",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=12,
    )
)

# Không dùng tên "Code" vì ReportLab đã có style "Code".
styles.add(
    ParagraphStyle(
        name="ReportCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7,
        leading=9,
        leftIndent=10,
        rightIndent=10,
        borderWidth=0.5,
        borderColor=colors.grey,
        borderPadding=8,
        backColor=colors.HexColor("#F5F5F5"),
    )
)


# ============================================================
# Helpers
# ============================================================

def md_table(
    df: pd.DataFrame,
    digits: int = 4,
) -> str:
    """
    Giữ lại helper tương tự code Markdown cũ.
    Có thể dùng nếu sau này muốn sinh Markdown.
    """
    if df.empty:
        return "_No data available._"

    view = df.copy()

    for col in view.select_dtypes(include="number").columns:
        view[col] = view[col].map(
            lambda x: (
                f"{x:.{digits}f}"
                if pd.notna(x)
                else ""
            )
        )

    return view.to_markdown(index=False)


def dataframe_to_reportlab_table(
    df: pd.DataFrame,
    digits: int = 4,
    max_rows: int | None = None,
):
    """
    Convert pandas DataFrame -> ReportLab Table.
    """

    if df.empty:
        return Paragraph(
            "<i>No data available.</i>",
            styles["ReportBody"],
        )

    view = df.copy()

    if max_rows is not None:
        view = view.head(max_rows)

    # Format numeric columns
    for col in view.select_dtypes(include="number").columns:
        view[col] = view[col].map(
            lambda x: (
                f"{x:.{digits}f}"
                if pd.notna(x)
                else ""
            )
        )

    # Replace NaN/None
    view = view.fillna("")

    # Convert everything to string
    view = view.astype(str)

    # Header + body
    data = [
        list(view.columns),
        *view.values.tolist(),
    ]

    table = Table(
        data,
        repeatRows=1,
        hAlign="LEFT",
    )

    table_style = [
        # Header
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#2F5597"),
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white,
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold",
        ),

        # Body
        (
            "FONTNAME",
            (0, 1),
            (-1, -1),
            "Helvetica",
        ),
        (
            "FONTSIZE",
            (0, 0),
            (-1, -1),
            7,
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),

        # Grid
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.4,
            colors.grey,
        ),

        # Padding
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
    ]

    # Alternating row colors
    for row in range(2, len(data), 2):
        table_style.append(
            (
                "BACKGROUND",
                (0, row),
                (-1, row),
                colors.HexColor("#F5F7FA"),
            )
        )

    table.setStyle(TableStyle(table_style))

    return table


def add_section_title(
    story: list,
    title: str,
):
    """
    Add section heading.
    """

    story.append(
        Paragraph(
            title,
            styles["Heading2"],
        )
    )

    story.append(
        Spacer(
            1,
            0.15 * cm,
        )
    )


def add_figure(
    story: list,
    path: Path,
    caption: str,
):
    """
    Add PNG/JPG figure to PDF.
    """

    if not path.exists():
        story.append(
            Paragraph(
                f"<i>Figure not found: {path}</i>",
                styles["ReportBody"],
            )
        )

        story.append(
            Spacer(
                1,
                0.3 * cm,
            )
        )

        return

    try:
        img = Image(str(path))

        max_width = 16 * cm
        max_height = 10 * cm

        if img.imageWidth > 0 and img.imageHeight > 0:
            scale = min(
                max_width / img.imageWidth,
                max_height / img.imageHeight,
                1.0,
            )

            img.drawWidth = img.imageWidth * scale
            img.drawHeight = img.imageHeight * scale

        story.append(img)

        story.append(
            Paragraph(
                caption,
                styles["FigureCaption"],
            )
        )

        story.append(
            Spacer(
                1,
                0.3 * cm,
            )
        )

    except Exception as exc:
        story.append(
            Paragraph(
                f"<i>Could not load figure {path}: {exc}</i>",
                styles["ReportBody"],
            )
        )


def footer(canvas, doc):
    """
    Add page number to every page.
    """

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8,
    )

    canvas.setFillColor(
        colors.grey
    )

    page_number = canvas.getPageNumber()

    canvas.drawCentredString(
        A4[0] / 2,
        0.8 * cm,
        f"Page {page_number}",
    )

    canvas.restoreState()


# ============================================================
# Main
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description="Generate CafeF-FinABSA PDF report."
    )

    parser.add_argument(
        "--analysis",
        default="data/cafef_oct2022/analysis",
        help="Analysis directory.",
    )

    parser.add_argument(
        "--out",
        default="/home/huylkq/repos/nlp/FinABSA-Valid/results/pdf/report_generated.pdf",
        help="Output PDF path.",
    )

    args = parser.parse_args()

    analysis = Path(args.analysis).resolve()
    out = Path(args.out).resolve()

    # ========================================================
    # Check analysis directory
    # ========================================================

    if not analysis.exists():
        raise FileNotFoundError(
            f"Analysis directory not found: {analysis}"
        )

    # ========================================================
    # Load validation
    # ========================================================

    validation = {}

    val_path = (
        analysis / "prediction_validation.json"
    )

    if val_path.exists():
        validation = json.loads(
            val_path.read_text(
                encoding="utf-8"
            )
        )

    # ========================================================
    # Load event summary
    # ========================================================

    summary_path = (
        analysis
        / "tables"
        / "event_summary_by_label.csv"
    )

    if summary_path.exists():
        summary = pd.read_csv(summary_path)
    else:
        summary = pd.DataFrame()

    # ========================================================
    # Load daily sentiment
    # ========================================================

    daily_path = (
        analysis
        / "tables"
        / "daily_market_sentiment.csv"
    )

    if daily_path.exists():
        daily = pd.read_csv(daily_path)
    else:
        daily = pd.DataFrame()

    # ========================================================
    # Load regression coefficients
    # ========================================================

    coef_path = (
        analysis
        / "tables"
        / "panel_regression_coefficients.csv"
    )

    if coef_path.exists():
        coef = pd.read_csv(coef_path)
    else:
        coef = pd.DataFrame()

    # ========================================================
    # Load market models
    # ========================================================

    model_path = (
        analysis / "market_models.csv"
    )

    if model_path.exists():
        market_models = pd.read_csv(
            model_path
        )
    else:
        market_models = pd.DataFrame()

    # ========================================================
    # Create PDF document
    # ========================================================

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,

        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,

        title="CafeF-FinABSA Validation Report",
        author="FinABSA-Valid",
    )

    story = []

    # ========================================================
    # Title
    # ========================================================

    story.append(
        Paragraph(
            "CafeF–FinABSA Validation Report",
            styles["ReportTitle"],
        )
    )

    story.append(
        Paragraph(
            "Báo cáo được sinh tự động từ dữ liệu "
            "và kết quả trong repository.",
            styles["ReportSubtitle"],
        )
    )

    story.append(
        Paragraph(
            "<b>Lưu ý:</b> Các kết luận học thuật cần "
            "được kiểm tra lại sau khi model output hoàn tất.",
            styles["ReportNote"],
        )
    )

    story.append(
        Spacer(
            1,
            0.2 * cm,
        )
    )

    # ========================================================
    # 1. Executive summary
    # ========================================================

    add_section_title(
        story,
        "1. Executive summary",
    )

    input_rows = validation.get(
        "input_rows",
        "N/A",
    )

    prediction_rows = validation.get(
        "prediction_rows",
        "N/A",
    )

    unknown_labels = validation.get(
        "unknown_labels",
        "N/A",
    )

    story.append(
        Paragraph(
            f"Số dòng input: <b>{input_rows}</b>.",
            styles["ReportBody"],
        )
    )

    story.append(
        Paragraph(
            f"Số dòng prediction: "
            f"<b>{prediction_rows}</b>.",
            styles["ReportBody"],
        )
    )

    story.append(
        Paragraph(
            f"Số nhãn chưa parse được: "
            f"<b>{unknown_labels}</b>.",
            styles["ReportBody"],
        )
    )

    story.append(
        Spacer(
            1,
            0.2 * cm,
        )
    )

    story.append(
        Paragraph(
            "Kết quả chính được thiết kế theo "
            "next-trading-day return và abnormal return "
            "dựa trên market model. Đây là kiểm định "
            "liên hệ ngoài mẫu, không phải bằng chứng "
            "nhân quả hay khuyến nghị đầu tư.",
            styles["ReportBody"],
        )
    )

    # ========================================================
    # 2. Prediction validation
    # ========================================================

    add_section_title(
        story,
        "2. Prediction validation",
    )

    validation_json = json.dumps(
        validation,
        ensure_ascii=False,
        indent=2,
    )

    story.append(
        Preformatted(
            validation_json,
            styles["ReportCode"],
        )
    )

    story.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    # ========================================================
    # 3. Event-study summary
    # ========================================================

    add_section_title(
        story,
        "3. Event-study summary",
    )

    story.append(
        dataframe_to_reportlab_table(
            summary,
            digits=4,
        )
    )

    story.append(
        Spacer(
            1,
            0.5 * cm,
        )
    )

    # ========================================================
    # 4. Panel regression
    # ========================================================

    add_section_title(
        story,
        "4. Panel regression",
    )

    story.append(
        dataframe_to_reportlab_table(
            coef,
            digits=4,
        )
    )

    story.append(
        Spacer(
            1,
            0.5 * cm,
        )
    )

    # ========================================================
    # 5. Data coverage
    # ========================================================

    add_section_title(
        story,
        "5. Data coverage",
    )

    story.append(
        Paragraph(
            f"Số ngày aggregate: "
            f"<b>{len(daily)}</b>.",
            styles["ReportBody"],
        )
    )

    story.append(
        Paragraph(
            f"Số ticker có market model: "
            f"<b>{len(market_models)}</b>.",
            styles["ReportBody"],
        )
    )

    story.append(
        Spacer(
            1,
            0.2 * cm,
        )
    )

    story.append(
        dataframe_to_reportlab_table(
            market_models,
            digits=4,
            max_rows=30,
        )
    )

    # ========================================================
    # 6. Figures
    # ========================================================

    story.append(PageBreak())

    add_section_title(
        story,
        "6. Figures",
    )

    figures_dir = (
        analysis / "figures"
    )

    add_figure(
        story,
        figures_dir
        / "sentiment_vs_abnormal_return.png",
        "Figure 1. Sentiment versus abnormal return",
    )

    add_figure(
        story,
        figures_dir
        / "abnormal_return_by_label.png",
        "Figure 2. Abnormal return by label",
    )

    # ========================================================
    # 7. Interpretation checklist
    # ========================================================

    add_section_title(
        story,
        "7. Interpretation checklist",
    )

    checklist = [
        (
            "Kiểm tra temporal leakage: bài sau giờ "
            "đóng cửa không được gán cho cùng phiên."
        ),
        (
            "Kiểm tra entity linking: kết quả chính "
            "nên dùng strict/high-confidence mapping."
        ),
        (
            "So sánh với baseline và placebo; "
            "không chỉ nhìn p-value."
        ),
        (
            "Báo cáo effect size và khoảng tin cậy."
        ),
        (
            "Nếu intrinsic sentiment tốt nhưng extrinsic "
            "không có tín hiệu, đó vẫn là kết quả hợp lệ "
            "của môn NLP."
        ),
    ]

    for index, item in enumerate(
        checklist,
        start=1,
    ):
        story.append(
            Paragraph(
                f"{index}. {item}",
                styles["ReportBody"],
            )
        )

    # ========================================================
    # 8. Limitations
    # ========================================================

    add_section_title(
        story,
        "8. Limitations",
    )

    story.append(
        Paragraph(
            "CafeF là một nguồn tin, không đại diện "
            "toàn bộ thông tin thị trường. Timestamp, "
            "entity linking, coverage của ticker và cờ "
            "adjusted price cần được kiểm tra thủ công. "
            "Kết quả quan sát không chứng minh bài báo "
            "gây ra lợi suất.",
            styles["ReportBody"],
        )
    )

    # ========================================================
    # References
    # ========================================================

    add_section_title(
        story,
        "References",
    )

    references = [
        (
            "1",
            "FinABSA-Valid repository",
            "https://github.com/Khoaph1709/FinABSA-Valid",
        ),
        (
            "2",
            "CafeF",
            "https://cafef.vn/",
        ),
        (
            "3",
            "vnstock",
            "https://github.com/thinh-vu/vnstock",
        ),
    ]

    for number, name, url in references:
        story.append(
            Paragraph(
                f"[{number}] {name}: {url}",
                styles["ReportBody"],
            )
        )

    # ========================================================
    # Build PDF
    # ========================================================

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )

    print(f"saved={out}")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()

