# FinABSA--CafeF Slide Deck for Prism

Gói này chứa `slide.tex` và đúng tám hình được slide tham chiếu trong bốn thư mục kỳ dữ liệu. Cấu trúc thư mục phải được giữ nguyên khi tải lên Prism.

## Cách compile

1. Tải toàn bộ nội dung gói lên cùng một project Prism, không chỉ tải riêng `slide.tex`.
2. Mở `slide.tex` làm file chính.
3. Dùng engine mặc định của Prism, tức **pdfLaTeX**. File đã dùng `\usepackage[utf8]{inputenc}` và `\usepackage[T5]{fontenc}`, nên không cần XeLaTeX hoặc LuaLaTeX.
4. Nếu Prism vẫn hiện lỗi font tiếng Việt, hãy bảo đảm project đang compile `slide.tex` chứ không phải một file `.tex` khác.

## Nội dung deck

Deck gồm 12 slide tiếng Việt: động cơ nghiên cứu, pipeline và data contract, dữ liệu 2019--2022, kiểm định event study, CAR, news-day control, sentiment contrasts, fixed effects, lag robustness, diagnostic figures, limitations, future work và kết luận.

## Các đường dẫn hình được dùng

- `2019-10/analysis/figures/abnormal_return_by_label.png`
- `2020-10/analysis/figures/abnormal_return_by_label.png`
- `2021-10/analysis/figures/abnormal_return_by_label.png`
- `2022-10/analysis/figures/abnormal_return_by_label.png`
- `2019-10/analysis/figures/sentiment_vs_abnormal_return.png`
- `2020-10/analysis/figures/sentiment_vs_abnormal_return.png`
- `2021-10/analysis/figures/sentiment_vs_abnormal_return.png`
- `2022-10/analysis/figures/sentiment_vs_abnormal_return.png`

Các bảng trong slide là bản tóm tắt để thuyết trình; toàn bộ bảng kết quả còn nằm trong `data/cafef_multiyear/analysis_multiyear/multiyear_validation_tables.xlsx`.

## Tùy chỉnh trước khi nộp

Thay `\institute{Natural Language Processing}` và `\date{\today}` trong `slide.tex` nếu cần tên trường/khoa hoặc ngày trình bày cụ thể.
