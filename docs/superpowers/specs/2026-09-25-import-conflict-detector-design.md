# Thiết Kế Kỹ Thuật: Bộ Phát Hiện & Xử Lý Xung Đột Khi Import (Import Conflict Detector)

## 1. Bối cảnh & Vấn đề

Trong quá trình dịch và chuẩn hóa tiểu thuyết, hiện tượng **Xung đột mở rộng cụm từ con (Subphrase Expansion Conflict)** xảy ra khi:
- Một cụm từ ngắn gồm $M$ từ (ví dụ: `Tạ quốc`, 2 từ) được người dùng hoặc bản dịch thô gán `target` thành $N$ từ với $N > M$ (ví dụ: `Tạ Quốc Hoa`, 3 từ - tức là tự tiện bù thêm chữ `"Hoa"`).
- Trong khi đó, `Tạ quốc` thực chất là họ và tên đệm của nhiều nhân vật khác nhau trong cùng tác phẩm (như `Tạ quốc hoa` $\rightarrow$ `Tạ Quốc Hoa`, `Tạ quốc vĩ` $\rightarrow$ `Tạ Quốc Vĩ`).

Hậu quả:
1. **Lặp từ khi chuyển đổi (Double Replacement Corruption)**: Khi văn bản chứa `"Tạ quốc hoa"`, nếu từ ngắn `"Tạ quốc"` bị thay thế trước (hoặc thay thế nhiều lần), nó trở thành `"Tạ Quốc Hoa hoa"` hoặc `"Tạ Quốc Hoa Hoa"`.
2. **Sai lệch nhân vật (Character Identity Collision)**: Khi văn bản nhắc đến nhân vật khác `"Tạ quốc vĩ"`, việc `"Tạ quốc"` tự động biến thành `"Tạ Quốc Hoa"` sẽ khiến tên nhân vật bị đổi sai thành `"Tạ Quốc Hoa vĩ"`.
3. **Hiện trạng từ điển hiện có**: Kiểm tra tự động trên `data/character_dict.json` phát hiện **19 mục** đang mắc lỗi mở rộng xung đột này (`ch-12: Tạ quốc -> Tạ Quốc Hoa`, `ch-14: Dương ngọc -> Dương Ngọc Nhàn`, `ch-26: Trương Tử -> Trương Tử Kiến`, `ch-32: Long đại -> Long Đại Ca`...).

---

## 2. Mục tiêu & Phạm vi

### Mục tiêu:
1. **Kiểm tra trùng lặp chính xác (Exact Duplicate Detection)**: Khi nạp dữ liệu (từ file JSON, TXT hoặc từ bảng duyệt Scan), tự động phát hiện các mục đã tồn tại trong từ điển (so sánh `source` không phân biệt hoa thường và chuẩn hóa Unicode NFC). Nếu đã có mục y hệt, tự động bỏ qua (`skipped`) để không sinh thêm bản ghi rác.
2. **Phát hiện & Chuẩn hóa Xung đột Mở rộng (Subphrase Expansion Conflict Resolution)**:
   - Phát hiện các trường hợp `len(target.split()) > len(source.split())` mà `source` là tiền tố / cụm từ con của một mục khác trong từ điển hoặc trong chính mẻ nạp.
   - **Tự động chuẩn hóa 1-1**: Đưa `target` về Title Case tương ứng với số từ của `source` (ví dụ `"Tạ quốc"` $\rightarrow$ `"Tạ Quốc"`, loại bỏ chữ `"Hoa"` dư thừa).
   - Đánh dấu trạng thái `normalized_expansion` trong báo cáo kết quả nạp.
3. **Làm sạch & Chuẩn hóa Từ điển Hiện tại (Audit & Cleanup Existing Dictionary)**:
   - Tích hợp vào `standardize_dictionaries()` để quét và sửa toàn bộ 19 mục đang bị lỗi trong `character_dict.json`, trả về thống kê số mục đã sửa xung đột.
4. **Tối ưu hóa nạp từ bảng duyệt Scan (`tab_scan.py`)**:
   - Thay thế vòng lặp gọi `add_character_term` / `add_common_term` (vốn đọc/ghi đĩa lặp lại N lần) bằng hàm nạp theo mẻ `import_records()`, đảm bảo lọc trùng và ngăn ngừa xung đột ngay khi bấm nút "Thêm các từ đã chọn vào Từ Điển".
5. **Zero Regression**: Đảm bảo toàn bộ 59 bài test hiện có tiếp tục PASS 100%.

### Phi mục tiêu:
- Không thay đổi thuật toán Longest Match First trong `ReplacerEngine` vì `ReplacerEngine` đã hoạt động tốt trên các mục từ điển chuẩn.

---

## 3. Thiết Kế Kiến Trúc & Chi Tiết Kỹ Thuật

### 3.1. Thuật toán Xử lý Xung đột Mở rộng (`DictManager.resolve_expansion_conflict`)

Phương thức tĩnh hoặc lớp trợ giúp trong `src/core/dict_manager.py`:

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
    
    Returns:
        (resolved_target, was_conflict_resolved)
    """
    source_words = source.strip().split()
    target_words = target.strip().split()
    
    # Chỉ xử lý khi target có nhiều từ hơn source
    if len(target_words) <= len(source_words):
        return target, False

    source_lower = source.strip().lower()
    # Kiểm tra xem source có phải là tiền tố (prefix) của một mục dài hơn nào khác không
    # Ví dụ: "tạ quốc" là tiền tố của "tạ quốc hoa" hoặc "tạ quốc vĩ"
    prefix_with_space = f"{source_lower} "
    is_subphrase = any(
        s != source_lower and (s.startswith(prefix_with_space) or f" {source_lower} " in f" {s} ")
        for s in all_known_sources
    )

    if is_subphrase:
        # Chuẩn hóa về Title Case 1-1 giữ nguyên số từ của source
        normalized_target = title_case_vietnamese(source)
        return normalized_target, True

    return target, False
```

### 3.2. Nâng cấp `DictManager.import_records`

Khi thực thi `import_records(records, default_novel_tag="Chung", auto_resolve_conflicts=True)`:
1. Tập hợp trước toàn bộ danh sách `source.lower()` từ:
   - Toàn bộ `char_terms` hiện có.
   - Toàn bộ `common_terms` hiện có.
   - Toàn bộ các bản ghi trong danh sách `records` đang nạp vào.
2. Duyệt từng bản ghi:
   - Chuẩn hóa Unicode NFC và làm sạch khoảng trắng.
   - Kiểm tra xem mục đã tồn tại trong từ điển chưa:
     - Nếu đã có cùng `source.lower()` và cùng `novel_tag` (với nhân vật) hoặc cùng `category`:
       - Nếu `target` giống hệt $\rightarrow$ Bỏ qua (`skipped`).
       - Nếu `target` khác $\rightarrow$ Cập nhật (`updated`).
     - Nếu là mục mới:
       - Nếu `is_char` và `auto_resolve_conflicts=True`: Gọi `resolve_expansion_conflict(source, target, all_known_sources)`.
       - Nếu phát hiện xung đột: Gán `target = resolved_target`, tăng bộ đếm `conflicts_resolved` và ghi nhận action `status: "normalized_expansion"`.
       - Nếu không xung đột: Thêm mới với target đề xuất ban đầu.
3. Trả về kết quả tổng hợp:
   - `total_records`: Tổng số bản ghi xử lý.
   - `chars_added`, `chars_updated`, `chars_skipped`.
   - `common_added`, `common_updated`, `common_skipped`.
   - `conflicts_resolved`: Số mục bị mở rộng sai lệch đã được tự động chuẩn hóa 1-1.

### 3.3. Nâng cấp `DictManager.standardize_dictionaries`

Mở rộng hàm dọn dẹp từ điển hiện tại:
1. Thu thập toàn bộ `sources` của `character_dict`.
2. Kiểm tra từng mục `c` trong `character_terms`:
   - Nếu `len(c.target.split()) > len(c.source.split())`:
     - Kiểm tra nếu `c.source.lower()` là tiền tố của mục khác trong từ điển.
     - Nếu có: Tự động chuẩn hóa `c.target = title_case_vietnamese(c.source)`.
     - Tăng biến đếm `conflicts_fixed`.
3. Khử trùng lặp case-insensitive + NFC.
4. Đánh lại ID tuần tự và lưu file.
5. Trả về thống kê: `{"common_deduped": ..., "character_deduped": ..., "conflicts_fixed": conflicts_fixed}`.

### 3.4. Tối ưu hóa `src/ui/tab_scan.py`

Tại nút "➕ Thêm các từ đã chọn vào Từ Điển" (dòng 207-231):
- Thay vì lặp `dict_manager.add_character_term(...)` từng dòng, chuyển sang đóng gói danh sách các dòng được chọn thành mảng `records`:
  ```python
  selected_records = [
      {
          "source": str(row["source"]).strip(),
          "target": str(row["target"]).strip(),
          "is_character": bool(row.get("is_character", False)),
          "category": str(row.get("category", "Chung")),
          "novel_tag": novel_tag
      }
      for _, row in edited_df.iterrows()
      if row.get("selected") and row.get("source") and row.get("target")
  ]
  res = dict_manager.import_records(selected_records, default_novel_tag=novel_tag)
  ```
- Hiển thị thông báo chi tiết: Đã thêm mới bao nhiêu, cập nhật bao nhiêu, bỏ qua bao nhiêu mục trùng lặp, và đã tự động nắn chuẩn bao nhiêu mục xung đột mở rộng.

---

## 4. Kế hoạch Kiểm Thử (Testing Plan)

### 4.1. Unit Tests (`tests/test_dict_manager.py`)
1. `test_resolve_expansion_conflict_detected_and_normalized`:
   - Kiểm tra `resolve_expansion_conflict("Tạ quốc", "Tạ Quốc Hoa", {"tạ quốc", "tạ quốc hoa", "tạ quốc vĩ"})` trả về `("Tạ Quốc", True)`.
   - Kiểm tra khi không có tiền tố hoặc số từ bằng nhau thì trả về nguyên dạng và `False`.
2. `test_import_records_skips_exact_duplicates`:
   - Nạp bản ghi đã có sẵn trong từ điển $\rightarrow$ `chars_skipped` tăng, không bị duplicate.
3. `test_import_records_resolves_expansion_conflicts`:
   - Nạp lô bản ghi gồm cả `"Tạ quốc"` $\rightarrow$ `"Tạ Quốc Hoa"` và `"Tạ quốc hoa"` $\rightarrow$ `"Tạ Quốc Hoa"` $\rightarrow$ `"Tạ quốc"` được tự động nắn thành `"Tạ Quốc"`.
4. `test_standardize_dictionaries_cleans_existing_conflicts`:
   - Tạo từ điển mẫu có `Tạ quốc -> Tạ Quốc Hoa` và `Tạ quốc hoa -> Tạ Quốc Hoa`. Chạy `standardize_dictionaries()` và kiểm tra target của `Tạ quốc` thành `Tạ Quốc`.

### 4.2. Toàn bộ Test Suite
- Chạy `.\venv\Scripts\python -m pytest` để đảm bảo 100% tests PASS và không có regression.
