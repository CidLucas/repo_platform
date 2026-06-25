"""RED test for behavior B-3 — onboarding_bootstrap_tx concurrency safety.

GOAL:
    Garantir que a função ``public.onboarding_bootstrap_tx`` (definida em
    ``supabase/migrations/20260523999999_baseline_v2.sql``, linha 3461)
    executa um ``SELECT ... FOR UPDATE`` sobre ``public.clientes_blu``
    ANTES do ``UPDATE public.clientes_blu SET`` que finaliza o body da
    função.

    Hoje, dois submits simultâneos do onboarding (duplo clique, retry de
    rede, dois devices logados no mesmo JWT) podem disparar duas
    transações concorrentes que leem o mesmo ``client_id``/``external_user_id``
    no fallback ``SELECT`` da linha 3489-3491, perdem o lock de linha e
    provocam lost-update em ``clientes_blu`` (campos ``nome_empresa``,
    ``company_profile``, ``team_structure``, ``policies``,
    ``onboarding_completed_at`` podem ser sobrescritos por uma transação
    mais antiga). Em produção, isso também se manifesta como
    inconsistência entre ``client_enabled_agents`` e ``client_routines``
    (counts parciais, routines duplicadas com triggers errados).

    A correção canônica (fase GREEN) é adicionar um
    ``SELECT ... FOR UPDATE`` em ``public.clientes_blu`` antes do
    ``UPDATE SET``, fazendo com que a segunda transação concorrente
    bloqueie até o commit da primeira, e re-leia o estado atualizado
    (read-your-own-writes) ao reentrar.

BEHAVIOR:
    B-3 — Onboarding bootstrap transaction: a função
    ``public.onboarding_bootstrap_tx`` deve fazer row-level lock
    (``FOR UPDATE``) em ``public.clientes_blu`` antes do ``UPDATE SET``
    final, para serializar submits concorrentes e prevenir lost-updates.

AC (Acceptance Criteria):
    AC#1 — A função ``public.onboarding_bootstrap_tx`` está declarada em
            ``supabase/migrations/20260523999999_baseline_v2.sql`` (linha
            3461 no baseline atual).
    AC#2 — O corpo da função (entre ``AS $function$`` e o ``$function$;``
            que a fecha) contém um ``SELECT`` sobre
            ``public.clientes_blu`` que termina com a cláusula
            ``FOR UPDATE`` (com ou sem ``NOWAIT`` / ``SKIP LOCKED``).
    AC#3 — Esse ``SELECT ... FOR UPDATE`` aparece textualmente ANTES do
            ``UPDATE public.clientes_blu SET`` que está no corpo da
            função, garantindo que a linha esteja lockada antes do
            write.
    AC#4 — O conjunto das três condições acima se refere a uma única
            declaração de função (mesmo bloco ``$function$``), não a
            funções distintas.

DECISÃO:
    Estratégia: source_inspection — leitura do arquivo .sql como texto
    puro, extração do bloco da função por marcadores
    ``CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx`` e o
    próximo ``$function$;`` no mesmo arquivo, e validação via regex.
    Sem mock, sem DB, sem fixtures de runtime.

Estado atual: RED — a função ``onboarding_bootstrap_tx`` no baseline
atual (``20260523999999_baseline_v2.sql``) NÃO contém nenhum
``SELECT ... FOR UPDATE`` em ``public.clientes_blu`` antes do
``UPDATE SET``. O teste falha via ``pytest.fail()`` em pt-BR até que
a correção seja aplicada na fase GREEN.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Constants: paths and markers under test ──────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MIGRATION_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

TARGET_FUNCTION_NAME = "public.onboarding_bootstrap_tx"
TARGET_TABLE = "public.clientes_blu"


# ── Regex patterns ───────────────────────────────────────────────────────

# Captura o início da declaração da função alvo. O marcador deve ser
# único no arquivo (o nome da função é único no baseline).
RE_FUNCTION_HEADER = re.compile(
    rf"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+{re.escape(TARGET_FUNCTION_NAME)}\b",
    re.IGNORECASE,
)

# SELECT ... FOR UPDATE sobre public.clientes_blu. Aceita variantes
# comuns: NOWAIT, SKIP LOCKED, OF <col>, etc.
RE_SELECT_FOR_UPDATE = re.compile(
    rf"SELECT\b[^\n;]*\bFROM\s+{re.escape(TARGET_TABLE)}\b[^\n;]*\bFOR\s+UPDATE\b",
    re.IGNORECASE | re.DOTALL,
)

# UPDATE SET sobre public.clientes_blu (o write que precisa estar
# protegido pelo lock).
RE_UPDATE_SET = re.compile(
    rf"UPDATE\s+{re.escape(TARGET_TABLE)}\s+SET\b",
    re.IGNORECASE,
)


# ── Override root conftest cleanup (no real Supabase needed) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure source-inspection tests, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_function_body(sql: str, function_name: str) -> tuple[str, int, int]:
    """Extrai o corpo da função ``function_name`` delimitado pelos
    marcadores ``AS $function$`` (abertura) e o próximo ``$function$;``
    (fechamento) que aparece depois do header.

    Retorna uma tupla ``(body, start_line, end_line)`` onde ``start_line``
    é a linha do header ``CREATE OR REPLACE FUNCTION ...`` e ``end_line``
    é a linha do ``$function$;`` de fechamento. Retorna ``("", -1, -1)``
    se a função não for encontrada.
    """
    header_match = RE_FUNCTION_HEADER.search(sql)
    if header_match is None:
        return "", -1, -1

    header_start = header_match.start()

    # Procura o "AS $function$" de abertura após o header.
    body_open = sql.find("$function$", header_start)
    if body_open == -1:
        return "", -1, -1

    # Procura o "$function$;" de fechamento após a abertura.
    body_close = sql.find("$function$;", body_open + len("$function$"))
    if body_close == -1:
        return "", -1, -1

    body = sql[header_start:body_close + len("$function$;")]

    # Converte offsets para números de linha (1-indexed) para reportar
    # de forma amigável no pytest.fail.
    start_line = sql.count("\n", 0, header_start) + 1
    end_line = sql.count("\n", 0, body_close) + 1
    return body, start_line, end_line


# ── Tests ────────────────────────────────────────────────────────────────


def test_b3_ac1_function_declared_in_baseline():
    """AC#1 — A função ``public.onboarding_bootstrap_tx`` está declarada
    no baseline ``20260523999999_baseline_v2.sql`` (linha 3461).
    """
    assert MIGRATION_PATH.exists(), (
        f"Migration de baseline não encontrada em {MIGRATION_PATH}. "
        f"Verifique a estrutura do repositório."
    )

    sql = _read_sql(MIGRATION_PATH)
    header_match = RE_FUNCTION_HEADER.search(sql)
    assert header_match is not None, (
        f"Função {TARGET_FUNCTION_NAME} não encontrada em {MIGRATION_PATH.name}. "
        f"AC#1 falhou: a função de bootstrap do onboarding deveria estar "
        f"declarada no baseline atual (linha 3461)."
    )

    # Confirma que o header está aproximadamente na linha 3461 do baseline
    # (pode variar com merges, então aceitamos uma janela razoável).
    header_line = sql.count("\n", 0, header_match.start()) + 1
    assert 3450 <= header_line <= 3470, (
        f"Header de {TARGET_FUNCTION_NAME} encontrado na linha {header_line}, "
        f"fora da janela esperada (3450..3470) do baseline "
        f"20260523999999_baseline_v2.sql. AC#1 falhou."
    )


def test_b3_ac2_select_for_update_presente_antes_do_update():
    """AC#2 + AC#3 + AC#4 — Dentro do corpo da função
    ``onboarding_bootstrap_tx`` deve existir um ``SELECT ... FOR UPDATE``
    em ``public.clientes_blu`` que apareça textualmente ANTES do
    ``UPDATE public.clientes_blu SET``.
    """
    sql = _read_sql(MIGRATION_PATH)
    body, start_line, end_line = _extract_function_body(sql, TARGET_FUNCTION_NAME)

    assert body, (
        f"Corpo da função {TARGET_FUNCTION_NAME} não pôde ser extraído de "
        f"{MIGRATION_PATH.name}. Verifique os marcadores AS $function$ / "
        f"$function$; no baseline."
    )

    # Localiza o UPDATE SET dentro do corpo da função.
    update_match = RE_UPDATE_SET.search(body)
    assert update_match is not None, (
        f"B-3 RED: o corpo de {TARGET_FUNCTION_NAME} (linhas {start_line}.."
        f"{end_line} em {MIGRATION_PATH.name}) não contém "
        f"``UPDATE {TARGET_TABLE} SET ...`` — AC#3 do comportamento B-3 "
        f"não pode ser avaliada sem o write alvo. Provável regressão "
        f"estrutural na baseline."
    )

    update_offset = update_match.start()

    # Procura um SELECT ... FOR UPDATE em public.clientes_blu ANTES do UPDATE.
    select_match = RE_SELECT_FOR_UPDATE.search(body, 0, update_offset)

    if select_match is None:
        # Reporta o snippet do trecho problemático para acelerar a fix
        # na fase GREEN.
        head = body[:update_offset]
        tail = body[update_offset:update_offset + 200]
        snippet = f"...{head[-300:]!r}\n>>> UPDATE_SET AQUI <<<\n{tail!r}..."
        pytest.fail(
            f"B-3 RED: a função {TARGET_FUNCTION_NAME} "
            f"(linhas {start_line}..{end_line} em {MIGRATION_PATH.name}) "
            f"NÃO contém um ``SELECT ... FOR UPDATE`` em {TARGET_TABLE} "
            f"antes do ``UPDATE SET`` final. Hoje, submits concorrentes do "
            f"onboarding podem disparar duas transações que leem o mesmo "
            f"client_id no fallback SELECT e provocam lost-update em "
            f"clientes_blu (campos nome_empresa, company_profile, "
            f"team_structure, policies, onboarding_completed_at). "
            f"Correção esperada (fase GREEN): adicionar logo antes do "
            f"UPDATE SET um lock de linha, por ex.:\n"
            f"    SELECT client_id FROM {TARGET_TABLE}\n"
            f"    WHERE client_id = v_client_id\n"
            f"    FOR UPDATE;\n"
            f"AC#2 (FOR UPDATE presente), AC#3 (FOR UPDATE antes do "
            f"UPDATE SET) e AC#4 (mesma função) falharam.\n"
            f"Snippet do corpo: {snippet}"
        )

    # AC#4 — Confirma que tanto o SELECT FOR UPDATE quanto o UPDATE SET
    # estão dentro do mesmo bloco $function$ (já garantido por estarmos
    # extraindo o body inteiro, mas reforçamos a asserção).
    assert select_match.start() < update_match.end(), (
        f"B-3 RED: SELECT ... FOR UPDATE encontrado em offset "
        f"{select_match.start()}, mas UPDATE SET em offset "
        f"{update_match.start()} dentro de {TARGET_FUNCTION_NAME}. "
        f"AC#3 falhou: o lock precisa aparecer antes do write."
    )
