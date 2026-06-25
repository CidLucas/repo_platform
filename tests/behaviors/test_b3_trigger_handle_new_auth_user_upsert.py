"""RED test for behavior B3 — Trigger handle_new_auth_user deve usar ON CONFLICT DO UPDATE.

GOAL:
    Garantir que a funcao-trigger ``public.handle_new_auth_user()`` definida
    em ``supabase/migrations/20260523999999_baseline_v2.sql`` utilize a
    estrategia de upsert ``ON CONFLICT (external_user_id) DO UPDATE`` ao
    inserir em ``public.clientes_blu`` a partir de um novo
    ``auth.users``.

    O comportamento desejado e' o de UPSERT: quando o mesmo
    ``auth.users.id`` (external_user_id) tenta reinserir em
    ``clientes_blu`` (por exemplo, em re-signup, recovery, ou seed
    retroativo), o trigger deve ATUALIZAR os campos aplicaveis
    (``updated_at``, ``nome_empresa`` derivado de ``NEW.email``) em vez
    de descartar o INSERT com ``DO NOTHING``. Isso preserva o
    ``api_key`` original e demais campos sensiveis, e garante que
    ``updated_at`` reflita o ultimo contato do usuario.

BEHAVIOR:
    B3 — Trigger handle_new_auth_user deve aplicar ON CONFLICT DO UPDATE
    (upsert) em clientes_blu.

    Cadeia do fluxo de signup:
        auth.users INSERT
            -> trigger AFTER INSERT ON auth.users
                -> handle_new_auth_user()
                    -> INSERT INTO public.clientes_blu (...)
                        ON CONFLICT (external_user_id) DO UPDATE
                            SET updated_at = now(),
                                nome_empresa = COALESCE(EXCLUDED.nome_empresa, ...)

AC (Acceptance Criteria):
    AC#1 — A funcao ``public.handle_new_auth_user()`` existe em
            ``supabase/migrations/20260523999999_baseline_v2.sql``.
    AC#2 — Dentro do corpo da funcao, o INSERT em ``public.clientes_blu``
            usa ``ON CONFLICT (external_user_id) DO UPDATE`` (e NAO
            ``DO NOTHING``).
    AC#3 — A clausula ``DO UPDATE`` referencia ``EXCLUDED.<coluna>``
            pelo menos uma vez, garantindo que o upsert sobrescreve
            campos vindos do ``NEW`` (e nao apenas reseta tudo).
    AC#4 — A clausula ``DO UPDATE`` inclui ``updated_at`` como uma das
            colunas atualizadas (sinal de que o trigger reage a novos
            signups do mesmo external_user_id).

DECISAO:
    Estrategia: source_inspection (leitura do arquivo .sql como texto).
    Arquivo alvo:
        - supabase/migrations/20260523999999_baseline_v2.sql
    Sem mock, sem DB, sem fixtures de runtime.

Estado atual: RED — a funcao ``handle_new_auth_user()`` na baseline_v2.sql
(linha 2961) AINDA usa ``ON CONFLICT (external_user_id) DO NOTHING`` na
linha 2989, em vez de ``DO UPDATE``. O teste falha via ``pytest.fail()``
em pt-BR ate que a migration seja ajustada na fase GREEN para satisfazer
os AC#1..AC#4 do comportamento B3.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ── Constants: the public interface under test ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

BASELINE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

FUNCTION_MARKER = "CREATE OR REPLACE FUNCTION public.handle_new_auth_user()"

CONFLICT_TARGET = "external_user_id"
TARGET_TABLE = "public.clientes_blu"


# ── Override root conftest cleanup (no real Supabase needed) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file I/O, no DB teardown."""
    yield


# ── Helpers ─────────────────────────────────────────────────────────────


def _extract_function_body(source: str, marker: str) -> str:
    """Dado um trecho SQL e um marcador que aparece na primeira linha de uma
    funcao (ex.: ``CREATE OR REPLACE FUNCTION public.handle_new_auth_user()``),
    retorna o corpo da funcao como string — desde a linha do marcador ate
    (mas excluindo) a proxima linha que fecha o bloco (``$function$;``).

    Estrategia intencionalmente frouxa: queremos apenas um substring que
    inclua todo o corpo da funcao para que possamos procurar dentro dele
    por padroes SQL especificos (ex.: ``ON CONFLICT ... DO UPDATE``).
    """
    idx = source.find(marker)
    if idx == -1:
        return ""
    lines = source[idx:].split("\n")
    body_lines = [lines[0]]
    for line in lines[1:]:
        stripped = line.rstrip()
        body_lines.append(stripped)
        if stripped == "$function$;":
            break
    return "\n".join(body_lines)


# ── AC#1 — handle_new_auth_user existe na baseline_v2.sql ───────────────


def test_b3_ac1_handle_new_auth_user_function_exists():
    """AC#1: a funcao ``public.handle_new_auth_user()`` deve existir em
    ``supabase/migrations/20260523999999_baseline_v2.sql``.

    Sem essa funcao, o trigger ``on_auth_user_created`` (que escuta
    ``auth.users``) nao tem implementacao e novos signups nao criam
    registros em ``public.clientes_blu``.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#1 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text(encoding="utf-8")

    assert FUNCTION_MARKER in source, (
        f"AC#1 violated: marker `{FUNCTION_MARKER}` not found in "
        f"{BASELINE_PATH}. Esperado na linha 2961 da baseline. Sem essa "
        f"funcao, o trigger `on_auth_user_created` nao tem implementacao "
        f"e novos signups nao populam `public.clientes_blu`."
    )


# ── AC#2..AC#4 — handle_new_auth_user usa ON CONFLICT DO UPDATE ─────────


def test_b3_ac2_to_ac4_handle_new_auth_user_uses_on_conflict_do_update():
    """AC#2..AC#4: dentro do corpo de ``public.handle_new_auth_user()``,
    o INSERT em ``public.clientes_blu`` deve usar
    ``ON CONFLICT (external_user_id) DO UPDATE`` (UPSERT), e nao
    ``DO NOTHING``.

    Pre-condicoes verificadas:
      - AC#1: funcao existe na baseline_v2.sql.
      - AC#2: clausula ``ON CONFLICT (external_user_id) DO UPDATE``
              presente no corpo.
      - AC#3: a clausula ``DO UPDATE`` referencia ``EXCLUDED.`` pelo
              menos uma vez (sinal de que o upsert usa os valores do
              INSERT proposto).
      - AC#4: a clausula ``DO UPDATE`` inclui ``updated_at`` como uma
              das colunas atualizadas.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#2..AC#4 require inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text(encoding="utf-8")

    # AC#1 (re-checked within this test for self-containment)
    assert FUNCTION_MARKER in source, (
        f"AC#1 violated: marker `{FUNCTION_MARKER}` not found in "
        f"{BASELINE_PATH}."
    )

    # Extrai o corpo da funcao para escopo de busca.
    function_body = _extract_function_body(source, FUNCTION_MARKER)
    assert function_body, (
        "AC#2 violated: nao foi possivel extrair o corpo de "
        "handle_new_auth_user() a partir de "
        f"{BASELINE_PATH}. Esperado bloco delimitado por "
        "`AS $function$` ... `$function$;`."
    )

    # AC#2 — ON CONFLICT (external_user_id) DO UPDATE presente.
    expected_on_conflict = f"ON CONFLICT ({CONFLICT_TARGET}) DO UPDATE"
    assert expected_on_conflict in function_body, (
        f"AC#2 violated: `{expected_on_conflict}` nao encontrado dentro "
        f"de handle_new_auth_user() em {BASELINE_PATH}.\n"
        f"  - Comportamento atual esperado: a funcao usa "
        f"`ON CONFLICT ({CONFLICT_TARGET}) DO NOTHING`, o que descarta "
        f"o INSERT no segundo signup com o mesmo `auth.users.id`.\n"
        f"  - Comportamento desejado: a funcao deve fazer UPSERT via "
        f"`ON CONFLICT ({CONFLICT_TARGET}) DO UPDATE`, preservando o "
        f"`api_key` original e atualizando `updated_at` (e demais "
        f"campos aplicaveis).\n"
        f"  - Sem isso, um re-signup (ex.: recovery, re-onboarding) "
        f"perdera o `updated_at` e qualquer coluna sincronizada via "
        f"`NEW.<coluna>`."
    )

    # AC#3 — DO UPDATE referencia EXCLUDED.<coluna> pelo menos uma vez.
    # Captura o trecho "DO UPDATE SET ... " (ate a proxima linha em
    # branco ou ate "RETURNING", o que vier primeiro) e verifica
    # presenca de EXCLUDED.
    do_update_match_start = function_body.find(expected_on_conflict)
    assert do_update_match_start != -1, (
        f"AC#3 pre-check violated: `{expected_on_conflict}` ausente no "
        f"corpo de handle_new_auth_user()."
    )

    # Pega ate 800 caracteres apos o "DO UPDATE" — cobre SET clause,
    # multiplas colunas e EXCLUDED.<col>.
    do_update_section = function_body[
        do_update_match_start:do_update_match_start + 800
    ]
    # Corta no RETURNING ou no final do bloco para nao vazar.
    for terminator in ("RETURNING", "$function$;"):
        cut_at = do_update_section.find(terminator)
        if cut_at != -1:
            do_update_section = do_update_section[:cut_at]

    assert "EXCLUDED." in do_update_section, (
        "AC#3 violated: a clausula `DO UPDATE` nao referencia "
        "`EXCLUDED.<coluna>`. Sem `EXCLUDED.`, o upsert nao tem como "
        "acessar os valores propostos pelo INSERT (ex.: `NEW.email` "
        "mapeado para `nome_empresa`). O `DO UPDATE` deve usar "
        "pelo menos `EXCLUDED.<alguma_coluna>` para refletir o novo "
        "signup.\n"
        f"Trecho inspecionado em {BASELINE_PATH} (ate 800 chars apos "
        f"`{expected_on_conflict}`):\n  {do_update_section}"
    )

    # AC#4 — DO UPDATE inclui `updated_at` como uma das colunas.
    # Regex robusta: aceita `updated_at = ` seguido de now(),
    # EXCLUDED.updated_at, ou expressao similar.
    import re

    RE_DO_UPDATE_UPDATED_AT = re.compile(
        r"updated_at\s*=\s*(?:now\s*\(\s*\)|EXCLUDED\.updated_at|EXCLUDED\.[a-zA-Z_]+)",
        re.IGNORECASE,
    )
    assert RE_DO_UPDATE_UPDATED_AT.search(do_update_section), (
        "AC#4 violated: a clausula `DO UPDATE` nao inclui `updated_at` "
        "como uma das colunas atualizadas. Esperado um padrao como "
        "`updated_at = now()` ou `updated_at = EXCLUDED.updated_at` "
        "dentro do `DO UPDATE`.\n"
        f"Trecho inspecionado em {BASELINE_PATH}:\n  {do_update_section}"
    )

    # ── RED: falhas semanticamente corretas foram captadas acima; este
    # pytest.fail() final documenta o estado atual e o que se espera
    # da fase GREEN.
    pytest.fail(
        "B3 RED: handle_new_auth_user() na baseline_v2.sql AINDA usa "
        "`ON CONFLICT (external_user_id) DO NOTHING` (linha 2989), em "
        "vez de `ON CONFLICT (external_user_id) DO UPDATE`.\n\n"
        f"Arquivo: {BASELINE_PATH.relative_to(REPO_ROOT)} (linhas 2961-3018)\n\n"
        "Estado atual (RED):\n"
        "  - INSERT INTO public.clientes_blu ...\n"
        "      ON CONFLICT (external_user_id) DO NOTHING\n"
        "      RETURNING client_id INTO v_client_id;\n"
        "  - No segundo signup com mesmo auth.users.id: o INSERT e' "
        "descartado; o codigo faz SELECT do client_id existente.\n"
        "  - Consequencia: `updated_at` NAO e' atualizado no re-signup; "
        "qualquer coluna sincronizada via `NEW.<coluna>` nao reflete "
        "o novo signup (ex.: nome_empresa derivado de NEW.email).\n\n"
        "Comportamento desejado (GREEN):\n"
        "  - Substituir `DO NOTHING` por `DO UPDATE SET updated_at = "
        "now(), nome_empresa = COALESCE(EXCLUDED.nome_empresa, "
        "clientes_blu.nome_empresa)` (ou equivalente).\n"
        "  - Manter o SELECT de fallback para o `v_client_id` em caso "
        "de conflito (idempotencia).\n"
        "  - Preservar o `api_key` original (NAO sobrescrever com "
        "novo gen_random_uuid()).\n\n"
        "Risco:\n"
        "  - Re-signup (recovery, re-onboarding, hot-fix manual via "
        "supabase) nao refresca `updated_at`.\n"
        "  - Sincronizacoes de metadados do auth.users (ex.: "
        "email rename via Supabase dashboard) nao propagam para "
        "clientes_blu.nome_empresa.\n"
        "  - Relatorios que filtram por `updated_at > X` perdem "
        "eventos de re-signup.\n\n"
        "Proximo passo (fase GREEN): ajustar a migration "
        "supabase/migrations/20260523999999_baseline_v2.sql na "
        "linha 2989 para usar `DO UPDATE` com `EXCLUDED.<coluna>` e "
        "`updated_at = now()`."
    )


# ── Sanity check — ON CONFLICT DO NOTHING nao deve coexistir com DO UPDATE
# dentro do mesmo INSERT (sanidade estrutural) ───────────────────────────


def test_b3_sanity_no_mixed_do_nothing_do_update_in_handle_new_auth_user():
    """Sanity: dentro do corpo de ``handle_new_auth_user()``, nao deve
    coexistir um INSERT com ``ON CONFLICT ... DO NOTHING`` e outro
    INSERT com ``ON CONFLICT ... DO UPDATE`` referenciando
    ``clientes_blu``. Se houver confusao entre as estrategias, o
    trigger pode se comportar de forma inconsistente entre
    primeiro e segundo signup.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "Sanity check requires baseline_v2.sql to exist."
    )

    source = BASELINE_PATH.read_text(encoding="utf-8")
    function_body = _extract_function_body(source, FUNCTION_MARKER)
    assert function_body, (
        "Sanity violated: nao foi possivel extrair o corpo de "
        "handle_new_auth_user() a partir de "
        f"{BASELINE_PATH}."
    )

    has_do_nothing = (
        f"ON CONFLICT ({CONFLICT_TARGET}) DO NOTHING" in function_body
    )
    has_do_update = (
        f"ON CONFLICT ({CONFLICT_TARGET}) DO UPDATE" in function_body
    )

    # Estado esperado na fase GREEN: APENAS DO UPDATE.
    # Estado atual (RED): APENAS DO NOTHING.
    # Estado INVALIDO (sanity): ambos os dois (mistura).
    assert not (has_do_nothing and has_do_update), (
        "Sanity violated: handle_new_auth_user() contem simultaneamente "
        f"`ON CONFLICT ({CONFLICT_TARGET}) DO NOTHING` E "
        f"`ON CONFLICT ({CONFLICT_TARGET}) DO UPDATE` em "
        f"{BASELINE_PATH}. Mantenha apenas uma estrategia: apos a fase "
        f"GREEN, o trigger deve usar exclusivamente `DO UPDATE`."
    )

    # GREEN-equivalente sanity: apos a fase GREEN, `has_do_update` sera
    # True e `has_do_nothing` sera False. No estado RED atual,
    # `has_do_nothing` e' True e `has_do_update` e' False.
    # O teste RED abaixo documenta o estado atual.
    pytest.fail(
        "B3 Sanity RED: handle_new_auth_user() em "
        f"{BASELINE_PATH.relative_to(REPO_ROOT)} usa exclusivamente "
        f"`ON CONFLICT ({CONFLICT_TARGET}) DO NOTHING` "
        f"(has_do_nothing={has_do_nothing}, has_do_update={has_do_update}). "
        f"A fase GREEN deve substituir por `DO UPDATE`.\n\n"
        f"  - has_do_nothing: {has_do_nothing}\n"
        f"  - has_do_update:  {has_do_update}\n"
        f"  - mistura (invalida): {has_do_nothing and has_do_update}\n"
    )
