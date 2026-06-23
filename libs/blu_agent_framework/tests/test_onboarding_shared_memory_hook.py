# GOAL: Hook pós-ETL onboarding — Issue #24, Fase 2
# BEHAVIOR: Testes unitários para write_onboarding_snapshot_to_shared_memory
# DECISÃO: create_new — testes focados no hook, monkeypatch + injeção de mock db

"""Unit tests for onboarding_shared_memory_hook.

Tests the ``write_onboarding_snapshot_to_shared_memory`` function in
isolation, injecting a mocked db client to avoid database dependency.

Key behaviors tested:
  - Writes 3 client entries (company_profile, brand_voice, goals)
  - Writes 1 snapshot entry (onboarding:{slug} / key=initial)
  - Writes 1 meta entry in shared_business_memory_meta
  - Snake_case conversion of company names
  - Error handling: Supabase client failure, individual write failures
  - Empty company name handling
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Build a mock Supabase client with a chainable table().upsert().execute().

    Returns the mock db client.
    Uses a closure over `capture` (list) that collects every payload dict
    passed to .upsert(), enabling assertion on what was written.
    """
    capture: list[dict] = []

    # Build the chain: db.schema("public").table("...").upsert(payload, ...).execute()
    mock_execute = MagicMock()
    mock_execute.data = [{"id": 1}]

    mock_upsert = MagicMock()
    mock_upsert.upsert.return_value = mock_execute

    mock_table = MagicMock()
    mock_table.upsert = lambda payload, **kw: (
        capture.append(payload) or mock_upsert
    )

    mock_schema = MagicMock()
    mock_schema.table.return_value = mock_table

    mock_db = MagicMock()
    mock_db.schema.return_value = mock_schema

    # Attach capture to the mock for test assertions
    mock_db._capture = capture
    return mock_db


@pytest.fixture
def sample_structured_context():
    """Return a realistic structured_context dict as produced by onboarding_context_build."""
    return {
        "company_profile": {
            "enriched": {
                "vertical": "ecommerce",
                "products": ["SaaS platform", "API integration"],
                "services": ["consulting", "support"],
                "differentiators": ["AI-powered", "real-time analytics"],
                "target_audience": "Small to medium ecommerce businesses",
                "value_proposition": "AI-driven ecommerce optimization platform",
            }
        },
        "brand_voice": {
            "initial": {
                "tone": "consultivo",
                "vocabulary": ["otimizacao", "inteligencia", "resultados"],
                "formality": "media",
                "example_phrases": [
                    "Transforme seus dados em decisoes",
                ],
            }
        },
        "goals": [
            {
                "dimension": "clientes",
                "title": "Aumentar conversao",
                "target": "15%",
                "deadline": "2026-12-31",
                "unit": "percentual",
            }
        ],
        "home_summary": "Ecommerce SaaS focado em otimizacao com IA.",
        "context_map_md": "# Contexto Inicial — Acme Corp\n...",
    }


# ---------------------------------------------------------------------------
# Helper: patch before first import by manipulating sys.modules
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_supabase_client(monkeypatch):
    """Replace blu_supabase_client.get_supabase_client so the lazy import
    inside write_onboarding_snapshot_to_shared_memory gets a controllable mock.

    The default mock returns a bare MagicMock; individual tests override via
    monkeypatch context if they need a more specific mock.
    """
    import blu_supabase_client

    def _fake_get(*, use_service_role=False):
        raise RuntimeError("_patch_supabase_client default — test must inject mock_db")

    monkeypatch.setattr(blu_supabase_client, "get_supabase_client", _fake_get)


# ---------------------------------------------------------------------------
# Helper to invoke the hook
# ---------------------------------------------------------------------------


async def _call_hook(
    mock_db,
    client_id: str = "00000000-0000-0000-0000-000000000001",
    company_name: str = "Acme Corp",
    structured_context: dict | None = None,
):
    """Invoke the hook with monkeypatched get_supabase_client returning mock_db."""
    import blu_supabase_client

    from blu_agent_framework.onboarding import onboarding_shared_memory_hook as hook_mod

    if structured_context is None:
        structured_context = {
            "company_profile": {},
            "brand_voice": {},
            "goals": [],
        }

    original = blu_supabase_client.get_supabase_client
    blu_supabase_client.get_supabase_client = lambda *, use_service_role=False: mock_db
    try:
        return await hook_mod.write_onboarding_snapshot_to_shared_memory(
            client_id=client_id,
            company_name=company_name,
            structured_context=structured_context,
        )
    finally:
        blu_supabase_client.get_supabase_client = original


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWriteOnboardingSnapshot:
    """Suite for write_onboarding_snapshot_to_shared_memory."""

    @pytest.mark.asyncio
    async def test_writes_three_client_entries(self, mock_db, sample_structured_context):
        """Must write company_profile, brand_voice, and goals under entity_type='client'."""
        result = await _call_hook(mock_db, structured_context=sample_structured_context)

        # All 3 client entries succeed
        assert len(result["client_entries"]) == 3
        assert all(e["success"] for e in result["client_entries"])
        assert result["errors"] == []

        capture = mock_db._capture
        client_payloads = [p for p in capture if p["entity_type"] == "client"]
        assert len(client_payloads) == 3

        keys = {p["key"] for p in client_payloads}
        assert keys == {"company_profile", "brand_voice", "goals"}

    @pytest.mark.asyncio
    async def test_writes_snapshot_entry(self, mock_db, sample_structured_context):
        """Must write a snapshot entry with entity_name 'onboarding:{slug}' and key 'initial'."""
        result = await _call_hook(
            mock_db,
            company_name="Acme Corp",
            structured_context=sample_structured_context,
        )

        assert result["snapshot_entry"]["success"] is True
        assert result["snapshot_entry"]["entity_name"] == "onboarding:acme_corp"

        capture = mock_db._capture
        snapshot_payloads = [p for p in capture if p["entity_type"] == "snapshot"]
        assert len(snapshot_payloads) == 1
        snap = snapshot_payloads[0]
        assert snap["key"] == "initial"
        assert snap["entity_name"] == "onboarding:acme_corp"
        assert snap["value"] == sample_structured_context
        assert snap["source"] == "system"
        assert snap["category"] == "context"
        assert snap["version"] == 1

        # Verify frontmatter in metadata
        metadata = snap["metadata"]
        assert metadata["tipo"] == "snapshot"
        assert metadata["dimensao"] == "clientes"
        assert metadata["periodo"] == "inicial"
        assert metadata["gerado_por"] == "system"
        assert metadata["versao"] == 1
        assert metadata["template_version"] == 1
        assert metadata["fontes"] == ["onboarding_wizard", "website_scrape"]
        assert "gerado_em" in metadata  # runtime-filled

    @pytest.mark.asyncio
    async def test_writes_meta_entry(self, mock_db, sample_structured_context):
        """Must write a meta entry for hook execution metadata."""
        result = await _call_hook(mock_db, structured_context=sample_structured_context)

        assert result["meta_entry"]["success"] is True

        capture = mock_db._capture
        meta_payloads = [p for p in capture if p["entity_type"] == "synthesis_output"]
        assert len(meta_payloads) == 1
        meta = meta_payloads[0]
        assert meta["key"] == "onboarding_snapshot"
        assert meta["source"] == "system"
        assert "hook" in meta["body"]
        assert meta["body"]["hook"] == "onboarding_shared_memory_hook"
        assert meta["body"]["version"] == 1
        assert "written_at" in meta["body"]
        assert "company_name" in meta["body"]
        assert "entity_name" in meta["body"]

    @pytest.mark.asyncio
    async def test_snake_case_conversion(self, mock_db):
        """Company names must be converted to snake_case for entity_name."""
        cases = [
            ("Acme Corp", "acme_corp"),
            ("  Tech 4 Good  ", "tech_4_good"),
            ("João's Café!", "joos_caf"),        # ã, â, ç stripped; ' stripped
            ("BLU-Solutions", "blusolutions"),  # hyphens stripped
            ("simple", "simple"),
        ]
        for raw, expected in cases:
            mock_db._capture.clear()
            result = await _call_hook(mock_db, company_name=raw)
            assert result["errors"] == []
            capture = mock_db._capture
            client_payloads = [p for p in capture if p["entity_type"] == "client"]
            if client_payloads:
                assert client_payloads[0]["entity_name"] == expected
            snapshot_payloads = [p for p in capture if p["entity_type"] == "snapshot"]
            if snapshot_payloads:
                assert snapshot_payloads[0]["entity_name"] == f"onboarding:{expected}"

    @pytest.mark.asyncio
    async def test_empty_company_name_returns_early(self, mock_db):
        """An empty/symbol-only company name should return early with an error."""
        result = await _call_hook(mock_db, company_name="!!!")
        assert result["errors"] != []
        assert result["client_entries"] == []
        assert result["snapshot_entry"] is None
        assert result["meta_entry"] is None

    @pytest.mark.asyncio
    async def test_client_entries_have_correct_payload_structure(self, mock_db):
        """Each client entry must have source='system', category='context', confidence=1.0."""
        structured = {
            "company_profile": {"enriched": {"vertical": "tech"}},
            "brand_voice": {"initial": {"tone": "formal"}},
            "goals": [{"dimension": "clientes", "title": "Crescer"}],
        }
        result = await _call_hook(mock_db, structured_context=structured)
        assert result["errors"] == []

        capture = mock_db._capture
        client_payloads = [p for p in capture if p["entity_type"] == "client"]
        for p in client_payloads:
            assert p["source"] == "system"
            assert p["category"] == "context"
            assert p["confidence"] == 1.0
            assert p["version"] == 1
            assert p["metadata"] == {
                "onboarding_version": 1,
                "generated_by": "onboarding_complete_routine",
            }

    @pytest.mark.asyncio
    async def test_client_id_passed_through(self, mock_db):
        """The client_id must be passed through to every payload."""
        client_id = "550e8400-e29b-41d4-a716-446655440000"
        await _call_hook(mock_db, client_id=client_id)
        for p in mock_db._capture:
            assert p["client_id"] == client_id

    @pytest.mark.asyncio
    async def test_logs_error_when_db_init_fails(self):
        """If get_supabase_client raises, the hook must return early with error."""
        import blu_supabase_client

        from blu_agent_framework.onboarding import onboarding_shared_memory_hook as hook_mod

        original = blu_supabase_client.get_supabase_client

        def _failing(*, use_service_role=False):
            raise RuntimeError("Connection refused")

        blu_supabase_client.get_supabase_client = _failing
        try:
            result = await hook_mod.write_onboarding_snapshot_to_shared_memory(
                client_id="00000000-0000-0000-0000-000000000001",
                company_name="Acme Corp",
                structured_context={},
            )
        finally:
            blu_supabase_client.get_supabase_client = original

        assert result["errors"] != []
        assert "Connection refused" in result["errors"][0]
        assert result["snapshot_entry"] is None
        assert result["meta_entry"] is None

    @pytest.mark.asyncio
    async def test_individual_write_failure_does_not_break_others(self, mock_db):
        """If one client write fails, the others must still proceed."""
        # Make the second call to upsert fail
        call_count = [0]

        def _fail_on_second(*args, **kw):
            call_count[0] += 1
            if call_count[0] == 2:  # second client entry (brand_voice)
                raise RuntimeError("Simulated DB error")
            # otherwise chain normally
            mock_execute = MagicMock()
            mock_execute.data = [{"id": 999}]
            mock_upsert = MagicMock()
            mock_upsert.upsert.return_value = mock_execute
            mock_table = MagicMock()
            mock_table.upsert.return_value = mock_upsert
            mock_schema = MagicMock()
            mock_schema.table.return_value = mock_table
            return mock_schema

        mock_db.schema.side_effect = _fail_on_second

        result = await _call_hook(mock_db)

        # First and third client entry should succeed
        entries = result["client_entries"]
        assert entries[0]["success"] is True
        assert entries[1]["success"] is False  # the one we broke
        assert entries[2]["success"] is True

        # Snapshot and meta should still succeed
        assert result["snapshot_entry"]["success"] is True
        assert result["meta_entry"]["success"] is True

        # Errors list must contain the failure
        assert any("brand_voice" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_structured_context_defaults_empty_values(self, mock_db):
        """If structured_context is missing keys, defaults to empty dicts/list."""
        result = await _call_hook(
            mock_db,
            structured_context={"unrelated": "data"},
        )

        assert result["errors"] == []
        assert all(e["success"] for e in result["client_entries"])

        capture = mock_db._capture
        client_payloads = [p for p in capture if p["entity_type"] == "client"]
        profile_payload = next(p for p in client_payloads if p["key"] == "company_profile")
        assert profile_payload["value"] == {}

        goals_payload = next(p for p in client_payloads if p["key"] == "goals")
        assert goals_payload["value"] == []

    @pytest.mark.asyncio
    async def test_meta_entry_contains_context_keys(self, mock_db, sample_structured_context):
        """Meta entry body must list the keys from structured_context."""
        await _call_hook(mock_db, structured_context=sample_structured_context)

        capture = mock_db._capture
        meta_payloads = [p for p in capture if p["entity_type"] == "synthesis_output"]
        assert len(meta_payloads) == 1
        keys = meta_payloads[0]["body"]["structured_context_keys"]
        assert "company_profile" in keys
        assert "brand_voice" in keys
        assert "goals" in keys
        assert "home_summary" in keys
        assert "context_map_md" in keys

    @pytest.mark.asyncio
    async def test_idempotent_upsert_on_conflict(self, mock_db):
        """Calling the hook twice must use upsert (no duplicate-key errors)."""
        structured = {"company_profile": {"x": 1}, "brand_voice": {"y": 2}, "goals": []}

        r1 = await _call_hook(mock_db, structured_context=structured)
        assert r1["errors"] == []
        first_count = len(mock_db._capture)

        r2 = await _call_hook(mock_db, structured_context=structured)
        assert r2["errors"] == []
        second_count = len(mock_db._capture)

        # Both calls produced payloads — upsert means no conflict
        assert second_count == first_count * 2
