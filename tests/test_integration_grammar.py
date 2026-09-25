from src.core.scanner import NovelScanner
from src.core.replacer import ReplacerEngine

def test_full_pipeline_scanner_and_replacer():
    raw_text = """
    Lý tổng nhìn chằm chằm của nàng ánh mắt.
    Trần thiếu nói: 'Tập đoàn chúng ta không tiếp kẻ như tiểu tam.'
    Nàng cúi đầu, của hắn bàn tay nhẹ nhàng vỗ vai nàng.
    """
    scanner = NovelScanner()
    candidates = scanner.scan_text(raw_text, min_count=1)
    
    # Scanner tìm ra cấu trúc sở hữu ngược
    suggested = {c.phrase: c.suggested_target for c in candidates}
    assert "của nàng ánh mắt" in suggested
    assert suggested["của nàng ánh mắt"] == "ánh mắt của nàng"
    assert "của hắn bàn tay" in suggested
    assert suggested["của hắn bàn tay"] == "bàn tay của hắn"

    # Replacer tự động đảo ngữ mượt mà
    engine = ReplacerEngine(character_mappings={"trần thiếu": "Trần Thiếu"})
    converted, stats, count = engine.replace_text(raw_text, apply_grammar_fixes=True)
    assert "ánh mắt của nàng" in converted
    assert "bàn tay của hắn" in converted
    assert "Trần Thiếu" in converted
    assert count == 2
