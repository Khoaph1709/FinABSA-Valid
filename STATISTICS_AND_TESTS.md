# Cần thống kê gì và kiểm định như thế nào?

## 1. Tách hai câu hỏi khác nhau

Dự án có hai tầng đánh giá. Tầng thứ nhất là **intrinsic NLP evaluation**: mô hình có dự đoán đúng sentiment cho target entity trong headline CafeF hay không? Tầng thứ hai là **downstream market validation**: sentiment do mô hình sinh ra có liên hệ với lợi suất hoặc abnormal return sau thời điểm bài báo hay không?

Không được dùng kết quả giá cổ phiếu để thay thế nhãn sentiment. Một mô hình có macro-F1 thấp nhưng tình cờ có tương quan với giá chưa thể được kết luận là hiểu sentiment. Ngược lại, một mô hình có macro-F1 tốt nhưng không có tín hiệu giá vẫn là một kết quả NLP hợp lệ.

## 2. Thống kê mô tả dữ liệu

Bộ dữ liệu hiện tại có 1.472 bài CafeF tháng 10/2022, 512 article–ticker rows trong full mapping và 208 rows trong strict/high-confidence mapping. Bộ strict nên dùng cho kết quả chính; full mapping dùng cho robustness.

| Nhóm thống kê | Chỉ số cần báo cáo | Mục đích |
|---|---|---|
| Crawl | số URL sitemap, số URL tải thành công, số bài parse thành công, số lỗi, số bài trùng | Đánh giá độ phủ và khả năng tái lập |
| Thời gian | số bài theo ngày, số bài theo giờ, tỷ lệ bài có timestamp chính xác | Kiểm soát temporal leakage |
| Văn bản | độ dài title theo token/ký tự, số bài thiếu title/body, số bài duplicate | Kiểm tra domain và chất lượng input |
| Entity linking | số rows auto-high-confidence/manual-review, số ticker unique, top ticker, số ticker/article | Đánh giá lỗi target linking |
| Nhãn sau inference | tỷ lệ positive/neutral/negative, sentiment score trung bình, entropy nếu có xác suất | Kiểm tra class imbalance và prediction collapse |
| Giá | số ticker có giá, số phiên/ticker, first/last date, missing close/return | Kiểm tra khả năng ghép dữ liệu thị trường |

Nên có ít nhất ba hình: số bài theo ngày, phân bố độ dài headline và top 20 ticker theo số bài. Không nên chỉ đưa tổng số bài vì tổng số không cho biết dữ liệu có bị tập trung vào một vài ticker hay không.

## 3. Intrinsic NLP evaluation

### 3.1. Tạo nhãn chuẩn

Dùng `data/cafef_oct2022/annotation_sample.csv`. Vì strict dataset hiện có 208 rows, cách tốt nhất là gán nhãn thủ công toàn bộ 208 rows. Nếu muốn tập 300–500 rows, lấy mẫu bổ sung từ `model_inputs.csv` và đánh dấu rõ rằng đây là broad mapping.

Mỗi dòng cần có hai annotator độc lập và một người adjudicate khi bất đồng. Mỗi annotator điền sentiment vào `annotator_1_label` hoặc `annotator_2_label`, gồm đúng ba giá trị `positive`, `neutral`, `negative`. Người adjudicator điền `adjudicated_label`. Ticker đúng cũng cần được gán nhãn trong `adjudicated_ticker`, vì entity linking là một phần quan trọng của bài toán.

### 3.2. Agreement giữa người gán nhãn

Trước khi đánh giá model, tính agreement giữa hai annotator. Với hai annotator và ba lớp sentiment, dùng Cohen’s kappa; nếu có nhiều annotator hoặc nhiều vòng gán nhãn, dùng Krippendorff’s alpha. Báo cáo cả raw agreement và kappa, vì kappa có thể thấp khi phân bố lớp quá lệch.

Đối với ticker, báo cáo exact-match accuracy và confusion/error rate của entity linker. Nếu ticker sai, sentiment đúng về mặt ngôn ngữ nhưng sai target vẫn phải được xem là lỗi end-to-end.

### 3.3. Metrics của mô hình

Bảng chính nên có accuracy, balanced accuracy, macro-F1, weighted-F1, Matthews correlation coefficient, precision/recall/F1 riêng cho từng lớp và confusion matrix.

Macro-F1 là metric chính vì nó không để lớp chiếm đa số lấn át hai lớp còn lại. Accuracy chỉ là metric phụ. MCC hữu ích khi dữ liệu mất cân bằng và khi cần một thước đo đơn tổng quát hơn.

| Metric | Dùng để trả lời |
|---|---|
| Accuracy | Tỷ lệ dòng dự đoán đúng tổng thể |
| Balanced accuracy | Hiệu quả trung bình trên các lớp |
| Macro-F1 | Model có xử lý đều positive/neutral/negative không |
| Per-class recall | Model có bỏ sót lớp negative hoặc positive không |
| MCC | Chất lượng tổng quát khi class imbalance |
| Confusion matrix | Model nhầm neutral thành polarity hay đảo ngược polarity |

Tính confidence interval 95% bằng bootstrap theo **article**, không bootstrap độc lập từng article–ticker row, vì cùng một bài có thể tạo nhiều rows. Có thể lấy 1.000 bootstrap samples và báo cáo percentile interval cho macro-F1.

### 3.4. Baselines và ablation

Cần tối thiểu ba baseline: majority-class baseline, lexicon/rule baseline và TF-IDF + Logistic Regression hoặc Linear SVM. Nếu mô hình FinABSA không vượt qua majority baseline, không được diễn giải kết quả downstream như một thành công.

Các ablation quan trọng gồm target masking so với không masking, strict mapping so với full mapping, headline-only so với context/body nếu có thể tạo được input tương thích, và model chính so với baseline. Báo cáo delta macro-F1, không chỉ điểm tuyệt đối.

### 3.5. Error analysis

Chọn tối thiểu 20–30 lỗi và chia theo nhóm: nhiều ticker trong một headline, phủ định, dự báo tương lai, câu trích dẫn, số liệu tăng/giảm, sentiment cho ngành nhưng không cho doanh nghiệp, ticker bị nhận nhầm, neutral bị gán positive/negative và polarity reversal.

Mỗi lỗi cần có title gốc, target, input sau mask, output model, nhãn adjudicated và nguyên nhân lỗi. Đây là phần thể hiện rõ nhất đóng góp NLP của dự án.

## 4. Chuẩn hóa sentiment để ghép thị trường

Nếu model trả về xác suất, dùng sentiment score:

```text
sentiment_score = P(positive) − P(negative)
```

Nếu chỉ có label, quy đổi `positive=+1`, `neutral=0`, `negative=-1`. Theo từng ticker và ngày, tính mean score, median score, positive share, negative share, neutral share, article count và prediction entropy nếu có xác suất.

Nên giữ cả cấp article–ticker và cấp ticker–day. Cấp article–ticker dùng cho event study; cấp ticker–day dùng cho panel regression.

## 5. Gắn timestamp và lợi suất

Thời điểm công bố phải được gắn vào phiên giao dịch đầu tiên **sau khi bài xuất hiện**. Nếu bài đăng trước giờ đóng cửa, có thể định nghĩa phiên kế tiếp là outcome chính để tránh phản ứng cùng phiên. Nếu chỉ có ngày mà không có giờ, đánh dấu timestamp precision thấp và không dùng cho cửa sổ intraday.

Lợi suất log của ticker i tại ngày t là:

```text
r_i,t = 100 × log(Close_i,t / Close_i,t−1)
```

Abnormal return theo market-adjusted model là:

```text
AR_i,t = r_i,t − r_market,t
```

Nếu đủ dữ liệu estimation, dùng market model:

```text
r_i,t = alpha_i + beta_i × r_market,t + epsilon_i,t
AR_i,t = r_i,t − (alpha_hat_i + beta_hat_i × r_market,t)
```

Bộ giá hiện có bao phủ khoảng tháng 5–12/2022, đủ để dùng một estimation window 60 phiên trước event. Với các ticker mới niêm yết hoặc VVS có ít phiên, phải báo cáo riêng và không coi chúng có cùng độ tin cậy với ticker có đầy đủ lịch sử.

## 6. Event study and news-price reaction

### 6.1. Câu hỏi và giả thuyết

Câu hỏi chính của downstream validation là liệu các ticker có xuất hiện trong news event có phản ứng bất thường so với ngày không có event hay không. Câu hỏi thứ hai là phản ứng có khác nhau theo sentiment hay không.

Các giả thuyết chính là:

```text
H0a: Mean CAR trong các event window bằng 0.
H1a: Mean CAR trong ít nhất một event window khác 0.

H0b: Mean AR ở news-day không khác mean AR ở eligible no-news-day.
H1b: Hai nhóm ngày có mean AR khác nhau.

H0c: Mean CAR của các nhóm sentiment không khác nhau.
H1c: Ít nhất một nhóm sentiment có mean CAR khác nhóm khác.
```

Kết quả chính nên dùng cửa sổ `[0,+1]`, tức ngày công bố hoặc phiên giao dịch kế tiếp đến một phiên sau đó. Các cửa sổ tự động gồm `[0,0]`, `[0,+1]` và `[0,+3]`. Kết quả được lưu tại `tables/car_tests.csv`; kiểm định một mẫu, sign-flip permutation và bootstrap 95% CI được tính cho toàn bộ event unit và từng nhóm sentiment. Kiểm định news-day so với eligible no-news-day được lưu tại `tables/news_day_control_tests.csv`.

### 6.2. Chỉ số phải báo cáo

| Chỉ số | Ý nghĩa |
|---|---|
| N events | Số article–ticker event hợp lệ |
| Mean return | Lợi suất trung bình theo sentiment |
| Median return | Giảm ảnh hưởng outlier |
| Mean AR | Lợi suất bất thường trung bình |
| AAR | Average abnormal return theo event day |
| CAR | Cộng AR trong một cửa sổ |
| CAAR | Trung bình CAR của một nhóm |
| 95% CI | Khoảng bất định của effect |
| p-value | Bằng chứng chống lại H0, chỉ là một phần của kết luận |

### 6.3. Kiểm định nhóm

Dùng Welch t-test để so sánh mean AR giữa hai nhóm khi muốn kiểm định trung bình mà không giả định variance bằng nhau. Dùng Mann–Whitney U như kiểm định phi tham số phụ trợ. Với ba nhóm, dùng Welch ANOVA hoặc permutation test.

Tuy nhiên, kiểm định chính nên là **block bootstrap hoặc permutation theo ngày**, vì nhiều bài xuất hiện trong cùng ngày và cùng chịu một cú sốc thị trường. Không nên coi tất cả article–ticker rows là độc lập hoàn toàn.

## 7. Panel regression

Tạo panel ticker–date bằng cách aggregate sentiment theo ngày. Mô hình đề xuất:

```text
AR_i,t+1 = alpha_i + delta_t
         + beta1 × sentiment_score_i,t
         + beta2 × negative_share_i,t
         + beta3 × positive_share_i,t
         + gamma × log(1 + article_count_i,t)
         + epsilon_i,t
```

Trong đó `alpha_i` là ticker fixed effect và `delta_t` là date fixed effect. Có thể thêm pre-event return, volatility, market return và sector nếu dữ liệu point-in-time có sẵn.

Giả thuyết:

```text
H0: beta1 = 0
H1: beta1 khác 0
```

Báo cáo coefficient, standard error, 95% CI, p-value, N observations, số ticker, số ngày và R-squared. Dùng HC3 hoặc standard error cluster theo date/ticker khi implementation hỗ trợ.

Không viết “sentiment gây ra lợi suất”. Cách diễn giải đúng là: “sentiment có tương quan có điều kiện với abnormal return trong thiết kế này”.

## 8. Lag, placebo và permutation robustness

### 8.1. Lag test

Tính outcome tại lag 0, 1, 2, 3, 5 và 10 phiên. Nếu sentiment thực sự gắn với phản ứng thông tin, tín hiệu thường được kỳ vọng mạnh hơn ở lag ngắn và suy yếu dần. Nếu tín hiệu mạnh nhất ở lag bất thường hoặc trước thời điểm bài xuất hiện, cần nghi ngờ leakage hoặc misalignment.

### 8.2. Time-shift placebo

Dịch event sang +5 và +10 phiên rồi chạy lại. Nếu placebo mạnh tương đương kết quả chính, sentiment có thể chỉ đang phản ánh đặc tính cố hữu của ticker hoặc một xu hướng kéo dài chứ không phải phản ứng với bài báo.

### 8.3. Permutation test

Trong từng ngày, xáo trộn sentiment giữa các ticker 1.000 lần. Mỗi lần tính chênh lệch mean AR giữa nhóm negative và positive. So sánh statistic quan sát với phân bố null. Đây là kiểm định phù hợp hơn random shuffle toàn bộ vì giữ được cấu trúc ngày và article volume.

### 8.4. Multiple testing

Chỉ định trước một primary outcome: next-tradable-session AR, và một primary window: `[0,+1]`. Các lag, sector, topic và cửa sổ khác là exploratory. Nếu kiểm định nhiều giả thuyết, dùng Benjamini–Hochberg hoặc báo cáo rõ số lần kiểm định để tránh chọn riêng kết quả có lợi.

## 9. Bộ bảng và hình cần đưa vào report

| Bảng | Nội dung |
|---|---|
| Table 1 | Dataset statistics, số bài/ngày, độ dài title, ticker coverage |
| Table 2 | Annotator agreement và entity-linking accuracy |
| Table 3 | Intrinsic metrics: macro-F1, balanced accuracy, MCC, per-class F1 |
| Table 4 | Confusion matrix và error categories |
| Table 5 | CAR theo cửa sổ, kiểm định CAR khác 0 và bootstrap CI |
| Table 6 | News-day so với eligible no-news-day |
| Table 7 | Sentiment-group tests: Welch, permutation và bootstrap |
| Table 8 | Panel regression coefficients và robust SE |
| Table 9 | Robustness theo lag, strict/full, placebo, permutation |

| Hình | Nội dung |
|---|---|
| Figure 1 | Số bài CafeF theo ngày |
| Figure 2 | Phân bố positive/neutral/negative |
| Figure 3 | VNINDEX và các mốc bài báo/event |
| Figure 4 | Mean AR theo sentiment |
| Figure 5 | CAR theo event window với bootstrap CI |
| Figure 6 | News-day so với no-news-day |
| Figure 7 | Sentiment-group contrasts |
| Figure 8 | Kết quả lag và placebo |

## 10. Quy trình chạy sau khi có model output

```bash
# 1. Chạy model trên đường chạy chính
python3 run_finabsa_on_cafef.py \
  --model ./YOUR_CHECKPOINT \
  --input data/cafef_oct2022/model_inputs_strict.csv \
  --output data/cafef_oct2022/model_predictions.csv

# 2. Nếu output do script riêng sinh ra
python3 normalize_model_output.py \
  --raw your_model_output.csv \
  --inputs data/cafef_oct2022/model_inputs_strict.csv \
  --out data/cafef_oct2022/model_predictions.csv

# 3. Kiểm tra output và tạo sentiment aggregate
python3 validate_predictions.py

# 4. Tạo annotation sample, điền nhãn adjudicated rồi đánh giá intrinsic
python3 make_annotation_sample.py --n 208
python3 evaluate_intrinsic.py

# 5. Chạy downstream experiments và sinh unified report
python3 run_pipeline.py
# Kết quả gồm report_generated.md và report_generated.pdf
```

Nếu chạy `run_pipeline.py` trước khi có model output, pipeline phải dừng với thông báo thiếu output. Đây là hành vi đúng vì không được tự tạo prediction giả.

## 11. Cách kết luận

Có bốn tình huống chính. Nếu intrinsic tốt và downstream ổn định qua lag/placebo, có bằng chứng rằng model vừa phân loại tốt vừa có utility trong thiết kế thị trường. Nếu intrinsic tốt nhưng downstream không có tín hiệu, đó vẫn là kết quả NLP tốt; sentiment không nhất thiết dự báo được giá.

Nếu intrinsic thấp nhưng downstream có tín hiệu, không được kết luận model hiểu sentiment; tín hiệu có thể đến từ entity linking, topic hoặc ticker frequency. Nếu cả intrinsic và downstream đều yếu, cần tập trung vào domain shift, nhãn, target linking, timestamp và chất lượng dữ liệu.

Kết luận cuối cùng nên sử dụng effect size và confidence interval cùng p-value. Không nên chỉ viết “p < 0.05 nên mô hình tốt”, và không nên biến association thành tuyên bố causal hay khuyến nghị đầu tư.

## References

[1]: https://doi.org/10.2307/2729691 MacKinlay, A. C. (1997). Event Studies in Economics and Finance.

[2]: https://scikit-learn.org/stable/modules/model_evaluation.html Scikit-learn model evaluation documentation.

[3]: https://www.statsmodels.org/stable/stats.html Statsmodels statistical tests and models documentation.
