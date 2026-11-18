# Kiểm tra bài trên Windows: lỗi đường dẫn và CRLF

Lệnh kiểm tra tương thích đầy đủ, gồm train:

```powershell
python scripts/check_submission_portable.py
```

Đây là runner bổ sung để kiểm tra cục bộ, không phải bản chấm chính thức của giảng viên. Runner thực thi toàn bộ `check_submission.py`, chỉ áp dụng hai thay đổi công khai trong bộ nhớ, không sửa file đề trên đĩa:

1. Dùng `p.relative_to(ROOT).as_posix()` để so với các khóa có dấu `/` của `_protected.json`. Trên Windows, `str(...)` dùng dấu `\`, làm checker quét nhầm file calibration đã được bảo vệ. Việc kiểm hash của các file bảo vệ vẫn giữ nguyên.
2. So `manifest_sha1` với SHA1 của **byte gốc** của manifest, giống `train_compare.py`. Không chuẩn hóa CRLF ở phép so này. Hàm chuẩn hóa dùng để kiểm các file đề vẫn giữ nguyên.

Với kết quả hiện tại:

- SHA1 byte gốc manifest: `93b4684870d984139b16e76da546a4ae513715d7`.
- SHA1 nếu chuyển CRLF thành LF: `3cae0138cfcf7c649976b263b590cfa643bf3081`.
- Hai JSON clean lưu hash byte gốc. Manifest trong gói upload Colab giống từng byte với file hiện tại.

Runner không sửa JSON, không chấp nhận hash bất kỳ, không bỏ unit test, không thay đổi ngưỡng gate/ngân sách hoặc bỏ kiểm tra train. Manifest thực sự khác byte sẽ vẫn bị báo lỗi. Khi câu lệnh gốc thay đổi, runner dừng nếu không còn tìm đúng hai vị trí cần sửa.

Lệnh gốc `python scripts/check_submission.py` vẫn có thể báo bốn lỗi template này; cần gửi mô tả và bản vá cho giảng viên khi đối chiếu kết quả chấm chính thức. Bằng chứng gốc ở `submission/evidence/windows_check_full.log`, bằng chứng kiểm tra tương thích ở `submission/evidence/windows_check_portable.log`.
