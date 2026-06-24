"""RED test for behavior B4.4 — Covering indexes for FK client_id.

GOAL:
    Corrigir 4 bottlenecks P1 no código de produção. Issue #121 — Performance.
    Tabelas hot-path com FK client_id precisam de covering indexes para evitar
    scans sequenciais. Os indexes devem cobrir as colunas mais consultadas
    para permitir index-only scans.

BEHAVIOR:
    B4.4 — Adicionar covering indexes para FK client_id em tabelas hot-path.
    Identificar tabelas mais consultadas via client_id e criar covering indexes
    que incluam as colunas mais frequentes em consultas WHERE/ORDER BY.

    Hot-path tables a indexar (identificadas via análise de consultas):
    - shared_business_memory (client_id)
    - shared_memory_links (client_id)
    - agent_messages (client_id)
    - integration_tokens (client_id)

AC (Acceptance Criteria):
    AC#3 — Migration SQL contém CREATE INDEX CONCURRENTLY statements para cada
           covering index identificado
    AC#4 — Cada index inclui client_id como coluna líder + covering columns

DECISION:
    Estratégia: extend (adicionar migration com covering indexes)
    Arquivo alvo: supabase/migrations/ (nova migration)
    Tabelas alvo: shared_business_memory, shared_memory_links, agent_messages,
                  integration_tokens

Anti-Goals (must NOT be violated):
    1. NÃO modificar migrations existentes
    2. NÃO usar CREATE INDEX sem CONCURRENTLY (bloqueia tabela)
    3. NÃO drop indexes existentes sem verificar uso
    4. NÃO alterar schema de tabelas (só adicionar indexes)

Estado atual: RED — os covering indexes não existem. O teste verifica que NENHUM
index covering client_id existe nas tabelas alvo.
"""

import re
from pathlib import Path

import pytest


# ── Paths ─────────────────────────────────────────────────────────────────

MIGRATIONS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "supabase"
    / "migrations"
)

# Tables that should get covering indexes for client_id FK
HOT_PATH_TABLES = [
    "shared_business_memory",
    "shared_memory_links",
    "agent_messages",
    "integration_tokens",
]

# Expected covered columns per table (minimum set)
# client_id is always the leading column
COVERING_COLUMNS = {
    "shared_business_memory": ["client_id", "entity_type", "entity_name", "updated_at"],
    "shared_memory_links": ["client_id", "source_entity_type", "source_entity_name", "link_type"],
    "agent_messages": ["client_id", "created_at", "role"],
    "integration_tokens": ["client_id", "provider", "expires_at"],
}


# ── Helpers ───────────────────────────────────────────────────────────────


def _get_migration_files() -> list[Path]:
    """Get all pending (not applied) migration SQL files, sorted by timestamp."""
    files = sorted(MIGRATIONS_DIR.glob("2026*.sql"))
    # Exclude applied/ directory
    files = [f for f in files if f.name != "applied"]
    return files


def _read_all_migration_sql() -> str:
    """Read all pending migration files and concatenate."""
    files = _get_migration_files()
    sql_parts = []
    for f in files:
        sql_parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(sql_parts)


def _has_index_on_table(sql: str, table: str) -> bool:
    """Check if SQL contains a CREATE INDEX for the given table with client_id."""
    # Patterns: CREATE INDEX ... ON ...table... (...client_id...)
    patterns = [
        rf"CREATE\s+(UNIQUE\s+)?INDEX\s+\w+\s+ON\s+(ONLY\s+)?{re.escape(table)}\s*\(.*client_id",
        rf"CREATE\s+INDEX\s+CONCURRENTLY\s+\w+\s+ON\s+{re.escape(table)}",
    ]
    for pat in patterns:
        if re.search(pat, sql, re.IGNORECASE | re.DOTALL):
            return True
    return False


def _has_covering_index(sql: str, table: str, columns: list[str]) -> bool:
    """Check if SQL contains a covering (INCLUDE) index for the given table.

    A covering index includes extra columns via INCLUDE clause.
    Example:
        CREATE INDEX CONCURRENTLY idx_shared_business_memory_client
        ON shared_business_memory (client_id)
        INCLUDE (entity_type, entity_name, updated_at);
    """
    # Pattern: CREATE INDEX ... ON table (...) INCLUDE (col1, col2, ...)
    include_pat = rf"CREATE\s+(UNIQUE\s+)?INDEX\s+CONCURRENTLY\s+\w+\s+ON\s+{re.escape(table)}\s*\(.*?\)\s*INCLUDE\s*\("
    if re.search(include_pat, sql, re.IGNORECASE | re.DOTALL):
        return True

    # Also accept a composite index on client_id + the covering columns
    # Pattern: CREATE INDEX ... ON table (client_id, col1, col2, ...)
    for col in columns[1:]:  # skip client_id, check at least one covering col
        composite_pat = (
            rf"CREATE\s+(UNIQUE\s+)?INDEX\s+\w+\s+ON\s+{re.escape(table)}\s*\(.*client_id.*{re.escape(col)}"
        )
        if re.search(composite_pat, sql, re.IGNORECASE | re.DOTALL):
            return True

    return False


# ── Tests ─────────────────────────────────────────────────────────────────


def test_b4_4_migration_file_exists():
    """A migration file should exist in supabase/migrations/ for covering indexes."""
    files = _get_migration_files()
    assert len(files) > 0, (
        "No migration files found in supabase/migrations/. "
        "A new migration file is needed for covering indexes."
    )


def test_b4_4_covering_index_for_shared_business_memory():
    """shared_business_memory must have a covering index for client_id."""
    sql = _read_all_migration_sql()
    table = "shared_business_memory"
    # Assert RED: covering index should exist but doesn't
    assert _has_covering_index(sql, table, COVERING_COLUMNS[table]), (
        f"RED — No covering index found for {table}. "
        "Expected: CREATE INDEX CONCURRENTLY idx_{table}_client ON {table} (client_id) "
        "INCLUDE (entity_type, entity_name, updated_at). "
        "The Coder must add a migration with covering indexes for hot-path tables "
        "queried by client_id."
    )


def test_b4_4_covering_index_for_shared_memory_links():
    """shared_memory_links must have a covering index for client_id."""
    sql = _read_all_migration_sql()
    table = "shared_memory_links"
    assert _has_covering_index(sql, table, COVERING_COLUMNS[table]), (
        f"RED — No covering index found for {table}. "
        "Expected: covering index on (client_id) INCLUDE (source_entity_type, ...)."
    )


def test_b4_4_covering_index_for_agent_messages():
    """agent_messages must have a covering index for client_id."""
    sql = _read_all_migration_sql()
    table = "agent_messages"
    assert _has_covering_index(sql, table, COVERING_COLUMNS[table]), (
        f"RED — No covering index found for {table}. "
        "Expected: covering index on (client_id) INCLUDE (created_at, role)."
    )


def test_b4_4_covering_index_for_integration_tokens():
    """integration_tokens must have a covering index for client_id."""
    sql = _read_all_migration_sql()
    table = "integration_tokens"
    assert _has_covering_index(sql, table, COVERING_COLUMNS[table]), (
        f"RED — No covering index found for {table}. "
        "Expected: covering index on (client_id) INCLUDE (provider, expires_at)."
    )
