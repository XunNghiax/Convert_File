import os
from pathlib import Path
from src.config import Config

def test_config_paths_exist():
    config = Config()
    assert config.BASE_DIR.exists()
    assert config.DATA_DIR.name == "data"
    assert config.COMMON_DICT_PATH.name == "common_dict.json"
    assert config.CHARACTER_DICT_PATH.name == "character_dict.json"
    assert config.TXT_DIR.exists()
    assert config.OUTPUT_DIR.exists()
    assert config.SCANNED_DIR.name == "scanned"
    assert config.SCANNED_DIR.exists()
    assert config.DEFAULT_IMPORT_PATH.name == "import.json"

def test_filter_paths():
    config = Config()
    assert config.FILTERS_DIR.name == "filters"
    assert config.BLACKLIST_FILTER_PATH.name == "blacklist.txt"
    assert config.PRONOUNS_FILTER_PATH.name == "pronouns.txt"
    assert config.TRAILING_STOPWORDS_FILTER_PATH.name == "trailing_stopwords.txt"
    assert config.NON_PERSON_FILTER_PATH.name == "non_person.txt"
    assert config.FILTERS_DIR.exists()

