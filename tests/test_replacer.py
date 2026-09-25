import pytest
import time
from pathlib import Path
from src.core.replacer import ReplacerEngine, title_case_vietnamese

def test_title_case_vietnamese():
    assert title_case_vietnamese("đường văn thanh") == "Đường Văn Thanh"
    assert title_case_vietnamese("lâm ngọc chi") == "Lâm Ngọc Chi"
    assert title_case_vietnamese("Gavin phong") == "Gavin Phong"

def test_auto_upcase_only_for_character_mappings():
    # ch- mappings: Tự động upcase tên riêng
    char_mappings = {
        "đường văn thanh": "đường văn thanh",  # Cố tình để chữ thường
        "lâm ngọc chi": "Lâm Ngọc Chi",
    }
    # co- mappings: Không tự động Title Case từng từ
    common_mappings = {
        "đương gia hoa đán": "ngôi sao số một",
    }
    engine = ReplacerEngine(common_mappings=common_mappings, character_mappings=char_mappings)
    
    text = "Hôm nay đường văn thanh và lâm ngọc chi gặp gỡ đương gia hoa đán. Đương gia hoa đán mỉm cười."
    result, stats, _ = engine.replace_text(text)
    
    # Nhân vật phải được tự động viết hoa toàn bộ từng từ:
    assert "Đường Văn Thanh" in result
    assert "Lâm Ngọc Chi" in result
    # Từ phổ biến không bị ép Title Case (không thành 'Ngôi Sao Số Một'):
    assert "ngôi sao số một." in result
    # Nhưng nếu đứng đầu câu thì được viết hoa chữ cái đầu:
    assert "Ngôi sao số một mỉm cười." in result

def test_longest_match_first_precedence():
    char_mappings = {
        "Trương Tử": "Trương Tử",
        "Trương Tử Kiến": "Trương Kiến",
    }
    common_mappings = {
        "đương gia hoa đán": "ngôi sao số một",
        "hoa đán": "tiểu thư",
    }
    engine = ReplacerEngine(common_mappings=common_mappings, character_mappings=char_mappings)
    text = "Hôm nay Trương Tử Kiến gặp gỡ đương gia hoa đán."
    result, stats, _ = engine.replace_text(text)
    
    assert result == "Hôm nay Trương Kiến gặp gỡ ngôi sao số một."
    assert stats["Trương Tử Kiến"] == 1
    assert "Trương Tử" not in stats
    assert stats["đương gia hoa đán"] == 1
    assert "hoa đán" not in stats

def test_replace_file_streaming(tmp_path):
    input_file = tmp_path / "input.txt"
    output_file = tmp_path / "output.txt"
    input_file.write_text("trương tử kiến là một nhân vật. gavin phong cũng vậy.\n", encoding="utf-8")
    
    char_mappings = {
        "trương tử kiến": "Trương Kiến",
        "gavin phong": "Giả Văn Phong"
    }
    engine = ReplacerEngine(character_mappings=char_mappings)
    stats = engine.replace_file(input_file, output_file)
    
    converted_content = output_file.read_text(encoding="utf-8")
    assert converted_content == "Trương Kiến là một nhân vật. Giả Văn Phong cũng vậy.\n"
    assert stats["trương tử kiến"] == 1
    assert stats["gavin phong"] == 1

def test_empty_mappings_returns_original():
    engine = ReplacerEngine()
    text = "Không có thay đổi."
    res, stats, _ = engine.replace_text(text)
    assert res == text
    assert stats == {}


def test_large_content_performance(tmp_path):
    mappings = {f"NhânVật_{i}": f"TenChuan_{i}" for i in range(500)}
    mappings["Trương Tử Kiến"] = "Trương Kiến"
    engine = ReplacerEngine(mappings=mappings)
    
    line = "Hôm nay Trương Tử Kiến cùng NhânVật_1 và NhânVật_2 đi dạo trên phố.\n"
    input_file = tmp_path / "large_input.txt"
    output_file = tmp_path / "large_output.txt"
    
    with open(input_file, "w", encoding="utf-8") as f:
        for _ in range(50000):
            f.write(line)
            
    start = time.time()
    stats = engine.replace_file(input_file, output_file)
    elapsed = time.time() - start
    
    assert elapsed < 30.0
    assert stats["Trương Tử Kiến"] == 50000
    assert stats["NhânVật_1"] == 50000
    assert stats["NhânVật_2"] == 50000

def test_replacer_with_grammar_fixes():
    mappings = {"long kiếm phi": "Long Kiếm Phi"}
    engine = ReplacerEngine(character_mappings=mappings)
    raw = "long kiếm phi nắm chặt của nàng bàn tay."
    output, stats, grammar_count = engine.replace_text(raw, apply_grammar_fixes=True)
    assert "Long Kiếm Phi" in output
    assert "bàn tay của nàng" in output
    assert grammar_count == 1

def test_replace_file_with_grammar_fixes(tmp_path):
    input_file = tmp_path / "input_grammar.txt"
    output_file = tmp_path / "output_grammar.txt"
    input_file.write_text("long kiếm phi nắm chặt của nàng bàn tay.\n", encoding="utf-8")
    mappings = {"long kiếm phi": "Long Kiếm Phi"}
    engine = ReplacerEngine(character_mappings=mappings)
    stats = engine.replace_file(input_file, output_file, apply_grammar_fixes=True)
    assert output_file.read_text(encoding="utf-8") == "Long Kiếm Phi nắm chặt bàn tay của nàng.\n"
    assert stats["long kiếm phi"] == 1
    assert stats["__grammar_fixes__"] == 1


