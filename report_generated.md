# CafeF–FinABSA Validation Report

> Báo cáo này được sinh tự động từ dữ liệu và kết quả trong repository. Các kết luận học thuật cần được kiểm tra lại sau khi model output hoàn tất.

## 1. Executive summary

Số dòng input: **208**. Số dòng prediction: **208**. Số nhãn chưa parse được: **0**.

Kết quả chính được thiết kế theo next-trading-day return và abnormal return dựa trên market model. Đây là kiểm định liên hệ ngoài mẫu, không phải bằng chứng nhân quả hay khuyến nghị đầu tư.

## 2. Prediction validation

```json
{
  "input_rows": 208,
  "prediction_rows": 208,
  "missing_predictions": 0,
  "unexpected_predictions": 0,
  "duplicate_input_ids": 0,
  "duplicate_prediction_ids": 0,
  "unknown_labels": 0,
  "label_counts": {
    "neutral": 180,
    "positive": 18,
    "negative": 10
  }
}
```

## 3. Event-study summary

| label    |   events |   mean_sentiment |   mean_return |   mean_abnormal_return |   median_abnormal_return |   mean_article_count |
|:---------|---------:|-----------------:|--------------:|-----------------------:|-------------------------:|---------------------:|
| negative |       10 |               -1 |       -1.4767 |                -0.3665 |                  -1.2829 |               1      |
| neutral  |      172 |                0 |       -0.8231 |                 0.1105 |                   0.1322 |               1.0058 |
| positive |       18 |                1 |        0.3498 |                 1.1637 |                   0.9237 |               1      |

## 4. Panel regression

| Unnamed: 0                                         |    coef |   std_err |   p_value |
|:---------------------------------------------------|--------:|----------:|----------:|
| Intercept                                          | -1.8291 |    5.4691 |    0.7381 |
| C(ticker)[T.AMD]                                   | -4.9171 |    3.4395 |    0.1528 |
| C(ticker)[T.BID]                                   |  1.9194 |    1.9354 |    0.3213 |
| C(ticker)[T.CEN]                                   |  1.6369 |    3.7176 |    0.6597 |
| C(ticker)[T.CTG]                                   |  1.2628 |    2.3821 |    0.596  |
| C(ticker)[T.DGC]                                   |  0.8485 |    2.8135 |    0.763  |
| C(ticker)[T.DIG]                                   | -0.8724 |    4.1289 |    0.8327 |
| C(ticker)[T.DNP]                                   | -0.9514 |    3.4516 |    0.7828 |
| C(ticker)[T.DXG]                                   | -7.5774 |    4.0035 |    0.0584 |
| C(ticker)[T.EIB]                                   |  1.4452 |    4.5491 |    0.7507 |
| C(ticker)[T.FTS]                                   | -0.1724 |    2.0299 |    0.9323 |
| C(ticker)[T.GAS]                                   | -1.0327 |    3.8559 |    0.7888 |
| C(ticker)[T.GEX]                                   |  0.3615 |    2.1823 |    0.8684 |
| C(ticker)[T.HAG]                                   | -2.4415 |    2.1962 |    0.2663 |
| C(ticker)[T.HBC]                                   | -0.8147 |    3.102  |    0.7928 |
| C(ticker)[T.HCM]                                   | -0.2331 |    2.9209 |    0.9364 |
| C(ticker)[T.HDB]                                   |  2.1276 |   11.7445 |    0.8562 |
| C(ticker)[T.HDC]                                   | -6.4797 |    2.1536 |    0.0026 |
| C(ticker)[T.HPG]                                   | -0.4182 |    1.7056 |    0.8063 |
| C(ticker)[T.HSG]                                   | -7.3402 |   10.5634 |    0.4871 |
| C(ticker)[T.ICT]                                   | -0.854  |    2.1616 |    0.6928 |
| C(ticker)[T.ITA]                                   | -1.8278 |    1.5351 |    0.2338 |
| C(ticker)[T.KBC]                                   | -2.5913 |    2.6672 |    0.3313 |
| C(ticker)[T.LHG]                                   | -3.556  |    4.6496 |    0.4444 |
| C(ticker)[T.LPB]                                   |  2.2946 |    2.3586 |    0.3306 |
| C(ticker)[T.MBS]                                   | -0.4024 |    1.9255 |    0.8345 |
| C(ticker)[T.MSH]                                   | -0.2933 |    2.0826 |    0.888  |
| C(ticker)[T.MWG]                                   | -3.4522 |    1.6534 |    0.0368 |
| C(ticker)[T.NKG]                                   | -7.254  |    3.431  |    0.0345 |
| C(ticker)[T.NVL]                                   | -0.5029 |    1.9152 |    0.7929 |
| C(ticker)[T.OCB]                                   | -0.5328 |    1.6627 |    0.7486 |
| C(ticker)[T.PNJ]                                   | -2.4299 |    2.2718 |    0.2848 |
| C(ticker)[T.POW]                                   | -0.087  |    1.8452 |    0.9624 |
| C(ticker)[T.PVD]                                   |  4.4128 |    1.8301 |    0.0159 |
| C(ticker)[T.REE]                                   | -0.344  |    1.8775 |    0.8546 |
| C(ticker)[T.SAB]                                   |  1.7553 |    2.4196 |    0.4682 |
| C(ticker)[T.SHB]                                   |  1.0687 |    1.5824 |    0.4994 |
| C(ticker)[T.SSI]                                   |  0.1418 |    1.7487 |    0.9354 |
| C(ticker)[T.STB]                                   |  1.7136 |    2.1608 |    0.4277 |
| C(ticker)[T.TCB]                                   | -0.1826 |    2.4646 |    0.941  |
| C(ticker)[T.TGG]                                   | -1.6901 |    3.1975 |    0.5971 |
| C(ticker)[T.TNI]                                   | -1.1091 |    1.7293 |    0.5213 |
| C(ticker)[T.VCB]                                   | -4.8236 |    2.9515 |    0.1022 |
| C(ticker)[T.VIC]                                   |  0.4502 |    2.7778 |    0.8712 |
| C(ticker)[T.VIX]                                   | -1.866  |    2.5217 |    0.4593 |
| C(ticker)[T.VND]                                   | -1.8544 |    1.698  |    0.2748 |
| C(ticker)[T.VNM]                                   | -2.5842 |    1.8985 |    0.1735 |
| C(ticker)[T.VPB]                                   |  1.227  |    4.0363 |    0.7611 |
| C(ticker)[T.VPS]                                   | -1.7226 |    2.188  |    0.4311 |
| C(ticker)[T.VRE]                                   |  0.911  |    2.5553 |    0.7215 |
| C(ticker)[T.VVS]                                   |  9.566  |    2.8734 |    0.0009 |
| C(target_date)[T.Timestamp('2022-10-04 00:00:00')] | -2.0415 |    2.5795 |    0.4287 |
| C(target_date)[T.Timestamp('2022-10-05 00:00:00')] |  0.9548 |    2.0132 |    0.6353 |
| C(target_date)[T.Timestamp('2022-10-06 00:00:00')] | -1.7025 |    2.0323 |    0.4022 |
| C(target_date)[T.Timestamp('2022-10-07 00:00:00')] |  0.0051 |    1.1307 |    0.9964 |
| C(target_date)[T.Timestamp('2022-10-10 00:00:00')] |  1.6246 |    1.0908 |    0.1364 |
| C(target_date)[T.Timestamp('2022-10-11 00:00:00')] | -3.9368 |    1.403  |    0.005  |
| C(target_date)[T.Timestamp('2022-10-12 00:00:00')] | -0.3466 |    1.8998 |    0.8552 |
| C(target_date)[T.Timestamp('2022-10-13 00:00:00')] |  0.4847 |    1.5072 |    0.7477 |
| C(target_date)[T.Timestamp('2022-10-14 00:00:00')] |  4.8858 |    2.6284 |    0.063  |
| C(target_date)[T.Timestamp('2022-10-17 00:00:00')] |  2.318  |    1.0089 |    0.0216 |
| C(target_date)[T.Timestamp('2022-10-18 00:00:00')] |  1.6051 |    3.0663 |    0.6007 |
| C(target_date)[T.Timestamp('2022-10-19 00:00:00')] | -1.5669 |    2.6281 |    0.551  |
| C(target_date)[T.Timestamp('2022-10-20 00:00:00')] | -2.7718 |    3.3084 |    0.4021 |
| C(target_date)[T.Timestamp('2022-10-21 00:00:00')] | -1.7783 |    1.1927 |    0.136  |
| C(target_date)[T.Timestamp('2022-10-24 00:00:00')] | -0.3876 |    1.2539 |    0.7572 |
| C(target_date)[T.Timestamp('2022-10-25 00:00:00')] |  0.2984 |    1.6036 |    0.8524 |
| C(target_date)[T.Timestamp('2022-10-26 00:00:00')] | -0.7031 |    1.1391 |    0.537  |
| C(target_date)[T.Timestamp('2022-10-27 00:00:00')] |  1.3949 |    1.4806 |    0.3461 |
| C(target_date)[T.Timestamp('2022-10-28 00:00:00')] | -0.3715 |    1.502  |    0.8047 |
| C(target_date)[T.Timestamp('2022-10-31 00:00:00')] | -0.4446 |    1.2466 |    0.7213 |
| sentiment_score                                    |  0.7092 |    0.8201 |    0.3871 |
| negative_share                                     |  0.6307 |    1.5473 |    0.6835 |
| positive_share                                     |  0.7672 |    1.0588 |    0.4687 |
| log_article_count                                  |  3.5604 |    7.6464 |    0.6415 |

## 5. Data coverage

Số ngày aggregate: **21**. Số ticker có market model: **54**.

| ticker   |   alpha |    beta |   n_estimation | model_status   |
|:---------|--------:|--------:|---------------:|:---------------|
| ACB      |  0.0288 |  0.9434 |            105 | market_model   |
| AMD      | -0.6832 |  1.4887 |            105 | market_model   |
| BID      |  0.1454 |  1.4112 |            105 | market_model   |
| BIG      | -0.3924 |  0.3397 |            105 | market_model   |
| CEN      | -0.2903 |  1.1666 |            105 | market_model   |
| CTG      |  0.0958 |  1.4386 |            105 | market_model   |
| DGC      | -0.0688 |  1.5952 |            105 | market_model   |
| DIG      | -0.2028 |  1.7626 |            105 | market_model   |
| DNP      |  0.0483 | -0.0055 |             99 | market_model   |
| DXG      | -0.2254 |  1.7109 |            105 | market_model   |
| EIB      |  0.1702 |  0.1483 |            105 | market_model   |
| FLC      | -0.7855 |  1.5124 |             89 | market_model   |
| FTS      |  0.1854 |  1.8623 |            105 | market_model   |
| GAS      |  0.2293 |  1.1169 |            105 | market_model   |
| GEX      | -0.049  |  1.7771 |            105 | market_model   |
| HAG      |  0.4616 |  1.1152 |            105 | market_model   |
| HBC      |  0.0116 |  1.5022 |            105 | market_model   |
| HCM      |  0.2349 |  1.681  |            105 | market_model   |
| HDB      |  0.1528 |  1.112  |            105 | market_model   |
| HDC      | -0.0407 |  1.6777 |            105 | market_model   |
| HPG      | -0.2097 |  1.0532 |            105 | market_model   |
| HSG      | -0.1268 |  1.4914 |            105 | market_model   |
| ICT      |  0.1137 |  0.4238 |            105 | market_model   |
| ITA      | -0.5754 |  1.5134 |            105 | market_model   |
| KBC      |  0.1289 |  1.3851 |            105 | market_model   |
| LHG      | -0.1524 |  1.5908 |            105 | market_model   |
| LPB      | -0.0106 |  1.4453 |            105 | market_model   |
| MBS      |  0.1213 |  2.1671 |            105 | market_model   |
| MSH      | -0.2744 |  1.2546 |            105 | market_model   |
| MWG      |  0.0632 |  1.2326 |            105 | market_model   |

## 6. Figures

![Sentiment versus abnormal return](data/cafef_oct2022/analysis/figures/sentiment_vs_abnormal_return.png)

![Abnormal return by label](data/cafef_oct2022/analysis/figures/abnormal_return_by_label.png)

## 7. Interpretation checklist

1. Kiểm tra temporal leakage: bài sau giờ đóng cửa không được gán cho cùng phiên.
2. Kiểm tra entity linking: kết quả chính nên dùng strict/high-confidence mapping.
3. So sánh với baseline và placebo; không chỉ nhìn p-value.
4. Báo cáo effect size và khoảng tin cậy.
5. Nếu intrinsic sentiment tốt nhưng extrinsic không có tín hiệu, đó vẫn là kết quả hợp lệ của môn NLP.

## 8. Limitations

CafeF là một nguồn tin, không đại diện toàn bộ thông tin thị trường. Timestamp, entity linking, coverage của ticker và cờ adjusted price cần được kiểm tra thủ công. Kết quả quan sát không chứng minh bài báo gây ra lợi suất.

## References

[1]: https://github.com/Khoaph1709/FinABSA-Valid FinABSA-Valid repository
[2]: https://cafef.vn/ CafeF
[3]: https://github.com/thinh-vu/vnstock vnstock
