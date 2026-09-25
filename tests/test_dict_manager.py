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
    assert terms[0].id == "co-1"
    assert terms[0].source == "đương gia hoa đán"
    assert terms[0].target == "ngôi sao trụ cột"

def test_add_and_retrieve_character_term(temp_dict_manager):
    term = temp_dict_manager.add_character_term("Gavin phong", "Giả Văn Phong", "Thiếu Long")
    chars = temp_dict_manager.load_character_dict()
    assert len(chars) == 1
    assert chars[0].id == "ch-1"
    assert chars[0].source == "Gavin phong"
    assert chars[0].target == "Giả Văn Phong"
    assert chars[0].novel_tag == "Thiếu Long"

def test_sequential_ids(temp_dict_manager):
    term1 = temp_dict_manager.add_common_term("ba ba", "bố")
    term2 = temp_dict_manager.add_common_term("ma ma", "mẹ")
    terms = temp_dict_manager.load_common_dict()
    assert terms[0].id == "co-1"
    assert terms[1].id == "co-2"

def test_prevent_duplicate_source(temp_dict_manager):
    temp_dict_manager.add_common_term("ba ba", "bố")
    with pytest.raises(ValueError, match="already exists"):
        temp_dict_manager.add_common_term("ba ba", "cha")

def test_upsert_common_term(temp_dict_manager):
    term1, status1 = temp_dict_manager.upsert_common_term("lấy gã bác sĩ", "gả cho bác sĩ", "Lỗi dịch máy")
    assert status1 == "new"
    assert term1.id == "co-1"
    assert term1.target == "gả cho bác sĩ"

    # Upsert with different target -> updated
    term2, status2 = temp_dict_manager.upsert_common_term("lấy gã bác sĩ", "kết hôn với bác sĩ")
    assert status2 == "updated"
    assert term2.target == "kết hôn với bác sĩ"

    # Upsert with same target -> skipped
    term3, status3 = temp_dict_manager.upsert_common_term("lấy gã bác sĩ", "kết hôn với bác sĩ")
    assert status3 == "skipped"

    # Verify count remains 1
    terms = temp_dict_manager.load_common_dict()
    assert len(terms) == 1
    assert terms[0].target == "kết hôn với bác sĩ"

def test_upsert_character_term(temp_dict_manager):
    term1, status1 = temp_dict_manager.upsert_character_term("như tỷ", "như tỷ", novel_tag="Thiếu Long")
    assert status1 == "new"
    assert term1.id == "ch-1"
    # Target should be automatically Title Cased
    assert term1.target == "Như Tỷ"

    # Upsert with updated target
    term2, status2 = temp_dict_manager.upsert_character_term("như tỷ", "Liễu Ngọc Như", novel_tag="Thiếu Long")
    assert status2 == "updated"
    assert term2.target == "Liễu Ngọc Như"

    # Upsert identical -> skipped
    term3, status3 = temp_dict_manager.upsert_character_term("như tỷ", "Liễu Ngọc Như", novel_tag="Thiếu Long")
    assert status3 == "skipped"

def test_standardize_dictionaries(tmp_path):
    import unicodedata
    common_path = tmp_path / "common.json"
    char_path = tmp_path / "char.json"

    # Create raw data with NFD decomposed chars, mixed IDs, and duplicate source
    nfd_source = unicodedata.normalize('NFD', "thành thục mỹ phụ")
    common_data = [
        {"id": "random-99", "source": nfd_source, "target": "mỹ phụ chín chắn", "category": "Cụm từ Hán Việt"},
        {"id": "foo", "source": "thành thục mỹ phụ", "target": "mỹ phụ thành thục", "category": "Cụm từ Hán Việt"},
        {"id": "bar", "source": "ba ba", "target": "bố", "category": "Xưng hô"}
    ]
    char_data = [
        {"id": "xyz", "source": "long kiếm phi", "target": "long kiếm phi", "novel_tag": "Thiếu Long"},
        {"id": "abc", "source": "Long Kiếm Phi", "target": "Long Kiếm Phi", "novel_tag": "Thiếu Long"}
    ]
    import json
    common_path.write_text(json.dumps(common_data), encoding="utf-8")
    char_path.write_text(json.dumps(char_data), encoding="utf-8")

    mgr = DictManager(common_path=common_path, character_path=char_path)
    stats = mgr.standardize_dictionaries()

    assert stats["common_deduped"] == 1
    assert stats["character_deduped"] == 1

    clean_common = mgr.load_common_dict()
    assert len(clean_common) == 2
    assert clean_common[0].id == "co-1"
    assert clean_common[1].id == "co-2"
    # Ensure NFC
    assert clean_common[0].source == unicodedata.normalize('NFC', clean_common[0].source)

    clean_chars = mgr.load_character_dict()
    assert len(clean_chars) == 1
    assert clean_chars[0].id == "ch-1"
    assert clean_chars[0].target == "Long Kiếm Phi"

def test_parse_scanned_file(tmp_path):
    # Test JSON file
    json_path = tmp_path / "test_candidates.json"
    json_data = [
        {"id": "scan-1", "source": "Vĩ ca", "suggested_target": "Vĩ Ca", "category": "Tên nhân vật", "is_character": True},
        {"id": "scan-2", "source": "đương gia hoa đán", "suggested_target": "ngôi sao trụ cột", "category": "Lỗi dịch máy"}
    ]
    import json
    json_path.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    records = DictManager.parse_scanned_file(json_path)
    assert len(records) == 2
    assert records[0]["source"] == "Vĩ ca"

    # Test TXT review file with prompt header
    txt_path = tmp_path / "test_review.txt"
    txt_content = """=== DANH SÁCH TỪ SCAN ĐƯỢC CẦN BIÊN TẬP ===
Truyện: Thiếu Long
--- DỮ LIỆU CẦN XỬ LÝ ---
[
  {
    "id": "scan-1",
    "source": "Mị tỷ",
    "target": "Mị Tỷ",
    "type": "Tên nhân vật",
    "context": "Chu Ngọc Mị"
  }
]
"""
    txt_path.write_text(txt_content, encoding="utf-8")
    txt_records = DictManager.parse_scanned_file(txt_path)
    assert len(txt_records) == 1
    assert txt_records[0]["source"] == "Mị tỷ"

def test_import_records(temp_dict_manager):
    records = [
        {"source": "Như tỷ", "suggested_target": "Như Tỷ", "category": "Tên nhân vật", "is_character": True},
        {"source": "Vĩ ca", "target": "Vĩ Ca", "type": "Tên nhân vật"},
        {"source": "tiêu thụ bộ quản lí", "target": "trưởng phòng kinh doanh", "category": "Thuật ngữ"}
    ]
    res = temp_dict_manager.import_records(records, default_novel_tag="Thiếu Long")
    assert res["chars_added"] == 2
    assert res["common_added"] == 1

    chars = temp_dict_manager.load_character_dict()
    assert len(chars) == 2
    assert chars[0].id == "ch-1"
    assert chars[0].novel_tag == "Thiếu Long"

    common = temp_dict_manager.load_common_dict()
    assert len(common) == 1
    assert common[0].id == "co-1"

