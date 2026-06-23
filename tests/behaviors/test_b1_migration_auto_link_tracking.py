"""RED test for behavior B1 — SQL Migration: auto-link tracking columns.

GOAL:
    Garantir que existe uma migration SQL em supabase/migrations/proposed/ que
    adiciona as colunas de tracking de auto-linking à tabela
    shared_business_memory, sem alterar a tabela shared_memory_links.

BEHAVIOR:
    B1 — SQL Migration: Add auto-link tracking columns to
    shared_business_memory (Issue #28, Fase 3).

AC (Acceptance Criteria):
    AC#1 — A tabela public.shared_business_memory ganha as colunas:
        - last_auto_link_at  TIMESTAMPTZ  (nullable)
        - auto_link_count    INTEGER      DEFAULT 0
    A migration é uma transação (BEGIN/COMMIT).
    A tabela public.shared_memory_links NÃO é modificada (anti-goal).

DECISÃO:
    Estratégia: create_new
    Arquivo alvo: supabase/migrations/proposed/20260623000001_auto_link_tracking.sql

Estado atual: RED — o arquivo de migration ainda não existe; este teste valida
a interface pública (caminho do arquivo + conteúdo SQL) e falhará com
FileNotFoundError até que a migration seja criada na fase GREEN.
"""

import re
from pathlib import Path

import pytest


# ── Constants: the public interface under test ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATION_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "proposed"
    / "20260623000001_auto_link_tracking.sql"
)

TARGET_TABLE = "public.shared_business_memory"
PROTECTED_TABLE = "public.shared_memory_links"


# ── Override root conftest cleanup (no real Supabase needed) ───────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file I/O, no DB teardown."""
    yield


# ── The single behavior under test ──────────────────────────────────────


def test_b1_migration_adds_auto_link_tracking_columns_to_shared_business_memory():
    """A migration must exist at the canonical path and declare the new
    columns on shared_business_memory, inside a transaction, without
    touching shared_memory_links.
    """
    # 1. The migration file must exist at the canonical proposed path.
    assert MIGRATION_PATH.exists(), (
        f"Migration not found at {MIGRATION_PATH}. "
        "Behavior B1 requires a SQL migration at this exact path."
    )

    sql = MIGRATION_PATH.read_text()

    # 2. Sanity: the file must be a single transaction.
    assert "BEGIN" in sql, "Migration must wrap DDL in BEGIN ... COMMIT."
    assert "COMMIT" in sql, "Migration must wrap DDL in BEGIN ... COMMIT."

    # 3. The migration must target shared_business_memory, not the
    #    protected shared_memory_links table.
    assert re.search(
        rf"ALTER\s+TABLE\s+(IF\s+EXISTS\s+)?{re.escape(TARGET_TABLE)}",
        sql,
        re.IGNORECASE,
    ), f"Migration must ALTER TABLE {TARGET_TABLE}."

    assert not re.search(
        rf"ALTER\s+TABLE\s+(IF\s+EXISTS\s+)?{re.escape(PROTECTED_TABLE)}",
        sql,
        re.IGNORECASE,
    ), f"Migration must NOT alter {PROTECTED_TABLE} (anti-goal #2)."

    # 4. AC#1 — both new columns must be declared.
    assert re.search(
        rf"ADD\s+COLUMN\s+(IF\s+NOT\s+EXISTS\s+)?last_auto_link_at\s+TIMESTAMPTZ",
        sql,
        re.IGNORECASE,
    ), "Missing `ADD COLUMN last_auto_link_at TIMESTAMPTZ` on shared_business_memory."

    assert re.search(
        rf"ADD\s+COLUMN\s+(IF\s+NOT\s+EXISTS\s+)?auto_link_count\s+INTEGER\s+DEFAULT\s+0",
        sql,
        re.IGNORECASE,
    ), "Missing `ADD COLUMN auto_link_count INTEGER DEFAULT 0` on shared_business_memory."
