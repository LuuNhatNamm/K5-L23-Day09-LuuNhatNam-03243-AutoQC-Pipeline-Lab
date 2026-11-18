# Hoàn thành Lab09 — Luu Nhat Nam, 03243

**Cập nhật 19/11/2026:** đã nhập đủ bốn kết quả train Colab và cập nhật mục 5 REPORT. Các trạng thái “chưa train” trong bảng lịch sử dưới đây là trước lần train đó. Để kiểm tra trên Windows, dùng `python scripts/check_submission_portable.py`; xem `CHECKER_COMPATIBILITY.md` để biết hai lỗi template được sửa khi chạy. File checker gốc và JSON kết quả vẫn được giữ nguyên.

## Trạng thái đã kiểm tra ngày 18/11/2026

Đối chiếu CP4 với file hướng dẫn HTML do học viên cung cấp:

| Yêu cầu | Bằng chứng hiện tại | Kết quả |
|---|---|---|
| Pipeline chạy đủ, xuất reports và clean_v1 | 224 ảnh vào, 22 ảnh loại, 202 ảnh xuất; manifest và 202 nhãn khớp SHA1 | Đạt |
| Đọc đúng quyết định cuối | Hold, 0 lỗi bắt buộc, 38/202 ảnh còn cảnh báo chưa duyệt (18,81%), đã mô phỏng duyệt 80 ảnh | Đạt; không cần ép thành Release |
| Cửa chặn thật | Ngân sách 0: Rework, 6 lỗi thiếu nhãn, mã 20, exported=null, thư mục export thử nghiệm không tồn tại | Đạt |
| Code/test | Kiểm tra lại: 79 passed; file đề, tests và phần cấu hình cố định không bị bộ kiểm tra báo thay đổi | Đạt |
| Mở ảnh kiểm tra | Có 10 cặp ảnh raw/clean đã vẽ tại work/cp4_review |  Các file img_0004,0017,0005 đang đánh sai hoặc thừa box, còn file img_0015 thì thiếu box  |
| Train tùy chọn đã chọn làm | Chưa có bốn JSON kết quả trong submission/results | Chưa hoàn thành |

Hai lỗi MANIFEST/data/calib trên Windows là lỗi template được ghi rõ trong chính file HTML, không phải lỗi thuật toán. Không sửa/xóa nội dung file đề để né lỗi. Notebook dưới đây chạy **bản kiểm tra nguyên gốc trên Linux Colab** trước khi train; phải ra 0 lỗi mới chạy tiếp.

## 1. Xem ảnh để hoàn tất phần thực hành trực quan

Mở hai thư mục trong dự án:

- `work/cp4_review/raw/`: 10 ảnh với nhãn trước pipeline.
- `work/cp4_review/clean/`: cùng 10 ảnh với nhãn xuất clean.

Ví dụ để tự đối chiếu: `img_0001` ở raw thiếu box người đứng mặc quân phục, ở clean đã có box. Ở raw `img_0015`, box bên trái không bao trọn riêng từng người. Kiểm tra các ảnh còn lại và ghi **3 quan sát của chính bạn**, không đổi cảnh báo AI thành khẳng định lỗi nếu chưa nhìn ảnh. Gửi lại các quan sát để bổ sung REPORT. Không sửa dữ liệu gốc.

## 2. Upload notebook và chọn GPU trên Colab

Mở https://colab.research.google.com/ và đăng nhập Google của bạn.

1. Chọn **File → Upload notebook** (hoặc hộp Open notebook → Upload).
2. Chọn file trong thư mục dự án:
   `notebooks/day09_train_LuuNhatNam_03243.ipynb`.
3. Chọn **Runtime → Change runtime type → T4 GPU → Save**.
4. Chạy các ô từ trên xuống. Ô đầu yêu cầu upload gói:
   `work/colab/day09_colab_bundle.zip` (khoảng 65 MiB).

Gói này đã có code, cấu hình đã chọn, dữ liệu, báo cáo và export 202 ảnh; notebook kiểm checksum để tránh dùng nhầm bộ dữ liệu. Không cần sửa REPO_URL hoặc chờ GitHub có manifest cho cách upload này. Tài khoản Google, quyền GPU và quota do Colab cấp; không cần mua gói trả phí để làm theo hướng dẫn này.

## 3. Chạy các ô theo thứ tự

| Ô | Việc thực hiện | Dấu hiệu hoàn thành |
|---|---|---|
| 1 | Upload ZIP, kiểm checksum, đọc manifest | Clean 202 ảnh, quyết định Hold |
| 2 | Cài requirements-train.txt và kiểm GPU | In tên GPU và ultralytics 8.4.214 |
| 3 | Chạy check_submission.py --no-train nguyên gốc trên Linux | 79 test đạt và 0 lỗi kiểm tra |
| 4 | Train raw/clean, mỗi loại seed 0 và 1 | Có đủ raw_seed0, raw_seed1, clean_seed0, clean_seed1 JSON |
| 5 | Tổng hợp bằng summarize_results.py | Hiện bảng mean ± std và biểu đồ |
| 6 | Đóng gói và tải kết quả | Tải được day09_results_03243.zip |

Cấu hình chung: yolo26n.pt, 20 epoch, imgsz 640, batch 16; cùng gold_val và test. Không thay tham số giữa các biến thể. Val dùng cho đánh giá trong train, test dùng đo cuối; không chọn ngưỡng bằng nhãn test.

Giữ tab Colab mở. Thời gian có thể thay đổi theo GPU và tải dịch vụ. Cảnh báo ảnh/nhãn hỏng ở raw là dữ liệu của thí nghiệm; đọc log, không sửa raw cho giống clean. Số 224 là số ảnh nguồn, không bảo đảm model dùng đủ sau khi tự bỏ dữ liệu không hợp lệ.

Nếu ô lỗi đỏ: dừng tại ô đó, gửi nội dung lỗi. Không chạy các ô sau để tạo kết quả thiếu. Trong cùng runtime, có thể chạy lại ô train; --skip-existing chỉ tái sử dụng JSON khớp cấu hình. Nếu runtime bị xóa thì dữ liệu RAM/đĩa tạm Colab có thể mất; giữ các kết quả đã tải về.

## 4. Trả kết quả về dự án và hoàn thiện REPORT

Gửi `day09_results_03243.zip` vào chat này. Gói chứa số liệu gốc do script đề sinh, bảng/biểu đồ so sánh và log kiểm tra/train; không cần gửi trọng số .pt.

Các việc sẽ làm khi nhận kết quả:

1. Kiểm đủ bốn lượt, seed và siêu tham số bằng nhau, checksum manifest/config trùng snapshot.
2. Đưa kết quả vào `submission/results/`, log vào `submission/evidence/`.
3. Chạy lại `python scripts/summarize_results.py`.
4. Thay mục 5 REPORT bằng bảng thực tế; so chênh mAP với độ lệch giữa seed; phân tích ít nhất hai khả năng (dữ liệu rò rỉ/trùng ở raw, nhãn hỏng bị model bỏ, clean còn Hold, phân bố lớp).
5. Không kết luận clean tốt hơn nếu số liệu không đủ; cập nhật tình trạng kiểm tra Linux trong REPORT.
6. Kiểm đầy đủ bằng `python scripts/check_submission.py` trên Linux sau khi cập nhật bài. Windows có thể vẫn báo hai lỗi template đã nêu.

Chưa có kết quả thì không xóa chữ “Chưa chạy” trong mục train hoặc tự điền số mAP.

## 5. Lưu và nộp bài sau khi hoàn thiện kết quả

Chạy từ thư mục gốc dự án, xem thay đổi trước khi commit:

```powershell
git status --short
git diff --check
git add README.md configs/pipeline.yaml submission notebooks/day09_train_LuuNhatNam_03243.ipynb scripts/prepare_colab_bundle.py scripts/check_submission_portable.py docs/FINISH_LAB09.md docs/CHECKER_COMPATIBILITY.md
git commit -m "Complete calibrated QC report and raw clean training comparison"
git push origin main
```

Chỉ commit khi mục train đã cập nhật theo kết quả thật. Không commit work/, .venv/, *.pt, token hay API key. Gói upload nằm trong work/ nên không đưa vào GitHub. Hiện có bốn commit cá nhân cho bốn module; commit kết quả tiếp theo giúp đạt ít nhất năm commit cá nhân theo rubric.

Repo hiện public nhưng tại lần kiểm tra chưa có manifest trên GitHub. Sau push, mở GitHub kiểm tra `submission/export/clean_v1/manifest.json`, bốn JSON kết quả và REPORT hiển thị đúng. Tên repo hiện khác mẫu `K5-L23-DAY09-03243-AutoQCPipeline`; đối chiếu quy ước riêng của lớp trước khi nộp, không tự đổi tên repo giữa lúc làm bài.

Cuối cùng nộp link repo lên https://aithucchien.vinuni.edu.vn/ hoặc kênh giảng viên chỉ định. Git push không đồng nghĩa đã nộp LMS.

## Nếu thay code/config/export sau khi chuẩn bị gói

Sinh lại kết quả pipeline/calibration có liên quan trước, rồi chạy:

```powershell
python scripts/prepare_colab_bundle.py
```

Upload lại cả notebook mới và ZIP mới trong runtime Colab sạch để tránh trộn snapshot. Không dùng số liệu train cũ với manifest mới.
