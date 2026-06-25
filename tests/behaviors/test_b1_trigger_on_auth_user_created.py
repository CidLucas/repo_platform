"""RED test for behavior B1 — Trigger ``on_auth_user_created`` deve existir
na baseline_v2.sql para conectar ``auth.users`` -> ``handle_new_auth_user()``.

GOAL:
    Garantir que exista o trigger ``on_auth_user_created`` na tabela
    ``auth.users`` definido em
    ``supabase/migrations/20260523999999_baseline_v2.sql``, com disparo
    ``AFTER INSERT`` e execucao da funcao ``public.handle_new_auth_user()``.

    Sem esse trigger, novos signups em ``auth.users`` NAO propagam para
    ``public.clientes_blu`` (a funcao existe mas nunca e' chamada),
    quebrando o fluxo de onboarding de novos clientes da plataforma Blu.

BEHAVIOR:
    B1 — Trigger ``on_auth_user_created`` deve existir em ``auth.users``
    AFTER INSERT EXECUTE FUNCTION ``public.handle_new_auth_user()``.

    Cadeia do fluxo de signup:
        auth.users INSERT
            -> trigger AFTER INSERT ON auth.users (on_auth_user_created)
                -> handle_new_auth_user()
                    -> INSERT INTO public.clientes_blu (...)
                        ON CONFLICT (external_user_id) DO UPDATE
                            SET updated_at = now(),
                                nome_empresa = COALESCE(EXCLUDED.nome_empresa, ...)

AC (Acceptance Criteria):
    AC#1 — O comando ``CREATE TRIGGER on_auth_user_created ON auth.users
            AFTER INSERT EXECUTE FUNCTION public.handle_new_auth_user()``
            existe em ``supabase/migrations/20260523999999_baseline_v2.sql``.
    AC#2 — O trigger referencia explicitamente o evento ``AFTER INSERT``
            (e NAO ``BEFORE INSERT`` ou ``AFTER UPDATE``).
    AC#3 — O trigger faz ``EXECUTE FUNCTION public.handle_new_auth_user()``
            (i.e., a funcao alvo do trigger e' a ``handle_new_auth_user``
            que faz o upsert em ``public.clientes_blu``).

DECISAO:
    Estrategia: source_inspection (leitura do arquivo .sql como texto).
    Arquivo alvo:
        - supabase/migrations/20260523999999_baseline_v2.sql
    Sem mock, sem DB, sem fixtures de runtime.

Estado atual: RED — a funcao ``handle_new_auth_user()`` existe na
baseline_v2.sql (linha 2961), MAS o trigger ``on_auth_user_created`` que
dispara essa funcao em ``AFTER INSERT ON auth.users`` NAO esta definido
no arquivo. O teste falha via ``pytest.fail()`` em pt-BR ate que a
migration seja ajustada na fase GREEN para satisfazer os AC#1..AC#3 do
comportamento B1.
"""

from __future__ import annotations

import re
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

TRIGGER_NAME = "on_auth_user_created"
TRIGGER_TABLE = "auth.users"
TRIGGER_EVENT = "AFTER INSERT"
TRIGGER_FUNCTION = "public.handle_new_auth_user()"

# Regex tolerante a espacos e que captura a linha inteira do CREATE TRIGGER.
# Aceita variantes como:
#   CREATE TRIGGER on_auth_user_created
#       ON auth.users
#       AFTER INSERT
#       EXECUTE FUNCTION public.handle_new_auth_user();
RE_CREATE_TRIGGER = re.compile(
    r"CREATE\s+TRIGGER\s+"
    + re.escape(TRIGGER_NAME)
    + r"\b[^;]*?"
    + r"\bON\s+"
    + re.escape(TRIGGER_TABLE)
    + r"\b[^;]*?"
    + r"\b"
    + re.escape(TRIGGER_EVENT)
    + r"\b[^;]*?"
    + r"EXECUTE\s+FUNCTION\s+"
    + re.escape(TRIGGER_FUNCTION)
    + r"\s*;",
    re.IGNORECASE | re.DOTALL,
)


# ── Override root conftest cleanup (no real Supabase needed) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file I/O, no DB teardown."""
    yield


# ── AC#1 — Trigger on_auth_user_created existe na baseline_v2.sql ───────


def test_b1_ac1_trigger_on_auth_user_created_exists():
    """AC#1: o comando ``CREATE TRIGGER on_auth_user_created ON auth.users
    AFTER INSERT EXECUTE FUNCTION public.handle_new_auth_user()`` deve
    existir em ``supabase/migrations/20260523999999_baseline_v2.sql``.

    Sem esse trigger, a funcao ``handle_new_auth_user()`` (que existe
    na linha 2961) nunca e' invocada em novos signups, e a tabela
    ``public.clientes_blu`` nao recebe o registro do novo cliente.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#1 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text(encoding="utf-8")

    match = RE_CREATE_TRIGGER.search(source)
    assert match, (
        f"AC#1 violated: `CREATE TRIGGER {TRIGGER_NAME} ON {TRIGGER_TABLE} "
        f"{TRIGGER_EVENT} EXECUTE FUNCTION {TRIGGER_FUNCTION}` nao "
        f"encontrado em {BASELINE_PATH}.\n"
        f"  - Esperado: a baseline deve definir o trigger que conecta "
        f"`auth.users` (AFTER INSERT) -> `public.handle_new_auth_user()`.\n"
        f"  - Atual: a funcao `handle_new_auth_user()` existe na linha "
        f"2961, mas nenhum trigger `on_auth_user_created` esta "
        f"registrado em `auth.users` para invoca-la.\n"
        f"  - Consequencia: novos signups nao propagam para "
        f"`public.clientes_blu` e o fluxo de onboarding quebra."
    )


# ── AC#2 — Trigger usa AFTER INSERT (e nao BEFORE/AFTER UPDATE) ────────


def test_b1_ac2_trigger_on_auth_user_created_uses_after_insert():
    """AC#2: o trigger ``on_auth_user_created`` deve referenciar
    explicitamente o evento ``AFTER INSERT`` em ``auth.users``.

    Gatilhos ``BEFORE INSERT`` rodariam antes do insert em
    ``auth.users`` ser confirmado, e ``AFTER UPDATE`` jamais dispararia
    em um signup novo. Apenas ``AFTER INSERT`` garante que o registro
    em ``auth.users`` ja' esteja persistido quando a funcao
    ``handle_new_auth_user()`` e' chamada (a funcao le ``NEW.id``,
    ``NEW.email``, etc.).
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#2 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text(encoding="utf-8")

    # Localiza o bloco do trigger de interesse (case-insensitive).
    pattern_trigger_block = re.compile(
        r"CREATE\s+TRIGGER\s+"
        + re.escape(TRIGGER_NAME)
        + r"\b.*?;",
        re.IGNORECASE | re.DOTALL,
    )
    block_match = pattern_trigger_block.search(source)
    assert block_match, (
        f"AC#2 violated: trigger `{TRIGGER_NAME}` nao encontrado em "
        f"{BASELINE_PATH}. Sem trigger, AC#2 nao pode ser avaliado."
    )

    trigger_block = block_match.group(0)

    # O bloco deve mencionar o evento AFTER INSERT e NAO pode
    # mencionar BEFORE INSERT nem AFTER UPDATE (sao eventos
    # semanticamente diferentes para o caso de uso).
    assert re.search(r"\bAFTER\s+INSERT\b", trigger_block, re.IGNORECASE), (
        f"AC#2 violated: trigger `{TRIGGER_NAME}` em {BASELINE_PATH} "
        f"nao referencia o evento `AFTER INSERT`.\n"
        f"  - Bloco atual: {trigger_block}\n"
        f"  - Esperado: `AFTER INSERT` para que a funcao "
        f"`handle_new_auth_user()` receba o `NEW.id` ja' persistido em "
        f"`auth.users`."
    )

    assert not re.search(r"\bBEFORE\s+INSERT\b", trigger_block, re.IGNORECASE), (
        f"AC#2 violated: trigger `{TRIGGER_NAME}` usa `BEFORE INSERT` "
        f"em {BASELINE_PATH}, mas o esperado e' `AFTER INSERT`. "
        f"`BEFORE INSERT` rodaria antes do insert ser confirmado em "
        f"`auth.users`, e o `NEW.id` ainda nao estaria visivel para "
        f"a funcao `handle_new_auth_user()`."
    )

    assert not re.search(r"\bAFTER\s+UPDATE\b", trigger_block, re.IGNORECASE), (
        f"AC#2 violated: trigger `{TRIGGER_NAME}` usa `AFTER UPDATE` "
        f"em {BASELINE_PATH}, mas o esperado e' `AFTER INSERT`. "
        f"`AFTER UPDATE` nao dispararia em um signup novo (que e' "
        f"um INSERT em `auth.users`, nao um UPDATE)."
    )


# ── AC#3 — Trigger executa public.handle_new_auth_user() ───────────────


def test_b1_ac3_trigger_on_auth_user_created_executes_handle_new_auth_user():
    """AC#3: o trigger ``on_auth_user_created`` deve fazer
    ``EXECUTE FUNCTION public.handle_new_auth_user()``.

    Essa e' a funcao responsavel por fazer o UPSERT em
    ``public.clientes_blu`` a partir de um novo ``auth.users``.
    Apontar o trigger para qualquer outra funcao (ex.:
    ``handle_new_auth_user_v2``, ``seed_clientes_blu``, etc.)
    quebraria o fluxo de onboarding.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#3 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text(encoding="utf-8")

    pattern_trigger_block = re.compile(
        r"CREATE\s+TRIGGER\s+"
        + re.escape(TRIGGER_NAME)
        + r"\b.*?;",
        re.IGNORECASE | re.DOTALL,
    )
    block_match = pattern_trigger_block.search(source)
    assert block_match, (
        f"AC#3 violated: trigger `{TRIGGER_NAME}` nao encontrado em "
        f"{BASELINE_PATH}. Sem trigger, AC#3 nao pode ser avaliado."
    )

    trigger_block = block_match.group(0)

    expected_clause = f"EXECUTE FUNCTION {TRIGGER_FUNCTION}"
    assert expected_clause.lower() in trigger_block.lower(), (
        f"AC#3 violated: trigger `{TRIGGER_NAME}` em {BASELINE_PATH} "
        f"nao faz `{expected_clause}`.\n"
        f"  - Bloco atual: {trigger_block}\n"
        f"  - Esperado: `{expected_clause}` (a funcao que faz o "
        f"UPSERT em `public.clientes_blu` a partir de um novo "
        f"`auth.users`)."
    )


# ── RED: documenta estado atual e orienta a fase GREEN ──────────────────


def test_b1_red_trigger_on_auth_user_created_esta_ausente_na_baseline():
    """RED consolidado para B1: falha explicitamente enquanto o trigger
    ``on_auth_user_created`` nao existir na baseline_v2.sql.

    Estado atual (RED): o trigger NAO esta definido em
    ``supabase/migrations/20260523999999_baseline_v2.sql``. A funcao
    ``public.handle_new_auth_user()`` existe (linha 2961) e esta'
    pronta, mas nao ha' nenhum trigger que a invoque em
    ``AFTER INSERT ON auth.users``.

    Consequencia: novos signups nao populam ``public.clientes_blu`` e
    o onboarding de novos clientes da plataforma Blu quebra.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "RED check requires baseline_v2.sql to exist."
    )

    source = BASELINE_PATH.read_text(encoding="utf-8")

    trigger_present = RE_CREATE_TRIGGER.search(source) is not None

    if trigger_present:
        # Caso a fase GREEN ja' tenha sido aplicada em alguma iteracao
        # anterior, nao falhamos RED — deixamos os testes AC#1..AC#3
        # validarem com mais detalhes.
        return

    pytest.fail(
        f"B1 RED: o trigger `CREATE TRIGGER {TRIGGER_NAME} ON "
        f"{TRIGGER_TABLE} {TRIGGER_EVENT} EXECUTE FUNCTION "
        f"{TRIGGER_FUNCTION}` NAO existe em {BASELINE_PATH.relative_to(REPO_ROOT)}.\n\n"
        f"  - A funcao `public.handle_new_auth_user()` existe na "
        f"linha 2961 da baseline e esta' pronta para fazer o UPSERT "
        f"em `public.clientes_blu` a partir de um novo `auth.users`.\n"
        f"  - Porem, nenhum trigger `on_auth_user_created` esta' "
        f"registrado na tabela `auth.users` para invoca-la em "
        f"`AFTER INSERT`.\n\n"
        f"Estado atual (RED):\n"
        f"  - auth.users INSERT acontece normalmente (via Supabase "
        f"Auth / signup).\n"
        f"  - handle_new_auth_user() NAO e' chamada (nenhum trigger "
        f"a dispara).\n"
        f"  - public.clientes_blu NAO recebe o registro do novo "
        f"cliente.\n"
        f"  - Downstream (auto_enroll_catalog_routines, "
        f"auto_enroll_system_routines, ensure_client_approval_stats, "
        f"seed_client_owner) NAO disparam, pois dependem do INSERT "
        f"em `clientes_blu`.\n\n"
        f"Comportamento desejado (GREEN):\n"
        f"  - Adicionar em {BASELINE_PATH.relative_to(REPO_ROOT)} "
        f"(apos a definicao da funcao `handle_new_auth_user()` e "
        f"antes do bloco de CREATE TRIGGERs das tabelas public.*) "
        f"a seguinte DDL:\n"
        f"      CREATE TRIGGER {TRIGGER_NAME}\n"
        f"          ON {TRIGGER_TABLE}\n"
        f"          {TRIGGER_EVENT}\n"
        f"          FOR EACH ROW\n"
        f"          EXECUTE FUNCTION {TRIGGER_FUNCTION};\n\n"
        f"Risco:\n"
        f"  - 100% dos novos signups nao criam registro em "
        f"`public.clientes_blu`.\n"
        f"  - Login do novo cliente retorna sucesso (auth.users "
        f"existe), mas o backend Blu nao consegue associar o "
        f"usuario a um `client_id`, quebrando RLS e queries "
        f"dependentes.\n"
        f"  - Rotinas automaticas de onboarding (catalog, system "
        f"routines, approval stats, client owner) nunca sao "
        f"enfileiradas.\n\n"
        f"Proximo passo (fase GREEN): ajustar a migration "
        f"supabase/migrations/20260523999999_baseline_v2.sql "
        f"adicionando o `CREATE TRIGGER {TRIGGER_NAME}` descrito "
        f"acima."
    )
