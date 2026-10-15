# SaleHunter VN V3.1 — GitHub AutoScan

Bộ thu thập công khai cho giao diện Hugging Face **Static**. Python chạy bằng GitHub Actions, không dùng Docker.

## Cài đặt
1. Upload toàn bộ nội dung ZIP lên repository `CNKhoi/salehunter-vn-static` (nhánh `main`).
2. Kiểm tra `.github/workflows/update.yml`, `requirements.txt`, `collectors.py`, `scripts/update_feed.py` nằm đúng vị trí.
3. Vào Settings → Actions → General, cấp `Read and write permissions` nếu cần; chạy workflow **Cap nhat voucher cong khai**.
4. Kiểm tra `data/offers.json` được cập nhật, xem trạng thái mỗi nguồn ở `sources`.

Mã được phát hiện từ trang công khai chưa được Shopee/TikTok Shop xác minh khi thanh toán; một mã có thể không áp dụng cho một tài khoản hoặc đơn hàng. Không tự suy ra mã còn dùng chỉ từ hạn công bố.

Quản trị viên có thể dùng `data/excluded_codes.json` để tạm loại mã bị phản ánh. Thư mục `data/manual_offers.json` được để rỗng để tránh hiển thị mã seed chưa được xác minh.


## Tự đồng bộ lên Hugging Face
- GitHub `Settings > Secrets and variables > Actions > New repository secret`: tạo `HF_TOKEN`.
- Token là Hugging Face fine-grained với quyền write **chỉ vào Space** `khoiminh333/salehunter-vn-v2`. Không chia sẻ token trong chat.
- `Actions > Deploy Hugging Face Static > Run workflow`. Nếu thiếu token, workflow chỉ bỏ qua.
- Dữ liệu `data/offers.json` được cập nhật bởi workflow săn mã độc lập; Hugging Face tải trực tiếp JSON GitHub.
