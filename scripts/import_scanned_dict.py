import sys
import os
import argparse
import time
import unicodedata
from pathlib import Path
from datetime import datetime

# Đảm bảo PYTHONPATH bao gồm thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Cấu hình UTF-8 cho console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

from src.config import Config
from src.core.dict_manager import DictManager, CommonTerm, CharacterTerm

def log(level: str, message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if HAS_COLOR:
        color_map = {
            "INFO": Fore.CYAN,
            "IMPORT": Fore.MAGENTA,
            "SUCCESS": Fore.GREEN,
            "WARN": Fore.YELLOW + Style.BRIGHT,
            "ERROR": Fore.RED + Style.BRIGHT,
            "NEW": Fore.GREEN + Style.BRIGHT,
            "UPDATE": Fore.YELLOW,
            "SKIP": Fore.LIGHTBLACK_EX,
        }
        color = color_map.get(level, Fore.WHITE)
        print(f"[{Fore.WHITE}{timestamp}{Style.RESET_ALL}] [{color}{level:<7}{Style.RESET_ALL}] {message}")
    else:
        print(f"[{timestamp}] [{level:<7}] {message}")

def print_banner():
    banner = """
========================================================================
     NOVEL TRANSLATION REFINER - SCAN IMPORT & DICTIONARY SYNC
========================================================================
"""
    if HAS_COLOR:
        print(Fore.CYAN + Style.BRIGHT + banner)
    else:
        print(banner)

def infer_novel_tag(file_path: Path) -> str:
    """Tự động suy đoán tag truyện từ tên file."""
    stem = file_path.stem
    if stem.lower() in ("import", "default", "data"):
        return "Thiếu Long"
    for suffix in ["_candidates", "_review", "_scan", "_edited"]:
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
    return stem or "Thiếu Long"

def run_import(file_path: Path, novel_tag: str = "", dry_run: bool = False) -> int:
    config = Config()
    dict_mgr = DictManager(config.COMMON_DICT_PATH, config.CHARACTER_DICT_PATH)

    if not file_path.exists():
        log("ERROR", f"Không tìm thấy file: {file_path}")
        return 1

    if not novel_tag:
        novel_tag = infer_novel_tag(file_path)

    log("INFO", f"Tệp nguồn scan: {file_path.name}")
    log("INFO", f"Tag truyện mặc định: '{novel_tag}'")
    if dry_run:
        log("WARN", "CHẾ ĐỘ DRY-RUN: Chỉ phân tích và kiểm tra, không ghi vào file từ điển.")

    try:
        records = dict_mgr.parse_scanned_file(file_path)
    except Exception as e:
        log("ERROR", f"Lỗi đọc file: {e}")
        return 1

    if not records:
        log("WARN", "Không tìm thấy bản ghi nào trong file.")
        return 0

    log("INFO", f"Đã tìm thấy {len(records)} mục cần xử lý từ file.")

    if dry_run:
        print("\n" + "="*80)
        print(" DANH SÁCH XEM TRƯỚC (PREVIEW - DRY RUN)")
        print("="*80)
        print(f"{'Loại':<15} | {'Từ gốc (Source)':<25} | {'Từ thay thế (Target)':<25} | {'Phân loại / Tag'}")
        print("-" * 80)
        for r in records[:20]:
            src = str(r.get("source") or r.get("phrase") or "")
            tgt = str(r.get("target") or r.get("suggested_target") or src)
            cat = str(r.get("category") or r.get("type") or "Chung")
            is_char = r.get("is_character", False) or cat.lower() in ["tên nhân vật", "nhân vật"]
            type_str = "Nhân vật" if is_char else "Từ phổ biến"
            tag_str = novel_tag if is_char else cat
            print(f"{type_str:<15} | {src:<25} | {tgt:<25} | {tag_str}")
        if len(records) > 20:
            print(f"... và còn {len(records) - 20} mục khác.")
        print("="*80 + "\n")
        return 0

    # Thực hiện nạp thật
    log("IMPORT", "Đang xử lý phân loại và đồng bộ vào từ điển...")
    start_time = time.time()
    res = dict_mgr.import_records(records, default_novel_tag=novel_tag)
    elapsed = time.time() - start_time

    # Chuẩn hóa lại từ điển để bảo đảm ID tuần tự và không trùng lặp
    std_stats = dict_mgr.standardize_dictionaries()

    # In kết quả chi tiết
    print("\n" + "="*80)
    print(" CHI TIẾT ĐỒNG BỘ TỪ ĐIỂN")
    print("="*80)
    print(f"  • Tổng số mục đã quét/nhận:  {res['total_records']}")
    print(f"  ─────────────────────────────────────────────────────────────")
    print(f"  • TÊN NHÂN VẬT (character_dict.json):")
    print(f"     + Thêm mới (New):       {res['chars_added']}")
    print(f"     ~ Cập nhật (Updated):   {res['chars_updated']}")
    print(f"     = Giữ nguyên (Skipped): {res['chars_skipped']}")
    print(f"     => Tổng số nhân vật:    {std_stats['character_after']} mục")
    print(f"  ─────────────────────────────────────────────────────────────")
    print(f"  • TỪ PHỔ BIẾN / DỊCH THÔ (common_dict.json):")
    print(f"     + Thêm mới (New):       {res['common_added']}")
    print(f"     ~ Cập nhật (Updated):   {res['common_updated']}")
    print(f"     = Giữ nguyên (Skipped): {res['common_skipped']}")
    print(f"     => Tổng số từ phổ biến: {std_stats['common_after']} mục")
    print("="*80)
    log("SUCCESS", f"Đồng bộ hoàn tất thành công trong {elapsed:.2f} giây!\n")
    return 0

def run_standardize_only():
    config = Config()
    dict_mgr = DictManager(config.COMMON_DICT_PATH, config.CHARACTER_DICT_PATH)
    log("INFO", "Đang chuẩn hóa toàn bộ file từ điển...")
    stats = dict_mgr.standardize_dictionaries()
    print("\n" + "="*80)
    print(" KẾT QUẢ CHUẨN HÓA TỪ ĐIỂN")
    print("="*80)
    print(f"  • Từ phổ biến (common_dict.json):")
    print(f"     - Trước: {stats['common_before']} mục | Sau: {stats['common_after']} mục | Đã khử trùng: {stats['common_deduped']}")
    print(f"  • Tên nhân vật (character_dict.json):")
    print(f"     - Trước: {stats['character_before']} mục | Sau: {stats['character_after']} mục | Đã khử trùng: {stats['character_deduped']}")
    print(f"  • Chuẩn mã: Unicode NFC (đã xử lý triệt để dấu tổ hợp NFD)")
    print(f"  • Mã ID: Đánh số tuần tự co-1..N và ch-1..N")
    print("="*80 + "\n")
    log("SUCCESS", "Chuẩn hóa hoàn tất!")
    return 0

def interactive_wizard():
    print_banner()
    config = Config()
    default_file = getattr(config, "DEFAULT_IMPORT_PATH", BASE_DIR / "import.txt")
    has_default = default_file.exists()

    print("📋 CHỌN CHỨC NĂNG:")
    if has_default:
        print(f"   [1] Nạp file mặc định '{default_file.name}' (Khuyên dùng)")
        print("   [2] Chọn file scan từ thư mục 'scanned/'")
        print("   [3] Nhập đường dẫn file scan tùy ý (kéo thả hoặc dán path)")
        print("   [4] Chỉ chuẩn hóa lại từ điển hiện tại (NFC, khử trùng, đánh lại ID)")
        default_choice = "1"
    else:
        print("   [1] Chọn file scan từ thư mục 'scanned/'")
        print("   [2] Nhập đường dẫn file scan tùy ý (kéo thả hoặc dán path)")
        print("   [3] Chỉ chuẩn hóa lại từ điển hiện tại (NFC, khử trùng, đánh lại ID)")
        default_choice = "1"

    choice = input(f"👉 Lựa chọn [{'1/2/3/4' if has_default else '1/2/3'}] [Mặc định: {default_choice}]: ").strip()
    if not choice:
        choice = default_choice

    if (has_default and choice == "4") or (not has_default and choice == "3"):
        run_standardize_only()
        input("\nNhấn Enter để kết thúc...")
        return

    target_file = None
    if has_default and choice == "1":
        target_file = default_file
    elif (has_default and choice == "2") or (not has_default and choice == "1"):
        scanned_files = list(config.SCANNED_DIR.glob("*.*"))
        # Lọc các file json và txt
        valid_files = [f for f in scanned_files if f.suffix.lower() in [".json", ".txt"]]
        if not valid_files:
            print(f"\n{Fore.YELLOW if HAS_COLOR else ''}⚠️ Thư mục 'scanned/' chưa có file nào. Chuyển sang chế độ nhập đường dẫn file...{Style.RESET_ALL if HAS_COLOR else ''}")
            target_file = None
        else:
            print(f"\n📂 CÁC FILE TRONG THƯ MỤC 'scanned/':")
            for idx, f in enumerate(valid_files, start=1):
                size_kb = f.stat().st_size / 1024
                print(f"   [{idx}] {f.name} ({size_kb:.1f} KB)")
            file_choice = input(f"👉 Chọn số [1-{len(valid_files)}] hoặc dán tên file: ").strip()
            if file_choice.isdigit() and 1 <= int(file_choice) <= len(valid_files):
                target_file = valid_files[int(file_choice) - 1]
            else:
                found = next((f for f in valid_files if file_choice.lower() in f.name.lower()), None)
                if found:
                    target_file = found

    if not target_file:
        print("\n📂 NHẬP ĐƯỜNG DẪN FILE:")
        prompt_hint = f" [Mặc định: {default_file.name}]" if has_default else ""
        print(f"   (Kéo thả file vào cửa sổ terminal hoặc dán đường dẫn{prompt_hint})")
        while True:
            raw_path = input(f"👉 Đường dẫn file{prompt_hint}: ").strip()
            clean_path = raw_path.strip("\"'")
            if not clean_path and has_default:
                target_file = default_file
                break
            if clean_path:
                tf = Path(clean_path)
                if not tf.is_absolute():
                    tf = BASE_DIR / tf
                if tf.exists() and tf.is_file():
                    target_file = tf
                    break
            print(f"{Fore.RED if HAS_COLOR else ''}❌ Không tìm thấy file. Vui lòng nhập lại!{Style.RESET_ALL if HAS_COLOR else ''}")

    # Suy đoán tag truyện
    default_tag = infer_novel_tag(target_file)
    print(f"\n🏷️ TAG BỘ TRUYỆN CHO NHÂN VẬT:")
    tag_input = input(f"👉 Tag truyện [Mặc định: '{default_tag}']: ").strip()
    novel_tag = tag_input if tag_input else default_tag

    # Hỏi xác nhận
    print(f"\n{Fore.GREEN if HAS_COLOR else ''}✔ Đã chọn file: {target_file.name}{Style.RESET_ALL if HAS_COLOR else ''}")
    print(f"{Fore.GREEN if HAS_COLOR else ''}✔ Tag nhân vật: {novel_tag}{Style.RESET_ALL if HAS_COLOR else ''}")
    confirm = input("👉 Bạn có muốn tiến hành nạp vào từ điển ngay không? (y/n) [Mặc định: y]: ").strip().lower()
    if confirm in ("", "y", "yes"):
        run_import(target_file, novel_tag=novel_tag, dry_run=False)
    else:
        print("Đã hủy thao tác.")

    # Tùy chọn mở thư mục data/
    open_data = input("📂 Bạn có muốn mở thư mục chứa từ điển 'data/' không? (y/n) [Mặc định: n]: ").strip().lower()
    if open_data in ("y", "yes"):
        try:
            if sys.platform == "win32":
                os.startfile(str(config.DATA_DIR))
            else:
                import subprocess
                subprocess.run(["xdg-open", str(config.DATA_DIR)])
        except Exception as e:
            print(f"Không thể mở thư mục tự động: {e}")

    input("\nNhấn Enter để kết thúc...")

def main():
    if len(sys.argv) == 1:
        interactive_wizard()
        return

    parser = argparse.ArgumentParser(description="Novel Translation Refiner - Scan Import & Dictionary Sync")
    parser.add_argument("--file", "-f", type=str, default="import.txt", help="Đường dẫn đến file scan cần nạp (mặc định: import.txt)")
    parser.add_argument("--tag", "-t", type=str, default="", help="Tag truyện cho nhân vật (mặc định: suy đoán theo tên file)")
    parser.add_argument("--standardize-only", action="store_true", help="Chỉ chuẩn hóa từ điển hiện tại (NFC, khử trùng, đánh lại ID)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Chỉ xem trước các mục, không lưu vào file từ điển")
    parser.add_argument("--yes", "-y", action="store_true", help="Tự động đồng ý không hỏi lại")

    args = parser.parse_args()
    print_banner()

    if args.standardize_only:
        sys.exit(run_standardize_only())

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = BASE_DIR / file_path

    if not file_path.exists():
        log("ERROR", f"Không tìm thấy file: {file_path}")
        sys.exit(1)

    code = run_import(file_path, novel_tag=args.tag, dry_run=args.dry_run)
    sys.exit(code)

if __name__ == "__main__":
    main()
