"""Optional reranking step for RAG retrieval results.

Provides two reranking strategies:

1. **LLMReranker** — Uses a fast LLM tier to score query-document relevance
   (lightweight, no extra model download, higher latency per doc).
2. **CrossEncoderReranker** — Uses ``bge-reranker-v2-m3`` cross-encoder model
   for fast, accurate relevance scoring (requires ``sentence-transformers``).

Usage:
    # LLM-based (no extra deps)
    reranker = LLMReranker(llm=get_model(tier="FAST"))
    reranked = await reranker.arerank(query, docs, top_k=3)

    # Cross-encoder (faster per-doc, better accuracy)
    reranker = CrossEncoderReranker()
    reranked = await reranker.arerank(query, docs, top_k=3)
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel

from vizu_prompt_management.templates import RAG_RERANK_PROMPT

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

# Centralized in vizu_prompt_management — convert Jinja2 {{ var }} to Python .format() {var}
RERANK_PROMPT = RAG_RERANK_PROMPT.content.replace("{{ question }}", "{question}").replace(
    "{{ passage }}", "{passage}"
)


@dataclass
class ScoredDocument:
    """A document with both vector similarity and reranker relevance scores."""

    document: Document
    rerank_score: float


class LLMReranker:
    """Reranks retrieved documents using an LLM to score query-passage relevance.

    This is a lightweight alternative to a full cross-encoder model.
    It uses a fast LLM tier to score each document against the query,
    then re-sorts by the LLM relevance score.
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def _score_one(self, question: str, doc: Document) -> ScoredDocument:
        """Score a single document against the question."""
        # Truncate very long passages to avoid exhausting context
        passage = doc.page_content[:1500]
        try:
            prompt = RERANK_PROMPT.format(question=question, passage=passage)
            result = await self.llm.ainvoke(prompt)
            text = result.content.strip() if hasattr(result, "content") else str(result).strip()
            # Parse integer score
            score = float(text.split()[0])
            score = max(0.0, min(10.0, score))
        except Exception as e:
            logger.warning(f"[Reranker] Failed to score document: {e}, using similarity fallback")
            score = doc.metadata.get("similarity", 0.5) * 10
        return ScoredDocument(document=doc, rerank_score=score)

    async def arerank(
        self,
        question: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        """Rerank documents by LLM-scored relevance. Returns top_k most relevant.

        Args:
            question: The user's search query.
            documents: Retrieved documents from vector search.
            top_k: Number of documents to return. None = return all, re-sorted.

        Returns:
            Documents re-ordered by relevance, with ``rerank_score`` added to metadata.
        """
        if not documents:
            return []

        if len(documents) <= 1:
            return documents

        logger.debug(f"[Reranker] Scoring {len(documents)} documents for: '{question[:80]}...'")

        # Score all documents concurrently
        scored = await asyncio.gather(*[self._score_one(question, doc) for doc in documents])

        # Sort by reranker score descending
        scored.sort(key=lambda s: s.rerank_score, reverse=True)

        # Build result with enriched metadata
        result: list[Document] = []
        for s in scored[:top_k]:
            doc = s.document
            doc.metadata["rerank_score"] = s.rerank_score
            result.append(doc)

        logger.debug(
            f"[Reranker] Top scores: {[f'{s.rerank_score:.1f}' for s in scored[: top_k or len(scored)]]}"
        )
        return result

    def rerank(
        self,
        question: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        """Sync wrapper for arerank — runs in a new event loop if needed."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in an async context — run scoring synchronously
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.arerank(question, documents, top_k)).result()
        return asyncio.run(self.arerank(question, documents, top_k))


# ---------------------------------------------------------------------------
# Module-level singleton for CrossEncoder model (lazy-loaded, thread-safe)
# ---------------------------------------------------------------------------
_cross_encoder_lock = threading.Lock()
_cross_encoder_instance: CrossEncoder | None = None

DEFAULT_CROSS_ENCODER_MODEL = "BAAI/bge-reranker-v2-m3"


def _get_cross_encoder(
    model_name: str = DEFAULT_CROSS_ENCODER_MODEL, device: str = "cpu"
) -> CrossEncoder:
    """Return a module-level singleton ``CrossEncoder`` instance.

    The model (~1.1 GB) is loaded on first call and reused for all
    subsequent rerank requests.  Loading is thread-safe.
    """
    global _cross_encoder_instance  # noqa: PLW0603
    if _cross_encoder_instance is None:
        with _cross_encoder_lock:
            # Double-checked locking
            if _cross_encoder_instance is None:
                from sentence_transformers import CrossEncoder as _CrossEncoder

                logger.info(
                    f"[CrossEncoderReranker] Loading model '{model_name}' on device='{device}' "
                    "(first call — subsequent calls will reuse cached model)"
                )
                _cross_encoder_instance = _CrossEncoder(model_name, device=device)
                logger.info("[CrossEncoderReranker] Model loaded successfully")
    return _cross_encoder_instance


class CrossEncoderReranker:
    """Reranks documents using a cross-encoder model (``bge-reranker-v2-m3``).

    Multilingual, supports PT-BR natively, 278M params.
    Much faster and cheaper than LLM-based reranking per query.

    The underlying ``CrossEncoder`` model is loaded lazily as a module-level
    singleton — the first ``rerank`` / ``arerank`` call triggers the download
    (if not cached) and load; all subsequent calls reuse the same instance.

    Args:
        model_name: HuggingFace model identifier (default ``BAAI/bge-reranker-v2-m3``).
        device: Torch device string (``"cpu"``, ``"cuda"``, ``"mps"``).
        max_passage_length: Passage truncation length in characters (default 1500).
    """

    def __init__(
        self,
        model_name: str = DEFAULT_CROSS_ENCODER_MODEL,
        device: str = "cpu",
        max_passage_length: int = 1500,
    ):
        self.model_name = model_name
        self.device = device
        self.max_passage_length = max_passage_length

    @property
    def _model(self) -> CrossEncoder:
        """Lazy accessor for the singleton cross-encoder model."""
        return _get_cross_encoder(self.model_name, self.device)

    async def arerank(
        self,
        question: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        """Asynchronously rerank ``documents`` by cross-encoder relevance.

        Inference is executed in a thread-pool to avoid blocking the event loop.

        Args:
            question: The user's search query.
            documents: Retrieved documents from vector / hybrid search.
            top_k: Number of top documents to return.  ``None`` returns all, re-sorted.

        Returns:
            Documents re-ordered by cross-encoder score, with ``rerank_score``
            added to each document's metadata.
        """
        if not documents:
            return []
        if len(documents) <= 1:
            return documents

        logger.debug(
            f"[CrossEncoderReranker] Scoring {len(documents)} documents for: '{question[:80]}...'"
        )

        # Cross-encoder expects list of [query, passage] pairs
        pairs = [[question, doc.page_content[: self.max_passage_length]] for doc in documents]

        # Run model inference in a thread pool so we don't block the event loop
        scores = await asyncio.to_thread(self._model.predict, pairs)

        # Pair documents with scores, sort descending
        scored = sorted(
            zip(documents, scores, strict=False),
            key=lambda x: float(x[1]),
            reverse=True,
        )

        result: list[Document] = []
        for doc, score in scored[:top_k]:
            doc.metadata["rerank_score"] = float(score)
            result.append(doc)

        logger.debug(
            f"[CrossEncoderReranker] Top scores: "
            f"{[f'{float(s):.4f}' for _, s in scored[: top_k or len(scored)]]}"
        )
        return result

    def rerank(
        self,
        question: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        """Sync wrapper for ``arerank``.

        If an event loop is already running (e.g. inside LangChain's sync path),
        this falls back to running inference directly on the calling thread.
        """
        if not documents:
            return []
        if len(documents) <= 1:
            return documents

        logger.debug(
            f"[CrossEncoderReranker] Sync scoring {len(documents)} documents for: "
            f"'{question[:80]}...'"
        )

        pairs = [[question, doc.page_content[: self.max_passage_length]] for doc in documents]
        scores = self._model.predict(pairs)

        scored = sorted(
            zip(documents, scores, strict=False),
            key=lambda x: float(x[1]),
            reverse=True,
        )

        result: list[Document] = []
        for doc, score in scored[:top_k]:
            doc.metadata["rerank_score"] = float(score)
            result.append(doc)

        logger.debug(
            f"[CrossEncoderReranker] Sync top scores: "
            f"{[f'{float(s):.4f}' for _, s in scored[: top_k or len(scored)]]}"
        )
        return result
