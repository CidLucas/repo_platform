"""Unit tests for the business-memory REST endpoint (T5.1).

Tests the ``business_memory_router`` with:
- Mocked Supabase client (avoids real database)
- Mocked authentication via FastAPI dependency_overrides
- Covers: list all, filter by entity_type, filter by entity_name,
  pagination, get single record, invalid UUID, not found, server errors
"""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tool_pool_api.api import business_memory_router
from tool_pool_api.api.integrations_router import _get_auth_result


# ---------------------------------------------------------------------------
# Fake objects
# ---------------------------------------------------------------------------


class FakeAuthResult:
    """Mock auth result with a fixed client_id."""

    def __init__(self, client_id: uuid.UUID | None = None):
        self.client_id = client_id or uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_rows(count: int = 3) -> list[dict]:
    """Build sample row data for testing."""
    rows = []
    for i in range(1, count + 1):
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "client_id": str(uuid.uuid4()),
                "entity_type": "snapshot",
                "entity_name": "financeiro:semanal",
                "key": f"2026-06-{15 + i:02d}T10:00:00Z",
                "value": {
                    "indicadores": [{"nome": "receita", "valor": 50000}],
                    "resumo_executivo": f"Snapshot #{i}",
                },
                "metadata": {"source_agent": "specialist-7"},
                "source": "specialist",
                "confidence": 0.95,
                "version": 1,
                "created_at": "2026-06-19T10:00:00Z",
                "updated_at": "2026-06-19T10:00:00Z",
            }
        )
    return rows


def _make_mock_supabase_client(
    rows: list[dict] | None = None,
    raise_error: bool = False,
) -> MagicMock:
    """Create a mock Supabase client that returns the given rows."""
    db = MagicMock()

    if raise_error:
        result = MagicMock()
        result.data = None

        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.ilike.return_value = query
        query.order.return_value = query
        query.range.return_value = query
        query.single.return_value = query
        query.execute.side_effect = Exception("Database connection failed")
    else:
        result = MagicMock()
        result.data = rows
        result.execute.return_value = result

        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.ilike.return_value = query
        query.order.return_value = query
        query.range.return_value = query
        query.single.return_value = query
        query.execute.return_value = result

    schema_mock = MagicMock()
    schema_mock.table.return_value = query

    db.schema.return_value = schema_mock
    return db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_auth():
    return FakeAuthResult()


@pytest.fixture
def app(fake_auth):
    """FastAPI app with mocked auth via dependency_overrides."""
    app = FastAPI()
    app.include_router(business_memory_router.router)
    # Override the auth dependency so no real JWT is required
    app.dependency_overrides[_get_auth_result] = lambda _fake=fake_auth: _fake
    return app


@pytest.fixture
def client(app, fake_auth):
    """TestClient with mocked auth."""
    return TestClient(app), fake_auth


# ---------------------------------------------------------------------------
# Tests — list endpoint
# ---------------------------------------------------------------------------


def test_list_business_memory_success(client, fake_auth):
    """Should return all records for the authenticated client."""
    test_client, _ = client
    rows = _sample_rows(count=2)
    mock_db = _make_mock_supabase_client(rows)

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 200

    body = resp.json()
    assert body["client_id"] == str(fake_auth.client_id)
    assert body["total_records"] == 2
    assert len(body["records"]) == 2
    assert body["records"][0]["entity_type"] == "snapshot"
    assert body["records"][0]["entity_name"] == "financeiro:semanal"
    assert body["records"][0]["key"].startswith("2026-06-")
    assert body["records"][0]["value"] is not None
    assert body["records"][0]["metadata"] == {"source_agent": "specialist-7"}
    assert body["records"][0]["source"] == "specialist"
    assert body["records"][0]["confidence"] == 0.95
    assert body["records"][0]["version"] == 1
    assert body["records"][0]["created_at"] is not None
    assert body["records"][0]["updated_at"] is not None


def test_list_business_memory_empty(client):
    """Should return empty records array for client with no data."""
    test_client, _ = client
    mock_db = _make_mock_supabase_client([])

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 0
    assert body["records"] == []


def test_list_business_memory_none_data(client):
    """Should handle None .data gracefully (returns empty)."""
    test_client, _ = client
    mock_db = _make_mock_supabase_client(None)

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 0
    assert body["records"] == []


def test_list_business_memory_filter_by_entity_type(client):
    """Should apply entity_type filter when provided."""
    test_client, _ = client
    rows = _sample_rows(count=1)
    mock_db = _make_mock_supabase_client(rows)

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get("/api/business-memory?entity_type=snapshot")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 1


def test_list_business_memory_filter_by_entity_name(client):
    """Should apply entity_name filter when provided."""
    test_client, _ = client
    rows = _sample_rows(count=1)
    mock_db = _make_mock_supabase_client(rows)

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get("/api/business-memory?entity_name=financeiro")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 1


def test_list_business_memory_pagination(client):
    """Should respect limit and offset query params."""
    test_client, _ = client
    rows = _sample_rows(count=5)
    mock_db = _make_mock_supabase_client(rows)

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get("/api/business-memory?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_records"] == 5  # total is what mock returns


def test_list_business_memory_db_error(client):
    """Should return 500 on database error."""
    test_client, _ = client
    mock_db = _make_mock_supabase_client(raise_error=True)

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 500
    assert "Failed to query" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests — get single record endpoint
# ---------------------------------------------------------------------------


def test_get_business_memory_record_success(client, fake_auth):
    """Should return a single record by UUID."""
    test_client, _ = client
    record_id = str(uuid.uuid4())
    row = {
        "id": record_id,
        "client_id": str(fake_auth.client_id),
        "entity_type": "snapshot",
        "entity_name": "financeiro:diario",
        "key": "2026-06-19T10:00:00Z",
        "value": {"indicadores": []},
        "metadata": {},
        "source": "system",
        "confidence": 1.0,
        "version": 2,
        "created_at": "2026-06-19T10:00:00Z",
        "updated_at": "2026-06-19T11:00:00Z",
    }
    mock_db = _make_mock_supabase_client(row)

    business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

    resp = test_client.get(f"/api/business-memory/{record_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["id"] == record_id
    assert body["entity_type"] == "snapshot"
    assert body["entity_name"] == "financeiro:diario"
    assert body["key"] == "2026-06-19T10:00:00Z"


def test_get_business_memory_record_invalid_uuid(client):
    """Should return 400 for non-UUID record ID."""
    test_client, _ = client

    resp = test_client.get("/api/business-memory/not-a-uuid")
    assert resp.status_code == 400
    assert "Invalid record ID format" in resp.json()["detail"]


def test_get_business_memory_record_not_found(client):
    """Should return 404 when record doesn't exist."""
    test_client, _ = client
    record_id = str(uuid.uuid4())

    # Supabase .single() raises on no match
    db = MagicMock()
    schema_mock = MagicMock()
    table_mock = MagicMock()
    query_mock = MagicMock()

    query_mock.select.return_value = query_mock
    query_mock.eq.return_value = query_mock
    query_mock.single.return_value = query_mock
    query_mock.execute.side_effect = Exception("No rows found")

    table_mock.select.return_value = query_mock
    schema_mock.table.return_value = table_mock
    db.schema.return_value = schema_mock

    business_memory_router.get_supabase_client = MagicMock(return_value=db)

    resp = test_client.get(f"/api/business-memory/{record_id}")
    assert resp.status_code == 404
