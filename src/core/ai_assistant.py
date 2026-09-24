import json
import re
from typing import List, Optional
from pydantic import BaseModel
from src.core.scanner import ScannedCandidate

class AIAnalysisResult(BaseModel):
    phrase: str
    suggested_translation: str
    category: str
    is_character: bool
    confidence: float = 1.0

class AIAssistant:
    """
    Trợ lý AI (Gemini / OpenAI) hỗ trợ phân loại và đề xuất bản dịch chuẩn tiếng Việt
    cho danh sách các cụm từ nghi vấn/tên riêng trích xuất từ truyện convert.
    """
    def __init__(self, api_key: str = "", provider: str = "gemini"):
        self.api_key = api_key
        self.provider = provider

    def _call_llm(self, prompt: str) -> str:
        if not self.api_key:
            return ""

        if self.provider == "gemini":
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return response.text or ""
            except Exception:
                return ""
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                return response.choices[0].message.content or ""
            except Exception:
                return ""
        return ""

    def analyze_batch(self, candidates: List[ScannedCandidate]) -> List[AIAnalysisResult]:
        if not candidates:
            return []

        # Nếu không có API Key, fallback giữ nguyên từ và phân loại dựa theo Heuristic
        if not self.api_key:
            return [
                AIAnalysisResult(
                    phrase=c.phrase,
                    suggested_translation=c.phrase,
                    category="Tên nhân vật" if c.candidate_type == "Tên nhân vật" else "Từ dịch thô",
                    is_character=(c.candidate_type == "Tên nhân vật"),
                    confidence=0.5
                )
                for c in candidates
            ]

        # Chuẩn bị dữ liệu gửi cho AI
        items = [{"phrase": c.phrase, "contexts": c.sample_contexts} for c in candidates]
        prompt = f"""
Bạn là chuyên gia biên tập và dịch truyện tiếng Trung sang tiếng Việt.
Dưới đây là danh sách các cụm từ nghi vấn được trích xuất từ bản dịch thô (convert).
Nhiệm vụ của bạn:
1. Phân loại từ đó là "Tên nhân vật" (is_character: true) hay cụm từ/lỗi dịch thô thông thường (is_character: false).
2. Đề xuất bản dịch / tên tiếng Việt chuẩn hóa, mượt mà và tự nhiên nhất (suggested_translation).
   Ví dụ:
   - "Gavin phong" -> "Giả Văn Phong" (do phiên âm nhầm Jia Wen Feng)
   - "đương gia hoa đán" -> "ngôi sao trụ cột"
   - "đợi ảnh thị kịch" -> "các phim truyền hình"
   - "lấy gã bác sĩ" -> "gả cho bác sĩ"

Danh sách cụm từ:
{json.dumps(items, ensure_ascii=False, indent=2)}

Trả về DUY NHẤT một mảng JSON (không có markdown giải thích thêm) theo định dạng:
[
  {{
    "phrase": "từ gốc",
    "suggested_translation": "từ chuẩn đề xuất",
    "category": "Tên nhân vật" hoặc "Lỗi dịch máy" hoặc "Xưng hô",
    "is_character": true hoặc false,
    "confidence": 0.95
  }}
]
"""
        response_text = self._call_llm(prompt)

        # Parse JSON output
        try:
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return [AIAnalysisResult(**item) for item in data]
        except Exception:
            pass

        # Fallback nếu parse thất bại
        return [
            AIAnalysisResult(
                phrase=c.phrase,
                suggested_translation=c.phrase,
                category=c.candidate_type,
                is_character=(c.candidate_type == "Tên nhân vật"),
                confidence=0.5
            )
            for c in candidates
        ]
