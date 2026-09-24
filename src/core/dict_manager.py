import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

class CommonTerm(BaseModel):
    id: int = 0
    source: str
    target: str
    category: str = "Chung"
    notes: str = ""

class CharacterTerm(BaseModel):
    id: int = 0
    source: str
    target: str
    novel_tag: str = "Chung"
    gender_role: str = ""

class DictManager:
    def __init__(self, common_path: Path, character_path: Path):
        self.common_path = common_path
        self.character_path = character_path
        self._ensure_files()

    def _ensure_files(self):
        if not self.common_path.exists():
            self.common_path.parent.mkdir(parents=True, exist_ok=True)
            self.common_path.write_text("[]", encoding="utf-8")
        if not self.character_path.exists():
            self.character_path.parent.mkdir(parents=True, exist_ok=True)
            self.character_path.write_text("[]", encoding="utf-8")

    def load_common_dict(self) -> List[CommonTerm]:
        content = self.common_path.read_text(encoding="utf-8").strip() or "[]"
        data = json.loads(content)
        # Tự động gán id tuần tự nếu dữ liệu cũ chưa có hoặc là chuỗi
        terms = []
        for idx, item in enumerate(data, start=1):
            if not isinstance(item.get("id"), int) or item.get("id") <= 0:
                item["id"] = idx
            terms.append(CommonTerm(**item))
        return terms

    def save_common_dict(self, terms: List[CommonTerm]) -> None:
        # Đánh số thứ tự tăng dần liên tục: 1, 2, 3...
        for idx, t in enumerate(terms, start=1):
            t.id = idx
        data = [t.model_dump() for t in terms]
        self.common_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_character_dict(self) -> List[CharacterTerm]:
        content = self.character_path.read_text(encoding="utf-8").strip() or "[]"
        data = json.loads(content)
        chars = []
        for idx, item in enumerate(data, start=1):
            if not isinstance(item.get("id"), int) or item.get("id") <= 0:
                item["id"] = idx
            chars.append(CharacterTerm(**item))
        return chars

    def save_character_dict(self, terms: List[CharacterTerm]) -> None:
        # Đánh số thứ tự tăng dần liên tục: 1, 2, 3...
        for idx, t in enumerate(terms, start=1):
            t.id = idx
        data = [t.model_dump() for t in terms]
        self.character_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_common_term(self, source: str, target: str, category: str = "Chung", notes: str = "") -> CommonTerm:
        source_clean = source.strip()
        terms = self.load_common_dict()
        if any(t.source.lower() == source_clean.lower() for t in terms):
            raise ValueError(f"Term '{source_clean}' already exists in common dictionary.")
        new_term = CommonTerm(id=len(terms) + 1, source=source_clean, target=target.strip(), category=category, notes=notes)
        terms.append(new_term)
        self.save_common_dict(terms)
        return new_term

    def add_character_term(self, source: str, target: str, novel_tag: str = "Chung", gender_role: str = "") -> CharacterTerm:
        source_clean = source.strip()
        chars = self.load_character_dict()
        if any(c.source.lower() == source_clean.lower() and c.novel_tag == novel_tag for c in chars):
            raise ValueError(f"Character '{source_clean}' already exists in '{novel_tag}' dictionary.")
        new_char = CharacterTerm(id=len(chars) + 1, source=source_clean, target=target.strip(), novel_tag=novel_tag, gender_role=gender_role)
        chars.append(new_char)
        self.save_character_dict(chars)
        return new_char
