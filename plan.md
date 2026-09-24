# KẾ HOẠCH THIẾT KẾ VÀ TRIỂN KHAI CHI TIẾT ỨNG DỤNG CONVERT & CHUẨN HÓA TRUYỆN DỊCH THÔ
*(Novel Translation Refiner & Dictionary Builder)*

---

# PHẦN 1: THIẾT KẾ KIẾN TRÚC TỔNG QUAN (SPECIFICATION & DESIGN)

## 1. TỔNG QUAN DỰ ÁN
- **Mục tiêu**: Xây dựng công cụ chuyên dụng giúp đọc, chuẩn hóa và chuyển đổi các file truyện convert/dịch thô tiếng Trung (bản dịch máy, Hán Việt ngô nghê) sang tiếng Việt tự nhiên và chuẩn xác.
- **Điểm đột phá**:
  - Hỗ trợ xây dựng từ điển bán tự động thông qua cơ chế quét heuristic phát hiện tên riêng và từ ngữ bất thường, kết hợp AI (Gemini/OpenAI) để phân loại và đề xuất bản dịch chuẩn.
  - Quản lý 2 tầng từ điển rõ ràng: **Từ điển từ phổ biến (`co-N`)** (dùng chung cho mọi truyện) và **Từ điển tên nhân vật (`ch-N`)** (kèm tag truyện để quản lý tập trung).
  - Tự động chuẩn hóa viết hoa (Title Case) riêng cho tên nhân vật (`ch-`), trong khi bảo lưu ngữ cảnh chữ hoa/thường tự nhiên cho từ phổ biến (`co-`).
  - Engine thay thế siêu tốc (Longest-Match-First Trie / Regex Alternation + Streaming Buffer) xử lý mượt mà các file truyện dung lượng lớn (10MB – 70MB+).
  - Giao diện trực quan bằng **Streamlit Web UI**, cho phép duyệt từ điển trực tiếp trên bảng, xem trước (diff preview) và tải file đã convert.

---

## 2. KIẾN TRÚC DỮ LIỆU & TỪ ĐIỂN
Hệ thống quản lý 2 file từ điển độc lập lưu dưới định dạng JSON:

### 2.1. Từ điển Từ phổ biến (`data/common_dict.json`)
- `id`: Mã định danh tăng dần `co-1`, `co-2`, ...
- `source`: Từ gốc / từ thô (vd: *"đương gia hoa đán"*, *"lấy gã bác sĩ"*).
- `target`: Từ thay thế chuẩn (vd: *"ngôi sao trụ cột"*, *"bác sĩ gả cho"*).
- `category`: Phân loại (*"Lỗi dịch máy"*, *"Xưng hô"*, *"Thuật ngữ"*, *"Chung"*).
- `notes`: Ghi chú ngữ cảnh.

### 2.2. Từ điển Tên nhân vật (`data/character_dict.json`)
- `id`: Mã định danh tăng dần `ch-1`, `ch-2`, ...
- `source`: Tên thô ban đầu (vd: *"Gavin phong"*, *"Chu phương băng"*, *"Tô Liên Xuân"*).
- `target`: Tên chuẩn hóa Title Case (vd: *"Giả Văn Phong"*, *"Chu Phương Băng"*, *"Tô Liên Xuân"*).
- `novel_tag`: Tag bộ truyện (vd: *"Thiếu Long"*, *"Toàn chức"* hoặc *"Chung"*).
- `gender_role`: Vai vế / giới tính (vd: *"nam, 30 tuổi"*).

---

## 3. CÁC MODULE CỐT LÕI (CORE ENGINES)
1. **Module Quét & Trích xuất (NovelScanner)**:
   - Regex & N-gram thống kê trích xuất cụm viết hoa (tên riêng) và các mẫu dịch thô bất thường.
2. **AI Assistant (Gemini / OpenAI)**:
   - Batching 30-50 từ/lô để phân loại thực thể và gợi ý bản dịch tiếng Việt chuẩn.
3. **High-Performance Replacer Engine**:
   - Longest Match First: Ưu tiên cụm từ dài trước cụm từ ngắn.
   - Auto Title-Case exclusively for `ch-`.
   - Streaming Buffer: Đọc & ghi theo khối dòng, không bao giờ tràn RAM với file 50-70MB.

---

# PHẦN 2: KẾ HOẠCH TRIỂN KHAI KỸ THUẬT CHI TIẾT (IMPLEMENTATION PLAN)

### Task 1: Environment & Project Scaffolding
- **Files**: `src/__init__.py`, `src/config.py`, `src/core/__init__.py`, `src/ui/__init__.py`, `data/common_dict.json`, `data/character_dict.json`
- **Test**: `tests/test_config.py`
- [x] **Step 1: Write test_config.py**
```python
from src.config import Config
def test_config_paths_exist():
    config = Config()
    assert config.BASE_DIR.exists()
    assert config.DATA_DIR.name == "data"
    assert config.COMMON_DICT_PATH.name == "common_dict.json"
    assert config.CHARACTER_DICT_PATH.name == "character_dict.json"
```
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Implement src/config.py and directories**
- [x] **Step 4: Run test to verify it passes**
- [x] **Step 5: Git commit**

---

### Task 2: Data Layer & Dictionary Manager (`DictManager`)
- **Files**: `src/core/dict_manager.py`
- **Test**: `tests/test_dict_manager.py`
- **Models**: `CommonTerm(id: str, source: str, target: str, category: str, notes: str)`
- **Models**: `CharacterTerm(id: str, source: str, target: str, novel_tag: str, gender_role: str)`
- [x] **Step 1: Write test_dict_manager.py**
```python
def test_add_and_retrieve_common_term(temp_dict_manager):
    term = temp_dict_manager.add_common_term("đương gia hoa đán", "ngôi sao trụ cột")
    assert term.id == "co-1"
def test_add_and_retrieve_character_term(temp_dict_manager):
    term = temp_dict_manager.add_character_term("Gavin phong", "Giả Văn Phong", "Thiếu Long")
    assert term.id == "ch-1"
```
- [x] **Step 2: Implement CRUD operations with co-N and ch-N re-indexing**
- [x] **Step 3: Verify all tests pass**

---

### Task 3: High-Performance Replacer Engine (`ReplacerEngine`)
- **Files**: `src/core/replacer.py`
- **Test**: `tests/test_replacer.py`
- **Key Features**:
  - Longest Match First sorting
  - Factored word boundary regex `\b(?:...)\b`
  - Auto Title Case for `character_mappings` (`ch-`)
  - Sentence case preservation for `common_mappings` (`co-`)
  - Streaming line buffer for 50-70MB files
- [x] **Step 1: Write test_replacer.py**
```python
def test_auto_upcase_only_for_character_mappings():
    char_mappings = {"đường văn thanh": "đường văn thanh"}
    common_mappings = {"đương gia hoa đán": "ngôi sao số một"}
    engine = ReplacerEngine(common_mappings=common_mappings, character_mappings=char_mappings)
    res, _ = engine.replace_text("đường văn thanh gặp đương gia hoa đán. Đương gia hoa đán cười.")
    assert "Đường Văn Thanh" in res
    assert "ngôi sao số một." in res
    assert "Ngôi sao số một cười." in res
```
- [x] **Step 2: Implement ReplacerEngine with buffer streaming**
- [x] **Step 3: Benchmark 50.000 lines test**

---

### Task 4: Heuristic Scanner & Statistical Extractor (`NovelScanner`)
- **Files**: `src/core/scanner.py`
- **Test**: `tests/test_scanner.py`
- **Functions**:
  - `extract_proper_nouns(text: str, min_count: int)`: Trích xuất 2-4 gram viết hoa, lọc từ đầu câu thông thường và sub-ngrams.
  - `extract_abnormal_patterns(text: str, min_count: int)`: Trích xuất các cụm từ dị thường dịch thô.
- [x] **Step 1: Write test_scanner.py**
- [x] **Step 2: Implement NovelScanner with Vietnamese Unicode word boundaries**
- [x] **Step 3: Verify tests pass**

---

### Task 5: AI Assistant Integration (`AIAssistant`)
- **Files**: `src/core/ai_assistant.py`
- **Test**: `tests/test_ai_assistant.py`
- **Key Features**:
  - Batching 30 candidate words per API call
  - Gemini / OpenAI integration
  - JSON schema parsing with graceful fallback
- [x] **Step 1: Write test_ai_assistant.py with mocks**
- [x] **Step 2: Implement AIAssistant**
- [x] **Step 3: Verify tests pass**

---

### Task 6: Streamlit UI - Tab Quản lý Từ điển (`src/ui/tab_dict.py`)
- **Files**: `src/ui/tab_dict.py`
- **Key Features**:
  - 2 Subtabs: Từ phổ biến (co-) & Tên nhân vật (ch-)
  - `st.data_editor` sửa trực tiếp
  - Tìm kiếm theo từ khóa / mã ID
  - Lọc theo `novel_tag`
- [x] **Implement tab_dict.py**

---

### Task 7: Streamlit UI - Tab Quét & Lọc Từ Mới (`src/ui/tab_scan.py`)
- **Files**: `src/ui/tab_scan.py`
- **Key Features**:
  - Chọn file từ `txt/` hoặc tải file mới
  - Tùy chọn quét mẫu hoặc quét sâu
  - Bật/tắt AI phân tích & đề xuất
  - Bảng duyệt từ tương tác, nút lưu vào từ điển
- [x] **Implement tab_scan.py**

---

### Task 8: Streamlit UI - Tab Convert Truyện & App Entrypoint
- **Files**: `src/ui/tab_convert.py`, `src/ui/app.py`
- **Key Features**:
  - File picker (từ `txt/` hoặc upload)
  - Chọn từ điển áp dụng (common + character by tag)
  - Xem trước Diff 30 dòng đầu
  - Convert toàn bộ file, thanh tiến độ, thống kê thời gian và số từ thay thế
  - Nút tải file kết quả `[tên_truyện]_converted.txt`
- [x] **Implement tab_convert.py & app.py**

---

### Task 9: Scripts & Full End-to-End Integration
- **Files**: `scripts/import_initial_dict.py`, `run_app.bat`, `tests/test_integration.py`
- **Key Features**:
  - Nạp 91 nhân vật từ `dictionary.txt`
  - Script `run_app.bat` khởi chạy webapp 1-click
  - Toàn bộ 16/16 bài test vượt qua 100%
- [x] **Implement & Verify End-to-End**
