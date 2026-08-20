# Đánh giá ý tưởng dự án dưới góc độ môn NLP

## Kết luận

Ý tưởng **phù hợp với môn NLP và có tiềm năng rất tốt**, nhưng chỉ khi phần trung tâm được đặt ở bài toán ngôn ngữ: target/entity linking, target-masked aspect sentiment, domain adaptation tiếng Việt tài chính, intrinsic evaluation và error analysis. Nếu báo cáo chỉ lấy label sentiment rồi hồi quy với giá cổ phiếu, đề tài sẽ bị nhìn như finance/data analysis hơn là NLP.

## Vì sao phù hợp với NLP

Bài toán headline tài chính có nhiều thực thể trong cùng câu và mỗi thực thể có thể nhận sentiment khác nhau. Ví dụ một headline có thể nói một mã tăng nhưng một mã khác giảm. Đây là lý do ABSA phù hợp hơn sentiment toàn văn. Mô hình FinABSA hiện tại dùng target masking; target được chọn trước và model sinh nhãn sentiment. Đây là một bài toán sequence-to-sequence classification/conditional generation.

Dữ liệu CafeF tạo ra domain shift rõ ràng so với SEntFiN: ngôn ngữ Việt, tên doanh nghiệp Việt, ticker, thuật ngữ chứng khoán, câu trích dẫn, số liệu, tiêu đề giật gân và dự báo tương lai. Kiểm tra model có chuyển giao sang domain mới hay không là một câu hỏi NLP hợp lệ.

## Phần nào là NLP cốt lõi

| Thành phần | Mức độ NLP | Cách trình bày |
|---|---:|---|
| Crawl/clean tiếng Việt | Trung bình | Data construction và reproducibility |
| Entity/ticker linking | Cao | NER/entity resolution trong domain tài chính |
| Target masking | Cao | Data contract của ABSA |
| Sentiment classification | Cao | Intrinsic task chính |
| Calibration/error analysis | Cao | Phân tích chất lượng mô hình |
| Ghép giá cổ phiếu | Downstream | Extrinsic validation |
| Event study/regression | Ngoài NLP thuần | Kiểm tra utility của output NLP |

## Thiết kế để không bị chê là “lệch sang tài chính”

Báo cáo nên dành khoảng 60–70% dung lượng cho data construction, target linking, mô hình, intrinsic metrics, domain shift, error analysis và ablation. Phần giá cổ phiếu chiếm khoảng 30–40%, được gọi là downstream/extrinsic validation.

Các thí nghiệm NLP bắt buộc nên gồm title-only so với context, target masking so với không masking, mô hình chính so với lexicon/TF-IDF baseline, strict entity linking so với broad linking, calibration, macro-F1 và lỗi theo nhóm ngôn ngữ.

## Điểm yếu cần nói thẳng

Mô hình hiện tại không dự đoán ticker. Nếu người viết báo cáo nói “model input là tin tức và output là ticker + sentiment” thì đó là mô tả sai. Correct description là: entity linker xác định target ticker trước; FinABSA nhận headline đã mask target và output sentiment cho target đó.

Dữ liệu CafeF không có nhãn sentiment tự nhiên. Nếu chỉ chạy model rồi coi prediction là ground truth, sẽ không thể đánh giá model. Cần một tập thủ công khoảng 300–500 article–ticker rows, có hai annotator và adjudication, cho intrinsic evaluation.

Một tháng khủng hoảng có thể có quá ít ngày giao dịch để kết luận thống kê mạnh. Vì vậy nên thu thập estimation window trước đó, chạy next-day return, bootstrap theo ngày và dùng tháng thứ hai/control regime làm robustness.

## Phiên bản đề tài nên đặt tên

> **Target-Aware Vietnamese Financial Sentiment Analysis on CafeF News with Downstream Stock-Market Validation**

Tên này nhấn mạnh đúng đóng góp NLP, còn stock-market validation là downstream evaluation.
