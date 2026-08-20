# CafeF–FinABSA End-to-End Pipeline

## Kết luận quan trọng về model contract

Mô hình trong repository **không dự đoán ticker**. Ticker/entity phải được xác định trước bằng entity-linking. Mỗi input là một headline đã mask target, ví dụ:

```text
Raw title: Cổ phiếu ngân hàng tràn ngập trong sắc xanh: EIB tăng trần, khối ngoại gom mạnh CTG
Target ticker: CTG
Model input: Cổ phiếu ngân hàng tràn ngập trong sắc xanh: Other tăng trần, khối ngoại gom mạnh Target
```

Mô hình sinh output sentiment, thường chứa `POSITIVE`, `NEGATIVE` hoặc `NEUTRAL`. Vì vậy một dòng model input tương ứng với **một article–ticker pair**, không phải một bài báo duy nhất.

## Các bước chuẩn bị đã có

`prepare_cafef_data.py` đọc sitemap tháng 10/2022, lọc các bài có dấu hiệu tài chính, tải raw HTML và lưu `data/cafef_oct2022/articles.csv`. Crawler lưu định kỳ nên có thể chạy lại an toàn.

`prepare_model_inputs.py` chuyển `articles.csv` thành `data/cafef_oct2022/model_inputs.csv`. File này chứa `sample_id`, `article_id`, URL, timestamp, title gốc, target surface, ticker, entity method, confidence, masked headline và model contract.

Model chính nên chạy trên cột `input_text`, không chạy trực tiếp trên full body. Model gốc được huấn luyện trên headline/câu ngắn; full body là nhánh mở rộng để kiểm tra độ nhạy, không phải input chính.

## Chạy mô hình

Nếu dùng checkpoint Hugging Face/local checkpoint:

```bash
python3 run_finabsa_on_cafef.py \
  --model ./finabsa-other-masked-final \
  --input data/cafef_oct2022/model_inputs_strict.csv \
  --output data/cafef_oct2022/model_predictions.csv
```

Đường chạy chính dùng `model_inputs_strict.csv`; `model_inputs.csv` là bộ full để chạy robustness sau. Nếu bạn có script model riêng, yêu cầu tối thiểu là output phải giữ `sample_id` và một cột chứa raw output. Nếu output chỉ có một prediction trên mỗi dòng theo đúng thứ tự input, adapter vẫn hỗ trợ:

```bash
python3 normalize_model_output.py \
  --raw your_model_output.csv \
  --inputs data/cafef_oct2022/model_inputs.csv \
  --out data/cafef_oct2022/model_predictions.csv
```

Khuyến nghị giữ `sample_id`. Không nên chỉ giữ label vì cần raw output để phân tích lỗi và kiểm tra parser.

## Chạy kiểm tra và ghép dữ liệu

```bash
python3 validate_predictions.py
python3 download_market_data.py \
  --inputs data/cafef_oct2022/model_inputs_strict.csv \
  --start 2022-05-01 \
  --end 2022-12-31 \
  --sleep 8.0
python3 run_experiments.py
python3 run_robustness.py
python3 build_report.py
```

The market downloader uses a per-ticker cache under `data/cafef_oct2022/market_cache/` and writes checkpoints after each ticker. The default delay is intentionally conservative because guest vnstock access can be rate-limited. If a request fails, it is recorded in `market_download_errors.json`; rerunning the same command resumes from cached tickers.

Kết quả nằm trong `data/cafef_oct2022/analysis/`, gồm validation JSON, bảng sentiment cấp bài–mã–ngày, event observations, market model, event summary, regression coefficients, regression report, figures và `report_generated.md`.

## Thiết kế kiểm định được tự động hóa

Pipeline tính next-trading-day return, market return, expected return và abnormal return. Estimation window mặc định bắt đầu từ ngày đầu dữ liệu giá đến trước `2022-10-01`, còn crisis window là tháng 10/2022. Nếu đổi crisis month, truyền `--crisis-start` và `--crisis-end` cho `run_experiments.py`.

Các bảng chính gồm kết quả theo nhãn sentiment, daily sentiment–market aggregate, market model theo ticker và hồi quy với sentiment score, negative share, positive share, log article count, ticker fixed effect và date fixed effect.

## Các kiểm định nên bổ sung trong report

Kết quả tự động là bộ chính. Report nên bổ sung hoặc chạy thêm các nhánh sau nếu có thời gian: title-only so với body/context; strict entity mapping so với broad mapping; market-adjusted return so với market model; event window `[0,0]`, `[0,+1]`, `[0,+3]`; placebo dịch timestamp; sentiment permutation giữa ticker trong cùng ngày; sector/VN30 split; và intrinsic evaluation trên tập nhãn thủ công.

## Lưu ý học thuật

Đây là một đề tài NLP có phần downstream evaluation tài chính. Đóng góp NLP nằm ở entity linking, target-masked ABSA, xử lý tiếng Việt, calibration/error analysis và kiểm tra khả năng chuyển từ nhãn ngôn ngữ sang tín hiệu ngoài mẫu. Không được trình bày kết quả quan sát là bằng chứng bài báo gây ra biến động giá hoặc là chiến lược đầu tư.
