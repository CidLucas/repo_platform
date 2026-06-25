"""RED test — B-2 (BATCH #215): Migration de backfill para clientes existentes.

GOAL:
    Adicionar um UPDATE de backfill no final da migration
    ``20260625_p13_is_onboarded_client.sql`` que preenche
    ``onboarding_completed_at`` para clientes existentes que já têm
    atividade (data_sources ou enabled_agents + conta > 1h) mas
    não têm o campo preenchido. Usa ``LEAST(created_at + 1h, now())``
    para garantir que o valor nunca seja data futura. Atualiza
    ``updated_at`` para ``now()`` nos registros afetados.

BEHAVIOR:
    "B-2 — Migration de backfill que preenche onboarding_completed_at
    para clientes existentes com atividade (data_sources ou
    enabled_agents + conta > 1h), usando LEAST para evitar data
    futura e atualizando updated_at."

    O UPDATE deve:
        1. Usar ``UPDATE public.clientes_blu cb`` com SET
           ``onboarding_completed_at = LEAST(cb.created_at + interval
           '1 hour', now())``.
        2. Incluir ``updated_at = now()`` no SET.
        3. Filtrar com ``WHERE cb.onboarding_completed_at IS NULL``.
        4. Incluir EXISTS subquery em ``client_data_sources``.
        5. Incluir condição de ``enabled_agents`` + conta > 1h
           (``created_at < now() - interval '1 hour'``).

    Estado atual (BEFORE — RED):
        O arquivo ``supabase/migrations/applied/20260625_p13_is_onboarded_client.sql``
        NÃO existe — o coder ainda não criou a migration com a RPC
        e o backfill.

    Estado esperado (AFTER — GREEN):
        O arquivo de migration existirá com o UPDATE de backfill
        completo, incluindo todos os 5 requisitos acima.

AC (Acceptance Criteria):
    AC#1 — UPDATE com ``SET onboarding_completed_at = LEAST(
           cb.created_at + interval '1 hour', now())`` presente.
    AC#2 — ``SET updated_at = now()`` presente no mesmo UPDATE.
    AC#3 — ``WHERE cb.onboarding_completed_at IS NULL`` presente.
    AC#4 — EXISTS subquery em ``client_data_sources`` presente no WHERE.
    AC#5 — Condição de ``enabled_agents`` + ``created_at < now()
           - interval '1 hour'`` presente no WHERE.

Anti-Goals:
    1. NÃO modificar código de produção (migration SQL).
    2. NÃO executar/parsear SQL — somente inspeção textual com regex.
    3. NÃO usar mocks, Supabase ou banco de dados.
    4. NÃO quebrar funcionalidade existente.
    5. NÃO relaxar o teste para que ele passe — precisa ser TRUE RED agora.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

MIGRATION_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "applied"
    / "20260625_p13_is_onboarded_client.sql"
)


# ── Override do root conftest (teste puramente estático) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção textual do arquivo de migration SQL, sem teardown
    no Supabase, sem rede, sem import/execução de SQL.
    """
    yield


# ── Helpers de inspeção textual ───────────────────────────────────────


def _read_source(path: Path) -> str:
    """Lê o arquivo SQL como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Migration file not found: {path}.  "
        "O behavior B-2 (BATCH #215) exige que o arquivo "
        "supabase/migrations/applied/20260625_p13_is_onboarded_client.sql "
        "exista no repo.  O coder precisa criar a migration (B-1) e "
        "adicionar o UPDATE de backfill (B-2) antes que este teste "
        "possa passar (GREEN)."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os ACs de B-2 ────────────────


@pytest.mark.behaviors
def test_b2_backfill_migration_red() -> None:
    """B-2 (BATCH #215) — RED.  Falha enquanto o UPDATE de backfill
    não estiver presente na migration
    ``20260625_p13_is_onboarded_client.sql``.

    Esta função agrega a verificação de TODOS os ACs em uma única
    asserção: coleta todas as deficiências e dispara ``pytest.fail`` com
    mensagem consolidada em pt-BR listando o que falta para GREEN.
    """
    source = _read_source(MIGRATION_PATH)

    problemas: list[str] = []

    # ── AC#1 — SET onboarding_completed_at = LEAST(...) ─────────────
    #     Evidência esperada:
    #       SET onboarding_completed_at =
    #         LEAST(cb.created_at + interval '1 hour', now())
    has_onboarding_least = bool(
        re.search(
            r"SET\s+onboarding_completed_at\s*=\s*LEAST\s*\("
            r"cb\.created_at\s*\+\s*interval\s+'1\s*hour'\s*,\s*now\(\)\s*\)",
            source,
            re.IGNORECASE,
        )
    )

    if not has_onboarding_least:
        problemas.append(
            "AC#1 — `SET onboarding_completed_at = LEAST(cb.created_at "
            "+ interval '1 hour', now())` NAO presente no UPDATE de "
            "backfill.  O migration precisa preencher este campo com "
            "LEAST para garantir que o valor nunca seja data futura."
        )

    # ── AC#2 — SET updated_at = now() ──────────────────────────────
    #     Evidência esperada: updated_at = now() no mesmo UPDATE
    has_updated_at = bool(
        re.search(
            r"SET\s+.*updated_at\s*=\s*now\(\)",
            source,
            re.IGNORECASE,
        )
    )

    if not has_updated_at:
        problemas.append(
            "AC#2 — `SET updated_at = now()` NAO presente no UPDATE "
            "de backfill.  Registros afetados precisam ter seu "
            "updated_at atualizado para now()."
        )

    # ── AC#3 — WHERE onboarding_completed_at IS NULL ──────────────
    #     Evidência esperada: WHERE cb.onboarding_completed_at IS NULL
    has_where_null = bool(
        re.search(
            r"WHERE\s+cb\.onboarding_completed_at\s+IS\s+NULL",
            source,
            re.IGNORECASE,
        )
    )

    if not has_where_null:
        problemas.append(
            "AC#3 — `WHERE cb.onboarding_completed_at IS NULL` NAO "
            "presente no UPDATE de backfill.  O filtro deve garantir "
            "que apenas clientes sem onboarding_completed_at sejam "
            "afetados."
        )

    # ── AC#4 — EXISTS subquery em client_data_sources ──────────────
    #     Evidência esperada: EXISTS (SELECT ... FROM
    #     public.client_data_sources ...)
    has_exists_data_sources = bool(
        re.search(
            r"EXISTS\s*\(\s*SELECT\s+1\s+FROM\s+public\.client_data_sources\b",
            source,
            re.IGNORECASE,
        )
    )

    if not has_exists_data_sources:
        problemas.append(
            "AC#4 — Subquery `EXISTS (SELECT 1 FROM "
            "public.client_data_sources ...)` NAO presente no WHERE "
            "do UPDATE de backfill.  Clientes com fontes de dados "
            "ativas devem ser identificados para receber o "
            "onboarding_completed_at."
        )

    # ── AC#5 — enabled_agents + conta > 1h ────────────────────────
    #     Evidência esperada: created_at < now() - interval '1 hour'
    #     combinado com EXISTS em client_enabled_agents
    has_age_check = bool(
        re.search(
            r"cb\.created_at\s*<\s*now\(\)\s*-\s*interval\s+'1\s*hour'",
            source,
            re.IGNORECASE,
        )
    )
    has_enabled_agents = bool(
        re.search(
            r"EXISTS\s*\(\s*SELECT\s+1\s+FROM\s+public\.client_enabled_agents\b",
            source,
            re.IGNORECASE,
        )
    )

    if not has_age_check:
        problemas.append(
            "AC#5.1 — Condicao `cb.created_at < now() - interval "
            "'1 hour'` NAO presente no UPDATE de backfill.  "
            "Clientes com enabled_agents so devem ser considerados "
            "se a conta tiver mais de 1 hora."
        )
    if not has_enabled_agents:
        problemas.append(
            "AC#5.2 — Subquery `EXISTS (SELECT 1 FROM "
            "public.client_enabled_agents ...)` NAO presente no WHERE "
            "do UPDATE de backfill.  Clientes com enabled_agents "
            "devem ser identificados para receber o "
            "onboarding_completed_at."
        )

    # ── Agrega todas as deficiências ─────────────────────────────────
    if problemas:
        cabecalho = (
            f"[RED] B-2 (BATCH #215) — Backfill migration — "
            f"{len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  • {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
