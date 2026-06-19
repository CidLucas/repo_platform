"""test_snapshot_templates_agenda.py — Unit tests for agenda snapshot validation."""

import pytest

from tool_pool_api.server.tool_modules.memory_module import (
    _validate_snapshot_body,
    _validate_snapshot_frontmatter,
    _SNAPSHOT_DIMENSION_FIELDS,
)

AGENDA_ENTITY = "agenda:mensal"

VALID_FRONTMATTER = {
    "tipo": "snapshot",
    "dimensao": "agenda",
    "periodo": "mensal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "gerado_por": "agenda_agent",
    "versao": 1,
    "template_version": 1,
    "ultimo_update": "2025-06-19T10:00:00Z",
    "fontes": ["get_today_meetings", "get_weekly_meetings v2"],
    "confianca": 0.90,
}

VALID_BODY = {
    "snapshot_id": "snap-a-001",
    "dimensao": "agenda",
    "periodo": "mensal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "vigencia_inicio": "2025-06-01T00:00:00Z",
    "vigencia_fim": "2025-06-30T00:00:00Z",
    "indicadores": [
        {"nome": "reunioes_hoje", "valor": 4, "unidade": "count"},
        {"nome": "reunioes_semana", "valor": 18, "unidade": "count"},
        {"nome": "followups_pendentes", "valor": 7, "unidade": "count"},
        {"nome": "contatos_a_cobrar", "valor": 3, "unidade": "count"},
    ],
    "alertas": [],
    "resumo_executivo": "Agenda do mês dentro do esperado.",
}


class TestAgendaFrontmatter:
    def test_valid_frontmatter_passes(self):
        _validate_snapshot_frontmatter(AGENDA_ENTITY, VALID_FRONTMATTER)

    def test_missing_fields_raises(self):
        bad = dict(VALID_FRONTMATTER)
        del bad["gerado_por"]
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_snapshot_frontmatter(AGENDA_ENTITY, bad)


class TestAgendaBody:
    def test_valid_body_passes(self):
        _validate_snapshot_body(AGENDA_ENTITY, VALID_BODY)

    def test_missing_required_indicator_raises(self):
        bad = dict(VALID_BODY)
        bad["indicadores"] = [
            i for i in VALID_BODY["indicadores"]
            if i["nome"] not in ("reunioes_hoje", "reunioes_semana")
        ]
        with pytest.raises(ValueError, match="Missing required indicators"):
            _validate_snapshot_body(AGENDA_ENTITY, bad)

    def test_dimensao_mismatch_raises(self):
        bad = dict(VALID_BODY)
        bad["dimensao"] = "compras"
        with pytest.raises(ValueError, match="body.dimensao"):
            _validate_snapshot_body(AGENDA_ENTITY, bad)


class TestAgendaDimensionSpec:
    def test_dimension_exists(self):
        assert "agenda" in _SNAPSHOT_DIMENSION_FIELDS

    def test_has_required_indicators(self):
        spec = _SNAPSHOT_DIMENSION_FIELDS["agenda"]
        required = [i["nome"] for i in spec["indicadores"] if i.get("required")]
        assert "reunioes_hoje" in required
        assert "reunioes_semana" in required
