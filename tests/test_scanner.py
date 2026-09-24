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
