"""Root conftest for Phase 8 integration tests.

Loads .env so Supabase credentials are available.
Provides shared fixtures and automatic teardown of test data.
"""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env from repo root (parent of tests/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=False)

_DEFAULT_CLIENT_ID = "e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"


@pytest.fixture
def client_id() -> str:
    """Client ID for E2E tests.  Override via TEST_CLIENT_ID env var."""
    return os.getenv("TEST_CLIENT_ID", _DEFAULT_CLIENT_ID)


@pytest.fixture(autouse=True)
def _cleanup_test_data(client_id: str):
    """Delete rows created during each test so the DB stays clean."""
    from vizu_supabase_client import get_supabase_client

    yield  # run the test

    db = get_supabase_client()

    # uploaded_files_metadata has FK session_id → standalone_agent_sessions,
    # but ON DELETE SET NULL, so order doesn't strictly matter.  Delete files
    # first anyway to avoid transient FK issues.
    db.table("uploaded_files_metadata").delete().eq(
        "cliente_vizu_id", client_id
    ).execute()

    db.table("standalone_agent_sessions").delete().eq(
        "client_id", client_id
    ).execute()

    db.schema("vector_db").table("documents").delete().eq(
        "client_id", client_id
    ).in_(
        "file_name",
        ["company_knowledge.md", "2024_business_strategy.md", "vendas.csv"],
    ).execute()
