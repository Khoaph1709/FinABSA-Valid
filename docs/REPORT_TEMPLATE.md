# FinABSA–CafeF: Kiểm định mô hình sentiment tài chính tiếng Việt

## Abstract

Báo cáo đánh giá mô hình phân loại sentiment theo target entity trên headline tài chính tiếng Việt, sử dụng dữ liệu bài báo CafeF trong tháng 10/2022 và dữ liệu OHLCV từ vnstock. Thiết kế gồm intrinsic validation trên mẫu gán nhãn thủ công và extrinsic validation bằng next-trading-day return, abnormal return, event study, panel regression, placebo và lag robustness.

## 1. Introduction

Trình bày bài toán NLP: một headline có thể chứa nhiều doanh nghiệp với sentiment khác nhau. Mục tiêu của ABSA là phân loại sentiment cho đúng target entity, thay vì gán một nhãn duy nhất cho cả headline.

Nêu rõ câu hỏi chính: mô hình có giữ được chất lượng khi chuyển từ benchmark sang headline CafeF tiếng Việt hay không, và đầu ra sentiment có giá trị thông tin bổ sung đối với biến động thị trường hay không?

Đóng góp cần viết theo hướng NLP: data contract target-masked cho tiếng Việt, entity linking mã cổ phiếu, đánh giá lỗi theo ngữ cảnh tài chính và downstream validation ngoài mẫu. Không tuyên bố đây là hệ thống dự báo đầu tư hoàn chỉnh.

## 2. Related work

Thảo luận financial sentiment, ABSA, target masking, financial event study và sentiment–market reaction. Phân biệt intrinsic metrics với extrinsic utility. Trích dẫn repository/model và các nghiên cứu market reaction phù hợp.

## 3. Dataset

### 3.1. CafeF crawl

Báo cáo khoảng thời gian, sitemap, số URL, số bài tải thành công, số bài parse được, số bài lọc tài chính, số bài có body và số bài có ticker candidate. Ghi timestamp, URL, title, summary, body, raw hash và quy tắc chống duplicate.

### 3.2. Model-ready transformation

Mỗi dòng là một article–ticker pair. Trình bày ví dụ:

```text
Cổ phiếu ngân hàng tràn ngập trong sắc xanh: EIB tăng trần, khối ngoại gom mạnh CTG
→ Cổ phiếu ngân hàng tràn ngập trong sắc xanh: Other tăng trần, khối ngoại gom mạnh Target
```

Giải thích model không dự đoán ticker. Ticker được entity linker xác định trước; model chỉ phân loại sentiment cho target đã mask.

### 3.3. Market data

Báo cáo mã, khoảng ngày, provider vnstock, adjusted flag, missingness, số ticker lấy được và VN-Index series. Nêu rõ estimation window phải nằm trước crisis window.

## 4. Methodology

### 4.1. Intrinsic evaluation

Dùng mẫu annotation có hai annotator và một adjudicator. Báo cáo Cohen’s kappa/agreement cho target và sentiment. Chỉ tính metrics trên dòng có nhãn adjudicated hợp lệ.

Bảng cần điền: accuracy, balanced accuracy, macro-F1, weighted-F1, MCC, per-class precision/recall/F1, confusion matrix và error examples.

### 4.2. Sentiment aggregation

`sentiment_score = p_positive − p_negative`; nếu chỉ có label thì positive=1, neutral=0, negative=-1. Aggregate theo article–ticker–day bằng mean/median, negative share, positive share, article count và entropy nếu có xác suất.

### 4.3. Time alignment

Dùng next tradable session làm outcome chính. Bài sau giờ đóng cửa không được gán cho cùng phiên. Bài chỉ có ngày không có giờ gắn cờ temporal precision thấp.

### 4.4. Event study

Định nghĩa return, market model, abnormal return, CAR và cửa sổ `[0,0]`, `[0,+1]`, `[0,+3]`. Estimation window 60–120 phiên trước tháng khủng hoảng; báo cáo số quan sát estimation cho từng ticker.

### 4.5. Panel regression

```text
AR_i,t+1 = α_i + δ_t + β1 sentiment_i,t
           + β2 negative_share_i,t
           + β3 positive_share_i,t
           + γ log_article_count_i,t + ε_i,t
```

Diễn giải β1 là association conditional on fixed effects, không phải causal effect.

### 4.6. Out-of-time evaluation

Chia train/validation/test theo thời gian, không random split. So sánh với majority, lagged return, VN-Index return, volatility và title-only baseline.

## 5. Results

### 5.1. Data statistics

Chèn bảng `data_coverage.csv` và hình số bài/ngày.

### 5.2. Intrinsic metrics

Chèn `analysis/intrinsic/metrics.csv`, classification report và confusion matrix. Mô tả lớp neutral, lỗi phủ định, dự báo tương lai, nhiều target, tên doanh nghiệp và câu trích dẫn.

### 5.3. Event study

Chèn `event_summary_by_label.csv`. So sánh dấu và magnitude của abnormal return giữa negative/neutral/positive. Báo cáo confidence interval nếu đã bootstrap.

### 5.4. Regression

Chèn bảng coefficient/p-value/standard error. Tập trung vào sentiment_score, negative_share, positive_share. Kiểm tra dấu và độ ổn định, không chỉ p-value.

### 5.5. Robustness

Chèn `robustness_summary.csv`, gồm lag 0/1/2/3/5/10, strict/broad mapping, market-adjusted/market-model, cửa sổ khác nhau, placebo và sector split.

## 6. Error analysis

Chọn tối thiểu 20 lỗi theo nhóm: neutral bị gán positive/negative, polarity reversal, nhiều công ty trong một title, phủ định, mỉa mai, trích dẫn, dự báo tương lai, từ chuyên ngành và ticker viết không chuẩn.

Mỗi lỗi cần có title gốc, target, input mask, prediction, nhãn thủ công, nguyên nhân và hướng khắc phục.

## 7. Discussion

Nếu intrinsic tốt và extrinsic có tín hiệu: mô hình có tính chuyển giao và giá trị thông tin bổ sung trong thiết kế đã thử nghiệm. Nếu intrinsic tốt nhưng extrinsic không có tín hiệu: sentiment đã có thể bị thị trường phản ánh, timestamp/coverage chưa đủ hoặc nhiệm vụ downstream khác với classification.

Nếu intrinsic thấp: không được che giấu bằng kết quả hồi quy. Tập trung vào domain shift giữa SEntFiN và CafeF, chênh lệch ngôn ngữ, độ dài headline, entity linking và calibration.

## 8. Limitations and ethics

CafeF không đại diện toàn bộ thị trường. Sitemap/crawl có thể thiếu archive hoặc bài bị cập nhật. Ticker linking tự động có thể nhầm. Dữ liệu giá có thể khác provider/adjustment. Tháng khủng hoảng ngắn làm power thấp. Không dùng kết quả như tư vấn đầu tư.

## 9. Conclusion

Kết luận phải trả lời riêng RQ1–RQ6. Nêu mô hình nào tốt nhất trên intrinsic, tín hiệu nào mạnh nhất trên extrinsic, kết quả có bền qua placebo/lag hay không và phần nào cần nghiên cứu tiếp.

## Phụ lục

Đưa schema, command chạy pipeline, hyperparameters, danh sách từ khóa, mapping rules, bảng lỗi crawler, model contract và hash/version của dữ liệu.
