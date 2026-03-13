"""Service layer for standalone agent operations."""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage
from vizu_agent_framework.state import create_initial_state
from vizu_supabase_client import get_supabase_client
from vizu_parsers.csv_ingestion import ingest_csv

from standalone_agent_api.core.factory import get_factory

logger = logging.getLogger(__name__)


class CatalogService:
    """Service for agent catalog operations."""

    def __init__(self):
        """Initialize service."""
        self.db = get_supabase_client()

    async def list_agents(self, client_tier: str = "BASIC") -> list[dict]:
        """List active agents filtered by client tier."""
        result = self.db.table("agent_catalog").select(
            "id,name,slug,description,category,icon,tier_required"
        ).eq("is_active", True).execute()

        # Filter by tier (client can access their tier and below)
        tier_hierarchy = {"BASIC": 0, "PRO": 1, "ENTERPRISE": 2}
        client_tier_level = tier_hierarchy.get(client_tier, 0)

        agents = []
        for agent in result.data:
            agent_tier_level = tier_hierarchy.get(
                agent.get("tier_required", "BASIC"), 0
            )
            if agent_tier_level <= client_tier_level:
                agents.append(agent)

        return agents

    async def get_agent(self, agent_id: UUID) -> dict:
        """Get agent details with full config."""
        result = self.db.table("agent_catalog").select(
            "id,name,slug,description,category,icon,"
            "agent_config,prompt_name,required_context,required_files,"
            "requires_google,tier_required"
        ).eq("id", str(agent_id)).eq("is_active", True).execute()

        if not result.data:
            raise ValueError(f"Agent {agent_id} not found")

        return result.data[0]


class SessionService:
    """Service for session CRUD and status management."""

    def __init__(self):
        """Initialize service."""
        self.db = get_supabase_client()

    async def create_session(
        self,
        client_id: UUID,
        agent_catalog_id: UUID,
    ) -> dict:
        """Create new standalone agent session."""
        session_id = str(uuid4())

        result = self.db.table("standalone_agent_sessions").insert({
            "client_id": str(client_id),
            "agent_catalog_id": str(agent_catalog_id),
            "session_id": session_id,
            "config_status": "configuring",
            "collected_context": {},
            "uploaded_file_ids": [],
            "uploaded_document_ids": [],
        }).execute()

        return result.data[0]

    async def list_sessions(
        self,
        client_id: UUID,
        status: str | None = None,
    ) -> list[dict]:
        """List user sessions, optionally filtered by status."""
        query = self.db.table("standalone_agent_sessions").select(
            "id,agent_catalog_id,config_status,collected_context,"
            "uploaded_file_ids,created_at,updated_at"
        ).eq("client_id", str(client_id))

        if status:
            query = query.eq("config_status", status)

        result = query.order("created_at", desc=True).execute()
        return result.data or []

    async def get_session(
        self,
        client_id: UUID,
        session_id: str,
    ) -> dict:
        """Get session with full details including computed requirements."""
        result = self.db.table("standalone_agent_sessions").select(
            "id,client_id,agent_catalog_id,session_id,config_status,collected_context,"
            "uploaded_file_ids,uploaded_document_ids,"
            "google_account_email,metadata,created_at,updated_at"
        ).eq("client_id", str(client_id)).eq("id", session_id).execute()

        if not result.data:
            raise ValueError(f"Session {session_id} not found")

        session = result.data[0]

        # Compute requirements from agent catalog
        requirements = await self._compute_requirements(session)
        session["requirements"] = requirements

        return session

    async def _compute_requirements(self, session: dict) -> dict:
        """Compute requirements status from agent catalog vs session state."""
        agent_catalog_id = session.get("agent_catalog_id")
        catalog_result = self.db.table("agent_catalog").select(
            "required_context,required_files,requires_google"
        ).eq("id", str(agent_catalog_id)).execute()

        required_context = []
        required_files = {}
        requires_google = False

        if catalog_result.data:
            catalog = catalog_result.data[0]
            required_context = catalog.get("required_context") or []
            required_files = catalog.get("required_files") or {}
            requires_google = catalog.get("requires_google", False)

        collected = session.get("collected_context") or {}
        total_fields = len(required_context)
        filled_fields = 0
        missing = []

        for field in required_context:
            field_key = field.get("field") or field.get("field_name") or field.get("name", "")
            if collected.get(field_key):
                filled_fields += 1
            else:
                missing.append({
                    "field_name": field_key,
                    "label": field.get("label", field_key),
                    "type": field.get("type", "text"),
                })

        csv_req = required_files.get("csv", {})
        text_req = required_files.get("text", {})
        csv_current = len(session.get("uploaded_file_ids") or [])
        text_current = len(session.get("uploaded_document_ids") or [])

        google_connected = bool(session.get("google_account_email"))

        # Compute completion percentage
        total_checks = total_fields
        filled_checks = filled_fields
        if csv_req.get("min", 0) > 0:
            total_checks += 1
            if csv_current >= csv_req["min"]:
                filled_checks += 1
        if text_req.get("min", 0) > 0:
            total_checks += 1
            if text_current >= text_req["min"]:
                filled_checks += 1
        if requires_google:
            total_checks += 1
            if google_connected:
                filled_checks += 1

        completion_pct = (filled_checks / total_checks * 100) if total_checks > 0 else 100

        return {
            "total_fields": total_fields,
            "filled_fields": filled_fields,
            "missing": missing,
            "files_required": {
                "csv": {
                    "min": csv_req.get("min", 0),
                    "max": csv_req.get("max", 10),
                    "current": csv_current,
                },
                "text": {
                    "min": text_req.get("min", 0),
                    "max": text_req.get("max", 10),
                    "current": text_current,
                },
            },
            "google_required": requires_google,
            "google_connected": google_connected,
            "completion_pct": round(completion_pct, 1),
        }

    async def update_collected_context(
        self,
        client_id: UUID,
        session_id: str,
        context_update: dict,
    ) -> dict:
        """Merge context into collected_context."""
        session = await self.get_session(client_id, session_id)

        updated_context = session.get("collected_context") or {}
        updated_context.update(context_update)

        self.db.table("standalone_agent_sessions").update({
            "collected_context": updated_context,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", session_id).execute()

        return updated_context

    async def finalize_session(
        self,
        client_id: UUID,
        session_id: str,
    ) -> dict:
        """Finalize config — transition session to 'ready'."""
        session = await self.get_session(client_id, session_id)

        self.db.table("standalone_agent_sessions").update({
            "config_status": "ready",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", session_id).eq("client_id", str(client_id)).execute()

        session["config_status"] = "ready"
        return session

    async def activate_session(
        self,
        client_id: UUID,
        session_id: str,
    ) -> dict:
        """Transition session from 'ready' to 'active'."""
        session = await self.get_session(client_id, session_id)

        self.db.table("standalone_agent_sessions").update({
            "config_status": "active",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", session_id).eq("client_id", str(client_id)).execute()

        session["config_status"] = "active"
        return session

    async def link_google_account(
        self,
        client_id: UUID,
        session_id: str,
        email: str,
    ) -> dict:
        """Link Google account to session."""
        self.db.table("standalone_agent_sessions").update({
            "google_account_email": email,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", session_id).eq("client_id", str(client_id)).execute()

        return {"session_id": session_id, "google_account_email": email}

    async def link_document_to_session(
        self,
        client_id: UUID,
        session_id: str,
        document_id: str,
    ) -> dict:
        """Link a document (uploaded via knowledge base) to session's uploaded_document_ids."""
        session_result = self.db.table(
            "standalone_agent_sessions"
        ).select("uploaded_document_ids").eq(
            "id", session_id
        ).eq("client_id", str(client_id)).execute()

        if not session_result.data:
            raise ValueError(f"Session {session_id} not found")

        doc_ids = session_result.data[0].get("uploaded_document_ids") or []
        if document_id not in doc_ids:
            doc_ids.append(document_id)

        self.db.table("standalone_agent_sessions").update({
            "uploaded_document_ids": doc_ids,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", session_id).eq("client_id", str(client_id)).execute()

        return {"session_id": session_id, "document_id": document_id, "uploaded_document_ids": doc_ids}


class CsvUploadService:
    """Service for CSV upload and ingestion."""

    def __init__(self):
        """Initialize service."""
        self.db = get_supabase_client()

    async def upload_csv(
        self,
        session_id: str,
        client_id: UUID,
        file_stream,
        file_name: str,
    ) -> dict:
        """Upload CSV file and register in database."""
        try:
            # Get Supabase Storage instance
            from vizu_supabase_client import get_storage

            supabase_storage = get_storage(bucket="file-uploads")

            # Ingest CSV using existing parser
            metadata = await ingest_csv(
                file_stream=file_stream,
                client_id=client_id,
                session_id=session_id,
                file_name=file_name,
                supabase_storage=supabase_storage,
            )

            # Add to session's uploaded_file_ids
            session_result = self.db.table(
                "standalone_agent_sessions"
            ).select("uploaded_file_ids").eq("id", session_id).execute()

            if not session_result.data:
                raise ValueError(f"Session {session_id} not found")

            file_ids = session_result.data[0].get("uploaded_file_ids") or []
            file_ids.append(str(metadata["file_id"]))

            self.db.table("standalone_agent_sessions").update({
                "uploaded_file_ids": file_ids,
            }).eq("id", session_id).execute()

            return metadata

        except Exception as e:
            logger.error(f"CSV upload failed: {e}")
            raise

    async def list_session_csvs(self, session_id: str) -> list[dict]:
        """List CSVs for a session."""
        session_result = self.db.table(
            "standalone_agent_sessions"
        ).select("uploaded_file_ids").eq("id", session_id).execute()

        if not session_result.data:
            return []

        file_ids = session_result.data[0].get("uploaded_file_ids") or []

        if not file_ids:
            return []

        result = self.db.table("uploaded_files_metadata").select(
            "id,file_name,columns_schema,records_count"
        ).in_("id", file_ids).execute()

        return result.data or []


class StandaloneAgentService:
    """High-level service for agent chat operations."""

    def __init__(self):
        """Initialize service."""
        self.factory = get_factory()

    async def invoke_agent(
        self,
        session_id: str,
        client_id: UUID,
        agent_catalog_id: UUID,
        user_message: str,
        thread_id: str | None = None,
    ) -> dict:
        """
        Invoke an agent with a user message and stream responses.

        Args:
            session_id: LangGraph session/thread ID
            client_id: User/client ID
            agent_catalog_id: Which agent from catalog
            user_message: User's question/request
            thread_id: Optional LangGraph thread (uses session_id if not provided)

        Returns:
            dict with response, tool_calls, etc
        """
        thread_id = thread_id or session_id

        # Build agent (cached if already built) — returns BuiltAgent with context
        built = await self.factory.build_agent(
            session_id=thread_id,
            client_id=client_id,
            agent_catalog_id=agent_catalog_id,
        )

        # Create initial state using context from factory
        initial_state = create_initial_state(
            session_id=thread_id,
            cliente_id=str(client_id),
            channel="standalone",
            system_prompt=built.system_prompt,
            agent_name=built.agent_name,
            agent_role=built.agent_role,
            enabled_tools=built.enabled_tools,
            client_context=built.client_context,
        )

        # Add user message
        initial_state["messages"].append(HumanMessage(content=user_message))

        # Invoke agent with thread-based recovery
        result = await built.graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )

        # Extract final response
        ai_messages = [
            msg for msg in result.get("messages", [])
            if isinstance(msg, AIMessage)
        ]

        return {
            "session_id": session_id,
            "thread_id": thread_id,
            "messages": result.get("messages", []),
            "tool_results": result.get("tool_results", []),
            "ended": result.get("ended", False),
            "turn_count": result.get("turn_count", 0),
            "last_response": ai_messages[-1].content if ai_messages else None,
        }

    async def stream_agent_response(
        self,
        session_id: str,
        client_id: UUID,
        agent_catalog_id: UUID,
        user_message: str,
        thread_id: str | None = None,
    ):
        """
        Stream agent response using SSE.

        Yields events as agent runs: tool_calls, responses, etc.
        """
        thread_id = thread_id or session_id

        # Build agent — returns BuiltAgent with context
        built = await self.factory.build_agent(
            session_id=thread_id,
            client_id=client_id,
            agent_catalog_id=agent_catalog_id,
        )

        # Create initial state using context from factory
        initial_state = create_initial_state(
            session_id=thread_id,
            cliente_id=str(client_id),
            channel="standalone",
            system_prompt=built.system_prompt,
            agent_name=built.agent_name,
            agent_role=built.agent_role,
            enabled_tools=built.enabled_tools,
            client_context=built.client_context,
        )

        # Add user message
        initial_state["messages"].append(HumanMessage(content=user_message))

        # Stream events from agent
        async for event in built.graph.astream(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        ):
            yield event


def get_catalog_service() -> CatalogService:
    """Get catalog service singleton."""
    return CatalogService()


def get_session_service() -> SessionService:
    """Get session service singleton."""
    return SessionService()


def get_csv_upload_service() -> CsvUploadService:
    """Get CSV upload service singleton."""
    return CsvUploadService()


def get_agent_service() -> StandaloneAgentService:
    """Get agent service singleton."""
    return StandaloneAgentService()
