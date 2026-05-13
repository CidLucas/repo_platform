import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from blu_prompt_management import PromptLoader

from cryptography.fernet import Fernet

from blu_supabase_client import SupabaseCRUD, get_supabase_client
from blu_supabase_client.client import set_rls_context as supabase_set_rls

from blu_models.blu_client_context import BluClientContext

from .redis_service import RedisService

logger = logging.getLogger(__name__)


class ContextService:
    """Service for fetching and caching client context via Supabase SDK."""

    CACHE_KEY_PREFIX = "context:client:"
    CACHE_TTL_SECONDS = 300  # 5 minutos

    def __init__(self, cache_service: RedisService):
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

    def _get_cache_key(self, cliente_id: UUID) -> str:
        return f"{self.CACHE_KEY_PREFIX}{cliente_id}"

    def _set_rls_context(self, cliente_id: UUID) -> None:
        try:
            client = get_supabase_client()
            supabase_set_rls(client, str(cliente_id))
            logger.debug(f"RLS context set via Supabase RPC for: {cliente_id}")
        except Exception as e:
            logger.warning(f"Could not set RLS context via Supabase: {e}")

    def _build_context_from_dict(self, data: dict) -> BluClientContext:
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
        self, context: BluClientContext, cliente_id: UUID
    ) -> BluClientContext:
        """Enrich BluClientContext.data_schema with detailed table schemas from sql_table_config."""
        try:
            configs = await self.get_sql_table_configs(cliente_id)

            if not configs:
                logger.debug(f"No sql_table_config entries for {cliente_id}")
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
                f"Enriched data_schema with {len(table_schemas)} table schemas for {cliente_id}"
            )
            return context

        except Exception as e:
            logger.warning(f"Failed to enrich data_schema with table_schemas: {e}")
            return context

    async def get_client_context_by_external_user_id(
        self, external_user_id: str | UUID
    ) -> BluClientContext | None:
        """
        Fetch context using the external_user_id (Supabase Auth user ID / JWT sub claim).

        This is the primary entry point for JWT-authenticated requests.
        """
        try:
            cliente_data = await asyncio.to_thread(
                self._supabase_crud.get_cliente_blu_by_external_user_id, str(external_user_id)
            )

            if not cliente_data:
                logger.warning(f"Cliente não encontrado para external_user_id={external_user_id}")
                return None

            internal_client_id = UUID(cliente_data["client_id"])
            logger.debug(
                f"Found cliente: external_user_id={external_user_id} -> client_id={internal_client_id}"
            )

            return await self.get_client_context_by_id(internal_client_id)

        except Exception as e:
            logger.error(
                f"Erro ao buscar contexto por external_user_id={external_user_id}: {e}",
                exc_info=True,
            )
            return None

    async def get_client_context_by_id(self, cliente_id: UUID) -> BluClientContext | None:
        """Fetch full client context with Redis caching and RLS enforcement."""
        cache_key = self._get_cache_key(cliente_id)

        await asyncio.to_thread(self._set_rls_context, cliente_id)

        try:
            cached_data = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached_data:
                try:
                    return BluClientContext.model_validate(cached_data)
                except Exception as e:
                    logger.warning(f"Cache corrompido para {cliente_id}, invalidando... Erro: {e}")
                    await self.clear_context_cache(cliente_id)
        except Exception as e:
            logger.warning(f"Falha ao ler cache Redis: {e}")

        try:
            cliente_data = await asyncio.to_thread(
                self._supabase_crud.get_cliente_blu_by_id, cliente_id
            )
            if not cliente_data:
                logger.warning(f"Cliente {cliente_id} não encontrado no banco.")
                return None

            client_context = self._build_context_from_dict(cliente_data)
            client_context = await self._enrich_data_schema_with_table_schemas(
                client_context, cliente_id
            )

            await asyncio.to_thread(
                self.cache.set_json,
                key=cache_key,
                data=client_context,
                ttl_seconds=self.CACHE_TTL_SECONDS,
            )

            return client_context

        except Exception as e:
            logger.error(f"Erro crítico ao montar contexto para {cliente_id}: {e}", exc_info=True)
            return None

    async def clear_context_cache(self, cliente_id: UUID) -> None:
        """Remove context from cache (call after client updates)."""
        cache_key = self._get_cache_key(cliente_id)
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"Cache invalidado para: {cliente_id}")

    # --------------------------
    # Resource caching methods
    # --------------------------

    async def get_sql_table_configs(self, cliente_id: UUID) -> list[dict]:
        """Get SQL table configurations for client, with Redis caching."""
        cache_key = f"sql_configs:{cliente_id}"

        try:
            cached = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached is not None:
                logger.debug(f"SQL configs cache hit for {cliente_id}")
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
                .or_(f"client_id.is.null,client_id.eq.{str(cliente_id)}")
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
            logger.debug(f"Loaded {len(configs)} SQL table configs for {cliente_id}")
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
        variables: dict,
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

    async def clear_sql_configs_cache(self, cliente_id: UUID) -> None:
        """Clear SQL table configs cache for a client."""
        cache_key = f"sql_configs:{cliente_id}"
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"SQL configs cache invalidated for: {cliente_id}")

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
        scopes: list,
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

    async def get_integration_config(self, client_id: UUID, provider: str):
        """Retrieve integration config."""
        return await asyncio.to_thread(
            self._supabase_crud.get_integration_config, client_id, provider
        )

    async def get_platform_oauth_config(self, provider: str) -> dict | None:
        """Retrieve platform-level OAuth credentials from Supabase Vault."""
        return await asyncio.to_thread(
            self._supabase_crud.get_platform_oauth_config, provider
        )

    async def save_integration_tokens(
        self,
        client_id: UUID,
        provider: str,
        access_token: str,
        refresh_token: str | None,
        token_type: str | None,
        expires_at: datetime | None,
        scopes: list,
        metadata: dict | None = None,
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
            expires_at,
            scopes,
            metadata,
            account_email,
            account_name,
            is_default,
        )

    class _IntegrationTokenWrapper:
        """Wrapper around a DB row exposing token validity and decryption helpers."""

        def __init__(self, row, decrypt_fn, context_service=None, cliente_id=None, provider=None):
            self._row = row
            self._decrypt = decrypt_fn
            self._context_service = context_service
            self._cliente_id = cliente_id
            self._provider = provider

        def _get(self, key):
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
                return bool(self._get("access_token"))
            if isinstance(expires, str):
                try:
                    exp_dt = datetime.fromisoformat(expires)
                except Exception:
                    return True
            elif isinstance(expires, datetime):
                exp_dt = expires
            else:
                return True
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

        def get_decrypted_tokens(self) -> dict:
            return {
                "access_token": self._get("access_token"),
                "refresh_token": self._get("refresh_token"),
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
    ) -> Optional["ContextService._IntegrationTokenWrapper"]:
        """Refresh a Google access token using the stored refresh token."""
        try:
            cfg_row = await self.get_integration_config(client_id, "google")

            if cfg_row:
                oauth_client_id = self._decrypt(
                    cfg_row.get("client_id_encrypted")
                    if isinstance(cfg_row, dict)
                    else cfg_row.client_id_encrypted
                )
                oauth_client_secret = self._decrypt(
                    cfg_row.get("client_secret_encrypted")
                    if isinstance(cfg_row, dict)
                    else cfg_row.client_secret_encrypted
                )
                redirect_uri = (
                    cfg_row.get("redirect_uri") if isinstance(cfg_row, dict) else cfg_row.redirect_uri
                )
                scopes = cfg_row.get("scopes") if isinstance(cfg_row, dict) else cfg_row.scopes
            else:
                platform_cfg = await self.get_platform_oauth_config("google")
                if not platform_cfg:
                    logger.error(f"[Token Refresh] No Google config found for cliente {client_id}")
                    return None
                oauth_client_id = platform_cfg["client_id"]
                oauth_client_secret = platform_cfg["client_secret"]
                redirect_uri = ""
                scopes = []

            from datetime import timedelta

            from blu_auth.oauth2.models import OAuthConfig
            from blu_auth.oauth2.oauth_manager import OAuthManager

            oauth_config = OAuthConfig(
                client_id=oauth_client_id,
                client_secret=oauth_client_secret,
                redirect_uri=redirect_uri,
                scopes=scopes if isinstance(scopes, list) else [],
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
                expires_at=expires_at,
                scopes=new_tokens.scope.split() if new_tokens.scope else scopes,
                account_email=account_email,
            )

            logger.info(
                f"[Token Refresh] Successfully refreshed Google token for cliente {client_id}"
            )

            return await self.get_integration_tokens(
                client_id, "google", auto_refresh=False, account_email=account_email
            )

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
            cliente_id=client_id,
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

    async def list_integration_accounts(self, client_id: UUID, provider: str) -> list:
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
