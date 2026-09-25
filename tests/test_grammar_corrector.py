import pytest
from src.core.grammar_corrector import GrammarCorrector

def test_fix_reverse_possession_pronouns():
    text = "Nàng gắt gao nắm lấy của hắn bàn tay."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 1
    assert fixed == "Nàng gắt gao nắm lấy bàn tay của hắn."

def test_fix_reverse_possession_proper_name():
    text = "Trong của Lệ Na ánh mắt hiện lên vẻ hoảng hốt."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 1
    assert fixed == "Trong ánh mắt của Lệ Na hiện lên vẻ hoảng hốt."

def test_fix_reverse_possession_sentence_start():
    text = "Của hắn bàn tay rất ấm áp."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 1
    assert fixed == "Bàn tay của hắn rất ấm áp."

def test_fix_reverse_possession_non_noun_guard():
    text = "Cái này vốn là của hắn là đồ giả, của ta không có."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 0
    assert fixed == text

def test_fix_reverse_possession_single_word_noun_with_predicate():
    text = "Của hắn tóc rất dài."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 1
    assert fixed == "Tóc của hắn rất dài."

def test_fix_reverse_possession_multiple_occurrences():
    text = "Của hắn bàn tay nắm lấy của nàng góc áo."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 2
    assert fixed == "Bàn tay của hắn nắm lấy góc áo của nàng."

def test_fix_reverse_possession_empty_or_none():
    assert GrammarCorrector.fix_reverse_possession("") == ("", 0)
    assert GrammarCorrector.fix_reverse_possession(None) == (None, 0)
    assert GrammarCorrector.fix_reverse_possession("Không có từ đó ở đây.") == ("Không có từ đó ở đây.", 0)

def test_fix_reverse_possession_final_particles_guard():
    text = "Cái đó là của hắn đó sao? Của ta đây rồi."
    fixed, count = GrammarCorrector.fix_reverse_possession(text)
    assert count == 0
    assert fixed == text


