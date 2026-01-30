import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from vizu_prompt_management import PromptLoader

from cryptography.fernet import Fernet

# Suporte a ambos os modos: SQLAlchemy (legado) e Supabase SDK (novo)
try:
    from vizu_supabase_client import SupabaseCRUD, get_supabase_client
    from vizu_supabase_client.client import set_rls_context as supabase_set_rls

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

try:
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from vizu_db_connector import crud as sqlalchemy_crud

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

from vizu_models.vizu_client_context import VizuClientContext

from .redis_service import RedisService

logger = logging.getLogger(__name__)


class ContextService:
    """
    Service for fetching and caching client context.

    Supports two backends:
    1. Supabase SDK (preferred) - Uses HTTP REST API
    2. SQLAlchemy (legacy) - Uses direct PostgreSQL connection

    The backend is automatically selected based on initialization.
    """

    CACHE_KEY_PREFIX = "context:client:"
    CACHE_TTL_SECONDS = 300  # 5 minutos

    def __init__(
        self,
        cache_service: RedisService,
        db_session: Optional["Session"] = None,
        use_supabase: bool = True,
    ):
        """
        Initialize ContextService.

        Args:
            cache_service: Redis service for caching
            db_session: SQLAlchemy session (optional, for legacy mode)
            use_supabase: If True and available, use Supabase SDK
        """
        self.cache = cache_service
        self.db = db_session

        # Determine backend
        if use_supabase and SUPABASE_AVAILABLE:
            self._use_supabase = True
            self._supabase_crud = SupabaseCRUD()
            logger.info("ContextService initialized with Supabase SDK backend")
        elif SQLALCHEMY_AVAILABLE and db_session is not None:
            self._use_supabase = False
            self._supabase_crud = None
            logger.info("ContextService initialized with SQLAlchemy backend (legacy)")
        else:
            raise RuntimeError(
                "No database backend available. "
                "Install vizu_supabase_client or provide a SQLAlchemy session."
            )

        # Initialize credential encryption cipher
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
        """
        Define o contexto RLS para o cliente atual.

        Para Supabase SDK: chama RPC function
        Para SQLAlchemy: executa SET config
        """
        if self._use_supabase:
            try:
                client = get_supabase_client()
                supabase_set_rls(client, str(cliente_id))
                logger.debug(f"RLS context set via Supabase RPC for: {cliente_id}")
            except Exception as e:
                logger.warning(f"Could not set RLS context via Supabase: {e}")
        else:
            # Legacy SQLAlchemy mode
            try:
                self.db.execute(
                    text(
                        "SELECT set_config('app.current_cliente_id', :cliente_id, false)"
                    ),
                    {"cliente_id": str(cliente_id)},
                )
                logger.debug(f"RLS context set via SQLAlchemy for: {cliente_id}")
            except Exception as e:
                logger.warning(f"Could not set RLS context (SQLAlchemy): {e}")

    def _build_context_from_dict(self, data: dict) -> VizuClientContext:
        """Build VizuClientContext from Supabase response dict.

        Context 2.0: Now includes all modular context sections.
        """
        def _normalize_enabled_tools(raw):
            if not raw:
                return []
            if isinstance(raw, str):
                # JSON string? Try to parse conservatively
                try:
                    import json

                    parsed = json.loads(raw)
                except Exception:
                    return []
            else:
                parsed = raw

            if not isinstance(parsed, list | tuple):
                return []

            seen = set()
            deduped = []
            for v in parsed:
                if v is None:
                    continue
                if v in seen:
                    continue
                seen.add(v)
                deduped.append(v)
            return deduped

        enabled_tools = _normalize_enabled_tools(data.get("enabled_tools"))

        return VizuClientContext(
            # Identification
            id=UUID(data["client_id"]) if isinstance(data["client_id"], str) else data["client_id"],
            nome_empresa=data["nome_empresa"],
            cpf_cnpj=data.get("cpf_cnpj"),
            tipo_cliente=data["tipo_cliente"],
            tier=data["tier"],

            # Context 2.0 sections
            company_profile=data.get("company_profile"),
            brand_voice=data.get("brand_voice"),
            product_catalog=data.get("product_catalog"),
            target_audience=data.get("target_audience"),
            market_context=data.get("market_context"),
            current_moment=data.get("current_moment"),
            team_structure=data.get("team_structure"),
            policies=data.get("policies"),
            data_schema=data.get("data_schema"),
            available_tools=data.get("available_tools"),
            client_custom=data.get("client_custom"),

            # Legacy fields (backward compatibility)
            prompt_base=data.get("prompt_base") or "Você é um assistente útil.",
            horario_funcionamento=data.get("horario_funcionamento") or {},
            enabled_tools=enabled_tools,
            collection_rag=data.get("collection_rag", "default_collection"),
            credenciais=[],
        )

    def _build_context_from_orm(self, cliente_db) -> VizuClientContext:
        """Build VizuClientContext from SQLAlchemy ORM object.

        Context 2.0: Now includes all modular context sections.
        """
        raw = getattr(cliente_db, "enabled_tools", None) or []
        # Normalize/dedupe preserving order
        seen = set()
        deduped = []
        for v in raw or []:
            if v is None:
                continue
            if v in seen:
                continue
            seen.add(v)
            deduped.append(v)

        return VizuClientContext(
            # Identification
            id=cliente_db.client_id,
            nome_empresa=cliente_db.nome_empresa,
            cpf_cnpj=getattr(cliente_db, "cpf_cnpj", None),
            tipo_cliente=cliente_db.tipo_cliente,
            tier=cliente_db.tier,

            # Context 2.0 sections
            company_profile=getattr(cliente_db, "company_profile", None),
            brand_voice=getattr(cliente_db, "brand_voice", None),
            product_catalog=getattr(cliente_db, "product_catalog", None),
            target_audience=getattr(cliente_db, "target_audience", None),
            market_context=getattr(cliente_db, "market_context", None),
            current_moment=getattr(cliente_db, "current_moment", None),
            team_structure=getattr(cliente_db, "team_structure", None),
            policies=getattr(cliente_db, "policies", None),
            data_schema=getattr(cliente_db, "data_schema", None),
            available_tools=getattr(cliente_db, "available_tools", None),
            client_custom=getattr(cliente_db, "client_custom", None),

            # Legacy fields (backward compatibility)
            prompt_base=getattr(cliente_db, "prompt_base", None)
            or "Você é um assistente útil.",
            horario_funcionamento=getattr(cliente_db, "horario_funcionamento", {})
            or {},
            enabled_tools=deduped,
            collection_rag=getattr(cliente_db, "collection_rag", "default_collection"),
            credenciais=[],
        )

    async def get_client_context_by_external_user_id(
        self, external_user_id: str | UUID
    ) -> VizuClientContext | None:
        """
        Recupera o contexto do cliente usando o external_user_id (Supabase Auth user ID).

        Este é o método principal para autenticação JWT:
        - JWT `sub` claim contém o Supabase Auth user ID
        - Este ID é armazenado na coluna `external_user_id`
        - A coluna `id` é o ID interno do cliente Vizu (diferente)

        Args:
            external_user_id: Supabase Auth user ID (from JWT sub claim)

        Returns:
            VizuClientContext or None if not found
        """
        if not self._use_supabase:
            logger.error(
                "get_client_context_by_external_user_id requires Supabase backend"
            )
            return None

        try:
            # Look up cliente by external_user_id
            cliente_data = await asyncio.to_thread(
                self._supabase_crud.get_cliente_vizu_by_external_user_id,
                str(external_user_id)
            )

            if not cliente_data:
                logger.warning(
                    f"Cliente não encontrado para external_user_id={external_user_id}"
                )
                return None

            # Extract the internal client ID (column name is client_id, not id)
            internal_client_id = UUID(cliente_data["client_id"])
            logger.debug(
                f"Found cliente: external_user_id={external_user_id} -> client_id={internal_client_id}"
            )

            # Use existing method to get full context (with caching and RLS)
            return await self.get_client_context_by_id(internal_client_id)

        except Exception as e:
            logger.error(
                f"Erro ao buscar contexto por external_user_id={external_user_id}: {e}",
                exc_info=True
            )
            return None

    async def get_client_context_by_id(
        self, cliente_id: UUID
    ) -> VizuClientContext | None:
        """
        Recupera o contexto completo (Cliente + Configurações), usando Cache Redis.
        Também configura o contexto RLS para garantir isolamento de dados.

        Note: For JWT authentication, prefer get_client_context_by_external_user_id()
        since JWT sub claim = external_user_id, not the internal id.
        """
        cache_key = self._get_cache_key(cliente_id)

        # --- 0. CONFIGURAR CONTEXTO RLS ---
        await asyncio.to_thread(self._set_rls_context, cliente_id)

        # --- 1. TENTATIVA DE CACHE (REDIS) ---
        try:
            cached_data = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached_data:
                try:
                    return VizuClientContext.model_validate(cached_data)
                except Exception as e:
                    logger.warning(
                        f"Cache corrompido para {cliente_id}, invalidando... Erro: {e}"
                    )
                    await self.clear_context_cache(cliente_id)
        except Exception as e:
            logger.warning(f"Falha ao ler cache Redis: {e}")

        # --- 2. BUSCA NO BANCO DE DADOS ---
        try:
            if self._use_supabase:
                # Supabase SDK mode
                cliente_data = await asyncio.to_thread(
                    self._supabase_crud.get_cliente_vizu_by_id, cliente_id
                )
                if not cliente_data:
                    logger.warning(
                        f"Cliente {cliente_id} não encontrado no banco (Supabase)."
                    )
                    return None
                client_context = self._build_context_from_dict(cliente_data)
            else:
                # Legacy SQLAlchemy mode
                cliente_db = await asyncio.to_thread(
                    sqlalchemy_crud.get_cliente_vizu_by_id, self.db, cliente_id
                )
                if not cliente_db:
                    logger.warning(
                        f"Cliente {cliente_id} não encontrado no banco (SQLAlchemy)."
                    )
                    return None
                client_context = self._build_context_from_orm(cliente_db)

            # --- 3. SALVAR NO CACHE ---
            await asyncio.to_thread(
                self.cache.set_json,
                key=cache_key,
                data=client_context,
                ttl_seconds=self.CACHE_TTL_SECONDS,
            )

            return client_context

        except Exception as e:
            logger.error(
                f"Erro crítico ao montar contexto para {cliente_id}: {e}", exc_info=True
            )
            return None

    async def clear_context_cache(self, cliente_id: UUID) -> None:
        """Remove o contexto do cache (útil após updates no cliente)."""
        cache_key = self._get_cache_key(cliente_id)
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"Cache invalidado para: {cliente_id}")

    # --------------------------
    # Resource caching methods
    # --------------------------

    async def get_sql_table_configs(self, cliente_id: UUID) -> list[dict]:
        """
        Get SQL table configurations for client, with Redis caching.

        Uses:
        - Redis pool (singleton via cache_service)
        - Supabase client (singleton via get_supabase_client())

        Args:
            cliente_id: The client UUID

        Returns:
            List of table config dicts from sql_table_config table
        """
        cache_key = f"sql_configs:{cliente_id}"

        # Check Redis cache
        try:
            cached = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached is not None:
                logger.debug(f"SQL configs cache hit for {cliente_id}")
                return cached
        except Exception as e:
            logger.warning(f"Redis cache read failed for sql_configs: {e}")

        # Fetch from Supabase
        configs = []
        if self._use_supabase:
            try:
                supabase = get_supabase_client()  # Singleton
                response = (
                    supabase
                    .table("sql_table_config")
                    .select("*")
                    .eq("client_id", str(cliente_id))
                    .eq("is_active", True)
                    .execute()
                )
                configs = response.data or []
                logger.debug(f"Loaded {len(configs)} SQL configs from Supabase for {cliente_id}")
            except Exception as e:
                logger.error(f"Failed to load SQL configs from Supabase: {e}")
        else:
            # SQLAlchemy fallback - not implemented, return empty
            logger.warning("SQL table configs not implemented for SQLAlchemy backend")

        # Cache in Redis
        if configs:
            try:
                await asyncio.to_thread(
                    self.cache.set_json,
                    cache_key,
                    configs,
                    self.CACHE_TTL_SECONDS
                )
            except Exception as e:
                logger.warning(f"Failed to cache SQL configs: {e}")

        return configs

    async def get_cached_prompt(
        self,
        name: str,
        cliente_id: UUID | None,
        loader: "PromptLoader",
        variables: dict,
    ) -> str:
        """
        Get prompt with Redis caching.

        Caches RAW template (before variable substitution).
        Variables are applied after cache retrieval for freshness.

        Args:
            name: Prompt template name (e.g., "atendente/system/v3")
            cliente_id: Client UUID for client-specific prompts
            loader: PromptLoader instance (injected, not created inside)
            variables: Variables to render into template

        Returns:
            Rendered prompt content
        """
        cache_key = f"prompt:{name}:{cliente_id or 'global'}"

        # Check Redis cache for raw template
        try:
            cached = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached and "content" in cached:
                logger.debug(f"Prompt cache hit for {name}")
                return loader.renderer.render(cached["content"], variables)
        except Exception as e:
            logger.warning(f"Redis cache read failed for prompt: {e}")

        # Load from DB via PromptLoader
        try:
            loaded = await loader.load(name, variables={}, cliente_id=cliente_id)

            # Cache raw template
            try:
                await asyncio.to_thread(
                    self.cache.set_json,
                    cache_key,
                    {"content": loaded.content, "version": loaded.version},
                    self.CACHE_TTL_SECONDS
                )
            except Exception as e:
                logger.warning(f"Failed to cache prompt: {e}")

            return loader.renderer.render(loaded.content, variables)

        except Exception as e:
            logger.warning(f"PromptLoader.load failed for {name}: {e}, using builtin")
            loaded = loader.load_builtin(name, variables)
            return loaded.content

    async def clear_sql_configs_cache(self, cliente_id: UUID) -> None:
        """Clear SQL table configs cache for a client."""
        cache_key = f"sql_configs:{cliente_id}"
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"SQL configs cache invalidated for: {cliente_id}")

    async def clear_prompt_cache(self, name: str, cliente_id: UUID | None = None) -> None:
        """Clear prompt cache for a specific prompt."""
        cache_key = f"prompt:{name}:{cliente_id or 'global'}"
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

        if self._use_supabase:
            try:
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
            except Exception:
                raise
        else:
            return await asyncio.to_thread(
                sqlalchemy_crud.save_integration_config,
                self.db,
                client_id,
                provider,
                config_type,
                enc_client_id,
                enc_client_secret,
                redirect_uri,
                scopes,
            )

    async def get_integration_config(self, client_id: UUID, provider: str):
        """Retrieve integration config and decrypt public values when needed."""
        if self._use_supabase:
            row = await asyncio.to_thread(
                self._supabase_crud.get_integration_config, client_id, provider
            )
            return row
        else:
            row = await asyncio.to_thread(
                sqlalchemy_crud.get_integration_config,
                self.db,
                client_id,
                provider,
            )
            return row

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
        """Encrypt tokens and persist them.

        Args:
            client_id: The cliente UUID
            provider: Provider name (e.g., 'google')
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            token_type: Token type (usually 'Bearer')
            expires_at: Token expiration datetime
            scopes: List of granted scopes
            metadata: Optional metadata dict
            account_email: Email of the Google account (for multi-account support)
            account_name: Friendly name for the account (e.g., 'Personal', 'Work')
            is_default: Whether this should be the default account
        """
        enc_access = await asyncio.to_thread(self._encrypt, access_token)
        enc_refresh = (
            await asyncio.to_thread(self._encrypt, refresh_token)
            if refresh_token
            else None
        )

        if self._use_supabase:
            return await asyncio.to_thread(
                self._supabase_crud.save_integration_tokens,
                client_id,
                provider,
                enc_access,
                enc_refresh,
                token_type,
                expires_at,
                scopes,
                metadata,
                account_email,
                account_name,
                is_default,
            )
        else:
            return await asyncio.to_thread(
                sqlalchemy_crud.save_integration_tokens,
                self.db,
                client_id,
                provider,
                enc_access,
                enc_refresh,
                token_type,
                expires_at,
                scopes,
                metadata,
                account_email,
                account_name,
                is_default,
            )

    class _IntegrationTokenWrapper:
        """Simple wrapper around DB row to expose helper methods used by tools."""

        def __init__(
            self, row, decrypt_fn, context_service=None, cliente_id=None, provider=None
        ):
            # row may be a SQLAlchemy Row or dict-like
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
                    # SQLAlchemy Row mapping
                    try:
                        return self._row._mapping.get(key)
                    except Exception:
                        return None

        def is_valid(self) -> bool:
            """Check if token is still valid (not expired)."""
            expires = self._get("expires_at")
            if not expires:
                # If no expires set, assume valid when access token present
                return bool(self._get("access_token_encrypted"))
            # expires might be string; try parsing
            if isinstance(expires, str):
                try:
                    exp_dt = datetime.fromisoformat(expires)
                except Exception:
                    return True
            elif isinstance(expires, datetime):
                exp_dt = expires
            else:
                return True
            # compare in UTC
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
            access = self._get("access_token_encrypted")
            refresh = self._get("refresh_token_encrypted")
            token_type = self._get("token_type")
            expires_at = self._get("expires_at")
            scopes = self._get("scopes")
            metadata = self._get("metadata")
            account_email = self._get("account_email")
            account_name = self._get("account_name")
            is_default = self._get("is_default")

            dec_access = self._decrypt(access) if access else None
            dec_refresh = self._decrypt(refresh) if refresh else None

            return {
                "access_token": dec_access,
                "refresh_token": dec_refresh,
                "token_type": token_type,
                "expires_at": expires_at,
                "scopes": scopes,
                "metadata": metadata,
                "account_email": account_email,
                "account_name": account_name,
                "is_default": is_default,
            }

    async def _refresh_google_token(
        self,
        client_id: UUID,
        refresh_token: str,
        account_email: str | None = None,
    ) -> Optional["ContextService._IntegrationTokenWrapper"]:
        """Refresh a Google access token using the refresh token.

        Returns a new token wrapper with the refreshed token, or None if refresh fails.
        """
        try:
            # Get the OAuth config to get client_id/secret
            cfg_row = await self.get_integration_config(client_id, "google")
            if not cfg_row:
                logger.error(
                    f"[Token Refresh] No Google config found for cliente {client_id}"
                )
                return None

            client_id = self._decrypt(
                cfg_row.get("client_id_encrypted")
                if isinstance(cfg_row, dict)
                else cfg_row.client_id_encrypted
            )
            client_secret = self._decrypt(
                cfg_row.get("client_secret_encrypted")
                if isinstance(cfg_row, dict)
                else cfg_row.client_secret_encrypted
            )
            redirect_uri = (
                cfg_row.get("redirect_uri")
                if isinstance(cfg_row, dict)
                else cfg_row.redirect_uri
            )
            scopes = (
                cfg_row.get("scopes")
                if isinstance(cfg_row, dict)
                else cfg_row.scopes
            )

            # Use OAuthManager to refresh
            from datetime import timedelta

            from vizu_auth.oauth2.models import OAuthConfig
            from vizu_auth.oauth2.oauth_manager import OAuthManager

            oauth_config = OAuthConfig(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scopes=scopes if isinstance(scopes, list) else [],
            )

            manager = OAuthManager("google")
            new_tokens = await manager.refresh(oauth_config, refresh_token)

            # Calculate new expiry
            expires_at = datetime.now(UTC) + timedelta(
                seconds=new_tokens.expires_in or 3600
            )

            # Save the new tokens
            await self.save_integration_tokens(
                client_id=client_id,
                provider="google",
                access_token=new_tokens.access_token,
                refresh_token=new_tokens.refresh_token
                or refresh_token,  # Keep old if not returned
                token_type=new_tokens.token_type,
                expires_at=expires_at,
                scopes=new_tokens.scope.split() if new_tokens.scope else scopes,
                account_email=account_email,
            )

            logger.info(
                f"[Token Refresh] Successfully refreshed Google token for cliente {client_id}"
            )

            # Return new wrapper
            return await self.get_integration_tokens(
                client_id,
                "google",
                auto_refresh=False,
                account_email=account_email,
            )

        except Exception as e:
            logger.error(
                f"[Token Refresh] Failed to refresh Google token: {e}", exc_info=True
            )
            return None

    async def get_integration_tokens(
        self,
        client_id: UUID,
        provider: str,
        auto_refresh: bool = True,
        account_email: str | None = None,
    ):
        """Retrieve tokens wrapper that exposes is_valid and get_decrypted_tokens.

        Args:
            client_id: The cliente UUID
            provider: Provider name (e.g., 'google')
            auto_refresh: If True and token is expired/expiring, attempt refresh
            account_email: Specific account to get (None = default account)

        Returns:
            _IntegrationTokenWrapper or None if not found
        """
        if self._use_supabase:
            row = await asyncio.to_thread(
                self._supabase_crud.get_integration_tokens,
                client_id,
                provider,
                account_email,
            )
        else:
            row = await asyncio.to_thread(
                sqlalchemy_crud.get_integration_tokens,
                self.db,
                client_id,
                provider,
                account_email,
            )

        if not row:
            return None

        wrapper = ContextService._IntegrationTokenWrapper(
            row,
            self._decrypt,
            context_service=self,
            cliente_id=client_id,
            provider=provider,
        )

        # Auto-refresh if token is expired or expiring soon
        if (
            auto_refresh
            and provider == "google"
            and wrapper.is_expiring_soon(margin_seconds=300)
        ):
            tokens = wrapper.get_decrypted_tokens()
            refresh_token = tokens.get("refresh_token")
            current_account_email = tokens.get("account_email")

            if refresh_token:
                logger.info(
                    f"[Token Refresh] Token expiring soon for {client_id}, attempting refresh..."
                )
                refreshed_wrapper = await self._refresh_google_token(
                    client_id,
                    refresh_token,
                    account_email=current_account_email,
                )
                if refreshed_wrapper:
                    return refreshed_wrapper
                else:
                    logger.warning(
                        "[Token Refresh] Refresh failed, returning possibly expired token"
                    )
            else:
                logger.warning(
                    f"[Token Refresh] No refresh token available for {client_id}"
                )

        return wrapper

    async def list_integration_accounts(
        self,
        client_id: UUID,
        provider: str,
    ) -> list:
        """List all connected accounts for a cliente/provider.

        Returns list of dicts with: id, account_email, account_name, is_default, expires_at, scopes
        """
        if self._use_supabase:
            rows = await asyncio.to_thread(
                self._supabase_crud.list_integration_accounts,
                client_id,
                provider,
            )
        else:
            rows = await asyncio.to_thread(
                sqlalchemy_crud.list_integration_accounts,
                self.db,
                client_id,
                provider,
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
        self,
        client_id: UUID,
        provider: str,
        account_email: str,
    ) -> bool:
        """Set a specific account as the default for a cliente/provider."""
        if self._use_supabase:
            result = await asyncio.to_thread(
                self._supabase_crud.set_default_account,
                client_id,
                provider,
                account_email,
            )
        else:
            result = await asyncio.to_thread(
                sqlalchemy_crud.set_default_account,
                self.db,
                client_id,
                provider,
                account_email,
            )
        return result is not None

    async def revoke_integration(
        self,
        client_id: UUID,
        provider: str,
        account_email: str | None = None,
    ) -> bool:
        """Revoke integration for a specific account or all accounts.

        If account_email is provided, only that account is revoked.
        Otherwise, all accounts and configs for the provider are revoked.
        """
        if self._use_supabase:
            return await asyncio.to_thread(
                self._supabase_crud.revoke_integration,
                client_id,
                provider,
                account_email,
            )
        else:
            return await asyncio.to_thread(
                sqlalchemy_crud.revoke_integration,
                self.db,
                client_id,
                provider,
                account_email,
            )
