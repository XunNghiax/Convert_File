# Thiết kế Hệ thống Thư mục Bộ lọc Tùy biến (`filters/`) cho Novel Translation Refiner

## 1. Mục tiêu
Cung cấp cho người dùng một thư mục độc lập `filters/` chứa các tệp văn bản thuần (`.txt`, mã hóa UTF-8) để dễ dàng kiểm tra, bổ sung, chỉnh sửa hoặc xóa bỏ các từ ngữ cần lọc trong quá trình quét tiểu thuyết (NovelScanner).

## 2. Cấu trúc thư mục & Quy ước tệp

Thư mục nằm tại gốc dự án: `filters/`
Bao gồm các tệp cấu hình:
- `filters/blacklist.txt`: Danh sách các từ/cụm từ cấm tuyệt đối. Mọi ứng viên trùng khớp (không phân biệt hoa/thường) với danh sách này sẽ bị loại bỏ hoàn toàn khỏi kết quả quét.
- `filters/pronouns.txt`: Danh sách các đại từ nhân xưng, từ mở đầu câu, liên từ, giới từ tiếng Việt. Các từ này tuyệt đối không được phép đứng đầu trong một ứng viên tên riêng.
- `filters/trailing_stopwords.txt`: Danh sách các động từ hành động, phó từ, trợ từ tiếng Việt. Trong cụm 2 từ, nếu từ thứ 2 thuộc danh sách này thì cụm đó không được xem là tên riêng.
- `filters/non_person.txt`: Danh sách các từ chỉ địa danh, tổ chức, đồ vật, khái niệm phi nhân vật (ví dụ: bệnh viện, trường học, công ty...).

### Quy cách nội dung mỗi tệp `.txt`:
- Mỗi từ hoặc cụm từ nằm trên một dòng riêng biệt.
- Hỗ trợ comment: Bất kỳ dòng nào bắt đầu bằng ký tự `#` (sau khi strip khoảng trắng) được coi là chú thích và sẽ bị bỏ qua.
- Dòng trống được tự động bỏ qua.
- Không phân biệt hoa/thường: Hệ thống tự động chuẩn hóa sang chữ thường (`.lower()`) khi nạp vào bộ nhớ để so sánh.
- Mã hóa bắt buộc: `utf-8`.

## 3. Kiến trúc & Thành phần triển khai

### 3.1. Cấu hình (`src/config.py`)
- Bổ sung `FILTERS_DIR: Path = BASE_DIR / "filters"` vào lớp `Config`.
- Định nghĩa các hằng số đường dẫn:
  - `BLACKLIST_FILTER_PATH: Path = FILTERS_DIR / "blacklist.txt"`
  - `PRONOUNS_FILTER_PATH: Path = FILTERS_DIR / "pronouns.txt"`
  - `TRAILING_STOPWORDS_FILTER_PATH: Path = FILTERS_DIR / "trailing_stopwords.txt"`
  - `NON_PERSON_FILTER_PATH: Path = FILTERS_DIR / "non_person.txt"`
- Trong `Config.__init__()`, đảm bảo thư mục `self.FILTERS_DIR.mkdir(parents=True, exist_ok=True)` được tự động tạo.

### 3.2. Quản lý Bộ lọc trong `NovelScanner` (`src/core/scanner.py`)
- Định nghĩa các tập từ khóa mặc định tích hợp sẵn (built-in defaults) cho từng danh mục để làm fallback an toàn:
  - `DEFAULT_BLACKLIST: Set[str]`
  - `DEFAULT_PRONOUNS_AND_STARTS: Set[str]`
  - `DEFAULT_TRAILING_STOPWORDS: Set[str]`
  - `DEFAULT_NON_PERSON: Set[str]`
- Phương thức `_ensure_filter_files()`:
  - Kiểm tra sự tồn tại của từng tệp trong `filters/`.
  - Nếu tệp chưa tồn tại, tự động tạo tệp với nội dung từ bộ mặc định tương ứng kèm dòng chú thích hướng dẫn ở đầu file.
- Phương thức `load_filters()`:
  - Đọc nội dung từ các tệp `.txt` trong `filters/`.
  - Parse từng dòng: loại bỏ khoảng trắng thừa, bỏ qua dòng trống và dòng bắt đầu bằng `#`.
  - Lưu vào các thuộc tính instance: `self.blacklist`, `self.pronouns_and_starts`, `self.trailing_stopwords`, `self.non_person_words`.
  - Nếu một file rỗng hoặc thiếu, fallback về bộ từ khóa mặc định.
- Phương thức `reload_filters()`:
  - Cho phép nạp lại bộ lọc tức thì từ đĩa mà không cần khởi tạo lại đối tượng scanner.
- Tích hợp vào quy trình quét (`_process_line` & `_build_candidates`):
  - Kiểm tra `self.blacklist`: nếu từ thô hoặc từ chuẩn hóa nằm trong blacklist, loại bỏ ngay.
  - Áp dụng `self.pronouns_and_starts` thay vì hằng số lớp cố định.
  - Áp dụng `self.trailing_stopwords` thay vì hằng số lớp cố định.
  - Áp dụng `self.non_person_words` để phân loại chính xác hoặc lọc bỏ.

### 3.3. Tích hợp CLI (`scripts/scan_cli.py`)
- Khi bắt đầu quét, hiển thị log thông báo số lượng từ khóa đã nạp từ thư mục `filters/`:
  - Ví dụ: `[INFO] Đã nạp bộ lọc tùy biến từ filters/: 45 từ cấm, 85 đại từ, 115 từ đuôi, 25 phi nhân vật.`

### 3.4. Tích hợp Giao diện Web Streamlit (`src/ui/tab_scan.py`)
- Trong giao diện Scan, hiển thị thông tin thống kê tóm tắt về bộ lọc:
  - Huy hiệu/Text nhỏ: *Bộ lọc đang hoạt động: X từ cấm, Y đại từ, Z từ đuôi.*
- Thêm nút tiện ích: **"🔄 Tải lại bộ lọc từ thư mục filters/"** (cho phép người dùng sau khi sửa file `.txt` bằng Notepad có thể click để áp dụng ngay mà không cần reload trang hay khởi động lại app).

## 4. Xử lý ngoại lệ & Tính chịu lỗi (Error Handling & Resilience)
1. **File không tồn tại:** Tự động tạo mới với dữ liệu mẫu hoàn chỉnh.
2. **File rỗng hoặc bị xóa hết nội dung:** Tự động fallback sang danh sách built-in default để không làm hỏng logic quét.
3. **Lỗi mã hóa hoặc ký tự đặc biệt:** Xử lý với `errors="replace"` và `strip()`, không gây crash chương trình.
4. **Từ trùng lặp:** Lưu trữ dưới dạng `set()`, tự động loại bỏ trùng lặp khi nạp vào RAM.

## 5. Kế hoạch Kiểm thử (Verification Plan)
1. **Unit tests (`tests/test_scanner.py`):**
   - Test tự động tạo file mẫu trong `filters/` khi chưa có.
   - Test đọc file text, bỏ qua comment `#` và dòng trắng.
   - Test thêm 1 từ mới vào `blacklist.txt` và xác nhận scanner bỏ qua từ đó khi quét.
   - Test thêm 1 từ mới vào `pronouns.txt` và xác nhận scanner không bắt cụm từ bắt đầu bằng từ đó.
   - Test tính năng `reload_filters()`.
2. **Kiểm thử hệ thống:**
   - Chạy toàn bộ test suite `pytest` (29+ tests) đảm bảo 100% PASS.
   - Chạy CLI scanner trên `exam.txt` xác nhận hoạt động mượt mà.
