import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    TXT_DIR: Path = BASE_DIR / "txt"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    
    COMMON_DICT_PATH: Path = DATA_DIR / "common_dict.json"
    CHARACTER_DICT_PATH: Path = DATA_DIR / "character_dict.json"
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.TXT_DIR.mkdir(parents=True, exist_ok=True)
