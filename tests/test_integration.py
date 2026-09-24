import pytest
from pathlib import Path
from src.core.dict_manager import DictManager
from src.core.scanner import NovelScanner
from src.core.replacer import ReplacerEngine

def test_full_pipeline_end_to_end(tmp_path):
    # 1. Setup mock input novel text
    input_text = """
    Lâm Ngọc Chi nhìn Trương Tử Kiến một cách giận dữ.
    Hôm nay đương gia hoa đán đến tham dự buổi tiệc.
    Trương Tử Kiến khẽ cười nhạt.
    """
    input_file = tmp_path / "raw_novel.txt"
    output_file = tmp_path / "converted_novel.txt"
    input_file.write_text(input_text, encoding="utf-8")

    # 2. Scan candidates
    scanner = NovelScanner()
    candidates = scanner.scan_text(input_text, min_count=1)
    extracted_phrases = {c.phrase for c in candidates}
    assert "Trương Tử Kiến" in extracted_phrases
    assert "Lâm Ngọc Chi" in extracted_phrases

    # 3. Add to DictManager
    common_file = tmp_path / "common.json"
    char_file = tmp_path / "char.json"
    dict_mgr = DictManager(common_path=common_file, character_path=char_file)
    dict_mgr.add_character_term("Trương Tử Kiến", "Trương Kiến Minh", "TestNovel")
    dict_mgr.add_common_term("đương gia hoa đán", "ngôi sao trụ cột", "Dịch thô")

    # 4. Run Replacer
    mappings = {t.source: t.target for t in dict_mgr.load_common_dict()}
    mappings.update({c.source: c.target for c in dict_mgr.load_character_dict()})
    
    engine = ReplacerEngine(mappings=mappings, case_sensitive=True)
    stats = engine.replace_file(input_file, output_file)

    converted_content = output_file.read_text(encoding="utf-8")
    assert "Trương Kiến Minh" in converted_content
    assert "ngôi sao trụ cột" in converted_content
    assert "Trương Tử Kiến" not in converted_content
    assert "đương gia hoa đán" not in converted_content
    assert stats["Trương Tử Kiến"] == 2
    assert stats["đương gia hoa đán"] == 1
