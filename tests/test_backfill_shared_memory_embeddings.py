# tests/test_backfill_shared_memory_embeddings.py
"""Testes do script de backfill (T3.1f Seção 6).

Testa as funções do backfill_shared_memory_embeddings.py:
- count_rows_without_embedding
- backfill (dry_run, update, skip existing, batching)
"""

import sys
from unittest.mock import MagicMock

import pytest


# ── Load backfill functions with proper namespace ────────────────


def _load_backfill_functions():
    import pathlib
    import logging
    import time as time_module

    script_path = (
        pathlib.Path(__file__).parent.parent
        / "scripts" / "backfill_shared_memory_embeddings.py"
    )
    source = script_path.read_text()

    # Build a full namespace with needed globals
    namespace = {
        "__name__": "backfill_test",
        "logging": logging,
        "logger": logging.getLogger("test_backfill"),
        "time": time_module,
        "MAX_BATCH_SIZE": 96,
    }

    # Execute the entire source in the namespace (skip the imports at top)
    lines = source.split("\n")
    exec_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#!/usr") or stripped.startswith("# -"):
            continue
        if "load_dotenv" in stripped or "sys.path.insert" in stripped:
            continue
        if "ROOT_DIR" in stripped and "Path" in stripped:
            continue
        if stripped.startswith("from dotenv"):
            continue
        if "from blu_supabase_client" in stripped:
            continue
        if "from blu_llm_service" in stripped:
            continue
        exec_lines.append(line)

    exec("\n".join(exec_lines), namespace)

    return (
        namespace["_build_embedding_text"],
        namespace["count_rows_without_embedding"],
        namespace["backfill"],
    )


_build_embedding_text, count_rows_without_embedding, backfill = _load_backfill_functions()


# ── Override root conftest cleanup (no real Supabase) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — no real Supabase teardown."""
    yield


# ── Helper: build a count chain mock ──────────────────────────────


def _make_count_chain(count: int):
    """Create a mock chain for count_rows_without_embedding."""
    count_result = MagicMock()
    count_result.count = count
    chain = MagicMock()
    chain.is_.return_value = chain
    chain.execute.return_value = count_result
    return chain


def _make_page_chain(rows: list[dict]):
    """Create a mock chain for a single pagination query."""
    page_result = MagicMock()
    page_result.data = rows
    chain = MagicMock()
    chain.is_.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.execute.return_value = page_result
    return chain


def _make_update_chain():
    """Create a mock chain for the update call."""
    chain = MagicMock()
    chain.eq.return_value = chain
    chain.execute.return_value = MagicMock(data={"id": "updated"})
    return chain


# ── Tests ─────────────────────────────────────────────────────────


class TestBackfillScript:
    """Testes do script de backfill (T3.1f Seção 6)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_embedder(self):
        embedder = MagicMock()
        embedder.embed_documents.return_value = [[0.1] * 384]
        embedder.MODEL = "embed-multilingual-light-v3.0"
        embedder.DIMENSIONS = 384
        return embedder

    # ── 1. test_dry_run_counts_only ──────────────────────────────

    def test_dry_run_counts_only(self, mock_db):
        """Dry-run não modifica — apenas conta."""
        mock_db.table.return_value.select.return_value = _make_count_chain(50)

        stats = backfill(db=mock_db, embedder=None, dry_run=True)

        assert stats["total"] == 50
        assert stats["updated"] == 0
        assert stats["failed"] == 0
        assert stats["batches"] == 1  # ceil(50/96) = 1

    def test_dry_run_counts_only_zero(self, mock_db):
        """Dry-run com zero rows."""
        mock_db.table.return_value.select.return_value = _make_count_chain(0)

        stats = backfill(db=mock_db, embedder=None, dry_run=True)

        assert stats["total"] == 0
        assert stats["batches"] == 0

    # ── 2. test_backfill_updates_null_embeddings ──────────────────

    def test_backfill_updates_null_embeddings(self, mock_db, mock_embedder):
        """Rows sem embedding → com embedding após backfill."""
        row = {
            "id": "row-1",
            "entity_type": "client",
            "entity_name": "acme",
            "key": "pref",
            "value": {"canal": "email"},
            "category": "preference",
        }

        call_count = [0]

        def select_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_count_chain(1)
            elif call_count[0] == 2:
                return _make_page_chain([row])
            else:
                return _make_page_chain([])  # end loop

        mock_db.table.return_value.select.side_effect = select_side_effect
        mock_db.table.return_value.update.return_value = _make_update_chain()

        stats = backfill(db=mock_db, embedder=mock_embedder, dry_run=False)

        assert stats["total"] == 1
        assert stats["updated"] == 1
        assert stats["failed"] == 0
        assert stats["batches"] == 1

    # ── 3. test_backfill_skips_existing_embeddings ────────────────

    def test_backfill_skips_existing_embeddings(self, mock_db, mock_embedder):
        """Rows já com embedding não são processadas (count=0)."""
        mock_db.table.return_value.select.return_value = _make_count_chain(0)

        stats = backfill(db=mock_db, embedder=mock_embedder, dry_run=False)

        assert stats["total"] == 0
        assert stats["updated"] == 0

    # ── 4. test_backfill_batching ─────────────────────────────────

    def test_backfill_batching(self, mock_db, mock_embedder):
        """Processa em batches — 200 rows com batch_size=96 → 3 batches."""
        call_count = [0]

        def select_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_count_chain(200)
            else:
                batch_num = call_count[0] - 1  # 1-indexed batch
                page_size = 96
                offset_rows = (batch_num - 1) * page_size
                remaining = 200 - offset_rows
                if remaining <= 0:
                    return _make_page_chain([])  # end loop
                batch_size = min(page_size, remaining)
                rows = [{
                    "id": "row-%d" % (offset_rows + i),
                    "entity_type": "client",
                    "entity_name": "acme",
                    "key": "key-%d" % (offset_rows + i),
                    "value": {"dado": "valor-%d" % (offset_rows + i)},
                    "category": None,
                } for i in range(batch_size)]
                return _make_page_chain(rows)

        mock_db.table.return_value.select.side_effect = select_side_effect
        mock_db.table.return_value.update.return_value = _make_update_chain()

        # Mock embed_documents
        mock_embedder.embed_documents.side_effect = (
            lambda texts: [[0.1] * 384 for _ in texts]
        )

        stats = backfill(db=mock_db, embedder=mock_embedder, batch_size=96)

        assert stats["total"] == 200
        assert stats["batches"] >= 3  # 200 / 96 = 3 batches
        assert stats["updated"] == 200
        assert stats["failed"] == 0
