// BƯỚC QUAN TRỌNG: Sau khi tạo GitHub repo công khai và chạy Actions,
// điền link RAW của data/offers.json vào trường dataUrl.
// Ví dụ: https://raw.githubusercontent.com/TEN_GITHUB/salehunter-vn-static/main/data/offers.json
// Nếu để trống, web sẽ đọc file dữ liệu đi kèm ở Hugging Face
// và KHÔNG tự nhận dữ liệu mới từ GitHub.
window.SALEHUNTER_CONFIG = Object.freeze({
  dataUrl: '',
  reloadSeconds: 180
});
