import pytest
import time
from pathlib import Path
from src.core.replacer import ReplacerEngine

def test_longest_match_first_precedence():
    # Longest match must win: "Trương Tử Kiến" before "Trương Tử"
    mappings = {
        "Trương Tử": "Trương Tử",
        "Trương Tử Kiến": "Trương Kiến",
        "đương gia hoa đán": "ngôi sao số một",
        "hoa đán": "tiểu thư",
    }
    engine = ReplacerEngine(mappings=mappings, case_sensitive=True)
    text = "Hôm nay Trương Tử Kiến gặp gỡ đương gia hoa đán."
    result, stats = engine.replace_text(text)
    
    assert result == "Hôm nay Trương Kiến gặp gỡ ngôi sao số một."
    assert stats["Trương Tử Kiến"] == 1
    assert "Trương Tử" not in stats
    assert stats["đương gia hoa đán"] == 1
    assert "hoa đán" not in stats

def test_replace_file_streaming(tmp_path):
    input_file = tmp_path / "input.txt"
    output_file = tmp_path / "output.txt"
    input_file.write_text("Trương Tử Kiến là một nhân vật. Gavin phong cũng vậy.\n", encoding="utf-8")
    
    mappings = {
        "Trương Tử Kiến": "Trương Kiến",
        "Gavin phong": "Giả Văn Phong"
    }
    engine = ReplacerEngine(mappings=mappings, case_sensitive=True)
    stats = engine.replace_file(input_file, output_file)
    
    converted_content = output_file.read_text(encoding="utf-8")
    assert converted_content == "Trương Kiến là một nhân vật. Giả Văn Phong cũng vậy.\n"
    assert stats["Trương Tử Kiến"] == 1
    assert stats["Gavin phong"] == 1

def test_empty_mappings_returns_original():
    engine = ReplacerEngine(mappings={})
    text = "Không có thay đổi."
    res, stats = engine.replace_text(text)
    assert res == text
    assert stats == {}

def test_large_content_performance(tmp_path):
    # Tạo một file 10MB và 500 từ thay thế
    mappings = {f"NhânVật_{i}": f"TenChuan_{i}" for i in range(500)}
    mappings["Trương Tử Kiến"] = "Trương Kiến"
    engine = ReplacerEngine(mappings=mappings, case_sensitive=True)
    
    line = "Hôm nay Trương Tử Kiến cùng NhânVật_1 và NhânVật_2 đi dạo trên phố.\n"
    input_file = tmp_path / "large_input.txt"
    output_file = tmp_path / "large_output.txt"
    
    # 50,000 dòng ~ 3.5 MB
    with open(input_file, "w", encoding="utf-8") as f:
        for _ in range(50000):
            f.write(line)
            
    start = time.time()
    stats = engine.replace_file(input_file, output_file)
    elapsed = time.time() - start
    
    assert elapsed < 5.0  # Phải xử lý dưới 5 giây
    assert stats["Trương Tử Kiến"] == 50000
    assert stats["NhânVật_1"] == 50000
    assert stats["NhânVật_2"] == 50000
