import pytest
from unittest.mock import MagicMock, patch
from src.core.scanner import ScannedCandidate
from src.core.ai_assistant import AIAssistant, AIAnalysisResult

def test_ai_assistant_fallback_when_no_api_key():
    assistant = AIAssistant(api_key="", provider="gemini")
    candidates = [
        ScannedCandidate(phrase="Trương Tử Kiến", count=5, candidate_type="Tên nhân vật", sample_contexts=[]),
        ScannedCandidate(phrase="đương gia hoa đán", count=3, candidate_type="Từ bất thường", sample_contexts=[])
    ]
    results = assistant.analyze_batch(candidates)
    assert len(results) == 2
    assert results[0].phrase == "Trương Tử Kiến"
    assert results[0].suggested_translation == "Trương Tử Kiến"
    assert results[1].phrase == "đương gia hoa đán"

@patch.object(AIAssistant, "_call_llm")
def test_ai_assistant_successful_parse(mock_call_llm):
    mock_call_llm.return_value = """
    [
        {"phrase": "Gavin phong", "suggested_translation": "Giả Văn Phong", "category": "Tên nhân vật", "is_character": true, "confidence": 0.95},
        {"phrase": "đợi ảnh thị kịch", "suggested_translation": "các phim truyền hình", "category": "Lỗi dịch máy", "is_character": false, "confidence": 0.9}
    ]
    """
    assistant = AIAssistant(api_key="mock_key", provider="gemini")
    candidates = [
        ScannedCandidate(phrase="Gavin phong", count=5, candidate_type="Tên nhân vật", sample_contexts=[]),
        ScannedCandidate(phrase="đợi ảnh thị kịch", count=3, candidate_type="Từ bất thường", sample_contexts=[])
    ]
    results = assistant.analyze_batch(candidates)
    assert len(results) == 2
    assert results[0].suggested_translation == "Giả Văn Phong"
    assert results[0].is_character is True
    assert results[1].suggested_translation == "các phim truyền hình"
