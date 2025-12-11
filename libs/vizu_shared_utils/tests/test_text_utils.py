# tests/unit/test_text_utils.py (Testa a função base)

from vizu_shared_utils.text_utils import normalize_text


def test_normalize_text_full_cases():
    assert normalize_text("Produto Ação") == "produto acao"
    assert normalize_text("  PRODUTO B  ") == "produto b"
    assert normalize_text("Maçã") == "maca"
    assert normalize_text(123) == "123" # Testa resiliência a não-strings


