# FinABSA--CafeF: NLP-to-Finance Validation Pipeline

Đây là repository của bài tập lớn môn **Natural Language Processing**, xây dựng và kiểm định một pipeline từ tin tức tài chính tiếng Việt đến phân tích phản ứng giá cổ phiếu. Dự án kết hợp **target-masked Aspect-Based Sentiment Analysis (ABSA)** với dữ liệu bài báo CafeF và giá cổ phiếu Việt Nam lấy qua vnstock.

> **Kết luận quan trọng:** FinABSA trong pipeline này không tự nhận diện ticker. Entity linking được thực hiện trước; model chỉ dự đoán sentiment của target đã được mask. Các kết quả tài chính là association quan sát được, không phải bằng chứng rằng tin tức hoặc sentiment gây ra biến động giá.

## 1. Mục tiêu và câu hỏi nghiên cứu

Pipeline được thiết kế để trả lời ba câu hỏi. Thứ nhất, output của model có được nối đúng với từng article--ticker pair hay không. Thứ hai, sentiment dự đoán có liên hệ với abnormal return sau ngày công bố tin hay không. Thứ ba, mối liên hệ này có bền vững qua các năm, event windows, nhóm sentiment, phương pháp suy luận và độ trễ hay không.

Đóng góp chính của dự án nằm ở việc xây dựng một **data contract có khóa nối ổn định**, kiểm soát entity linking bằng confidence threshold, chuẩn hóa output sentiment, và đưa các prediction vào một bộ financial validation có thể tái lập.

## 2. Model contract

Một dòng input của FinABSA tương ứng với **một article--ticker pair**, không nhất thiết là một bài báo duy nhất. Với headline có nhiều doanh nghiệp, target được giữ lại dưới token `Target` còn các entity khác được thay bằng `Other`.

```text
Headline gốc:  HPG tăng mạnh, trong khi SSI điều chỉnh.
Input cho HPG: Target tăng mạnh, trong khi Other điều chỉnh.
Output:        positive / neutral / negative
```

Entity linking, ABSA và market analysis là ba bước độc lập:

| Bước | Đầu vào | Đầu ra |
|---|---|---|
| Entity linking | Tên doanh nghiệp trong bài | Ticker, phương pháp và confidence |
| Target masking + FinABSA | Headline đã mask target | Nhãn positive, neutral hoặc negative |
| Financial validation | Ticker--day và OHLCV | Return, abnormal return, CAR và regression features |

## 3. Kết quả dữ liệu đã chuẩn bị

Dữ liệu chính gồm cùng một tháng October trong bốn năm 2019--2022. Strict sample giữ các entity link có confidence tối thiểu 0.95 để ưu tiên precision khi nối prediction với dữ liệu giá.

| Kỳ | Bài CafeF | Article--ticker full | Strict pairs | Predictions | Strict pairs có giá |
|---|---:|---:|---:|---:|---:|
| 2019-10 | 1,040 | 583 | 154 | 154 | 141 |
| 2020-10 | 1,115 | 657 | 182 | 182 | 168 |
| 2021-10 | 1,506 | 991 | 297 | 297 | 281 |
| 2022-10 | 1,472 | 509 | 206 | 206 | 206 |
| **Tổng** | **5,133** | **2,740** | **839** | **839** | **796** |

Toàn bộ 839 strict predictions đã được kiểm tra theo `sample_id`: missing ID = 0, unexpected ID = 0, duplicate ID = 0 và unknown label = 0. Trong strict sample, nhãn gồm 759 neutral, 54 positive và 26 negative; class imbalance này được báo cáo như một giới hạn thống kê thay vì bị che giấu.

## 4. Cấu trúc repository

```text
.
├── README.md                         # Tài liệu chính của repository
├── requirements_cafef.txt            # Python dependencies cho pipeline CafeF
├── data/
│   ├── model_contract.json           # Quy ước input/output của model
│   ├── entity_aliases.csv            # Alias doanh nghiệp--ticker
│   └── cafef_oct2022/                # Run gốc October 2022 và output đã kiểm tra
├── 2019-10/analysis/figures/         # Hai figure dùng trong report/slide
├── 2020-10/analysis/figures/
├── 2021-10/analysis/figures/
├── 2022-10/analysis/figures/
├── main.tex                          # Report LaTeX đa năm hoàn chỉnh
├── slide.tex                         # Beamer deck tiếng Việt, tương thích pdfLaTeX
├── statistical_validation_multiyear.tex # Section kiểm định đa năm
├── validation_section.tex            # Section cũ October 2022, tham khảo
├── tests/test_pipeline.py            # Unit tests cho parser và join logic
├── docs/                             # Hướng dẫn dữ liệu, pipeline, thống kê và LaTeX
└── scripts ở root                    # Crawler, data preparation, inference và validation runners
```

Raw HTML, cache vnstock, toàn bộ dữ liệu crawl đa năm, model checkpoints, file ZIP/PDF sinh tự động và artifact tạm không nên version-control. Các file này được ignore bởi `.gitignore`; chúng có thể được tái tạo bằng các script tương ứng.

## 5. Cài đặt môi trường

Khuyến nghị dùng Python 3.10 trở lên và một virtual environment riêng.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements_cafef.txt
```

Các thành phần chính gồm pandas/numpy cho xử lý dữ liệu, requests/BeautifulSoup cho crawl, transformers cho inference, matplotlib/seaborn cho figure, và scipy/statsmodels/scikit-learn cho kiểm định và regression.

## 6. Workflow tái lập

### 6.1. Crawl và chuẩn bị CafeF đa năm

Lệnh sau tạo sitemap manifest cho October 2019--2022. Thêm `--fetch` khi muốn tải và parse các candidate article.

```bash
python3 prepare_cafef_multiyear.py \
  --years 2019,2020,2021,2022 \
  --month 10 \
  --out-root data/cafef_multiyear \
  --fetch
```

Crawler có checkpoint theo từng period. `--max-fetch-per-period` có thể dùng cho dry run nhỏ; khi chạy bộ dữ liệu nghiên cứu chính, để mặc định `0` để lấy toàn bộ candidate.

### 6.2. Tạo article--ticker model inputs

```bash
python3 prepare_multiyear_inputs.py \
  --data-root data/cafef_multiyear \
  --years 2019,2020,2021,2022 \
  --month 10 \
  --aliases data/entity_aliases.csv
```

Mỗi period sẽ có `model_inputs.csv` và `model_inputs_strict.csv`. Bộ strict là input chính của phân tích; bộ full dành cho sensitivity analysis khi inference đã hoàn tất.

### 6.3. Chạy model inference

Model không dự đoán ticker. Checkpoint FinABSA/FinSenKH phải nhận input đã có target mask và trả về một output cho mỗi `sample_id`.

Với một period:

```bash
python3 run_finabsa_on_cafef.py \
  --model ./finabsa-other-masked-final \
  --input data/cafef_multiyear/2022-10/model_inputs_strict.csv \
  --output data/cafef_multiyear/2022-10/model_predictions.csv
```

Nếu model riêng chỉ xuất raw label theo thứ tự dòng, hãy giữ input order và chuẩn hóa qua adapter:

```bash
python3 normalize_model_output.py \
  --raw your_model_output.csv \
  --inputs data/cafef_multiyear/2022-10/model_inputs_strict.csv \
  --out data/cafef_multiyear/2022-10/model_predictions.csv
```

Output nên giữ `sample_id`, `classification_output` và `raw_model_output`. Parser chấp nhận dạng đầy đủ hoặc viết tắt `positive/negative/neutral` và `pos/neg/neu`, sau đó canonicalize về ba nhãn chuẩn.

### 6.4. Ghép giá và chạy validation đa năm

Sau khi có predictions hợp lệ, có thể chạy runner đa năm:

```bash
python3 run_multiyear_pipeline.py \
  --repo . \
  --data-root data/cafef_multiyear \
  --predictions data/cafef_multiyear/model_predictions.csv
```

Runner kiểm tra alignment theo `sample_id`, tách prediction theo bốn period, chạy validation, event study, robustness và tổng hợp output vào `data/cafef_multiyear/analysis_multiyear/`.

Nếu cần tải market data từ đầu cho một period, dùng downloader tương ứng:

```bash
python3 download_market_data.py \
  --inputs data/cafef_multiyear/2022-10/model_inputs_strict.csv \
  --start 2022-05-01 \
  --end 2022-12-31
```

Market window dùng May--December của từng năm. Crawler/downloader có cache và checkpoint; không commit cache hoặc raw HTML lên GitHub.

## 7. Các kiểm định tài chính

Pipeline dùng phiên giao dịch đầu tiên sau ngày xuất bản làm event day vì dữ liệu giá là daily OHLCV, không có timestamp intraday đáng tin cậy. Abnormal return được tính từ market model với VNINDEX làm market proxy và estimation window trước October của từng năm.

| Nhóm kiểm định | Nội dung |
|---|---|
| Event study | CAR tại `[0,0]`, `[0,+1]` và `[0,+3]` |
| One-sample inference | t-test, sign-flip permutation 5.000 lần, bootstrap 95% CI 5.000 lần |
| Control | News-day so với eligible no-news-day |
| Sentiment contrasts | Welch, permutation và bootstrap giữa positive/neutral/negative |
| Panel | Ticker fixed effects + date fixed effects, HC3 và HC1 fallback khi cần |
| Robustness | Lag 0, 1, 2, 3, 5 và 10 phiên |

Các output chính nằm trong thư mục `data/cafef_multiyear/analysis_multiyear/` sau khi chạy pipeline. Bảng Excel 15 sheet và Markdown report đầy đủ là artifact sinh tự động, không phải input bắt buộc để chạy lại pipeline.

## 8. Tóm tắt kết quả thực tế

Kết quả đa năm không cho thấy một quan hệ ổn định giữa sentiment và abnormal return. CAR cùng ngày không khác 0 một cách có ý nghĩa ở bốn period. CAR `[0,+3]` âm và nominally significant tại 2020 với mean = -0.9261 và tại 2021 với mean = -1.0149, nhưng pattern này không lặp lại ở 2019 hoặc 2022.

Positive-minus-neutral có kết quả nominally significant tại 2021 với difference = 1.5693 và Welch p = 0.0267, nhưng nhóm positive nhỏ. Fixed-effects sentiment coefficient cũng chỉ nominally significant tại 2020 với coefficient = 2.5056 và p = 0.0018; dấu và độ lớn thay đổi giữa các năm. Vì vậy, các kết quả này phải được trình bày là **period-specific exploratory findings**, không phải bằng chứng causal hay chiến lược giao dịch.

## 9. Report và slide

`main.tex` là report LaTeX hoàn chỉnh, gồm phần giới thiệu/model/related work, section kiểm định đa năm, limitations, future work và conclusion. Tám figure mà report/slide sử dụng nằm trong bốn thư mục:

```text
2019-10/analysis/figures/
2020-10/analysis/figures/
2021-10/analysis/figures/
2022-10/analysis/figures/
```

Mỗi thư mục cần có:

```text
abnormal_return_by_label.png
sentiment_vs_abnormal_return.png
```

`slide.tex` là Beamer deck tiếng Việt gồm 12 slide. Deck đã được viết cho **pdfLaTeX**, phù hợp với Prism chỉ có một engine mặc định; không dùng `fontspec`, `polyglossia`, XeLaTeX hoặc LuaLaTeX.

Để compile report/slide trên Prism, upload toàn bộ file `.tex` cùng các thư mục figure, chọn file tương ứng làm main file và giữ nguyên đường dẫn tương đối. Xem thêm [docs/STATISTICAL_SECTION_USAGE.md](docs/STATISTICAL_SECTION_USAGE.md) và [docs/PRISM_SLIDE_README.md](docs/PRISM_SLIDE_README.md).

## 10. Kiểm tra phần mềm

Chạy unit tests trước khi chạy inference hoặc financial validation:

```bash
python3 -m unittest discover -s tests -v
```

Các test kiểm tra label parser, alignment theo `sample_id`, aggregate theo `ticker + published_date`, next-trading-day mapping, panel uniqueness và các hàm robustness. `check_slide.py` kiểm tra riêng cấu trúc 12 frame, engine dependency và tám đường dẫn figure của slide.

## 11. Giới hạn và hướng phát triển

Dữ liệu hiện tại chỉ lấy một tháng October cho mỗi năm, dùng một nguồn tin và daily prices. Entity linking vẫn có thể có false positive/negative; strict threshold đổi coverage lấy precision. Class imbalance làm giảm power của group comparisons, còn daily timestamp không cho phép xác định phản ứng intraday. Ngoài ra, nhiều period/window tests khiến nominal p-values cần được đọc thận trọng.

Hướng phát triển gồm xây dựng gold labels có adjudication, báo cáo F1/MCC/kappa, lưu logits để calibration, mở rộng nhiều tháng và nhiều nguồn, thêm placebo/factor models, multiple-testing correction, pre-registration và out-of-time forecasting.

## 12. Tài liệu trong `docs/`

| Tài liệu | Nội dung |
|---|---|
| [`README_CAFEF_PIPELINE.md`](docs/README_CAFEF_PIPELINE.md) | Workflow CafeF October 2022 và model contract chi tiết |
| [`MULTIYEAR_DATA_README.md`](docs/MULTIYEAR_DATA_README.md) | Đặc tả dữ liệu mở rộng 2019--2022 |
| [`STATISTICS_AND_TESTS.md`](docs/STATISTICS_AND_TESTS.md) | Thiết kế kiểm định và diễn giải thống kê |
| [`STATISTICAL_SECTION_USAGE.md`](docs/STATISTICAL_SECTION_USAGE.md) | Cách tích hợp section kiểm định vào report LaTeX |
| [`PRISM_SLIDE_README.md`](docs/PRISM_SLIDE_README.md) | Cách compile slide bằng engine pdfLaTeX của Prism |
| [`DATASET_CARD.md`](docs/DATASET_CARD.md) | Mô tả dữ liệu, nguồn và giới hạn |
| [`EXPERIMENTS.md`](docs/EXPERIMENTS.md) | Danh sách thí nghiệm và convention |
| [`PROJECT_EVALUATION.md`](docs/PROJECT_EVALUATION.md) | Đánh giá ý tưởng và pipeline của dự án |

## 13. Tài liệu tham khảo

1. [FinABSA trên Hugging Face](https://huggingface.co/amphora/FinABSA) — mô hình ABSA tài chính dựa trên target masking.
2. [SEntFiN dataset](https://asistdl.onlinelibrary.wiley.com/doi/10.1002/asi.24634) — dữ liệu sentiment tài chính được sử dụng trong hệ sinh thái FinABSA.
3. [FinABSA paper](https://arxiv.org/abs/2301.03136) — Son, Lee, Kang và Hahm, *Removing non-stationary knowledge from pre-trained language models for entity-level sentiment classification in finance*.
4. [Brown and Warner (1985)](https://www.jstor.org/stable/2327805) — event-study methodology.
5. [CafeF](https://cafef.vn/) — nguồn bài báo tài chính Việt Nam.
6. [vnstock](https://github.com/thinh-vu/vnstock) — thư viện truy xuất dữ liệu thị trường Việt Nam.

## 14. License và nhóm thực hiện

Repository phục vụ mục đích học thuật. Nhóm thực hiện gồm **Lê Khắc Quang Huy, Phùng Hữu Khoa, Nguyễn Nam Khánh và Lê Tuấn Duy**. Xem [LICENSE](LICENSE) để biết điều khoản của mã nguồn gốc và từng thành phần được sử dụng.
