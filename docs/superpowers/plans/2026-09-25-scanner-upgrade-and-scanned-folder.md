# Nâng Cấp Thuật Toán Scanner & Lưu Trữ Thư Mục Scanned - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp độ chính xác của thuật toán scan trong `NovelScanner` (nhận diện tên riêng thông minh, lọc từ rác đầu câu, phát hiện cấu trúc đảo ngữ và lỗi dịch máy) đồng thời tự động lưu trữ kết quả quét vào thư mục riêng `scanned/` dưới 2 định dạng (JSON và TXT).

**Architecture:** Mở rộng `Config` với đường dẫn `SCANNED_DIR`. Bổ sung tập luật ngôn ngữ (họ phổ biến, danh xưng, liên từ/hư từ loại trừ, mẫu đảo ngữ Hán văn) vào `NovelScanner`. Xây dựng module xuất file `ScanExporter` tạo ra file JSON và file TXT chuẩn format `docs/prompt.md`. Tích hợp luồng lưu trữ và tải file trực tiếp trên giao diện Streamlit `tab_scan.py`.

**Tech Stack:** Python 3.12, Regex (re.UNICODE), Pydantic v2, Streamlit, Pytest.

## Global Constraints

- Mọi đường dẫn thư mục/tệp tuân thủ `pathlib.Path` và lấy gốc từ `Config.BASE_DIR`.
- Đảm bảo mã hóa `utf-8` với `errors="replace"` khi đọc/ghi file.
- Không làm vỡ cấu trúc và tính tương thích ngược của 16 bài kiểm thử hiện có.
- Trả về kết quả candidate kèm ngữ cảnh trọn vẹn (1-2 câu hoàn chỉnh, 40-200 ký tự).

---

### Task 1: Mở rộng Cấu hình với Thư mục `SCANNED_DIR`

**Files:**
- Modify: `src/config.py:10-23`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config.SCANNED_DIR: Path` (trỏ đến `[BASE_DIR]/scanned`)

- [ ] **Step 1: Cập nhật failing test trong `tests/test_config.py`**

```python
from src.config import Config

def test_config_paths_exist():
    config = Config()
    assert config.BASE_DIR.exists()
    assert config.DATA_DIR.name == "data"
    assert config.COMMON_DICT_PATH.name == "common_dict.json"
    assert config.CHARACTER_DICT_PATH.name == "character_dict.json"
    assert config.SCANNED_DIR.name == "scanned"
    assert config.SCANNED_DIR.exists()
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL với AttributeError (không có thuộc tính SCANNED_DIR).

- [ ] **Step 3: Cập nhật `src/config.py`**

Thêm `SCANNED_DIR: Path = BASE_DIR / "scanned"` và thêm `self.SCANNED_DIR.mkdir(parents=True, exist_ok=True)` trong `__init__`.

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add SCANNED_DIR to Config"
```

---

### Task 2: Nâng cấp Thuật toán Quét `NovelScanner`

**Files:**
- Modify: `src/core/scanner.py`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Produces:
  - `ScannedCandidate(phrase: str, count: int, candidate_type: str, sample_contexts: List[str], suggested_target: str = "")`
  - `NovelScanner.extract_proper_nouns(text: str, min_count: int = 2) -> List[ScannedCandidate]`
  - `NovelScanner.extract_abnormal_patterns(text: str, min_count: int = 2) -> List[ScannedCandidate]`
  - `NovelScanner.scan_text(text: str, min_count: int = 2) -> List[ScannedCandidate]`

- [ ] **Step 1: Viết test mở rộng trong `tests/test_scanner.py`**

```python
import pytest
from src.core.scanner import NovelScanner

def test_extract_proper_nouns_advanced():
    text = """
    Tuy nhiên, Long Kiếm Phi vẫn rất bình tĩnh.
    Hôm nay Liễu Ngọc như cùng Chu Ngọc mị đi đến thăm bạn học.
    Khưu ngọc trinh đứng ở cửa thang máy, Mị tỷ mỉm cười chào hỏi.
    Vĩ ca tại sao không đi cùng?
    Quả nhiên, Long Kiếm Phi phát hiện điều bất thường.
    """
    scanner = NovelScanner()
    candidates = scanner.extract_proper_nouns(text, min_count=1)
    found_phrases = {c.phrase: c.suggested_target for c in candidates}

    # Phải bắt được tên nhân vật chuẩn và tên viết thường âm sau kèm suggested Title Case
    assert "Long Kiếm Phi" in found_phrases
    assert "Liễu Ngọc như" in found_phrases
    assert found_phrases["Liễu Ngọc như"] == "Liễu Ngọc Như"
    assert "Chu Ngọc mị" in found_phrases
    assert found_phrases["Chu Ngọc mị"] == "Chu Ngọc Mị"
    assert "Khưu ngọc trinh" in found_phrases
    assert found_phrases["Khưu ngọc trinh"] == "Khưu Ngọc Trinh"
    assert "Mị tỷ" in found_phrases
    assert "Vĩ ca" in found_phrases

    # Không được bắt nhầm từ rác đầu câu
    assert "Tuy nhiên" not in found_phrases
    assert "Quả nhiên" not in found_phrases
    assert "Hôm nay" not in found_phrases

def test_extract_abnormal_patterns_advanced():
    text = """
    Của hắn chị dâu đứng bên cạnh, một cái sáu bảy tuổi đứa nhỏ đang khóc.
    Vài người đang ở cởi quần áo, chuẩn bị một chút thủy cứu người.
    Long Kiếm Phi mua hoàn toàn ăn mày và kẹo cao su.
    Trên xe đang truyền phát tin gây ra dòng điện ảnh.
    Nàng có thân hình lồi lõm có hứng thú.
    """
    scanner = NovelScanner()
    candidates = scanner.extract_abnormal_patterns(text, min_count=1)
    found_phrases = {c.phrase for c in candidates}

    assert "của hắn chị dâu" in found_phrases
    assert "một cái sáu bảy tuổi đứa nhỏ" in found_phrases
    assert "đang ở cởi quần áo" in found_phrases
    assert "chuẩn bị một chút thủy" in found_phrases or "một chút thủy" in found_phrases
    assert "hoàn toàn ăn mày" in found_phrases
    assert "gây ra dòng điện ảnh" in found_phrases
    assert "lồi lõm có hứng thú" in found_phrases
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_scanner.py -v`
Expected: FAIL (chưa có các tính năng nhận diện họ, danh xưng, cấu trúc đảo ngữ).

- [ ] **Step 3: Triển khai nâng cấp `src/core/scanner.py`**
  - Thêm trường `suggested_target: str = ""` vào `ScannedCandidate`.
  - Định nghĩa tập hợp họ phổ biến `VIET_CHINESE_SURNAMES`.
  - Định nghĩa danh xưng `TITLES_HONORIFICS` (`tỷ`, `ca`, `muội`, `bác sĩ`, `quản lí`...).
  - Mở rộng tập từ đầu câu `EXTENDED_START_WORDS` (> 80 từ).
  - Cải tiến logic `extract_proper_nouns`:
    - Quét cụm từ 2-4 âm tiết.
    - Xử lý tên chuẩn viết hoa và tên có họ viết hoa + âm sau viết thường (`Liễu Ngọc như`).
    - Bắt tên gắn với danh xưng (`Như tỷ`, `Vĩ ca`).
    - Lọc bỏ các từ nằm trong `EXTENDED_START_WORDS`.
  - Cải tiến logic `extract_abnormal_patterns`:
    - Regex tìm cấu trúc sở hữu ngược: `r'\bcủa\s+(?:hắn|nàng|ngươi|ta)\s+[a-zà-ỹA-ZÀ-Ỹ]+(?:\s+[a-zà-ỹA-ZÀ-Ỹ]+)?\b'`
    - Regex tìm lượng từ Hán: `r'\bmột\s+cái\s+[a-zà-ỹ0-9\-]+(?:\s+[a-zà-ỹ0-9\-]+){1,3}\s+đứa\s+nhỏ\b'` hoặc cấu trúc lượng từ tương đương.
    - Regex tìm vị ngữ Hán: `r'\bđang\s+ở\s+[a-zà-ỹ]+(?:\s+[a-zà-ỹ]+){1,2}\b'`
    - Bổ sung bộ từ khóa lỗi dịch máy mở rộng.
  - Cải tiến `_get_contexts` để trích xuất trọn vẹn câu chứa từ đó.

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_scanner.py -v`
Expected: Toàn bộ các test trong `test_scanner.py` đều PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/scanner.py tests/test_scanner.py
git commit -m "feat: upgrade NovelScanner with intelligent name & MT error detection"
```

---

### Task 3: Xây dựng Module Xuất Kết Quả Quét `ScanExporter`

**Files:**
- Create: `src/core/scan_exporter.py`
- Test: `tests/test_scan_exporter.py`

**Interfaces:**
- Produces:
  - `ScanExporter.export_to_json(candidates: List[ScannedCandidate], output_path: Path) -> Path`
  - `ScanExporter.export_to_prompt_txt(candidates: List[ScannedCandidate], novel_name: str, output_path: Path) -> Path`
  - `ScanExporter.auto_export_scanned(candidates: List[ScannedCandidate], novel_name: str, scanned_dir: Path) -> Tuple[Path, Path]`

- [ ] **Step 1: Viết test cho `ScanExporter` trong `tests/test_scan_exporter.py`**

```python
import json
from pathlib import Path
from src.core.scanner import ScannedCandidate
from src.core.scan_exporter import ScanExporter

def test_export_scanned_files(tmp_path):
    candidates = [
        ScannedCandidate(
            phrase="Liễu Ngọc như",
            suggested_target="Liễu Ngọc Như",
            count=15,
            candidate_type="Tên nhân vật",
            sample_contexts=["Long Kiếm Phi nhìn Liễu Ngọc như."]
        ),
        ScannedCandidate(
            phrase="hoàn toàn ăn mày",
            suggested_target="ô mai",
            count=2,
            candidate_type="Lỗi dịch máy",
            sample_contexts=["Mang theo đồ ăn vặt hoàn toàn ăn mày."]
        )
    ]
    scanned_dir = tmp_path / "scanned"
    json_path, txt_path = ScanExporter.auto_export_scanned(candidates, "exam", scanned_dir)

    assert json_path.exists()
    assert txt_path.exists()
    assert json_path.name == "exam_candidates.json"
    assert txt_path.name == "exam_review.txt"

    # Kiểm tra nội dung json
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["source"] == "Liễu Ngọc như"
    assert data[0]["suggested_target"] == "Liễu Ngọc Như"

    # Kiểm tra nội dung txt format prompt
    txt_content = txt_path.read_text(encoding="utf-8")
    assert "Liễu Ngọc như" in txt_content
    assert "hoàn toàn ăn mày" in txt_content
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_scan_exporter.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'src.core.scan_exporter').

- [ ] **Step 3: Triển khai `src/core/scan_exporter.py`**
  - Cung cấp phương thức `export_to_json`: tạo danh sách các dict có `id`, `source`, `suggested_target`, `category`, `is_character`, `count`, `context` và ghi ra JSON đẹp (`indent=2`, `ensure_ascii=False`).
  - Cung cấp phương thức `export_to_prompt_txt`: tạo file văn bản mở đầu bằng hướng dẫn biên tập và danh sách json các mục cần xử lý theo đúng tinh thần của `docs/prompt.md`.
  - Cung cấp `auto_export_scanned`: đảm bảo thư mục `scanned_dir` tồn tại, làm sạch tên file `novel_name`, xuất đồng thời 2 file và trả về tuple `(json_path, txt_path)`.

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_scan_exporter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/scan_exporter.py tests/test_scan_exporter.py
git commit -m "feat: add ScanExporter to save scanned candidates to json and review txt"
```

---

### Task 4: Tích hợp Tự Động Lưu và Tải Kết Quả vào Giao Diện UI

**Files:**
- Modify: `src/ui/tab_scan.py`

**Interfaces:**
- Consumes:
  - `Config.SCANNED_DIR`
  - `ScanExporter.auto_export_scanned`
  - `NovelScanner.scan_text`
- Produces:
  - Tự động lưu 2 file khi hoàn tất quét
  - Nút bấm tải xuống `[novel_name]_candidates.json` và `[novel_name]_review.txt`
  - Thông báo hiển thị vị trí file `scanned/`

- [ ] **Step 1: Cập nhật logic trong `src/ui/tab_scan.py`**
  - Import `ScanExporter`.
  - Sau khi `NovelScanner` và `AIAssistant` (nếu có) hoàn tất phân tích:
    - Tạo danh sách `ScannedCandidate` chứa `suggested_target`.
    - Gọi `json_path, txt_path = ScanExporter.auto_export_scanned(candidates, target_novel_tag, config.SCANNED_DIR)`.
    - Lưu đường dẫn `json_path`, `txt_path` vào `st.session_state`.
    - Hiển thị `st.success(f"💾 Đã tự động lưu kết quả scan vào: {json_path.name} và {txt_path.name} trong thư mục scanned/")`.
  - Dưới bảng duyệt từ hoặc khu vực kết quả, bổ sung 2 nút tải file:
    - `st.download_button("📥 Tải file JSON (Dữ liệu đầy đủ)", ...)`
    - `st.download_button("📥 Tải file TXT (Format Prompt AI)", ...)`

- [ ] **Step 2: Chạy kiểm thử toàn bộ test suite để đảm bảo không có xung đột**

Run: `.\venv\Scripts\python.exe -m pytest -v`
Expected: Tất cả bài test đều PASS.

- [ ] **Step 3: Commit**

```bash
git add src/ui/tab_scan.py
git commit -m "feat: integrate automatic scanned saving and download buttons in UI"
```

---

### Task 5: Kiểm Thử Toàn Diện (End-to-End Test) Trên File Mẫu `exam.txt`

**Files:**
- Create: `tests/test_integration_exam.py`

**Interfaces:**
- Consumes: `exam.txt`, `NovelScanner`, `ScanExporter`, `Config`
- Produces: Kiểm tra xác minh độ chính xác thực tế trên văn bản convert

- [ ] **Step 1: Viết test tích hợp `tests/test_integration_exam.py`**

```python
from pathlib import Path
from src.config import Config
from src.core.scanner import NovelScanner
from src.core.scan_exporter import ScanExporter

def test_scan_accuracy_on_exam_txt():
    config = Config()
    exam_file = config.BASE_DIR / "exam.txt"
    assert exam_file.exists(), "Cần có file exam.txt để kiểm thử"

    text = exam_file.read_text(encoding="utf-8", errors="replace")
    scanner = NovelScanner()
    candidates = scanner.scan_text(text, min_count=1)

    phrase_to_target = {c.phrase: c.suggested_target for c in candidates}
    phrase_types = {c.phrase: c.candidate_type for c in candidates}

    # 1. Kiểm tra nhận diện tên nhân vật và chuẩn hóa Title Case
    assert "Liễu Ngọc như" in phrase_to_target
    assert phrase_to_target["Liễu Ngọc như"] == "Liễu Ngọc Như"
    assert "Chu Ngọc mị" in phrase_to_target
    assert phrase_to_target["Chu Ngọc mị"] == "Chu Ngọc Mị"
    assert "Khưu ngọc trinh" in phrase_to_target
    assert phrase_to_target["Khưu ngọc trinh"] == "Khưu Ngọc Trinh"
    assert "dương ngọc khanh" in phrase_to_target or "Dương ngọc khanh" in phrase_to_target or "Dương phu nhân" in phrase_to_target
    assert "Long Kiếm Phi" in phrase_to_target

    # 2. Kiểm tra nhận diện lỗi dịch máy / dịch thô
    assert "hoàn toàn ăn mày" in phrase_types
    assert "gây ra dòng điện ảnh" in phrase_types or "truyền phát tin gây ra dòng điện ảnh" in phrase_types
    assert "lồi lõm có hứng thú" in phrase_types
    assert any("của hắn" in p for p in phrase_types)

    # 3. Kiểm tra xuất file vào thư mục scanned
    json_path, txt_path = ScanExporter.auto_export_scanned(candidates, "exam_test", config.SCANNED_DIR)
    assert json_path.exists()
    assert txt_path.exists()
```

- [ ] **Step 2: Chạy test để kiểm tra tính chính xác**

Run: `.\venv\Scripts\python.exe -m pytest tests/test_integration_exam.py -v`
Expected: PASS.

- [ ] **Step 3: Chạy toàn bộ test suite dự án**

Run: `.\venv\Scripts\python.exe -m pytest -v`
Expected: 100% tests PASS (tất cả các test cũ và mới).

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration_exam.py
git commit -m "test: add integration test on real exam.txt verifying scan accuracy"
```
