import re
from pathlib import Path
from typing import Dict, Tuple, Optional

def title_case_vietnamese(text: str) -> str:
    """Viết hoa chữ cái đầu cho mỗi từ trong tên riêng tiếng Việt."""
    return " ".join(w.capitalize() for w in text.strip().split())

class ReplacerEngine:
    """
    Engine thay thế tốc độ cao dựa trên Regex Alternation và Longest Match First.
    Hỗ trợ:
    - Tự động upcase (Title Case) toàn bộ tên riêng cho các mục từ điển nhân vật (ch-).
    - Bảo toàn chữ hoa/thường ngữ cảnh cho từ phổ biến (co-).
    - Xử lý streaming buffer trên các file truyện dung lượng lớn (>50MB).
    """
    def __init__(
        self,
        common_mappings: Optional[Dict[str, str]] = None,
        character_mappings: Optional[Dict[str, str]] = None,
        mappings: Optional[Dict[str, str]] = None,
        case_sensitive: bool = False
    ):
        self.common_mappings = common_mappings or {}
        self.character_mappings = character_mappings or {}
        # Nếu truyền legacy mappings, gộp vào common_mappings
        if mappings:
            for k, v in mappings.items():
                if k not in self.common_mappings and k not in self.character_mappings:
                    self.common_mappings[k] = v

        self.case_sensitive = case_sensitive
        self._compiled_regex = None
        # _lookup lưu: lookup_key -> (target_text, is_character)
        self._lookup: Dict[str, Tuple[str, bool]] = {}
        self._build_engine()

    def _build_engine(self):
        # 1. Đăng ký tên nhân vật (ch-): luôn Title Case target
        char_keys = set()
        for k, v in self.character_mappings.items():
            if not k.strip():
                continue
            k_clean = k.strip()
            # Tự động upcase tên riêng chuẩn:
            target_title = title_case_vietnamese(v if v else k_clean)
            self._lookup[k_clean.lower()] = (target_title, True)
            char_keys.add(k_clean)

        # 2. Đăng ký từ phổ biến (co-): không ép Title Case, bảo lưu nguyên dạng
        common_keys = set()
        for k, v in self.common_mappings.items():
            if not k.strip():
                continue
            k_clean = k.strip()
            # Nếu chưa có trong char_mappings
            if k_clean.lower() not in self._lookup:
                self._lookup[k_clean.lower()] = (v.strip(), False)
                common_keys.add(k_clean)

        all_keys = list(char_keys.union(common_keys))
        if not all_keys:
            return

        # Sắp xếp các cụm từ theo độ dài giảm dần (Longest Match First)
        sorted_keys = sorted(all_keys, key=lambda x: len(x), reverse=True)

        word_keys = []
        other_keys = []
        for k in sorted_keys:
            # Phân tách từ có ranh giới từ (bắt đầu và kết thúc bằng ký tự chữ/số)
            if re.match(r'^\w', k, re.UNICODE) and re.search(r'\w$', k, re.UNICODE):
                word_keys.append(re.escape(k))
            else:
                other_keys.append(re.escape(k))

        patterns = []
        if word_keys:
            patterns.append(r'\b(?:' + '|'.join(word_keys) + r')\b')
        if other_keys:
            patterns.append(r'(?:' + '|'.join(other_keys) + r')')

        combined_pattern = "|".join(patterns)
        # Sử dụng IGNORECASE để tìm được tên nhân vật ngay cả khi bản dịch thô viết thường/lộn xộn
        flags = re.IGNORECASE if not self.case_sensitive else 0
        self._compiled_regex = re.compile(combined_pattern, flags)

    def replace_text(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Thay thế chuỗi văn bản và trả về kết quả kèm thống kê số lần thay thế của từng từ.
        """
        if not self._compiled_regex or not text:
            return text, {}

        stats: Dict[str, int] = {}

        def _sub_callback(match: re.Match) -> str:
            matched_str = match.group(0)
            lookup_key = matched_str.lower()
            info = self._lookup.get(lookup_key)
            if not info:
                return matched_str

            target, is_character = info

            if is_character:
                # TỰ ĐỘNG UPCASE: Tên nhân vật (ch-) luôn luôn viết hoa từng từ chuẩn hóa
                replacement = target
            else:
                # TỪ PHỔ BIẾN (co-): Bảo toàn viết hoa chữ đầu nếu đứng đầu câu/đoạn, không ép Title Case
                if matched_str and matched_str[0].isupper() and target:
                    replacement = target[0].upper() + target[1:]
                else:
                    replacement = target

            stats[matched_str] = stats.get(matched_str, 0) + 1
            return replacement

        result = self._compiled_regex.sub(_sub_callback, text)
        return result, stats

    def replace_file(self, input_path: Path, output_path: Path, buffer_lines: int = 5000) -> Dict[str, int]:
        """
        Xử lý streaming theo buffer dòng để convert file lớn (50-70MB+) mà không gây tràn RAM.
        """
        total_stats: Dict[str, int] = {}
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(input_path, "r", encoding="utf-8", errors="replace") as fin, \
             open(output_path, "w", encoding="utf-8", errors="replace") as fout:

            buffer = []
            for line in fin:
                buffer.append(line)
                if len(buffer) >= buffer_lines:
                    chunk_text = "".join(buffer)
                    converted_chunk, stats = self.replace_text(chunk_text)
                    fout.write(converted_chunk)
                    for k, v in stats.items():
                        total_stats[k] = total_stats.get(k, 0) + v
                    buffer.clear()

            if buffer:
                chunk_text = "".join(buffer)
                converted_chunk, stats = self.replace_text(chunk_text)
                fout.write(converted_chunk)
                for k, v in stats.items():
                    total_stats[k] = total_stats.get(k, 0) + v
                buffer.clear()

        return total_stats
