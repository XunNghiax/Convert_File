# Import Conflict Detector & Dictionary Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng cơ chế tự động phát hiện và giải quyết xung đột khi nạp từ điển (Import Conflict Detector) nhằm ngăn chặn triệt để lỗi lặp từ ("Tạ Quốc Hoa hoa"), loại bỏ trùng lặp khi import, và dọn dẹp sạch sẽ 19 mục xung đột mở rộng hiện có trong `character_dict.json`.

**Architecture:** Mở rộng `DictManager` với thuật toán `resolve_expansion_conflict`, nâng cấp quy trình nạp mẻ `import_records` với bộ lọc trùng lặp và chuẩn hóa 1-1 cho các từ ngắn bị bù chữ. Tích hợp dọn dẹp tự động vào `standardize_dictionaries()`, và tối ưu luồng nạp từ bảng duyệt Scan trong `tab_scan.py`.

**Tech Stack:** Python 3.12, Pydantic, Streamlit, Pytest, Git.

## Global Constraints

- Tuân thủ mã hóa UTF-8 và chuẩn hóa Unicode NFC cho tất cả các chuỗi và tệp.
- Xử lý xung đột mở rộng theo nguyên tắc chuẩn hóa 1-1: nếu `source` gồm $M$ từ mà `target` có $N > M$ từ và `source` là tiền tố của từ khác trong từ điển, tự động đưa `target` về Title Case 1-1 (`title_case_vietnamese(source)`).
- Lọc trùng lặp chính xác: nếu `source.lower()` và `novel_tag` (hoặc `category`) đã tồn tại với cùng `target`, bỏ qua (`skipped`) không nhân đôi bản ghi.
- Đảm bảo 100% các bài test hiện có (59/59) tiếp tục PASS (Zero Regression).

---

### Task 1: Xây Dựng Thuật Toán Phát Hiện & Giải Quyết Xung Đột Mở Rộng (`resolve_expansion_conflict`)

**Files:**
- Modify: `src/core/dict_manager.py:20-50`
- Test: `tests/test_dict_manager.py`

**Interfaces:**
- Consumes: `title_case_vietnamese` từ `src.core.replacer`
- Produces: `DictManager.resolve_expansion_conflict(cls, source: str, target: str, all_known_sources: Set[str]) -> Tuple[str, bool]`

- [ ] **Step 1: Viết test thất bại (TDD) trong `tests/test_dict_manager.py`**

```python
def test_resolve_expansion_conflict():
    from src.core.dict_manager import DictManager
    known = {"tạ quốc hoa", "tạ quốc vĩ", "long kiếm phi"}
    
    # Trường hợp 1: Có xung đột mở rộng (Tạ quốc 2 từ -> Tạ Quốc Hoa 3 từ, và là tiền tố)
    resolved, was_conflict = DictManager.resolve_expansion_conflict("Tạ quốc", "Tạ Quốc Hoa", known)
    assert was_conflict is True
    assert resolved == "Tạ Quốc"

    # Trường hợp 2: Không có xung đột vì số từ bằng nhau (3 từ -> 3 từ)
    resolved, was_conflict = DictManager.resolve_expansion_conflict("Tạ quốc hoa", "Tạ Quốc Hoa", known)
    assert was_conflict is False
    assert resolved == "Tạ Quốc Hoa"

    # Trường hợp 3: Target nhiều từ hơn nhưng source KHÔNG phải là tiền tố của từ nào
    resolved, was_conflict = DictManager.resolve_expansion_conflict("Tiểu hoa", "Tiểu Mỹ Nhân Hoa", known)
    assert was_conflict is False
    assert resolved == "Tiểu Mỹ Nhân Hoa"
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `.\venv\Scripts\python -m pytest tests/test_dict_manager.py -k test_resolve_expansion_conflict`
Expected: FAIL với lỗi `AttributeError: type object 'DictManager' has no attribute 'resolve_expansion_conflict'`

- [ ] **Step 3: Cài đặt phương thức `resolve_expansion_conflict` trong `src/core/dict_manager.py`**

```python
    @classmethod
    def resolve_expansion_conflict(
        cls,
        source: str,
        target: str,
        all_known_sources: Set[str]
    ) -> Tuple[str, bool]:
        """
        Kiểm tra xem target có bị mở rộng thêm từ so với source không.
        Nếu có và source là tiền tố của ít nhất một từ khác trong all_known_sources,
        tự động hạ target về dạng Title Case 1-1 tương ứng với source.
        """
        source_clean = unicodedata.normalize('NFC', source.strip())
        target_clean = unicodedata.normalize('NFC', target.strip())
        source_words = source_clean.split()
        target_words = target_clean.split()

        if len(target_words) <= len(source_words) or not source_words:
            return target_clean, False

        source_lower = source_clean.lower()
        prefix_with_space = f"{source_lower} "
        is_subphrase = any(
            s != source_lower and (s.startswith(prefix_with_space) or f" {source_lower} " in f" {s} ")
            for s in all_known_sources
        )

        if is_subphrase:
            return title_case_vietnamese(source_clean), True

        return target_clean, False
```

- [ ] **Step 4: Chạy lại test để xác nhận test pass**

Run: `.\venv\Scripts\python -m pytest tests/test_dict_manager.py -k test_resolve_expansion_conflict`
Expected: PASS

- [ ] **Step 5: Commit code**

```bash
git add src/core/dict_manager.py tests/test_dict_manager.py
git commit -m "feat(dict): add resolve_expansion_conflict to prevent subphrase expansion bugs"
```

---

### Task 2: Nâng Cấp `DictManager.import_records` Với Bộ Lọc Trùng Lặp & Xử Lý Xung Đột

**Files:**
- Modify: `src/core/dict_manager.py:326-448`
- Test: `tests/test_dict_manager.py`

**Interfaces:**
- Consumes: `DictManager.resolve_expansion_conflict`
- Produces: `DictManager.import_records(records: List[dict], default_novel_tag: str = "Chung", auto_resolve_conflicts: bool = True) -> Dict[str, Any]`

- [ ] **Step 1: Viết test thất bại (TDD) trong `tests/test_dict_manager.py`**

```python
def test_import_records_with_conflict_and_deduplication(tmp_path):
    common_file = tmp_path / "common.json"
    char_file = tmp_path / "char.json"
    common_file.write_text("[]", encoding="utf-8")
    char_file.write_text(json.dumps([
        {"id": "ch-1", "source": "Tạ quốc hoa", "target": "Tạ Quốc Hoa", "novel_tag": "Thiếu Long"}
    ], ensure_ascii=False), encoding="utf-8")

    mgr = DictManager(common_file, char_file)

    records = [
        # Mục 1: Trùng lặp chính xác đã có sẵn -> phải skipped
        {"source": "Tạ quốc hoa", "target": "Tạ Quốc Hoa", "is_character": True, "novel_tag": "Thiếu Long"},
        # Mục 2: Xung đột mở rộng ("Tạ quốc" 2 từ -> "Tạ Quốc Hoa" 3 từ) -> phải tự động nắn về "Tạ Quốc"
        {"source": "Tạ quốc", "target": "Tạ Quốc Hoa", "is_character": True, "novel_tag": "Thiếu Long"},
        # Mục 3: Nhân vật mới chuẩn
        {"source": "Tạ quốc vĩ", "target": "Tạ Quốc Vĩ", "is_character": True, "novel_tag": "Thiếu Long"}
    ]

    res = mgr.import_records(records, default_novel_tag="Thiếu Long", auto_resolve_conflicts=True)
    assert res["chars_skipped"] == 1
    assert res["conflicts_resolved"] == 1
    assert res["chars_added"] == 2

    saved_chars = mgr.load_character_dict()
    char_map = {c.source: c.target for c in saved_chars}
    assert char_map["Tạ quốc"] == "Tạ Quốc" # Đã được nắn 1-1, không còn "Tạ Quốc Hoa"
    assert char_map["Tạ quốc hoa"] == "Tạ Quốc Hoa"
    assert char_map["Tạ quốc vĩ"] == "Tạ Quốc Vĩ"
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `.\venv\Scripts\python -m pytest tests/test_dict_manager.py -k test_import_records_with_conflict_and_deduplication`
Expected: FAIL với `KeyError: 'conflicts_resolved'` hoặc assertion lỗi.

- [ ] **Step 3: Cập nhật `import_records` trong `src/core/dict_manager.py`**

- Tập hợp `all_known_sources`:
  ```python
  all_known_sources = {c.source.lower() for c in char_terms}.union({t.source.lower() for t in common_terms})
  for r in records:
      if isinstance(r, dict):
          s = r.get("source") or r.get("phrase") or r.get("from") or ""
          if s:
              all_known_sources.add(str(s).strip().lower())
  ```
- Khởi tạo bộ đếm: `conflicts_resolved = 0`.
- Trong nhánh `is_char`:
  - Trước khi thêm mới, nếu `auto_resolve_conflicts`:
    ```python
    resolved_tgt, was_conflict = self.resolve_expansion_conflict(source, target_clean, all_known_sources)
    if was_conflict:
        target_clean = resolved_tgt
        conflicts_resolved += 1
    ```
  - Xử lý `status: "normalized_expansion"` nếu `was_conflict` khi thêm mới.
- Trả về `conflicts_resolved` trong dict kết quả.

- [ ] **Step 4: Chạy lại test để xác nhận test pass**

Run: `.\venv\Scripts\python -m pytest tests/test_dict_manager.py -k test_import_records_with_conflict_and_deduplication`
Expected: PASS

- [ ] **Step 5: Commit code**

```bash
git add src/core/dict_manager.py tests/test_dict_manager.py
git commit -m "feat(dict): enhance import_records with duplicate skipping and expansion conflict resolution"
```

---

### Task 3: Nâng Cấp `standardize_dictionaries` Để Dọn Sạch Toàn Bộ 19 Mục Xung Đột Hiện Có

**Files:**
- Modify: `src/core/dict_manager.py:206-263`
- Test: `tests/test_dict_manager.py`

**Interfaces:**
- Consumes: `DictManager.resolve_expansion_conflict`
- Produces: `standardize_dictionaries(self) -> Dict[str, Any]` trả về thêm `conflicts_fixed`

- [ ] **Step 1: Viết test thất bại (TDD) trong `tests/test_dict_manager.py`**

```python
def test_standardize_dictionaries_cleans_expansion_conflicts(tmp_path):
    common_file = tmp_path / "common.json"
    char_file = tmp_path / "char.json"
    common_file.write_text("[]", encoding="utf-8")
    char_file.write_text(json.dumps([
        {"id": "ch-1", "source": "Tạ quốc", "target": "Tạ Quốc Hoa", "novel_tag": "Thiếu Long"},
        {"id": "ch-2", "source": "Tạ quốc hoa", "target": "Tạ Quốc Hoa", "novel_tag": "Thiếu Long"},
        {"id": "ch-3", "source": "Dương ngọc", "target": "Dương Ngọc Nhàn", "novel_tag": "Thiếu Long"},
        {"id": "ch-4", "source": "Dương ngọc nhàn", "target": "Dương Ngọc Nhàn", "novel_tag": "Thiếu Long"}
    ], ensure_ascii=False), encoding="utf-8")

    mgr = DictManager(common_file, char_file)
    stats = mgr.standardize_dictionaries()

    assert stats["conflicts_fixed"] == 2
    chars = mgr.load_character_dict()
    char_map = {c.source: c.target for c in chars}
    assert char_map["Tạ quốc"] == "Tạ Quốc"
    assert char_map["Dương ngọc"] == "Dương Ngọc"
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `.\venv\Scripts\python -m pytest tests/test_dict_manager.py -k test_standardize_dictionaries_cleans_expansion_conflicts`
Expected: FAIL với `KeyError: 'conflicts_fixed'`

- [ ] **Step 3: Cập nhật `standardize_dictionaries` trong `src/core/dict_manager.py`**

- Tập hợp toàn bộ `all_sources = {c.source.lower() for c in char_terms}`.
- Duyệt qua từng `CharacterTerm`:
  ```python
  conflicts_fixed = 0
  for c in char_terms:
      resolved_tgt, was_conflict = cls.resolve_expansion_conflict(c.source, c.target, all_sources)
      if was_conflict:
          c.target = resolved_tgt
          conflicts_fixed += 1
  ```
- Trả về `conflicts_fixed` trong dictionary kết quả.
- Chạy hàm chuẩn hóa một lần trên dữ liệu thực tế `data/character_dict.json` để làm sạch 19 mục đang lỗi.

- [ ] **Step 4: Chạy test để xác nhận test pass**

Run: `.\venv\Scripts\python -m pytest tests/test_dict_manager.py -k test_standardize_dictionaries_cleans_expansion_conflicts`
Expected: PASS

- [ ] **Step 5: Làm sạch tệp dữ liệu `data/character_dict.json` và commit**

Run Python script gọi `mgr.standardize_dictionaries()` trên `data/character_dict.json`.
Kiểm tra git diff để thấy 19 mục (như Tạ quốc -> Tạ Quốc, Dương ngọc -> Dương Ngọc) đã được nắn chuẩn.
Commit:
```bash
git add src/core/dict_manager.py data/character_dict.json tests/test_dict_manager.py
git commit -m "fix(dict): clean up 19 subphrase expansion conflicts in character dictionary"
```

---

### Task 4: Cập Nhật UI Trong `tab_scan.py` & `tab_dict.py`

**Files:**
- Modify: `src/ui/tab_scan.py:207-232`
- Modify: `src/ui/tab_dict.py:11-17`

- [ ] **Step 1: Cập nhật `src/ui/tab_scan.py`**

Thay thế vòng lặp đơn lẻ bằng mảng `records` và gọi `dict_manager.import_records()`:
```python
        if st.button("➕ Thêm các từ đã chọn vào Từ Điển", type="primary"):
            novel_tag = st.session_state.get("scan_novel_tag", "Chung")
            selected_records = []
            for _, row in edited_df.iterrows():
                if row.get("selected") and row.get("source") and row.get("target"):
                    selected_records.append({
                        "source": str(row["source"]).strip(),
                        "target": str(row["target"]).strip(),
                        "is_character": bool(row.get("is_character", False)),
                        "category": str(row.get("category", "Chung")),
                        "novel_tag": novel_tag
                    })

            res = dict_manager.import_records(selected_records, default_novel_tag=novel_tag)
            msg_parts = [
                f"🎉 **Đã xử lý {res['total_records']} mục:**",
                f"+ Thêm mới: **{res['chars_added']}** nhân vật, **{res['common_added']}** từ phổ biến",
                f"+ Cập nhật: **{res['chars_updated']}** nhân vật, **{res['common_updated']}** từ phổ biến",
                f"+ Bỏ qua trùng: **{res['chars_skipped'] + res['common_skipped']}** mục"
            ]
            if res.get("conflicts_resolved", 0) > 0:
                msg_parts.append(f"+ Tự động chuẩn hóa 1-1 chống xung đột lặp từ: **{res['conflicts_resolved']}** mục")

            st.success(" | ".join(msg_parts))
            st.session_state["scan_results"] = []
            st.rerun()
```

- [ ] **Step 2: Cập nhật `src/ui/tab_dict.py`**

Hiển thị thêm số xung đột được sửa khi nhấn nút "✨ Thực hiện Chuẩn hóa ngay":
```python
            if st.button("✨ Thực hiện Chuẩn hóa ngay", key="btn_standardize"):
                stats = dict_manager.standardize_dictionaries()
                extra_msg = f", Đã khắc phục {stats.get('conflicts_fixed', 0)} mục xung đột mở rộng" if stats.get('conflicts_fixed', 0) > 0 else ""
                st.success(f"Đã chuẩn hóa thành công! Common: {stats['common_after']} từ (khử {stats['common_deduped']}), Characters: {stats['character_after']} từ (khử {stats['character_deduped']}){extra_msg}.")
                st.rerun()
```

- [ ] **Step 3: Kiểm tra cú pháp của `tab_scan.py` và `tab_dict.py`**

Run: `.\venv\Scripts\python -m py_compile src/ui/tab_scan.py src/ui/tab_dict.py`
Expected: 0 errors.

- [ ] **Step 4: Commit code**

```bash
git add src/ui/tab_scan.py src/ui/tab_dict.py
git commit -m "feat(ui): integrate batch conflict-aware import into tab_scan and report conflict fixes in tab_dict"
```

---

### Task 5: Kiểm Thử Toàn Diện & Đảm Bảo Zero Regression

**Files:**
- Modify: `tests/test_dict_manager.py`

- [ ] **Step 1: Chạy kiểm thử module `test_dict_manager.py`**

Run: `.\venv\Scripts\python -m pytest tests/test_dict_manager.py -v`
Expected: Tất cả bài test đều PASS.

- [ ] **Step 2: Chạy kiểm thử toàn bộ test suite dự án**

Run: `.\venv\Scripts\python -m pytest -v`
Expected: Toàn bộ 60+ test cases PASS (Zero Regression).

- [ ] **Step 3: Kiểm tra kịch bản end-to-end cho "Tạ quốc hoa"**

Viết thêm test trong `tests/test_dict_manager.py`:
- Nạp danh sách gồm `Tạ quốc -> Tạ Quốc Hoa`, `Tạ quốc hoa -> Tạ Quốc Hoa`, `Tạ quốc vĩ -> Tạ Quốc Vĩ`.
- Dùng `ReplacerEngine` chạy thay thế chuỗi: `"Tạ quốc hoa bước vào, phía sau là Tạ quốc vĩ, Tạ quốc cũng mỉm cười."`
- Assert chuỗi kết quả: `"Tạ Quốc Hoa bước vào, phía sau là Tạ Quốc Vĩ, Tạ Quốc cũng mỉm cười."`
- Assert hoàn toàn KHÔNG có chữ `"Hoa hoa"` hay `"Hoa vĩ"`.

- [ ] **Step 4: Commit test hoàn chỉnh**

```bash
git add tests/test_dict_manager.py
git commit -m "test: add comprehensive end-to-end test verifying absence of double word replacement"
```
