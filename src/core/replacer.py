import re
from pathlib import Path
from typing import Dict, Tuple

class ReplacerEngine:
    """
    Engine thay thế tốc độ cao dựa trên Regex Alternation và Longest Match First.
    Hỗ trợ xử lý streaming buffer trên các file truyện dung lượng lớn (>50MB).
    """
    def __init__(self, mappings: Dict[str, str], case_sensitive: bool = False):
        self.mappings = mappings
        self.case_sensitive = case_sensitive
        self._compiled_regex = None
        self._lookup: Dict[str, str] = {}
        self._build_engine()

    def _build_engine(self):
        if not self.mappings:
            return

        # Sắp xếp các cụm từ theo độ dài giảm dần (Longest Match First)
        # Giúp ưu tiên cụm từ dài trước (vd: "Trương Tử Kiến" trước "Trương Tử")
        sorted_keys = sorted(self.mappings.keys(), key=lambda x: len(x), reverse=True)

        word_keys = []
        other_keys = []
        for k in sorted_keys:
            if not k:
                continue
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
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._compiled_regex = re.compile(combined_pattern, flags)

        if self.case_sensitive:
            self._lookup = {k: v for k, v in self.mappings.items()}
        else:
            self._lookup = {k.lower(): v for k, v in self.mappings.items()}

    def replace_text(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Thay thế chuỗi văn bản và trả về kết quả kèm thống kê số lần thay thế của từng từ.
        """
        if not self._compiled_regex or not text:
            return text, {}

        stats: Dict[str, int] = {}

        def _sub_callback(match: re.Match) -> str:
            matched_str = match.group(0)
            lookup_key = matched_str if self.case_sensitive else matched_str.lower()
            replacement = self._lookup.get(lookup_key, matched_str)
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
