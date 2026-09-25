import pytest
from src.core.scanner import NovelScanner

def test_extract_proper_nouns():
    sample_text = """
    Lâm Ngọc Chi nhìn Trương Tử Kiến rồi nói với Gavin phong.
    Trương Tử Kiến khẽ mỉm cười. Lâm Ngọc Chi cũng gật đầu.
    Hôm nay Trương Tử Kiến đi công tác cùng Gavin phong.
    """
    scanner = NovelScanner()
    candidates = scanner.extract_proper_nouns(sample_text, min_count=2)
    phrases = [c.phrase for c in candidates]
    
    assert "Trương Tử Kiến" in phrases
    assert "Lâm Ngọc Chi" in phrases
    assert "Gavin phong" in phrases

def test_extract_abnormal_patterns():
    sample_text = """
    Cô ấy từng tham gia đợi ảnh thị kịch nổi tiếng.
    Rất nhiều bộ đợi ảnh thị kịch được sản xuất năm đó.
    """
    scanner = NovelScanner()
    candidates = scanner.extract_abnormal_patterns(sample_text, min_count=2)
    phrases = [c.phrase for c in candidates]
    assert any("đợi ảnh thị kịch" in p for p in phrases)

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
    assert "gây ra dòng điện ảnh" in found_phrases or "truyền phát tin gây ra dòng điện ảnh" in found_phrases
    assert "lồi lõm có hứng thú" in found_phrases

def test_scan_file_streaming(tmp_path):
    file_path = tmp_path / "large_novel_mock.txt"
    content = """
    Lâm Ngọc Chi nhìn Trương Tử Kiến rồi nói với Gavin phong.
    Trương Tử Kiến khẽ mỉm cười. Lâm Ngọc Chi cũng gật đầu.
    Hôm nay Trương Tử Kiến đi công tác cùng Gavin phong.
    Cô ấy từng tham gia đợi ảnh thị kịch nổi tiếng.
    Rất nhiều bộ đợi ảnh thị kịch được sản xuất năm đó.
    """ * 10
    file_path.write_text(content, encoding="utf-8")

    scanner = NovelScanner()
    progress_records = []
    def on_progress(bytes_read, total_bytes, count):
        progress_records.append((bytes_read, total_bytes, count))

    candidates = scanner.scan_file_streaming(
        file_path=file_path,
        min_count=2,
        chunk_size_bytes=400,
        on_chunk_progress=on_progress
    )

    phrases = [c.phrase for c in candidates]
    assert "Trương Tử Kiến" in phrases
    assert "Lâm Ngọc Chi" in phrases
    assert len(progress_records) > 1

def test_scan_file_streaming_continuous_export(tmp_path):
    file_path = tmp_path / "large_novel_mock.txt"
    content = """
    Lâm Ngọc Chi nhìn Trương Tử Kiến rồi nói với Gavin phong.
    Trương Tử Kiến khẽ mỉm cười. Lâm Ngọc Chi cũng gật đầu.
    Hôm nay Trương Tử Kiến đi công tác cùng Gavin phong.
    Cô ấy từng tham gia đợi ảnh thị kịch nổi tiếng.
    Rất nhiều bộ đợi ảnh thị kịch được sản xuất năm đó.
    """ * 10
    file_path.write_text(content, encoding="utf-8")

    scanned_dir = tmp_path / "scanned"
    scanner = NovelScanner()
    save_records = []

    def on_save(candidates, json_path, txt_path):
        save_records.append((len(candidates), json_path))

    candidates = scanner.scan_file_streaming(
        file_path=file_path,
        min_count=2,
        chunk_size_bytes=400,
        scanned_dir=scanned_dir,
        novel_name="test_streaming_novel",
        save_interval_chunks=2,
        on_save_checkpoint=on_save
    )

    assert len(save_records) >= 1
    assert (scanned_dir / "test_streaming_novel_candidates.json").exists()
    assert (scanned_dir / "test_streaming_novel_review.txt").exists()
    assert any(c.phrase == "Trương Tử Kiến" for c in candidates)

def test_filter_false_positive_names():
    text = """
    Nàng mặc lấy Chu Ngọc mị ty chức áo ngủ, hai cái tuyết trắng đùi ngọc lộ ở bên ngoài.
    Nàng rốt cuộc biết cái gì là chỉ tiện uyên ương không tiện tiên.
    Long Kiếm Phi mang theo văn kiện túi đi vào thang máy.
    Long Kiếm Phi không nói gì thêm. Hắn nhìn sang bên cạnh.
    Trương Tử Kiến cười lớn một tiếng.
    """
    scanner = NovelScanner()
    candidates = scanner.extract_proper_nouns(text, min_count=1)
    found_phrases = {c.phrase for c in candidates}

    # Các tên nhân vật hợp lệ phải có
    assert "Long Kiếm Phi" in found_phrases
    assert "Chu Ngọc mị" in found_phrases
    assert "Trương Tử Kiến" in found_phrases

    # Các cụm rác tuyệt đối KHÔNG được có
    assert "Nàng mặc" not in found_phrases
    assert "Nàng rốt" not in found_phrases
    assert "Phi mang" not in found_phrases
    assert "Phi không" not in found_phrases
    assert "Hắn nhìn" not in found_phrases

def test_auto_create_and_load_filters(tmp_path):
    filters_dir = tmp_path / "filters"
    scanner = NovelScanner(filters_dir=filters_dir)
    
    assert (filters_dir / "blacklist.txt").exists()
    assert (filters_dir / "pronouns.txt").exists()
    assert (filters_dir / "trailing_stopwords.txt").exists()
    assert (filters_dir / "non_person.txt").exists()
    
    assert len(scanner.pronouns_and_starts) > 20
    assert len(scanner.trailing_stopwords) > 20
    assert len(scanner.non_person_words) > 5

def test_filters_comment_and_blank_handling(tmp_path):
    filters_dir = tmp_path / "filters"
    filters_dir.mkdir(parents=True, exist_ok=True)
    
    (filters_dir / "blacklist.txt").write_text("# Day la chu thich\n\n  Tu Cam  \n# Tu cam khac\n", encoding="utf-8")
    (filters_dir / "pronouns.txt").write_text("hắn\nnàng\n", encoding="utf-8")
    (filters_dir / "trailing_stopwords.txt").write_text("đi\nđến\n", encoding="utf-8")
    (filters_dir / "non_person.txt").write_text("bệnh viện\n", encoding="utf-8")
    
    scanner = NovelScanner(filters_dir=filters_dir)
    assert "tu cam" in scanner.blacklist
    assert "# Day la chu thich" not in scanner.blacklist
    assert len(scanner.blacklist) == 1

def test_blacklist_filtering(tmp_path):
    filters_dir = tmp_path / "filters"
    filters_dir.mkdir(parents=True, exist_ok=True)
    (filters_dir / "blacklist.txt").write_text("Huyền Vũ\n", encoding="utf-8")
    
    scanner = NovelScanner(filters_dir=filters_dir)
    text = "Huyền Vũ đã xuất hiện. Long Kiếm Phi cũng bước tới."
    candidates = scanner.scan_text(text, min_count=1)
    phrases = {c.phrase for c in candidates}
    
    assert "Long Kiếm Phi" in phrases
    assert "Huyền Vũ" not in phrases

def test_reload_filters(tmp_path):
    filters_dir = tmp_path / "filters"
    scanner = NovelScanner(filters_dir=filters_dir)
    assert "cấm thử nghiệm" not in scanner.blacklist
    
    # Ghi thêm từ mới vào blacklist.txt
    bl_file = filters_dir / "blacklist.txt"
    with open(bl_file, "a", encoding="utf-8") as f:
        f.write("\nCấm Thử Nghiệm\n")
        
    counts = scanner.reload_filters()
    assert "cấm thử nghiệm" in scanner.blacklist
    assert counts["blacklist"] >= 1

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



