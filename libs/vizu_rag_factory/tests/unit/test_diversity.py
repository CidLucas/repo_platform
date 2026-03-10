"""Tests for MMRDiversifier — diversity post-processing for RAG results."""

import pytest
from langchain_core.documents import Document

from vizu_rag_factory.diversity import MMRDiversifier, _get_score, _jaccard, _tokenize

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def same_doc_chunks() -> list[Document]:
    """5 chunks all from the same document — worst-case for diversity."""
    return [
        Document(
            page_content="A empresa atua no setor de logística reversa de embalagens.",
            metadata={
                "document_id": "doc-AAA",
                "combined_score": 0.95,
                "file_name": "sobre_empresa.pdf",
            },
        ),
        Document(
            page_content="A empresa possui 200 funcionários e atua em 5 estados.",
            metadata={
                "document_id": "doc-AAA",
                "combined_score": 0.90,
                "file_name": "sobre_empresa.pdf",
            },
        ),
        Document(
            page_content="A empresa foi fundada em 2010 no estado de São Paulo.",
            metadata={
                "document_id": "doc-AAA",
                "combined_score": 0.85,
                "file_name": "sobre_empresa.pdf",
            },
        ),
        Document(
            page_content="A empresa tem parceria com mais de 100 cooperativas.",
            metadata={
                "document_id": "doc-AAA",
                "combined_score": 0.80,
                "file_name": "sobre_empresa.pdf",
            },
        ),
        Document(
            page_content="A empresa tem receita de R$ 50 milhões por ano.",
            metadata={
                "document_id": "doc-AAA",
                "combined_score": 0.75,
                "file_name": "sobre_empresa.pdf",
            },
        ),
    ]


@pytest.fixture
def diverse_chunks() -> list[Document]:
    """8 chunks from 4 different documents — diverse source material."""
    return [
        Document(
            page_content="A empresa atua no setor de logística reversa de embalagens.",
            metadata={
                "document_id": "doc-AAA",
                "combined_score": 0.95,
                "file_name": "sobre_empresa.pdf",
            },
        ),
        Document(
            page_content="A empresa possui 200 funcionários e atua em 5 estados.",
            metadata={
                "document_id": "doc-AAA",
                "combined_score": 0.90,
                "file_name": "sobre_empresa.pdf",
            },
        ),
        Document(
            page_content="Análise de dados estatística permite identificar tendências de mercado.",
            metadata={
                "document_id": "doc-BBB",
                "combined_score": 0.88,
                "file_name": "analise_dados.pdf",
            },
        ),
        Document(
            page_content="Indicadores de performance KPI são essenciais para tomada de decisão.",
            metadata={
                "document_id": "doc-BBB",
                "combined_score": 0.82,
                "file_name": "analise_dados.pdf",
            },
        ),
        Document(
            page_content="A política de devolução permite troca em até 30 dias.",
            metadata={
                "document_id": "doc-CCC",
                "combined_score": 0.78,
                "file_name": "politicas.pdf",
            },
        ),
        Document(
            page_content="O reembolso é processado em até 5 dias úteis.",
            metadata={
                "document_id": "doc-CCC",
                "combined_score": 0.72,
                "file_name": "politicas.pdf",
            },
        ),
        Document(
            page_content="Preços são atualizados trimestralmente conforme variação cambial.",
            metadata={
                "document_id": "doc-DDD",
                "combined_score": 0.70,
                "file_name": "precos.pdf",
            },
        ),
        Document(
            page_content="Tabela de preços inclui desconto progressivo por volume.",
            metadata={
                "document_id": "doc-DDD",
                "combined_score": 0.65,
                "file_name": "precos.pdf",
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_tokenize_basic(self):
        tokens = _tokenize("Olá mundo, teste 123!")
        assert "olá" in tokens
        assert "mundo" in tokens
        assert "teste" in tokens
        assert "123" in tokens
        # Single chars should be excluded
        assert "," not in tokens

    def test_tokenize_empty(self):
        assert _tokenize("") == set()

    def test_jaccard_identical(self):
        s = {"a", "b", "c"}
        assert _jaccard(s, s) == 1.0

    def test_jaccard_disjoint(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_jaccard_partial(self):
        # {a, b, c} & {b, c, d} = {b, c} → 2/4 = 0.5
        assert _jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5

    def test_jaccard_empty(self):
        assert _jaccard(set(), {"a"}) == 0.0

    def test_get_score_combined(self):
        doc = Document(
            page_content="test",
            metadata={"combined_score": 0.85, "similarity": 0.70},
        )
        assert _get_score(doc) == 0.85

    def test_get_score_rerank_priority(self):
        doc = Document(
            page_content="test",
            metadata={"rerank_score": 0.92, "combined_score": 0.85},
        )
        assert _get_score(doc) == 0.92

    def test_get_score_fallback_to_similarity(self):
        doc = Document(page_content="test", metadata={"similarity": 0.60})
        assert _get_score(doc) == 0.60

    def test_get_score_no_scores(self):
        doc = Document(page_content="test", metadata={})
        assert _get_score(doc) == 0.0


# ---------------------------------------------------------------------------
# MMRDiversifier tests
# ---------------------------------------------------------------------------


class TestMMRDiversifier:
    def test_empty_input(self):
        d = MMRDiversifier()
        assert d.select([], top_k=5) == []

    def test_fewer_than_top_k(self):
        """When fewer docs than top_k, return all with mmr_score metadata."""
        docs = [
            Document(page_content="chunk 1", metadata={"combined_score": 0.9}),
            Document(page_content="chunk 2", metadata={"combined_score": 0.8}),
        ]
        d = MMRDiversifier()
        result = d.select(docs, top_k=5)
        assert len(result) == 2
        assert all("mmr_score" in doc.metadata for doc in result)

    def test_top_k_respected(self, diverse_chunks):
        d = MMRDiversifier()
        result = d.select(diverse_chunks, top_k=4)
        assert len(result) == 4

    def test_same_doc_penalty_promotes_diversity(self, same_doc_chunks):
        """With 5 chunks from the same doc, diversifier should still work."""
        d = MMRDiversifier()
        result = d.select(same_doc_chunks, top_k=3, lambda_=0.5)
        assert len(result) == 3
        # The highest-scored chunk should always be first
        assert result[0].metadata["combined_score"] == 0.95

    def test_diverse_sources_selected(self, diverse_chunks):
        """With λ=0.5, MMR should prefer chunks from different documents."""
        d = MMRDiversifier()
        result = d.select(diverse_chunks, top_k=4, lambda_=0.5)
        doc_ids = {doc.metadata["document_id"] for doc in result}
        # With strong diversity (λ=0.5), we should get chunks from at least 3 docs
        assert len(doc_ids) >= 3, f"Expected >= 3 unique docs, got {doc_ids}"

    def test_pure_relevance_mode(self, diverse_chunks):
        """With λ=1.0, MMR degenerates to pure relevance ordering."""
        d = MMRDiversifier()
        result = d.select(diverse_chunks, top_k=4, lambda_=1.0)
        scores = [_get_score(doc) for doc in result]
        # Should be sorted by descending relevance
        assert scores == sorted(scores, reverse=True)

    def test_mmr_score_in_metadata(self, diverse_chunks):
        d = MMRDiversifier()
        result = d.select(diverse_chunks, top_k=4)
        for doc in result:
            assert "mmr_score" in doc.metadata
            assert isinstance(doc.metadata["mmr_score"], float)

    def test_first_selected_is_most_relevant(self, diverse_chunks):
        """The first document selected should always be the most relevant."""
        d = MMRDiversifier()
        result = d.select(diverse_chunks, top_k=4, lambda_=0.7)
        # doc-AAA with score 0.95 should be first
        assert result[0].metadata["combined_score"] == 0.95

    def test_default_lambda(self, diverse_chunks):
        """Default λ=0.7 should produce reasonable diversity."""
        d = MMRDiversifier()
        result = d.select(diverse_chunks, top_k=4)  # default lambda_=0.7
        doc_ids = {doc.metadata["document_id"] for doc in result}
        # Should get at least 2 different docs even with higher relevance weight
        assert len(doc_ids) >= 2

    def test_single_document(self):
        """Single document should be returned as-is."""
        doc = Document(page_content="only one", metadata={"combined_score": 0.9})
        d = MMRDiversifier()
        result = d.select([doc], top_k=5)
        assert len(result) == 1
        assert result[0].page_content == "only one"
