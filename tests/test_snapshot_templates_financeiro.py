"""test_snapshot_templates_financeiro.py — Unit tests for financeiro snapshot validation.

Validates that the snapshot body and frontmatter validation rules work
correctly for the "financeiro" dimension.
"""

import pytest

# Import the validation functions and constants from memory_module
from tool_pool_api.server.tool_modules.memory_module import (
    _validate_snapshot_body,
    _validate_snapshot_frontmatter,
    _SNAPSHOT_DIMENSION_FIELDS,
)

# ── Helpers ──────────────────────────────────────────────────────────────

FINANCEIRO_ENTITY = "financeiro:semanal"

VALID_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "financeiro",
    "periodo": "semanal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "gerado_por": "financeiro_agent",
    "versao": 1,
    "template_version": 1,
    "ultimo_update": "2025-06-19T10:00:00Z",
    "fontes": ["get_cash_position v2", "get_recent_transactions v1"],
    "confianca": 0.95,
}

VALID_BODY = {
    "snapshot_id": "snap-001",
    "dimensao": "financeiro",
    "periodo": "semanal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "vigencia_inicio": "2025-06-12T00:00:00Z",
    "vigencia_fim": "2025-06-19T00:00:00Z",
    "indicadores": [
        {"nome": "saldo_atual", "valor": 150000, "unidade": "BRL", "tendencia": "estavel"},
        {"nome": "receita_periodo", "valor": 50000, "unidade": "BRL", "tendencia": "alta"},
        {"nome": "despesa_periodo", "valor": 35000, "unidade": "BRL", "tendencia": "baixa"},
        {"nome": "fluxo_liquido", "valor": 15000, "unidade": "BRL", "tendencia": "alta"},
        {"nome": "contas_a_pagar", "valor": 20000, "unidade": "BRL", "tendencia": "estavel"},
        {"nome": "contas_a_receber", "valor": 30000, "unidade": "BRL", "tendencia": "alta"},
        {"nome": "inadimplencia_percentual", "valor": 2.5, "unidade": "%", "tendencia": "baixa"},
    ],
    "alertas": [],
    "resumo_executivo": "Semana estável com receita acima da despesa.",
}


# ── Frontmatter ──────────────────────────────────────────────────────────


class TestFinanceiroFrontmatter:
    """Tests for _validate_snapshot_frontmatter — financeiro dimension."""

    def test_valid_frontmatter_passes(self):
        _validate_snapshot_frontmatter(FINANCEIRO_ENTITY, VALID_FRONTMATTER)

    def test_missing_fields_raises(self):
        bad = dict(VALID_FRONTMATTER)
        del bad["fontes"]
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_snapshot_frontmatter(FINANCEIRO_ENTITY, bad)

    def test_wrong_tipo_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["tipo"] = "fact"
        with pytest.raises(ValueError, match="frontmatter.tipo must be 'snapshot'"):
            _validate_snapshot_frontmatter(FINANCEIRO_ENTITY, bad)

    def test_invalid_dimensao_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["dimensao"] = "invalid"
        with pytest.raises(ValueError, match="frontmatter.dimensao"):
            _validate_snapshot_frontmatter(FINANCEIRO_ENTITY, bad)

    def test_mismatched_dimensao_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["dimensao"] = "clientes"
        with pytest.raises(ValueError, match="entity_name dimension"):
            _validate_snapshot_frontmatter(FINANCEIRO_ENTITY, bad)

    def test_mismatched_period_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["periodo"] = "mensal"
        with pytest.raises(ValueError, match="entity_name period"):
            _validate_snapshot_frontmatter("financeiro:semanal", bad)

    def test_none_frontmatter_raises(self):
        with pytest.raises(ValueError, match="frontmatter is required"):
            _validate_snapshot_frontmatter(FINANCEIRO_ENTITY, None)

    def test_version_not_int_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["versao"] = 0
        with pytest.raises(ValueError, match="frontmatter.versao"):
            _validate_snapshot_frontmatter(FINANCEIRO_ENTITY, bad)


# ── Body ─────────────────────────────────────────────────────────────────


class TestFinanceiroBody:
    """Tests for _validate_snapshot_body — financeiro dimension."""

    def test_valid_body_passes(self):
        _validate_snapshot_body(FINANCEIRO_ENTITY, VALID_BODY)

    def test_missing_base_fields_raises(self):
        bad = dict(VALID_BODY)
        del bad["vigencia_inicio"]
        with pytest.raises(ValueError, match="missing required base fields"):
            _validate_snapshot_body(FINANCEIRO_ENTITY, bad)

    def test_dimensao_mismatch_raises(self):
        bad = dict(VALID_BODY)
        bad["dimensao"] = "clientes"
        with pytest.raises(ValueError, match="body.dimensao"):
            _validate_snapshot_body(FINANCEIRO_ENTITY, bad)

    def test_invalid_dimension_raises(self):
        with pytest.raises(ValueError, match="Invalid snapshot dimension"):
            _validate_snapshot_body("invalid:diario", VALID_BODY)

    def test_missing_required_indicator_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = [
            i for i in VALID_BODY["indicadores"]
            if i["nome"] not in ("saldo_atual", "receita_periodo", "despesa_periodo", "fluxo_liquido")
        ]
        with pytest.raises(ValueError, match="Missing required indicators"):
            _validate_snapshot_body(FINANCEIRO_ENTITY, bad)

    def test_indicator_missing_valor_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = [{"nome": "saldo_atual", "unidade": "BRL"}]
        with pytest.raises(ValueError, match="missing required field 'valor'"):
            _validate_snapshot_body(FINANCEIRO_ENTITY, bad)

    def test_indicator_invalid_tendencia_warns(self):
        """Invalid tendencia raises ValueError."""
        bad = dict(VALID_BODY)
        bad["indicadores"] = [
            {"nome": "saldo_atual", "valor": 1000, "unidade": "BRL", "tendencia": "otima"},
            {"nome": "receita_periodo", "valor": 5000, "unidade": "BRL"},
            {"nome": "despesa_periodo", "valor": 3000, "unidade": "BRL"},
            {"nome": "fluxo_liquido", "valor": 2000, "unidade": "BRL"},
        ]
        with pytest.raises(ValueError, match="invalid tendencia"):
            _validate_snapshot_body(FINANCEIRO_ENTITY, bad)

    def test_alertas_not_list_raises(self):
        bad = dict(VALID_BODY)
        bad["alertas"] = "not a list"
        with pytest.raises(ValueError, match="body.alertas must be a list"):
            _validate_snapshot_body(FINANCEIRO_ENTITY, bad)


# ── Dimension spec ───────────────────────────────────────────────────────


class TestFinanceiroDimensionSpec:
    """Verify the financeiro dimension is correctly defined."""

    def test_dimension_exists(self):
        assert "financeiro" in _SNAPSHOT_DIMENSION_FIELDS

    def test_has_required_indicators(self):
        spec = _SNAPSHOT_DIMENSION_FIELDS["financeiro"]
        required = [i["nome"] for i in spec["indicadores"] if i.get("required")]
        assert "saldo_atual" in required
        assert "receita_periodo" in required
        assert "despesa_periodo" in required
        assert "fluxo_liquido" in required

    def test_has_queries(self):
        spec = _SNAPSHOT_DIMENSION_FIELDS["financeiro"]
        assert len(spec["queries_referencia"]) > 0
