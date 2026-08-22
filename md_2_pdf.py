import argparse
from pathlib import Path

import markdown
from weasyprint import HTML


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    input_file = Path(args.input).resolve()

    if not input_file.is_file():
        raise FileNotFoundError(f"File not found: {input_file}")

    output_file = (
        Path(args.output).resolve()
        if args.output
        else input_file.with_suffix(".pdf")
    )

    md_text = input_file.read_text(encoding="utf-8")

    html = markdown.markdown(
        md_text,
        extensions=[
            "extra",
            "tables",
            "fenced_code",
            "toc",
        ],
    )

    html_document = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}

            body {{
                font-family: sans-serif;
                font-size: 11pt;
                line-height: 1.5;
            }}

            h1, h2, h3 {{
                margin-top: 1.5em;
            }}

            code {{
                font-family: monospace;
            }}

            pre {{
                padding: 10px;
                overflow-x: auto;
                background: #f5f5f5;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
            }}

            th, td {{
                border: 1px solid #ccc;
                padding: 6px;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    HTML(string=html_document).write_pdf(str(output_file))

    print(f"Created: {output_file}")


if __name__ == "__main__":
    main()