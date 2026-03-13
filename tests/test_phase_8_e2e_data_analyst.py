"""
Phase 8 E2E Test: Data Analyst Agent Flow
Tests the standalone agent configuration and execution flow for data analysis.
"""
import logging
from uuid import uuid4

import pytest

from vizu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers (not tests — build state for the real tests)
# ---------------------------------------------------------------------------

def _get_data_analyst_agent(db):
    """Return the Data Analyst row from agent_catalog."""
    result = db.table("agent_catalog").select(
        "id,name,slug,description,category,icon,tier_required,"
        "agent_config,prompt_name,required_context,required_files,requires_google"
    ).eq("is_active", True).execute()

    agent = next(
        (a for a in result.data if "data-analyst" in a.get("slug", "").lower()),
        None,
    )
    assert agent is not None, "Data Analyst agent not found in catalog"
    return agent


def _create_session(db, client_id: str, agent_id: str) -> dict:
    """Insert a configuring session and return the row."""
    result = db.table("standalone_agent_sessions").insert({
        "client_id": client_id,
        "agent_catalog_id": agent_id,
        "session_id": str(uuid4()),
        "config_status": "configuring",
        "collected_context": {},
        "uploaded_file_ids": [],
        "uploaded_document_ids": [],
    }).execute()
    return result.data[0]


def _upload_csv(db, client_id: str, session_id: str) -> dict:
    """Insert a CSV file metadata row linked to *session_id*."""
    csv_content = "produto,preco,quantidade,data\nA,100.00,10,2025-01-01\nB,200.00,5,2025-01-02\nC,150.00,8,2025-01-03"
    lines = csv_content.strip().split("\n")
    header = lines[0].split(",")
    columns_schema = [
        {"name": col, "type": "text" if col == "data" else "numeric",
         "sample": lines[1].split(",")[i]}
        for i, col in enumerate(header)
    ]
    file_id = str(uuid4())
    result = db.table("uploaded_files_metadata").insert({
        "id": file_id,
        "cliente_vizu_id": client_id,
        "file_name": "vendas.csv",
        "file_type": "text/csv",
        "storage_path": f"{client_id}/{file_id}-vendas.csv",
        "file_size_bytes": len(csv_content.encode()),
        "records_count": len(lines) - 1,
        "status": "completed",
        "session_id": session_id,
        "columns_schema": columns_schema,
    }).execute()
    return result.data[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_catalog_contains_data_analyst():
    """Data Analyst agent exists in catalog with expected fields."""
    db = get_supabase_client()
    agent = _get_data_analyst_agent(db)

    assert agent["name"]
    assert agent["description"]
    assert agent.get("prompt_name") == "standalone/data-analyst"

    agent_config = agent.get("agent_config", {})
    assert agent_config.get("name")
    assert agent_config.get("role")
    assert agent_config.get("enabled_tools")


@pytest.mark.asyncio
async def test_create_session(client_id: str):
    """A configuring session can be created for the Data Analyst agent."""
    db = get_supabase_client()
    agent = _get_data_analyst_agent(db)
    session = _create_session(db, client_id, agent["id"])

    assert session["config_status"] == "configuring"
    assert session["client_id"] == client_id


@pytest.mark.asyncio
async def test_upload_csv_linked_to_session(client_id: str):
    """Uploading a CSV creates metadata linked to the session."""
    db = get_supabase_client()
    agent = _get_data_analyst_agent(db)
    session = _create_session(db, client_id, agent["id"])
    file_meta = _upload_csv(db, client_id, session["id"])

    assert file_meta["session_id"] == session["id"]
    assert file_meta["records_count"] == 3
    assert file_meta["columns_schema"] is not None


@pytest.mark.asyncio
async def test_collect_context_and_activate(client_id: str):
    """Context is saved, then session transitions configuring -> ready -> active."""
    db = get_supabase_client()
    agent = _get_data_analyst_agent(db)
    session = _create_session(db, client_id, agent["id"])
    _upload_csv(db, client_id, session["id"])

    context = {"company_name": "Acme Corp", "industry": "Technology"}
    db.table("standalone_agent_sessions").update({
        "collected_context": context,
    }).eq("id", session["id"]).execute()

    db.table("standalone_agent_sessions").update({
        "config_status": "ready",
    }).eq("id", session["id"]).execute()

    result = db.table("standalone_agent_sessions").update({
        "config_status": "active",
    }).eq("id", session["id"]).execute()

    active = result.data[0]
    assert active["config_status"] == "active"
    assert active["collected_context"] == context


@pytest.mark.asyncio
async def test_session_persistence(client_id: str):
    """An active session can be listed and resumed."""
    db = get_supabase_client()
    agent = _get_data_analyst_agent(db)
    session = _create_session(db, client_id, agent["id"])

    db.table("standalone_agent_sessions").update({
        "config_status": "active",
        "collected_context": {"company_name": "Acme Corp"},
    }).eq("id", session["id"]).execute()

    result = db.table("standalone_agent_sessions").select(
        "id,config_status,collected_context"
    ).eq("client_id", client_id).execute()

    resumed = next((s for s in result.data if s["id"] == session["id"]), None)
    assert resumed is not None
    assert resumed["config_status"] == "active"
    assert resumed["collected_context"] is not None


@pytest.mark.asyncio
async def test_google_sheets_link(client_id: str):
    """A Google account email can be linked to a session."""
    db = get_supabase_client()
    agent = _get_data_analyst_agent(db)
    session = _create_session(db, client_id, agent["id"])

    result = db.table("standalone_agent_sessions").update({
        "google_account_email": "user@gmail.com",
    }).eq("id", session["id"]).execute()

    assert result.data[0]["google_account_email"] == "user@gmail.com"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_phase_8_e2e_data_analyst.py -v -s
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    pytest.main([__file__, "-v", "-s"])
