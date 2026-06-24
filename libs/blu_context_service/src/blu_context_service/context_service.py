
from __future__ import annotations
import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from blu_prompt_management import PromptLoader

from cryptography.fernet import Fernet

from blu_models.blu_client_context import BluClientContext
from blu_supabase_client import SupabaseCRUD, get_supabase_client
from blu_supabase_client.client import set_rls_context as supabase_set_rls

from .redis_service import RedisService

logger = logging.getLogger(__name__)


_ALL_CONTEXT_SECTIONS: frozenset[str] = frozenset({
    "company_profile", "brand_voice", "team_structure",
    "policies", "data_schema", "available_tools",
})

# Maps domain keyword → the sections relevant to that domain.
# Unlisted domains fall back to all loaded sections.
_DOMAIN_SECTIONS: dict[str, frozenset[str]] = {
    "analytics":     frozenset({"data_schema", "available_tools", "company_profile"}),
    "data":          frozenset({"data_schema", "available_tools", "company_profile"}),
    "sql":           frozenset({"data_schema", "available_tools", "company_profile"}),
    "rfq":           frozenset({"brand_voice", "policies", "team_structure", "company_profile"}),
    "communication": frozenset({"brand_voice", "policies", "team_structure", "company_profile"}),
    "sales":         frozenset({"brand_voice", "policies", "team_structure", "company_profile"}),
    "customer":      frozenset({"brand_voice", "policies", "team_structure", "company_profile"}),
    "knowledge":     frozenset({"company_profile", "policies", "brand_voice"}),
    "rag":           frozenset({"company_profile", "policies", "brand_voice"}),
    "documents":     frozenset({"company_profile", "policies", "brand_voice"}),
    "config":        frozenset({"available_tools", "team_structure", "company_profile"}),
    "settings":      frozenset({"available_tools", "team_structure", "company_profile"}),
}

# Domains that consume RAG and should receive knowledge_graph_summary
_RAG_DOMAINS: frozenset[str] = frozenset({
    "documentos", "crm", "financeiro", "compras", "strategy",
})

# Domains that explicitly do NOT use RAG
_NON_RAG_DOMAINS: frozenset[str] = frozenset({
    "agenda",  # uses Google Calendar, not RAG
})

_GOOGLE_OAUTH_CONFIG_CACHE: dict[str, str] | None = None
_GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT: datetime | None = None
_GOOGLE_OAUTH_CONFIG_CACHE_TTL_SECONDS = 600
_GOOGLE_OAUTH_CONFIG_CACHE_LOCK = Lock()


class ContextService:
    """Service for fetching and caching client context via Supabase SDK."""

    CACHE_KEY_PREFIX = "context:client:"
    CACHE_TTL_SECONDS = 300        # 5 minutes — client context
    CANONICAL_TTL_SECONDS = 3600   # 1 hour — changes only on schema migrations

    def __init__(self, cache_service: RedisService) -> None:
        """
        Initialize ContextService.

        Args:
            cache_service: Redis service for caching
        """
        self.cache = cache_service
        self._supabase_crud = SupabaseCRUD()
        logger.info("ContextService initialized with Supabase SDK backend")

        fernet_key = os.getenv("CREDENTIALS_ENCRYPTION_KEY")
        if fernet_key:
            try:
                self._cipher = Fernet(
                    fernet_key.encode() if isinstance(fernet_key, str) else fernet_key
                )
            except Exception as e:
                logger.error("Invalid CREDENTIALS_ENCRYPTION_KEY: %s", e)
                self._cipher = None
        else:
            self._cipher = None

    def _get_cache_key(self, client_id: UUID) -> str:
        return f"{self.CACHE_KEY_PREFIX}{client_id}"

    def _set_rls_context(self, client_id: UUID) -> None:
        try:
            client = get_supabase_client()
            supabase_set_rls(client, str(client_id))
            logger.debug(f"RLS context set via Supabase RPC for: {client_id}")
        except Exception as e:
            logger.warning(f"Could not set RLS context via Supabase: {e}")

    def _build_context_from_dict(self, data: dict[str, Any]) -> BluClientContext:
        """Build BluClientContext from Supabase response dict."""
        return BluClientContext(
            id=UUID(data["client_id"]) if isinstance(data["client_id"], str) else data["client_id"],
            nome_empresa=data["nome_empresa"],
            cpf_cnpj=data.get("cpf_cnpj"),
            tipo_cliente=data["tipo_cliente"],
            tier=data["tier"],
            company_profile=data.get("company_profile"),
            brand_voice=data.get("brand_voice"),
            team_structure=data.get("team_structure"),
            policies=data.get("policies"),
            data_schema=data.get("data_schema"),
            available_tools=data.get("available_tools"),
            credenciais=[],
        )

    async def _enrich_data_schema_with_table_schemas(
        self, context: BluClientContext, client_id: UUID
    ) -> BluClientContext:
        """Enrich BluClientContext.data_schema with detailed table schemas from sql_table_config."""
        try:
            configs = await self.get_sql_table_configs(client_id)

            if not configs:
                logger.debug(f"No sql_table_config entries for {client_id}")
                return context

            from blu_models.context_schemas import DataSchema, TableSchemaInfo

            table_schemas = []
            for config in configs:
                schema_info = TableSchemaInfo(
                    table_name=config.get("table_name", ""),
                    display_name=config.get("display_name"),
                    description=config.get("description"),
                    is_primary=config.get("is_primary", False),
                    columns=config.get("column_descriptions") or {},
                    enum_values=config.get("enum_values") or {},
                    example_queries=config.get("example_queries") or [],
                    join_keys=config.get("join_keys") or [],
                )
                table_schemas.append(schema_info)

            if context.data_schema and isinstance(context.data_schema, dict):
                existing_data = context.data_schema.copy()
                existing_data["table_schemas"] = table_schemas
                context.data_schema = DataSchema.model_validate(existing_data)
            elif context.data_schema and hasattr(context.data_schema, "model_copy"):
                context.data_schema = context.data_schema.model_copy(
                    update={"table_schemas": table_schemas}
                )
            else:
                context.data_schema = DataSchema(
                    table_schemas=table_schemas,
                    available_tables=[ts.table_name for ts in table_schemas],
                )

            logger.info(
                f"Enriched data_schema with {len(table_schemas)} table schemas for {client_id}"
            )
            return context

        except Exception as e:
            logger.warning(f"Failed to enrich data_schema with table_schemas: {e}")
            return context

    async def get_client_context(
        self,
        client_id: UUID | None = None,
        *,
        external_user_id: str | UUID | None = None,
    ) -> BluClientContext | None:
        """
        Fetch full client context with Redis caching.

        Accepts either a direct ``client_id`` (UUID) or an ``external_user_id``
        (JWT sub / Supabase Auth user ID).  When ``external_user_id`` is given,
        the internal client UUID is resolved first (one Supabase call, not
        cached), then the standard Redis → Supabase → enrich path is used.

        Exactly one of the two arguments must be provided.
        """
        if client_id is None and external_user_id is None:
            raise ValueError("Provide either client_id or external_user_id")

        # --- resolve external_user_id → client_id ---
        if client_id is None:
            try:
                cliente_data = await asyncio.to_thread(
                    self._supabase_crud.get_cliente_blu_by_external_user_id,
                    str(external_user_id),
                )
            except Exception as e:
                logger.error(
                    f"Erro ao resolver external_user_id={external_user_id}: {e}",
                    exc_info=True,
                )
                return None

            if not cliente_data:
                logger.warning(
                    f"Cliente não encontrado para external_user_id={external_user_id}"
                )
                return None

            client_id = UUID(cliente_data["client_id"])
            logger.debug(
                f"Resolved external_user_id={external_user_id} → client_id={client_id}"
            )

        # --- cached fetch by client_id ---
        cache_key = self._get_cache_key(client_id)
        await asyncio.to_thread(self._set_rls_context, client_id)

        try:
            cached_data = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached_data:
                try:
                    return BluClientContext.model_validate(cached_data)
                except Exception as e:
                    logger.warning(
                        f"Cache corrompido para {client_id}, invalidando... Erro: {e}"
                    )
                    await self.clear_context_cache(client_id)
        except Exception as e:
            logger.warning(f"Falha ao ler cache Redis: {e}")

        try:
            cliente_data = await asyncio.to_thread(
                self._supabase_crud.get_cliente_blu_by_id, client_id
            )
            if not cliente_data:
                logger.warning(f"Cliente {client_id} não encontrado no banco.")
                return None

            client_context = self._build_context_from_dict(cliente_data)
            client_context = await self._enrich_data_schema_with_table_schemas(
                client_context, client_id
            )

            await asyncio.to_thread(
                self.cache.set_json,
                key=cache_key,
                data=client_context,
                ttl_seconds=self.CACHE_TTL_SECONDS,
            )

            return client_context

        except Exception as e:
            logger.error(
                f"Erro crítico ao montar contexto para {client_id}: {e}", exc_info=True
            )
            return None

    # ------------------------------------------------------------------
    # Backwards-compat aliases — prefer get_client_context() in new code
    # ------------------------------------------------------------------

    async def get_client_context_by_id(self, client_id: UUID) -> BluClientContext | None:
        return await self.get_client_context(client_id)

    async def get_client_context_by_external_user_id(
        self, external_user_id: str | UUID
    ) -> BluClientContext | None:
        return await self.get_client_context(external_user_id=external_user_id)

    async def clear_context_cache(self, client_id: UUID) -> None:
        """Remove context from cache (call after client updates)."""
        cache_key = self._get_cache_key(client_id)
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"Cache invalidado para: {client_id}")

    async def get_domain_projection(self, domain: str, client_id: UUID) -> dict[str, Any]:
        """
        Return a filtered view of the cached BluClientContext for a given domain.

        The projection includes only the context sections relevant to the
        requested domain, plus the identity fields (nome_empresa, tier, id).
        Uses the cached context from get_client_context_by_id — no extra DB call.

        For RAG-consuming domains (documentos, crm, financeiro, compras,
        strategy), the projection also includes knowledge_graph_summary when
        available in Redis (key ``ctx:{client_id}:knowledge_graph_summary``).
        The field is omitted when the cache is empty or Redis is unreachable —
        zero breaking change for existing flows.

        Args:
            domain: Specialist domain keyword (e.g. "analytics", "rfq", "rag").
                    Unknown domains include all loaded sections.
            client_id: Client UUID.

        Returns:
            Dict suitable for injection into AgentState.client_context at the
            specialist level. Empty dict if the context cannot be loaded.
        """
        ctx = await self.get_client_context(client_id)
        if ctx is None:
            logger.warning("[domain_projection] No context found for client_id=%s", client_id)
            return {}

        allowed_sections = _DOMAIN_SECTIONS.get(domain.lower(), _ALL_CONTEXT_SECTIONS)

        projection: dict[str, Any] = {
            "id": str(ctx.id),
            "nome_empresa": ctx.nome_empresa,
            "tier": ctx.tier,
        }
        for section in allowed_sections:
            value = ctx.get_section(section)
            if value:
                projection[section] = value

        # --- Knowledge Graph Summary injection (for RAG domains) ---
        domain_lower = domain.lower()
        if domain_lower in _RAG_DOMAINS:
            kg_cache_key = f"ctx:{client_id}:knowledge_graph_summary"
            try:
                kg_summary = await asyncio.to_thread(
                    self.cache.get_json, kg_cache_key
                )
                if kg_summary is not None:
                    projection["knowledge_graph_summary"] = kg_summary
                    logger.debug(
                        "[domain_projection] Injected KG summary for domain=%s client=%s",
                        domain, client_id,
                    )
            except Exception as e:
                logger.warning(
                    "[domain_projection] Failed to fetch KG summary from Redis "
                    "for client=%s: %s",
                    client_id, e,
                )

        logger.debug(
            "[domain_projection] domain=%s client=%s sections=%s",
            domain, client_id, sorted(projection.keys()),
        )
        return projection

    async def get_knowledge_graph_summary(
        self, client_id: UUID
    ) -> "KnowledgeGraphSummary | None":
        """Return the knowledge graph summary for a client, if available.

        Extracts ``available_tools.knowledge_graph_summary`` from the cached
        client context (no extra DB call).  Returns a typed
        ``KnowledgeGraphSummary`` or ``None`` when the section is absent.

        Args:
            client_id: Client UUID.

        Returns:
            ``KnowledgeGraphSummary`` with aggregated graph metrics, or ``None``
            if the context is unavailable or the section is not populated.
        """
        from blu_models.context_schemas import KnowledgeGraphSummary

        ctx = await self.get_client_context(client_id)
        if ctx is None:
            logger.debug(
                "[kg_summary] No context found for client_id=%s", client_id
            )
            return None

        available_tools = ctx.available_tools
        if not available_tools:
            logger.debug(
                "[kg_summary] available_tools is None/empty for client_id=%s",
                client_id,
            )
            return None

        summary_data = available_tools.get("knowledge_graph_summary")
        if not summary_data:
            logger.debug(
                "[kg_summary] knowledge_graph_summary not present for client_id=%s",
                client_id,
            )
            return None

        try:
            return KnowledgeGraphSummary.model_validate(summary_data)
        except Exception as e:
            logger.warning(
                "[kg_summary] Failed to parse knowledge_graph_summary for "
                "client_id=%s: %s",
                client_id,
                e,
            )
            return None

    # --------------------------
    # Resource caching methods
    # --------------------------

    async def get_sql_table_configs(self, client_id: UUID) -> list[dict]:
        """Get SQL table configurations for client, with Redis caching."""
        cache_key = f"sql_configs:{client_id}"

        try:
            cached = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached is not None:
                logger.debug(f"SQL configs cache hit for {client_id}")
                return cached
        except Exception as e:
            logger.warning(f"Redis cache read failed for sql_configs: {e}")

        configs = []
        try:
            supabase = get_supabase_client()
            # Fetch global (client_id IS NULL) + client-specific rows in one query.
            # client_id IS NULL → shared analytics_v2 schema, applies to all clients.
            # client_id = <uuid> → per-client override (e.g. BigQuery FDW tables).
            response = (
                supabase.table("sql_table_config")
                .select("*")
                .or_(f"client_id.is.null,client_id.eq.{str(client_id)}")
                .eq("is_active", True)
                .execute()
            )
            rows = response.data or []
            # Client-specific rows win over global ones with the same table_name.
            by_table: dict[str, dict] = {}
            for row in rows:
                name = row["table_name"]
                if name not in by_table or row["client_id"] is not None:
                    by_table[name] = row
            configs = list(by_table.values())
            logger.debug(f"Loaded {len(configs)} SQL table configs for {client_id}")
        except Exception as e:
            logger.error(f"Failed to load SQL configs from Supabase: {e}")

        if configs:
            try:
                await asyncio.to_thread(
                    self.cache.set_json, cache_key, configs, self.CACHE_TTL_SECONDS
                )
            except Exception as e:
                logger.warning(f"Failed to cache SQL configs: {e}")

        return configs

    async def get_cached_prompt(
        self,
        name: str,
        loader: "PromptLoader",
        variables: dict[str, Any],
        langfuse_label: str | None = None,
    ) -> str:
        """Get prompt with Redis caching. Caches raw template; applies variables after retrieval."""
        label = langfuse_label or "production"
        cache_key = f"prompt:{name}:{label}"

        try:
            cached = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached and "content" in cached:
                logger.debug(f"Prompt cache hit for {name}")
                return loader.renderer.render(cached["content"], variables)
        except Exception as e:
            logger.warning(f"Redis cache read failed for prompt: {e}")

        try:
            loaded = await loader.load_raw(name, langfuse_label=label)

            try:
                await asyncio.to_thread(
                    self.cache.set_json,
                    cache_key,
                    {"content": loaded.content, "version": loaded.version, "source": loaded.source},
                    self.CACHE_TTL_SECONDS,
                )
            except Exception as e:
                logger.warning(f"Failed to cache prompt: {e}")

            return loader.renderer.render(loaded.content, variables)

        except Exception as e:
            logger.warning(f"PromptLoader.load_raw failed for {name}: {e}, using builtin")
            loaded = loader.load_builtin(name, variables)
            return loaded.content

    async def get_canonical_columns(
        self,
        *,
        category: str | None = None,
        table_name: str | None = None,
    ) -> list[dict]:
        """Return canonical column definitions, optionally filtered by category or table.

        Data is global (not per-client) and cached under a single key with a long TTL.
        Filter in-memory after retrieval to avoid cache key proliferation.

        Args:
            category: One of 'mappable', 'aggregation', 'cluster', 'dimension', 'system'.
            table_name: analytics_v2 table name, e.g. 'fato_transacoes'.
        """
        cache_key = "canonical_columns:all"

        rows: list[dict] = []
        try:
            cached = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached is not None:
                logger.debug("canonical_columns cache hit")
                rows = cached
        except Exception as e:
            logger.warning("Redis read failed for canonical_columns: %s", e)

        if not rows:
            try:
                supabase = get_supabase_client()
                response = (
                    supabase.table("canonical_columns")
                    .select("table_name,column_name,data_type,is_required,category,description,examples")
                    .order("table_name")
                    .order("column_name")
                    .execute()
                )
                rows = response.data or []
                logger.debug("Loaded %d canonical columns from Supabase", len(rows))
            except Exception as e:
                logger.error("Failed to load canonical_columns: %s", e)
                return []

            if rows:
                try:
                    await asyncio.to_thread(self.cache.set_json, cache_key, rows, self.CANONICAL_TTL_SECONDS)
                except Exception as e:
                    logger.warning("Failed to cache canonical_columns: %s", e)

        if category:
            rows = [r for r in rows if r.get("category") == category]
        if table_name:
            rows = [r for r in rows if r.get("table_name") == table_name]

        return rows

    async def clear_canonical_columns_cache(self) -> None:
        """Invalidate the canonical columns cache (call after schema migrations)."""
        await asyncio.to_thread(self.cache.delete, "canonical_columns:all")
        logger.info("canonical_columns cache invalidated")

    # --------------------------
    # Business Memory Snapshot
    # --------------------------

    async def get_business_memory_snapshot(
        self,
        client_id: UUID,
        *,
        max_chars: int = 6000,
    ) -> str:
        """Return a compact, LLM-ready snapshot of the client's business state.

        Aggregates five sources (ordered by priority):
          1. Pending approval_requests  → decisions waiting for the user
          2. Unread urgent notifications → active alerts
          3. Active client_goals         → what the client is working toward
          4. dimension_state (valid)     → per-room business state summaries
          5. Recent client_insights      → AI-generated observations

        The result is plain text, truncated to ``max_chars``, ready to be
        injected into any agent prompt under a "## Estado do Negócio" section.

        Args:
            client_id: Client UUID.
            max_chars: Soft character budget (default 6 000 ≈ ~1 500 tokens).

        Returns:
            Formatted text block, or empty string if nothing is available.
        """
        try:
            supabase = get_supabase_client()
            parts: list[str] = []
            used = 0

            # --- 1. Pending approvals ---
            try:
                resp = (
                    supabase.table("approval_requests")
                    .select("title, action_type, priority, insight_text, created_at")
                    .eq("client_id", str(client_id))
                    .eq("status", "pending")
                    .order("created_at", desc=True)
                    .limit(5)
                    .execute()
                )
                rows = resp.data or []
                if rows:
                    lines = ["### Aprovações pendentes"]
                    for r in rows:
                        pri = r.get("priority", "normal")
                        title = r.get("title") or r.get("action_type", "")
                        note = r.get("insight_text", "")
                        lines.append(f"- [{pri.upper()}] {title}" + (f": {note}" if note else ""))
                    block = "\n".join(lines)
                    parts.append(block)
                    used += len(block)
            except Exception as e:
                logger.warning("[snapshot] approval_requests failed: %s", e)

            # --- 2. Urgent unread notifications ---
            if used < max_chars:
                try:
                    resp = (
                        supabase.table("notifications")
                        .select("title, body, urgency_level, created_at")
                        .eq("client_id", str(client_id))
                        .is_("read_at", "null")
                        .is_("dismissed_at", "null")
                        .in_("urgency_level", ["high", "critical"])
                        .order("created_at", desc=True)
                        .limit(5)
                        .execute()
                    )
                    rows = resp.data or []
                    if rows:
                        lines = ["### Alertas não lidos"]
                        for r in rows:
                            lvl = r.get("urgency_level", "")
                            title = r.get("title", "")
                            body = r.get("body", "")
                            lines.append(f"- [{lvl.upper()}] {title}" + (f": {body}" if body else ""))
                        block = "\n".join(lines)
                        parts.append(block)
                        used += len(block)
                except Exception as e:
                    logger.warning("[snapshot] notifications failed: %s", e)

            # --- 3. Active goals ---
            if used < max_chars:
                try:
                    resp = (
                        supabase.table("client_goals")
                        .select("dimension, title, target_value, current_value, unit, deadline, description")
                        .eq("client_id", str(client_id))
                        .eq("status", "active")
                        .order("created_at", desc=True)
                        .limit(8)
                        .execute()
                    )
                    rows = resp.data or []
                    if rows:
                        lines = ["### Metas ativas"]
                        for r in rows:
                            dim = r.get("dimension", "")
                            title = r.get("title", "")
                            cur = r.get("current_value")
                            tgt = r.get("target_value")
                            unit = r.get("unit", "")
                            dl = r.get("deadline", "")
                            progress = ""
                            if cur is not None and tgt is not None and tgt != 0:
                                pct = round(float(cur) / float(tgt) * 100)
                                progress = f" ({pct}% — {cur}/{tgt} {unit})"
                            elif tgt is not None:
                                progress = f" (meta: {tgt} {unit})"
                            deadline_str = f" prazo {dl}" if dl else ""
                            lines.append(f"- [{dim}] {title}{progress}{deadline_str}")
                        block = "\n".join(lines)
                        parts.append(block)
                        used += len(block)
                except Exception as e:
                    logger.warning("[snapshot] client_goals failed: %s", e)

            # --- 4. dimension_state (valid rows only) ---
            if used < max_chars:
                try:
                    resp = (
                        supabase.table("dimension_state")
                        .select("dimension, summary, updated_at, valid_until")
                        .eq("client_id", str(client_id))
                        .order("updated_at", desc=True)
                        .execute()
                    )
                    rows = resp.data or []
                    if rows:
                        lines = ["### Estado por dimensão"]
                        for r in rows:
                            # Skip expired rows (valid_until not null and in the past)
                            valid_until = r.get("valid_until")
                            if valid_until:
                                from datetime import timezone
                                try:
                                    from dateutil import parser as dtparser
                                    vu = dtparser.parse(valid_until)
                                    if vu.tzinfo is None:
                                        vu = vu.replace(tzinfo=UTC)
                                    if vu < datetime.now(UTC):
                                        continue
                                except Exception:
                                    pass
                            dim = r.get("dimension", "")
                            summary = r.get("summary", "").strip()
                            if summary:
                                remaining = max_chars - used - len("\n".join(lines))
                                if remaining < 50:
                                    break
                                lines.append(f"**{dim.capitalize()}**: {summary[:min(len(summary), remaining)]}")
                        if len(lines) > 1:
                            block = "\n".join(lines)
                            parts.append(block)
                            used += len(block)
                except Exception as e:
                    logger.warning("[snapshot] dimension_state failed: %s", e)

            # --- 5. Recent insights ---
            if used < max_chars:
                try:
                    resp = (
                        supabase.table("client_insights")
                        .select("dimension, title, observation, recommendation, severity")
                        .eq("client_id", str(client_id))
                        .eq("dismissed", False)
                        .in_("severity", ["warning", "critical"])
                        .order("generated_at", desc=True)
                        .limit(5)
                        .execute()
                    )
                    rows = resp.data or []
                    if rows:
                        lines = ["### Insights recentes"]
                        for r in rows:
                            dim = r.get("dimension", "")
                            title = r.get("title", "")
                            obs = r.get("observation", "")
                            rec = r.get("recommendation", "")
                            sev = r.get("severity", "")
                            line = f"- [{sev.upper()} | {dim}] {title}"
                            if obs:
                                line += f"\n  Obs: {obs}"
                            if rec:
                                line += f"\n  Rec: {rec}"
                            lines.append(line)
                        block = "\n".join(lines)
                        parts.append(block)
                        used += len(block)
                except Exception as e:
                    logger.warning("[snapshot] client_insights failed: %s", e)

            if not parts:
                return ""

            snapshot = "\n\n".join(parts)
            if len(snapshot) > max_chars:
                snapshot = snapshot[:max_chars] + "\n[...snapshot truncado]"

            return f"## Estado do Negócio\n\n{snapshot}"

        except Exception as e:
            logger.error("[snapshot] get_business_memory_snapshot failed: %s", e, exc_info=True)
            return ""

    async def get_morning_brief(
        self,
        client_id: UUID | str,
        *,
        max_chars: int = 2000,
    ) -> str:
        """Return a structured morning brief for the User-Facing Agent.

        Aggregates three live sources:
          1. Pending approvals (approval_requests, status='pending', limit 5)
          2. Active routines  (cross_agent_routines with client_routine_configs, limit 10)
          3. Business memory snapshot (delegates to get_business_memory_snapshot)

        The result is plain text, truncated to ``max_chars``, ready to be injected
        into the agent system prompt under a "## Morning Brief" section.

        Args:
            client_id: Client UUID (str or UUID).
            max_chars: Soft character budget (default 2 000).

        Returns:
            Formatted text block, or empty string on error / no data.
        """
        try:
            if isinstance(client_id, str):
                client_id_uuid = UUID(client_id)
            else:
                client_id_uuid = client_id

            supabase = get_supabase_client(use_service_role=True)
            parts: list[str] = []

            # --- 1. Pending approvals ---
            try:
                resp = (
                    supabase.table("approval_requests")
                    .select("title, agent_slug, priority")
                    .eq("client_id", str(client_id_uuid))
                    .eq("status", "pending")
                    .order("created_at", desc=True)
                    .limit(5)
                    .execute()
                )
                rows = resp.data or []
                if rows:
                    lines = ["## Aprovações Pendentes"]
                    for r in rows:
                        title = r.get("title") or ""
                        slug = r.get("agent_slug") or ""
                        pri = r.get("priority") or "normal"
                        lines.append(f"• {title} — {slug} ({pri})")
                    parts.append("\n".join(lines))
            except Exception as e:
                logger.warning("[morning_brief] approval_requests failed: %s", e)

            # --- 2. Active routines ---
            try:
                resp = (
                    supabase.table("cross_agent_routines")
                    .select("name, trigger_config, client_routine_configs!inner(client_id)")
                    .eq("client_routine_configs.client_id", str(client_id_uuid))
                    .eq("is_active", True)
                    .limit(10)
                    .execute()
                )
                rows = resp.data or []
                if rows:
                    lines = ["## Rotinas Ativas"]
                    for r in rows:
                        name = r.get("name") or ""
                        tc = r.get("trigger_config") or {}
                        cron = tc.get("cron") or tc.get("expression") or str(tc)
                        lines.append(f"• {name} (cron: {cron})")
                    parts.append("\n".join(lines))
            except Exception as e:
                logger.warning("[morning_brief] cross_agent_routines failed: %s", e)

            # --- 3. Business memory snapshot ---
            try:
                snapshot = await self.get_business_memory_snapshot(
                    client_id_uuid, max_chars=max_chars
                )
                if snapshot:
                    parts.append(snapshot)
            except Exception as e:
                logger.warning("[morning_brief] get_business_memory_snapshot failed: %s", e)

            if not parts:
                return ""

            brief = "\n\n".join(parts)
            if len(brief) > max_chars:
                brief = brief[:max_chars] + "\n[...brief truncado]"

            return f"## Morning Brief\n\n{brief}"

        except Exception as e:
            logger.error("[morning_brief] get_morning_brief failed: %s", e, exc_info=True)
            return ""

    async def clear_sql_configs_cache(self, client_id: UUID) -> None:
        """Clear SQL table configs cache for a client."""
        cache_key = f"sql_configs:{client_id}"
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"SQL configs cache invalidated for: {client_id}")

    async def clear_prompt_cache(self, name: str, langfuse_label: str = "production") -> None:
        """Clear prompt cache for a specific prompt."""
        cache_key = f"prompt:{name}:{langfuse_label}"
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"Prompt cache invalidated for: {name}")

    # --------------------------
    # Integration helpers
    # --------------------------

    def _encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return plaintext
        if not self._cipher:
            raise RuntimeError("No CREDENTIALS_ENCRYPTION_KEY configured")
        return self._cipher.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ciphertext
        if not self._cipher:
            raise RuntimeError("No CREDENTIALS_ENCRYPTION_KEY configured")
        return self._cipher.decrypt(ciphertext.encode()).decode()

    async def save_integration_config(
        self,
        client_id: UUID,
        provider: str,
        config_type: str,
        oauth_client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[Any],
    ):
        """Encrypt and persist integration client credentials."""
        enc_client_id = await asyncio.to_thread(self._encrypt, oauth_client_id)
        enc_client_secret = await asyncio.to_thread(self._encrypt, client_secret)
        return await asyncio.to_thread(
            self._supabase_crud.save_integration_config,
            client_id,
            provider,
            config_type,
            enc_client_id,
            enc_client_secret,
            redirect_uri,
            scopes,
        )

    async def get_integration_config(self, client_id: UUID, provider: str) -> None:
        """Retrieve integration config."""
        return await asyncio.to_thread(
            self._supabase_crud.get_integration_config, client_id, provider
        )

    async def get_platform_oauth_config(self, provider: str) -> dict[str, Any] | None:
        """Retrieve platform-level OAuth credentials from Supabase Vault."""
        return await asyncio.to_thread(
            self._supabase_crud.get_platform_oauth_config, provider
        )

    async def _fetch_google_oauth_config_from_vault(self) -> dict[str, str]:
        """Fetch Google OAuth config from Vault via service-role RPC."""
        try:
            service_client = get_supabase_client(use_service_role=True)
            service_crud = SupabaseCRUD(client=service_client)
            platform_cfg = await asyncio.to_thread(
                service_crud.get_platform_oauth_config,
                "google",
            )
        except Exception as exc:
            raise RuntimeError(
                "[Token Refresh] Failed to read Google OAuth config from Vault via "
                "get_platform_google_oauth_config"
            ) from exc

        if not isinstance(platform_cfg, dict):
            raise RuntimeError(
                "[Token Refresh] Google OAuth config is missing in Vault "
                "(get_platform_google_oauth_config returned empty)"
            )

        oauth_client_id = platform_cfg.get("client_id")
        oauth_client_secret = platform_cfg.get("client_secret")

        if not oauth_client_id or not oauth_client_secret:
            raise RuntimeError(
                "[Token Refresh] Google OAuth config in Vault is invalid: "
                "missing client_id/client_secret"
            )

        return {
            "client_id": oauth_client_id,
            "client_secret": oauth_client_secret,
        }

    async def _get_google_oauth_config_cached(self) -> dict[str, str]:
        """Return Vault Google OAuth config with in-process TTL cache."""
        global _GOOGLE_OAUTH_CONFIG_CACHE, _GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT

        now = datetime.now(UTC)
        with _GOOGLE_OAUTH_CONFIG_CACHE_LOCK:
            if (
                _GOOGLE_OAUTH_CONFIG_CACHE
                and _GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT
                and _GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT > now
            ):
                return dict(_GOOGLE_OAUTH_CONFIG_CACHE)

        oauth_config = await self._fetch_google_oauth_config_from_vault()

        with _GOOGLE_OAUTH_CONFIG_CACHE_LOCK:
            _GOOGLE_OAUTH_CONFIG_CACHE = dict(oauth_config)
            _GOOGLE_OAUTH_CONFIG_CACHE_EXPIRES_AT = datetime.now(UTC) + timedelta(
                seconds=_GOOGLE_OAUTH_CONFIG_CACHE_TTL_SECONDS
            )
            return dict(_GOOGLE_OAUTH_CONFIG_CACHE)

    async def save_integration_tokens(
        self,
        client_id: UUID,
        provider: str,
        access_token: str,
        refresh_token: str | None,
        token_type: str | None,
        scopes: list[Any],
        metadata: dict[str, Any] | None = None,
        account_email: str | None = None,
        account_name: str | None = None,
        is_default: bool = False,
    ):
        """Persist tokens to Vault via RPC (encryption handled by PostgreSQL)."""
        return await asyncio.to_thread(
            self._supabase_crud.save_integration_tokens,
            client_id,
            provider,
            access_token,
            refresh_token,
            token_type,
            scopes,
            metadata,
            account_email,
            account_name,
            is_default,
        )

    class _IntegrationTokenWrapper:
        """Wrapper around a DB row exposing token validity and decryption helpers."""

        def __init__(self, row, decrypt_fn, context_service=None, client_id=None, provider=None) -> None:
            self._row = row
            self._decrypt = decrypt_fn
            self._context_service = context_service
            self._client_id = client_id
            self._provider = provider

        def _get(self, key) -> None:
            try:
                return self._row[key]
            except Exception:
                try:
                    return getattr(self._row, key)
                except Exception:
                    try:
                        return self._row._mapping.get(key)
                    except Exception:
                        return None

        def is_valid(self) -> bool:
            """Check if token is still valid (not expired)."""
            expires = self._get("expires_at")
            if not expires:
                access_token = self._get("access_token") or self._get("access_token_encrypted")
                return bool(access_token)
            if isinstance(expires, str):
                try:
                    exp_dt = datetime.fromisoformat(expires)
                except Exception:
                    access_token = self._get("access_token") or self._get("access_token_encrypted")
                    return bool(access_token)
            elif isinstance(expires, datetime):
                exp_dt = expires
            else:
                access_token = self._get("access_token") or self._get("access_token_encrypted")
                return bool(access_token)
            now = datetime.now(UTC)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=UTC)
            return exp_dt > now

        def is_expiring_soon(self, margin_seconds: int = 300) -> bool:
            """Check if token will expire within margin_seconds (default 5 minutes)."""
            expires = self._get("expires_at")
            if not expires:
                return False
            if isinstance(expires, str):
                try:
                    exp_dt = datetime.fromisoformat(expires)
                except Exception:
                    return False
            elif isinstance(expires, datetime):
                exp_dt = expires
            else:
                return False

            from datetime import timedelta

            now = datetime.now(UTC)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=UTC)
            return exp_dt <= now + timedelta(seconds=margin_seconds)

        def get_decrypted_tokens(self) -> dict[str, Any]:
            access_token = self._get("access_token") or self._get("access_token_encrypted")
            refresh_token = self._get("refresh_token") or self._get("refresh_token_encrypted")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": self._get("token_type"),
                "expires_at": self._get("expires_at"),
                "scopes": self._get("scopes"),
                "metadata": self._get("metadata"),
                "account_email": self._get("account_email"),
                "account_name": self._get("account_name"),
                "is_default": self._get("is_default"),
            }

    async def _refresh_google_token(
        self,
        client_id: UUID,
        refresh_token: str,
        account_email: str | None = None,
    ) -> "ContextService._IntegrationTokenWrapper" | None:
        """Refresh a Google access token using the stored refresh token."""
        try:
            oauth_config_values = await self._get_google_oauth_config_cached()
            if not isinstance(oauth_config_values, dict):
                raise RuntimeError(
                    "[Token Refresh] Google OAuth config is missing in Vault "
                    "(cached config is empty)"
                )

            oauth_client_id = oauth_config_values.get("client_id")
            oauth_client_secret = oauth_config_values.get("client_secret")
            if not oauth_client_id or not oauth_client_secret:
                logger.warning(
                    "[Token Refresh] Google OAuth config in Vault is missing "
                    "client_id/client_secret; attempting refresh without updated credentials"
                )
                oauth_client_id = oauth_client_id or ""
                oauth_client_secret = oauth_client_secret or ""

            redirect_uri = ""
            scopes: list[str] = []

            from blu_auth.oauth2.models import OAuthConfig
            from blu_auth.oauth2.oauth_manager import OAuthManager

            oauth_config = OAuthConfig(
                client_id=oauth_client_id,
                client_secret=oauth_client_secret,
                redirect_uri=redirect_uri,
                scopes=scopes,
            )

            manager = OAuthManager("google")
            new_tokens = await manager.refresh(oauth_config, refresh_token)
            expires_at = datetime.now(UTC) + timedelta(seconds=new_tokens.expires_in or 3600)

            await self.save_integration_tokens(
                client_id=client_id,
                provider="google",
                access_token=new_tokens.access_token,
                refresh_token=new_tokens.refresh_token or refresh_token,
                token_type=new_tokens.token_type,
                scopes=new_tokens.scope.split() if new_tokens.scope else scopes,
                account_email=account_email,
            )

            logger.info(
                f"[Token Refresh] Successfully refreshed Google token for cliente {client_id}"
            )

            return await self.get_integration_tokens(
                client_id, "google", auto_refresh=False, account_email=account_email
            )

        except RuntimeError:
            logger.error("[Token Refresh] Failed to refresh Google token due to Vault config error", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[Token Refresh] Failed to refresh Google token: {e}", exc_info=True)
            return None

    async def get_integration_tokens(
        self,
        client_id: UUID,
        provider: str,
        auto_refresh: bool = True,
        account_email: str | None = None,
    ):
        """Retrieve token wrapper exposing is_valid() and get_decrypted_tokens()."""
        row = await asyncio.to_thread(
            self._supabase_crud.get_integration_tokens,
            client_id,
            provider,
            account_email,
        )

        if not row:
            return None

        wrapper = ContextService._IntegrationTokenWrapper(
            row,
            lambda x: x,  # no-op: Vault decrypts tokens inside PostgreSQL
            context_service=self,
            client_id=client_id,
            provider=provider,
        )

        if auto_refresh and provider == "google" and wrapper.is_expiring_soon(margin_seconds=300):
            tokens = wrapper.get_decrypted_tokens()
            refresh_token = tokens.get("refresh_token")
            current_account_email = tokens.get("account_email")

            if refresh_token:
                logger.info(
                    f"[Token Refresh] Token expiring soon for {client_id}, attempting refresh..."
                )
                refreshed_wrapper = await self._refresh_google_token(
                    client_id, refresh_token, account_email=current_account_email
                )
                if refreshed_wrapper:
                    return refreshed_wrapper
                logger.warning("[Token Refresh] Refresh failed, returning possibly expired token")
            else:
                logger.warning(f"[Token Refresh] No refresh token available for {client_id}")

        return wrapper

    async def list_integration_accounts(self, client_id: UUID, provider: str) -> list[Any]:
        """List all connected accounts for a cliente/provider."""
        rows = await asyncio.to_thread(
            self._supabase_crud.list_integration_accounts, client_id, provider
        )

        result = []
        for row in rows or []:
            if hasattr(row, "_mapping"):
                row = dict(row._mapping)
            elif not isinstance(row, dict):
                row = dict(row)
            result.append(
                {
                    "id": str(row.get("id")),
                    "account_email": row.get("account_email"),
                    "account_name": row.get("account_name"),
                    "is_default": row.get("is_default", False),
                    "expires_at": row.get("expires_at"),
                    "scopes": row.get("scopes"),
                    "created_at": row.get("created_at"),
                }
            )
        return result

    async def set_default_account(
        self, client_id: UUID, provider: str, account_email: str
    ) -> bool:
        """Set a specific account as the default for a cliente/provider."""
        result = await asyncio.to_thread(
            self._supabase_crud.set_default_account, client_id, provider, account_email
        )
        return result is not None

    async def revoke_integration(
        self, client_id: UUID, provider: str, account_email: str | None = None
    ) -> bool:
        """Revoke integration for a specific account or all accounts."""
        return await asyncio.to_thread(
            self._supabase_crud.revoke_integration, client_id, provider, account_email
        )
