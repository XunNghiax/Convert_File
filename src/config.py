import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    TXT_DIR: Path = BASE_DIR / "txt"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    SCANNED_DIR: Path = BASE_DIR / "scanned"
    FILTERS_DIR: Path = BASE_DIR / "filters"
    
    COMMON_DICT_PATH: Path = DATA_DIR / "common_dict.json"
    CHARACTER_DICT_PATH: Path = DATA_DIR / "character_dict.json"
    DEFAULT_IMPORT_PATH: Path = BASE_DIR / "import.json"

    BLACKLIST_FILTER_PATH: Path = FILTERS_DIR / "blacklist.txt"
    PRONOUNS_FILTER_PATH: Path = FILTERS_DIR / "pronouns.txt"
    TRAILING_STOPWORDS_FILTER_PATH: Path = FILTERS_DIR / "trailing_stopwords.txt"
    NON_PERSON_FILTER_PATH: Path = FILTERS_DIR / "non_person.txt"
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.TXT_DIR.mkdir(parents=True, exist_ok=True)
        self.SCANNED_DIR.mkdir(parents=True, exist_ok=True)
        self.FILTERS_DIR.mkdir(parents=True, exist_ok=True)

