# Kế Hoạch Triển Khai Module Nắn Ngữ Pháp (Grammar Corrector) & Mở Rộng Bộ Lọc Đô Thị

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng module `GrammarCorrector` nắn chỉnh tự động lỗi cấu trúc sở hữu ngược ("của hắn bàn tay" -> "bàn tay của hắn"), mở rộng từ vựng đô thị (danh xưng, phi nhân vật, từ điển dịch thô) cho `NovelScanner`, đồng bộ file `filters/non_person.txt` và tích hợp tùy chọn tự động nắn ngữ pháp vào `ReplacerEngine` khi Convert.

**Architecture:** Tạo module `src/core/grammar_corrector.py` độc lập với thuật toán Regex biên dịch trước; tích hợp vào `NovelScanner.extract_abnormal_patterns` để gợi ý sửa khi quét; mở rộng các hằng số từ vựng trong `NovelScanner` và đồng bộ vào `filters/`; mở rộng `ReplacerEngine.replace_text` với cờ `apply_grammar_fixes` và cập nhật UI Streamlit `tab_convert.py`.

**Tech Stack:** Python 3.12, Regex (re.UNICODE), Pytest, Streamlit.

## Global Constraints
- Tất cả tệp và chuỗi xử lý tuân thủ mã hóa UTF-8.
- Xử lý câu chữ an toàn: tuyệt đối không đảo ngữ khi từ đi liền sau là hư từ/liên từ/động từ không phải danh từ sở hữu (`NON_NOUN_WORDS`).
- Bảo tồn viết hoa đầu câu: nếu `Của` đứng đầu câu thì từ được đưa lên đầu phải được Title Case và `của` chuyển thành chữ thường.
- Đảm bảo 100% các bài test hiện có (34 tests) tiếp tục PASS (zero regression).

---

### Task 1: Xây dựng Module `GrammarCorrector`

**Files:**
- Create: `src/core/grammar_corrector.py`
- Test: `tests/test_grammar_corrector.py`

**Interfaces:**
- Produces:
  - `GrammarCorrector.NON_NOUN_WORDS: Set[str]`
  - `GrammarCorrector.REVERSE_POSSESSION_PATTERN: re.Pattern`
  - `GrammarCorrector.fix_reverse_possession(text: str) -> Tuple[str, int]`

- [ ] **Step 1: Viết test cho `GrammarCorrector` trong `tests/test_grammar_corrector.py`**

```python
import pytest
from src.core.grammar_corrector import GrammarCorrector

def test_fix_reverse_possession_pronouns():
    text = "Nàng gắt gao nắm lấy của hắn bàn tay."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 1
    assert fixed == "Nàng gắt gao nắm lấy bàn tay của hắn."

def test_fix_reverse_possession_proper_name():
    text = "Trong của Lệ Na ánh mắt hiện lên vẻ hoảng hốt."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 1
    assert fixed == "Trong ánh mắt của Lệ Na hiện lên vẻ hoảng hốt."

def test_fix_reverse_possession_sentence_start():
    text = "Của hắn bàn tay rất ấm áp."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 1
    assert fixed == "Bàn tay của hắn rất ấm áp."

def test_fix_reverse_possession_non_noun_guard():
    text = "Cái này vốn là của hắn là đồ giả, của ta không có."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 0
    assert fixed == text
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.\venv\Scripts\python -m pytest tests/test_grammar_corrector.py`
Expected: FAIL (ModuleNotFoundError: No module named 'src.core.grammar_corrector').

- [ ] **Step 3: Cài đặt `src/core/grammar_corrector.py`**

```python
import re
from typing import Tuple, Set

class GrammarCorrector:
    """
    Module xử lý và nắn chỉnh các lỗi ngữ pháp đặc thù trong văn bản convert Hán Việt.
    """
    # Các từ hư từ, trợ từ, liên từ, động từ không cấu thành danh từ sở hữu
    NON_NOUN_WORDS: Set[str] = {
        "là", "có", "không", "chưa", "đã", "sẽ", "đang", "phải", "được", "bị",
        "vốn", "tại", "cho", "với", "như", "thì", "mà", "bởi", "vì", "đều",
        "cũng", "rất", "quá", "lắm", "hơn", "nhất", "ngươi", "ta", "hắn", "nàng"
    }

    # Pattern bắt cấu trúc: [của] [Chủ thể] [Danh từ 1-3 âm tiết]
    REVERSE_POSSESSION_PATTERN = re.compile(
        r"(?i)\b(của)\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+)*|hắn|nàng|y|thị|ta|ngươi|bọn họ)\s+([a-zà-ỹA-ZÀ-Ỹ]+(?:\s+[a-zà-ỹA-ZÀ-Ỹ]+){0,2})\b",
        re.UNICODE
    )

    @classmethod
    def fix_reverse_possession(cls, text: str) -> Tuple[str, int]:
        """
        Nắn chỉnh cấu trúc sở hữu ngược:
        'của hắn bàn tay' -> 'bàn tay của hắn'
        'Của hắn bàn tay' -> 'Bàn tay của hắn'
        """
        if not text or "của " not in text.lower():
            return text, 0

        fix_count = 0

        def _replace_callback(match: re.Match) -> str:
            nonlocal fix_count
            cua_raw = match.group(1)      # 'của' hoặc 'Của'
            owner = match.group(2)        # 'hắn', 'Lệ Na', etc.
            noun_phrase = match.group(3)  # 'bàn tay'

            first_noun_word = noun_phrase.strip().split()[0].lower()
            if first_noun_word in cls.NON_NOUN_WORDS:
                return match.group(0)

            fix_count += 1
            # Xử lý viết hoa đầu câu nếu 'Của' viết hoa
            if cua_raw[0].isupper():
                # Viết hoa chữ đầu của cụm danh từ đưa lên
                noun_title = noun_phrase[0].upper() + noun_phrase[1:]
                return f"{noun_title} của {owner}"
            else:
                return f"{noun_phrase} {cua_raw.lower()} {owner}"

        result = cls.REVERSE_POSSESSION_PATTERN.sub(_replace_callback, text)
        return result, fix_count
```

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.\venv\Scripts\python -m pytest tests/test_grammar_corrector.py`
Expected: 4 passed.

- [ ] **Step 5: Commit thay đổi**

```bash
git add src/core/grammar_corrector.py tests/test_grammar_corrector.py
git commit -m "feat(grammar): add GrammarCorrector to fix reverse possession structures"
```

---

### Task 2: Mở Rộng Danh Xưng, Bộ Lọc Phi Nhân Vật & Lỗi Dịch Máy

**Files:**
- Modify: `src/core/scanner.py`
- Modify: `filters/non_person.txt`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Consumes: None
- Produces: Mở rộng `HONORIFIC_SUFFIXES`, `HONORIFIC_PREFIXES`, `DEFAULT_NON_PERSON`, `ABNORMAL_KEYWORDS`, `DEFAULT_TRANSLATION_MAP`

- [ ] **Step 1: Viết test kiểm tra từ khóa mới trong `tests/test_scanner.py`**

```python
def test_extended_urban_novel_vocabulary():
    text = """
    Lý tổng và Vương đổng vừa đến tập đoàn.
    Tiểu Vương cùng A Tinh đang ở quán bar gặp gỡ.
    Trần thiếu rất có ý tứ, ghét nhất tiểu tam và phú nhị đại.
    Nàng mặc nhục ti cùng hắc ti đi dạo phố.
    """
    scanner = NovelScanner()
    candidates = scanner.scan_text(text, min_count=1)
    phrases = {c.phrase for c in candidates}

    # Bắt được tên kèm danh xưng
    assert any("Lý tổng" in p for p in phrases)
    assert any("Vương đổng" in p for p in phrases)
    assert any("Trần thiếu" in p for p in phrases)
    assert any("Tiểu Vương" in p for p in phrases)
    assert any("A Tinh" in p for p in phrases)

    # Không bắt nhầm từ phi nhân vật
    assert "tập đoàn" not in phrases
    assert "quán bar" not in phrases

    # Bắt được lỗi dịch máy đô thị
    assert any("tiểu tam" in p for p in phrases)
    assert any("phú nhị đại" in p for p in phrases)
    assert any("nhục ti" in p for p in phrases)
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.\venv\Scripts\python -m pytest tests/test_scanner.py -k test_extended_urban_novel_vocabulary`
Expected: FAIL vì các từ khóa chưa có trong Scanner.

- [ ] **Step 3: Cập nhật `src/core/scanner.py` & `filters/non_person.txt`**

1. Trong `src/core/scanner.py`:
   - Bổ sung vào `HONORIFIC_SUFFIXES`: `"tổng", "đổng", "viện trưởng", "cục trưởng", "sở trưởng", "hiệu trưởng", "thiếu", "gia", "phu nhân", "mẫu", "tôn", "thần", "đế", "vương"`.
   - Bổ sung vào `HONORIFIC_PREFIXES`: `"tiểu", "lão", "đại", "a", "tổng giám đốc", "giám đốc", "đổng sự trưởng", "thị trưởng", "bí thư", "cảnh sát", "cảnh quan", "đội trưởng", "luật sư"`.
   - Bổ sung vào `DEFAULT_NON_PERSON`: `"tập đoàn", "biệt thự", "chung cư", "phòng khám", "cục cảnh sát", "đồn cảnh sát", "quán bar", "siêu thị", "trung tâm thương mại", "bệnh viện", "y viện", "phòng bệnh", "phòng cấp cứu", "phòng phẫu thuật", "trường học", "ký túc xá", "giảng đường", "căn tin", "nhà vệ sinh", "phòng tắm", "phòng khách", "phòng ngủ", "phòng bếp", "thư phòng", "ban giám đốc", "cổ đông", "hội đồng"`.
   - Bổ sung vào `ABNORMAL_KEYWORDS` và `DEFAULT_TRANSLATION_MAP` các mục từ trong spec (`tính lãnh đạm`, `kéo đen`, `nhục ti`, `hắc ti`, `bạch ti`, `màu da tất chân`, `phú nhị đại`, `tinh nhị đại`, `quan nhị đại`, `tiểu tam`, `khuê mật`, `cẩu huyết`, `tóc húi cua`, `điện quang hỏa thạch`, `ngưu bức`, `trang bức`, `sa điêu`, `đỉnh lưu`, `tiểu thịt tươi`, `hot search`, `lên hot search`, `tọa kỵ`, `thượng phô`, `hạ phô`, `tắm rửa một cái`, `trảo phách`, `có ý tứ`, `không có ý tứ`, `đánh xe`, `ngồi xổm phòng giam`, `chụp đùi`, `hắc tuyến`, `đầu đầy hắc tuyến`).
2. Ghi thêm các từ phi nhân vật mới vào tệp `filters/non_person.txt`.

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.\venv\Scripts\python -m pytest tests/test_scanner.py -k test_extended_urban_novel_vocabulary`
Expected: PASS.

- [ ] **Step 5: Commit thay đổi**

```bash
git add src/core/scanner.py filters/non_person.txt tests/test_scanner.py
git commit -m "feat(scanner,filters): expand honorifics, non-person words, and MT error vocabulary"
```

---

### Task 3: Tích Hợp Phát Hiện Cấu Trúc Sở Hữu Ngược Trong `NovelScanner`

**Files:**
- Modify: `src/core/scanner.py`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `GrammarCorrector.fix_reverse_possession`
- Produces: `ScannedCandidate` với `candidate_type="Cấu trúc sở hữu ngược"` và `suggested_target` tương ứng.

- [ ] **Step 1: Viết test cho scanner bắt cấu trúc sở hữu ngược trong `tests/test_scanner.py`**

```python
def test_scanner_detects_reverse_possession():
    text = "Hắn gắt gao giữ chặt lấy của nàng bàn tay, không chịu buông."
    scanner = NovelScanner()
    candidates = scanner.scan_text(text, min_count=1)
    rev_cands = [c for c in candidates if c.candidate_type == "Cấu trúc sở hữu ngược"]
    
    assert len(rev_cands) >= 1
    assert rev_cands[0].phrase == "của nàng bàn tay"
    assert rev_cands[0].suggested_target == "bàn tay của nàng"
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.\venv\Scripts\python -m pytest tests/test_scanner.py -k test_scanner_detects_reverse_possession`
Expected: FAIL vì scanner chưa phân loại `candidate_type="Cấu trúc sở hữu ngược"` và chưa tạo `suggested_target` nắn ngữ pháp.

- [ ] **Step 3: Cập nhật `NovelScanner.extract_abnormal_patterns`**

Import `GrammarCorrector` trong `src/core/scanner.py`.
Trong `extract_abnormal_patterns`:
Tìm các mẫu khớp với `GrammarCorrector.REVERSE_POSSESSION_PATTERN`.
Với mỗi cụm từ tìm được:
Kiểm tra xem từ đầu của danh từ có nằm trong `GrammarCorrector.NON_NOUN_WORDS` không.
Nếu hợp lệ, gán `candidate_type = "Cấu trúc sở hữu ngược"` và `suggested_target = GrammarCorrector.fix_reverse_possession(phrase)[0]`.

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.\venv\Scripts\python -m pytest tests/test_scanner.py -k test_scanner_detects_reverse_possession`
Expected: PASS.

- [ ] **Step 5: Commit thay đổi**

```bash
git add src/core/scanner.py tests/test_scanner.py
git commit -m "feat(scanner): integrate reverse possession detection with suggested correction"
```

---

### Task 4: Tích Hợp Tự Động Nắn Ngữ Pháp Vào `ReplacerEngine` & Giao Diện Convert

**Files:**
- Modify: `src/core/replacer.py`
- Modify: `src/ui/tab_convert.py`
- Test: `tests/test_replacer.py`

**Interfaces:**
- Consumes: `GrammarCorrector.fix_reverse_possession`
- Produces: `ReplacerEngine.replace_text(text: str, apply_grammar_fixes: bool = False) -> Tuple[str, Dict[str, int], int]`

- [ ] **Step 1: Viết test cho `ReplacerEngine` với tùy chọn `apply_grammar_fixes` trong `tests/test_replacer.py`**

```python
def test_replacer_with_grammar_fixes():
    mappings = {"long kiếm phi": "Long Kiếm Phi"}
    engine = ReplacerEngine(character_mappings=mappings)
    raw = "long kiếm phi nắm chặt của nàng bàn tay."
    output, stats, grammar_count = engine.replace_text(raw, apply_grammar_fixes=True)
    assert "Long Kiếm Phi" in output
    assert "bàn tay của nàng" in output
    assert grammar_count == 1
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

Run: `.\venv\Scripts\python -m pytest tests/test_replacer.py -k test_replacer_with_grammar_fixes`
Expected: FAIL vì `replace_text` chưa hỗ trợ tham số `apply_grammar_fixes`.

- [ ] **Step 3: Cập nhật `src/core/replacer.py` và `src/ui/tab_convert.py`**

1. Trong `src/core/replacer.py`:
   - Import `GrammarCorrector`.
   - Cập nhật chữ ký `replace_text(self, text: str, apply_grammar_fixes: bool = False) -> Tuple[str, Dict[str, int], int]`:
     - Nếu `apply_grammar_fixes=True`, chạy `text, grammar_count = GrammarCorrector.fix_reverse_possession(text)` sau khi thay thế từ điển.
     - Trả về `text, stats, grammar_count` (hoặc đảm bảo tương thích ngược khi chỉ unpack 2 giá trị nếu cần, bằng cách gán `stats["__grammar_fixes__"] = grammar_count` hoặc trả về tuple 3 phần tử).
2. Trong `src/ui/tab_convert.py`:
   - Thêm checkbox `st.checkbox("✨ Tự động sửa cấu trúc sở hữu ngược ('của hắn bàn tay' -> 'bàn tay của hắn')", value=True, key="fix_grammar_toggle")`.
   - Truyền giá trị checkbox vào `engine.replace_text(...)`.
   - Hiển thị thông báo kết quả: `st.info(f"✨ Đã tự động nắn chỉnh {grammar_fixes} cấu trúc sở hữu ngược.")`.

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `.\venv\Scripts\python -m pytest tests/test_replacer.py`
Expected: PASS toàn bộ các test của replacer.

- [ ] **Step 5: Commit thay đổi**

```bash
git add src/core/replacer.py src/ui/tab_convert.py tests/test_replacer.py
git commit -m "feat(replacer,ui): add automatic grammar fixing option during novel conversion"
```

---

### Task 5: Kiểm Thử Tích Hợp Toàn Diện & Đảm Bảo Zero Regression

**Files:**
- Create: `tests/test_integration_grammar.py`
- Test: Toàn bộ `tests/`

- [ ] **Step 1: Viết test tích hợp `tests/test_integration_grammar.py`**

```python
from src.core.scanner import NovelScanner
from src.core.replacer import ReplacerEngine

def test_full_pipeline_scanner_and_replacer():
    raw_text = """
    Lý tổng nhìn chằm chằm của nàng ánh mắt.
    Trần thiếu nói: 'Tập đoàn chúng ta không tiếp kẻ như tiểu tam.'
    Nàng cúi đầu, của hắn bàn tay nhẹ nhàng vỗ vai nàng.
    """
    scanner = NovelScanner()
    candidates = scanner.scan_text(raw_text, min_count=1)
    
    # Scanner tìm ra cấu trúc sở hữu ngược
    suggested = {c.phrase: c.suggested_target for c in candidates}
    assert "của nàng ánh mắt" in suggested
    assert suggested["của nàng ánh mắt"] == "ánh mắt của nàng"
    assert "của hắn bàn tay" in suggested
    assert suggested["của hắn bàn tay"] == "bàn tay của hắn"

    # Replacer tự động đảo ngữ mượt mà
    engine = ReplacerEngine(character_mappings={"trần thiếu": "Trần Thiếu"})
    converted, stats, count = engine.replace_text(raw_text, apply_grammar_fixes=True)
    assert "ánh mắt của nàng" in converted
    assert "bàn tay của hắn" in converted
    assert "Trần Thiếu" in converted
    assert count == 2
```

- [ ] **Step 2: Chạy test tích hợp**

Run: `.\venv\Scripts\python -m pytest tests/test_integration_grammar.py -v`
Expected: PASS.

- [ ] **Step 3: Chạy toàn bộ test suite dự án**

Run: `.\venv\Scripts\python -m pytest -v`
Expected: 100% tests PASS (38+ tests).

- [ ] **Step 4: Commit hoàn tất**

```bash
git add tests/test_integration_grammar.py
git commit -m "test: add integration test verifying grammar correction pipeline"
```
