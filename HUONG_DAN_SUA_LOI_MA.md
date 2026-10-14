# SaleHunter GitHub AutoScan V3.1

- Upload **toàn bộ file** ở thư mục gốc ZIP, gồm `.github/workflows/update.yml`, `collectors.py`, `requirements.txt`, `scripts/`, `tests/`, `data/`.
- `data/manual_offers.json` được đặt thành `[]` để tránh tái xuất bản 4 mã seed V3 chưa được thử tại thanh toán.
- `data/excluded_codes.json`: danh sách mã người dùng đã báo lỗi, quản trị viên quyết định loại khỏi đề xuất (đây không phải kết luận mã vô hiệu với mọi tài khoản).
- Chạy Actions → Cap nhat voucher cong khai → Run workflow. Xem JSON tại `data/offers.json`. Danh sách rỗng là kết quả hợp lệ khi chưa đọc được mã có nguồn; không sinh mã tự tạo.
- `data/source_cache.json` khởi tạo rỗng; quét thành công sẽ tạo lại. Nếu mã không hợp lệ được lưu ở nguồn cũ, denylist sẽ loại khỏi kết quả hiển thị.
- Dữ liệu từ nguồn ngoài được gắn nhãn “chưa xác minh tại thanh toán”; chỉ thao tác áp dụng trên sàn mới kết luận cho phiên giao dịch cụ thể.
