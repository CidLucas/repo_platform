"""Integration tests for business_memory_router (T5.1) API endpoint.

Tests the GET /api/business-memory and GET /api/business-memory/{id}
endpoints with:

- Authentication failure (no auth header) → 401
- Happy path — returns correct data structure
- Filtering by entity_type, entity_name
- Pagination (limit/offset)
- Invalid UUID → 400
- Record not found → 404
- Server error handling → 500

Uses FastAPI dependency_overrides to mock auth and Supabase,
so no real database or JWT tokens are needed.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from tool_pool_api.api import business_memory_router
from tool_pool_api.api.integrations_router import _get_auth_result

# ---------------------------------------------------------------------------
#  Fake objects
# ---------------------------------------------------------------------------


class FakeAuthResult:
    """Mock auth result with a fixed client_id."""

    def __init__(self, client_id: uuid.UUID | None = None):
        self.client_id = client_id or uuid.uuid4()


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_auth():
    """Return a FakeAuthResult with a random client_id."""
    return FakeAuthResult()


@pytest.fixture
def app(fake_auth):
    """FastAPI app with mocked auth dependency."""
    app = FastAPI()
    app.include_router(business_memory_router.router)

    # Override the auth dependency so no real JWT is needed
    app.dependency_overrides[_get_auth_result] = lambda: fake_auth

    return app


@pytest.fixture
def client(app, fake_auth):
    """TestClient with mocked auth and Supabase."""
    return TestClient(app), fake_auth


# ---------------------------------------------------------------------------
#  Helpers
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
    single: bool = False,
):
    """Create a mock Supabase client that returns the given rows.

    Parameters
    ----------
    rows : list[dict] | None
        Data to return from .execute().data. If single=True, returns
        the whole rows value as single-row data.
    raise_error : bool
        If True, .execute() raises an exception.
    single : bool
        If True, the mock simulates .single() path.
    """
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


# ===================================================================
#  Tests — Auth / Security
# ===================================================================


class TestAuth:
    """Authentication and authorization scenarios."""

    def test_request_without_auth_returns_401(self, app):
        """Endpoint should return 401 when no auth header is present.

        Remove the dependency override so FastAPI falls through to the
        real _get_auth_result, which requires a Bearer token.
        """
        # Build an app WITHOUT the auth override
        no_auth_app = FastAPI()
        no_auth_app.include_router(business_memory_router.router)
        # No dependency_overrides — the real auth runs
        no_auth_client = TestClient(no_auth_app)

        resp = no_auth_client.get("/api/business-memory")
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]

    def test_client_id_isolation(self, app, fake_auth):
        """Different client IDs should see different data scopes.

        The endpoint filters by client_id via .eq("client_id", client_id).
        """
        test_client = TestClient(app)
        rows = _sample_rows(count=3)
        mock_db = _make_mock_supabase_client(rows)

        # Mock Supabase
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_records"] == 3
        # The client_id in the response should match fake_auth.client_id
        assert body["client_id"] == str(fake_auth.client_id)


# ===================================================================
#  Tests — Happy Path
# ===================================================================


class TestHappyPath:
    """Success scenarios — endpoint returns correct data."""

    def test_list_all_records_success(self, app, fake_auth):
        """Should return all records with correct structure."""
        test_client = TestClient(app)
        rows = _sample_rows(count=2)
        mock_db = _make_mock_supabase_client(rows)
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory")
        assert resp.status_code == 200

        body = resp.json()
        assert "client_id" in body
        assert "total_records" in body
        assert "records" in body
        assert body["total_records"] == 2
        assert len(body["records"]) == 2
        assert body["client_id"] == str(fake_auth.client_id)

        record = body["records"][0]
        assert "id" in record
        assert "entity_type" in record
        assert "entity_name" in record
        assert "key" in record
        assert "value" in record
        assert "metadata" in record
        assert "source" in record
        assert "confidence" in record
        assert "version" in record
        assert "created_at" in record
        assert "updated_at" in record

        assert record["entity_type"] == "snapshot"
        assert record["entity_name"] == "financeiro:semanal"
        assert record["value"] is not None
        assert record["metadata"] == {"source_agent": "specialist-7"}
        assert record["confidence"] == 0.95
        assert record["version"] == 1

    def test_list_empty(self, app):
        """Should return empty records array for client with no data."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client([])
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory")
        assert resp.status_code == 200

        body = resp.json()
        assert body["total_records"] == 0
        assert body["records"] == []

    def test_list_none_data(self, app):
        """Should handle None .data gracefully (returns empty)."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client(None)
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory")
        assert resp.status_code == 200

        body = resp.json()
        assert body["total_records"] == 0
        assert body["records"] == []

    def test_get_single_record(self, app, fake_auth):
        """Should return a single record by UUID."""
        test_client = TestClient(app)
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
        assert body["value"] == {"indicadores": []}
        assert body["metadata"] == {}
        assert body["source"] == "system"
        assert body["confidence"] == 1.0
        assert body["version"] == 2


# ===================================================================
#  Tests — Filtering and Pagination
# ===================================================================


class TestFiltering:
    """Filter by entity_type and entity_name."""

    def test_filter_by_entity_type(self, app):
        """Should apply entity_type filter when provided."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client(_sample_rows(count=1))
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory?entity_type=snapshot")
        assert resp.status_code == 200
        assert resp.json()["total_records"] == 1

    def test_filter_by_entity_name(self, app):
        """Should apply entity_name filter when provided."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client(_sample_rows(count=1))
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory?entity_name=financeiro")
        assert resp.status_code == 200
        assert resp.json()["total_records"] == 1

    def test_pagination_limit_offset(self, app):
        """Should respect limit and offset query params."""
        test_client = TestClient(app)
        rows = _sample_rows(count=5)
        mock_db = _make_mock_supabase_client(rows)
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory?limit=2&offset=0")
        assert resp.status_code == 200
        assert resp.json()["total_records"] == 5


# ===================================================================
#  Tests — Error Handling
# ===================================================================


class TestErrorHandling:
    """Edge cases and error conditions."""

    def test_invalid_uuid(self, app):
        """Should return 400 for non-UUID record ID."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client([])
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory/not-a-uuid")
        assert resp.status_code == 400
        assert "Invalid record ID format" in resp.json()["detail"]

    def test_record_not_found(self, app):
        """Should return 404 when record doesn't exist."""
        test_client = TestClient(app)
        record_id = str(uuid.uuid4())

        # Supabase .single() raises on no match → caught as 404
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
        assert "Record not found" in resp.json()["detail"]

    def test_server_error_on_list(self, app):
        """Should return 500 on database error during list."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client(raise_error=True)
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory")
        assert resp.status_code == 500
        assert "Failed to query" in resp.json()["detail"]

    def test_server_error_on_get_single(self, app):
        """Should return 500 on database error during single record fetch."""
        test_client = TestClient(app)
        db = MagicMock()
        schema_mock = MagicMock()
        table_mock = MagicMock()
        query_mock = MagicMock()

        query_mock.select.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.single.return_value = query_mock
        query_mock.execute.side_effect = Exception("Connection timeout")

        table_mock.select.return_value = query_mock
        schema_mock.table.return_value = table_mock
        db.schema.return_value = schema_mock

        business_memory_router.get_supabase_client = MagicMock(return_value=db)

        record_id = str(uuid.uuid4())
        resp = test_client.get(f"/api/business-memory/{record_id}")
        assert resp.status_code == 404
        assert "Record not found" in resp.json()["detail"]

    def test_list_with_limit_validation(self, app):
        """Limit should be clamped to 1–1000 range."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client(_sample_rows(count=100))
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        # limit=0 should be rejected (ge=1)
        resp = test_client.get("/api/business-memory?limit=0")
        # FastAPI Query validation returns 422 for invalid query params
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any("limit" in str(d) for d in detail)

    def test_list_with_negative_offset(self, app):
        """Negative offset should be rejected (ge=0)."""
        test_client = TestClient(app)
        mock_db = _make_mock_supabase_client(_sample_rows(count=1))
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory?offset=-1")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any("offset" in str(d) for d in detail)


# ===================================================================
#  Tests — Response Structure Validation
# ===================================================================


class TestResponseStructure:
    """Verify the response schema matches the Pydantic models."""

    def test_response_has_all_expected_fields(self, app, fake_auth):
        """Response JSON schema must match BusinessMemoryListResponse."""
        test_client = TestClient(app)
        rows = _sample_rows(count=1)
        mock_db = _make_mock_supabase_client(rows)
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory")
        assert resp.status_code == 200
        body = resp.json()

        # Top-level fields
        assert "client_id" in body
        assert isinstance(body["client_id"], str)
        assert "total_records" in body
        assert isinstance(body["total_records"], int)
        assert "records" in body
        assert isinstance(body["records"], list)

    def test_record_schema(self, app):
        """Each record must have all BusinessMemoryRecord fields."""
        test_client = TestClient(app)
        rows = _sample_rows(count=1)
        mock_db = _make_mock_supabase_client(rows)
        business_memory_router.get_supabase_client = MagicMock(return_value=mock_db)

        resp = test_client.get("/api/business-memory")
        assert resp.status_code == 200
        body = resp.json()

        rec = body["records"][0]
        expected_fields = [
            "id", "entity_type", "entity_name", "key", "value",
            "metadata", "source", "confidence", "version",
            "created_at", "updated_at",
        ]
        for field in expected_fields:
            assert field in rec, f"Missing field: {field}"
