import json
import re
from pathlib import Path
from typing import List, Tuple
from src.core.scanner import ScannedCandidate

class ScanExporter:
    """
    Module phụ trách lưu trữ và xuất kết quả quét từ NovelScanner
    thành các định dạng file riêng biệt (JSON và TXT Prompt) trong thư mục scanned/.
    """

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        # Làm sạch tên file, loại bỏ ký tự không hợp lệ
        clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
        return clean or "scanned_novel"

    @classmethod
    def export_to_json(cls, candidates: List[ScannedCandidate], output_path: Path) -> Path:
        """
        Xuất danh sách candidates ra file JSON có cấu trúc đầy đủ.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for idx, c in enumerate(candidates, start=1):
            is_char = (c.candidate_type == "Tên nhân vật")
            target = c.suggested_target if c.suggested_target else c.phrase
            data.append({
                "id": f"scan-{idx}",
                "source": c.phrase,
                "suggested_target": target,
                "category": c.candidate_type,
                "is_character": is_char,
                "count": c.count,
                "context": c.sample_contexts[0] if c.sample_contexts else ""
            })
        
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    @classmethod
    def export_to_prompt_txt(cls, candidates: List[ScannedCandidate], novel_name: str, output_path: Path) -> Path:
        """
        Xuất file text định dạng chuẩn hóa theo mẫu docs/prompt.md
        giúp người dùng có thể gửi ngay cho AI hoặc tự sửa ngoại tuyến.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        items = []
        for idx, c in enumerate(candidates, start=1):
            target = c.suggested_target if c.suggested_target else c.phrase
            items.append({
                "id": f"scan-{idx}",
                "source": c.phrase,
                "target": target,
                "type": c.candidate_type,
                "context": c.sample_contexts[0] if c.sample_contexts else ""
            })

        header = f"""=== DANH SÁCH TỪ SCAN ĐƯỢC CẦN BIÊN TẬP ===
Truyện: {novel_name}
Tổng số mục: {len(candidates)} mục

--- HƯỚNG DẪN PROMPT GỬI CHO AI ---
Bạn là một biên tập viên dịch thuật chuyên nghiệp am hiểu nhiều ngôn ngữ và bối cảnh văn học mạng.
Nhiệm vụ của bạn là đọc danh sách định dạng JSON bên dưới, phân tích trường "source" và "context" (nếu có) để tạo ra kết quả dịch thuật tối ưu nhất điền vào trường "target".

Hãy tuân thủ các quy tắc sau:
1. Đối với tên nhân vật Trung Quốc/Việt Nam: Chuẩn hóa viết hoa chữ cái đầu (Title Case) và sử dụng âm Hán Việt mượt mà, đúng chuẩn.
2. Đối với tên nước ngoài (Nhật Bản, phương Tây, Hàn Quốc...): Nhận diện các tên bị phiên âm sang tiếng Trung rồi dịch máy thô ra Hán Việt. Hãy khôi phục tên về ngôn ngữ gốc hoặc định dạng phổ biến nhất với độc giả Việt Nam. 
   - Ví dụ tên Nhật Bản: Đổi về Romaji (VD: "Ma Sinh Thái Lang" -> "Aso Taro", "Giai Tử" -> "Kako", "Cung Trạch" -> "Miyazawa").
   - Ví dụ tên phương Tây: Khôi phục về chữ Latinh (VD: "Khắc Lạp Khắc" -> "Clark", "Á Lịch Sơn Đại" -> "Alexander").
3. Đối với lỗi dịch máy / cụm từ thô: Thay thế bằng từ vựng và văn phong tiếng Việt tự nhiên, đảm bảo phù hợp với ngữ cảnh trong "context" (ví dụ: bối cảnh đô thị, tiên hiệp, khoa học viễn tưởng...).
4. Định dạng đầu ra: Giữ nguyên cấu trúc JSON của đầu vào và trả về toàn bộ danh sách đã chỉnh sửa bên trong một Markdown code block.

--- DỮ LIỆU CẦN XỬ LÝ ---
"""
        json_body = json.dumps(items, ensure_ascii=False, indent=2)
        full_content = header + json_body + "\n"
        output_path.write_text(full_content, encoding="utf-8")
        return output_path

    @classmethod
    def auto_export_scanned(cls, candidates: List[ScannedCandidate], novel_name: str, scanned_dir: Path) -> Tuple[Path, Path]:
        """
        Tự động xuất đồng thời file JSON và file TXT vào thư mục scanned/.
        Trả về Tuple (json_path, txt_path).
        """
        scanned_dir.mkdir(parents=True, exist_ok=True)
        safe_name = cls._sanitize_filename(novel_name)
        json_path = scanned_dir / f"{safe_name}_candidates.json"
        txt_path = scanned_dir / f"{safe_name}_review.txt"

        cls.export_to_json(candidates, json_path)
        cls.export_to_prompt_txt(candidates, safe_name, txt_path)
        return json_path, txt_path

    @classmethod
    def export_partitioned(
        cls,
        candidates: List[ScannedCandidate],
        novel_name: str,
        scanned_dir: Path,
        part_size: int = 500
    ) -> Tuple[List[Path], Path]:
        """
        Chia nhỏ danh sách kết quả thành nhiều file review (mỗi file part_size mục, mặc định 500)
        giúp gửi cho AI hoặc biên tập từng đợt mà không bị tràn token context window.
        Đồng thời xuất master candidates.json đầy đủ.
        """
        scanned_dir.mkdir(parents=True, exist_ok=True)
        safe_name = cls._sanitize_filename(novel_name)
        master_json = scanned_dir / f"{safe_name}_candidates.json"
        cls.export_to_json(candidates, master_json)

        part_files = []
        if not candidates:
            single_txt = scanned_dir / f"{safe_name}_review.txt"
            cls.export_to_prompt_txt([], safe_name, single_txt)
            return [single_txt], master_json

        num_parts = (len(candidates) + part_size - 1) // part_size
        for part_idx in range(num_parts):
            batch = candidates[part_idx * part_size : (part_idx + 1) * part_size]
            part_filename = f"{safe_name}_part{part_idx + 1}_review.txt"
            part_path = scanned_dir / part_filename
            cls.export_to_prompt_txt(batch, f"{novel_name} (Phần {part_idx + 1}/{num_parts})", part_path)
            part_files.append(part_path)

        # Xuất thêm bản full review.txt
        full_review = scanned_dir / f"{safe_name}_review.txt"
        cls.export_to_prompt_txt(candidates, safe_name, full_review)

        return part_files, master_json
