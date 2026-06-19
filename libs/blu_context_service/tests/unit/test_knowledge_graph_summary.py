"""Tests for ContextService.get_knowledge_graph_summary().

Also validates that get_domain_projection was NOT altered
(rag/documents domains should NOT include available_tools).
"""

import asyncio
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from blu_context_service.context_service import ContextService
from blu_models.blu_client_context import BluClientContext
from blu_models.context_schemas import KnowledgeGraphSummary


# =============================================================================
# Helpers
# =============================================================================


def _make_service(mocker) -> tuple[ContextService, MagicMock]:
    """Return ContextService with mocked dependencies."""
    mock_redis = mocker.MagicMock()
    mocker.patch("blu_context_service.context_service.SupabaseCRUD")
    mocker.patch("blu_context_service.context_service.get_supabase_client")
    mocker.patch("blu_context_service.context_service.supabase_set_rls")
    return ContextService(cache_service=mock_redis), mock_redis


def _make_context_with_kg_summary(client_id: UUID) -> BluClientContext:
    """BluClientContext with knowledge_graph_summary populated in available_tools."""
    return BluClientContext(
        id=client_id,
        nome_empresa="Test Corp",
        tier="BASIC",
        available_tools={
            "enabled_tool_names": ["executar_rag_cliente"],
            "knowledge_graph_summary": {
                "total_documents": 150,
                "total_entities": 80,
                "top_entities": [
                    {"name": "Acme", "type": "organization", "degree": 42},
                ],
                "last_sync": "2025-06-19T12:00:00Z",
                "version": 1,
            },
        },
        credenciais=[],
    )


def _make_context_available_tools_without_kg(client_id: UUID) -> BluClientContext:
    """BluClientContext with available_tools but WITHOUT knowledge_graph_summary."""
    return BluClientContext(
        id=client_id,
        nome_empresa="Test Corp",
        tier="BASIC",
        available_tools={
            "enabled_tool_names": ["executar_sql_agent"],
        },
        credenciais=[],
    )


def _make_context_without_available_tools(client_id: UUID) -> BluClientContext:
    """BluClientContext with available_tools=None."""
    return BluClientContext(
        id=client_id,
        nome_empresa="Test Corp",
        tier="BASIC",
        available_tools=None,
        credenciais=[],
    )


# =============================================================================
# get_knowledge_graph_summary tests
# =============================================================================


class TestGetKnowledgeGraphSummary:
    """Tests for ContextService.get_knowledge_graph_summary(client_id)."""

    def test_returns_typed_object_when_summary_exists(self, mocker):
        """When knowledge_graph_summary is present, return a typed model."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = _make_context_with_kg_summary(client_id)
        mocker.patch.object(service, "get_client_context", return_value=ctx)

        result = asyncio.run(
            service.get_knowledge_graph_summary(client_id)
        )

        assert isinstance(result, KnowledgeGraphSummary)
        assert result.total_documents == 150
        assert result.total_entities == 80
        assert len(result.top_entities) == 1
        assert result.top_entities[0].name == "Acme"
        assert result.top_entities[0].degree == 42
        assert result.last_sync == "2025-06-19T12:00:00Z"
        assert result.version == 1

    def test_returns_none_when_context_is_none(self, mocker):
        """Returns None when get_client_context returns None."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        mocker.patch.object(service, "get_client_context", return_value=None)

        result = asyncio.run(
            service.get_knowledge_graph_summary(client_id)
        )

        assert result is None

    def test_returns_none_when_available_tools_is_none(self, mocker):
        """Returns None when available_tools is None."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = _make_context_without_available_tools(client_id)
        mocker.patch.object(service, "get_client_context", return_value=ctx)

        result = asyncio.run(
            service.get_knowledge_graph_summary(client_id)
        )

        assert result is None

    def test_returns_none_when_kg_field_missing(self, mocker):
        """Returns None when available_tools exists but no kg summary field."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = _make_context_available_tools_without_kg(client_id)
        mocker.patch.object(service, "get_client_context", return_value=ctx)

        result = asyncio.run(
            service.get_knowledge_graph_summary(client_id)
        )

        assert result is None

    def test_returns_none_when_available_tools_is_empty_dict(self, mocker):
        """Returns None when available_tools is an empty dict."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = BluClientContext(
            id=client_id,
            nome_empresa="Test Corp",
            tier="BASIC",
            available_tools={},
            credenciais=[],
        )
        mocker.patch.object(service, "get_client_context", return_value=ctx)

        result = asyncio.run(
            service.get_knowledge_graph_summary(client_id)
        )

        assert result is None

    def test_returns_none_when_kg_summary_is_none_value(self, mocker):
        """Returns None when knowledge_graph_summary field is None."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = BluClientContext(
            id=client_id,
            nome_empresa="Test Corp",
            tier="BASIC",
            available_tools={
                "enabled_tool_names": ["sql"],
                "knowledge_graph_summary": None,
            },
            credenciais=[],
        )
        mocker.patch.object(service, "get_client_context", return_value=ctx)

        result = asyncio.run(
            service.get_knowledge_graph_summary(client_id)
        )

        assert result is None


# =============================================================================
# get_domain_projection — rag/documents MUST NOT include available_tools
# =============================================================================


class TestDomainProjectionNoAvailableTools:
    """Verify get_domain_projection was NOT altered for rag/documents."""

    def test_rag_domain_excludes_available_tools(self, mocker):
        """rag domain must NOT include available_tools."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = BluClientContext(
            id=client_id,
            nome_empresa="Test Corp",
            tier="BASIC",
            company_profile={"legal_name": "Test Corp"},
            policies={"return_policy": "30 days"},
            brand_voice={"tone": "professional"},
            available_tools={"enabled_tool_names": ["sql"]},
            credenciais=[],
        )
        mocker.patch.object(
            service, "get_client_context", return_value=ctx
        )

        result = asyncio.run(
            service.get_domain_projection("rag", client_id)
        )

        assert "available_tools" not in result
        assert "company_profile" in result
        assert "policies" in result
        assert "brand_voice" in result

    def test_documents_domain_excludes_available_tools(self, mocker):
        """documents domain must NOT include available_tools."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = BluClientContext(
            id=client_id,
            nome_empresa="Test Corp",
            tier="BASIC",
            company_profile={"legal_name": "Test Corp"},
            policies={"return_policy": "30 days"},
            brand_voice={"tone": "professional"},
            available_tools={"enabled_tool_names": ["sql"]},
            credenciais=[],
        )
        mocker.patch.object(
            service, "get_client_context", return_value=ctx
        )

        result = asyncio.run(
            service.get_domain_projection("documents", client_id)
        )

        assert "available_tools" not in result
        assert "company_profile" in result
        assert "policies" in result
        assert "brand_voice" in result

    def test_knowledge_domain_excludes_available_tools(self, mocker):
        """knowledge domain must NOT include available_tools."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = BluClientContext(
            id=client_id,
            nome_empresa="Test Corp",
            tier="BASIC",
            company_profile={"legal_name": "Test Corp"},
            policies={"return_policy": "30 days"},
            brand_voice={"tone": "professional"},
            available_tools={"enabled_tool_names": ["sql"]},
            credenciais=[],
        )
        mocker.patch.object(
            service, "get_client_context", return_value=ctx
        )

        result = asyncio.run(
            service.get_domain_projection("knowledge", client_id)
        )

        assert "available_tools" not in result
        assert "company_profile" in result
        assert "policies" in result
        assert "brand_voice" in result

    def test_analytics_domain_includes_available_tools(self, mocker):
        """analytics domain SHOULD include available_tools (unchanged)."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        service, _ = _make_service(mocker)

        ctx = BluClientContext(
            id=client_id,
            nome_empresa="Test Corp",
            tier="BASIC",
            available_tools={"enabled_tool_names": ["execute_sql"]},
            company_profile={"legal_name": "Test Corp"},
            data_schema={"available_tables": ["orders"]},
            credenciais=[],
        )
        mocker.patch.object(
            service, "get_client_context", return_value=ctx
        )

        result = asyncio.run(
            service.get_domain_projection("analytics", client_id)
        )

        assert "available_tools" in result
        assert "data_schema" in result
        assert "company_profile" in result
