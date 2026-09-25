# Custom Filters Folder (`filters/`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cung cấp thư mục `filters/` chứa các tệp `.txt` (blacklist, pronouns, trailing_stopwords, non_person) cho phép người dùng tự do kiểm tra, sửa, xóa các từ ngữ cần lọc bỏ, đồng thời tự động nạp vào `NovelScanner` và hỗ trợ tải lại trên giao diện.

**Architecture:** Mở rộng `Config` với thư mục `filters/`; cài đặt các phương thức quản lý tệp bộ lọc trong `NovelScanner` (`_ensure_filter_files`, `load_filters`, `reload_filters`); tích hợp kiểm tra blacklist và dynamic sets vào quá trình quét dòng `_process_line`; hiển thị trạng thái và nút reload trên CLI và Streamlit UI.

**Tech Stack:** Python 3.12, Pathlib, Pytest, Streamlit.

## Global Constraints
- Tất cả tệp trong `filters/` phải dùng mã hóa `utf-8`.
- Mỗi dòng là một từ/cụm từ, tự động chuẩn hóa `.strip().lower()`. Bỏ qua dòng trống và dòng bắt đầu bằng `#`.
- Luôn có cơ chế fallback về bộ từ khóa mặc định nếu tệp bị xóa hoặc rỗng.
- Tất cả các bài kiểm thử hiện có (29 tests) phải tiếp tục PASS mà không có hồi quy (zero regression).

---

### Task 1: Cập nhật Cấu hình Đường dẫn Bộ lọc trong `src/config.py`

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: None
- Produces: `Config.FILTERS_DIR`, `Config.BLACKLIST_FILTER_PATH`, `Config.PRONOUNS_FILTER_PATH`, `Config.TRAILING_STOPWORDS_FILTER_PATH`, `Config.NON_PERSON_FILTER_PATH`

- [ ] **Step 1: Viết test cho cấu hình đường dẫn bộ lọc**

Mở `tests/test_config.py` và thêm test kiểm tra các đường dẫn bộ lọc:

```python
def test_filter_paths(tmp_path):
    config = Config()
    assert config.FILTERS_DIR.name == "filters"
    assert config.BLACKLIST_FILTER_PATH.name == "blacklist.txt"
    assert config.PRONOUNS_FILTER_PATH.name == "pronouns.txt"
    assert config.TRAILING_STOPWORDS_FILTER_PATH.name == "trailing_stopwords.txt"
    assert config.NON_PERSON_FILTER_PATH.name == "non_person.txt"
    assert config.FILTERS_DIR.exists()
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `.\venv\Scripts\python -m pytest tests/test_config.py -k test_filter_paths`
Expected: FAIL với AttributeError vì các thuộc tính chưa được định nghĩa trong `Config`.

- [ ] **Step 3: Cập nhật `src/config.py`**

Thêm các đường dẫn vào `Config`:

```python
    FILTERS_DIR: Path = BASE_DIR / "filters"
    BLACKLIST_FILTER_PATH: Path = FILTERS_DIR / "blacklist.txt"
    PRONOUNS_FILTER_PATH: Path = FILTERS_DIR / "pronouns.txt"
    TRAILING_STOPWORDS_FILTER_PATH: Path = FILTERS_DIR / "trailing_stopwords.txt"
    NON_PERSON_FILTER_PATH: Path = FILTERS_DIR / "non_person.txt"
```

Và trong `Config.__init__()`:
```python
    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.TXT_DIR.mkdir(parents=True, exist_ok=True)
        self.SCANNED_DIR.mkdir(parents=True, exist_ok=True)
        self.FILTERS_DIR.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Chạy test để xác nhận test vượt qua**

Run: `.\venv\Scripts\python -m pytest tests/test_config.py`
Expected: PASS

- [ ] **Step 5: Commit thay đổi**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): add filter directory and file paths"
```

---

### Task 2: Cài đặt Quản lý Bộ lọc & Tích hợp vào `NovelScanner`

**Files:**
- Modify: `src/core/scanner.py`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `Config.FILTERS_DIR`
- Produces: 
  - `NovelScanner._ensure_filter_files(filters_dir: Path)`
  - `NovelScanner.load_filters(filters_dir: Optional[Path] = None)`
  - `NovelScanner.reload_filters() -> Dict[str, int]`
  - `self.blacklist: Set[str]`
  - `self.pronouns_and_starts: Set[str]`
  - `self.trailing_stopwords: Set[str]`
  - `self.non_person_words: Set[str]`

- [ ] **Step 1: Viết test cho việc tự động tạo file và nạp bộ lọc**

Trong `tests/test_scanner.py`, thêm các test cases:
1. `test_auto_create_and_load_filters`: Kiểm tra thư mục tạm tạo đủ 4 file `.txt` có nội dung mẫu và nạp thành công vào scanner.
2. `test_filters_comment_and_blank_handling`: Đảm bảo các dòng bắt đầu bằng `#` và dòng trống được bỏ qua.
3. `test_blacklist_filtering`: Thêm một từ vào blacklist (ví dụ `"Thử nghiệm cấm"`) và xác nhận scanner bỏ qua hoàn toàn.
4. `test_reload_filters`: Thêm từ mới vào file `.txt` và gọi `reload_filters()`, kiểm tra scanner cập nhật ngay lập tức.

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `.\venv\Scripts\python -m pytest tests/test_scanner.py -k "test_auto_create_and_load_filters or test_blacklist_filtering"`
Expected: FAIL vì các phương thức quản lý filter chưa được cài đặt.

- [ ] **Step 3: Cài đặt logic nạp bộ lọc trong `NovelScanner`**

Trong `src/core/scanner.py`:
1. Định nghĩa `DEFAULT_BLACKLIST`, `DEFAULT_PRONOUNS_AND_STARTS`, `DEFAULT_TRAILING_STOPWORDS`, `DEFAULT_NON_PERSON`.
2. Trong `NovelScanner.__init__(self, filters_dir: Optional[Path] = None)`:
   - Khởi tạo `self.filters_dir = filters_dir or Config.FILTERS_DIR`.
   - Gọi `self._ensure_filter_files()` và `self.load_filters()`.
3. Cài đặt `_ensure_filter_files()`: Tự động ghi file template kèm header hướng dẫn (`# Danh sách từ cấm...`) nếu file chưa có.
4. Cài đặt `_read_filter_file(path: Path) -> Set[str]`: Đọc file UTF-8, strip, lower, bỏ qua `#` và rỗng.
5. Cài đặt `load_filters()`: Đọc các file và gán vào `self.blacklist`, `self.pronouns_and_starts`, `self.trailing_stopwords`, `self.non_person_words`. Nếu file rỗng, fallback về `DEFAULT_*`.
6. Cài đặt `reload_filters() -> Dict[str, int]`: Nạp lại và trả về dict thống kê số lượng từ mỗi loại.
7. Cập nhật `_process_line` và `_build_candidates`:
   - Kiểm tra `if lower_phrase in self.blacklist or phrase.lower() in self.blacklist: return`
   - Dùng `self.pronouns_and_starts` thay vì `self.COMMON_PRONOUNS_AND_STARTS`.
   - Dùng `self.trailing_stopwords` thay vì `self.COMMON_TRAILING_STOPWORDS`.
   - Dùng `self.non_person_words` thay vì `self.COMMON_NON_PERSON_WORDS`.

- [ ] **Step 4: Chạy test để xác nhận tất cả test scanner vượt qua**

Run: `.\venv\Scripts\python -m pytest tests/test_scanner.py`
Expected: PASS 100%

- [ ] **Step 5: Commit thay đổi**

```bash
git add src/core/scanner.py tests/test_scanner.py
git commit -m "feat(scanner): add customizable filters folder support and blacklist filtering"
```

---

### Task 3: Tích hợp Thông tin Bộ lọc & Nút Reload vào CLI và Streamlit UI

**Files:**
- Modify: `scripts/scan_cli.py`
- Modify: `src/ui/tab_scan.py`

**Interfaces:**
- Consumes: `scanner.reload_filters()`, `scanner.filters_dir`, `len(scanner.blacklist)`, etc.
- Produces: CLI logs & Streamlit UI widgets

- [ ] **Step 1: Cập nhật `scripts/scan_cli.py`**

Thêm log hiển thị trạng thái bộ lọc khi khởi động scanner:
```python
counts = {
    "từ cấm": len(scanner.blacklist),
    "đại từ": len(scanner.pronouns_and_starts),
    "từ đuôi": len(scanner.trailing_stopwords),
    "phi nhân vật": len(scanner.non_person_words),
}
logger.info(f"Đã nạp bộ lọc tùy biến từ filters/: {', '.join(f'{v} {k}' for k, v in counts.items())}")
```

- [ ] **Step 2: Cập nhật `src/ui/tab_scan.py`**

1. Khởi tạo scanner và hiển thị khối thông tin trạng thái bộ lọc gọn gàng (ví dụ `st.caption` hoặc info box):
   - "📁 Thư mục bộ lọc: `filters/` (X từ cấm, Y đại từ, Z từ đuôi)"
2. Thêm nút bấm **"🔄 Tải lại bộ lọc"**:
   - Khi bấm, gọi `st.session_state.scanner.reload_filters()`
   - Hiển thị `st.success("Đã nạp lại bộ lọc thành công!")` và cập nhật thông số.

- [ ] **Step 3: Chạy thử nghiệm CLI để kiểm tra hiển thị**

Run: `.\venv\Scripts\python scripts/scan_cli.py --file exam.txt --min-count 5`
Expected: Log hiển thị thông báo bộ lọc rõ ràng và scan thành công.

- [ ] **Step 4: Commit thay đổi**

```bash
git add scripts/scan_cli.py src/ui/tab_scan.py
git commit -m "feat(ui,cli): display filter stats and add filter reload capability"
```

---

### Task 4: Kiểm thử Tổng thể & Xác minh Hoạt động (Verification)

**Files:**
- Test all: `tests/`
- Real-world scan: `exam.txt`

- [ ] **Step 1: Chạy toàn bộ test suite dự án**

Run: `.\venv\Scripts\python -m pytest`
Expected: Tất cả các bài test (30+ tests) PASS 100%.

- [ ] **Step 2: Thử nghiệm sửa file bộ lọc thực tế**

1. Mở `filters/blacklist.txt` và thêm một từ đang có tần suất cao (ví dụ `"Huyền Vũ"`).
2. Chạy lại `scan_cli.py --file exam.txt --min-count 2`.
3. Xác minh `"Huyền Vũ"` biến mất hoàn toàn khỏi danh sách ứng viên được tìm thấy.
4. Xóa `"Huyền Vũ"` khỏi `filters/blacklist.txt` để khôi phục trạng thái ban đầu.

- [ ] **Step 3: Commit hoàn tất tính năng**

```bash
git add filters/
git commit -m "feat: initialize default filters in filters directory"
```
