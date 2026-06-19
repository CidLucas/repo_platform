"""test_snapshot_templates_compras.py — Unit tests for compras/inventory snapshot validation."""

import pytest

from tool_pool_api.server.tool_modules.memory_module import (
    _validate_snapshot_body,
    _validate_snapshot_frontmatter,
    _SNAPSHOT_DIMENSION_FIELDS,
)

COMPRAS_ENTITY = "compras:semanal"

VALID_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "compras",
    "periodo": "semanal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "gerado_por": "compras_agent",
    "versao": 1,
    "template_version": 1,
    "ultimo_update": "2025-06-19T10:00:00Z",
    "fontes": ["get_open_purchase_orders v1", "get_critical_stock v1"],
    "confianca": 0.92,
}

VALID_BODY = {
    "snapshot_id": "snap-p-001",
    "dimensao": "compras",
    "periodo": "semanal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "vigencia_inicio": "2025-06-12T00:00:00Z",
    "vigencia_fim": "2025-06-19T00:00:00Z",
    "indicadores": [
        {"nome": "total_pos_abertas", "valor": 15, "unidade": "count", "tendencia": "alta"},
        {"nome": "estoque_critico", "valor": 3, "unidade": "count", "tendencia": "estavel"},
        {"nome": "fornecedores_com_pendencia", "valor": 5, "unidade": "count", "tendencia": "baixa"},
        {"nome": "pedidos_em_analise", "valor": 2, "unidade": "count", "tendencia": "estavel"},
    ],
    "alertas": [],
    "resumo_executivo": "Estoque controlado, 3 itens críticos.",
}


class TestComprasFrontmatter:
    def test_valid_frontmatter_passes(self):
        _validate_snapshot_frontmatter(COMPRAS_ENTITY, VALID_FRONTMATTER)

    def test_invalid_period_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["periodo"] = "anual"
        with pytest.raises(ValueError, match="frontmatter.periodo"):
            _validate_snapshot_frontmatter(COMPRAS_ENTITY, bad)

    def test_invalid_versao_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["versao"] = -1
        with pytest.raises(ValueError, match="frontmatter.versao"):
            _validate_snapshot_frontmatter(COMPRAS_ENTITY, bad)


class TestComprasBody:
    def test_valid_body_passes(self):
        _validate_snapshot_body(COMPRAS_ENTITY, VALID_BODY)

    def test_missing_required_indicator_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = [
            {"nome": "estoque_critico", "valor": 3, "unidade": "count"}
        ]
        with pytest.raises(ValueError, match="Missing required indicators"):
            _validate_snapshot_body(COMPRAS_ENTITY, bad)

    def test_missing_base_fields_raises(self):
        bad = dict(VALID_BODY)
        del bad["snapshot_id"]
        with pytest.raises(ValueError, match="missing required base fields"):
            _validate_snapshot_body(COMPRAS_ENTITY, bad)

    def test_indicadores_not_list_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = {}
        with pytest.raises(ValueError, match="body.indicadores must be a list"):
            _validate_snapshot_body(COMPRAS_ENTITY, bad)

    def test_indicator_not_dict_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = ["not a dict"]
        with pytest.raises(ValueError, match="must be a dict"):
            _validate_snapshot_body(COMPRAS_ENTITY, bad)

    def test_indicator_no_nome_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = [{"valor": 10, "unidade": "count"}]
        with pytest.raises(ValueError, match="must have a 'nome'"):
            _validate_snapshot_body(COMPRAS_ENTITY, bad)

    def test_resumo_executivo_not_string_raises(self):
        bad = dict(VALID_BODY)
        bad["resumo_executivo"] = 123
        with pytest.raises(ValueError, match="body.resumo_executivo must be a string"):
            _validate_snapshot_body(COMPRAS_ENTITY, bad)

    def test_dimension_not_from_entity_name(self):
        """Entity name without colon raises."""
        with pytest.raises(ValueError, match="Cannot determine snapshot dimension"):
            _validate_snapshot_body("invalid_entity", VALID_BODY)


class TestComprasDimensionSpec:
    def test_dimension_exists(self):
        assert "compras" in _SNAPSHOT_DIMENSION_FIELDS

    def test_has_required_indicators(self):
        spec = _SNAPSHOT_DIMENSION_FIELDS["compras"]
        required = [i["nome"] for i in spec["indicadores"] if i.get("required")]
        assert "total_pos_abertas" in required

    def test_label_is_correct(self):
        spec = _SNAPSHOT_DIMENSION_FIELDS["compras"]
        assert "Compras" in spec["label"] or "Inventory" in spec["label"]
