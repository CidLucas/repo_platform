"""RED test for behavior B-3 — SQL data-fix migration: backfill onboarding_completed_at.

GOAL:
    Garantir que existe uma migration SQL em supabase/migrations/ (fora de
    applied/ e archive/) que executa um data-fix em public.clientes_blu,
    preenchendo onboarding_completed_at = now() para todos os clientes que
    já possuem pelo menos uma fonte de dados vinculada, mas cujo
    onboarding_completed_at ainda está NULL.

BEHAVIOR:
    B-3 — Data-fix migration: backfill onboarding_completed_at for clients
    that already have at least one row in public.client_data_sources.

AC (Acceptance Criteria):
    AC#1 — A migration está localizada em supabase/migrations/ (NÃO dentro
            de applied/ ou archive/).
    AC#2 — A migration contém a instrução:
            UPDATE public.clientes_blu SET onboarding_completed_at = now()
    AC#3 — A instrução UPDATE é restrita por uma cláusula EXISTS que
            referencia public.client_data_sources:
            EXISTS (SELECT 1 FROM public.client_data_sources)
    AC#4 — A instrução UPDATE inclui a cláusula:
            WHERE onboarding_completed_at IS NULL
            (evita sobrescrever timestamps já preenchidos).
    AC#5 — As três condições acima aparecem em uma única instrução
            (mesma migration, garantindo idempotência semântica).

DECISÃO:
    Estratégia: create_new
    Padrão: source-inspection — leitura de arquivos .sql como texto puro,
            uso de regex para detectar a presença da instrução alvo.
    Sem mock, sem DB, sem fixtures de runtime.

Estado atual: RED — nenhuma migration existente (fora de applied/ e archive/)
contém a instrução combinada alvo. O teste falha via pytest.fail() em
pt-BR até que a migration seja criada na fase GREEN.
"""

import re
from pathlib import Path

import pytest


# ── Constants: the public interface under test ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_ROOT = REPO_ROOT / "supabase" / "migrations"

EXCLUDED_DIRS = {"applied", "archive"}

TARGET_TABLE = "public.clientes_blu"
RELATED_TABLE = "public.client_data_sources"
TARGET_COLUMN = "onboarding_completed_at"


# ── Regex patterns: the three clauses that must co-exist ────────────────

RE_UPDATE_SET = re.compile(
    rf"UPDATE\s+{re.escape(TARGET_TABLE)}\s+SET\s+{re.escape(TARGET_COLUMN)}\s*=\s*now\s*\(",
    re.IGNORECASE,
)

RE_EXISTS_RELATED = re.compile(
    rf"EXISTS\s*\(\s*SELECT\s+1\s+FROM\s+{re.escape(RELATED_TABLE)}",
    re.IGNORECASE,
)

RE_WHERE_NULL = re.compile(
    rf"WHERE\s+{re.escape(TARGET_COLUMN)}\s+IS\s+NULL",
    re.IGNORECASE,
)


# ── Override root conftest cleanup (no real Supabase needed) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file I/O, no DB teardown."""
    yield


# ── Helpers ─────────────────────────────────────────────────────────────


def _iter_migration_files() -> list[Path]:
    """Lista arquivos .sql em supabase/migrations/, excluindo applied/ e
    archive/. Retorna lista ordenada para reprodutibilidade.
    """
    if not MIGRATIONS_ROOT.exists():
        return []
    files: list[Path] = []
    for path in MIGRATIONS_ROOT.rglob("*.sql"):
        # Exclui qualquer arquivo dentro de applied/ ou archive/.
        parts = {p.name for p in path.relative_to(MIGRATIONS_ROOT).parents}
        if parts & EXCLUDED_DIRS:
            continue
        files.append(path)
    return sorted(files)


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── The single behavior under test ──────────────────────────────────────


def test_b3_ac1_to_ac5_data_fix_migration():
    """AC#1..AC#5 — Deve existir uma migration (fora de applied/ e archive/)
    que faz backfill de onboarding_completed_at em public.clientes_blu
    usando EXISTS sobre public.client_data_sources e WHERE
    onboarding_completed_at IS NULL.
    """
    migration_files = _iter_migration_files()
    assert migration_files, (
        f"Nenhum arquivo .sql encontrado em {MIGRATIONS_ROOT} (excluindo "
        f"{sorted(EXCLUDED_DIRS)}). Verifique a estrutura do repositório."
    )

    # Procura uma migration que combine as três cláusulas (AC#2 + AC#3 + AC#4).
    matching_files: list[Path] = []
    for path in migration_files:
        sql = _read_sql(path)
        if RE_UPDATE_SET.search(sql) and RE_EXISTS_RELATED.search(sql) and RE_WHERE_NULL.search(sql):
            matching_files.append(path)

    if not matching_files:
        pytest.fail(
            "B-3 RED: nenhuma migration de data-fix foi encontrada em "
            f"{MIGRATIONS_ROOT} (excluindo applied/ e archive/) que "
            f"contenha simultaneamente as três cláusulas exigidas:\n"
            f"  1) UPDATE {TARGET_TABLE} SET {TARGET_COLUMN} = now()\n"
            f"  2) EXISTS (SELECT 1 FROM {RELATED_TABLE})\n"
            f"  3) WHERE {TARGET_COLUMN} IS NULL\n"
            "Crie a migration correspondente na fase GREEN para satisfazer "
            "os AC#1..AC#5 do comportamento B-3."
        )

    # Se chegarmos aqui, a migration existe — validação adicional (AC#5).
    found = matching_files[0]
    sql = _read_sql(found)
    assert RE_UPDATE_SET.search(sql), f"[AC#2] Cláusula UPDATE ausente em {found}."
    assert RE_EXISTS_RELATED.search(sql), f"[AC#3] Cláusula EXISTS ausente em {found}."
    assert RE_WHERE_NULL.search(sql), f"[AC#4] Cláusula WHERE ... IS NULL ausente em {found}."
