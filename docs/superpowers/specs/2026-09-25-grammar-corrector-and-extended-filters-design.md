# ĐẶC TẢ THIẾT KẾ: MODULE NẮN NGỮ PHÁP (GRAMMAR CORRECTOR) & MỞ RỘNG BỘ LỌC ĐÔ THỊ
*(Novel Translation Refiner - Grammar Corrector & Extended Filters Specification)*

- **Ngày tạo**: 2026-09-25
- **Trạng thái**: Đã phê duyệt (Approved by User)
- **Tác giả**: Antigravity & User

---

## 1. TỔNG QUAN VÀ MỤC TIÊU (OVERVIEW & GOALS)

### 1.1. Bối cảnh
Trong các tiểu thuyết convert Hán Việt (đặc biệt là thể loại Đô thị, Tổng tài, Nữ cường), văn bản thường gặp phải hai vấn đề lớn làm suy giảm trải nghiệm đọc:
1. **Lỗi Cấu trúc Sở hữu Ngược (Reverse Possession)**: Bản dịch máy thô giữ nguyên ngữ pháp tiếng Trung `[的]` dẫn đến cấu trúc "của [Chủ thể] [Đối tượng]" (ví dụ: *"của hắn bàn tay"*, *"của Lệ Na ánh mắt"*, *"của nàng váy ngắn"*). Đây là lỗi cú pháp động không thể giải quyết triệt để bằng từ điển tĩnh.
2. **Thiếu hụt từ vựng nhận diện chuyên biệt cho bối cảnh Đô thị**:
   - Thiếu các hậu tố/tiền tố danh xưng hiện đại (*Tổng, Đổng, Thiếu, Gia, Phu nhân, Bác sĩ, Đội trưởng, Giám đốc, Tiểu, Lão, A...*), dẫn đến nhận diện sai hoặc bỏ sót tên riêng.
   - Bắt nhầm các danh từ chỉ địa điểm/tổ chức viết hoa thành tên người (*Tập đoàn, Chung cư, Bệnh viện, Quán bar, Thư phòng...*).
   - Chưa xử lý được các từ lóng convert thô phổ biến (*kéo đen, nhục ti, hắc ti, phú nhị đại, tiểu tam, khuê mật, cẩu huyết, sa điêu, ngưu bức...*).

### 1.2. Mục tiêu cụ thể
1. **Xây dựng module `GrammarCorrector` độc lập**:
   - Cung cấp hàm `fix_reverse_possession(text)` sử dụng Regex chuẩn xác để đảo ngược cấu trúc sở hữu `"của [Ai] [Cái gì]"` thành `"[Cái gì] của [Ai]"`.
   - Có cơ chế guard clauses loại trừ các từ không phải danh từ sở hữu (như `của hắn là`, `của ta đã`, `của nàng không`...).
2. **Tích hợp kép (Dual Integration)**:
   - **Trong `NovelScanner`**: Tự động phát hiện các cấu trúc sở hữu ngược trong `extract_abnormal_patterns` và đề xuất bản sửa ngữ pháp chuẩn hóa vào `suggested_target`.
   - **Trong `ReplacerEngine`**: Thêm tùy chọn `enable_grammar_fixes: bool = True` để tự động nắn chỉnh ngữ pháp khi convert file truyện.
3. **Mở rộng Từ vựng & Bộ lọc**:
   - Cập nhật tiền tố / hậu tố danh xưng trong `NovelScanner`.
   - Mở rộng danh sách từ phi nhân vật trong `DEFAULT_NON_PERSON` và cập nhật trực tiếp vào file `filters/non_person.txt`.
   - Bổ sung các từ khóa dịch thô vào `ABNORMAL_KEYWORDS` và bảng ánh xạ dịch thuật mặc định `DEFAULT_TRANSLATION_MAP`.

---

## 2. KIẾN TRÚC & THÀNH PHẦN CHI TIẾT

### 2.1. Module mới `GrammarCorrector` (`src/core/grammar_corrector.py`)

- **Vị trí**: `src/core/grammar_corrector.py`
- **Class**: `GrammarCorrector`
- **Phương thức chính**:
  ```python
  class GrammarCorrector:
      NON_NOUN_WORDS = {
          "là", "có", "không", "chưa", "đã", "sẽ", "đang", "phải", "được", "bị",
          "vốn", "tại", "cho", "với", "như", "thì", "mà", "bởi", "vì", "đều",
          "cũng", "rất", "quá", "lắm", "hơn", "nhất"
      }
      
      @classmethod
      def fix_reverse_possession(cls, text: str) -> Tuple[str, int]:
          """
          Đảo ngữ cấu trúc sở hữu ngược:
          'của [Chủ thể] [Danh từ]' -> '[Danh từ] của [Chủ thể]'
          Trả về: (văn bản sau khi sửa, số lượng cụm từ đã sửa)
          """
  ```
- **Quy tắc Regex**:
  - Bắt đầu bằng từ `của` (không phân biệt hoa/thường).
  - Chủ thể: Đại từ nhân xưng (`hắn`, `nàng`, `y`, `thị`, `ta`, `ngươi`, `bọn họ`, `chúng nó`) HOẶC tên người viết hoa 1-3 từ (`[A-ZÀ-Ỹ][a-zà-ỹ]+...`).
  - Danh từ sở hữu: Cụm từ 1-3 âm tiết đi liền sau. Nếu âm tiết đầu tiên thuộc `NON_NOUN_WORDS`, bỏ qua không đảo.

### 2.2. Nâng cấp `NovelScanner` (`src/core/scanner.py`)

1. **Bổ sung Tiền tố & Hậu tố danh xưng**:
   - `HONORIFIC_SUFFIXES`: Thêm `tổng`, `đổng`, `viện trưởng`, `cục trưởng`, `sở trưởng`, `hiệu trưởng`, `thiếu`, `gia`, `phu nhân`, `mẫu`, `tôn`, `thần`, `đế`, `vương`.
   - `HONORIFIC_PREFIXES`: Thêm `tiểu`, `lão`, `đại`, `a`, `tổng giám đốc`, `giám đốc`, `đổng sự trưởng`, `thị trưởng`, `bí thư`, `cảnh sát`, `cảnh quan`, `đội trưởng`, `luật sư`.
2. **Bổ sung Danh sách Phi nhân vật (`DEFAULT_NON_PERSON`)**:
   - Thêm các địa điểm & tổ chức đô thị: `tập đoàn`, `biệt thự`, `chung cư`, `phòng khám`, `cục cảnh sát`, `đồn cảnh sát`, `quán bar`, `siêu thị`, `trung tâm thương mại`, `bệnh viện`, `y viện`, `phòng bệnh`, `phòng cấp cứu`, `phòng phẫu thuật`, `trường học`, `ký túc xá`, `giảng đường`, `căn tin`, `nhà vệ sinh`, `phòng tắm`, `phòng khách`, `phòng ngủ`, `phòng bếp`, `thư phòng`, `ban giám đốc`, `cổ đông`, `hội đồng`.
3. **Bổ sung Lỗi dịch máy (`ABNORMAL_KEYWORDS` & `DEFAULT_TRANSLATION_MAP`)**:
   - Thêm: `tính lãnh đạm`, `kéo đen`, `nhục ti`, `hắc ti`, `bạch ti`, `màu da tất chân`, `phú nhị đại`, `tinh nhị đại`, `quan nhị đại`, `tiểu tam`, `khuê mật`, `cẩu huyết`, `tóc húi cua`, `điện quang hỏa thạch`, `ngưu bức`, `trang bức`, `sa điêu`, `đỉnh lưu`, `tiểu thịt tươi`, `hot search`, `lên hot search`, `tọa kỵ`, `thượng phô`, `hạ phô`, `tắm rửa một cái`, `trảo phách`, `có ý tứ`, `không có ý tứ`, `đánh xe`, `ngồi xổm phòng giam`, `chụp đùi`, `hắc tuyến`, `đầu đầy hắc tuyến`.
   - Map các từ trên sang nghĩa tiếng Việt mượt mà trong `DEFAULT_TRANSLATION_MAP`.
4. **Tích hợp phát hiện cấu trúc sở hữu ngược trong `extract_abnormal_patterns`**:
   - Khi phát hiện mẫu `của [Chủ thể] [Danh từ]`, tự động tạo `ScannedCandidate` với:
     - `phrase`: cụm từ lỗi gốc (ví dụ: `"của hắn bàn tay"`).
     - `suggested_target`: cụm từ đã nắn chuẩn (ví dụ: `"bàn tay của hắn"`).
     - `candidate_type`: `"Cấu trúc sở hữu ngược"`.

### 2.3. Cập nhật Bộ lọc Tệp (`filters/non_person.txt`)

- Đồng bộ các từ phi nhân vật mới vào file `filters/non_person.txt` hiện hữu trên đĩa để người dùng nhận được ngay hiệu quả mà không cần xóa thư mục `filters/`.

### 2.4. Tích hợp `ReplacerEngine` & Giao diện Convert (`src/core/replacer.py`, `src/ui/tab_convert.py`)

1. **`ReplacerEngine.replace_text(text: str, apply_grammar_fixes: bool = False)`**:
   - Nếu `apply_grammar_fixes=True`, chạy `GrammarCorrector.fix_reverse_possession` sau khi đã thay thế từ điển (hoặc trước tùy luồng tối ưu).
   - Thống kê số lần sửa ngữ pháp vào kết quả trả về.
2. **Giao diện Convert (`src/ui/tab_convert.py`)**:
   - Bổ sung tùy chọn checkbox: `[x] Tự động sửa cấu trúc sở hữu ngược ("của hắn bàn tay" -> "bàn tay của hắn")` (mặc định bật).
   - Hiển thị thông báo sau khi convert: `Đã nắn chỉnh X cấu trúc sở hữu ngược`.

---

## 3. XỬ LÝ NGOẠI LỆ & TÍNH CHỊU LỖI (ERROR HANDLING)

1. **An toàn về câu chữ**: Nếu danh từ phía sau là từ phủ định/hư từ/động từ không thể đảo (thuộc `NON_NOUN_WORDS`), thuật toán giữ nguyên văn bản, không ép đổi.
2. **Bảo toàn viết hoa đầu câu**: Nếu từ `Của` viết hoa ở đầu câu, từ thay thế được đưa lên đầu câu sẽ được viết hoa chữ cái đầu và chữ `của` chuyển thành chữ thường:
   - *"Của hắn bàn tay rất ấm áp."* $\rightarrow$ *"Bàn tay của hắn rất ấm áp."*
3. **Hiệu năng xử lý**:
   - Sử dụng regex đã compiled trước (`re.compile`) kèm flags `re.UNICODE | re.IGNORECASE`.
   - Tốc độ xử lý hàng trăm nghìn từ dưới 0.2 giây.

---

## 4. KẾ HOẠCH KIỂM THỬ (TESTING & VERIFICATION)

1. **Unit Test cho `GrammarCorrector` (`tests/test_grammar_corrector.py`)**:
   - Test đảo ngữ với đại từ nhân xưng: `"của hắn bàn tay"` -> `"bàn tay của hắn"`.
   - Test đảo ngữ với tên riêng viết hoa: `"của Lệ Na ánh mắt"` -> `"ánh mắt của Lệ Na"`.
   - Test viết hoa đầu câu: `"Của nàng gương mặt xinh đẹp."` -> `"Gương mặt của nàng xinh đẹp."`.
   - Test từ chối đảo ngữ với hư từ: `"Của hắn là đồ giả"` -> giữ nguyên `"Của hắn là đồ giả"`.
2. **Unit Test nâng cấp `NovelScanner` (`tests/test_scanner.py`)**:
   - Test bắt tên với danh xưng mới: `Lý tổng`, `Trần thiếu`, `Tiểu Vương`, `A Tinh`.
   - Test lọc bỏ từ phi nhân vật mới: `Tập đoàn`, `Quán bar`, `Bệnh viện`.
   - Test đề xuất sửa cấu trúc sở hữu trong candidate scanner.
3. **Integration Test cho `ReplacerEngine`**:
   - Test luồng thay thế kết hợp tự động sửa ngữ pháp đảo ngữ.
4. **Kiểm thử hồi quy**:
   - Chạy toàn bộ 34 tests hiện tại bảo đảm đạt 100% PASS.
