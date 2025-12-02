import asyncio
import logging
from uuid import UUID
from typing import Optional

# Suporte a ambos os modos: SQLAlchemy (legado) e Supabase SDK (novo)
try:
    from vizu_supabase_client import get_supabase_client, SupabaseCRUD
    from vizu_supabase_client.client import set_rls_context as supabase_set_rls
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import text
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
        use_supabase: bool = True
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
                    text("SELECT set_config('app.current_cliente_id', :cliente_id, false)"),
                    {"cliente_id": str(cliente_id)}
                )
                logger.debug(f"RLS context set via SQLAlchemy for: {cliente_id}")
            except Exception as e:
                logger.warning(f"Could not set RLS context (SQLAlchemy): {e}")

    async def get_client_context_by_api_key(self, api_key: str) -> Optional[VizuClientContext]:
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
        return VizuClientContext(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            api_key=data["api_key"],
            nome_empresa=data["nome_empresa"],
            tipo_cliente=data["tipo_cliente"],
            tier=data["tier"],
            prompt_base=data.get("prompt_base") or "Você é um assistente útil.",
            horario_funcionamento=data.get("horario_funcionamento") or {},
            ferramenta_rag_habilitada=bool(data.get("ferramenta_rag_habilitada", False)),
            ferramenta_sql_habilitada=bool(data.get("ferramenta_sql_habilitada", False)),
            collection_rag=data.get("collection_rag", "default_collection"),
            credenciais=[]
        )

    def _build_context_from_orm(self, cliente_db) -> VizuClientContext:
        """Build VizuClientContext from SQLAlchemy ORM object."""
        return VizuClientContext(
            id=cliente_db.id,
            api_key=cliente_db.api_key,
            nome_empresa=cliente_db.nome_empresa,
            tipo_cliente=cliente_db.tipo_cliente,
            tier=cliente_db.tier,
            prompt_base=getattr(cliente_db, "prompt_base", None) or "Você é um assistente útil.",
            horario_funcionamento=getattr(cliente_db, "horario_funcionamento", {}) or {},
            ferramenta_rag_habilitada=bool(getattr(cliente_db, "ferramenta_rag_habilitada", False)),
            ferramenta_sql_habilitada=bool(getattr(cliente_db, "ferramenta_sql_habilitada", False)),
            collection_rag=getattr(cliente_db, "collection_rag", "default_collection"),
            credenciais=[]
        )

    async def get_client_context_by_id(self, cliente_id: UUID) -> Optional[VizuClientContext]:
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
                    logger.warning(f"Cache corrompido para {cliente_id}, invalidando... Erro: {e}")
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
                    logger.warning(f"Cliente {cliente_id} não encontrado no banco (Supabase).")
                    return None
                client_context = self._build_context_from_dict(cliente_data)
            else:
                # Legacy SQLAlchemy mode
                cliente_db = await asyncio.to_thread(
                    sqlalchemy_crud.get_cliente_vizu_by_id, self.db, cliente_id
                )
                if not cliente_db:
                    logger.warning(f"Cliente {cliente_id} não encontrado no banco (SQLAlchemy).")
                    return None
                client_context = self._build_context_from_orm(cliente_db)

            # --- 3. SALVAR NO CACHE ---
            await asyncio.to_thread(
                self.cache.set_json,
                key=cache_key,
                data=client_context,
                ttl_seconds=self.CACHE_TTL_SECONDS
            )

            return client_context

        except Exception as e:
            logger.error(f"Erro crítico ao montar contexto para {cliente_id}: {e}", exc_info=True)
            return None

    async def clear_context_cache(self, cliente_id: UUID) -> None:
        """Remove o contexto do cache (útil após updates no cliente)."""
        cache_key = self._get_cache_key(cliente_id)
        await asyncio.to_thread(self.cache.delete, cache_key)
        logger.info(f"Cache invalidado para: {cliente_id}")