import re
from collections import Counter
from typing import List, Set, Optional
from pydantic import BaseModel

class ScannedCandidate(BaseModel):
    phrase: str
    count: int
    candidate_type: str  # "Tên nhân vật" hoặc "Từ bất thường"
    sample_contexts: List[str] = []

class NovelScanner:
    """
    Quét và phát hiện tự động các cụm từ viết hoa (tên nhân vật)
    và các cụm từ dịch thô/lỗi dịch máy phổ biến từ văn bản convert.
    """
    # Các từ phổ biến đầu câu tiếng Việt cần bỏ qua
    COMMON_START_WORDS = {
        "hôm nay", "ngày mai", "hôm qua", "hắn", "nàng", "chúng ta", "bọn họ",
        "tuy nhiên", "nhưng mà", "sau đó", "trước đó", "bởi vì", "như vậy",
        "không có", "có thể", "ngươi", "ta", "ông ấy", "bà ấy", "đột nhiên",
        "vào lúc", "lúc này", "một lát", "không biết", "người này", "thời điểm",
        "mặc dù", "cho nên", "đồng thời", "thậm chí", "nhìn thấy", "nói cách khác"
    }

    # Một số cụm từ dịch thô / lỗi convert thường gặp
    ABNORMAL_KEYWORDS = [
        "đợi ảnh thị kịch", "lấy gã bác sĩ", "đương gia hoa đán",
        "thành thục mỹ phụ", "tiêu thụ bộ quản lí", "nghàng an ninh",
        "đệ đệ", "muội muội", "thê tử", "nữ nhi", "ba ba", "ma ma",
        "đại quản lí", "phó quản lý", "thành phần tri thức", "chocolate mỹ nữ"
    ]

    def __init__(self, existing_words: Optional[Set[str]] = None):
        self.existing_words = {w.lower() for w in (existing_words or set())}

    def _get_contexts(self, text: str, phrase: str, max_contexts: int = 2) -> List[str]:
        contexts = []
        pattern = re.compile(r'([^.\n]*?' + re.escape(phrase) + r'[^.\n]*)', re.IGNORECASE)
        for match in pattern.finditer(text):
            ctx = match.group(0).strip()
            if ctx and ctx not in contexts:
                contexts.append(ctx[:120])
            if len(contexts) >= max_contexts:
                break
        return contexts

    def extract_proper_nouns(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        counts = Counter()
        lines = text.splitlines()

        for line in lines:
            words = re.findall(r'[^\W\d_]+', line)
            n = len(words)
            # Quét các cụm 4 từ, 3 từ, 2 từ
            for length in (4, 3, 2):
                for i in range(n - length + 1):
                    ngram = words[i:i+length]
                    phrase = " ".join(ngram)
                    phrase_lower = phrase.lower()

                    if phrase_lower in self.COMMON_START_WORDS or phrase_lower in self.existing_words:
                        continue

                    # Trường hợp 1: Tất cả các từ đều viết hoa (Chuẩn tên người: Trương Tử Kiến, Lâm Ngọc Chi)
                    if all(w[0].isupper() for w in ngram):
                        counts[phrase] += 1
                    # Trường hợp 2: Từ đầu viết hoa, các từ sau thường (vd: Gavin phong, Lỗ quân)
                    elif ngram[0][0].isupper() and all(w.islower() for w in ngram[1:]):
                        counts[phrase] += 1

        # Lọc cụm từ con bị trùng lặp tần suất (vd: bỏ "Trương Tử" nếu "Trương Tử Kiến" có cùng số lần)
        filtered_counts = {}
        for phrase, count in sorted(counts.items(), key=lambda x: len(x[0]), reverse=True):
            if count < min_count:
                continue
            is_sub = False
            for longer_phrase, longer_count in filtered_counts.items():
                if phrase in longer_phrase and count <= longer_count:
                    is_sub = True
                    break
            if not is_sub:
                filtered_counts[phrase] = count

        results = []
        for phrase, count in sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True):
            results.append(ScannedCandidate(
                phrase=phrase,
                count=count,
                candidate_type="Tên nhân vật",
                sample_contexts=self._get_contexts(text, phrase)
            ))
        return results

    def extract_abnormal_patterns(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        results = []
        for pattern_str in self.ABNORMAL_KEYWORDS:
            pattern = re.compile(re.escape(pattern_str), re.IGNORECASE)
            matches = pattern.findall(text)
            count = len(matches)
            if count >= min_count and pattern_str.lower() not in self.existing_words:
                results.append(ScannedCandidate(
                    phrase=pattern_str,
                    count=count,
                    candidate_type="Từ bất thường",
                    sample_contexts=self._get_contexts(text, pattern_str)
                ))
        return sorted(results, key=lambda x: x.count, reverse=True)

    def scan_text(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        nouns = self.extract_proper_nouns(text, min_count=min_count)
        abnormals = self.extract_abnormal_patterns(text, min_count=min_count)
        return nouns + abnormals
