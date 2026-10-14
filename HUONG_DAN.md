# HƯỚNG DẪN SALEHUNTER VN V3 (KHÔNG CẦN DOCKER)

## 1. Cập nhật Hugging Face Static Space

- Vào Space đã tạo: `https://huggingface.co/spaces/khoiminh333/salehunter-vn-v2` (nếu bạn dùng Space này).
- Chọn **Files → Add file → Upload files**.
- Giải nén `SaleHunter_V3_HuggingFace_Static.zip` rồi upload **các file bên trong**, không upload nguyên ZIP.
- Khi hiện xung đột file cũ, chọn ghi đè các file tương ứng (`index.html`, `styles.css`, `main.js`, `config.js`, `README.md`, `data/offers.json`).
- **Commit changes** và mở **App**, bấm Ctrl+F5.
- Trong `README.md` cần có `sdk: static`, màu hợp lệ `indigo`, `pink`, `short_description` không quá 60 ký tự.

**Chú ý:** Không upload Python/backend vào Hugging Face Static, vì SDK Static không chạy collector. Gói HF chỉ có frontend và dữ liệu dự phòng.

## 2. Cập nhật GitHub Actions (tự quét nguồn)

- Vào repo của bạn: `https://github.com/CNKhoi/salehunter-vn-static`.
- Giải nén `SaleHunter_V3_GitHub_AutoScan.zip` rồi upload **toàn bộ file, thư mục** lên nhánh chính (`main`).
- Quan trọng: `.github/workflows/update.yml` phải nằm đúng thư mục, `requirements.txt` và `collectors.py` nằm thư mục gốc, `scripts/update_feed.py` nằm trong `scripts`.
- Nếu có file workflow cũ trong `.github/workflows/` thực hiện cùng chức năng, hãy xóa/disable cái cũ để tránh chạy trùng.
- **Settings → Actions → General → Workflow permissions**: chọn **Read and write permissions**.
- **Actions → Cap nhat voucher cong khai → Run workflow**.
- Chờ job báo xanh. Dữ liệu được commit về `data/offers.json`, đồng thời cache từng nguồn nằm trong `data/source_cache.json`.
- Mặc định quét khoảng 30 phút/lần, nhưng lịch GitHub Actions có thể chạy trễ hoặc bỏ lượt theo tải hệ thống.

## 3. Liên kết dữ liệu Hugging Face với GitHub

File `config.js` V3 đã cấu hình sẵn:

```javascript
window.SALEHUNTER_CONFIG = Object.freeze({
  dataUrl: 'https://raw.githubusercontent.com/CNKhoi/salehunter-vn-static/main/data/offers.json',
  reloadSeconds: 180
});
```

Nếu repo đổi tên hoặc chuyển private, phải sửa `dataUrl` cho đúng URL JSON public. Nút **Làm mới dữ liệu** chỉ tải lại JSON, không kích hoạt workflow quét trên server.

## 4. Những thay đổi quan trọng

- Thêm nguồn quét danh sách **chuỗi mã nhập tay công khai** của Mekoupon Shopee; có kết cấu parser để lọc đúng mã, điều kiện đơn tối thiểu, hạn dùng.
- Nguồn TikTok Shop được cấu hình thử theo URL công khai; nếu nguồn không phản hồi hoặc không xuất bản mã nhập tay, danh sách TikTok có thể bằng 0. KHÔNG tạo mã giả.
- Giữ thêm Google News/Bloggiamgia làm thông tin ưu đãi dạng link; những nguồn này thường không có mã Copy.
- Không gọi API cá nhân, không vượt CAPTCHA, không dùng token Shopee/TikTok của người dùng.
- Tránh duplicate; lỗi nguồn không xóa cache; giới hạn cũ theo thời gian; status nguồn công khai trong UI.
- Có **4 mã Shopee được niêm yết trên Mekoupon ngày 14/10/2026** làm dữ liệu khởi tạo. Chúng có hạn dùng và tự ẩn khi quá hạn; KHÔNG cam kết còn lượt/áp dụng được tại thanh toán. Link gốc: https://mekoupon.com/ma-giam-gia/shopee

## 5. Khi báo chưa có mã nhập tay

1. Kiểm tra `https://raw.githubusercontent.com/CNKhoi/salehunter-vn-static/main/data/offers.json`: số lượng `stats.codes` và mảng `items`.
2. GitHub → Actions → workflow → update → xem phần **Thu thap va chuan hoa du lieu**. Nếu source 403/timeout, phải chờ nguồn hồi phục hoặc thay nguồn hợp lệ.
3. Không coi tin báo khuyến mãi là mã Copy trừ khi **có chuỗi code** trong dữ liệu.
4. Mã mới hiển thị không đồng nghĩa còn lượt, vì các nền tảng có quota, thời gian, tài khoản và sản phẩm áp dụng riêng.

## 6. Phân biệt loại link

- **Copy mã**: trang đã niêm yết chuỗi ký tự; sao chép xong người dùng phải tự áp ở bước thanh toán.
- **Xem nguồn**: đọc thông tin và bấm nhận voucher trên trang sàn/đối tác nếu có. Link bài báo không được coi là link lưu mã chính thức.
- Nếu không có nguồn xác minh, không khẳng định mã còn hiệu lực khi thanh toán.

## 7. Kiểm thử

- Backend: `python -m pip install -r requirements.txt` và `python -m unittest discover -s tests -v`.
- Frontend: JavaScript thuần, HTML/CSS không cần build, chạy trên HF Static.
- Không nên dán token tài khoản, mật khẩu hoặc cookie phiên Shopee/TikTok vào GitHub repository công khai.
