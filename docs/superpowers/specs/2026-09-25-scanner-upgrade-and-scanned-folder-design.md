# ĐẶC TẢ THIẾT KẾ: NÂNG CẤP THUẬT TOÁN SCAN & LƯU KẾT QUẢ VÀO THƯ MỤC RIÊNG
*(Novel Translation Refiner - Smart Scanner & Scanned Storage Specification)*

- **Ngày tạo**: 2026-09-25
- **Trạng thái**: Bản thảo thiết kế hoàn chỉnh (Approved by User)
- **Tác giả**: Antigravity & User

---

## 1. TỔNG QUAN VÀ MỤC TIÊU (OVERVIEW & GOALS)

### 1.1. Bối cảnh
Chế độ Scan hiện tại trong `src/core/scanner.py` chỉ quét đơn thuần các cụm từ viết hoa 2-4 âm tiết và 16 từ khóa dịch thô cố định. Khi áp dụng vào các văn bản convert thực tế như `exam.txt`:
1. Bị bắt nhầm nhiều từ thông dụng đứng đầu câu (false positives).
2. Bỏ sót các tên riêng bị viết thường âm sau (như *"Liễu Ngọc như"*, *"Chu Ngọc mị"*, *"hạ ngọc hà"*).
3. Bỏ sót các danh xưng kèm tên nhân vật (*"Như tỷ"*, *"Vĩ ca"*, *"Mị tỷ"*, *"Mai quản lí"*).
4. Không tự động phát hiện được các cấu trúc đảo ngữ Hán văn (*"của hắn chị dâu"*, *"một cái sáu bảy tuổi đứa nhỏ"*).
5. Kết quả quét chỉ lưu tạm trong `st.session_state` mà chưa được lưu trữ bền vững vào một thư mục riêng để người dùng có thể quản lý, xem lại hoặc nạp vào AI xử lý độc lập.

### 1.2. Mục tiêu thiết kế
1. **Nâng cấp `NovelScanner`**:
   - Nhận diện chính xác tên nhân vật (kết hợp danh sách hơn 60 họ phổ biến, chuẩn hóa Title Case cho tên viết lỗi âm cuối, bắt tên kèm danh xưng).
   - Loại bỏ triệt để từ đầu câu thông dụng (bộ lọc ngữ pháp và ranh giới câu mở rộng).
   - Phát hiện các cấu trúc đảo ngữ Hán văn và mở rộng danh sách mẫu lỗi dịch máy đặc trưng (MT errors).
   - Trích xuất ngữ cảnh trọn vẹn (1-2 câu hoàn chỉnh) thay vì cắt xén cụt dòng.
2. **Xây dựng module lưu trữ kết quả (`scanned/`)**:
   - Thư mục lưu trữ chuyên biệt `scanned/` tại gốc dự án.
   - Tự động xuất 2 định dạng file cho mỗi lần scan:
     - `scanned/[tên_truyện]_candidates.json`: Dữ liệu có cấu trúc phục vụ tái sử dụng và nạp vào DictManager.
     - `scanned/[tên_truyện]_review.txt`: Văn bản chuẩn định dạng theo cấu trúc `docs/prompt.md` để người dùng có thể gửi ngay cho AI hoặc tự chỉnh sửa offline.
3. **Tích hợp giao diện UI (`tab_scan.py`)**:
   - Tự động lưu vào thư mục `scanned/` khi hoàn thành quét.
   - Thêm nút tải trực tiếp file JSON và TXT kết quả quét.
   - Thông báo rõ ràng vị trí file đã lưu trên hệ thống.

---

## 2. KIẾN TRÚC DỮ LIỆU & THƯ MỤC LƯU TRỮ

### 2.1. Cấu hình thư mục (`src/config.py`)
Bổ sung đường dẫn `SCANNED_DIR`:
```python
SCANNED_DIR: Path = BASE_DIR / "scanned"
```
Tự động khởi tạo thư mục này nếu chưa tồn tại (`self.SCANNED_DIR.mkdir(parents=True, exist_ok=True)`).

### 2.2. Định dạng file lưu trữ

#### A. File JSON: `scanned/[novel_name]_candidates.json`
Mỗi phần tử chứa:
```json
[
  {
    "id": "scan-1",
    "source": "Liễu Ngọc như",
    "suggested_target": "Liễu Ngọc Như",
    "category": "Tên nhân vật",
    "is_character": true,
    "count": 18,
    "context": "Long Kiếm Phi cùng Liễu Ngọc như tại hoàng hôn mới lên thời gian, đi đến ninh hoa vùng mới giải phóng..."
  },
  {
    "id": "scan-2",
    "source": "hoàn toàn ăn mày",
    "suggested_target": "ô mai",
    "category": "Lỗi dịch máy",
    "is_character": false,
    "count": 2,
    "context": "ta dẫn theo chút đồ ăn vặt đã quên lấy ra nữa rồi. Hoàn toàn ăn mày, kẹo cao su, chocolate..."
  }
]
```

#### B. File Text: `scanned/[novel_name]_review.txt`
Định dạng tương thích 100% với mẫu trong `docs/prompt.md`:
```text
=== DANH SÁCH TỪ SCAN ĐƯỢC CẦN BIÊN TẬP ===
Truyện: [novel_name]
Tổng số mục: [N] mục

[
  {
    "id": "scan-1",
    "source": "Liễu Ngọc như",
    "target": "Liễu Ngọc Như",
    "context": "Long Kiếm Phi cùng Liễu Ngọc như tại hoàng hôn..."
  },
  ...
]
```

---

## 3. THIẾT KẾ THUẬT TOÁN NÂNG CẤP (`NovelScanner`)

### 3.1. Danh sách Họ và Danh xưng tiếng Trung/Việt
- **Danh sách họ phổ biến (`VIET_CHINESE_SURNAMES`)**:
  - Gồm: `Nguyễn`, `Trần`, `Lê`, `Phạm`, `Hoàng`, `Huỳnh`, `Phan`, `Vũ`, `Võ`, `Đặng`, `Bùi`, `Đỗ`, `Hồ`, `Ngô`, `Dương`, `Lý`, `Liễu`, `Chu`, `Khưu`, `Hạ`, `Mai`, `Trương`, `Long`, `Tiêu`, `Lâm`, `Tần`, `Tạ`, `Cố`, `Thẩm`, `Giang`, `Bạch`, `Phương`, `Diệp`, `Tô`, `Tiết`, `Tống`, `Hàn`, `Lưu`, `Triệu`, `Vương`, `Tôn`, `Châu`, `Vũ`, `Đới`, `Phùng`, `Lục`, `Tiền`, `Quách`, `Khương`, `Ân`, `Thường`, `Cố`, `Mạnh`, `Kim`...
- **Danh sách danh xưng / chức danh (`TITLES_AND_HONORIFICS`)**:
  - Hậu tố: `tỷ`, `ca`, `muội`, `đệ`, `bá`, `thúc`, `tẩu`, `thần`, `sư`, `lão`.
  - Tiền tố: `bác sĩ`, `chủ nhiệm`, `quản lí`, `trưởng phòng`, `giáo sư`, `y tá`, `lão sư`, `phu nhân`, `tiểu thư`.

### 3.2. Thuật toán nhận diện Tên riêng (`extract_proper_nouns`)
1. **Trường hợp 1 (Tên chuẩn viết hoa)**:
   - Các cụm từ 2-4 âm tiết mà tất cả các từ đều viết hoa chữ cái đầu (`all(w[0].isupper() for w in words)`).
   - Kiểm tra ranh giới câu: Nếu cụm từ đứng ngay đầu câu, bắt buộc âm đầu tiên phải thuộc `VIET_CHINESE_SURNAMES` hoặc không nằm trong danh sách `EXTENDED_START_WORDS`.
2. **Trường hợp 2 (Tên bị viết thường âm sau - MT Inconsistent Casing)**:
   - Cụm từ 2-3 âm tiết có âm đầu tiên viết hoa và thuộc `VIET_CHINESE_SURNAMES`, nhưng âm thứ 2 hoặc 3 viết thường (ví dụ: `Liễu Ngọc như`, `Chu Ngọc mị`, `Khưu ngọc trinh`, `hạ ngọc hà` - nếu có danh xưng hoặc xuất hiện lặp lại).
   - Tự động chuẩn hóa `suggested_target` thành dạng Title Case (`Liễu Ngọc Như`).
3. **Trường hợp 3 (Tên gắn với Danh xưng)**:
   - Các mẫu: `[Tên] + [tỷ|ca|muội|đệ]` (như `Như tỷ`, `Mị tỷ`, `Vĩ ca`, `Trinh tỷ`).
   - Các mẫu: `[Chức danh] + [Tên]` (như `Mạnh bác sĩ`, `Mai quản lí`, `Dương phu nhân`).
4. **Loại trừ rác đầu câu mở rộng (`EXTENDED_START_WORDS`)**:
   - Mở rộng thêm hơn 100 từ/cụm từ hư từ, trạng từ, liên từ tiếng Việt hay đứng đầu câu như:
     - `Tuy nhiên`, `Nhưng mà`, `Bởi vì`, `Cho nên`, `Quả nhiên`, `Bỗng nhiên`, `Đột nhiên`, `Không bao lâu`, `Một lát sau`, `Trong chốc lát`, `Mặt khác`, `Sau đó`, `Trước đó`, `Lúc này`, `Hiện tại`, `Thậm chí`, `Dù sao`, `Ngược lại`, `Có thể`, `Không thể`, `Chẳng lẽ`, `Nhìn thấy`, `Chính văn`, `Chương`...

### 3.3. Thuật toán nhận diện Cấu trúc dịch thô & Lỗi dịch máy (`extract_abnormal_patterns`)
1. **Cấu trúc đảo ngữ Hán văn**:
   - `của (hắn|nàng|ngươi|ta) + [từ 1-2 âm tiết]` (ví dụ: `của hắn chị dâu`, `của hắn ngọc thể`, `của ngươi nghiêm ngọc doanh`).
   - `một cái + [số từ/tính từ] + [danh từ]` (ví dụ: `một cái sáu bảy tuổi đứa nhỏ`, `một cái cổ lão nông thôn`, `một cái tuyết trắng cánh tay`).
   - `đang ở + [động từ]` (ví dụ: `đang ở cởi quần áo`).
2. **Từ vựng dịch thô đặc thù**:
   - Bổ sung danh sách các từ dịch thô/lỗi dịch máy kinh điển:
     - `hoàn toàn ăn mày`, `truyền phát tin`, `gây ra dòng điện ảnh`, `một chút thủy`, `lồi lõm có hứng thú`, `nhũ màu trắng`, `cao dép lê`, `viết chữ đại lâu`, `thành phần tri thức`, `quay đầu dẫn`, `hạt giảng`, `đản sanh vu`, `dũ phát`, `nguy kiều`, `lò vi sóng lý`, `nồi cơm điện lý`, `đang lúc`, `chờ thông tri`, `mô phạm trượng phu`, `bất tranh khí`, `dĩ nhiên cũng làm là`...
3. **Lọc từ con và trùng lặp**:
   - Thuật toán giữ lại cụm từ dài nhất nếu tần suất của cụm từ con nằm trọn trong cụm từ dài.

### 3.4. Trích xuất ngữ cảnh (Context Extraction)
- Trích xuất toàn bộ câu chứa từ đó (từ ranh giới câu trước `[.!?\n]` đến ranh giới câu sau).
- Độ dài ngữ cảnh tối thiểu 40 ký tự, tối đa 200 ký tự, đảm bảo câu văn gãy gọn, không bị cắt xén lửng lơ.

---

## 4. MODULE LƯU TRỮ VÀ GIAO DIỆN (`src/ui/tab_scan.py`)

### 4.1. Luồng hoạt động (Workflow)
1. Người dùng chọn file từ `txt/` hoặc tải file mới lên.
2. Chọn cấu hình quét (Quét mẫu 50k / 500k ký tự hoặc Quét toàn bộ file; Tần suất tối thiểu; Bật/tắt AI).
3. Bấm **"🚀 Bắt đầu Quét & Phân tích"**:
   - Quét qua `NovelScanner` nâng cấp.
   - Chạy qua AI Assistant (nếu bật) hoặc gán nhãn Heuristic chuẩn hóa.
   - **Tự động lưu** ngay kết quả vào 2 file trong `scanned/`:
     - `scanned/[novel_stem]_candidates.json`
     - `scanned/[novel_stem]_review.txt`
   - Hiển thị thông báo thành công: `✅ Đã lưu kết quả quét vào thư mục scanned/!`
4. Hiển thị bảng kết quả tương tác (`st.data_editor`) cho phép chỉnh sửa, tích chọn để nạp vào từ điển như hiện tại.
5. Cung cấp 2 nút tải file:
   - 📥 **Tải file JSON kết quả**
   - 📥 **Tải file TXT định dạng Prompt AI**

---

## 5. KẾ HOẠCH KIỂM THỬ (TESTING & VERIFICATION)

1. **Unit Tests mới (`tests/test_scanner.py`)**:
   - Test nhận diện tên viết hoa lộn xộn (`Liễu Ngọc như` -> nhận diện và đề xuất `Liễu Ngọc Như`).
   - Test nhận diện tên đi kèm danh xưng (`Như tỷ`, `Mị tỷ`, `Vĩ ca`).
   - Test lọc bỏ các từ đầu câu thông dụng (`Tuy nhiên`, `Quả nhiên`, `Bỗng nhiên`...).
   - Test bắt các cấu trúc đảo ngữ Hán (`của hắn chị dâu`, `một cái sáu bảy tuổi đứa nhỏ`).
   - Test bắt các lỗi dịch máy đặc thù (`hoàn toàn ăn mày`, `gây ra dòng điện ảnh`).
2. **Integration Test trên `exam.txt`**:
   - Chạy quét trên file mẫu thực tế `exam.txt`.
   - Xác nhận nhận diện chính xác các nhân vật: `Long Kiếm Phi`, `Liễu Ngọc Như`, `Lưu Ngọc Cần`, `Chu Ngọc Mị`, `Khưu Ngọc Trinh`, `Hạ Ngọc Hà`, `Mai Ngọc Huyên`, `Dương Ngọc Khanh`, `Dương Ngọc Nhã`, `Nghiêm Ngọc Doanh`.
   - Xác nhận bắt được lỗi dịch thô: `hoàn toàn ăn mày`, `truyền phát tin gây ra dòng điện ảnh`, `chuẩn bị một chút thủy`, `lồi lõm có hứng thú`.
   - Xác nhận file được tạo đầy đủ trong thư mục `scanned/`.
3. **Toàn bộ 16 tests hiện tại + các test mới phải vượt qua 100%**.
