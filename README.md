# Khảo sát tự động - UDA (myUDA)

Công cụ tự động hóa khảo sát học phần cho sinh viên Đại học Đông Á (UDA), hỗ trợ cổng thông tin **myUDA** mới nhất.

## Tính năng
- Tự động đăng nhập vào cổng thông tin myUDA.
- Tự động nạp danh sách các học phần cần khảo sát qua Ajax.
- **Turbo Mode**: Đánh giá tất cả câu hỏi theo thang điểm tối đa bằng JavaScript chỉ trong vài mili-giây.
- Tự động xử lý các modal xác nhận (`#globalConfirmModal`, SweetAlert).
- Tốc độ hoàn thành: ~1 - 1.5 giây / học phần.

## Cài đặt
Yêu cầu Python 3.9+ và Google Chrome.

```bash
pip install -r requirements.txt
```

## Sử dụng
1. Mở file `khao_sat_tu_dong v2.py` và cập nhật thông tin tài khoản:
   - `USERNAME`: Mã sinh viên
   - `PASSWORD`: Mật khẩu
2. Chạy script:
   ```bash
   python "khao_sat_tu_dong v2.py"
   ```
