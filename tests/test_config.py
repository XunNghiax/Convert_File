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
