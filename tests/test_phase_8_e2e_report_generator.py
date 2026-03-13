"""
Phase 8 E2E Test: Report Generator Agent Flow
Tests combining CSV analysis with RAG knowledge into structured reports.
"""
import logging
from uuid import uuid4

import pytest

from vizu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_report_generator(db):
    result = db.table("agent_catalog").select("*").eq("is_active", True).execute()
    agent = next(
        (a for a in result.data if "report-generator" in a.get("slug", "").lower()),
        None,
    )
    assert agent is not None, "Report Generator not in catalog"
    return agent


def _create_session(db, client_id: str, agent_id: str) -> dict:
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


def _upload_csvs_and_doc(db, client_id: str, session_id: str) -> dict:
    """Upload two CSVs + one document and link all to the session."""
    csv1_id = str(uuid4())
    db.table("uploaded_files_metadata").insert({
        "id": csv1_id,
        "cliente_vizu_id": client_id,
        "file_name": "vendas_2024.csv",
        "file_type": "text/csv",
        "storage_path": f"{client_id}/{csv1_id}-vendas.csv",
        "file_size_bytes": 5000,
        "records_count": 100,
        "status": "completed",
        "session_id": session_id,
        "columns_schema": [
            {"name": "data", "type": "date"},
            {"name": "regiao", "type": "text"},
            {"name": "vendas", "type": "numeric"},
        ],
    }).execute()

    csv2_id = str(uuid4())
    db.table("uploaded_files_metadata").insert({
        "id": csv2_id,
        "cliente_vizu_id": client_id,
        "file_name": "metas_2024.csv",
        "file_type": "text/csv",
        "storage_path": f"{client_id}/{csv2_id}-metas.csv",
        "file_size_bytes": 3000,
        "records_count": 50,
        "status": "completed",
        "session_id": session_id,
        "columns_schema": [
            {"name": "regiao", "type": "text"},
            {"name": "meta_vendas", "type": "numeric"},
        ],
    }).execute()

    doc_id = str(uuid4())
    db.schema("vector_db").table("documents").insert({
        "id": doc_id,
        "client_id": client_id,
        "file_name": "2024_business_strategy.md",
        "status": "pending",
    }).execute()

    result = db.table("standalone_agent_sessions").update({
        "uploaded_file_ids": [csv1_id, csv2_id],
        "uploaded_document_ids": [doc_id],
    }).eq("id", session_id).execute()
    return result.data[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_catalog_contains_report_generator():
    """Report Generator exists in catalog with CSV + RAG + Sheets tools."""
    db = get_supabase_client()
    rg = _get_report_generator(db)

    assert rg["prompt_name"] == "standalone/report-generator"
    assert rg["requires_google"] is True

    tools = rg["agent_config"].get("enabled_tools", [])
    assert "execute_csv_query" in tools
    assert "executar_rag_cliente" in tools
    assert "write_to_sheet" in tools


@pytest.mark.asyncio
async def test_create_session(client_id: str):
    """A session can be created for the Report Generator."""
    db = get_supabase_client()
    agent = _get_report_generator(db)
    session = _create_session(db, client_id, agent["id"])

    assert session["config_status"] == "configuring"
    assert session["client_id"] == client_id


@pytest.mark.asyncio
async def test_upload_csvs_and_document(client_id: str):
    """Two CSVs and one document can be uploaded and linked to a session."""
    db = get_supabase_client()
    agent = _get_report_generator(db)
    session = _create_session(db, client_id, agent["id"])
    updated = _upload_csvs_and_doc(db, client_id, session["id"])

    assert len(updated["uploaded_file_ids"]) == 2
    assert len(updated["uploaded_document_ids"]) == 1


@pytest.mark.asyncio
async def test_link_google_sheets(client_id: str):
    """A Google account email can be linked to the session."""
    db = get_supabase_client()
    agent = _get_report_generator(db)
    session = _create_session(db, client_id, agent["id"])
    _upload_csvs_and_doc(db, client_id, session["id"])

    result = db.table("standalone_agent_sessions").update({
        "google_account_email": "user@gmail.com",
    }).eq("id", session["id"]).execute()

    assert result.data[0]["google_account_email"] == "user@gmail.com"


@pytest.mark.asyncio
async def test_collect_context_and_activate(client_id: str):
    """Context is collected and session activated for report generation."""
    db = get_supabase_client()
    agent = _get_report_generator(db)
    session = _create_session(db, client_id, agent["id"])
    _upload_csvs_and_doc(db, client_id, session["id"])

    context = {
        "company_name": "Acme Sales Corp",
        "report_audience": "Director, Finance",
        "key_metrics": "Regional sales vs targets, growth trends",
        "frequency": "Monthly",
    }

    db.table("standalone_agent_sessions").update({
        "collected_context": context,
        "google_account_email": "user@gmail.com",
    }).eq("id", session["id"]).execute()

    result = db.table("standalone_agent_sessions").update({
        "config_status": "active",
    }).eq("id", session["id"]).execute()

    active = result.data[0]
    assert active["config_status"] == "active"
    assert active["collected_context"] == context
    assert active["google_account_email"] == "user@gmail.com"
