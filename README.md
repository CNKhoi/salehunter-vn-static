---
title: SaleHunter VN V2 - Free Static
emoji: 🎟️
colorFrom: orange
colorTo: pink
sdk: static
app_file: index.html
fullWidth: true
short_description: Theo dõi voucher công khai Shopee/TikTok Shop từ JSON do GitHub Actions cập nhật.
---

# SaleHunter VN V2 · Hugging Face Static (không cần Docker)

**Bản này dùng được với lựa chọn Static → Blank trong Hugging Face Free.**
Dùng giao diện HTML/CSS/JS của V2; backend quét được chuyển sang **GitHub Actions** (tùy chọn), lưu dữ liệu nguồn bằng JSON. Không cần chạy máy 24/7, không có server Python trong Static Space.

> **Tuyên bố trung thực:** Đây là hệ thống tổng hợp **tin/voucher từ nguồn công khai**, không phải bot tự động đăng nhập/nhận voucher; không bảo đảm tìm đủ mã hoặc mã áp dụng được ở checkout. Khi một nguồn lỗi, dữ liệu từ lần quét trước được giữ và có đánh dấu. Trong chế độ Static, "Làm mới" chỉ tải JSON đang có, **không kích hoạt một lượt quét mới**.

## A. Đưa giao diện lên Hugging Face (5 phút)

1. Vào https://huggingface.co/new-space; chọn **Manual setup**.
2. **Owner**: tài khoản của bạn; **Space name**: `salehunter-vn-v2` (hoặc `salehunter-vn-static` nếu trùng tên).
3. **Select Space SDK**: **Static** → **Blank** (không chọn Docker, Gradio).
4. Chọn Public (nếu muốn ai cũng truy cập), ấn **Create Space**.
5. Trong tab **Files**, chọn **Add file → Upload files**, tải **các file bên trong ZIP sau khi giải nén**, giữ đúng cây thư mục. Tối thiểu phải có `README.md`, `index.html`, `main.js`, `styles.css`, `config.js`, `data/offers.json` tại đúng đường dẫn.
6. Commit; mở tab **App**. Ban đầu danh sách có thể rỗng vì **không kèm voucher giả**.

**Bạn không cần cài Docker vào máy.** Các file `.github/`, `collectors.py`, `scripts/` và `requirements.txt` chỉ dành cho kho GitHub khi bật quét tự động; để chúng trong Static Space cũng không làm chạy Python.

## B. Bật tự động cập nhật qua GitHub (khuyến nghị)

1. Vào https://github.com/new, tạo repo **Public**, ví dụ tên `salehunter-vn-static`. Cần **quyền ghi (write) cho GitHub Actions** trên repo này.
2. Giải nén cùng ZIP và tải **toàn bộ nội dung** vào thư mục gốc repo GitHub, **bao gồm `.github/workflows/update.yml`** và các thư mục `scripts`, `data`, `tests`. Commit.
3. Trong GitHub repo: **Settings → Actions → General → Workflow permissions** → chọn **Read and write permissions** (nếu chưa được cho phép). Save. Đây là quyền GITHUB_TOKEN của workflow trong repo, không phải token Shopee/TikTok.
4. Vào **Actions** → workflow **Cap nhat voucher cong khai** → **Run workflow** → Run workflow; chờ chạy xong. GitHub tự tạo/cập nhật `data/offers.json`. Nếu không thấy workflow, kiểm tra file `.github/workflows/update.yml` có nằm đúng đường dẫn.
5. Vào repo GitHub → `data` → `offers.json` → nút **Raw**, sao chép URL dạng:

   `https://raw.githubusercontent.com/TEN_GITHUB/salehunter-vn-static/main/data/offers.json`

6. Quay về Hugging Face Space → **Files → config.js → Edit**. Điền URL trên vào `dataUrl` như sau:

   ```js
   window.SALEHUNTER_CONFIG = Object.freeze({
     dataUrl: 'https://raw.githubusercontent.com/TEN_GITHUB/salehunter-vn-static/main/data/offers.json',
     reloadSeconds: 180
   });
   ```

7. Commit `config.js` và quay lại tab **App**, tải lại trang (Ctrl+F5). Giao diện đọc JSON GitHub, kiểm tra trạng thái nguồn ở cuối trang.

**Lịch tự động:** `8,38 * * * *` (UTC), dự kiến mỗi 30 phút. GitHub Actions chạy theo giờ UTC, có thể chạy trễ hoặc bị bỏ qua trong thời gian tải cao. Workflow có thể bị vô hiệu hóa sau thời gian repo public không hoạt động; khi đó cần bật lại ở Actions. Việc bấm **Làm mới** trong giao diện **không** thay thế việc Run workflow.

## C. Cấu trúc ZIP

```text
README.md                       # Cấu hình Space SDK: static
index.html                      # Giao diện bản V2
styles.css, main.js, config.js  # CSS, giao diện, đường dẫn JSON
collectors.py                   # Tải tin/voucher từ nguồn công khai
requirements.txt               # Thư viện chỉ dành cho GitHub Actions
.github/workflows/update.yml   # Quét lịch 2 lần/giờ
scripts/update_feed.py         # Giữ cache nguồn lỗi, chống trùng, hết hạn
 data/
    manual_offers.json          # Mã do admin cung cấp (mặc định [])
    offers.json                 # JSON mà giao diện đọc
    source_cache.json           # Bộ nhớ cache theo nguồn, GitHub Actions ghi
 tests/test_update_feed.py      # Kiểm thử tự động (không cần mạng)
```

## D. Bổ sung voucher có nguồn thật

Mở `data/manual_offers.json` trong GitHub và điền **mã đã được công bố**, chỉ khi có bằng chứng nguồn thật:

```json
[
  {
    "platform": "Shopee",
    "title": "Tên chương trình đúng theo nguồn thật",
    "description": "Mô tả điều kiện được công bố",
    "code": null,
    "discount": "20%",
    "min_spend": "Từ 199.000đ",
    "url": "https://shopee.vn/m/ma-giam-gia",
    "expires_at": "2026-12-31T23:59:59+07:00"
  }
]
```

Đây chỉ là **mẫu cú pháp JSON**, không phải ưu đãi hiện có. Nếu nguồn không cung cấp chuỗi mã, để `code: null` và người dùng nhấn "Xem nguồn". Nhớ nhấn **Run workflow** sau khi thay đổi nếu muốn thấy ngay.

Tùy chọn nguồn JSON khác: vào GitHub repo → Settings → Secrets and variables → Actions → tab **Variables** → **New repository variable** đặt tên `EXTERNAL_FEEDS`. Giá trị gồm tối đa 3 URL HTTPS raw GitHub/Gist, ngăn cách bằng dấu phẩy. Nguồn có cấu trúc tương tự `manual_offers.json`. Không cung cấp cookie hoặc token tài khoản mua sắm.

## E. Xử lý lỗi

| Triệu chứng | Cách kiểm tra |
|---|---|
| Docker ghi Paid | Chọn **Static**, không chọn Docker. |
| Tạo Space xong nhưng hiện màn hình trống | `index.html`, `styles.css`, `main.js`, `config.js` phải ở thư mục gốc, không nằm trong thư mục ZIP lồng nhau. |
| Chưa có mã/ưu đãi | Kiểm tra Actions có run thành công chưa; mở JSON Raw, xem `stats.all` và `sources[].error`. Không có tin mới thì kết quả bằng 0 là bình thường. |
| Có lỗi HTTP/CORS | Kiểm tra `config.js` là URL `https://raw.githubusercontent.com/.../main/data/offers.json`, repo phải là **Public**. |
| GitHub Actions không ghi JSON | Repo → Settings → Actions → General → Workflow permissions: **Read and write permissions**. |
| Bấm Làm mới nhưng không có mã mới | Nút chỉ nạp lại JSON đang có; nhấn Run workflow trên GitHub để thu thập ngay. |
| Không thấy lịch sử sau khi lỗi nguồn | Cache theo nguồn nằm ở `data/source_cache.json`; đừng xóa file này nếu muốn giữ dữ liệu hợp lệ cũ. |

**Cảnh báo:** Tin Google News không phải danh mục voucher chính thức. Không thể khẳng định mã còn lượt hay hiệu lực nếu chưa kiểm tra điều kiện trong ứng dụng Shopee/TikTok Shop. Các tính năng claim tự động, vượt CAPTCHA hoặc xác minh tại thanh toán không nằm trong bản này.
