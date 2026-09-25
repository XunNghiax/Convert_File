import sys
import os
import argparse
import time
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
from src.core.dict_manager import DictManager
from src.core.scanner import NovelScanner, ScannedCandidate
from src.core.ai_assistant import AIAssistant
from src.core.scan_exporter import ScanExporter

def log(level: str, message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if HAS_COLOR:
        color_map = {
            "INFO": Fore.CYAN,
            "SCAN": Fore.MAGENTA,
            "AI": Fore.YELLOW,
            "SUCCESS": Fore.GREEN,
            "WARN": Fore.YELLOW + Style.BRIGHT,
            "ERROR": Fore.RED + Style.BRIGHT,
        }
        color = color_map.get(level, Fore.WHITE)
        print(f"[{Fore.WHITE}{timestamp}{Style.RESET_ALL}] [{color}{level:<7}{Style.RESET_ALL}] {message}")
    else:
        print(f"[{timestamp}] [{level:<7}] {message}")

def print_banner():
    banner = """
========================================================================
     NOVEL TRANSLATION REFINER - CLI REALTIME SCANNER
========================================================================
"""
    if HAS_COLOR:
        print(Fore.BLUE + Style.BRIGHT + banner)
    else:
        print(banner)

def run_scan_cli(
    file_path: Path,
    min_count: int = 2,
    sample_size: int = 0,
    novel_tag: str = "",
    use_ai: bool = False,
    provider: str = "gemini"
):
    print_banner()
    config = Config()
    dict_mgr = DictManager(config.COMMON_DICT_PATH, config.CHARACTER_DICT_PATH)

    if not file_path.exists():
        log("ERROR", f"Không tìm thấy file: {file_path}")
        return 1

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    log("INFO", f"Tệp mục tiêu: {file_path.name} ({file_size_mb:.2f} MB)")
    if not novel_tag:
        novel_tag = file_path.stem[:25]
    log("INFO", f"Tag truyện: '{novel_tag}' | Tần suất tối thiểu: {min_count}")

    # 1. Đọc nội dung
    log("INFO", "Đang nạp nội dung văn bản...")
    start_time = time.time()
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        if sample_size > 0:
            text = f.read(sample_size)
            log("INFO", f"Chế độ: Quét mẫu {sample_size:,} ký tự đầu tiên.")
        else:
            text = f.read()
            log("INFO", f"Chế độ: Quét toàn bộ file ({len(text):,} ký tự).")

    # 2. Nạp từ điển hiện có để loại trừ
    log("INFO", "Đang nạp từ điển hiện có để loại trừ từ đã duyệt...")
    common_terms = dict_mgr.load_common_dict()
    char_terms = dict_mgr.load_character_dict()
    existing_all = {t.source.lower() for t in common_terms}.union({c.source.lower() for c in char_terms})
    log("INFO", f"-> Đã nạp {len(common_terms)} từ phổ biến, {len(char_terms)} tên nhân vật làm bộ lọc loại trừ.")

    # 3. Khởi tạo Scanner và chạy Heuristic
    log("SCAN", "Bắt đầu thuật toán quét Heuristic (Tên riêng, lỗi dịch máy, cấu trúc Hán)...")
    scanner_start = time.time()
    scanner = NovelScanner(existing_words=existing_all)
    candidates = scanner.scan_text(text, min_count=min_count)
    scanner_elapsed = time.time() - scanner_start

    char_candidates = [c for c in candidates if c.candidate_type == "Tên nhân vật"]
    abnormal_candidates = [c for c in candidates if c.candidate_type != "Tên nhân vật"]
    log("SCAN", f"Quét hoàn tất trong {scanner_elapsed:.2f}s! Tìm thấy tổng cộng {len(candidates)} ứng viên mới:")
    log("SCAN", f"   ├── Tên riêng / Nhân vật: {len(char_candidates)} mục")
    log("SCAN", f"   └── Lỗi dịch máy / Cấu trúc Hán: {len(abnormal_candidates)} mục")

    if not candidates:
        log("WARN", "Không tìm thấy cụm từ mới nào thỏa mãn điều kiện quét.")
        return 0

    # 4. Chạy AI Assistant nếu được bật
    if use_ai:
        api_key = config.GEMINI_API_KEY if provider == "gemini" else config.OPENAI_API_KEY
        if not api_key:
            log("WARN", f"Không tìm thấy API Key cho provider '{provider}' trong file .env. Bỏ qua phân tích AI.")
        else:
            log("AI", f"Khởi động Trợ lý AI ({provider.upper()}) để phân loại & đề xuất từ chuẩn...")
            ai = AIAssistant(api_key=api_key, provider=provider)
            batch_size = 30
            total_batches = (len(candidates) + batch_size - 1) // batch_size
            
            for b_idx in range(total_batches):
                batch = candidates[b_idx * batch_size : (b_idx + 1) * batch_size]
                log("AI", f"Đang gửi lô {b_idx + 1}/{total_batches} ({len(batch)} từ) lên AI...")
                b_start = time.time()
                ai_results = ai.analyze_batch(batch)
                b_elapsed = time.time() - b_start
                for c, r in zip(batch, ai_results):
                    c.suggested_target = r.suggested_translation
                    c.candidate_type = r.category
                log("AI", f"   └── Lô {b_idx + 1}/{total_batches} hoàn tất trong {b_elapsed:.2f}s.")

    # 5. Xuất kết quả vào thư mục scanned/
    log("INFO", f"Đang xuất kết quả vào thư mục: {config.SCANNED_DIR}...")
    json_path, txt_path = ScanExporter.auto_export_scanned(candidates, novel_tag, config.SCANNED_DIR)
    log("SUCCESS", f"File JSON cấu trúc: {json_path}")
    log("SUCCESS", f"File Prompt biên tập: {txt_path}")

    # 6. In bảng tóm tắt Top kết quả ra màn hình CLI
    total_time = time.time() - start_time
    print("\n" + "="*80)
    print(f" TOP 15 TỪ ĐƯỢC PHÁT HIỆN TỪ FILE [{file_path.name}]")
    print("="*80)
    print(f"{'Loại':<15} | {'Từ gốc (Thô)':<25} | {'Đề xuất chuẩn':<25} | {'Tần suất'}")
    print("-" * 80)
    for c in candidates[:15]:
        target = c.suggested_target if c.suggested_target else c.phrase
        print(f"{c.candidate_type:<15} | {c.phrase:<25} | {target:<25} | {c.count:>5}")
    print("="*80)
    log("SUCCESS", f"Hoàn tất toàn bộ quy trình scan trong {total_time:.2f} giây!\n")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Novel Translation Refiner - CLI Realtime Scanner")
    parser.add_argument("--file", "-f", type=str, default="exam.txt", help="Đường dẫn đến file truyện cần scan (mặc định: exam.txt)")
    parser.add_argument("--min-count", "-m", type=int, default=2, help="Tần suất xuất hiện tối thiểu (mặc định: 2)")
    parser.add_argument("--sample-size", "-s", type=int, default=0, help="Số ký tự quét mẫu (0 = quét toàn bộ file, mặc định: 0)")
    parser.add_argument("--tag", "-t", type=str, default="", help="Tag tên truyện để gán cho nhân vật")
    parser.add_argument("--use-ai", "-a", action="store_true", help="Bật AI phân tích & đề xuất")
    parser.add_argument("--provider", "-p", type=str, default="gemini", choices=["gemini", "openai"], help="Nhà cung cấp AI (mặc định: gemini)")

    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = BASE_DIR / file_path

    exit_code = run_scan_cli(
        file_path=file_path,
        min_count=args.min_count,
        sample_size=args.sample_size,
        novel_tag=args.tag,
        use_ai=args.use_ai,
        provider=args.provider
    )
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
