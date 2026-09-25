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
) -> int:
    config = Config()
    dict_mgr = DictManager(config.COMMON_DICT_PATH, config.CHARACTER_DICT_PATH)

    if not file_path.exists():
        log("ERROR", f"Không tìm thấy file: {file_path}")
        return 1

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    log("INFO", f"Tệp mục tiêu: {file_path.name} ({file_size_mb:.2f} MB)")
    log("INFO", f"Đường dẫn: {file_path}")
    if not novel_tag:
        novel_tag = file_path.stem[:25]
    log("INFO", f"Tag truyện: '{novel_tag}' | Tần suất tối thiểu: {min_count}")
    start_time = time.time()

    # 1. Nạp từ điển hiện có để loại trừ
    log("INFO", "Đang nạp từ điển hiện có để loại trừ từ đã duyệt...")
    common_terms = dict_mgr.load_common_dict()
    char_terms = dict_mgr.load_character_dict()
    existing_all = {t.source.lower() for t in common_terms}.union({c.source.lower() for c in char_terms})
    log("INFO", f"-> Đã nạp {len(common_terms)} từ phổ biến, {len(char_terms)} tên nhân vật làm bộ lọc loại trừ.")

    # 2. Khởi tạo Scanner và chạy Heuristic
    log("SCAN", "Bắt đầu thuật toán quét Heuristic (Tên riêng, lỗi dịch máy, cấu trúc Hán)...")
    scanner_start = time.time()
    scanner = NovelScanner(existing_words=existing_all)
    filter_counts = {
        "từ cấm": len(scanner.blacklist),
        "đại từ": len(scanner.pronouns_and_starts),
        "từ đuôi": len(scanner.trailing_stopwords),
        "phi nhân vật": len(scanner.non_person_words),
    }
    log("INFO", f"Đã nạp bộ lọc tùy biến từ filters/: {', '.join(f'{v} {k}' for k, v in filter_counts.items())}")

    if sample_size > 0:
        log("INFO", f"Chế độ: Quét mẫu {sample_size:,} ký tự đầu tiên.")
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(sample_size)
        candidates = scanner.scan_text(text, min_count=min_count)
    else:
        log("INFO", "Chế độ: Quét toàn bộ file bằng Streaming Buffer (tránh tràn RAM, tự động lưu liên tục vào scanned/)...")
        last_progress_time = 0

        def on_chunk_progress(bytes_read, total_bytes, count):
            nonlocal last_progress_time
            now = time.time()
            if now - last_progress_time >= 1.0 or bytes_read >= total_bytes:
                pct = (bytes_read / total_bytes * 100) if total_bytes > 0 else 100
                mb_read = bytes_read / (1024 * 1024)
                mb_total = total_bytes / (1024 * 1024)
                log("SCAN", f"Đang quét: {pct:5.1f}% ({mb_read:.2f}/{mb_total:.2f} MB) ── Đã tìm thấy {count} ứng viên...")
                last_progress_time = now

        def on_checkpoint(cands, jpath, tpath):
            log("INFO", f"💾 Đã lưu liên tục checkpoint {len(cands)} từ vào thư mục scanned/: {jpath.name}")

        candidates = scanner.scan_file_streaming(
            file_path=file_path,
            min_count=min_count,
            chunk_size_bytes=128 * 1024,
            on_chunk_progress=on_chunk_progress,
            scanned_dir=config.SCANNED_DIR,
            novel_name=novel_tag,
            save_interval_chunks=5,
            on_save_checkpoint=on_checkpoint,
            export_partition=True,
            partition_size=50
        )

    scanner_elapsed = time.time() - scanner_start

    char_candidates = [c for c in candidates if c.candidate_type == "Tên nhân vật"]
    abnormal_candidates = [c for c in candidates if c.candidate_type != "Tên nhân vật"]
    log("SCAN", f"Quét hoàn tất trong {scanner_elapsed:.2f}s! Tìm thấy tổng cộng {len(candidates)} ứng viên mới:")
    log("SCAN", f"   ├── Tên riêng / Nhân vật: {len(char_candidates)} mục")
    log("SCAN", f"   └── Lỗi dịch máy / Cấu trúc Hán: {len(abnormal_candidates)} mục")

    if not candidates:
        log("WARN", "Không tìm thấy cụm từ mới nào thỏa mãn điều kiện quét.")
        return 0

    # 3. Chạy AI Assistant nếu được bật
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

    # 4. Xuất kết quả hoàn chỉnh vào thư mục scanned/
    log("INFO", f"Đang lưu trữ kết quả hoàn chỉnh vào thư mục: {config.SCANNED_DIR}...")
    part_files, master_json = ScanExporter.export_partitioned(candidates, novel_tag, config.SCANNED_DIR, part_size=50)
    log("SUCCESS", f"File JSON cấu trúc: {master_json}")
    log("SUCCESS", f"Đã chia thành {len(part_files)} file review trong scanned/ (50 từ/file)")


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

def interactive_wizard():
    print_banner()
    config = Config()

    # 1. Nhập đường dẫn file
    print("📂 BƯỚC 1: CHỌN FILE TRUYỆN")
    print("   Bạn có thể copy đường dẫn file, dán vào đây hoặc kéo thả file vào cửa sổ terminal.")
    while True:
        raw_input = input("👉 Nhập đường dẫn file [Mặc định: exam.txt]: ").strip()
        # Loại bỏ dấu ngoặc kép hoặc nháy đơn do copy-paste từ Windows
        cleaned_path = raw_input.strip("\"'")
        if not cleaned_path:
            cleaned_path = "exam.txt"

        target_file = Path(cleaned_path)
        if not target_file.is_absolute():
            target_file = BASE_DIR / target_file

        if target_file.exists() and target_file.is_file():
            break
        print(f"{Fore.RED if HAS_COLOR else ''}❌ Không tìm thấy file tại '{target_file}'. Vui lòng nhập lại!{Style.RESET_ALL if HAS_COLOR else ''}")

    print(f"{Fore.GREEN if HAS_COLOR else ''}✔ Đã chọn file: {target_file.name}{Style.RESET_ALL if HAS_COLOR else ''}\n")

    # 2. Chọn chế độ quét
    print("⚙️ BƯỚC 2: CHỌN CHẾ ĐỘ QUÉT")
    print("   [1] Quét toàn bộ file (Heuristic - Tốc độ cao, không tốn token)")
    print("   [2] Quét mẫu 50.000 ký tự đầu (Thử nghiệm nhanh)")
    print("   [3] Quét sâu 500.000 ký tự đầu")
    print("   [4] Quét kết hợp AI (Gemini/OpenAI phân tích ngữ cảnh & gợi ý)")
    mode_choice = input("👉 Chọn chế độ [1/2/3/4] [Mặc định: 1]: ").strip()
    if mode_choice not in ("1", "2", "3", "4"):
        mode_choice = "1"

    sample_size = 0
    use_ai = False
    provider = "gemini"

    if mode_choice == "2":
        sample_size = 50000
    elif mode_choice == "3":
        sample_size = 500000
    elif mode_choice == "4":
        use_ai = True
        ai_choice = input("👉 Chọn AI Provider [1: Gemini (Mặc định), 2: OpenAI]: ").strip()
        provider = "openai" if ai_choice == "2" else "gemini"

    # 3. Tần suất tối thiểu
    print("\n🔢 BƯỚC 3: TẦN SUẤT XUẤT HIỆN TỐI THIỂU")
    freq_input = input("👉 Nhập tần suất tối thiểu (>= 1) [Mặc định: 2]: ").strip()
    min_count = int(freq_input) if freq_input.isdigit() and int(freq_input) > 0 else 2

    # 4. Tag truyện
    default_tag = target_file.stem[:25]
    print(f"\n🏷️ BƯỚC 4: TAG BỘ TRUYỆN")
    tag_input = input(f"👉 Tag truyện cho nhân vật [Mặc định: '{default_tag}']: ").strip()
    novel_tag = tag_input if tag_input else default_tag

    print("\n" + "="*80)
    print("BẮT ĐẦU XỬ LÝ SCAN...")
    print("="*80)

    exit_code = run_scan_cli(
        file_path=target_file,
        min_count=min_count,
        sample_size=sample_size,
        novel_tag=novel_tag,
        use_ai=use_ai,
        provider=provider
    )

    if exit_code == 0:
        open_folder = input("📂 Bạn có muốn mở thư mục 'scanned/' để xem file kết quả ngay không? (y/n) [Mặc định: y]: ").strip().lower()
        if open_folder in ("", "y", "yes"):
            try:
                if sys.platform == "win32":
                    os.startfile(str(config.SCANNED_DIR))
                else:
                    import subprocess
                    subprocess.run(["xdg-open", str(config.SCANNED_DIR)])
            except Exception as e:
                print(f"Không thể mở thư mục tự động: {e}")

    input("\nNhấn Enter để kết thúc...")

def main():
    if len(sys.argv) == 1:
        # Nếu chạy không có tham số: Vào chế độ tương tác Wizard
        interactive_wizard()
        return

    # Nếu có tham số truyền vào: Chạy theo CLI arguments
    parser = argparse.ArgumentParser(description="Novel Translation Refiner - CLI Realtime Scanner")
    parser.add_argument("--file", "-f", type=str, default="exam.txt", help="Đường dẫn đến file truyện cần scan (mặc định: exam.txt)")
    parser.add_argument("--min-count", "-m", type=int, default=2, help="Tần suất xuất hiện tối thiểu (mặc định: 2)")
    parser.add_argument("--sample-size", "-s", type=int, default=0, help="Số ký tự quét mẫu (0 = quét toàn bộ file, mặc định: 0)")
    parser.add_argument("--tag", "-t", type=str, default="", help="Tag tên truyện để gán cho nhân vật")
    parser.add_argument("--use-ai", "-a", action="store_true", help="Bật AI phân tích & đề xuất")
    parser.add_argument("--provider", "-p", type=str, default="gemini", choices=["gemini", "openai"], help="Nhà cung cấp AI (mặc định: gemini)")

    args = parser.parse_args()
    print_banner()
    
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
