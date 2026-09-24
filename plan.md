# KẾ HOẠCH THIẾT KẾ VÀ PHÁT TRIỂN ỨNG DỤNG CONVERT & CHUẨN HÓA TRUYỆN DỊCH THÔ
*(Novel Translation Refiner & Dictionary Builder)*

---

## 1. TỔNG QUAN DỰ ÁN

- **Mục tiêu**: Xây dựng công cụ chuyên dụng giúp đọc, chuẩn hóa và chuyển đổi các file truyện convert/dịch thô tiếng Trung (bản dịch máy, Hán Việt ngô nghê) sang tiếng Việt tự nhiên và chuẩn xác.
- **Điểm đột phá**:
  - Hỗ trợ xây dựng từ điển bán tự động thông qua cơ chế quét heuristic phát hiện tên riêng và từ ngữ bất thường, kết hợp AI (Gemini/OpenAI) để phân loại và đề xuất bản dịch chuẩn.
  - Quản lý 2 tầng từ điển rõ ràng: **Từ điển từ phổ biến** (dùng chung cho mọi truyện) và **Từ điển tên nhân vật** (kèm tag truyện để quản lý tập trung).
  - Engine thay thế siêu tốc (Longest-Match-First Trie / Regex Alternation) xử lý mượt mà các file truyện dung lượng lớn (10MB – 70MB+).
  - Giao diện trực quan bằng **Streamlit Web UI**, cho phép duyệt từ điển trực tiếp trên bảng, xem trước (diff preview) và tải file đã convert.

---

## 2. KIẾN TRÚC DỮ LIỆU & TỪ ĐIỂN

Hệ thống quản lý 2 file từ điển độc lập lưu dưới định dạng JSON (dễ đọc, dễ backup, import/export CSV/Excel):

### 2.1. Từ điển Từ phổ biến (`data/common_dict.json`)
Chứa các từ/cụm từ dịch thô ngô nghê, lỗi dịch máy, thuật ngữ chung.
- **Cấu trúc trường**:
  - `id`: Định danh duy nhất.
  - `source`: Từ gốc / từ thô (vd: *"đương gia hoa đán"*, *"lấy gã bác sĩ"*).
  - `target`: Từ thay thế chuẩn (vd: *"ngôi sao trụ cột"*, *"bác sĩ gả cho"*).
  - `category`: Phân loại (*"Lỗi dịch máy"*, *"Xưng hô"*, *"Thuật ngữ"*, *"Khác"*).
  - `notes`: Ghi chú ngữ cảnh (nếu có).

### 2.2. Từ điển Tên nhân vật (`data/character_dict.json`)
Chứa danh sách tên nhân vật, danh xưng riêng.
- **Cấu trúc trường**:
  - `id`: Định danh duy nhất.
  - `source`: Tên thô ban đầu (vd: *"Gavin phong"*, *"Chu phương băng"*, *"Tô Liên Xuân"*).
  - `target`: Tên chuẩn hóa (vd: *"Giả Văn Phong"*, *"Chu Phương Băng"*, *"Tô Liên Xuân"*).
  - `novel_tag`: Tag bộ truyện (vd: *"Thiếu Long phong lưu"*, *"Toàn chức"* hoặc *"Chung"*).
  - `gender_role`: Vai vế / giới tính (vd: *"Nam"*, *"Nữ"*, *"Thê tử"* - hỗ trợ AI nhận diện ngữ cảnh).

---

## 3. CÁC MODULE CỐT LÕI (CORE ENGINES)

### 3.1. Module Quét & Trích xuất (Scanner & Extractor)
- **Bộ lọc Heuristic (Không tốn token API, chạy siêu nhanh)**:
  - *Quét Tên riêng*: Dùng Regex nhận diện các cụm từ viết hoa liên tiếp từ 2-4 âm tiết (vd: `[A-ZÀ-Ỹ][a-zà-ỹ]+(\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,3}`).
  - *Quét Từ ngữ dị thường / Lỗi dịch máy*: 
    - Thống kê N-gram xuất hiện nhiều lần nhưng có cấu trúc bất thường (vd: lặp từ, từ nửa Hán nửa Anh như *"Gavin phong"*, từ chứa ký tự lạ).
    - So sánh với danh sách từ đã có trong từ điển để loại trừ những từ đã duyệt.
- **AI Classifier & Suggester (Gemini / OpenAI Batch Processing)**:
  - Gom các ứng viên (candidates) thành từng lô (batch 30 - 50 từ).
  - Prompt AI chuyên biệt để:
    1. Xác định từ đó là **Tên nhân vật** hay **Từ phổ biến**.
    2. Gợi ý từ tiếng Việt chuẩn hóa tương ứng.
    3. Đưa ra độ tin cậy (Confidence score).

### 3.2. Module Thay thế Tối ưu (High-Performance Replacer Engine)
- **Quy tắc thay thế**:
  - *Longest Match First*: Sắp xếp các cụm từ cần thay thế theo độ dài giảm dần để ưu tiên thay thế cụm từ dài trước (tránh trường hợp thay thế *"Trương Tử"* làm hỏng *"Trương Tử Kiến"*).
  - *Word Boundary & Case Matching*: Đảm bảo không thay thế nhầm các từ con nằm trong một từ khác.
- **Tối ưu file lớn**:
  - Đọc và xử lý theo chunk/dòng hoặc sử dụng `re.compile('|'.join(...))` tối ưu hóa để xử lý file 50MB - 70MB chỉ trong vài giây.

---

## 4. THIẾT KẾ GIAO DIỆN (STREAMLIT WEB UI)

Ứng dụng gồm 3 màn hình/tab chính:

```
+-----------------------------------------------------------------------+
|              TRÌNH CONVERT & CHUẨN HÓA TRUYỆN DỊCH THÔ                |
|  [Tab 1: Quét & Xây dựng từ điển]  [Tab 2: Quản lý từ điển]  [Tab 3: Convert truyện]  |
+-----------------------------------------------------------------------+
```

### Tab 1: Quét & Lọc Từ Mới (Scan & Build Dictionary)
1. **Nguồn văn bản**: Cho phép chọn file có sẵn trong thư mục `txt/` hoặc tải lên file `.txt` mới.
2. **Tùy chọn quét**:
   - Quét mẫu (N chương đầu hoặc toàn bộ file).
   - Ngưỡng tần suất xuất hiện tối thiểu (vd: >= 3 lần).
   - Bật/tắt AI hỗ trợ gợi ý từ dịch.
3. **Bảng duyệt tương tác (`st.data_editor`)**:
   - Cột: `Duyệt (Checkbox)` | `Từ gốc` | `Từ đề xuất` | `Loại từ` | `Tag truyện` | `Tần suất` | `Ngữ cảnh mẫu`.
   - Người dùng có thể chỉnh sửa trực tiếp trên bảng.
4. **Hành động**: Nút *"Lưu các từ đã chọn vào Từ điển"*.

### Tab 2: Quản lý Từ Điển (Dictionary Management)
1. **Chuyển đổi 2 bảng**: Bảng "Tên nhân vật" và Bảng "Từ phổ biến".
2. **Tính năng bảng**:
   - Bộ lọc tìm kiếm theo từ khóa hoặc Tag truyện.
   - Thêm dòng mới, sửa trực tiếp, xóa dòng.
   - Nút Import / Export file Excel (.xlsx) hoặc CSV.

### Tab 3: Convert Truyện & Xem Trước (Convert & Diff Preview)
1. **Chọn truyện cần convert** (từ `txt/` hoặc upload).
2. **Chọn phạm vi từ điển áp dụng**:
   - Luôn áp dụng: Từ điển từ phổ biến.
   - Chọn Tag truyện của Từ điển nhân vật (hoặc áp dụng tất cả).
3. **Chế độ xem trước (Preview Diff)**:
   - Hiển thị 5-10 đoạn văn mẫu so sánh song song Trước và Sau khi thay thế, highlight các từ đã được đổi màu xanh/vàng.
4. **Thực thi Convert**:
   - Thanh tiến độ (Progress bar).
   - Thống kê kết quả: Tổng số từ đã thay thế, thời gian xử lý.
   - Nút Tải file kết quả (`[tên_truyện]_converted.txt`) và tự động lưu vào thư mục `output/`.

---

## 5. CẤU TRÚC THƯ MỤC DỰ ÁN

```
Convert_File/
├── .env                       # Chứa GEMINI_API_KEY, OPENAI_API_KEY
├── requirements.txt           # Thư viện: streamlit, pandas, google-genai, openai, pytest
├── plan.md                    # Tài liệu kế hoạch & thiết kế chi tiết (file này)
├── data/
│   ├── common_dict.json       # Từ điển từ phổ biến
│   └── character_dict.json    # Từ điển tên nhân vật
├── src/
│   ├── __init__.py
│   ├── config.py              # Đọc biến môi trường, đường dẫn mặc định
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dict_manager.py    # CRUD và lưu trữ từ điển
│   │   ├── scanner.py         # Quét Regex, N-gram, thống kê tần suất
│   │   ├── ai_assistant.py    # Kết nối AI phân loại & gợi ý bản dịch
│   │   └── replacer.py        # Engine thay thế tối ưu theo Trie / Regex
│   └── ui/
│       ├── __init__.py
│       ├── app.py             # Entrypoint chính của Streamlit
│       ├── tab_scan.py        # UI quét & duyệt từ
│       ├── tab_dict.py        # UI quản lý từ điển
│       └── tab_convert.py     # UI convert & preview diff
├── tests/
│   ├── test_dict_manager.py
│   ├── test_scanner.py
│   └── test_replacer.py
├── txt/                       # Nơi chứa các file truyện thô
└── Converted/                    # Nơi lưu các file truyện đã hoàn thiện
```

---

## 6. LỘ TRÌNH TRIỂN KHAI (ROADMAP)

- **Bước 1: Core Engine & Data Storage**:
  - Viết `dict_manager.py`: Tạo cấu trúc lưu trữ và nạp `common_dict.json`, `character_dict.json`. Khởi tạo sẵn một số từ mẫu trích từ `dictionary.txt`.
  - Viết `replacer.py`: Engine thay thế tối ưu (Longest match first).
  - Viết Unit test xác thực độ chính xác và tốc độ xử lý trên file lớn.
- **Bước 2: Scanner & AI Classifier**:
  - Viết `scanner.py`: Trích xuất thực thể viết hoa (tên nhân vật) và thống kê cụm từ bất thường.
  - Viết `ai_assistant.py`: Tích hợp Gemini / OpenAI để phân loại và gợi ý từ thay thế.
- **Bước 3: Xây dựng Giao diện Streamlit**:
  - Dựng Tab Quản lý từ điển (`tab_dict.py`).
  - Dựng Tab Quét & Duyệt từ (`tab_scan.py`).
  - Dựng Tab Convert & Preview Diff (`tab_convert.py`).
  - Kết nối ứng dụng trong `app.py`.
- **Bước 4: Kiểm thử thực tế & Tối ưu**:
  - Thử nghiệm trên các file truyện thực tế trong thư mục `txt/` (10MB - 70MB).
  - Đo thời gian xử lý, đảm bảo không bị tràn bộ nhớ và kết quả thay thế chuẩn xác.
