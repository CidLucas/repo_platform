# Vizu Mono — AI Coding Agent Instructions

**Monorepo for AI platform** built with Python 3.11+, FastAPI, LangGraph, and Poetry.


## Shared Libraries — CRITICAL (Never Duplicate Code)

| Library | Purpose | Key Pattern |
|---------|---------|-------------|
| `vizu_models` | ALL database models + API schemas (SQLModel/Pydantic) | `from vizu_models import ClienteVizu, Conversa` |
| `vizu_llm_service` | ALL LLM calls — provider-agnostic | `get_model(tier="FAST\|DEFAULT\|POWERFUL")` |
| `vizu_agent_framework` | Build new agents with 95% code reuse | `AgentBuilder(AgentConfig(...)).build()` |
| `vizu_db_connector` | Database sessions + Alembic migrations | `Depends(get_db_session)` |
| `vizu_supabase_client` | Supabase REST API (singleton) | `get_supabase_client().table("x").select("*")` |
| `vizu_tool_registry` | Tool discovery + tier access (BASIC/SME/ENTERPRISE) | `ToolRegistry.get_available_tools(tier="SME")` |
| `vizu_auth` | JWT + API-Key auth | `Depends(verify_api_key)` |
| `vizu_rag_factory` | RAG chain construction | Semantic search over Qdrant |
| `vizu_sql_factory` | Text-to-SQL agent | Natural language → SQL queries |
| `vizu_context_service` | Client context retrieval + Redis caching | `get_client_context_by_id(uuid)` |
| `vizu_elicitation_service` | Human-in-the-loop interactive prompts | `raise ElicitationRequired(...)` |
| `vizu_hitl_service` | Quality control queue for human review | Low confidence → HITL queue |
| `vizu_observability_bootstrap` | OpenTelemetry + Langfuse setup | `setup_observability(app)` |


Always perform lint tests and fixes when you finish a implementation.

Always remember you have supabase tools to run migrations, consult the names of columns and tables, etc... Use them often to avoid mistakes and save time.

The vizu_dashboard is the frontend. Clients connects to front and provide info so we can access databases throgh FDW, and ingest the data to Supabase. Then through vizu_dashboard the client can see it's data and see some insights.

The front end is connected to an agent that has access to client's data and some mcp tools in tool_pool_api.