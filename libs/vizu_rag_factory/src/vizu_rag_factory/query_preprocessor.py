"""Query preprocessor for RAG retrieval optimization.

Rewrites user queries before embedding + keyword search to improve
retrieval quality.  Uses a fast LLM tier to:

1. Decompose multi-topic queries into key concepts
2. Expand with synonyms and related terms
3. Remove conversational filler
4. Produce a search-optimized query string

The preprocessor is optional and can be disabled per-client via
``RagSearchConfig.query_preprocessing = False``.
"""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from vizu_prompt_management.templates import RAG_QUERY_REWRITE_PROMPT

logger = logging.getLogger(__name__)

# Convert Jinja2 ``{{ query }}`` to plain Python format string
_SYSTEM_PROMPT = RAG_QUERY_REWRITE_PROMPT.content


class QueryPreprocessor:
    """Rewrites user queries for optimal RAG retrieval.

    Uses a fast LLM to decompose, expand, and clean user queries so
    the downstream embedding and keyword search return better candidates.

    Parameters
    ----------
    llm:
        A chat model instance (ideally tier=FAST for low latency).
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm

    # -- public API ----------------------------------------------------------

    async def arewrite(self, query: str) -> str:
        """Asynchronously rewrite *query* for retrieval."""
        if not query or not query.strip():
            return query
        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=query),
                ],
            )
            rewritten = response.content.strip()
            if not rewritten:
                logger.warning("Query preprocessor returned empty — using original query")
                return query
            return rewritten
        except Exception:
            logger.exception("Query preprocessing failed — using original query")
            return query

    def rewrite(self, query: str) -> str:
        """Synchronously rewrite *query* for retrieval."""
        if not query or not query.strip():
            return query
        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=query),
                ],
            )
            rewritten = response.content.strip()
            if not rewritten:
                logger.warning("Query preprocessor returned empty — using original query")
                return query
            return rewritten
        except Exception:
            logger.exception("Query preprocessing failed — using original query")
            return query
