"""
Phase 8 E2E Test: Knowledge Assistant Agent Flow
Tests the RAG-powered knowledge assistant configuration and execution.
"""
import logging
from uuid import uuid4

import pytest

from vizu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_knowledge_assistant(db):
    result = db.table("agent_catalog").select("*").eq("is_active", True).execute()
    agent = next(
        (a for a in result.data if "knowledge-assistant" in a.get("slug", "").lower()),
        None,
    )
    assert agent is not None, "Knowledge Assistant not in catalog"
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


def _upload_document(db, client_id: str, session_id: str) -> tuple[dict, dict]:
    """Upload a document and link it to the session. Returns (doc, session)."""
    doc_id = str(uuid4())
    doc_result = db.schema("vector_db").table("documents").insert({
        "id": doc_id,
        "client_id": client_id,
        "file_name": "company_knowledge.md",
        "file_type": "text/markdown",
        "storage_path": f"{client_id}/{doc_id}-knowledge.md",
        "status": "pending",
    }).execute()

    session_result = db.table("standalone_agent_sessions").update({
        "uploaded_document_ids": [doc_id],
    }).eq("id", session_id).execute()

    return doc_result.data[0], session_result.data[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_catalog_contains_knowledge_assistant():
    """Knowledge Assistant exists in catalog with correct config."""
    db = get_supabase_client()
    ka = _get_knowledge_assistant(db)

    assert ka["prompt_name"] == "standalone/knowledge-assistant"
    assert ka["requires_google"] is False


@pytest.mark.asyncio
async def test_create_session(client_id: str):
    """A session can be created for the Knowledge Assistant."""
    db = get_supabase_client()
    agent = _get_knowledge_assistant(db)
    session = _create_session(db, client_id, agent["id"])

    assert session["config_status"] == "configuring"
    assert session["client_id"] == client_id


@pytest.mark.asyncio
async def test_upload_and_link_document(client_id: str):
    """A document is created in vector_db and linked to the session."""
    db = get_supabase_client()
    agent = _get_knowledge_assistant(db)
    session = _create_session(db, client_id, agent["id"])
    doc, updated_session = _upload_document(db, client_id, session["id"])

    assert doc["file_name"] == "company_knowledge.md"
    assert doc["id"] in updated_session["uploaded_document_ids"]


@pytest.mark.asyncio
async def test_collect_context_for_rag(client_id: str):
    """Context is saved to the session for RAG queries."""
    db = get_supabase_client()
    agent = _get_knowledge_assistant(db)
    session = _create_session(db, client_id, agent["id"])
    _upload_document(db, client_id, session["id"])

    context = {"company_name": "TechCorp", "query_focus": "Product features and support"}
    result = db.table("standalone_agent_sessions").update({
        "collected_context": context,
    }).eq("id", session["id"]).execute()

    assert result.data[0]["collected_context"] == context


@pytest.mark.asyncio
async def test_activate_knowledge_assistant(client_id: str):
    """Session transitions to active after context is collected."""
    db = get_supabase_client()
    agent = _get_knowledge_assistant(db)
    session = _create_session(db, client_id, agent["id"])
    _upload_document(db, client_id, session["id"])

    db.table("standalone_agent_sessions").update({
        "collected_context": {"company_name": "TechCorp"},
    }).eq("id", session["id"]).execute()

    result = db.table("standalone_agent_sessions").update({
        "config_status": "active",
    }).eq("id", session["id"]).execute()

    assert result.data[0]["config_status"] == "active"

    logger.info("\n" + "=" * 80)
    logger.info("✅ FULL KNOWLEDGE ASSISTANT E2E TEST FLOW COMPLETE")
    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    pytest.main([__file__, "-v", "-s"])
