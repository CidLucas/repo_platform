"""Maximal Marginal Relevance (MMR) diversity post-processing for RAG results.

After retrieval (and optional reranking), results often cluster around the same
document or topic.  ``MMRDiversifier`` iteratively selects chunks that balance
**relevance** to the query with **novelty** relative to already-selected chunks.

The similarity between chunks is computed using a lightweight heuristic that
combines:
1. **Document-ID penalty** — chunks from the same document are considered highly
   similar (penalty = 0.8).
2. **Jaccard word-set similarity** — fast overlap measure on token sets of
   ``page_content``.

This avoids any extra embedding API calls or heavy model inference while still
producing meaningfully diverse result sets.

Usage::

    diversifier = MMRDiversifier()
    diverse_docs = diversifier.select(docs, top_k=10, lambda_=0.7)
"""

from __future__ import annotations

import logging
import re
from typing import Sequence

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Penalty applied when two chunks share the same document_id.
# 0.8 means "80% similar by default" even before text overlap is considered.
_SAME_DOC_PENALTY = 0.8


def _tokenize(text: str) -> set[str]:
    """Return a lowered set of alphanumeric tokens (≥2 chars)."""
    return {t for t in re.findall(r"\w{2,}", text.lower())}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _chunk_similarity(
    doc_a: Document,
    doc_b: Document,
    tokens_a: set[str],
    tokens_b: set[str],
) -> float:
    """Compute similarity between two chunks.

    Returns a float in [0, 1] where 1 = identical.
    Uses max(same_doc_penalty, jaccard_similarity) so that:
    - Chunks from the same document always get a high baseline similarity.
    - Chunks from different documents are compared by text overlap.
    """
    same_doc = doc_a.metadata.get("document_id") is not None and doc_a.metadata.get(
        "document_id"
    ) == doc_b.metadata.get("document_id")
    text_sim = _jaccard(tokens_a, tokens_b)

    if same_doc:
        return max(_SAME_DOC_PENALTY, text_sim)
    return text_sim


def _get_score(doc: Document) -> float:
    """Extract the best available relevance score from a document's metadata.

    Priority: rerank_score (normalized) > combined_score > similarity.
    """
    # rerank_score is 0-10 (LLM) or arbitrary float (cross-encoder); normalize
    rerank = doc.metadata.get("rerank_score")
    if rerank is not None:
        # Cross-encoder scores can be negative; clamp to [0, 1]
        return max(0.0, min(1.0, float(rerank)))

    combined = doc.metadata.get("combined_score")
    if combined is not None:
        return float(combined)

    return float(doc.metadata.get("similarity", 0.0))


class MMRDiversifier:
    """Select documents using Maximal Marginal Relevance (MMR).

    At each iteration, the next document is chosen to maximize::

        λ · relevance(d_i) − (1 − λ) · max_{d_j ∈ S} similarity(d_i, d_j)

    where *S* is the set of already-selected documents.

    Args:
        same_doc_penalty: Similarity floor for chunks sharing the same
            ``document_id``.  Default 0.8.
    """

    def __init__(self, same_doc_penalty: float = _SAME_DOC_PENALTY):
        self.same_doc_penalty = same_doc_penalty

    def select(
        self,
        documents: Sequence[Document],
        top_k: int = 10,
        lambda_: float = 0.7,
    ) -> list[Document]:
        """Return up to *top_k* documents maximizing relevance + diversity.

        Args:
            documents: Candidate documents (already retrieved, optionally reranked).
            top_k: Maximum number of documents to return.
            lambda_: Trade-off parameter.  1.0 = pure relevance (no diversity),
                0.0 = pure diversity (ignores scores).  Recommended: 0.5 – 0.8.

        Returns:
            A list of up to *top_k* :class:`Document` objects with an added
            ``mmr_score`` key in their metadata.
        """
        if not documents:
            return []

        candidates = list(documents)
        n = min(top_k, len(candidates))

        if n >= len(candidates):
            # Nothing to diversify — return all
            for doc in candidates:
                doc.metadata["mmr_score"] = _get_score(doc)
            return candidates

        # Pre-compute token sets for all candidates
        token_cache: dict[int, set[str]] = {
            id(doc): _tokenize(doc.page_content) for doc in candidates
        }

        selected: list[Document] = []
        remaining = list(candidates)

        logger.debug(
            f"[MMRDiversifier] Selecting {n} from {len(candidates)} candidates (λ={lambda_})"
        )

        for _step in range(n):
            best_idx = -1
            best_mmr = float("-inf")

            for i, cand in enumerate(remaining):
                relevance = _get_score(cand)

                # Max similarity to any already-selected doc
                if selected:
                    max_sim = max(
                        _chunk_similarity(
                            cand,
                            sel,
                            token_cache[id(cand)],
                            token_cache[id(sel)],
                        )
                        for sel in selected
                    )
                else:
                    max_sim = 0.0

                mmr = lambda_ * relevance - (1 - lambda_) * max_sim

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = i

            # Select the winner
            winner = remaining.pop(best_idx)
            winner.metadata["mmr_score"] = best_mmr
            selected.append(winner)

        logger.debug(
            f"[MMRDiversifier] Selected {len(selected)} docs — "
            f"unique documents: {len({d.metadata.get('document_id') for d in selected})}"
        )

        return selected
