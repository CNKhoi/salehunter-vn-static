# SaleHunter V3.1 — GitHub Actions

Upload toàn bộ nội dung ZIP lên nhánh `main` (bao gồm `.github/workflows/update.yml`); vào Actions và chạy workflow “Cap nhat voucher cong khai”.

- Bộ quét đọc nguồn công khai và tạo `data/offers.json`.
- File `data/manual_offers.json` **rỗng**, không chứa 4 mã V3 cũ chưa kiểm chứng.
- `data/excluded_codes.json` lưu mã đang tạm ngừng đề xuất theo báo cáo; quản trị viên có thể chỉnh file này và chạy workflow lại. Đây không phải dữ liệu xác minh từ Shopee/TikTok Shop.
- Bộ quét không truy cập tài khoản sàn và không thể xác minh mã tại thanh toán.
- Không sinh mã giả; nếu không tìm thấy mã, dữ liệu 0 mục là hợp lệ.

Trên Hugging Face Static, cài ZIP giao diện V3.1 tương ứng. Giao diện và dữ liệu ngoài là hai thành phần độc lập.
