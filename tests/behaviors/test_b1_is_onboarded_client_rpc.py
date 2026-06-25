"""RED test — B-1 (BATCH #215): Criar RPC is_onboarded_client() no banco.

GOAL:
    Disponibilizar a RPC ``public.is_onboarded_client()`` que retorna um
    ``boolean`` indicando se o cliente autenticado está onboarded, usando
    3 sinais (onboarding_completed_at, data_sources ativos,
    enabled_agents + conta > 1h). SECURITY INVOKER.

BEHAVIOR:
    "B-1 — public.is_onboarded_client() retorna boolean indicando se o
    cliente autenticado está onboarded, usando 3 sinais. SECURITY INVOKER."

    A RPC deve:
        1. Ser declarada via ``CREATE OR REPLACE FUNCTION`` em
           ``public.is_onboarded_client()``.
        2. Retornar ``boolean``.
        3. Usar ``SECURITY INVOKER`` (NÃO SECURITY DEFINER).
        4. Chamar ``get_my_client_id()`` internamente no corpo.
        5. Rejeitar chamadas sem autenticação (``REVOKE ... FROM anon``).
        6. Incluir ``SET search_path = public, pg_temp`` (proteção contra
           search_path injection).

    Estado atual (BEFORE — RED):
        O arquivo ``supabase/migrations/applied/20260625_p13_is_onboarded_client.sql``
        NÃO existe — o coder ainda não criou a migration.

    Estado esperado (AFTER — GREEN):
        O arquivo de migration existirá com a definição completa da função,
        incluindo todos os 6 requisitos acima.

AC (Acceptance Criteria):
    AC#1 - ``CREATE OR REPLACE FUNCTION public.is_onboarded_client()``
           declarada no arquivo de migration.
    AC#2 - ``RETURNS boolean`` presente na assinatura.
    AC#3 - ``SECURITY INVOKER`` presente e ``SECURITY DEFINER`` ausente.
    AC#4 - ``get_my_client_id()`` chamada no corpo da função.
    AC#5 - ``REVOKE EXECUTE ON FUNCTION ... FROM anon`` presente.
    AC#6 - ``SET search_path = public, pg_temp`` presente.

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

FUNCTION_NAME = "is_onboarded_client"


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
        "O behavior B-1 (BATCH #215) exige que o arquivo "
        "supabase/migrations/applied/20260625_p13_is_onboarded_client.sql "
        "exista no repo.  O coder precisa criar a migration antes que "
        "este teste possa passar (GREEN)."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os ACs de B-1 ────────────────


@pytest.mark.behaviors
def test_b1_is_onboarded_client_rpc_red() -> None:
    """B-1 (BATCH #215) — RED.  Falha enquanto a RPC
    ``public.is_onboarded_client()`` não estiver implementada na migration
    ``20260625_p13_is_onboarded_client.sql``.

    Esta função agrega a verificação de TODOS os ACs em uma única
    asserção: coleta todas as deficiências e dispara ``pytest.fail`` com
    mensagem consolidada em pt-BR listando o que falta para GREEN.
    """
    source = _read_source(MIGRATION_PATH)

    problemas: list[str] = []

    # ── AC#1 — Function declarada via CREATE OR REPLACE FUNCTION ────
    #     Evidência esperada: CREATE OR REPLACE FUNCTION public.is_onboarded_client()
    has_create_function = bool(
        re.search(
            rf"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.{FUNCTION_NAME}\b",
            source,
            re.IGNORECASE,
        )
    )

    if not has_create_function:
        problemas.append(
            f"AC#1 — `CREATE OR REPLACE FUNCTION public.{FUNCTION_NAME}()` "
            "NAO declarada no arquivo de migration.  "
            "A migration precisa criar a funcao para que o cliente "
            "autenticado possa verificar seu status de onboarding."
        )

    # ── AC#2 — RETURNS boolean ──────────────────────────────────────
    #     Evidência esperada: RETURNS boolean na assinatura
    has_returns_boolean = bool(
        re.search(
            r"RETURNS\s+boolean\b",
            source,
            re.IGNORECASE,
        )
    )

    if not has_returns_boolean:
        problemas.append(
            "AC#2 — `RETURNS boolean` NAO presente na assinatura da funcao.  "
            "A RPC deve retornar um booleano indicando se o cliente "
            "esta onboarded ou nao."
        )

    # ── AC#3 — SECURITY INVOKER (NÃO SECURITY DEFINER) ──────────────
    #     Evidências esperadas:
    #       - SECURITY INVOKER presente
    #       - SECURITY DEFINER ausente
    has_security_invoker = bool(
        re.search(
            r"SECURITY\s+INVOKER",
            source,
            re.IGNORECASE,
        )
    )
    has_security_definer = bool(
        re.search(
            r"SECURITY\s+DEFINER",
            source,
            re.IGNORECASE,
        )
    )

    if not has_security_invoker:
        problemas.append(
            "AC#3 — `SECURITY INVOKER` NAO presente.  "
            "A RPC precisa usar SECURITY INVOKER (e NAO SECURITY DEFINER) "
            "para que a funcao rode com os privilegios do caller "
            "autenticado, evitando escalacao de privilegio."
        )
    if has_security_definer:
        problemas.append(
            "AC#3 — `SECURITY DEFINER` esta PRESENTE (deveria ser "
            "SECURITY INVOKER).  SECURITY DEFINER faz a funcao rodar "
            "com privilegios do criador, o que pode expor dados de "
            "outros clientes."
        )

    # ── AC#4 — get_my_client_id() chamada internamente ──────────────
    #     Evidência esperada: get_my_client_id() dentro do corpo $$
    has_get_my_client_id = bool(
        re.search(
            r"get_my_client_id\s*\(",
            source,
        )
    )

    if not has_get_my_client_id:
        problemas.append(
            "AC#4 — `get_my_client_id()` NAO chamada no corpo da funcao.  "
            "A RPC precisa obter o client_id do caller autenticado via "
            "get_my_client_id() para verificar o status de onboarding "
            "do cliente correto."
        )

    # ── AC#5 — REVOKE EXECUTE FROM anon ─────────────────────────────
    #     Evidência esperada: REVOKE ... EXECUTE ... FROM anon
    has_revoke_anon = bool(
        re.search(
            r"REVOKE\s+.*EXECUTE\s+.*FROM\s+anon",
            source,
            re.IGNORECASE,
        )
    )

    if not has_revoke_anon:
        problemas.append(
            "AC#5 — `REVOKE EXECUTE ON FUNCTION ... FROM anon` NAO presente.  "
            "Usuarios nao autenticados (anon) devem ser rejeitados ao "
            "chamar esta RPC, pois get_my_client_id() requer autenticacao."
        )

    # ── AC#6 — SET search_path = public, pg_temp ────────────────────
    #     Evidência esperada: SET search_path = public, pg_temp
    has_search_path = bool(
        re.search(
            r"SET\s+search_path\s*=\s*public\s*,\s*pg_temp",
            source,
            re.IGNORECASE,
        )
    )

    if not has_search_path:
        problemas.append(
            "AC#6 — `SET search_path = public, pg_temp` NAO presente.  "
            "Sem esta protecao, a funcao fica vulneravel a ataques de "
            "search_path injection (um schema malicioso poderia sobrescrever "
            "get_my_client_id ou outras funcoes referenciadas)."
        )

    # ── Agrega todas as deficiências ─────────────────────────────────
    if problemas:
        cabecalho = (
            f"[RED] B-1 (BATCH #215) — RPC public.{FUNCTION_NAME}() — "
            f"{len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  • {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
