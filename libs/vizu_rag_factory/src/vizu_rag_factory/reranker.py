"""Optional reranking step for RAG retrieval results.

Provides LLM-based reranking using the vizu_llm_service to score
query-document relevance more precisely than cosine similarity alone.

Usage:
    reranker = LLMReranker(llm=get_model(tier="FAST"))
    reranked = await reranker.arerank(query, docs, top_k=3)
"""

import asyncio
import logging
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

RERANK_PROMPT = """Rate how relevant and useful this document passage is for answering the given question.
Score from 0 to 10 where:
- 0 = completely irrelevant
- 5 = somewhat relevant but not directly useful
- 10 = highly relevant and directly answers the question

Respond with ONLY a single integer number, nothing else.

Question: {question}

Passage: {passage}

Score:"""


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
        scored = await asyncio.gather(
            *[self._score_one(question, doc) for doc in documents]
        )

        # Sort by reranker score descending
        scored.sort(key=lambda s: s.rerank_score, reverse=True)

        # Build result with enriched metadata
        result: list[Document] = []
        for s in scored[:top_k]:
            doc = s.document
            doc.metadata["rerank_score"] = s.rerank_score
            result.append(doc)

        logger.debug(
            f"[Reranker] Top scores: {[f'{s.rerank_score:.1f}' for s in scored[:top_k or len(scored)]]}"
        )
        return result

    def rerank(
        self,
        question: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        """Sync wrapper for arerank — runs in asyncio event loop."""
        return asyncio.get_event_loop().run_until_complete(
            self.arerank(question, documents, top_k)
        )
