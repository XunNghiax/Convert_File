import json
import re
import unicodedata
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Set
from pydantic import BaseModel, Field
from src.core.replacer import title_case_vietnamese

class CommonTerm(BaseModel):
    id: str = ""
    source: str
    target: str
    category: str = "Chung"

    def normalize(self) -> "CommonTerm":
        self.source = unicodedata.normalize('NFC', self.source.strip())
        self.target = unicodedata.normalize('NFC', self.target.strip())
        self.category = unicodedata.normalize('NFC', self.category.strip()) or "Chung"
        return self

class CharacterTerm(BaseModel):
    id: str = ""
    source: str
    target: str
    novel_tag: str = "Chung"

    def normalize(self) -> "CharacterTerm":
        self.source = unicodedata.normalize('NFC', self.source.strip())
        tgt = unicodedata.normalize('NFC', self.target.strip())
        self.target = title_case_vietnamese(tgt) if tgt else title_case_vietnamese(self.source)
        self.novel_tag = unicodedata.normalize('NFC', self.novel_tag.strip()) or "Chung"
        return self

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
        terms = []
        for idx, item in enumerate(data, start=1):
            curr_id = str(item.get("id", ""))
            if not curr_id.startswith("co-"):
                item["id"] = f"co-{idx}"
            # Loại bỏ các trường thừa không còn dùng như notes
            cleaned_item = {
                "id": item["id"],
                "source": item.get("source", ""),
                "target": item.get("target", ""),
                "category": item.get("category", "Chung")
            }
            t = CommonTerm(**cleaned_item).normalize()
            terms.append(t)
        return terms

    def save_common_dict(self, terms: List[CommonTerm]) -> None:
        # Chuẩn hóa ID dạng co-1, co-2, co-3...
        for idx, t in enumerate(terms, start=1):
            t.normalize()
            t.id = f"co-{idx}"
        data = [t.model_dump() for t in terms]
        self.common_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_character_dict(self) -> List[CharacterTerm]:
        content = self.character_path.read_text(encoding="utf-8").strip() or "[]"
        data = json.loads(content)
        chars = []
        for idx, item in enumerate(data, start=1):
            curr_id = str(item.get("id", ""))
            if not curr_id.startswith("ch-"):
                item["id"] = f"ch-{idx}"
            # Loại bỏ các trường thừa không còn dùng như gender_role
            cleaned_item = {
                "id": item["id"],
                "source": item.get("source", ""),
                "target": item.get("target", ""),
                "novel_tag": item.get("novel_tag", "Chung")
            }
            c = CharacterTerm(**cleaned_item).normalize()
            chars.append(c)
        return chars

    def save_character_dict(self, terms: List[CharacterTerm]) -> None:
        # Chuẩn hóa ID dạng ch-1, ch-2, ch-3...
        for idx, t in enumerate(terms, start=1):
            t.normalize()
            t.id = f"ch-{idx}"
        data = [t.model_dump() for t in terms]
        self.character_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_common_term(self, source: str, target: str, category: str = "Chung") -> CommonTerm:
        source_clean = unicodedata.normalize('NFC', source.strip())
        target_clean = unicodedata.normalize('NFC', target.strip())
        category_clean = unicodedata.normalize('NFC', category.strip()) or "Chung"
        terms = self.load_common_dict()
        if any(t.source.lower() == source_clean.lower() for t in terms):
            raise ValueError(f"Term '{source_clean}' already exists in common dictionary.")
        new_term = CommonTerm(id=f"co-{len(terms) + 1}", source=source_clean, target=target_clean, category=category_clean).normalize()
        terms.append(new_term)
        self.save_common_dict(terms)
        return new_term

    def add_character_term(self, source: str, target: str, novel_tag: str = "Chung") -> CharacterTerm:
        source_clean = unicodedata.normalize('NFC', source.strip())
        target_clean = unicodedata.normalize('NFC', target.strip())
        tag_clean = unicodedata.normalize('NFC', novel_tag.strip()) or "Chung"
        chars = self.load_character_dict()
        if any(c.source.lower() == source_clean.lower() and c.novel_tag == tag_clean for c in chars):
            raise ValueError(f"Character '{source_clean}' already exists in '{tag_clean}' dictionary.")
        new_char = CharacterTerm(id=f"ch-{len(chars) + 1}", source=source_clean, target=target_clean, novel_tag=tag_clean).normalize()
        chars.append(new_char)
        self.save_character_dict(chars)
        return new_char

    def upsert_common_term(
        self,
        source: str,
        target: str,
        category: str = "Chung"
    ) -> Tuple[CommonTerm, str]:
        source_clean = unicodedata.normalize('NFC', source.strip())
        target_clean = unicodedata.normalize('NFC', target.strip()) or source_clean
        category_clean = unicodedata.normalize('NFC', category.strip()) or "Chung"

        terms = self.load_common_dict()
        existing = next((t for t in terms if t.source.lower() == source_clean.lower()), None)

        if existing:
            updated = False
            if existing.target != target_clean:
                existing.target = target_clean
                updated = True
            if category_clean != "Chung" and existing.category != category_clean:
                existing.category = category_clean
                updated = True

            if updated:
                self.save_common_dict(terms)
                return existing, "updated"
            return existing, "skipped"
        else:
            new_term = CommonTerm(
                id=f"co-{len(terms) + 1}",
                source=source_clean,
                target=target_clean,
                category=category_clean
            ).normalize()
            terms.append(new_term)
            self.save_common_dict(terms)
            return new_term, "new"

    def upsert_character_term(
        self,
        source: str,
        target: str,
        novel_tag: str = "Chung"
    ) -> Tuple[CharacterTerm, str]:
        source_clean = unicodedata.normalize('NFC', source.strip())
        raw_target = unicodedata.normalize('NFC', target.strip()) or source_clean
        target_clean = title_case_vietnamese(raw_target)
        tag_clean = unicodedata.normalize('NFC', novel_tag.strip()) or "Chung"

        chars = self.load_character_dict()
        existing = next((
            c for c in chars
            if c.source.lower() == source_clean.lower() and (
                c.novel_tag.lower() == tag_clean.lower() or tag_clean == "Chung" or c.novel_tag == "Chung"
            )
        ), None)

        if existing:
            updated = False
            if existing.target != target_clean:
                existing.target = target_clean
                updated = True
            if tag_clean != "Chung" and existing.novel_tag == "Chung":
                existing.novel_tag = tag_clean
                updated = True

            if updated:
                self.save_character_dict(chars)
                return existing, "updated"
            return existing, "skipped"
        else:
            new_char = CharacterTerm(
                id=f"ch-{len(chars) + 1}",
                source=source_clean,
                target=target_clean,
                novel_tag=tag_clean
            ).normalize()
            chars.append(new_char)
            self.save_character_dict(chars)
            return new_char, "new"

    def standardize_dictionaries(self) -> Dict[str, Any]:
        """
        Chuẩn hóa toàn bộ từ điển theo cấu trúc tinh gọn:
        - Common: {id, source, target, category}
        - Character: {id, source, target, novel_tag}
        - Chuẩn hóa Unicode NFC mọi trường chuỗi.
        - Khử trùng lặp (deduplicate) case-insensitive.
        - Viết hoa chuẩn Title Case cho tên nhân vật.
        - Đánh lại ID tuần tự co-1..N và ch-1..N.
        """
        common_terms = self.load_common_dict()
        char_terms = self.load_character_dict()

        common_before = len(common_terms)
        char_before = len(char_terms)

        # Deduplicate common_dict
        deduped_common: List[CommonTerm] = []
        seen_common: Dict[str, int] = {}
        for t in common_terms:
            t.normalize()
            key = t.source.lower()
            if key in seen_common:
                idx = seen_common[key]
                if t.category != "Chung" and deduped_common[idx].category == "Chung":
                    deduped_common[idx].category = t.category
                if t.target and deduped_common[idx].target == deduped_common[idx].source:
                    deduped_common[idx].target = t.target
            else:
                seen_common[key] = len(deduped_common)
                deduped_common.append(t)

        # Deduplicate character_dict
        deduped_chars: List[CharacterTerm] = []
        seen_chars: Dict[Tuple[str, str], int] = {}
        for c in char_terms:
            c.normalize()
            key = (c.source.lower(), c.novel_tag.lower())
            if key in seen_chars:
                idx = seen_chars[key]
                if c.target and deduped_chars[idx].target == deduped_chars[idx].source:
                    deduped_chars[idx].target = c.target
            else:
                seen_chars[key] = len(deduped_chars)
                deduped_chars.append(c)

        self.save_common_dict(deduped_common)
        self.save_character_dict(deduped_chars)

        return {
            "common_before": common_before,
            "common_after": len(deduped_common),
            "common_deduped": common_before - len(deduped_common),
            "character_before": char_before,
            "character_after": len(deduped_chars),
            "character_deduped": char_before - len(deduped_chars),
        }

    @staticmethod
    def parse_scanned_file(file_path: Path) -> List[dict]:
        """
        Đọc và phân tích file kết quả scan (hỗ trợ .json hoặc .txt chứa cấu trúc JSON/markdown).
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        raw_text = file_path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw_text:
            return []

        # 1. Thử parse trực tiếp JSON
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for key in ["candidates", "items", "terms", "data"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                return [parsed]
        except Exception:
            pass

        # 2. Thử bóc tách code block markdown ```json ... ```
        fence_match = re.search(r'```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```', raw_text, re.DOTALL)
        if fence_match:
            try:
                cleaned_block = re.sub(r',\s*([}\]])', r'\1', fence_match.group(1))
                return json.loads(cleaned_block)
            except Exception:
                pass

        # 3. Thử tìm mảng JSON tổng quát [...] trong file text
        json_array_match = re.search(r'(\[\s*\{.*\}\s*\])', raw_text, re.DOTALL)
        if json_array_match:
            json_str = json_array_match.group(1)
            try:
                cleaned_json = re.sub(r',\s*([}\]])', r'\1', json_str)
                return json.loads(cleaned_json)
            except Exception:
                pass

        # 4. Hỗ trợ định dạng dòng đơn giản: nguồn -> đích
        line_records = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("="):
                continue
            if "->" in line:
                parts = line.split("->", 1)
                line_records.append({"source": parts[0].strip(), "target": parts[1].strip()})
            elif "=" in line:
                parts = line.split("=", 1)
                line_records.append({"source": parts[0].strip(), "target": parts[1].strip()})

        if line_records:
            return line_records

        raise ValueError(f"Không thể trích xuất danh sách JSON hợp lệ từ {file_path.name}")

    @classmethod
    def resolve_expansion_conflict(
        cls,
        source: str,
        target: str,
        all_known_sources: Set[str]
    ) -> Tuple[str, bool]:
        """
        Kiểm tra xem target có bị mở rộng thêm từ so với source không.
        Nếu có và source là tiền tố của ít nhất một từ khác trong all_known_sources,
        tự động hạ target về dạng Title Case 1-1 tương ứng với source.
        """
        source_clean = unicodedata.normalize('NFC', source.strip())
        target_clean = unicodedata.normalize('NFC', target.strip())
        source_words = source_clean.split()
        target_words = target_clean.split()

        if len(target_words) <= len(source_words) or not source_words:
            return target_clean, False

        source_lower = source_clean.lower()
        prefix_with_space = f"{source_lower} "
        is_subphrase = any(
            s != source_lower and (s.startswith(prefix_with_space) or f" {source_lower} " in f" {s} ")
            for s in all_known_sources
        )

        if is_subphrase:
            return title_case_vietnamese(source_clean), True

        return target_clean, False

    def import_records(self, records: List[dict], default_novel_tag: str = "Chung") -> Dict[str, Any]:
        """
        Nạp một danh sách các bản ghi (từ file scan đã biên tập) vào từ điển phù hợp:
        - Tên nhân vật -> character_dict.json ({id, source, target, novel_tag})
        - Từ phổ biến / dịch thô -> common_dict.json ({id, source, target, category})
        """
        common_terms = self.load_common_dict()
        char_terms = self.load_character_dict()

        chars_added = 0
        chars_updated = 0
        chars_skipped = 0

        common_added = 0
        common_updated = 0
        common_skipped = 0

        actions = []

        for rec in records:
            if not isinstance(rec, dict):
                continue
            source = rec.get("source") or rec.get("phrase") or rec.get("from") or ""
            source = unicodedata.normalize('NFC', str(source)).strip()
            if not source:
                continue

            target = rec.get("target") or rec.get("suggested_target") or rec.get("to") or source
            target = unicodedata.normalize('NFC', str(target)).strip()

            cat_raw = rec.get("category") or rec.get("type") or rec.get("candidate_type") or ""
            cat_clean = unicodedata.normalize('NFC', str(cat_raw)).strip()

            # Phân loại: Tên nhân vật hay Từ phổ biến
            is_char = rec.get("is_character", None)
            if is_char is None:
                is_char = cat_clean.lower() in ["tên nhân vật", "nhân vật", "character", "tên riêng"]

            if is_char:
                novel_tag = rec.get("novel_tag") or default_novel_tag or "Chung"
                novel_tag = unicodedata.normalize('NFC', str(novel_tag)).strip()
                target_clean = title_case_vietnamese(target)

                # Tìm kiếm đã tồn tại
                existing = next((
                    c for c in char_terms
                    if c.source.lower() == source.lower() and (
                        c.novel_tag.lower() == novel_tag.lower() or novel_tag == "Chung" or c.novel_tag == "Chung"
                    )
                ), None)

                if existing:
                    updated = False
                    if existing.target != target_clean:
                        existing.target = target_clean
                        updated = True
                    if novel_tag != "Chung" and existing.novel_tag == "Chung":
                        existing.novel_tag = novel_tag
                        updated = True

                    if updated:
                        chars_updated += 1
                        actions.append({"type": "character", "source": source, "target": target_clean, "novel_tag": existing.novel_tag, "status": "updated"})
                    else:
                        chars_skipped += 1
                        actions.append({"type": "character", "source": source, "target": target_clean, "novel_tag": existing.novel_tag, "status": "skipped"})
                else:
                    new_char = CharacterTerm(
                        id=f"ch-{len(char_terms) + 1}",
                        source=source,
                        target=target_clean,
                        novel_tag=novel_tag
                    )
                    char_terms.append(new_char)
                    chars_added += 1
                    actions.append({"type": "character", "source": source, "target": target_clean, "novel_tag": novel_tag, "status": "new"})
            else:
                category = cat_clean or "Lỗi dịch máy"

                existing = next((t for t in common_terms if t.source.lower() == source.lower()), None)
                if existing:
                    updated = False
                    if existing.target != target:
                        existing.target = target
                        updated = True
                    if category != "Chung" and existing.category != category:
                        existing.category = category
                        updated = True

                    if updated:
                        common_updated += 1
                        actions.append({"type": "common", "source": source, "target": target, "category": existing.category, "status": "updated"})
                    else:
                        common_skipped += 1
                        actions.append({"type": "common", "source": source, "target": target, "category": existing.category, "status": "skipped"})
                else:
                    new_term = CommonTerm(
                        id=f"co-{len(common_terms) + 1}",
                        source=source,
                        target=target,
                        category=category
                    )
                    common_terms.append(new_term)
                    common_added += 1
                    actions.append({"type": "common", "source": source, "target": target, "category": category, "status": "new"})

        # Lưu lại cả hai từ điển
        self.save_common_dict(common_terms)
        self.save_character_dict(char_terms)

        return {
            "total_records": len(records),
            "chars_added": chars_added,
            "chars_updated": chars_updated,
            "chars_skipped": chars_skipped,
            "chars_total_after": len(char_terms),
            "common_added": common_added,
            "common_updated": common_updated,
            "common_skipped": common_skipped,
            "common_total_after": len(common_terms),
            "actions": actions
        }
