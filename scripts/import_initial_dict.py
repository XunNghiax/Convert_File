import re
from pathlib import Path
from src.config import Config
from src.core.dict_manager import DictManager

def import_dictionary():
    config = Config()
    dict_mgr = DictManager(config.COMMON_DICT_PATH, config.CHARACTER_DICT_PATH)
    dict_file = config.BASE_DIR / "dictionary.txt"
    
    if not dict_file.exists():
        print("Không tìm thấy dictionary.txt")
        return

    content = dict_file.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    count = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Nhân vật") or line.startswith("("):
            continue
        
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if parts:
            name = parts[0]
            has_gender_or_age = len(parts) > 1 and any("tuổi" in p or p.lower() in ["nam", "nữ"] for p in parts[1:])
            if has_gender_or_age and 2 <= len(name.split()) <= 5:
                # Chuẩn hóa viết hoa chữ cái đầu cho tên
                name_clean = " ".join([w.capitalize() for w in name.split()])
                role = ", ".join(parts[1:]) if len(parts) > 1 else ""
                try:
                    dict_mgr.add_character_term(source=name, target=name_clean, novel_tag="Thiếu Long", gender_role=role[:50])
                    count += 1
                except ValueError:
                    pass

    # Thêm một vài từ dịch thô phổ biến mẫu vào common_dict.json
    sample_common_terms = [
        ("đương gia hoa đán", "ngôi sao trụ cột", "Lỗi dịch máy"),
        ("đợi ảnh thị kịch", "các phim ảnh", "Lỗi dịch máy"),
        ("lấy gã bác sĩ", "gả cho bác sĩ", "Lỗi dịch máy"),
        ("thành thục mỹ phụ", "mỹ phụ chín chắn", "Cụm từ Hán Việt"),
        ("tiêu thụ bộ quản lí", "trưởng phòng kinh doanh", "Thuật ngữ"),
        ("ba ba", "bố", "Xưng hô"),
        ("ma ma", "mẹ", "Xưng hô"),
        ("đệ đệ", "em trai", "Xưng hô"),
        ("muội muội", "em gái", "Xưng hô"),
        ("nữ nhi", "con gái", "Xưng hô"),
    ]
    added_common = 0
    for src, tgt, cat in sample_common_terms:
        try:
            dict_mgr.add_common_term(source=src, target=tgt, category=cat)
            added_common += 1
        except ValueError:
            pass

    print(f"Đã nạp thành công {count} nhân vật vào character_dict.json và {added_common} từ phổ biến vào common_dict.json!")

if __name__ == "__main__":
    import_dictionary()
