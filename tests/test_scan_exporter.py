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
    assert data[0]["is_character"] is True
    assert data[1]["source"] == "hoàn toàn ăn mày"
    assert data[1]["is_character"] is False

    # Kiểm tra nội dung txt format prompt
    txt_content = txt_path.read_text(encoding="utf-8")
    assert "Liễu Ngọc như" in txt_content
    assert "hoàn toàn ăn mày" in txt_content
    assert "DANH SÁCH TỪ SCAN" in txt_content
