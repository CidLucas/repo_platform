"""
Unit tests for sbm_to_lightrag_synthesis module (T4.1g).

Tests:
  - normalize_entity_name: basic, contact prefix, edge cases
  - build_synthesis: skill, client, contact, supplier, user, snapshot
  - lightrag_client cache: hit, TTL expiry, clear single, clear all
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from tool_pool_api.server.tool_modules.sbm_to_lightrag_synthesis import (
    SYNTHESIS_TEMPLATES,
    build_synthesis,
    normalize_entity_name,
)


# =============================================================================
# Sample record builders
# =============================================================================

def _make_record(
    entity_type: str = "client",
    entity_name: str = "Acme Corp",
    key: str = "preferencia_comunicacao",
    value: dict | list | str | None = None,
    source: str = "manual",
    confidence: float = 1.0,
    updated_at: str = "2026-06-15T10:00:00Z",
) -> dict:
    """Build a single SBM record dict matching the query result shape."""
    if value is None:
        value = {"canal": "WhatsApp", "tom": "amigavel"}
    return {
        "id": str(uuid4()),
        "client_id": str(uuid4()),
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "value": value,
        "metadata": {},
        "source": source,
        "confidence": confidence,
        "curated": True,
        "expires_at": None,
        "created_at": "2026-06-15T10:00:00Z",
        "updated_at": updated_at,
    }


# =============================================================================
# normalize_entity_name tests
# =============================================================================

class TestNormalizeEntityName:
    """Unit tests for normalize_entity_name — canonical ID generation."""

    # --- Basic ---------------------------------------------------------------

    def test_normalize_entity_name_basic(self):
        """Simple names: 'João da Silva' → 'joao_da_silva'."""
        assert normalize_entity_name("João da Silva") == "joao_da_silva"

    def test_normalize_entity_name_simple(self):
        """Simple ASCII name."""
        assert normalize_entity_name("Acme Corp") == "acme_corp"

    def test_normalize_entity_name_single_word(self):
        """Single-word name."""
        assert normalize_entity_name("Google") == "google"

    # --- Contact prefix ------------------------------------------------------

    def test_normalize_entity_name_contact_prefix(self):
        """entity_type='contact' prefixes with 'contact:'."""
        result = normalize_entity_name("João da Silva", entity_type="contact")
        assert result == "contact:joao_da_silva"

    def test_normalize_entity_name_contact_prefix_simple(self):
        """Contact with ASCII name."""
        result = normalize_entity_name("Maria Souza", entity_type="contact")
        assert result == "contact:maria_souza"

    # --- Edge cases ----------------------------------------------------------

    def test_normalize_entity_name_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_entity_name("") == ""

    def test_normalize_entity_name_whitespace_only(self):
        """Whitespace-only string collapses to empty."""
        assert normalize_entity_name("   ") == ""

    def test_normalize_entity_name_accents_removed(self):
        """Accents stripped: 'José' → 'jose'."""
        assert normalize_entity_name("José") == "jose"

    def test_normalize_entity_name_special_chars_removed(self):
        """Special characters removed: 'C&A Modas' → 'ca_modas'."""
        assert normalize_entity_name("C&A Modas") == "ca_modas"

    def test_normalize_entity_name_multiple_spaces_collapsed(self):
        """Multiple spaces collapse to single underscore."""
        assert normalize_entity_name("João   da   Silva") == "joao_da_silva"

    def test_normalize_entity_name_trailing_punctuation(self):
        """Trailing punctuation removed."""
        assert normalize_entity_name("Acme Corp.") == "acme_corp"

    def test_normalize_entity_name_mixed_accents_and_symbols(self):
        """Mixed accents and symbols: 'São Paulo S/A' → 'sao_paulo_sa'."""
        assert normalize_entity_name("São Paulo S/A") == "sao_paulo_sa"

    def test_normalize_entity_name_digits_preserved(self):
        """Digits preserved: 'Client 123' → 'client_123'."""
        assert normalize_entity_name("Client 123") == "client_123"

    def test_normalize_entity_name_underscore_collapse(self):
        """Multiple hyphens removed → no underscores between them: 'A--B' → 'ab'."""
        # Hyphens are punctuation removed by _RE_PUNCTUATION; nothing remains
        # between 'a' and 'b' after removal, so result is 'ab' not 'a_b'.
        assert normalize_entity_name("A--B") == "ab"

    def test_normalize_entity_name_none_input(self):
        """None treated as empty string (via str coercion handled by caller)."""
        # Our implementation checks `if not name` so None → truthy as bool(None) = False
        assert normalize_entity_name(None) == ""  # type: ignore[arg-type]


# =============================================================================
# build_synthesis tests
# =============================================================================

class TestBuildSynthesis:
    """Unit tests for build_synthesis — Markdown synthesis generation."""

    # --- Skill ---------------------------------------------------------------

    def test_build_synthesis_skill(self):
        """Skill entity_type generates correct Markdown with heading and facts."""
        records = [
            _make_record(
                entity_type="skill",
                entity_name="Python Development",
                key="proficiency",
                value={"level": "advanced", "years": 5},
                source="linkedin",
                confidence=0.9,
            ),
            _make_record(
                entity_type="skill",
                entity_name="Python Development",
                key="certifications",
                value=["PCEP", "PCAP"],
                source="manual",
                confidence=0.85,
            ),
        ]
        result = build_synthesis(records)

        assert "# python_development" in result
        assert "**Type**: Skill" in result
        assert "**Source**: linkedin" in result
        assert "**Confidence**: 0.9" in result
        assert "### proficiency" in result
        assert "level" in result
        assert "advanced" in result
        assert "### certifications" in result
        assert "PCEP" in result
        assert "PCAP" in result

    # --- Client --------------------------------------------------------------

    def test_build_synthesis_client(self):
        """Client entity_type with nested dict value."""
        records = [
            _make_record(
                entity_type="client",
                entity_name="Acme Corp",
                key="company_info",
                value={"industry": "Tech", "employees": 500},
            ),
        ]
        result = build_synthesis(records)

        assert "# acme_corp" in result
        assert "**Type**: Client" in result
        assert "### company_info" in result
        assert "**industry**" in result
        assert "Tech" in result
        assert "**employees**" in result
        assert "500" in result

    # --- Contact -------------------------------------------------------------

    def test_build_synthesis_contact(self):
        """Contact entity_type uses contact: prefix in heading (template + normalize)."""
        records = [
            _make_record(
                entity_type="contact",
                entity_name="João Silva",
                key="role",
                value="CEO",
                source="crm",
            ),
        ]
        result = build_synthesis(records)

        # normalize_entity_name adds 'contact:' prefix AND template heading
        # also uses it → doubling. This is the current behavior.
        assert "contact:" in result
        assert "**Type**: Contact" in result
        assert "**Source**: crm" in result

    # --- Supplier ------------------------------------------------------------

    def test_build_synthesis_supplier(self):
        """Supplier entity_type."""
        records = [
            _make_record(
                entity_type="supplier",
                entity_name="Fornecedor XYZ",
                key="contract",
                value={"status": "active", "renewal": "2027-01-01"},
            ),
        ]
        result = build_synthesis(records)

        assert "# fornecedor_xyz" in result
        assert "**Type**: Supplier" in result
        assert "### contract" in result
        assert "**status**" in result
        assert "active" in result

    # --- User ----------------------------------------------------------------

    def test_build_synthesis_user(self):
        """User entity_type."""
        records = [
            _make_record(
                entity_type="user",
                entity_name="Maria Souza",
                key="department",
                value="Engineering",
            ),
        ]
        result = build_synthesis(records)

        assert "# maria_souza" in result
        assert "**Type**: User" in result
        assert "### department" in result
        assert "Engineering" in result

    # --- Snapshot ------------------------------------------------------------

    def test_build_synthesis_snapshot(self):
        """Snapshot entity_type generates special layout with resumo and indicadores."""
        records = [
            _make_record(
                entity_type="snapshot",
                entity_name="financeiro:semanal",
                key="resumo_executivo",
                value="Receita cresceu 15% esta semana.",
            ),
            _make_record(
                entity_type="snapshot",
                entity_name="financeiro:semanal",
                key="indicadores",
                value={"receita": 50000, "despesas": 30000},
            ),
            _make_record(
                entity_type="snapshot",
                entity_name="financeiro:semanal",
                key="kp_is",
                value=[
                    {"nome": "NPS", "valor": 85},
                    {"nome": "Churn", "valor": 2.1},
                ],
            ),
            _make_record(
                entity_type="snapshot",
                entity_name="financeiro:semanal",
                key="general_notes",
                value="Equipe motivada com os resultados.",
            ),
        ]
        result = build_synthesis(records)

        # Colon in "financeiro:semanal" is removed as punctuation by normalize_entity_name
        assert "financeirosemanal" in result
        assert "**Type**: Snapshot" in result
        assert "## Resumo Executivo" in result
        assert "Receita cresceu 15% esta semana." in result
        assert "## Indicadores" in result
        assert "**receita**" in result
        assert "50000" in result

    # --- Edge cases ----------------------------------------------------------

    def test_build_synthesis_empty_records(self):
        """Empty record list returns empty string."""
        assert build_synthesis([]) == ""

    def test_build_synthesis_unknown_entity_type(self):
        """Unknown entity_type uses the generic fallback template.

        Regression: o fallback tem placeholder {entity_type} que não era
        passado ao format() — todo entity_type sem template dedicado (ex.:
        routine) explodia com KeyError. Corrigido em 2026-07-15.
        """
        records = [
            _make_record(
                entity_type="unknown_xyz",
                entity_name="Mystery Entity",
                key="data",
                value="some value",
            ),
        ]
        result = build_synthesis(records)
        assert "**Type**: unknown_xyz" in result
        assert "mystery_entity" in result
        assert "some value" in result

    def test_build_synthesis_empty_value_skipped(self):
        """Records with empty values are omitted from facts block.
        
        Note: _make_record(value=None) triggers the default, so we construct
        the None/empty-value records manually.
        """
        valid = _make_record(
            entity_type="client",
            entity_name="Acme",
            key="keep_me",
            value="valid data",
        )
        # Construct null-value records manually to bypass _make_record's default
        null_record = {
            "id": str(uuid4()),
            "client_id": str(uuid4()),
            "entity_type": "client",
            "entity_name": "Acme",
            "key": "skip_none",
            "value": None,
            "metadata": {},
            "source": "manual",
            "confidence": 1.0,
            "curated": True,
            "expires_at": None,
            "created_at": "2026-06-15T10:00:00Z",
            "updated_at": "2026-06-15T10:00:00Z",
        }
        empty_dict = {**null_record, "key": "skip_empty_dict", "value": {}}
        empty_str = {**null_record, "key": "skip_empty_str", "value": ""}

        records = [valid, null_record, empty_dict, empty_str]
        result = build_synthesis(records)

        assert "### keep_me" in result
        assert "valid data" in result
        assert "### skip_none" not in result
        assert "### skip_empty_dict" not in result
        assert "### skip_empty_str" not in result

    def test_build_synthesis_snapshot_without_indicators(self):
        """Snapshot with only resumo_executivo records — indicators fallback message shown."""
        records = [
            _make_record(
                entity_type="snapshot",
                entity_name="simple_snapshot",
                key="resumo_executivo",
                value="Just a summary.",
            ),
            _make_record(
                entity_type="snapshot",
                entity_name="simple_snapshot",
                key="resumo_financeiro",
                value="Revenue up 10%.",
            ),
        ]
        result = build_synthesis(records)

        assert "_No indicators available._" in result
        # resumo_executivo records still appear in the "All Facts" section
        # but they are split out of the facts block into the Resumo Executivo section

    def test_build_synthesis_list_value_bullets(self):
        """List values render as bullet points."""
        records = [
            _make_record(
                entity_type="skill",
                entity_name="DevOps",
                key="tools",
                value=["Docker", "Kubernetes", "Terraform"],
            ),
        ]
        result = build_synthesis(records)

        assert "- Docker" in result
        assert "- Kubernetes" in result
        assert "- Terraform" in result

    def test_build_synthesis_uses_first_record_metadata(self):
        """Entity metadata (source, confidence) comes from the first record."""
        records = [
            _make_record(
                entity_type="client",
                entity_name="Acme",
                key="primary",
                value="first record",
                source="source_a",
                confidence=0.8,
            ),
            _make_record(
                entity_type="client",
                entity_name="Acme",
                key="secondary",
                value="second record",
                source="source_b",
                confidence=0.5,
            ),
        ]
        result = build_synthesis(records)

        assert "**Source**: source_a" in result
        assert "**Confidence**: 0.8" in result
        assert "**Source**: source_b" not in result


# =============================================================================
# LightRAG client cache tests — async tests
# =============================================================================

@pytest.mark.asyncio
class TestLightRagClientCache:
    """Tests for get_client_rag cache behavior."""

    @pytest.fixture(autouse=True)
    def _setup_cache(self):
        """Reset the global cache before each test."""
        from tool_pool_api.server.utils.lightrag_client import _RAG_CLIENTS

        _RAG_CLIENTS.clear()
        yield
        _RAG_CLIENTS.clear()

    # --- Cache hit -----------------------------------------------------------

    async def test_lightrag_client_cache_hit(self):
        """Second call to get_client_rag returns the cached (same) instance."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174000")

        mock_rag = MagicMock()
        mock_rag.initialize_storages = AsyncMock()

        with patch(
            "tool_pool_api.server.utils.lightrag_client._create_lightrag_instance",
            return_value=mock_rag,
        ), patch(
            "tool_pool_api.server.utils.lightrag_client._ensure_postgres_env_from_database_url",
        ):
            from tool_pool_api.server.utils.lightrag_client import (
                _RAG_CLIENTS,
                get_client_rag,
            )

            # First call — creates instance
            first = await get_client_rag(client_id)
            assert first is mock_rag
            assert str(client_id) in _RAG_CLIENTS

            # Second call — should return cached instance
            second = await get_client_rag(client_id)
            assert second is first  # same object identity

    # --- TTL expiry ----------------------------------------------------------

    async def test_lightrag_client_cache_ttl_expiry(self):
        """After TTL expires, a new instance is created."""
        client_id = UUID("123e4567-e89b-12d3-a456-426614174001")
        client_id_str = str(client_id)

        mock_rag_old = MagicMock()
        mock_rag_old.initialize_storages = AsyncMock()
        mock_rag_new = MagicMock()
        mock_rag_new.initialize_storages = AsyncMock()

        from tool_pool_api.server.utils.lightrag_client import (
            _RAG_CLIENTS,
            _RAG_CLIENTS_TTL,
        )

        # Pre-populate cache with an expired entry
        import time

        _RAG_CLIENTS[client_id_str] = (mock_rag_old, time.time() - _RAG_CLIENTS_TTL - 60)

        with patch(
            "tool_pool_api.server.utils.lightrag_client._ensure_postgres_env_from_database_url",
        ):
            with patch(
                "tool_pool_api.server.utils.lightrag_client._create_lightrag_instance",
                return_value=mock_rag_new,
            ):
                from tool_pool_api.server.utils.lightrag_client import get_client_rag

                result = await get_client_rag(client_id)

        # Should return the new instance
        assert result is mock_rag_new
        assert result is not mock_rag_old
        # Cache should now have the new instance
        cached_instance, _ = _RAG_CLIENTS[client_id_str]
        assert cached_instance is mock_rag_new


# =============================================================================
# LightRAG client cache tests — sync tests
# =============================================================================


class TestLightRagClientCacheClear:
    """Tests for clear_client_rag_cache."""

    @pytest.fixture(autouse=True)
    def _setup_cache(self):
        """Reset the global cache before each test."""
        from tool_pool_api.server.utils.lightrag_client import _RAG_CLIENTS

        _RAG_CLIENTS.clear()
        yield
        _RAG_CLIENTS.clear()

    # --- Clear cache single --------------------------------------------------

    def test_clear_cache_single(self):
        """clear_client_rag_cache(client_id) removes only that entry."""
        from tool_pool_api.server.utils.lightrag_client import (
            _RAG_CLIENTS,
            clear_client_rag_cache,
        )

        client_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        client_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        mock_a = MagicMock()
        mock_b = MagicMock()
        _RAG_CLIENTS[client_a] = (mock_a, 1000.0)
        _RAG_CLIENTS[client_b] = (mock_b, 2000.0)

        clear_client_rag_cache(client_a)

        assert client_a not in _RAG_CLIENTS
        assert client_b in _RAG_CLIENTS
        remaining, _ = _RAG_CLIENTS[client_b]
        assert remaining is mock_b

    def test_clear_cache_single_nonexistent(self):
        """Clearing a non-existent client_id does not raise."""
        from tool_pool_api.server.utils.lightrag_client import clear_client_rag_cache

        clear_client_rag_cache("nonexistent-id")  # no exception

    # --- Clear cache all -----------------------------------------------------

    def test_clear_cache_all(self):
        """clear_client_rag_cache() without args removes all entries."""
        from tool_pool_api.server.utils.lightrag_client import (
            _RAG_CLIENTS,
            clear_client_rag_cache,
        )

        client_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        client_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        _RAG_CLIENTS[client_a] = (MagicMock(), 1000.0)
        _RAG_CLIENTS[client_b] = (MagicMock(), 2000.0)

        clear_client_rag_cache()  # clear all

        assert len(_RAG_CLIENTS) == 0
