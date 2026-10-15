# SaleHunter VN V3.3 — GitHub AutoScan

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


### Hiển thị nghiêm ngặt V3.3

- Tab chính **Mã đã thử thành công** chỉ hiển thị chuỗi mã được quản trị viên
  xác nhận đã áp dụng thành công trong 24 giờ qua (không bảo đảm cho tài khoản khác).
- Tab **Mã chưa kiểm chứng** là khu vực tham khảo riêng; không tự trộn vào mục chính.
- File `data/verified_codes.json` trên GitHub mặc định là danh sách rỗng.
  Không thêm xác nhận khi chưa có thử nghiệm thực tế.
- File `data/excluded_codes.json` chặn mã đã báo lỗi trên **tất cả** thiết bị
  trong lần quét kế tiếp, kể cả mã từ cache; xem xét gỡ chặn sau khi kiểm tra lại.
- Không có API checkout từ Shopee/TikTok Shop nên hệ thống không thể tự xác minh
  mã cho mọi tài khoản. Không sử dụng mã giả hoặc thử đoán mã.
