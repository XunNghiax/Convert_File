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
Bạn là một biên tập viên dịch thuật chuyên nghiệp.
Nhiệm vụ của bạn là đọc danh sách bên dưới, dựa theo trường Context và source để sinh ra target
1. Nếu là Tên nhân vật: Chuẩn hóa Title Case tiếng Việt hoặc Hán Việt mượt mà.
2. Nếu là Lỗi dịch máy / Cụm từ thô: Thay thế bằng từ tiếng Việt tự nhiên, phù hợp với ngữ cảnh trong "context".
3. Giữ nguyên cấu trúc JSON và trả về danh sách đã chỉnh sửa trong code block.

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
