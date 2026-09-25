import re
from collections import Counter
from typing import List, Set, Optional, Dict
from pydantic import BaseModel

def title_case_vietnamese(text: str) -> str:
    """Viết hoa chữ cái đầu cho mỗi từ trong tên riêng tiếng Việt."""
    return " ".join(w.capitalize() for w in text.strip().split())

class ScannedCandidate(BaseModel):
    phrase: str
    count: int
    candidate_type: str  # "Tên nhân vật", "Lỗi dịch máy", "Cấu trúc Hán", "Từ bất thường"
    sample_contexts: List[str] = []
    suggested_target: str = ""

class NovelScanner:
    """
    Quét và phát hiện tự động các cụm từ viết hoa (tên nhân vật),
    tên kèm danh xưng, và các cụm từ dịch thô/lỗi dịch máy phổ biến từ văn bản convert.
    """
    # Các từ phổ biến đầu câu tiếng Việt cần bỏ qua (được mở rộng đầy đủ)
    COMMON_START_WORDS = {
        "hôm nay", "ngày mai", "hôm qua", "hắn", "nàng", "chúng ta", "bọn họ",
        "tuy nhiên", "nhưng mà", "sau đó", "trước đó", "bởi vì", "như vậy",
        "không có", "có thể", "ngươi", "ta", "ông ấy", "bà ấy", "đột nhiên",
        "vào lúc", "lúc này", "một lát", "không biết", "người này", "thời điểm",
        "mặc dù", "cho nên", "đồng thời", "thậm chí", "nhìn thấy", "nói cách khác",
        "kết quả", "chính là", "nếu như", "bất quá", "chỉ là", "chỉ có", "nguyên lai",
        "trong lòng", "lập tức", "vừa rồi", "hiện tại", "thực ra", "kỳ thật",
        "dù sao", "ngược lại", "không thể", "chẳng lẽ", "hơn nữa", "ngoài ra",
        "trên thực tế", "không bao lâu", "vài ngày sau", "sau khi", "một bên",
        "đúng vậy", "quả nhiên", "bỗng nhiên", "một lát sau", "trong chốc lát",
        "thanh niên", "thiếu nữ", "đứa nhỏ", "cô gái", "bác sĩ", "y tá",
        "chính văn", "chương", "tiết", "tập", "hồi", "nhìn", "nghe", "thấy",
        "vài cái", "một cái", "vài người", "hai người", "mọi người", "trên bờ"
    }

    # Danh sách Họ phổ biến trong truyện tiếng Trung / Việt (chữ thường để đối chiếu)
    VIET_CHINESE_SURNAMES = {
        "nguyễn", "trần", "lê", "phạm", "hoàng", "huỳnh", "phan", "vũ", "võ", "đặng",
        "bùi", "đỗ", "hồ", "ngô", "dương", "lý", "liễu", "chu", "khưu", "hạ", "mai",
        "trương", "long", "tiêu", "lâm", "tần", "tạ", "cố", "thẩm", "giang", "bạch",
        "phương", "diệp", "tô", "tiết", "tống", "hàn", "lưu", "triệu", "vương", "tôn",
        "châu", "đới", "phùng", "lục", "tiền", "quách", "khương", "ân", "thường", "mạnh",
        "kim", "doãn", "nghiêm", "thôi", "hứa", "gia cát", "tư mã", "âu dương", "mộ dung"
    }

    # Hậu tố danh xưng thân tộc/vai vế thường đi sau tên riêng
    HONORIFIC_SUFFIXES = {"tỷ", "ca", "muội", "đệ", "bác", "thúc", "tẩu", "sư", "lão", "bá"}

    # Tiền tố chức danh / danh xưng thường đi trước tên
    HONORIFIC_PREFIXES = {"bác sĩ", "chủ nhiệm", "quản lí", "quản lý", "trưởng phòng", "giáo sư", "y tá", "lão sư", "phu nhân", "tiểu thư"}

    # Danh sách các từ khóa lỗi dịch máy / convert thô thường gặp
    ABNORMAL_KEYWORDS = [
        "hoàn toàn ăn mày", "gây ra dòng điện ảnh", "truyền phát tin gây ra dòng điện ảnh",
        "truyền phát tin", "chuẩn bị một chút thủy", "một chút thủy",
        "lồi lõm có hứng thú", "nhũ màu trắng cao dép lê", "nhũ màu trắng", "cao dép lê",
        "viết chữ đại lâu", "thành phần tri thức", "quay đầu dẫn rất cao", "quay đầu dẫn",
        "hạt giảng", "đản sanh vu này", "đản sanh vu", "dũ phát mãnh liệt", "dũ phát",
        "nguy kiều", "lò vi sóng lý", "nồi cơm điện lý", "đang lúc", "chờ thông tri",
        "mô phạm trượng phu", "bất tranh khí", "dĩ nhiên cũng làm là", "đợi ảnh thị kịch",
        "lấy gã bác sĩ", "đương gia hoa đán", "thành thục mỹ phụ", "tiêu thụ bộ quản lí",
        "nghàng an ninh", "đệ đệ", "muội muội", "thê tử", "nữ nhi", "ba ba", "ma ma",
        "đại quản lí", "phó quản lý", "chocolate mỹ nữ"
    ]

    # Bản dịch gợi ý nhanh cho các lỗi dịch máy điển hình
    DEFAULT_TRANSLATION_MAP = {
        "hoàn toàn ăn mày": "ô mai",
        "gây ra dòng điện ảnh": "phim điện ảnh",
        "truyền phát tin gây ra dòng điện ảnh": "đang chiếu phim điện ảnh",
        "chuẩn bị một chút thủy": "chuẩn bị xuống nước",
        "một chút thủy": "xuống nước",
        "lồi lõm có hứng thú": "đường cong lồi lõm quyến rũ",
        "nhũ màu trắng cao dép lê": "dép lê cao gót màu trắng sữa",
        "nhũ màu trắng": "màu trắng sữa",
        "cao dép lê": "dép lê cao gót",
        "viết chữ đại lâu": "tòa nhà văn phòng",
        "thành phần tri thức": "dân văn phòng",
        "quay đầu dẫn rất cao": "tỷ lệ ngoái nhìn cực cao",
        "quay đầu dẫn": "tỷ lệ ngoái nhìn",
        "hạt giảng": "nói bừa",
        "đản sanh vu này": "sinh ra tại nơi này",
        "đản sanh vu": "sinh ra tại",
        "dũ phát mãnh liệt": "càng thêm mãnh liệt",
        "dũ phát": "càng thêm",
        "lò vi sóng lý": "trong lò vi sóng",
        "nồi cơm điện lý": "trong nồi cơm điện",
        "dĩ nhiên cũng làm là": "hóa ra chính là",
        "đợi ảnh thị kịch": "các phim ảnh",
        "lấy gã bác sĩ": "gả cho bác sĩ",
        "đương gia hoa đán": "ngôi sao trụ cột",
        "thành thục mỹ phụ": "mỹ phụ chín chắn",
        "tiêu thụ bộ quản lí": "trưởng phòng kinh doanh",
        "nghàng an ninh": "ngành an ninh"
    }

    def __init__(self, existing_words: Optional[Set[str]] = None):
        self.existing_words = {w.lower() for w in (existing_words or set())}

    def _get_contexts(self, text: str, phrase: str, max_contexts: int = 2) -> List[str]:
        contexts = []
        # Trích xuất nguyên câu hoàn chỉnh chứa phrase
        escaped_phrase = re.escape(phrase)
        pattern = re.compile(r'([^.!?\n\r]*?' + escaped_phrase + r'[^.!?\n\r]*)', re.IGNORECASE)
        for match in pattern.finditer(text):
            ctx = match.group(0).strip()
            # Làm sạch ký tự thụt lề
            ctx = re.sub(r'[\t\s]+', ' ', ctx)
            if ctx and ctx not in contexts:
                contexts.append(ctx[:160])
            if len(contexts) >= max_contexts:
                break
        return contexts

    def extract_proper_nouns(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        counts: Counter = Counter()
        suggested_map: Dict[str, str] = {}
        lines = text.splitlines()

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            words = re.findall(r'[^\W\d_]+', line_str)
            n = len(words)

            # 1. Quét tên chuẩn 2-4 âm tiết (viết hoa chuẩn hoặc viết thường âm sau)
            for length in (4, 3, 2):
                for i in range(n - length + 1):
                    ngram = words[i:i+length]
                    phrase = " ".join(ngram)
                    phrase_lower = phrase.lower()

                    if phrase_lower in self.COMMON_START_WORDS or phrase_lower in self.existing_words:
                        continue

                    first_word_lower = ngram[0].lower()
                    is_known_surname = first_word_lower in self.VIET_CHINESE_SURNAMES

                    # Trường hợp 1A: Tên chuẩn viết hoa từng từ (Long Kiếm Phi, Trương Tử Kiến)
                    if all(w[0].isupper() for w in ngram):
                        # Nếu là cụm 2 từ đứng đầu dòng/câu mà không phải là họ và nằm trong từ thông thường -> bỏ qua
                        if length == 2 and not is_known_surname and phrase_lower in self.COMMON_START_WORDS:
                            continue
                        counts[phrase] += 1
                        if phrase not in suggested_map:
                            suggested_map[phrase] = phrase

                    # Trường hợp 1B: Họ viết hoa, âm sau viết thường (Liễu Ngọc như, Chu Ngọc mị, Khưu ngọc trinh)
                    elif ngram[0][0].isupper() and is_known_surname and (length in (2, 3)):
                        counts[phrase] += 1
                        if phrase not in suggested_map:
                            suggested_map[phrase] = title_case_vietnamese(phrase)

                    # Trường hợp 1C: Tên nửa Tây nửa Việt / âm sau viết thường (Gavin phong, Lỗ quân)
                    elif ngram[0][0].isupper() and all(w.islower() for w in ngram[1:]) and length == 2:
                        counts[phrase] += 1
                        if phrase not in suggested_map:
                            suggested_map[phrase] = title_case_vietnamese(phrase)

            # 2. Quét tên gắn với hậu tố danh xưng: [Tên] + [tỷ|ca|muội|đệ|...] (Như tỷ, Mị tỷ, Vĩ ca)
            for i in range(n - 1):
                first_w = words[i]
                second_w = words[i+1]
                if second_w.lower() in self.HONORIFIC_SUFFIXES:
                    # Tên viết hoa (Như tỷ, Mị tỷ, Vĩ ca) hoặc tên thường
                    if first_w[0].isupper() and first_w.lower() not in self.COMMON_START_WORDS:
                        name_phrase = f"{first_w} {second_w.lower()}"
                        counts[name_phrase] += 1
                        if name_phrase not in suggested_map:
                            suggested_map[name_phrase] = f"{first_w.capitalize()} {second_w.lower()}"

            # 3. Quét tiền tố chức danh: [Chức danh] + [Tên] (Mạnh bác sĩ, Mai quản lí, Dương phu nhân)
            for prefix in self.HONORIFIC_PREFIXES:
                p_pattern = re.compile(re.escape(prefix) + r'\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[a-zà-ỹA-ZÀ-Ỹ]+)?)', re.UNICODE)
                for m in p_pattern.finditer(line_str):
                    full_match = m.group(0).strip()
                    name_part = m.group(1).strip()
                    if name_part.lower() not in self.COMMON_START_WORDS:
                        counts[full_match] += 1
                        if full_match not in suggested_map:
                            suggested_map[full_match] = full_match

        # Lọc cụm từ con bị trùng lặp tần suất (ví dụ: bỏ "Trương Tử" nếu "Trương Tử Kiến" có cùng hoặc nhiều hơn số lần)
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
                sample_contexts=self._get_contexts(text, phrase),
                suggested_target=suggested_map.get(phrase, title_case_vietnamese(phrase))
            ))
        return results

    def extract_abnormal_patterns(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        results_map: Dict[str, ScannedCandidate] = {}

        # 1. Quét theo danh sách từ khóa lỗi dịch máy ABNORMAL_KEYWORDS
        for pattern_str in self.ABNORMAL_KEYWORDS:
            pattern = re.compile(re.escape(pattern_str), re.IGNORECASE)
            matches = pattern.findall(text)
            count = len(matches)
            if count >= min_count and pattern_str.lower() not in self.existing_words:
                target_suggested = self.DEFAULT_TRANSLATION_MAP.get(pattern_str.lower(), pattern_str)
                results_map[pattern_str.lower()] = ScannedCandidate(
                    phrase=pattern_str,
                    count=count,
                    candidate_type="Lỗi dịch máy",
                    sample_contexts=self._get_contexts(text, pattern_str),
                    suggested_target=target_suggested
                )

        # 2. Quét cấu trúc sở hữu ngược: "của (hắn|nàng|ngươi|ta) + [danh từ]"
        # Ví dụ: "của hắn chị dâu" -> "chị dâu của hắn"
        possessive_pattern = re.compile(r'\b(của\s+(?:hắn|nàng|ngươi|ta)\s+([a-zà-ỹA-ZÀ-Ỹ]+(?:\s+[a-zà-ỹA-ZÀ-Ỹ]+)?))\b', re.IGNORECASE)
        pos_counts: Counter = Counter()
        for m in possessive_pattern.finditer(text):
            full_match = m.group(1).strip()
            # Bỏ qua nếu là "của hắn là", "của hắn có"
            words = full_match.lower().split()
            if len(words) >= 3 and words[2] not in {"là", "có", "sẽ", "được", "bị", "mà", "đến"}:
                pos_counts[full_match] += 1

        for phrase, count in pos_counts.items():
            phrase_clean = phrase.lower()
            if count >= min_count and phrase_clean not in self.existing_words:
                words = phrase_clean.split()
                # Gợi ý đảo vị trí: "của hắn chị dâu" -> "chị dâu của hắn"
                pronoun = words[1]
                noun_part = " ".join(words[2:])
                suggested = f"{noun_part} của {pronoun}"
                results_map[phrase_clean] = ScannedCandidate(
                    phrase=phrase_clean,
                    count=count,
                    candidate_type="Cấu trúc Hán",
                    sample_contexts=self._get_contexts(text, phrase),
                    suggested_target=suggested
                )

        # 3. Quét cấu trúc lượng từ Hán: "một cái [sáu bảy tuổi|cổ lão|tuyết trắng...] đứa nhỏ/nông thôn/cánh tay"
        quantifier_pattern = re.compile(r'\b(một\s+cái\s+[a-zà-ỹ0-9\-]+(?:\s+[a-zà-ỹ0-9\-]+){1,3}\s+đứa\s+nhỏ)\b', re.IGNORECASE)
        for m in quantifier_pattern.finditer(text):
            full_match = m.group(1).strip()
            phrase_clean = full_match.lower()
            # Đếm số lần
            c_matches = len(re.findall(re.escape(full_match), text, re.IGNORECASE))
            if c_matches >= min_count and phrase_clean not in self.existing_words:
                results_map[phrase_clean] = ScannedCandidate(
                    phrase=phrase_clean,
                    count=c_matches,
                    candidate_type="Cấu trúc Hán",
                    sample_contexts=self._get_contexts(text, full_match),
                    suggested_target=phrase_clean.replace("một cái", "một").replace("đứa nhỏ", "đứa trẻ")
                )

        # 4. Quét cấu trúc vị ngữ Hán: "đang ở + [động từ 1-2 từ]"
        # Ví dụ: "đang ở cởi quần áo"
        aspect_pattern = re.compile(r'\b(đang\s+ở\s+[a-zà-ỹ]+(?:\s+[a-zà-ỹ]+){1,2})\b', re.IGNORECASE)
        aspect_counts: Counter = Counter()
        for m in aspect_pattern.finditer(text):
            full_match = m.group(1).strip()
            # Lọc bỏ nếu từ sau là địa điểm như "đang ở nhà", "đang ở trường", "đang ở đây"
            words = full_match.lower().split()
            if len(words) >= 3 and words[2] not in {"nhà", "trường", "đây", "đó", "bên", "trong", "phòng"}:
                aspect_counts[full_match] += 1

        for phrase, count in aspect_counts.items():
            phrase_clean = phrase.lower()
            if count >= min_count and phrase_clean not in self.existing_words:
                suggested = phrase_clean.replace("đang ở ", "đang ")
                results_map[phrase_clean] = ScannedCandidate(
                    phrase=phrase_clean,
                    count=count,
                    candidate_type="Cấu trúc Hán",
                    sample_contexts=self._get_contexts(text, phrase),
                    suggested_target=suggested
                )

        # Sắp xếp kết quả theo tần suất giảm dần
        sorted_results = sorted(results_map.values(), key=lambda x: x.count, reverse=True)
        return sorted_results

    def scan_text(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        nouns = self.extract_proper_nouns(text, min_count=min_count)
        abnormals = self.extract_abnormal_patterns(text, min_count=min_count)
        return nouns + abnormals
