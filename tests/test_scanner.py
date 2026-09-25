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

