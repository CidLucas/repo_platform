"""test_snapshot_templates_clientes.py — Unit tests for clientes snapshot validation."""

import pytest

from tool_pool_api.server.tool_modules.memory_module import (
    _validate_snapshot_body,
    _validate_snapshot_frontmatter,
    _SNAPSHOT_DIMENSION_FIELDS,
)

CLIENTES_ENTITY = "clientes:diario"

VALID_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "clientes",
    "periodo": "diario",
    "gerado_em": "2025-06-19T10:00:00Z",
    "gerado_por": "crm_agent",
    "versao": 1,
    "template_version": 1,
    "ultimo_update": "2025-06-19T10:00:00Z",
    "fontes": ["get_active_clients", "get_churn_metrics v1"],
    "confianca": 0.95,
}

VALID_BODY = {
    "snapshot_id": "snap-c-001",
    "dimensao": "clientes",
    "periodo": "diario",
    "gerado_em": "2025-06-19T10:00:00Z",
    "vigencia_inicio": "2025-06-19T00:00:00Z",
    "vigencia_fim": "2025-06-20T00:00:00Z",
    "indicadores": [
        {"nome": "total_clientes_ativos", "valor": 120, "unidade": "count", "tendencia": "estavel"},
        {"nome": "novos_clientes_periodo", "valor": 3, "unidade": "count", "tendencia": "alta"},
        {"nome": "churn_periodo", "valor": 1, "unidade": "count", "tendencia": "estavel"},
        {"nome": "nps_medio", "valor": 72, "unidade": "score", "tendencia": "alta"},
        {"nome": "ltv_medio", "valor": 8500, "unidade": "BRL", "tendencia": "estavel"},
        {"nome": "ticket_medio", "valor": 420, "unidade": "BRL", "tendencia": "alta"},
    ],
    "alertas": [],
    "resumo_executivo": "Base estável com leve crescimento.",
}


class TestClientesFrontmatter:
    def test_valid_frontmatter_passes(self):
        _validate_snapshot_frontmatter(CLIENTES_ENTITY, VALID_FRONTMATTER)

    def test_missing_fields_raises(self):
        bad = dict(VALID_FRONTMATTER)
        del bad["fontes"]
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_snapshot_frontmatter(CLIENTES_ENTITY, bad)

    def test_mismatched_dimensao_raises(self):
        bad = dict(VALID_FRONTMATTER)
        bad["dimensao"] = "financeiro"
        with pytest.raises(ValueError, match="entity_name dimension"):
            _validate_snapshot_frontmatter(CLIENTES_ENTITY, bad)


class TestClientesBody:
    def test_valid_body_passes(self):
        _validate_snapshot_body(CLIENTES_ENTITY, VALID_BODY)

    def test_missing_required_indicator_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = [
            i for i in VALID_BODY["indicadores"]
            if i["nome"] != "total_clientes_ativos"
        ]
        with pytest.raises(ValueError, match="Missing required indicators"):
            _validate_snapshot_body(CLIENTES_ENTITY, bad)

    def test_unknown_indicator_warns(self):
        """Unknown indicators are logged as warnings, not errors."""
        bad = dict(VALID_BODY)
        bad["indicadores"] = list(VALID_BODY["indicadores"]) + [
            {"nome": "indicador_desconhecido", "valor": 0, "unidade": "count"}
        ]
        _validate_snapshot_body(CLIENTES_ENTITY, bad)  # Should not raise


class TestClientesDimensionSpec:
    def test_dimension_exists(self):
        assert "clientes" in _SNAPSHOT_DIMENSION_FIELDS

    def test_has_required_indicators(self):
        spec = _SNAPSHOT_DIMENSION_FIELDS["clientes"]
        required = [i["nome"] for i in spec["indicadores"] if i.get("required")]
        assert "total_clientes_ativos" in required
        assert "novos_clientes_periodo" in required

    def test_has_agrupamentos(self):
        spec = _SNAPSHOT_DIMENSION_FIELDS["clientes"]
        assert "segmentacao" in spec["agrupamentos"]
        assert "status" in spec["agrupamentos"]
