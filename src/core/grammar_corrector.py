import re
from typing import Tuple, Set

class GrammarCorrector:
    """
    Module xử lý và nắn chỉnh các lỗi ngữ pháp đặc thù trong văn bản convert Hán Việt.
    """
    # Các từ hư từ, trợ từ, liên từ, động từ không cấu thành danh từ sở hữu
    NON_NOUN_WORDS: Set[str] = {
        "là", "có", "không", "chưa", "đã", "sẽ", "đang", "phải", "được", "bị",
        "vốn", "tại", "cho", "với", "như", "thì", "mà", "bởi", "vì", "đều",
        "cũng", "rất", "quá", "lắm", "hơn", "nhất", "ngươi", "ta", "hắn", "nàng",
        "đó", "đây", "này", "kia", "rồi", "sao", "đâu", "gì", "nhé", "nha", "à", "ơi",
        "hả", "chứ", "thế", "vậy", "y", "thị", "họ"
    }

    _V_UPPER = "A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
    _V_LOWER = "a-zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    _V_ALL = _V_UPPER + _V_LOWER

    _PROPER_NAME = rf"[{_V_UPPER}][{_V_LOWER}]+(?:\s+[{_V_UPPER}][{_V_LOWER}]+)*"
    _PRONOUNS = r"[Hh]ắn|[Nn]àng|[Yy]|[Tt]hị|[Tt]a|[Nn]gươi|[Bb]ọn họ|[Cc]húng nó"
    _OWNER = rf"(?:{_PROPER_NAME}|{_PRONOUNS})"

    # Pattern bắt cấu trúc: [của] [Chủ thể] [Danh từ 1-2 âm tiết]
    REVERSE_POSSESSION_PATTERN = re.compile(
        rf"\b([Cc]ủa|CỦA)\s+({_OWNER})\s+([{_V_ALL}]+(?:\s+[{_V_ALL}]+)?)\b",
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
            cua_raw = match.group(1)      # 'của' hoặc 'Của'
            owner = match.group(2)        # 'hắn', 'Lệ Na', etc.
            noun_phrase = match.group(3)  # 'bàn tay'

            words = noun_phrase.strip().split()
            if not words:
                return match.group(0)

            first_noun_word = words[0].lower()
            if first_noun_word in cls.NON_NOUN_WORDS:
                return match.group(0)

            if len(words) > 1 and words[1].lower() in cls.NON_NOUN_WORDS:
                actual_noun = words[0]
                leftover = " " + " ".join(words[1:])
            else:
                actual_noun = noun_phrase
                leftover = ""

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
