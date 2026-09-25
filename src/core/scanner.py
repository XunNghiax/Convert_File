import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Set, Optional, Dict, Tuple, Callable
from pydantic import BaseModel
from src.config import Config
from src.core.grammar_corrector import GrammarCorrector

def title_case_vietnamese(text: str) -> str:

    """Viết hoa chữ cái đầu cho mỗi từ trong tên riêng tiếng Việt."""
    return " ".join(w.capitalize() for w in text.strip().split())

class ScannedCandidate(BaseModel):
    phrase: str
    count: int
    candidate_type: str  # "Tên nhân vật", "Lỗi dịch máy", "Cấu trúc Hán", "Cấu trúc sở hữu ngược", "Từ bất thường"
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
        "vài cái", "một cái", "vài người", "hai người", "mọi người", "trên bờ",
        "nhưng là", "tỷ tỷ", "muội muội", "ca ca", "đệ đệ", "bá phụ", "bá mẫu", "cha mẹ"
    }

    # Danh sách từ cấm tuyệt đối mặc định (blacklist)
    DEFAULT_BLACKLIST: Set[str] = set()

    # Các từ chỉ địa danh, tổ chức, phi nhân vật (tránh nhận nhầm tên người)
    DEFAULT_NON_PERSON: Set[str] = {
        "thành phố", "thị trấn", "thị xã", "quận huyện", "trường học", "bệnh viện",
        "công ty", "đại lâu", "khách sạn", "nhà hàng", "sân bay", "bến xe", "quân đội",
        "thôn trang", "nông thôn", "sơn hải", "thiên địa", "nhật nguyệt", "nam phương",
        "bắc kinh", "thượng hải", "trung nguyên", "hoàng hà", "hoàng đế",
        "tập đoàn", "biệt thự", "chung cư", "phòng khám", "cục cảnh sát", "đồn cảnh sát",
        "quán bar", "siêu thị", "trung tâm thương mại", "y viện", "phòng bệnh",
        "phòng cấp cứu", "phòng phẫu thuật", "ký túc xá", "giảng đường", "căn tin",
        "nhà vệ sinh", "phòng tắm", "phòng khách", "phòng ngủ", "phòng bếp",
        "thư phòng", "ban giám đốc", "cổ đông", "hội đồng"
    }

    # Các động từ thường đi liền sau tên riêng (tránh bắt nhầm "Phi cười", "Phi chậm")
    COMMON_VERBS_FOLLOWING = {
        "cười", "nói", "hỏi", "đáp", "nghĩ", "nhìn", "thấy", "chậm", "chạy",
        "đến", "đi", "ngồi", "đứng", "nằm", "quay", "bước", "nhảy", "kêu", "la", "hét"
    }

    # Đại từ nhân xưng và các từ mở đầu câu tuyệt đối không phải là tên riêng
    DEFAULT_PRONOUNS_AND_STARTS: Set[str] = {
        "hắn", "nàng", "ta", "ngươi", "tôi", "tao", "mày", "chúng", "bọn", "họ",
        "nó", "y", "thị", "mình", "người", "ai", "kẻ", "gã", "tên", "vị", "con",
        "cái", "thứ", "việc", "chuyện", "đứa", "tiểu tử", "nha đầu", "lão giả",
        "thanh niên", "thiếu nữ", "đứa nhỏ", "cô gái", "bác sĩ", "y tá",
        "khi", "lúc", "sau", "trước", "trong", "ngoài", "trên", "dưới", "giữa", "bên",
        "tại", "ở", "từ", "đến", "tới", "về", "vào", "ra", "lên", "xuống", "qua", "lại",
        "nếu", "bởi", "vì", "do", "nhưng", "tuy", "dù", "dẫu", "thế", "vậy",
        "vừa", "đang", "đã", "sẽ", "mới", "chưa", "chẳng", "không", "có", "rồi",
        "hôm nay", "ngày mai", "hôm qua", "chúng ta", "bọn họ", "tuy nhiên", "nhưng mà",
        "sau đó", "trước đó", "bởi vì", "như vậy", "không có", "có thể", "ông ấy", "bà ấy",
        "đột nhiên", "vào lúc", "lúc này", "một lát", "không biết", "người này", "thời điểm",
        "mặc dù", "cho nên", "đồng thời", "thậm chí", "nhìn thấy", "nói cách khác",
        "kết quả", "chính là", "nếu như", "bất quá", "chỉ là", "chỉ có", "nguyên lai",
        "trong lòng", "lập tức", "vừa rồi", "hiện tại", "thực ra", "kỳ thật",
        "dù sao", "ngược lại", "không thể", "chẳng lẽ", "hơn nữa", "ngoài ra",
        "trên thực tế", "không bao lâu", "vài ngày sau", "sau khi", "một bên",
        "đúng vậy", "quả nhiên", "bỗng nhiên", "một lát sau", "trong chốc lát",
        "chính văn", "chương", "tiết", "tập", "hồi", "vài cái", "một cái",
        "vài người", "hai người", "mọi người", "trên bờ", "nhưng là"
    }

    # Các từ đi sau tên người (động từ hành động, hư từ, phó từ) tuyệt đối không ghép vào tên
    DEFAULT_TRAILING_STOPWORDS: Set[str] = {
        # Động từ:
        "cười", "nói", "hỏi", "đáp", "nghĩ", "nhìn", "thấy", "chậm", "chạy",
        "đến", "đi", "ngồi", "đứng", "nằm", "quay", "bước", "nhảy", "kêu", "la", "hét",
        "mang", "mặc", "cầm", "lấy", "cho", "đưa", "gặp", "biết", "hiểu", "nhớ", "quên",
        "yêu", "thích", "ghét", "sợ", "muốn", "cần", "phải", "nên", "được", "bị", "làm",
        "tạo", "viết", "đọc", "xem", "nghe", "ăn", "uống", "ngủ", "dậy", "mở", "đóng",
        "bắt", "thả", "giữ", "bỏ", "tìm", "kiếm", "chọn", "mua", "bán", "trả", "mượn",
        "gửi", "nhận", "đem", "dẫn", "kéo", "đẩy", "đặt", "để", "chờ", "đợi", "dừng",
        "thôi", "xong", "hết", "thở", "cảm", "tâm", "hướng", "liếc", "nhấc", "bảo", "kể",
        "mừng", "giận", "hận", "khóc", "buông", "ôm", "hôn", "đánh", "đấm", "đá", "giết",
        "chết", "sống", "bay", "lặn", "trốn", "thoát", "cứu", "giúp", "theo",
        # Hư từ, phó từ, liên từ, đại từ:
        "rốt", "rốt cuộc", "không", "chưa", "chẳng", "cũng", "lại", "trong", "ngoài",
        "trên", "dưới", "với", "cùng", "và", "hoặc", "nhưng", "mà", "thì", "là", "ở",
        "tại", "rất", "quá", "lắm", "hơi", "khá", "cực", "càng", "luôn", "thường", "hay",
        "ít", "nhiều", "đã", "đang", "sẽ", "vừa", "mới", "ngay", "liền", "chợt", "bỗng",
        "tự", "hãy", "đừng", "chớ", "nào", "gì", "đâu", "sao", "thế", "vậy", "nhất",
        "nữa", "mãi", "rồi", "kìa", "này", "đó", "kia", "ấy", "nọ", "hắn", "nàng", "ta"
    }

    # Biến tương thích ngược cho các lớp con hoặc tham chiếu ngoài
    COMMON_NON_PERSON_WORDS = DEFAULT_NON_PERSON
    COMMON_PRONOUNS_AND_STARTS = DEFAULT_PRONOUNS_AND_STARTS
    COMMON_TRAILING_STOPWORDS = DEFAULT_TRAILING_STOPWORDS

    # Các danh từ thường đứng trước 'của' trong cấu trúc sở hữu thuận (tham chiếu nguồn tập trung từ GrammarCorrector)
    COMMON_POSSESSIVE_NOUNS: Set[str] = GrammarCorrector.COMMON_POSSESSIVE_NOUNS


    _V_UPPER = "A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
    _V_LOWER = "a-zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"

    # Danh sách Họ phổ biến trong truyện tiếng Trung / Việt (chữ thường để đối chiếu)
    VIET_CHINESE_SURNAMES = {
        # Các họ gốc đã cung cấp
        "nguyễn", "trần", "lê", "phạm", "hoàng", "huỳnh", "phan", "vũ", "võ", "đặng",
        "bùi", "đỗ", "hồ", "ngô", "dương", "lý", "liễu", "chu", "khưu", "hạ", "mai",
        "trương", "long", "tiêu", "lâm", "tần", "tạ", "cố", "thẩm", "giang", "bạch",
        "phương", "diệp", "tô", "tiết", "tống", "hàn", "lưu", "triệu", "vương", "tôn",
        "châu", "đới", "phùng", "lục", "tiền", "quách", "khương", "ân", "thường", "mạnh",
        "kim", "doãn", "nghiêm", "thôi", "hứa", "gia cát", "tư mã", "âu dương", "mộ dung", "lỗ",
        "điền",
        
        # Các họ đơn Trung Quốc bổ sung
        "mã", "la", "tào", "ngụy", "đường", "thạch", "hùng", "nhậm", "lương", "hồng", 
        "đoàn", "trình", "kiều", "bàng", "đinh", "tưởng", "phó", "mao", "bành", "dư", 
        "khang", "chúc", "kỷ", "chung", "sử", "vạn", "ôn", "biện", "sầm", "lôi", "du", 
        "cung", "thang", "nguyên", "nhạc", "địch", "lư", "bồ", "niếp", "phù", "dữu",
        
        # Các họ kép (phức danh) Trung Quốc bổ sung
        "đông phương", "tây môn", "nam cung", "bắc minh", "công tôn", "hoàng phủ", 
        "thượng quan", "lệnh hồ", "độc cô", "tư đồ", "hạ hầu", "uất trì"
    }

    # Hậu tố danh xưng thân tộc/vai vế thường đi sau tên riêng
    HONORIFIC_SUFFIXES = {
        "tỷ", "ca", "muội", "đệ", "bác", "thúc", "tẩu", "sư", "lão", "bá",
        "tổng", "đổng", "viện trưởng", "cục trưởng", "sở trưởng", "hiệu trưởng",
        "thiếu", "gia", "phu nhân", "mẫu", "tôn", "thần", "đế", "vương"
    }

    # Tiền tố chức danh / danh xưng thường đi trước tên
    HONORIFIC_PREFIXES = {
        "bác sĩ", "chủ nhiệm", "quản lí", "quản lý", "trưởng phòng", "giáo sư", "y tá", "lão sư", "phu nhân", "tiểu thư",
        "tiểu", "lão", "đại", "a", "tổng giám đốc", "giám đốc", "đổng sự trưởng", "thị trưởng", "bí thư", "cảnh sát", "cảnh quan", "đội trưởng", "luật sư"
    }

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
        "đại quản lí", "phó quản lý", "chocolate mỹ nữ",
        # Extended Urban & Web Novel MT Keywords:
        "tính lãnh đạm", "kéo đen", "nhục ti", "hắc ti", "bạch ti", "màu da tất chân",
        "phú nhị đại", "tinh nhị đại", "quan nhị đại", "tiểu tam", "khuê mật", "cẩu huyết",
        "tóc húi cua", "điện quang hỏa thạch", "ngưu bức", "trang bức", "sa điêu", "đỉnh lưu",
        "tiểu thịt tươi", "lên hot search", "hot search", "tọa kỵ", "thượng phô", "hạ phô",
        "tắm rửa một cái", "trảo phách", "không có ý tứ", "có ý tứ", "đánh xe",
        "ngồi xổm phòng giam", "chụp đùi", "đầu đầy hắc tuyến", "hắc tuyến"
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
        "nghàng an ninh": "ngành an ninh",
        "đại quản lí": "giám đốc",
        "phó quản lý": "phó giám đốc",
        "tính lãnh đạm": "lãnh cảm",
        "kéo đen": "chặn / block",
        "nhục ti": "quần tất màu da",
        "hắc ti": "quần tất đen",
        "bạch ti": "quần tất trắng",
        "màu da tất chân": "quần tất màu da",
        "phú nhị đại": "con nhà giàu / thiếu gia",
        "quan nhị đại": "con ông cháu cha",
        "tinh nhị đại": "con của sao",
        "tiểu tam": "kẻ thứ ba",
        "khuê mật": "bạn thân",
        "cẩu huyết": "máu chó / kịch tính",
        "tóc húi cua": "tóc đinh",
        "điện quang hỏa thạch": "chớp nhoáng",
        "ngưu bức": "lợi hại / trâu bò",
        "trang bức": "ra vẻ / làm màu",
        "sa điêu": "ngu ngốc / hài hước",
        "tiểu thịt tươi": "mỹ nam / sao nam trẻ",
        "đánh xe": "gọi taxi",
        "ngồi xổm phòng giam": "ngồi tù",
        "chụp đùi": "vỗ đùi",
        "hắc tuyến": "cạn lời",
        "đầu đầy hắc tuyến": "vạch đen đầy đầu / cạn lời",
        "không có ý tứ": "ngại quá / xin lỗi",
        "có ý tứ": "thú vị",
        "thượng phô": "giường tầng trên",
        "hạ phô": "giường tầng dưới",
        "tắm rửa một cái": "tắm rửa",
        "tọa kỵ": "thú cưỡi",
        "trảo phách": "chụp bắt / bắt lấy",
        "đỉnh lưu": "ngôi sao hàng đầu",
        "hot search": "tìm kiếm nóng / top thịnh hành",
        "lên hot search": "lên top thịnh hành"
    }

    @classmethod
    def _ensure_filter_files(cls, filters_dir: Path):
        filters_dir = Path(filters_dir)
        filters_dir.mkdir(parents=True, exist_ok=True)

        files_to_create = [
            (
                filters_dir / "blacklist.txt",
                "# DANH SÁCH TỪ CẤM TUYỆT ĐỐI (BLACKLIST)\n"
                "# Mọi từ hoặc cụm từ trong danh sách này sẽ bị loại bỏ hoàn toàn khỏi kết quả quét.\n"
                "# Mỗi dòng một từ/cụm từ (không phân biệt hoa/thường). Dòng bắt đầu bằng # là chú thích.\n\n",
                cls.DEFAULT_BLACKLIST,
            ),
            (
                filters_dir / "pronouns.txt",
                "# DANH SÁCH ĐẠI TỪ NHÂN XƯNG & TỪ MỞ ĐẦU CÂU (PRONOUNS & STARTS)\n"
                "# Các từ này tuyệt đối không được đứng đầu trong tên nhân vật hoặc tên riêng.\n"
                "# Mỗi dòng một từ/cụm từ (không phân biệt hoa/thường). Dòng bắt đầu bằng # là chú thích.\n\n",
                cls.DEFAULT_PRONOUNS_AND_STARTS,
            ),
            (
                filters_dir / "trailing_stopwords.txt",
                "# DANH SÁCH ĐỘNG TỪ & TRỢ TỪ Ở ĐUÔI (TRAILING STOPWORDS)\n"
                "# Trong cụm 2 từ, nếu từ thứ hai là từ trong danh sách này thì cụm đó không phải tên riêng (ví dụ: 'Phi mang', 'Hắn nhìn').\n"
                "# Mỗi dòng một từ (không phân biệt hoa/thường). Dòng bắt đầu bằng # là chú thích.\n\n",
                cls.DEFAULT_TRAILING_STOPWORDS,
            ),
            (
                filters_dir / "non_person.txt",
                "# DANH SÁCH TỪ PHI NHÂN VẬT (NON-PERSON / ĐỊA DANH / TỔ CHỨC)\n"
                "# Các từ chỉ địa danh, trường học, bệnh viện, đồ vật, khái niệm không phải tên người.\n"
                "# Mỗi dòng một từ/cụm từ (không phân biệt hoa/thường). Dòng bắt đầu bằng # là chú thích.\n\n",
                cls.DEFAULT_NON_PERSON,
            ),
        ]

        for filepath, header, word_set in files_to_create:
            if not filepath.exists():
                content = header + "\n".join(sorted(word_set)) + "\n"
                filepath.write_text(content, encoding="utf-8")

    @staticmethod
    def _read_filter_file(path: Path) -> Set[str]:
        words = set()
        if not path.exists():
            return words
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    words.add(line.lower())
        except Exception:
            pass
        return words

    def load_filters(self, filters_dir: Optional[Path] = None):
        if filters_dir is not None:
            self.filters_dir = Path(filters_dir)
        elif not hasattr(self, "filters_dir") or self.filters_dir is None:
            self.filters_dir = Config.FILTERS_DIR

        self._ensure_filter_files(self.filters_dir)

        bl = self._read_filter_file(self.filters_dir / "blacklist.txt")
        pr = self._read_filter_file(self.filters_dir / "pronouns.txt")
        tr = self._read_filter_file(self.filters_dir / "trailing_stopwords.txt")
        np = self._read_filter_file(self.filters_dir / "non_person.txt")

        self.blacklist = set(bl)
        self.pronouns_and_starts = set(pr) if pr else set(self.DEFAULT_PRONOUNS_AND_STARTS)
        self.trailing_stopwords = set(tr) if tr else set(self.DEFAULT_TRAILING_STOPWORDS)
        self.non_person_words = set(np) if np else set(self.DEFAULT_NON_PERSON)

        self.COMMON_PRONOUNS_AND_STARTS = self.pronouns_and_starts
        self.COMMON_TRAILING_STOPWORDS = self.trailing_stopwords
        self.COMMON_NON_PERSON_WORDS = self.non_person_words

    def reload_filters(self) -> Dict[str, int]:
        self.load_filters()
        return {
            "blacklist": len(self.blacklist),
            "pronouns": len(self.pronouns_and_starts),
            "trailing_stopwords": len(self.trailing_stopwords),
            "non_person": len(self.non_person_words),
        }

    def __init__(self, existing_words: Optional[Set[str]] = None, filters_dir: Optional[Path] = None):
        self.existing_words = {w.lower() for w in (existing_words or set())}
        # Tự động loại trừ các cụm con của các từ đã có trong từ điển (vd: có "long kiếm phi" -> loại "long kiếm", "kiếm phi")
        self.existing_subphrases = set()
        for w in self.existing_words:
            sub = w.split()
            if len(sub) >= 3:
                for l in range(2, len(sub)):
                    for i in range(len(sub) - l + 1):
                        self.existing_subphrases.add(" ".join(sub[i:i+l]))

        self.filters_dir = Path(filters_dir) if filters_dir is not None else Config.FILTERS_DIR
        self._ensure_filter_files(self.filters_dir)
        self.load_filters(self.filters_dir)


        self._possessive_pattern = GrammarCorrector.REVERSE_POSSESSION_PATTERN
        self._quantifier_pattern = re.compile(
            r'\b(một\s+cái\s+[a-zà-ỹ0-9\-]+(?:\s+[a-zà-ỹ0-9\-]+){1,3}\s+đứa\s+nhỏ)\b',
            re.IGNORECASE
        )
        self._aspect_pattern = re.compile(
            r'\b(đang\s+ở\s+[a-zà-ỹ]+(?:\s+[a-zà-ỹ]+){1,2})\b',
            re.IGNORECASE
        )
        word_proper = rf"[{self._V_UPPER}][{self._V_LOWER}]*"
        self._prefix_patterns = [
            (prefix, re.compile(rf"\b(?i:{re.escape(prefix)})\s+({word_proper}(?:\s+{word_proper})?)", re.UNICODE))
            for prefix in sorted(self.HONORIFIC_PREFIXES, key=len, reverse=True)
        ]

    @classmethod
    def extract_context_snippet(cls, line_str: str, phrase: str, target_len: int = 240) -> str:
        """
        Trích xuất ngữ cảnh xung quanh cụm từ mục tiêu một cách thông minh:
        - Luôn đảm bảo cụm từ mục tiêu nằm ở trung tâm của đoạn trích (không bị cắt cụt).
        - Căn chỉnh tự nhiên theo ranh giới câu (dấu chấm, chấm hỏi, chấm than, dấu ngoặc kép) hoặc ranh giới từ.
        - Độ dài mục tiêu ~240 ký tự giúp AI và người dùng có đầy đủ thông tin ngữ cảnh để phân tích.
        """
        line_clean = " ".join(line_str.strip().split())
        if not line_clean:
            return ""

        pos = line_clean.lower().find(phrase.lower())
        if pos == -1:
            return line_clean[:target_len].strip()

        if len(line_clean) <= target_len:
            return line_clean

        phrase_len = len(phrase)
        margin = max(30, (target_len - phrase_len) // 2)
        left = max(0, pos - margin)
        right = min(len(line_clean), pos + phrase_len + margin)

        if left == 0:
            right = min(len(line_clean), target_len)
        elif right == len(line_clean):
            left = max(0, len(line_clean) - target_len)

        # Căn chỉnh lề trái theo ranh giới câu hoặc từ
        if left > 0:
            sent_bound = -1
            for punct in ('. ', '! ', '? ', '." ', '!" ', '?" ', '.” ', '!” ', '?” '):
                p_idx = line_clean.rfind(punct, max(0, left - 40), pos)
                if p_idx != -1 and p_idx > sent_bound:
                    sent_bound = p_idx + len(punct)
            if sent_bound != -1 and (pos - sent_bound) <= (target_len - phrase_len):
                left = sent_bound
            else:
                space_idx = line_clean.find(' ', left)
                if space_idx != -1 and space_idx <= pos:
                    left = space_idx + 1

        # Căn chỉnh lề phải theo ranh giới câu hoặc từ
        if right < len(line_clean):
            sent_bound = -1
            for punct in ('. ', '! ', '? ', '."', '!"', '?"', '.”', '!”', '?”'):
                p_idx = line_clean.find(punct, pos + phrase_len, min(len(line_clean), right + 40))
                if p_idx != -1 and (sent_bound == -1 or p_idx < sent_bound):
                    sent_bound = p_idx + (1 if punct in ('. ', '! ', '? ') else len(punct))
            if sent_bound != -1 and (sent_bound - left) <= target_len + 50:
                right = sent_bound
            else:
                space_idx = line_clean.rfind(' ', pos + phrase_len, right)
                if space_idx != -1:
                    right = space_idx

        prefix = "... " if left > 0 else ""
        suffix = " ..." if right < len(line_clean) else ""
        return f"{prefix}{line_clean[left:right].strip()}{suffix}"

    def _get_contexts(self, text: str, phrase: str, max_contexts: int = 2) -> List[str]:
        contexts = []
        for line in text.splitlines():
            line_str = line.strip()
            if phrase.lower() in line_str.lower():
                ctx = self.extract_context_snippet(line_str, phrase)
                if ctx and ctx not in contexts:
                    contexts.append(ctx)
                if len(contexts) >= max_contexts:
                    break
        return contexts

    def extract_proper_nouns(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        text = unicodedata.normalize('NFC', text)
        noun_counts = Counter()
        suggested_map = {}
        noun_contexts = defaultdict(list)
        dummy_counts = Counter()
        dummy_types = {}
        dummy_targets = {}
        dummy_contexts = defaultdict(list)

        for line in text.splitlines():
            self._process_line(
                line,
                noun_counts,
                suggested_map,
                noun_contexts,
                dummy_counts,
                dummy_types,
                dummy_targets,
                dummy_contexts
            )

        cands = self._build_candidates(
            min_count=min_count,
            noun_counts=noun_counts,
            suggested_map=suggested_map,
            noun_contexts=noun_contexts,
            abnormal_counts=Counter(),
            abnormal_type_map={},
            abnormal_target_map={},
            abnormal_contexts=defaultdict(list)
        )
        return [c for c in cands if c.candidate_type == "Tên nhân vật"]

    def extract_abnormal_patterns(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        text = unicodedata.normalize('NFC', text)
        dummy_counts = Counter()
        dummy_sugg = {}
        dummy_noun_ctx = defaultdict(list)
        abnormal_counts = Counter()
        abnormal_types = {}
        abnormal_targets = {}
        abnormal_contexts = defaultdict(list)

        for line in text.splitlines():
            self._process_line(
                line,
                dummy_counts,
                dummy_sugg,
                dummy_noun_ctx,
                abnormal_counts,
                abnormal_types,
                abnormal_targets,
                abnormal_contexts
            )

        cands = self._build_candidates(
            min_count=min_count,
            noun_counts=Counter(),
            suggested_map={},
            noun_contexts=defaultdict(list),
            abnormal_counts=abnormal_counts,
            abnormal_type_map=abnormal_types,
            abnormal_target_map=abnormal_targets,
            abnormal_contexts=abnormal_contexts
        )
        return [c for c in cands if c.candidate_type != "Tên nhân vật"]

    def scan_text(self, text: str, min_count: int = 2) -> List[ScannedCandidate]:
        text = unicodedata.normalize('NFC', text)
        noun_counts = Counter()
        suggested_map = {}
        noun_contexts = defaultdict(list)
        abnormal_counts = Counter()
        abnormal_types = {}
        abnormal_targets = {}
        abnormal_contexts = defaultdict(list)

        for line in text.splitlines():
            self._process_line(
                line,
                noun_counts,
                suggested_map,
                noun_contexts,
                abnormal_counts,
                abnormal_types,
                abnormal_targets,
                abnormal_contexts
            )

        return self._build_candidates(
            min_count=min_count,
            noun_counts=noun_counts,
            suggested_map=suggested_map,
            noun_contexts=noun_contexts,
            abnormal_counts=abnormal_counts,
            abnormal_type_map=abnormal_types,
            abnormal_target_map=abnormal_targets,
            abnormal_contexts=abnormal_contexts
        )

    def _process_line(
        self,
        line: str,
        noun_counts: Counter,
        suggested_map: Dict[str, str],
        noun_contexts: Dict[str, List[str]],
        abnormal_counts: Counter,
        abnormal_type_map: Dict[str, str],
        abnormal_target_map: Dict[str, str],
        abnormal_contexts: Dict[str, List[str]],
    ):
        line_str = line.strip()
        if not line_str:
            return

        # 1. Quét tên nhân vật & danh xưng
        words = re.findall(r'[^\W\d_]+', line_str)
        n = len(words)

        for length in (4, 3, 2):
            for i in range(n - length + 1):
                ngram = words[i:i+length]
                phrase = " ".join(ngram)
                phrase_lower = phrase.lower()

                # 0. Bỏ qua nếu từ thuộc blacklist tuyệt đối
                if phrase_lower in self.blacklist or phrase in self.blacklist:
                    continue

                first_word_lower = ngram[0].lower()
                # 1. Bỏ qua nếu từ đầu tiên là đại từ hoặc từ nối đầu câu thông dụng (Nàng, Hắn, Ta...)
                if first_word_lower in self.pronouns_and_starts:
                    continue

                if phrase_lower in self.COMMON_START_WORDS or phrase_lower in self.existing_words or phrase_lower in self.existing_subphrases or phrase_lower in self.non_person_words:
                    continue

                if any(np_w in phrase_lower for np_w in self.non_person_words):
                    continue

                # 2. Bỏ qua nếu từ thứ hai trong cụm 2 từ là động từ hoặc hư từ/phó từ đi sau tên (Phi mang, Nàng mặc...)
                if length == 2 and ngram[1].lower() in self.trailing_stopwords:
                    continue

                is_known_surname = first_word_lower in self.VIET_CHINESE_SURNAMES

                # Trường hợp 1A: Tên chuẩn viết hoa từng từ (Long Kiếm Phi, Trương Tử Kiến)
                if all(w[0].isupper() for w in ngram):
                    if length == 2 and not is_known_surname and (phrase_lower in self.COMMON_START_WORDS or ngram[1].lower() in self.trailing_stopwords):
                        continue
                    noun_counts[phrase] += 1
                    if phrase not in suggested_map:
                        suggested_map[phrase] = phrase
                    if len(noun_contexts[phrase]) < 2:
                        ctx = self.extract_context_snippet(line_str, phrase)
                        if ctx and ctx not in noun_contexts[phrase]:
                            noun_contexts[phrase].append(ctx)

                # Trường hợp 1B: Họ viết hoa, âm sau viết thường (Liễu Ngọc như, Chu Ngọc mị, Khưu ngọc trinh)
                elif ngram[0][0].isupper() and is_known_surname and (length in (2, 3)):
                    if length == 2 and ngram[1].lower() in self.trailing_stopwords:
                        continue
                    noun_counts[phrase] += 1
                    if phrase not in suggested_map:
                        suggested_map[phrase] = title_case_vietnamese(phrase)
                    if len(noun_contexts[phrase]) < 2:
                        ctx = self.extract_context_snippet(line_str, phrase)
                        if ctx and ctx not in noun_contexts[phrase]:
                            noun_contexts[phrase].append(ctx)

                # Trường hợp 1C: Tên nửa Tây nửa Việt (Gavin phong) hoặc họ + tên thường (Lỗ quân)
                elif ngram[0][0].isupper() and all(w.islower() for w in ngram[1:]) and length == 2:
                    is_foreign = bool(re.search(r'[wfjzWFJZ]', ngram[0])) or ngram[0].lower() in {
                        "gavin", "david", "peter", "john", "mary", "jack", "tom", "alex"
                    }
                    if (is_known_surname or is_foreign) and ngram[1].lower() not in self.trailing_stopwords:
                        noun_counts[phrase] += 1
                        if phrase not in suggested_map:
                            suggested_map[phrase] = title_case_vietnamese(phrase)
                        if len(noun_contexts[phrase]) < 2:
                            ctx = self.extract_context_snippet(line_str, phrase)
                            if ctx and ctx not in noun_contexts[phrase]:
                                noun_contexts[phrase].append(ctx)

        for i in range(n - 1):
            first_w = words[i]
            matched_suffix = None
            if i + 2 < n:
                candidate_suffix_2 = f"{words[i+1]} {words[i+2]}".lower()
                if candidate_suffix_2 in self.HONORIFIC_SUFFIXES:
                    matched_suffix = candidate_suffix_2

            if not matched_suffix:
                candidate_suffix_1 = words[i+1].lower()
                if candidate_suffix_1 in self.HONORIFIC_SUFFIXES:
                    matched_suffix = candidate_suffix_1

            if matched_suffix:
                if (
                    first_w[0].isupper()
                    and first_w.lower() not in self.pronouns_and_starts
                    and first_w.lower() not in self.non_person_words
                ):
                    name_phrase = f"{first_w} {matched_suffix}"
                    name_phrase_lower = name_phrase.lower()
                    if name_phrase_lower in self.blacklist or name_phrase in self.blacklist:
                        continue
                    if name_phrase_lower in self.existing_words or name_phrase_lower in self.existing_subphrases:
                        continue
                    noun_counts[name_phrase] += 1
                    if name_phrase not in suggested_map:
                        suggested_map[name_phrase] = f"{first_w.capitalize()} {matched_suffix}"
                    if len(noun_contexts[name_phrase]) < 2:
                        ctx = self.extract_context_snippet(line_str, name_phrase)
                        if ctx and ctx not in noun_contexts[name_phrase]:
                            noun_contexts[name_phrase].append(ctx)

        for prefix, p_pattern in self._prefix_patterns:
            for m in p_pattern.finditer(line_str):
                full_match = m.group(0).strip()
                full_match_lower = full_match.lower()
                if full_match_lower in self.blacklist or full_match in self.blacklist:
                    continue
                if full_match_lower in self.existing_words or full_match_lower in self.existing_subphrases:
                    continue
                name_part = m.group(1).strip()
                if (
                    name_part.lower() not in self.COMMON_START_WORDS
                    and name_part.lower() not in self.blacklist
                    and name_part.lower() not in self.trailing_stopwords
                    and name_part.lower() not in self.non_person_words
                ):
                    noun_counts[full_match] += 1
                    if full_match not in suggested_map:
                        suggested_map[full_match] = full_match
                    if len(noun_contexts[full_match]) < 2:
                        ctx = self.extract_context_snippet(line_str, full_match)
                        if ctx and ctx not in noun_contexts[full_match]:
                            noun_contexts[full_match].append(ctx)

        # 2. Quét lỗi dịch máy & Cấu trúc Hán
        line_lower = line_str.lower()
        for kw in self.ABNORMAL_KEYWORDS:
            if kw.lower() in line_lower:
                if kw.lower() in self.blacklist or kw in self.blacklist:
                    continue
                c_matches = len(re.findall(re.escape(kw), line_str, re.IGNORECASE))
                if c_matches > 0 and kw.lower() not in self.existing_words:
                    abnormal_counts[kw.lower()] += c_matches
                    abnormal_type_map[kw.lower()] = "Lỗi dịch máy"
                    abnormal_target_map[kw.lower()] = self.DEFAULT_TRANSLATION_MAP.get(kw.lower(), kw)
                    if len(abnormal_contexts[kw.lower()]) < 2:
                        ctx = self.extract_context_snippet(line_str, kw)
                        if ctx and ctx not in abnormal_contexts[kw.lower()]:
                            abnormal_contexts[kw.lower()].append(ctx)

        PRONOUN_OWNERS = {"hắn", "nàng", "y", "thị", "ta", "ngươi", "bọn họ", "chúng nó"}
        for m in GrammarCorrector.REVERSE_POSSESSION_PATTERN.finditer(line_str):
            cua_part = m.group(1)      # 'của' hoặc 'Của'
            owner = m.group(2)         # 'hắn', 'Lệ Na', etc.
            noun_part = m.group(3)     # cụm từ sau chủ thể

            noun_words = noun_part.strip().split()
            if not noun_words:
                continue

            first_noun_word = noun_words[0].lower()
            if first_noun_word in GrammarCorrector.NON_NOUN_WORDS:
                continue

            valid_len = len(noun_words)
            for i in range(1, len(noun_words)):
                if noun_words[i].lower() in GrammarCorrector.NON_NOUN_WORDS:
                    valid_len = i
                    break

            if valid_len == 3:
                two_words = f"{noun_words[0]} {noun_words[1]}".lower()
                three_words = f"{noun_words[0]} {noun_words[1]} {noun_words[2]}".lower()
                if two_words in self.COMMON_POSSESSIVE_NOUNS and three_words not in self.COMMON_POSSESSIVE_NOUNS:
                    valid_len = 2

            actual_noun = " ".join(noun_words[:valid_len])

            # Guard clause: Tránh đảo nhầm khi trước 'của' đã có danh từ (sở hữu thuận)
            before_text = line_str[:m.start()].rstrip()
            if before_text:
                last_char = before_text[-1]
                if last_char not in {',', '.', '!', '?', ';', ':', '"', "'", '“', '”', '‘', '’', '—', '–', '-', '(', ')', '[', ']', '{', '}', '…'}:
                    prev_words = re.findall(r'[^\W\d_]+', before_text)
                    if prev_words:
                        prev_word = prev_words[-1].lower()
                        prev_2words = f"{prev_words[-2]} {prev_words[-1]}".lower() if len(prev_words) >= 2 else ""
                        if prev_word in self.COMMON_POSSESSIVE_NOUNS or prev_2words in self.COMMON_POSSESSIVE_NOUNS:
                            continue
                        if prev_word in self.non_person_words or prev_2words in self.non_person_words:
                            continue

            owner_clean = owner.lower() if owner.lower() in PRONOUN_OWNERS else owner
            phrase = f"{cua_part.lower()} {owner_clean} {actual_noun}"
            phrase_lower = phrase.lower()

            if phrase_lower in self.existing_words or phrase_lower in self.blacklist or phrase in self.blacklist:
                continue

            suggested, fix_count = GrammarCorrector.fix_reverse_possession(phrase)
            if fix_count == 0:
                continue

            abnormal_counts[phrase] += 1
            abnormal_type_map[phrase] = "Cấu trúc sở hữu ngược"
            abnormal_target_map[phrase] = suggested
            if len(abnormal_contexts[phrase]) < 2:
                ctx = self.extract_context_snippet(line_str, phrase)
                if ctx and ctx not in abnormal_contexts[phrase]:
                    abnormal_contexts[phrase].append(ctx)

        for m in self._quantifier_pattern.finditer(line_str):
            full_match = m.group(1).strip()
            p_clean = full_match.lower()
            if p_clean not in self.existing_words and p_clean not in self.blacklist:
                abnormal_counts[p_clean] += 1
                abnormal_type_map[p_clean] = "Cấu trúc Hán"
                abnormal_target_map[p_clean] = p_clean.replace("một cái", "một").replace("đứa nhỏ", "đứa trẻ")
                if len(abnormal_contexts[p_clean]) < 2:
                    ctx = self.extract_context_snippet(line_str, full_match)
                    if ctx and ctx not in abnormal_contexts[p_clean]:
                        abnormal_contexts[p_clean].append(ctx)

        for m in self._aspect_pattern.finditer(line_str):
            full_match = m.group(1).strip()
            w_split = full_match.lower().split()
            if len(w_split) >= 3 and w_split[2] not in {"nhà", "trường", "đây", "đó", "bên", "trong", "phòng"}:
                p_clean = full_match.lower()
                if p_clean not in self.existing_words and p_clean not in self.blacklist:
                    abnormal_counts[p_clean] += 1
                    abnormal_type_map[p_clean] = "Cấu trúc Hán"
                    abnormal_target_map[p_clean] = p_clean.replace("đang ở ", "đang ")
                    if len(abnormal_contexts[p_clean]) < 2:
                        ctx = self.extract_context_snippet(line_str, full_match)
                        if ctx and ctx not in abnormal_contexts[p_clean]:
                            abnormal_contexts[p_clean].append(ctx)

    def _build_candidates(
        self,
        min_count: int,
        noun_counts: Counter,
        suggested_map: Dict[str, str],
        noun_contexts: Dict[str, List[str]],
        abnormal_counts: Counter,
        abnormal_type_map: Dict[str, str],
        abnormal_target_map: Dict[str, str],
        abnormal_contexts: Dict[str, List[str]],
    ) -> List[ScannedCandidate]:
        eligible_nouns = [(phrase, count) for phrase, count in noun_counts.items() if count >= min_count]
        eligible_nouns.sort(key=lambda x: len(x[0]), reverse=True)
        filtered_counts = {}
        for phrase, count in eligible_nouns:
            is_sub = False
            for longer_phrase, longer_count in filtered_counts.items():
                if phrase in longer_phrase and count <= longer_count:
                    is_sub = True
                    break
            if not is_sub:
                filtered_counts[phrase] = count

        nouns = []
        for phrase, count in sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True):
            phrase_lower = phrase.lower()
            if phrase_lower in self.blacklist or phrase in self.blacklist:
                continue
            if phrase_lower in self.existing_words or phrase_lower in self.existing_subphrases:
                continue
            ctxs = noun_contexts.get(phrase, [])
            nouns.append(ScannedCandidate(
                phrase=phrase,
                count=count,
                candidate_type="Tên nhân vật",
                sample_contexts=ctxs,
                suggested_target=suggested_map.get(phrase, title_case_vietnamese(phrase))
            ))

        abnormals = []
        for phrase_clean, count in sorted(abnormal_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= min_count:
                phrase_clean_lower = phrase_clean.lower()
                if phrase_clean_lower in self.blacklist or phrase_clean in self.blacklist:
                    continue
                if phrase_clean_lower in self.existing_words:
                    continue
                ctxs = abnormal_contexts.get(phrase_clean, [])
                abnormals.append(ScannedCandidate(
                    phrase=phrase_clean,
                    count=count,
                    candidate_type=abnormal_type_map.get(phrase_clean, "Lỗi dịch máy"),
                    sample_contexts=ctxs,
                    suggested_target=abnormal_target_map.get(phrase_clean, phrase_clean)
                ))

        return nouns + abnormals

    def _save_checkpoint(
        self,
        candidates: List[ScannedCandidate],
        scanned_dir: Path,
        novel_name: str,
        export_partition: bool = False,
        partition_size: int = 50,
        on_save_checkpoint: Optional[Callable[[List[ScannedCandidate], Path, Path], None]] = None
    ):
        from src.core.scan_exporter import ScanExporter
        scanned_dir = Path(scanned_dir)
        scanned_dir.mkdir(parents=True, exist_ok=True)
        safe_novel_name = ScanExporter._sanitize_filename(novel_name) if novel_name else "scanned_novel"

        if export_partition:
            part_files, master_json = ScanExporter.export_partitioned(
                candidates, safe_novel_name, scanned_dir, part_size=partition_size
            )
            txt_target = part_files[0] if part_files else (scanned_dir / f"{safe_novel_name}_review.txt")
            if on_save_checkpoint:
                on_save_checkpoint(candidates, master_json, txt_target)
        else:
            json_path, txt_path = ScanExporter.auto_export_scanned(
                candidates, safe_novel_name, scanned_dir
            )
            if on_save_checkpoint:
                on_save_checkpoint(candidates, json_path, txt_path)

    def scan_file_streaming(
        self,
        file_path: Path,
        min_count: int = 2,
        chunk_size_bytes: int = 64 * 1024,
        on_chunk_progress: Optional[Callable[[int, int, int], None]] = None,
        scanned_dir: Optional[Path] = None,
        novel_name: str = "",
        save_interval_chunks: int = 5,
        on_save_checkpoint: Optional[Callable[[List[ScannedCandidate], Path, Path], None]] = None,
        export_partition: bool = False,
        partition_size: int = 50,
    ) -> List[ScannedCandidate]:
        """
        Quét file truyện theo luồng (streaming) từng chunk nhị phân để:
        1. Tránh tràn bộ nhớ RAM trên các file lớn (>30-50MB).
        2. Tự động lưu checkpoint liên tục vào thư mục scanned/ theo chu kỳ chunk.
        3. Cập nhật tiến trình (bytes_read, total_bytes, count) theo thời gian thực.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return []

        total_bytes = file_path.stat().st_size
        if total_bytes == 0:
            return []

        if scanned_dir:
            scanned_dir = Path(scanned_dir)
            scanned_dir.mkdir(parents=True, exist_ok=True)
            if not novel_name:
                novel_name = file_path.stem

        noun_counts: Counter = Counter()
        suggested_map: Dict[str, str] = {}
        noun_contexts: Dict[str, List[str]] = defaultdict(list)
        abnormal_counts: Counter = Counter()
        abnormal_type_map: Dict[str, str] = {}
        abnormal_target_map: Dict[str, str] = {}
        abnormal_contexts: Dict[str, List[str]] = defaultdict(list)

        bytes_read = 0
        chunk_idx = 0
        remainder = b""

        with open(file_path, "rb") as f:
            while True:
                raw_bytes = f.read(chunk_size_bytes)
                if not raw_bytes:
                    break

                bytes_read += len(raw_bytes)
                data = remainder + raw_bytes
                last_newline = data.rfind(b"\n")
                if last_newline != -1:
                    chunk_bytes = data[:last_newline + 1]
                    remainder = data[last_newline + 1:]
                else:
                    if len(data) > chunk_size_bytes * 4:
                        chunk_bytes = data
                        remainder = b""
                    else:
                        remainder = data
                        continue

                chunk_text = unicodedata.normalize('NFC', chunk_bytes.decode("utf-8", errors="replace"))
                for line in chunk_text.splitlines():
                    self._process_line(
                        line,
                        noun_counts,
                        suggested_map,
                        noun_contexts,
                        abnormal_counts,
                        abnormal_type_map,
                        abnormal_target_map,
                        abnormal_contexts
                    )
                chunk_idx += 1

                if on_chunk_progress:
                    curr_cand = self._build_candidates(
                        min_count=min_count,
                        noun_counts=noun_counts,
                        suggested_map=suggested_map,
                        noun_contexts=noun_contexts,
                        abnormal_counts=abnormal_counts,
                        abnormal_type_map=abnormal_type_map,
                        abnormal_target_map=abnormal_target_map,
                        abnormal_contexts=abnormal_contexts
                    )
                    on_chunk_progress(bytes_read, total_bytes, len(curr_cand))

                if scanned_dir and (chunk_idx % save_interval_chunks == 0):
                    curr_cand = self._build_candidates(
                        min_count=min_count,
                        noun_counts=noun_counts,
                        suggested_map=suggested_map,
                        noun_contexts=noun_contexts,
                        abnormal_counts=abnormal_counts,
                        abnormal_type_map=abnormal_type_map,
                        abnormal_target_map=abnormal_target_map,
                        abnormal_contexts=abnormal_contexts
                    )
                    if curr_cand:
                        self._save_checkpoint(
                            candidates=curr_cand,
                            scanned_dir=scanned_dir,
                            novel_name=novel_name or file_path.stem,
                            export_partition=export_partition,
                            partition_size=partition_size,
                            on_save_checkpoint=on_save_checkpoint
                        )

        if remainder:
            chunk_text = unicodedata.normalize('NFC', remainder.decode("utf-8", errors="replace"))
            for line in chunk_text.splitlines():
                self._process_line(
                    line,
                    noun_counts,
                    suggested_map,
                    noun_contexts,
                    abnormal_counts,
                    abnormal_type_map,
                    abnormal_target_map,
                    abnormal_contexts
                )

        final_candidates = self._build_candidates(
            min_count=min_count,
            noun_counts=noun_counts,
            suggested_map=suggested_map,
            noun_contexts=noun_contexts,
            abnormal_counts=abnormal_counts,
            abnormal_type_map=abnormal_type_map,
            abnormal_target_map=abnormal_target_map,
            abnormal_contexts=abnormal_contexts
        )

        if on_chunk_progress and bytes_read < total_bytes:
            on_chunk_progress(total_bytes, total_bytes, len(final_candidates))

        if scanned_dir:
            self._save_checkpoint(
                candidates=final_candidates,
                scanned_dir=scanned_dir,
                novel_name=novel_name or file_path.stem,
                export_partition=export_partition,
                partition_size=partition_size,
                on_save_checkpoint=on_save_checkpoint
            )

        return final_candidates

