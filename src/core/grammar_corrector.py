import re
from typing import Tuple, Set

class GrammarCorrector:
    """
    Module xử lý và nắn chỉnh các lỗi ngữ pháp đặc thù trong văn bản convert Hán Việt.
    """
    # Các từ hư từ, trợ từ, liên từ, động từ không cấu thành danh từ sở hữu
    NON_NOUN_WORDS: Set[str] = {
        # Đại từ, hư từ, trợ từ, liên từ
        "là", "có", "không", "chưa", "đã", "sẽ", "đang", "phải", "được", "bị",
        "vốn", "tại", "cho", "với", "như", "thì", "mà", "bởi", "vì", "đều",
        "cũng", "rất", "quá", "lắm", "hơn", "nhất", "ngươi", "ta", "hắn", "nàng",
        "đó", "đây", "này", "kia", "rồi", "sao", "đâu", "gì", "nhé", "nha", "à", "ơi",
        "hả", "chứ", "thế", "vậy", "y", "thị", "họ", "chúng", "bọn", "nó", "ai", "kẻ",
        # Phó từ, liên từ, giới từ, hư từ mở rộng
        "chẳng", "vừa", "mới", "lại", "nhưng", "hoặc", "và", "cùng", "trong", "ngoài",
        "trên", "dưới", "ở", "tự", "hãy", "đừng", "chớ", "luôn", "thường", "càng",
        "ngay", "liền", "chỉ", "còn", "nữa", "qua", "sang", "lên", "xuống", "vào",
        "ra", "tới", "đến", "lấy", "bèn", "tức", "thôi", "chăng",
        "hết", "xong", "chợt", "bỗng", "mãi", "rốt", "rốt cuộc", "hơi", "khá", "cực",
        "hay", "ít", "nhiều", "nào", "kìa", "ấy", "nọ",
        # Động từ hành động phổ biến đi sau danh từ / chủ ngữ (trailing stopwords)
        "cười", "nói", "hỏi", "đáp", "nghĩ", "nhìn", "thấy", "chậm", "chạy",
        "đi", "ngồi", "đứng", "nằm", "quay", "bước", "nhảy", "kêu", "la", "hét",
        "mang", "mặc", "cầm", "đưa", "gặp", "biết", "hiểu", "nhớ", "quên",
        "yêu", "thích", "ghét", "sợ", "muốn", "cần", "nên", "làm", "tạo", "viết",
        "đọc", "xem", "nghe", "ăn", "uống", "ngủ", "dậy", "mở", "đóng", "bắt",
        "thả", "giữ", "bỏ", "tìm", "chọn", "mua", "bán", "trả", "mượn", "gửi",
        "nhận", "đem", "dẫn", "kéo", "đẩy", "đặt", "để", "chờ", "đợi", "dừng",
        "thở", "liếc", "nhấc", "bảo", "kể", "mừng", "giận", "hận", "khóc",
        "buông", "ôm", "đánh", "đấm", "đá", "giết", "chết", "sống", "bay",
        "lặn", "trốn", "thoát", "cứu", "giúp", "theo",
        # Các động từ và phó từ thường gặp khác
        "nắm", "hiện", "nhẹ", "run", "chém", "vỗ"
    }

    # Các danh từ thường đứng trước 'của' trong cấu trúc sở hữu thuận (tránh nhận nhầm là sở hữu ngược)
    COMMON_POSSESSIVE_NOUNS: Set[str] = {
        # Bộ phận cơ thể
        "tay", "bàn tay", "chân", "bàn chân", "mắt", "ánh mắt", "đôi mắt", "mặt", "gương mặt", "khuôn mặt",
        "mũi", "miệng", "môi", "tai", "đầu", "tóc", "mái tóc", "vai", "bờ vai", "lưng", "ngực", "bụng",
        "thân", "thân thể", "thể xác", "xương", "thịt", "máu", "da", "làn da", "hơi thở", "nụ cười",
        "thủ", "mông", "háng", "nách", "cổ", "gáy", "eo", "đùi", "ngón tay", "cánh tay", "bắp tay",
        "hàm", "răng", "lưỡi", "trán", "sắc mặt", "thần sắc", "khí tức",
        # Đại từ nhân xưng, thân tộc, quan hệ
        "người", "người yêu", "bạn", "bạn thân", "bạn bè", "cha", "mẹ", "ba", "má", "bố", "anh", "chị", "em",
        "con", "cháu", "ông", "bà", "vợ", "chồng", "phu thê", "đối thủ", "kẻ thù", "đồng đội", "sư phụ",
        "đồ đệ", "thầy", "trò", "huynh đệ", "tỷ muội", "thê tử", "ái nhân", "hôn thê", "vị hôn thê",
        "chị dâu", "anh rể", "em dâu", "em rể", "con dâu", "con rể",
        "thuộc hạ", "thủ hạ", "chủ nhân", "tùy tùng", "đối tác", "trợ lý", "thư ký",
        # Đồ vật, tài sản, địa điểm, từ chỉ loại
        "áo", "quần", "váy", "giày", "dép", "nón", "mũ", "túi", "ví", "tiền", "bạc", "nhà", "xe", "phòng",
        "cửa", "bàn", "ghế", "sách", "vở", "bút", "kiếm", "đao", "vũ khí", "bảo vật", "đồ", "vật",
        "bức", "cuốn", "quyển", "chiếc", "cây", "tấm", "lá", "viên", "hạt", "bông", "mảnh", "tranh", "ảnh",
        "bức tranh", "bức ảnh", "súng", "khẩu súng", "thanh kiếm", "thanh đao", "đao kiếm", "phi kiếm",
        "bảo kiếm", "linh kiếm", "chiếc xe", "ngôi nhà", "căn nhà", "căn phòng", "tài sản", "gia sản",
        "gia đình", "cơ nghiệp", "điện thoại", "máy tính", "bức thư", "lá thư", "thư", "hộ chiếu", "chìa khóa",
        "góc áo", "vạt áo", "tay áo", "cổ áo",
        # Khái niệm tổ chức, cơ sở, địa điểm
        "công ty", "tập đoàn", "doanh nghiệp", "chi nhánh", "trường học", "bệnh viện", "khách sạn", "nhà hàng",
        "quân đội", "gia tộc", "môn phái", "tông môn", "bang phái", "bang hội", "đội", "nhóm", "phòng ban",
        # Khái niệm trừu tượng, tâm lý, lời nói
        "lời", "tiếng", "giọng", "giọng nói", "câu", "ý", "ý nghĩ", "suy nghĩ", "tâm", "lòng", "tâm tư",
        "tình cảm", "tình yêu", "nỗi đau", "niềm vui", "kế hoạch", "ý định", "quyết định", "hành động",
        "kết quả", "công lao", "tội lỗi", "sai lầm", "bí mật", "cuộc sống", "số phận", "vận mệnh",
        "tương lai", "quá khứ", "chuyện", "việc", "sức mạnh", "năng lực", "thực lực", "tu vi", "quyền lực",
        "địa vị", "danh tiếng", "uy tín", "tâm trạng", "cảm xúc", "thái độ"
    }

    _V_UPPER = "A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
    _V_LOWER = "a-zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    _V_ALL = _V_UPPER + _V_LOWER

    _PROPER_NAME = rf"[{_V_UPPER}][{_V_LOWER}]*(?:\s+[{_V_UPPER}][{_V_LOWER}]*)*"
    _PRONOUNS = r"[Hh]ắn|[Nn]àng|[Yy]|[Tt]hị|[Tt]a|[Nn]gươi|[Bb]ọn họ|[Cc]húng nó"
    _OWNER = rf"(?:{_PROPER_NAME}|{_PRONOUNS})"

    # Pattern bắt cấu trúc: [của] [Chủ thể] [Danh từ 1-3 từ]
    REVERSE_POSSESSION_PATTERN = re.compile(
        rf"\b([Cc]ủa|CỦA)\s+({_OWNER})\s+([{_V_ALL}]+(?:\s+[{_V_ALL}]+){{0,2}})\b",
        re.UNICODE
    )

    @classmethod
    def fix_reverse_possession(cls, text: str) -> Tuple[str, int]:
        """
        Nắn chỉnh cấu trúc sở hữu ngược:
        'của hắn bàn tay' -> 'bàn tay của hắn'
        'Của hắn bàn tay' -> 'Bàn tay của hắn'
        """
        if not text or "của" not in text.lower():
            return text, 0

        fix_count = 0

        def _replace_callback(match: re.Match) -> str:
            nonlocal fix_count

            # Guard clause: Tránh đảo nhầm khi trước 'của' đã có danh từ (sở hữu thuận)
            before_text = text[:match.start()].rstrip()
            if before_text:
                last_char = before_text[-1]
                if last_char not in {',', '.', '!', '?', ';', ':', '"', "'", '“', '”', '‘', '’', '—', '–', '-', '(', ')', '[', ']', '{', '}', '…'}:
                    prev_words = re.findall(r'[^\W\d_]+', before_text)
                    if prev_words:
                        prev_word = prev_words[-1].lower()
                        prev_2words = f"{prev_words[-2]} {prev_words[-1]}".lower() if len(prev_words) >= 2 else ""
                        if prev_word in cls.COMMON_POSSESSIVE_NOUNS or prev_2words in cls.COMMON_POSSESSIVE_NOUNS:
                            return match.group(0)

            cua_raw = match.group(1)      # 'của' hoặc 'Của'
            owner = match.group(2)        # 'hắn', 'Lệ Na', etc.
            noun_phrase = match.group(3)  # cụm danh từ sau chủ thể

            words = noun_phrase.strip().split()
            if not words:
                return match.group(0)

            first_noun_word = words[0].lower()
            if first_noun_word in cls.NON_NOUN_WORDS:
                return match.group(0)

            valid_len = len(words)
            for i in range(1, len(words)):
                if words[i].lower() in cls.NON_NOUN_WORDS:
                    valid_len = i
                    break

            # Nếu 2 từ đầu đã là danh từ sở hữu trọn vẹn trong COMMON_POSSESSIVE_NOUNS,
            # và cụm 3 từ không phải là danh từ sở hữu, không nuốt từ thứ 3 vào danh từ
            if valid_len == 3:
                two_words = f"{words[0]} {words[1]}".lower()
                three_words = f"{words[0]} {words[1]} {words[2]}".lower()
                if two_words in cls.COMMON_POSSESSIVE_NOUNS and three_words not in cls.COMMON_POSSESSIVE_NOUNS:
                    valid_len = 2

            actual_noun = " ".join(words[:valid_len])
            leftover = (" " + " ".join(words[valid_len:])) if valid_len < len(words) else ""

            fix_count += 1
            # Xử lý viết hoa đầu câu nếu 'Của' viết hoa
            if cua_raw[0].isupper():
                # Viết hoa chữ đầu của cụm danh từ đưa lên
                noun_title = actual_noun[0].upper() + actual_noun[1:]
                return f"{noun_title} của {owner}{leftover}"
            else:
                return f"{actual_noun} {cua_raw.lower()} {owner}{leftover}"

        result = cls.REVERSE_POSSESSION_PATTERN.sub(_replace_callback, text)
        return result, fix_count
