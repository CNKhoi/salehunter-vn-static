# Quy trình quản trị viên xác nhận mã

1. Lấy mã từ tab **Chưa kiểm chứng** và kiểm tra thực tế trên tài khoản được phép.
2. Chỉ khi màn hình thanh toán chấp nhận mã, ghi thông tin vào `data/verified_codes.json`.
3. Ví dụ bản ghi (KHÔNG phải mã dùng thật):

```json
{
  "records": [{
    "platform": "Shopee",
    "code": "EXAMPLE123",
    "basis": "checkout_success",
    "successful_at": "2026-10-15T10:00:00+07:00",
    "context": "Đã thử mã được chấp nhận tại thanh toán, đơn thử phù hợp điều kiện"
  }]
}
```

4. Commit file lên GitHub. Workflow quét lại và ghi nhãn. Sau 24 giờ mã tự rơi
   khỏi danh sách chính cho đến khi thử thành công lại.
5. Khi mã bị báo lỗi, người quản trị kiểm tra và thêm vào `data/excluded_codes.json`.
   Mã sẽ bị ẩn khỏi feed cho tất cả người xem sau lần cập nhật.

**Đừng đưa mã chưa dùng được hoặc chỉ thấy trên trang tổng hợp vào danh sách đã thử thành công.**
Tránh đăng thông tin người mua, mã đơn hoặc thông tin thanh toán trong JSON công khai.
