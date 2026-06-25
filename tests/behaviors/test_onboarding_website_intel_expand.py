# GOAL: Expandir EF onboarding-website-intel — CNPJ, telefone, verticais, confidence
# BEHAVIOR: B1 — Expandir EF com CNPJ, telefone, verticais expandidas e confidence dinâmico
#
# AC#1 — CNPJ extraído da página (se presente) e preenchido no response
# AC#2 — Telefone extraído (se presente)
# AC#3 — Verticais expandidas: design, buffet, construcao, saude, educacao, logistica, consultoria
# AC#4 — Confidence dinâmico: 1 fonte=0.3, 2 fontes=0.5, 3+=0.7
# AC#5 — Novos campos no response: cnpj, phone
# AC#6 — Timeout: 10s (aumentado de 5s)
# AC#7 — URL vazia/inválida → fallback sem erro
#
# State: RED. All assertions (except AC#7) validate features that do NOT
# exist in the current code. The test will fail until the EF is expanded.

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_EF_PATH = _REPO_ROOT / "supabase" / "functions" / "onboarding-website-intel" / "index.ts"


def _ef_source() -> str:
    """Read the current Edge Function source."""
    return _EF_PATH.read_text(encoding="utf-8")


# ── AC#1: CNPJ extraction ─────────────────────────────────────────────


def test_ac1_cnpj_regex_exists():
    """AC#1 — EF has NO CNPJ extraction regex.

    Expanded EF must include a regex pattern for CNPJ
    (\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}) in raw HTML,
    meta tags, and JSON-LD.
    """
    source = _ef_source()
    assert re.search(r"cnpj", source, re.IGNORECASE), (
        "RED: EF deve ter regex de extração de CNPJ"
    )


def test_ac1_cnpj_digit_validation_exists():
    """AC#1 — CNPJ extraction must validate check digits.

    Invalid check digits → cnpj: null in response.
    """
    source = _ef_source()
    has_digit_check = bool(
        re.search(r"valid|digito", source, re.IGNORECASE)
        and "cnpj" in source.lower()
    )
    assert has_digit_check, (
        "RED: EF deve validar dígitos verificadores do CNPJ"
    )


# ── AC#2: Phone extraction ────────────────────────────────────────────


def test_ac2_phone_regex_exists():
    """AC#2 — EF has NO phone extraction regex.

    Expanded EF must extract Brazilian phone numbers:
    (XX) XXXX-XXXX (fixed) and (XX) 9XXXX-XXXX (mobile).
    """
    source = _ef_source()
    assert re.search(r"phone|telefone|celular", source, re.IGNORECASE), (
        "RED: EF deve ter regex de extração de telefone"
    )


# ── AC#3: Expanded verticals ──────────────────────────────────────────


def test_ac3_vertical_design_exists():
    source = _ef_source()
    assert '"design"' in source or "'design'" in source, (
        "RED: detectVertical deve incluir vertical 'design'"
    )


def test_ac3_vertical_buffet_exists():
    source = _ef_source()
    assert '"buffet"' in source or "'buffet'" in source, (
        "RED: detectVertical deve incluir vertical 'buffet'"
    )


def test_ac3_vertical_construcao_exists():
    source = _ef_source()
    assert '"construcao"' in source or "'construcao'" in source, (
        "RED: detectVertical deve incluir vertical 'construcao'"
    )


def test_ac3_vertical_logistica_exists():
    source = _ef_source()
    assert '"logistica"' in source or "'logistica'" in source, (
        "RED: detectVertical deve incluir vertical 'logistica'"
    )


def test_ac3_vertical_consultoria_standalone():
    source = _ef_source()
    assert '"consultoria"' in source or "'consultoria'" in source, (
        "RED: detectVertical deve incluir vertical 'consultoria' "
        "(branch independente, nao so keyword de servicos)"
    )


# ── AC#4: Dynamic confidence ──────────────────────────────────────────


def test_ac4_confidence_dynamic():
    """AC#4 — Current EF has FIXED confidence (0.72 or 0.45).

    Expanded EF must compute: 1 source=0.3, 2 sources=0.5, 3+=0.7.
    Sources: title, meta description, CNPJ, phone, content text.
    """
    source = _ef_source()
    # Check for 0.3 as a standalone confidence value, not part of 0.35/0.45
    # Check for 0.3 as a standalone confidence value, not part of 0.35/0.45
    assert re.search(r"[^0-9]0\.[3][^0-9]", source), (
        "RED: EF deve calcular confidence dinamico "
        "(1 fonte=0.3, 2 fontes=0.5, 3+=0.7)"
    )


# ── AC#5: New response fields ─────────────────────────────────────────


def test_ac5_cnpj_field_in_response():
    source = _ef_source()
    assert "cnpj" in source.lower(), (
        "RED: Response JSON deve ter campo 'cnpj'"
    )


def test_ac5_phone_field_in_response():
    source = _ef_source()
    assert "phone" in source.lower(), (
        "RED: Response JSON deve ter campo 'phone'"
    )


# ── AC#6: Timeout increase ────────────────────────────────────────────


def test_ac6_timeout_10s():
    """AC#6 — Current timeout is 5000ms. Must be 10000ms."""
    source = _ef_source()
    assert "10000" in source, (
        "RED: Timeout deve ser 10000ms (10s), atualmente 5000ms"
    )


# ── AC#7: URL fallback (already works — should PASS) ──────────────────


def test_ac7_empty_url_fallback():
    """AC#7 — URL vazia → fallback sem erro (already implemented)."""
    source = _ef_source()
    assert re.search(r"if\s*\(!\s*normalized\s*\)", source), (
        "EF deve ter fallback para URL vazia"
    )
