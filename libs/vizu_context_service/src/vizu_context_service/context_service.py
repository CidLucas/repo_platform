import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

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

    async def get_client_context_by_api_key(
        self, api_key: str
    ) -> VizuClientContext | None:
        """
        Busca o contexto completo do cliente usando a API Key.
        1. Busca ID no DB (leve).
        2. Chama get_client_context_by_id (que tem cache pesado).
        """
        try:
            if self._use_supabase:
                # Supabase SDK mode
                cliente_data = await asyncio.to_thread(
                    self._supabase_crud.get_cliente_vizu_by_api_key, api_key
                )
                if not cliente_data:
                    return None
                cliente_id = UUID(cliente_data["id"])
            else:
                # Legacy SQLAlchemy mode
                cliente_db = await asyncio.to_thread(
                    sqlalchemy_crud.get_cliente_vizu_by_api_key, self.db, api_key
                )
                if not cliente_db:
                    return None
                cliente_id = cliente_db.id

            # 2. Com o ID em mãos, buscamos o contexto completo (com cache)
            return await self.get_client_context_by_id(cliente_id)

        except Exception as e:
            logger.error(f"Erro na autenticação por API Key: {e}", exc_info=True)
            return None

    def _build_context_from_dict(self, data: dict) -> VizuClientContext:
        """Build VizuClientContext from Supabase response dict."""
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

            if not isinstance(parsed, (list, tuple)):
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
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            api_key=data["api_key"],
            nome_empresa=data["nome_empresa"],
            tipo_cliente=data["tipo_cliente"],
            tier=data["tier"],
            prompt_base=data.get("prompt_base") or "Você é um assistente útil.",
            horario_funcionamento=data.get("horario_funcionamento") or {},
            enabled_tools=enabled_tools,
            collection_rag=data.get("collection_rag", "default_collection"),
            credenciais=[],
        )

    def _build_context_from_orm(self, cliente_db) -> VizuClientContext:
        """Build VizuClientContext from SQLAlchemy ORM object."""
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
            id=cliente_db.id,
            api_key=cliente_db.api_key,
            nome_empresa=cliente_db.nome_empresa,
            tipo_cliente=cliente_db.tipo_cliente,
            tier=cliente_db.tier,
            prompt_base=getattr(cliente_db, "prompt_base", None)
            or "Você é um assistente útil.",
            horario_funcionamento=getattr(cliente_db, "horario_funcionamento", {})
            or {},
            enabled_tools=deduped,
            collection_rag=getattr(cliente_db, "collection_rag", "default_collection"),
            credenciais=[],
        )

    async def get_client_context_by_id(
        self, cliente_id: UUID
    ) -> VizuClientContext | None:
        """
        Recupera o contexto completo (Cliente + Configurações), usando Cache Redis.
        Também configura o contexto RLS para garantir isolamento de dados.
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
        cliente_vizu_id: UUID,
        provider: str,
        config_type: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list,
    ):
        """Encrypt and persist integration client credentials."""
        enc_client_id = await asyncio.to_thread(self._encrypt, client_id)
        enc_client_secret = await asyncio.to_thread(self._encrypt, client_secret)

        if self._use_supabase:
            try:
                return await asyncio.to_thread(
                    self._supabase_crud.save_integration_config,
                    cliente_vizu_id,
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
                cliente_vizu_id,
                provider,
                config_type,
                enc_client_id,
                enc_client_secret,
                redirect_uri,
                scopes,
            )

    async def get_integration_config(self, cliente_vizu_id: UUID, provider: str):
        """Retrieve integration config and decrypt public values when needed."""
        if self._use_supabase:
            row = await asyncio.to_thread(
                self._supabase_crud.get_integration_config, cliente_vizu_id, provider
            )
            return row
        else:
            row = await asyncio.to_thread(
                sqlalchemy_crud.get_integration_config,
                self.db,
                cliente_vizu_id,
                provider,
            )
            return row

    async def save_integration_tokens(
        self,
        cliente_vizu_id: UUID,
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
            cliente_vizu_id: The cliente UUID
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
                cliente_vizu_id,
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
                cliente_vizu_id,
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
        cliente_vizu_id: UUID,
        refresh_token: str,
        account_email: str | None = None,
    ) -> Optional["ContextService._IntegrationTokenWrapper"]:
        """Refresh a Google access token using the refresh token.

        Returns a new token wrapper with the refreshed token, or None if refresh fails.
        """
        try:
            # Get the OAuth config to get client_id/secret
            cfg_row = await self.get_integration_config(cliente_vizu_id, "google")
            if not cfg_row:
                logger.error(
                    f"[Token Refresh] No Google config found for cliente {cliente_vizu_id}"
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
                cliente_vizu_id=cliente_vizu_id,
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
                f"[Token Refresh] Successfully refreshed Google token for cliente {cliente_vizu_id}"
            )

            # Return new wrapper
            return await self.get_integration_tokens(
                cliente_vizu_id,
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
        cliente_vizu_id: UUID,
        provider: str,
        auto_refresh: bool = True,
        account_email: str | None = None,
    ):
        """Retrieve tokens wrapper that exposes is_valid and get_decrypted_tokens.

        Args:
            cliente_vizu_id: The cliente UUID
            provider: Provider name (e.g., 'google')
            auto_refresh: If True and token is expired/expiring, attempt refresh
            account_email: Specific account to get (None = default account)

        Returns:
            _IntegrationTokenWrapper or None if not found
        """
        if self._use_supabase:
            row = await asyncio.to_thread(
                self._supabase_crud.get_integration_tokens,
                cliente_vizu_id,
                provider,
                account_email,
            )
        else:
            row = await asyncio.to_thread(
                sqlalchemy_crud.get_integration_tokens,
                self.db,
                cliente_vizu_id,
                provider,
                account_email,
            )

        if not row:
            return None

        wrapper = ContextService._IntegrationTokenWrapper(
            row,
            self._decrypt,
            context_service=self,
            cliente_id=cliente_vizu_id,
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
                    f"[Token Refresh] Token expiring soon for {cliente_vizu_id}, attempting refresh..."
                )
                refreshed_wrapper = await self._refresh_google_token(
                    cliente_vizu_id,
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
                    f"[Token Refresh] No refresh token available for {cliente_vizu_id}"
                )

        return wrapper

    async def list_integration_accounts(
        self,
        cliente_vizu_id: UUID,
        provider: str,
    ) -> list:
        """List all connected accounts for a cliente/provider.

        Returns list of dicts with: id, account_email, account_name, is_default, expires_at, scopes
        """
        if self._use_supabase:
            rows = await asyncio.to_thread(
                self._supabase_crud.list_integration_accounts,
                cliente_vizu_id,
                provider,
            )
        else:
            rows = await asyncio.to_thread(
                sqlalchemy_crud.list_integration_accounts,
                self.db,
                cliente_vizu_id,
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
        cliente_vizu_id: UUID,
        provider: str,
        account_email: str,
    ) -> bool:
        """Set a specific account as the default for a cliente/provider."""
        if self._use_supabase:
            result = await asyncio.to_thread(
                self._supabase_crud.set_default_account,
                cliente_vizu_id,
                provider,
                account_email,
            )
        else:
            result = await asyncio.to_thread(
                sqlalchemy_crud.set_default_account,
                self.db,
                cliente_vizu_id,
                provider,
                account_email,
            )
        return result is not None

    async def revoke_integration(
        self,
        cliente_vizu_id: UUID,
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
                cliente_vizu_id,
                provider,
                account_email,
            )
        else:
            return await asyncio.to_thread(
                sqlalchemy_crud.revoke_integration,
                self.db,
                cliente_vizu_id,
                provider,
                account_email,
            )
