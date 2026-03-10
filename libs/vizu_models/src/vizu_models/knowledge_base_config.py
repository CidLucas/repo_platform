"""
Knowledge Base Configuration Models

Tabela para armazenar configurações de knowledge bases por cliente.
Permite que cada cliente tenha múltiplas bases de conhecimento com metadados.

Integração com MCP: @mcp.resource("knowledge://...") busca desta tabela.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu


# ── Phase 7: Typed RAG Search Config ────────────────────────


class RagSearchConfig(BaseModel):
    """Typed schema for ``rag_search_config`` in ``available_tools``.

    All fields have sensible defaults so existing clients with partial or
    missing config continue to work unchanged (backward compatibility).

    Example JSON stored in ``clientes_vizu.available_tools.rag_search_config``::

        {
            "top_k": 10,
            "score_threshold": 0.3,
            "rerank": true,
            "rerank_top_k": 15,
            "search_mode": "hybrid",
            "fusion_strategy": "rrf",
            "keyword_weight": 0.4,
            "vector_weight": 0.6,
            "scope": ["platform", "client"],
            "categories": null,
            "themes": null,
            "reranker_type": "cohere",
            "diversity_lambda": 0.7,
            "retrieval_pool_multiplier": 2.0,
            "query_preprocessing": false
        }
    """

    # Core retrieval fields
    top_k: int = 10
    score_threshold: float = 0.3
    rerank: bool = True
    rerank_top_k: int = 15

    # Hybrid retriever fields (Phase 3)
    search_mode: Literal["semantic", "keyword", "hybrid"] = "hybrid"
    fusion_strategy: Literal["rrf", "weighted"] = "rrf"
    keyword_weight: float = 0.4
    vector_weight: float = 0.6
    scope: list[str] = ["platform", "client"]
    categories: list[str] | None = None

    # Chunk-level theme filter — Phase 5 (RAG Overhaul)
    # Filters by enriched metadata theme (e.g. "financial_reporting", "product_knowledge")
    # NULL means no filter — all themes are searched.
    themes: list[str] | None = None

    # Reranker selection (Phase 4 / Phase 7)
    reranker_type: Literal["cohere", "llm", "cross-encoder"] = "cohere"

    # Query preprocessing — Phase 3 (RAG Overhaul)
    # Disabled by default: the agent system prompt already instructs the LLM to
    # rewrite queries before calling the RAG tool, avoiding an extra LLM call.
    # Enable for non-agent (direct API) use cases where no upstream rewriting exists.
    query_preprocessing: bool = False

    # Diversity (MMR) settings — Phase 8
    diversity_lambda: float = 0.7
    retrieval_pool_multiplier: float = 2.0


class KnowledgeBaseConfigBase(SQLModel):
    """Base fields for knowledge base configuration."""

    name: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Nome identificador da base de conhecimento (ex: 'servicos', 'faq', 'produtos')",
    )

    description: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="Descrição do conteúdo da base",
    )

    collection_name: str | None = Field(
        default=None,
        sa_column=Column(String(100), nullable=True),
        description="DEPRECATED: anteriormente nome da collection no Qdrant. Isolação agora é por client_id no schema vector_db.",
    )

    embedding_model: str = Field(
        default="embed-multilingual-light-v3.0",
        sa_column=Column(String(100), nullable=False),
        description="Modelo de embedding usado (Cohere embed-multilingual-light-v3.0 via process-document EF)",
    )

    chunk_size: int = Field(
        default=512,
        sa_column=Column(Integer, nullable=False),
        description="Tamanho do chunk para splitting",
    )

    chunk_overlap: int = Field(
        default=50,
        sa_column=Column(Integer, nullable=False),
        description="Overlap entre chunks",
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default="true"),
        description="Se esta base está ativa para busca",
    )

    metadata_schema: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Schema esperado dos metadados dos documentos",
    )

    search_config: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Configurações de busca (top_k, score_threshold, etc.)",
    )


class KnowledgeBaseConfig(KnowledgeBaseConfigBase, table=True):
    """
    Tabela de configurações de knowledge bases.

    Cada cliente pode ter múltiplas bases de conhecimento.
    """

    __tablename__ = "knowledge_base_config"

    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    client_id: uuid.UUID = Field(
        sa_column=Column(
            pgUUID(as_uuid=True),
            ForeignKey("clientes_vizu.client_id"),
            nullable=False,
            index=True,
        )
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    # Stats (atualizado por jobs de sync)
    document_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
        description="Número de documentos na base",
    )

    last_sync_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime),
        description="Última sincronização (anteriormente com Qdrant, agora vector_db)",
    )

    # Relationship
    cliente_vizu: Optional["ClienteVizu"] = Relationship()


class KnowledgeBaseConfigCreate(KnowledgeBaseConfigBase):
    """Schema para criar uma nova base de conhecimento."""

    client_id: uuid.UUID


class KnowledgeBaseConfigRead(KnowledgeBaseConfigBase):
    """Schema para leitura de base de conhecimento."""

    id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    document_count: int
    last_sync_at: datetime | None = None


class KnowledgeBaseConfigUpdate(SQLModel):
    """Schema para atualizar uma base de conhecimento."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    search_config: dict | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
