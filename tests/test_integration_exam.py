import json
from pathlib import Path
from src.config import Config
from src.core.scanner import NovelScanner
from src.core.scan_exporter import ScanExporter

def test_scan_accuracy_on_exam_txt(tmp_path):
    config = Config()
    exam_file = config.BASE_DIR / "exam.txt"
    assert exam_file.exists(), "Cần có file exam.txt để kiểm thử"

    text = exam_file.read_text(encoding="utf-8", errors="replace")
    scanner = NovelScanner()
    candidates = scanner.scan_text(text, min_count=1)

    phrase_to_target = {c.phrase: c.suggested_target for c in candidates}
    phrase_types = {c.phrase: c.candidate_type for c in candidates}

    # 1. Kiểm tra nhận diện tên nhân vật và tự động chuẩn hóa Title Case
    assert "Liễu Ngọc như" in phrase_to_target
    assert phrase_to_target["Liễu Ngọc như"] == "Liễu Ngọc Như"
    assert "Chu Ngọc mị" in phrase_to_target
    assert phrase_to_target["Chu Ngọc mị"] == "Chu Ngọc Mị"
    assert "Khưu ngọc trinh" in phrase_to_target
    assert phrase_to_target["Khưu ngọc trinh"] == "Khưu Ngọc Trinh"
    assert "Long Kiếm Phi" in phrase_to_target

    # Kiểm tra nhận diện tên kèm danh xưng
    assert "Như tỷ" in phrase_to_target
    assert "Vĩ ca" in phrase_to_target

    # 2. Kiểm tra nhận diện lỗi dịch máy / dịch thô và cấu trúc Hán
    assert "hoàn toàn ăn mày" in phrase_types
    assert "lồi lõm có hứng thú" in phrase_types
    assert ("gây ra dòng điện ảnh" in phrase_types or "truyền phát tin gây ra dòng điện ảnh" in phrase_types)
    assert ("chuẩn bị một chút thủy" in phrase_types or "một chút thủy" in phrase_types)
    assert any("của hắn" in p for p in phrase_types)

    # 3. Kiểm tra lưu trữ file vào thư mục scanned
    scanned_test_dir = tmp_path / "scanned"
    json_path, txt_path = ScanExporter.auto_export_scanned(candidates, "exam_test", scanned_test_dir)
    assert json_path.exists()
    assert txt_path.exists()

    # Kiểm tra nội dung json
    saved_data = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(saved_data) == len(candidates)
    sources = {item["source"] for item in saved_data}
    assert "Liễu Ngọc như" in sources
    assert "hoàn toàn ăn mày" in sources

    # Kiểm tra nội dung txt
    txt_content = txt_path.read_text(encoding="utf-8")
    assert "exam_test" in txt_content
    assert "DANH SÁCH TỪ SCAN" in txt_content
