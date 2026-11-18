# Báo cáo Day 09 — Luu Nhat Nam, 2A202603243

## 1. Kết luận trước

**Hold.** Pipeline quét 224 ảnh, loại 22 ảnh và xuất 202 ảnh vào `export/clean_v1/` dưới dạng bản nháp Hold. Sau người duyệt **mô phỏng** 80/80 ảnh theo ngân sách, không còn lỗi bắt buộc nhưng còn 38/202 ảnh có cảnh báo chưa duyệt (18,81%), vượt ngưỡng 10%. Nguồn: `reports/01_intake.txt`, `reports/08_summary.json` và manifest của dataset xuất.

## 2. Lỗi và phân việc

Thống kê từ `reports/02_error_list_v1.csv`, **trước khi sửa**. Mẫu số: 224 ảnh ở cửa vào, 202 ảnh sau cửa vào; một ảnh có thể có nhiều mã lỗi. “Lượt” là số bản ghi phát hiện, không mặc nhiên là lỗi đã xác nhận bằng mắt người.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| BAD_SIZE | 3/224 ảnh | Máy | Loại ảnh dưới kích thước quy định |
| CORRUPT_IMAGE | 2/224 ảnh | Máy | Không đọc được ảnh |
| DUP_IMAGE_EXACT | 8/224 ảnh | Máy | Loại bản trùng từng byte |
| DUP_IMAGE_NEAR | 4/224 ảnh | Máy | Loại theo pHash đã hiệu chỉnh |
| LEAK_TEST | 5/224 ảnh | Máy | Loại ảnh trùng kho test/val |
| BAD_CLASS_NAME | 2 lượt cấp dataset | Máy | Chuẩn hóa tên lớp |
| BAD_CLASS_ID | 6 dòng trên 6/202 ảnh | Máy | Xóa dòng có ID ngoài danh sách |
| BAD_FORMAT | 3 dòng trên 3/202 ảnh | Máy | Xóa dòng không đọc được |
| BOX_ZERO | 4 dòng trên 4/202 ảnh | Máy | Xóa box có kích thước không dương |
| DUP_BOX | 7 dòng trên 7/202 ảnh | Máy | Xóa box trùng cùng lớp |
| BOX_OUT_OF_IMAGE | 8 dòng trên 8/202 ảnh | Máy | Cắt box về biên ảnh |
| MISSING_LABEL_FILE | 6/202 ảnh | Người | Máy không tự tạo nhãn thiếu |
| EMPTY_LABEL | 12/202 ảnh | Người | Xác minh ảnh nền hay thiếu nhãn |
| BOX_TINY | 6 lượt trên 4/202 ảnh | Người | Xác minh đối tượng nhỏ |
| BOX_HUGE | 3 lượt trên 3/202 ảnh | Người | Xác minh độ hợp lý của box |
| CLASS_RARE | 4 lượt cấp dataset | Người | Đánh giá phân bố lớp |
| POSSIBLE_FALSE_POS | 25 lượt trên 24/202 ảnh | Người | Xác minh nhãn có thực sự thừa |
| POSSIBLE_LOOSE_BOX | 28 lượt trên 24/202 ảnh | Người | Xác minh độ khít của box |
| POSSIBLE_MISSING | 53 lượt trên 52/202 ảnh | Người | Xác minh đối tượng còn thiếu |
| POSSIBLE_WRONG_CLASS | 18 lượt trên 18/202 ảnh | Người | Xác định lớp theo nội dung ảnh |

`03_fixes.csv` ghi 20 lần xóa dòng, 8 lần cắt box, 1 lần chuẩn hóa tên lớp và 6 yêu cầu chuyển người gán; 6 yêu cầu này không phải nhãn do máy tạo. 22 ảnh bị loại đầu vào được ghi riêng trong `01_intake`.

Hàng đợi sau tự sửa có 125 ảnh. `img_0020` đứng đầu với điểm 11,524 do kết hợp FIXED_DROP_LINE, POSSIBLE_MISSING và POSSIBLE_WRONG_CLASS; ảnh thiếu nhãn có NEEDS_LABEL được ưu tiên cao. Đối chiếu `04_error_list_v2.csv` với `06_review_log.csv`: 94/123 cảnh báo ngữ nghĩa nằm trên 74/103 ảnh có cảnh báo ngữ nghĩa được mô phỏng duyệt. Đây là phạm vi được duyệt, không phải 94 lỗi đã được xác nhận hoặc sửa hết.

## 3. Calibration (2 ngưỡng)

Nguồn: hai sweep trong `calibration/calibration_report.md` trên 39 ảnh calib.

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---:|---:|---|---|
| duplicates.phash_dist | 2 | 10 | Gần trùng: 1,00 / 0,50 → 1,00 / 0,67 | Bắt 4/6 thay vì 3/6 ca calib; tránh nhận nhầm quan sát được ở ngưỡng 16 |
| second_opinion.conf | 0,25 | 0,6 | Sai lớp: 0,56 / 0,83 → 0,62 / 0,83; thiếu nhãn: 0,50 / 1,00 → 0,57 / 1,00 | Giảm báo động giả ở hai loại này nhưng recall box lỏng giảm 0,40 → 0,20 |

**Điểm đánh lừa:** ngưỡng pHash 16 đạt precision 1,00, recall 0,83 trên calib nhưng kiểm tra ảnh raw có AI hỗ trợ phát hiện hai cặp nhận nhầm: `img_0011` (tennis) / `img_0008` (trượt tuyết), và `img_0177` (lướt sóng) / `img_0113` (ngồi bàn ăn). Chọn 10 giữ được cặp gần trùng `img_0186` / `img_0061` (khoảng cách 10), đổi lại bỏ sót cặp cùng ảnh `img_0084` / `img_0074` (khoảng cách 16). Calib nhỏ không bảo đảm precision tương tự trên raw; không dùng nhãn test để chọn ngưỡng.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

Thử nghiệm đã chạy:

```powershell
python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb
$LASTEXITCODE
```

Kết quả: **Rework**, mã thoát **20**, còn **6 lỗi MISSING_LABEL_FILE trên 6/202 ảnh**, 112/202 ảnh có cảnh báo chưa duyệt (55,45%), `reviewed: 0`, `exported: null`. Gate chặn lỗi bắt buộc và không xuất dataset.

Một lần chạy kiểm chứng độc lập dùng thêm `--work work/report_gate_no_review --reports submission/evidence/gate_no_review --export-dir work/report_gate_export` cho cùng verdict, số lỗi và mã thoát; thư mục `work/report_gate_export/clean_v1` không tồn tại. Bằng chứng được giữ tại `evidence/gate_no_review/08_summary.json`, `exit_code.txt`, `run.log`; không ghi đè lần chạy chính Hold.

Hai điểm mù có bằng chứng: (1) ở conf 0,6, checker chỉ bắt 1/5 ca box lỏng trong calib, bỏ sót 4/5; model không thay thế được đánh giá độ khít. (2) pHash 10 bỏ sót cặp ảnh biến đổi `img_0084` / `img_0074`, trong khi nâng lên 16 lại nhận nhầm các cảnh khác nhau. Các cảnh báo AI vẫn cần người xác minh; kết quả mô phỏng không chứng minh học viên đã tự duyệt toàn bộ ảnh.

## 5. Train: raw vs clean (tùy chọn)

Đã train trên **Tesla T4 / Google Colab**, Ultralytics 8.4.214, cùng model khởi tạo `yolo26n.pt`, **20 epoch**, batch 16, imgsz 640, hai seed **0 và 1** cho mỗi biến thể. Cùng gold_val 40 ảnh và test 100 ảnh; chỉ thay bộ train raw/clean. Bốn JSON gốc trong `results/` có cùng config SHA1 với bài hiện tại; hai lượt clean khớp SHA1 manifest `clean_v1` (202 ảnh, quyết định **Hold**).

Bảng dưới do `scripts/summarize_results.py` sinh từ bốn lượt train, trích `results/comparison.md`; độ lệch là độ lệch chuẩn mẫu giữa hai seed:

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 202 | 2 | 0.701 ± 0.025 | 0.487 ± 0.008 | 0.759 ± 0.003 | 0.625 ± 0.019 |

**So với nhiễu seed:** mAP50 raw trung bình 0,72575, SD 0,00021; clean trung bình 0,70060, SD 0,02461. Chênh clean − raw = **−0,02515** (khoảng −2,52 điểm phần trăm), xấp xỉ một SD của clean; số ±0,000 trong bảng chỉ do làm tròn. mAP50-95 trung bình cũng thấp hơn: 0,4874 so với 0,5117, chênh −0,0243. Hai lượt clean đều có mAP50 thấp hơn raw cùng seed, nhưng chỉ hai seed và test 100 ảnh chưa đủ để khẳng định xu hướng ổn định hoặc xác định nguyên nhân. **Thí nghiệm này chưa cho thấy clean tốt hơn raw.**

**Giải thích cần kiểm chứng và bước tiếp theo:**

- **Raw có thể được lợi từ trùng/rò rỉ:** intake gắn LEAK_TEST cho 5/224 ảnh nguồn; các ảnh này vẫn có trong biến thể raw. Đối chiếu cặp trùng từ `01_intake`, rồi làm thí nghiệm phụ loại rò rỉ với cùng cấu hình/seed để đo ảnh hưởng; chưa quy chênh lệch mAP hiện tại hoàn toàn cho rò rỉ.
- **Clean vẫn chưa sạch hoàn toàn:** còn 38/202 ảnh có cảnh báo chưa duyệt. AP50 trung bình lớp truck giảm từ 0,6485 xuống 0,5377, trong khi bus tăng nhẹ từ 0,6949 lên 0,7033. Cần ưu tiên kiểm tra chất lượng box và nhầm car/truck/bus, phân bố lớp, xử lý theo quy trình duyệt được phép rồi tái xuất manifest và train thí nghiệm mới.
- **Raw được thư viện tự lọc một phần:** log `evidence/colab_train.log` liệt kê 11 ảnh/nhãn hỏng bị bỏ, tương ứng 213 ảnh còn lại từ 224 ảnh nguồn; clean có 202 ảnh và 0 corrupt. Cột #ảnh train của script đếm ảnh nguồn trước lọc, không phải toàn bộ ảnh model thực sự nhận. Vì vậy so sánh không phải “224 ảnh lỗi hoàn toàn chưa được lọc” với “202 ảnh hoàn hảo”; cần đọc log khi diễn giải lợi ích QC.

Giữ kết luận dataset **Hold**. Cần thêm seed, kiểm tra lỗi còn lại và thí nghiệm đối chứng để đánh giá độ ổn định; không thay số liệu JSON hoặc chọn ngưỡng dựa trên điểm test. Bằng chứng: bốn `results/*_seed*.json`, `comparison.md/json/png`, `colab_run_info.json` và log train gốc.

## 6. Quyết định và ghi chú AI

Giữ **Hold**, chưa phát hành dataset. Để Release, cần xử lý và xác minh các cảnh báo theo quy trình duyệt được phép, chạy lại QC để không còn lỗi bắt buộc và tỷ lệ ảnh còn cảnh báo chưa duyệt dưới 10%. Không tự tăng ngân sách 80 hoặc đổi ngưỡng gate để ép Release.

- **Prompt chính:** yêu cầu AI giải thích code, chạy test và đọc calibration.
- **Cách kiểm:** dùng unit test, calibration trên lỗi chèn sẵn, báo cáo ba vòng QC, log trước/sau, thử gate ngân sách 0 và đối chiếu trực quan các cặp ảnh với AI hỗ trợ. Cần đọc hiểu code AI trước khi nộp.
- **Một lần AI chưa đúng:** đề xuất thử pHash 16 dựa vào calib không phù hợp khi áp dụng tự loại trên raw vì có nhận nhầm; sau kiểm tra ảnh, giảm xuống 10 và sinh lại kết quả. Không ghi quan sát của AI thành tuyên bố học viên đã tự xem toàn bộ ảnh.


**Tự kiểm bài nộp:** log `evidence/colab_check_core.log` xác nhận kiểm phần lõi trên Linux Colab trước train: **79 passed, 0 lỗi, 1 cảnh báo** (bỏ qua train ở lệnh `--no-train`). Sau khi nhập đủ kết quả và cập nhật báo cáo, kiểm đầy đủ trên Windows đạt **79 passed, 1 warning**, nhưng checker còn báo **4 lỗi**: 2 lỗi giả đường dẫn `MANIFEST`/`data/calib` đã biết và 2 lỗi hash manifest do template tính không nhất quán. `train_compare.py` băm byte gốc (SHA1 `93b4684870d984139b16e76da546a4ae513715d7`), còn checker chuyển CRLF thành LF trước khi băm. Manifest hiện tại giống từng byte với bản trong gói upload Colab; cả hai JSON clean khớp byte gốc. Bằng chứng: `evidence/train_integrity.json`, `evidence/windows_check_full.log`. Đây là kết quả của checker gốc chưa sửa lỗi tương thích; cần đối chiếu bản chính thức thống nhất cách băm.

**Kiểm tra tương thích Windows (19/11/2026):** `python scripts/check_submission_portable.py` chạy toàn bộ kiểm tra, gồm train: **79 passed, 1 warning của pytest; 0 lỗi, 0 cảnh báo của checker; mã thoát 0**. Runner chỉ sửa cách so đường dẫn và cách băm manifest trong bộ nhớ; giữ nguyên file checker đề, kiểm hash file bảo vệ, unit test, ngưỡng gate và bốn JSON train gốc. Đây là bản kiểm tra tương thích cục bộ, không phải bản chấm chính thức của giảng viên. Xem `evidence/windows_check_portable.log` và `../docs/CHECKER_COMPATIBILITY.md`.
