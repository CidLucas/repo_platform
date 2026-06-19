"""Unit tests for the business-memory REST endpoint (T5.1).

Tests the ``business_memory_router`` with:
- Mocked Supabase client (avoids real database)
- Mocked authentication
- Covers: list all, filter by entity_type, filter by entity_name,
  pagination, get single record, invalid UUID, not found, server errors
"""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tool_pool_api.api import business_memory_router


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
                "entity_name": f"financeiro:semanal",
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


def _make_mock_supabase_client(rows: list[dict] | None = None, raise_error: bool = False):
    """Create a mock Supabase client that returns the given rows."""
    db = MagicMock()
    result = MagicMock()
    result.data = rows

    if raise_error:
        # Make execute() raise
        result.execute.side_effect = Exception("Database connection failed")
    else:
        result.execute.return_value = result

    # Build chain: db.schema().table().select()...etc -> result
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
def client_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def app():
    """FastAPI app with only the business_memory_router mounted."""
    app = FastAPI()
    app.include_router(business_memory_router.router)
    return app


@pytest.fixture
def client(app, monkeypatch):
    """TestClient with mocked auth and Supabase."""
    client_id = uuid.uuid4()

    # Patch auth dependency
    monkeypatch.setattr(
        business_memory_router,
        "_get_auth_result",
        lambda *a, **k: FakeAuthResult(client_id=client_id),
    )

    return TestClient(app), client_id


# ---------------------------------------------------------------------------
# Tests — list endpoint
# ---------------------------------------------------------------------------


def test_list_business_memory_success(client, monkeypatch):
    """Should return all records for the authenticated client."""
    test_client, client_id = client
    rows = _sample_rows(count=2)
    mock_db = _make_mock_supabase_client(rows)

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 200

    body = resp.json()
    assert body["client_id"] == str(client_id)
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


def test_list_business_memory_empty(client, monkeypatch):
    """Should return empty records array for client with no data."""
    test_client, client_id = client
    mock_db = _make_mock_supabase_client([])

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 0
    assert body["records"] == []


def test_list_business_memory_none_data(client, monkeypatch):
    """Should handle None .data gracefully (returns empty)."""
    test_client, client_id = client
    mock_db = _make_mock_supabase_client(None)

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 0
    assert body["records"] == []


def test_list_business_memory_filter_by_entity_type(client, monkeypatch):
    """Should apply entity_type filter when provided."""
    test_client, client_id = client
    rows = _sample_rows(count=1)
    mock_db = _make_mock_supabase_client(rows)

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    resp = test_client.get("/api/business-memory?entity_type=snapshot")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 1


def test_list_business_memory_filter_by_entity_name(client, monkeypatch):
    """Should apply entity_name filter when provided."""
    test_client, client_id = client
    rows = _sample_rows(count=1)
    mock_db = _make_mock_supabase_client(rows)

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    resp = test_client.get("/api/business-memory?entity_name=financeiro")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_records"] == 1


def test_list_business_memory_pagination(client, monkeypatch):
    """Should respect limit and offset query params."""
    test_client, client_id = client
    rows = _sample_rows(count=5)
    mock_db = _make_mock_supabase_client(rows)

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    # Request 2 records, offset 0
    resp = test_client.get("/api/business-memory?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_records"] == 5  # total is what mock returns


def test_list_business_memory_db_error(client, monkeypatch):
    """Should return 500 on database error."""
    test_client, client_id = client
    mock_db = _make_mock_supabase_client(raise_error=True)

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    resp = test_client.get("/api/business-memory")
    assert resp.status_code == 500
    assert "Failed to query" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests — get single record endpoint
# ---------------------------------------------------------------------------


def test_get_business_memory_record_success(client, monkeypatch):
    """Should return a single record by UUID."""
    test_client, client_id = client
    record_id = str(uuid.uuid4())
    row = {
        "id": record_id,
        "client_id": str(client_id),
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

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: mock_db
    )

    resp = test_client.get(f"/api/business-memory/{record_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["id"] == record_id
    assert body["entity_type"] == "snapshot"
    assert body["entity_name"] == "financeiro:diario"
    assert body["key"] == "2026-06-19T10:00:00Z"


def test_get_business_memory_record_invalid_uuid(client, monkeypatch):
    """Should return 400 for non-UUID record ID."""
    test_client, client_id = client

    resp = test_client.get("/api/business-memory/not-a-uuid")
    assert resp.status_code == 400
    assert "Invalid record ID format" in resp.json()["detail"]


def test_get_business_memory_record_not_found(client, monkeypatch):
    """Should return 404 when record doesn't exist."""
    test_client, client_id = client
    record_id = str(uuid.uuid4())

    # Return no data via exception (Supabase .single() raises on no match)
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

    monkeypatch.setattr(
        business_memory_router, "get_supabase_client", lambda: db
    )

    resp = test_client.get(f"/api/business-memory/{record_id}")
    assert resp.status_code == 404
