import pytest
from pathlib import Path
from src.core.dict_manager import DictManager, CommonTerm, CharacterTerm

@pytest.fixture
def temp_dict_manager(tmp_path):
    common_path = tmp_path / "common.json"
    char_path = tmp_path / "char.json"
    common_path.write_text("[]", encoding="utf-8")
    char_path.write_text("[]", encoding="utf-8")
    return DictManager(common_path=common_path, character_path=char_path)

def test_add_and_retrieve_common_term(temp_dict_manager):
    term = temp_dict_manager.add_common_term("đương gia hoa đán", "ngôi sao trụ cột", "Dịch thô")
    terms = temp_dict_manager.load_common_dict()
    assert len(terms) == 1
    assert terms[0].id == 1
    assert terms[0].source == "đương gia hoa đán"
    assert terms[0].target == "ngôi sao trụ cột"

def test_add_and_retrieve_character_term(temp_dict_manager):
    term = temp_dict_manager.add_character_term("Gavin phong", "Giả Văn Phong", "Thiếu Long")
    chars = temp_dict_manager.load_character_dict()
    assert len(chars) == 1
    assert chars[0].id == 1
    assert chars[0].source == "Gavin phong"
    assert chars[0].target == "Giả Văn Phong"
    assert chars[0].novel_tag == "Thiếu Long"

def test_sequential_ids(temp_dict_manager):
    term1 = temp_dict_manager.add_common_term("ba ba", "bố")
    term2 = temp_dict_manager.add_common_term("ma ma", "mẹ")
    terms = temp_dict_manager.load_common_dict()
    assert terms[0].id == 1
    assert terms[1].id == 2

def test_prevent_duplicate_source(temp_dict_manager):
    temp_dict_manager.add_common_term("ba ba", "bố")
    with pytest.raises(ValueError, match="already exists"):
        temp_dict_manager.add_common_term("ba ba", "cha")
