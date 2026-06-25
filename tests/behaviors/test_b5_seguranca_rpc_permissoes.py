"""RED test — B-5 (BATCH #215): Seguranca da RPC is_onboarded_client() — permissoes.

GOAL:
    Garantir que a RPC ``public.is_onboarded_client()`` esteja configurada com
    permissoes corretas: REVOKE ALL FROM PUBLIC, REVOKE EXECUTE FROM anon,
    GRANT EXECUTE TO authenticated/service_role, SECURITY INVOKER (e NAO
    SECURITY DEFINER), ``SET search_path = public, pg_temp`` e sem
    execucao como superuser/bypassrls.

BEHAVIOR:
    "B-5 — public.is_onboarded_client() expoe permissoes corretas:
    anon NAO pode chamar, authenticated e service_role podem chamar,
    NAO executa como superuser, NAO usa SECURITY DEFINER."

    A migration deve:
        1. Executar ``REVOKE ALL ON FUNCTION public.is_onboarded_client()
           FROM PUBLIC``.
        2. Executar ``REVOKE EXECUTE ON FUNCTION public.is_onboarded_client()
           FROM anon``.
        3. Executar ``GRANT EXECUTE ON FUNCTION public.is_onboarded_client()
           TO authenticated, service_role``.
        4. Usar ``SECURITY INVOKER`` (e NAO SECURITY DEFINER).
        5. Incluir ``SET search_path = public, pg_temp``.
        6. NAO executar como superuser / NAO usar EXECUTE AS / NAO usar
           ``bypassrls``.

    Estado atual (BEFORE — RED):
        O arquivo ``supabase/migrations/applied/20260625_p13_is_onboarded_client.sql``
        NAO existe — o coder ainda nao criou a migration.

    Estado esperado (AFTER — GREEN):
        O arquivo de migration existira com TODAS as 8 clausulas de
        permissao/seguranca acima.

AC (Acceptance Criteria):
    AC#1 - ``REVOKE ALL ON FUNCTION public.is_onboarded_client() FROM PUBLIC``
           presente.
    AC#2 - ``REVOKE EXECUTE ON FUNCTION public.is_onboarded_client() FROM anon``
           presente.
    AC#3 - ``GRANT EXECUTE ON FUNCTION public.is_onboarded_client() TO
           authenticated, service_role`` presente.
    AC#4 - ``SECURITY INVOKER`` presente e ``SECURITY DEFINER`` ausente.
    AC#5 - ``SET search_path = public, pg_temp`` presente.
    AC#6 - Funcao NAO executa como superuser / NAO ha EXECUTE AS / NAO ha
           ``bypassrls``.
    AC#7 - Chamada anon falha com erro de permissao (evidenciado por
           AC#1 AND AC#2 — REVOKE ALL FROM PUBLIC + REVOKE EXECUTE FROM anon).
    AC#8 - Chamada authenticated funciona (evidenciado por AC#3 — GRANT
           EXECUTE TO authenticated, service_role).

Anti-Goals:
    1. NAO modificar codigo de producao (migration SQL).
    2. NAO executar/parsear SQL — somente inspecao textual com regex.
    3. NAO usar mocks, Supabase ou banco de dados.
    4. NAO quebrar funcionalidade existente.
    5. NAO relaxar o teste para que ele passe — precisa ser TRUE RED agora.
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


# ── Override do root conftest (teste puramente estatico) ──────────────


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
        "O behavior B-5 (BATCH #215) exige que o arquivo "
        "supabase/migrations/applied/20260625_p13_is_onboarded_client.sql "
        "exista no repo.  O coder precisa criar a migration antes que "
        "este teste possa passar (GREEN)."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os ACs de B-5 ────────────────


@pytest.mark.behaviors
def test_b5_seguranca_rpc_permissoes_red() -> None:
    """B-5 (BATCH #215) — RED.  Falha enquanto a RPC
    ``public.is_onboarded_client()`` não estiver configurada com as
    permissões de segurança adequadas na migration
    ``20260625_p13_is_onboarded_client.sql``.

    Esta função agrega a verificação de TODOS os ACs em uma única
    asserção: coleta todas as deficiências e dispara ``pytest.fail`` com
    mensagem consolidada em pt-BR listando o que falta para GREEN.
    """
    source = _read_source(MIGRATION_PATH)

    problemas: list[str] = []

    # ── AC#1 — REVOKE ALL ON FUNCTION ... FROM PUBLIC ───────────────
    #     Evidência esperada: REVOKE ALL ON FUNCTION public.is_onboarded_client() FROM PUBLIC
    has_revoke_all_public = bool(
        re.search(
            rf"REVOKE\s+ALL\s+ON\s+FUNCTION\s+public\.{FUNCTION_NAME}\s*\(\s*\)\s+FROM\s+PUBLIC",
            source,
            re.IGNORECASE,
        )
    )

    if not has_revoke_all_public:
        problemas.append(
            f"AC#1 — `REVOKE ALL ON FUNCTION public.{FUNCTION_NAME}() "
            "FROM PUBLIC` NAO presente.  "
            "A migration deve revogar todas as permissoes padrao do "
            "role PUBLIC sobre a funcao, garantindo que apenas roles "
            "explicitamente autorizadas possam executa-la."
        )

    # ── AC#2 — REVOKE EXECUTE ON FUNCTION ... FROM anon ─────────────
    #     Evidência esperada: REVOKE ... EXECUTE ON FUNCTION public.is_onboarded_client() FROM anon
    has_revoke_anon = bool(
        re.search(
            rf"REVOKE\s+.*EXECUTE\s+ON\s+FUNCTION\s+public\.{FUNCTION_NAME}\s*\(\s*\)\s+FROM\s+anon",
            source,
            re.IGNORECASE,
        )
    )

    if not has_revoke_anon:
        problemas.append(
            f"AC#2 — `REVOKE EXECUTE ON FUNCTION public.{FUNCTION_NAME}() "
            "FROM anon` NAO presente.  "
            "Usuarios nao autenticados (role anon) devem ser "
            "explicitamente bloqueados de chamar esta RPC, ja que "
            "get_my_client_id() requer autenticacao."
        )

    # ── AC#3 — GRANT EXECUTE ... TO authenticated, service_role ─────
    #     Evidência esperada: GRANT EXECUTE ON FUNCTION public.is_onboarded_client() TO authenticated
    has_grant_authenticated = bool(
        re.search(
            rf"GRANT\s+EXECUTE\s+ON\s+FUNCTION\s+public\.{FUNCTION_NAME}\s*\(\s*\)\s+TO\s+authenticated",
            source,
            re.IGNORECASE,
        )
    )

    if not has_grant_authenticated:
        problemas.append(
            f"AC#3 — `GRANT EXECUTE ON FUNCTION public.{FUNCTION_NAME}() "
            "TO authenticated, service_role` NAO presente.  "
            "Apos revogar o acesso padrao (AC#1, AC#2), a migration "
            "precisa GRANT EXECUTE explicitamente para os roles "
            "`authenticated` (clientes logados) e `service_role` "
            "(workers/backend)."
        )

    # ── AC#4 — SECURITY INVOKER presente e SECURITY DEFINER ausente ─
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
            "AC#4 — `SECURITY INVOKER` NAO presente.  "
            "A RPC precisa usar SECURITY INVOKER para rodar com os "
            "privilegios do caller autenticado, permitindo que as "
            "RLS policies sejam aplicadas corretamente."
        )
    if has_security_definer:
        problemas.append(
            "AC#4 — `SECURITY DEFINER` esta PRESENTE (deveria ser "
            "SECURITY INVOKER).  SECURITY DEFINER faz a funcao rodar "
            "com privilegios do criador (geralmente superuser/owner), "
            "o que pode expor dados de outros clientes e bypassar RLS."
        )

    # ── AC#5 — SET search_path = public, pg_temp ────────────────────
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
            "AC#5 — `SET search_path = public, pg_temp` NAO presente.  "
            "Sem esta protecao, a funcao fica vulneravel a ataques de "
            "search_path injection (um schema malicioso poderia "
            "sobrescrever get_my_client_id ou outras funcoes referenciadas)."
        )

    # ── AC#6 — Função NAO executa como superuser ───────────────────
    #     Padrões proibidos:
    #       - EXECUTE AS (qualquer combinacao: 'EXECUTE AS CALLER',
    #         'EXECUTE AS OWNER', 'EXECUTE AS ' + qualquer outro)
    #         - NOTA: apenas EXECUTE AS CALLER é equivalente a SECURITY
    #           INVOKER (default), mas a evidencia esperada é que NAO
    #           haja EXECUTE AS OWNER / EXECUTE AS superuser.
    #       - "superuser" como termo (pode indicar BYPASSRLS ou
    #         EXECUTE AS superuser)
    #       - bypassrls (atributo perigoso: bypassa todas as RLS)
    has_execute_as_owner = bool(
        re.search(
            r"EXECUTE\s+AS\s+OWNER",
            source,
            re.IGNORECASE,
        )
    )
    has_execute_as_superuser = bool(
        re.search(
            r"EXECUTE\s+AS\s+SUPERUSER",
            source,
            re.IGNORECASE,
        )
    )
    has_superuser_token = bool(
        re.search(
            r"\bsuperuser\b",
            source,
            re.IGNORECASE,
        )
    )
    has_bypassrls = bool(
        re.search(
            r"\bbypassrls\b",
            source,
            re.IGNORECASE,
        )
    )

    if (
        has_execute_as_owner
        or has_execute_as_superuser
        or has_superuser_token
        or has_bypassrls
    ):
        detalhes_ac6: list[str] = []
        if has_execute_as_owner:
            detalhes_ac6.append(
                "`EXECUTE AS OWNER` presente — faz a funcao rodar com "
                "privilegios do owner (tipicamente superuser), bypassando RLS."
            )
        if has_execute_as_superuser:
            detalhes_ac6.append(
                "`EXECUTE AS SUPERUSER` presente — execucao explicita como "
                "superuser, altissimo risco de privilege escalation."
            )
        if has_superuser_token:
            detalhes_ac6.append(
                "termo `superuser` presente na migration — possivel "
                "indicador de execucao privilegiada nao-justificada."
            )
        if has_bypassrls:
            detalhes_ac6.append(
                "`bypassrls` presente — atributo/role que bypassa TODAS as "
                "RLS policies, expondo dados entre clientes."
            )
        problemas.append(
            "AC#6 — Funcao NAO deve executar como superuser / NAO deve "
            "haver EXECUTE AS / NAO deve haver bypassrls.  "
            "Padroes problematicos encontrados: "
            + " | ".join(detalhes_ac6)
        )

    # ── AC#7 — Chamada anon falha (REVOKE ALL FROM PUBLIC + REVOKE EXECUTE FROM anon)
    #     Evidência: AC#1 AND AC#2 ambos verdadeiros
    if not (has_revoke_all_public and has_revoke_anon):
        problemas.append(
            "AC#7 — Chamada anon NAO falhara com erro de permissao.  "
            "Evidencia esperada: AC#1 (REVOKE ALL FROM PUBLIC) AND AC#2 "
            "(REVOKE EXECUTE FROM anon) ambos presentes.  "
            f"Status atual: AC#1={has_revoke_all_public}, AC#2={has_revoke_anon}.  "
            "Sem ambos os REVOKEs, um caller anon poderia invocar a RPC "
            "e receber um erro inesperado de get_my_client_id() em vez de "
            "um erro limpo de permissao (42501)."
        )

    # ── AC#8 — Chamada authenticated funciona (GRANT EXECUTE TO authenticated, service_role)
    #     Evidência: AC#3 verdadeiro
    if not has_grant_authenticated:
        problemas.append(
            "AC#8 — Chamada authenticated NAO funcionara.  "
            "Evidencia esperada: AC#3 (GRANT EXECUTE TO authenticated, "
            "service_role) presente.  "
            f"Status atual: AC#3={has_grant_authenticated}.  "
            "Sem o GRANT EXECUTE apos os REVOKEs, clientes autenticados "
            "receberao erro de permissao ao tentar chamar a RPC."
        )

    # ── Agrega todas as deficiências ─────────────────────────────────
    if problemas:
        cabecalho = (
            f"[RED] B-5 (BATCH #215) — Seguranca RPC public.{FUNCTION_NAME}() "
            f"— {len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  • {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
