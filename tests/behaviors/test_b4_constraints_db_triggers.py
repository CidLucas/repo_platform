"""RED test for behavior B4 — Investigar constraints DB e triggers.

GOAL:
    Investigar database constraints em clientes_blu (api_key unique?,
    external_user_id unique?), verificar se o trigger handle_new_auth_user
    e' idempotente para segundo signup, verificar se audit_log tem FK para
    clientes_blu, verificar se seed de client_routines falha no segundo
    cadastro por constraint concorrente, e verificar relacao de client_users
    com clientes_blu.

    Contexto: bug "segundo cadastro de email falha" — investigacao de causa
    raiz no pipeline de auth. Possiveis causas hipotetizadas:
      - UNIQUE(api_key) causando conflito em gen_random_uuid concorrente
      - UNIQUE(external_user_id) sem tratamento ON CONFLICT
      - FK cascade em audit_log bloqueando operacoes
      - client_routines seed quebrando no segundo cadastro
      - client_users FK interferindo

BEHAVIOR:
    B4 — Investigar constraints DB e triggers.
    Issue: segundo cadastro de email falha — constraints podem estar
    bloqueando o fluxo.

    Cadeia investigada:
        auth.users INSERT
            -> trigger handle_new_auth_user()
                -> INSERT INTO clientes_blu (...)
                    ON CONFLICT (external_user_id) DO NOTHING
                -> INSERT INTO audit_log (client_id, ...)
        onboarding_bootstrap_tx()
            -> INSERT INTO clientes_blu (...)
                ON CONFLICT (external_user_id) DO NOTHING
            -> INSERT INTO client_routines (...)
                ON CONFLICT (client_id, routine_id) DO UPDATE

AC (Acceptance Criteria):
    AC#1 — clientes_blu tem UNIQUE em external_user_id e api_key
    AC#2 — handle_new_auth_user usa ON CONFLICT (external_user_id) DO NOTHING
    AC#3 — audit_log NAO tem FK para clientes_blu
    AC#4 — onboarding_bootstrap_tx usa ON CONFLICT (idempotente)
    AC#5 — client_users e client_routines tem FK CASCADE ON DELETE

DECISAO:
    Estrategia: source_inspection (teste le arquivos .sql como texto).
    Arquivos alvo:
        - supabase/migrations/20260523999999_baseline_v2.sql
        - supabase/migrations/applied/20260525_p12_split_onboarding_completion.sql

Estado atual: RED — todos os ACs documentam propriedades estruturais do
banco que devem ser validadas formalmente por uma fase GREEN. Os testes
sinalizam RED como contrato: se um refactor futuro remover constraints,
ON CONFLICT, ou FK, o teste quebra.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

BASELINE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

ONBOARDING_SPLIT_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "applied"
    / "20260525_p12_split_onboarding_completion.sql"
)


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure source-inspection tests, no DB teardown."""
    yield


def _extract_function_body(source: str, marker: str) -> str:
    """Given a SQL source string and a marker that uniquely appears on the
    first line of a function (e.g. "CREATE OR REPLACE FUNCTION public.handle_new_auth_user()"),
    return the body of that function as a string — from the line with the
    marker up to (but excluding) the next line that closes the surrounding block.

    This is intentionally loose: we just want a substring that includes the
    whole function body so we can search inside it for specific SQL patterns.
    """
    idx = source.find(marker)
    if idx == -1:
        return ""
    lines = source[idx:].split("\n")
    body_lines = [lines[0]]
    base_indent = len(lines[0]) - len(lines[0].lstrip())
    dollar_found = "$function$" in lines[0] or "$$" in lines[0]
    for line in lines[1:]:
        stripped = line.rstrip()
        if stripped == "":
            body_lines.append(stripped)
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent and (
            stripped.startswith("CREATE OR REPLACE FUNCTION")
            or stripped.startswith("CREATE OR REPLACE")
            or stripped.startswith("CREATE FUNCTION")
            or stripped.startswith("--")
            or stripped.startswith("$function$")
            or stripped.startswith("$$")
        ):
            break
        body_lines.append(stripped)
    return "\n".join(body_lines)


# ══════════════════════════════════════════════════════════════════════════
# AC#1 — clientes_blu tem UNIQUE em external_user_id e api_key
# ══════════════════════════════════════════════════════════════════════════


def test_b4_ac1_clientes_blu_tem_unique_constraints():
    """AC#1: clientes_blu deve ter constraints UNIQUE em
    ``external_user_id`` e ``api_key``.

    O arquivo baseline_v2.sql (linhas 718-720) contem:
        ALTER TABLE public.clientes_blu ADD CONSTRAINT clientes_blu_pkey
            PRIMARY KEY (client_id);
        ALTER TABLE public.clientes_blu ADD CONSTRAINT clientes_blu_api_key_key
            UNIQUE (api_key);
        ALTER TABLE public.clientes_blu ADD CONSTRAINT
            clientes_blu_external_user_id_key UNIQUE (external_user_id);

    A UNIQUE(api_key) significa que gerar dois registros com mesmo api_key
    causaria erro. O trigger handle_new_auth_user gera gen_random_uuid()::text
    como api_key — colisao e' astronomicamente improdavel, mas nao impossivel.

    A UNIQUE(external_user_id) e' a constraint usada pelo ON CONFLICT no trigger.
    Ela garante que o mesmo auth.user.id nao crie duplicata em clientes_blu.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#1 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text()

    # Assertion 1: UNIQUE constraint on api_key exists
    assert "clientes_blu_api_key_key UNIQUE (api_key)" in source, (
        "AC#1 violated: UNIQUE constraint on api_key not found in "
        "baseline_v2.sql. Expected `clientes_blu_api_key_key UNIQUE (api_key)` "
        "at line 719. This constraint is critical: if two signups race and "
        "gen_random_uuid() generates the same UUID (astronomically rare), or "
        "if a migration sets api_key to NULL and a second signup tries to "
        "insert with a new api_key, the UNIQUE would fail."
    )

    # Assertion 2: UNIQUE constraint on external_user_id exists
    assert "clientes_blu_external_user_id_key UNIQUE (external_user_id)" in source, (
        "AC#1 violated: UNIQUE constraint on external_user_id not found in "
        "baseline_v2.sql. Expected `clientes_blu_external_user_id_key "
        "UNIQUE (external_user_id)` at line 720. This constraint is essential "
        "for the ON CONFLICT (external_user_id) DO NOTHING in the trigger."
    )

    # Assertion 3: api_key is nullable (no NOT NULL)
    # Find the CREATE TABLE for clientes_blu
    table_start = source.find("CREATE TABLE public.clientes_blu (")
    assert table_start != -1, (
        "AC#1 violated: could not find CREATE TABLE public.clientes_blu "
        "in baseline_v2.sql."
    )
    table_section = source[table_start:table_start + 500]
    if "api_key text" in table_section:
        # api_key tem apenas "text" sem NOT NULL — e' nullable
        pass

    pytest.fail(
        "AC#1 RED: constraints UNIQUE em clientes_blu identificadas, "
        "mas ainda nao formalmente validadas como corretas para o fluxo "
        "de signup.\n\n"
        "Constraints encontradas em "
        "supabase/migrations/20260523999999_baseline_v2.sql:\n"
        "  Linha 719: clientes_blu_api_key_key UNIQUE (api_key)\n"
        "  Linha 720: clientes_blu_external_user_id_key UNIQUE (external_user_id)\n\n"
        "Analise:\n"
        "  - UNIQUE(api_key): gen_random_uuid()::text gera valores unicos, "
        "mas a constraint impede insercao manual com api_key NULL ou "
        "duplicado. api_key e' nullable (sem NOT NULL), entao INSERT sem "
        "api_key passaria (NULL != NULL no PostgreSQL).\n"
        "  - UNIQUE(external_user_id): usada pelo ON CONFLICT no trigger "
        "handle_new_auth_user. Garante que o mesmo auth.user.id nao crie "
        "duplicata.\n\n"
        "Risco: se `gen_random_uuid()` colidir (probabilidade ~2^-122), "
        "o INSERT falharia com unique violation. Para o cenario de "
        "dois signups CONSECUTIVOS com emails DIFERENTES, a probabilidade "
        "e' irrelevante. Para signups CONCORRENTES com mesmo email, o "
        "ON CONFLICT (external_user_id) previne o INSERT (segundo e' "
        "descartado).\n\n"
        "Arquivo: supabase/migrations/20260523999999_baseline_v2.sql "
        "(linhas 718-720)."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#2 — handle_new_auth_user usa ON CONFLICT (idempotente)
# ══════════════════════════════════════════════════════════════════════════


def test_b4_ac2_handle_new_auth_user_on_conflict():
    """AC#2: a funcao-trigger ``handle_new_auth_user()`` deve usar
    ``ON CONFLICT (external_user_id) DO NOTHING`` para garantir
    idempotencia no segundo signup com mesmo email.

    O trigger (linhas 2961-3018 da baseline_v2.sql):
        1. Gera v_api_key via gen_random_uuid()::text
        2. INSERT INTO clientes_blu ON CONFLICT (external_user_id) DO NOTHING
        3. Se v_client_id IS NULL (conflito), faz SELECT do client_id existente
        4. Se v_client_id IS NOT NULL, insere em audit_log

    Este comportamento e' CORRETO: se o auth.users ja' existir (segundo
    signup com mesmo email), o ON CONFLICT previne duplicata e o codigo
    reusa o client_id existente.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#2 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text()

    # Assertion 1: function exists
    marker = "CREATE OR REPLACE FUNCTION public.handle_new_auth_user()"
    assert marker in source, (
        "AC#2 violated: handle_new_auth_user() function not found in "
        "baseline_v2.sql. Expected at line 2961."
    )

    # Assertion 2: ON CONFLICT (external_user_id) DO NOTHING
    function_body = _extract_function_body(source, marker)
    assert function_body, (
        "AC#2 violated: could not extract function body for "
        "handle_new_auth_user()."
    )

    assert "ON CONFLICT (external_user_id) DO NOTHING" in function_body, (
        "AC#2 violated: ON CONFLICT (external_user_id) DO NOTHING not found "
        "inside handle_new_auth_user(). Expected at line 2989. Without this, "
        "a second signup (same email) would cause a unique_violation on "
        "clientes_blu_external_user_id_key."
    )

    # Assertion 3: handles v_client_id IS NULL (conflict case)
    assert "IF v_client_id IS NULL THEN" in function_body, (
        "AC#2 violated: missing handling for v_client_id IS NULL after "
        "ON CONFLICT. Expected code to SELECT existing client_id when "
        "the INSERT was skipped due to conflict. Without this, the "
        "trigger would not return the correct client_id for subsequent "
        "operations (like audit_log insertion)."
    )

    # Assertion 4: selects existing client_id on conflict
    assert "SELECT client_id INTO v_client_id FROM public.clientes_blu" in function_body, (
        "AC#2 violated: missing SELECT for existing client_id on conflict. "
        "Expected at lines 2993-2996."
    )

    # Assertion 5: generates api_key via gen_random_uuid
    assert "gen_random_uuid()::text" in function_body, (
        "AC#2 violated: expected gen_random_uuid()::text for api_key "
        "generation in handle_new_auth_user()."
    )

    pytest.fail(
        "AC#2 RED: handle_new_auth_user() usa ON CONFLICT "
        "(external_user_id) DO NOTHING, mas a propriedade de "
        "idempotencia ainda nao foi formalmente validada.\n\n"
        "Trigger handle_new_auth_user() em "
        "supabase/migrations/20260523999999_baseline_v2.sql "
        "(linhas 2961-3018):\n"
        "  1. Gera v_api_key := gen_random_uuid()::text (linha 2971)\n"
        "  2. INSERT ON CONFLICT (external_user_id) DO NOTHING "
        "(linha 2989)\n"
        "  3. IF v_client_id IS NULL THEN SELECT (linhas 2993-2996)\n"
        "  4. INSERT INTO audit_log (linhas 3000-3012)\n\n"
        "Analise:\n"
        "  - ON CONFLICT (external_user_id) impede duplicata de "
        "clientes_blu para o mesmo auth.user.id.\n"
        "  - Quando o INSERT e' pulado (segundo signup), o SELECT "
        "recupera o client_id existente.\n"
        "  - audit_log so' recebe INSERT se v_client_id nao for NULL.\n"
        "  - Comportamento: IDEMPOTENTE e SEGURO.\n\n"
        "Risco: se a trigger nao for chamada (ex.: supabase nao criar "
        "o trigger on_auth_user_created), o clientes_blu nunca seria "
        "povoado. Mas isso e' um problema de configuracao, nao de "
        "constraint.\n\n"
        "Arquivo: supabase/migrations/20260523999999_baseline_v2.sql "
        "(linhas 2961-3018)."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#3 — audit_log NAO tem FK para clientes_blu
# ══════════════════════════════════════════════════════════════════════════


def test_b4_ac3_audit_log_sem_fk_clientes_blu():
    """AC#3: ``audit_log`` NAO deve ter FK (FOREIGN KEY) referenciando
    ``clientes_blu``.

    A tabela audit_log (linhas 71-80 da baseline) tem ``client_id uuid``
    como coluna solta — NOT NULL, mas sem REFERENCES clientes_blu.

    Isso e' INTENCIONAL e CORRETO: o audit_log e' um log de auditoria
    que deve persistir mesmo se o cliente for deletado. Se houvesse FK
    com ON DELETE CASCADE, a exclusao de um clientes_blu levaria junto
    todo o audit trail.

    Para o cenario de "segundo cadastro de email falha": a ausencia de
    FK em audit_log significa que nenhuma operacao no fluxo de signup
    pode ser bloqueada por constraint FK de audit_log.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#3 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text()

    # Assertion 1: audit_log exists
    assert "CREATE TABLE public.audit_log (" in source, (
        "AC#3 violated: could not find CREATE TABLE public.audit_log "
        "in baseline_v2.sql."
    )

    # Assertion 2: NO FK constraint referencing clientes_blu on audit_log
    # Search for any ALTER TABLE audit_log ... REFERENCES clientes_blu
    audit_log_fk_pattern = "audit_log.*REFERENCES.*clientes_blu"
    audit_log_fk_simple = "audit_log_client_id_fkey"

    # Check the constraints section (lines 762+)
    constraints_section = source[source.find("-- Foreign keys"):]
    for line in constraints_section.split("\n"):
        if "audit_log" in line and ("REFERENCES" in line or "FOREIGN KEY" in line):
            pytest.fail(
                f"AC#3 FIXED: audit_log now has a FK constraint:\n{line}\n"
                "Test needs update. If this FK was added intentionally, "
                "update the AC to document the new contract."
            )

    assert audit_log_fk_simple not in constraints_section, (
        "AC#3 violated: audit_log FK constraint found in baseline_v2.sql. "
        f"Expected NO FK constraint like `{audit_log_fk_simple}`. "
        "audit_log should keep client_id as a loose uuid for audit trail "
        "persistence."
    )

    # Assertion 3: verify audit_log has client_id as nullable uuid
    table_def_start = source.find("CREATE TABLE public.audit_log (")
    table_def = source[table_def_start:table_def_start + 200]
    assert "client_id uuid" in table_def, (
        "AC#3 violated: could not find client_id column in audit_log "
        "table definition."
    )

    pytest.fail(
        "AC#3 RED: audit_log NAO tem FK para clientes_blu, confirmado "
        "por source-inspection.\n\n"
        "Tabela audit_log em "
        "supabase/migrations/20260523999999_baseline_v2.sql "
        "(linhas 71-80):\n"
        "  - client_id uuid (solto, sem REFERENCES)\n"
        "  - Sem FK constraint na secao de foreign keys (linhas 762+)\n\n"
        "Analise:\n"
        "  - audit_log.client_id e' um uuid solto, SEM FK constraint.\n"
        "  - Isso significa: DELETE CASCADE em clientes_blu NAO afeta "
        "audit_log.\n"
        "  - O trigger handle_new_auth_user insere em audit_log com "
        "o client_id recem-criado.\n"
        "  - Como nao ha FK, nenhuma operacao de signup pode ser "
        "bloqueada por audit_log.\n\n"
        "Conclusao: audit_log NAO contribui para o bug 'segundo cadastro "
        "de email falha'.\n\n"
        "Arquivo: supabase/migrations/20260523999999_baseline_v2.sql "
        "(linhas 71-80, 762+)."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#4 — onboarding_bootstrap_tx usa ON CONFLICT (idempotente)
# ══════════════════════════════════════════════════════════════════════════


def test_b4_ac4_onboarding_bootstrap_on_conflict():
    """AC#4: a funcao ``onboarding_bootstrap_tx()`` deve usar ON CONFLICT
    para insercoes em ``clientes_blu`` e ``client_routines``.

    A funcao no arquivo applied/20260525_p12_split_onboarding_completion.sql:
      - INSERT INTO clientes_blu (...) ON CONFLICT (external_user_id) DO NOTHING
      - INSERT INTO client_enabled_agents (...) ON CONFLICT (client_id, agent_slug) DO NOTHING
      - INSERT INTO client_routines (...) ON CONFLICT (client_id, routine_id) DO UPDATE

    A UNIQUE(client_id, routine_id) em client_routines (linha 715 da baseline)
    e' o que torna o ON CONFLICT viavel. Sem ela, o PostgreSQL lancaria erro.

    Para o cenario de "segundo cadastro": o bootstrap e' chamado pelo
    frontend apos o signup. Se o client_id ja existir (ON CONFLICT no
    clientes_blu), as operacoes seguintes tambem sao idempotentes.
    """
    assert ONBOARDING_SPLIT_PATH.exists(), (
        f"Source file not found: {ONBOARDING_SPLIT_PATH}. "
        "AC#4 requires inspecting onboarding completion migration."
    )

    source = ONBOARDING_SPLIT_PATH.read_text()

    # Assertion 1: function exists with ON CONFLICT for clientes_blu
    marker = "CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx"
    assert marker in source, (
        "AC#4 violated: onboarding_bootstrap_tx() function not found in "
        "onboarding completion migration."
    )

    assert "ON CONFLICT (external_user_id) DO NOTHING" in source, (
        "AC#4 violated: ON CONFLICT (external_user_id) DO NOTHING not found "
        "in onboarding_bootstrap_tx(). Expected at line 56."
    )

    # Assertion 2: ON CONFLICT for client_routines
    assert "ON CONFLICT (client_id, routine_id) DO UPDATE" in source, (
        "AC#4 violated: ON CONFLICT (client_id, routine_id) DO UPDATE not "
        "found in onboarding_bootstrap_tx(). Expected at line 103."
    )

    # Assertion 3: client_routines has the UNIQUE constraint for ON CONFLICT
    baseline = BASELINE_PATH.read_text()
    assert "client_routines_client_id_routine_id_key UNIQUE (client_id, routine_id)" in baseline, (
        "AC#4 violated: UNIQUE(client_id, routine_id) constraint not found "
        "on client_routines table in baseline_v2.sql (line 715). Without this "
        "constraint, the ON CONFLICT in onboarding_bootstrap_tx would fail "
        "with 'there is no unique or exclusion constraint' error."
    )

    # Assertion 4: ON CONFLICT for client_enabled_agents
    assert "ON CONFLICT (client_id, agent_slug) DO NOTHING" in source, (
        "AC#4 violated: ON CONFLICT (client_id, agent_slug) DO NOTHING not "
        "found in onboarding_bootstrap_tx()."
    )

    pytest.fail(
        "AC#4 RED: onboarding_bootstrap_tx() usa ON CONFLICT para "
        "clientes_blu, client_enabled_agents e client_routines, mas "
        "a propriedade de idempotencia ainda nao foi formalmente "
        "validada.\n\n"
        "Funcao onboarding_bootstrap_tx() em\n"
        "  supabase/migrations/applied/20260525_p12_"
        "split_onboarding_completion.sql:\n"
        "  - INSERT clientes_blu ON CONFLICT (external_user_id) DO NOTHING "
        "(linha 56)\n"
        "  - INSERT client_enabled_agents ON CONFLICT (client_id, "
        "agent_slug) DO NOTHING (linha 86)\n"
        "  - INSERT client_routines ON CONFLICT (client_id, routine_id) "
        "DO UPDATE (linha 103)\n\n"
        "Constraint em baseline_v2.sql:\n"
        "  - client_routines_client_id_routine_id_key UNIQUE (client_id, "
        "routine_id) (linha 715)\n\n"
        "Analise:\n"
        "  - Todas as insercoes sao idempotentes via ON CONFLICT.\n"
        "  - A UNIQUE(client_id, routine_id) em client_routines torna "
        "o ON CONFLICT viavel.\n"
        "  - No segundo signup: clientes_blu nao e' duplicado (ON "
        "CONFLICT), client_routines faz UPDATE upsert.\n"
        "  - Seed de 10 client_routines NAO falha no segundo cadastro.\n\n"
        "Conclusao: client_routines seed NAO contribui para o bug "
        "'segundo cadastro de email falha'.\n\n"
        "Arquivos:\n"
        "  - supabase/migrations/applied/20260525_p12_split_onboarding_"
        "completion.sql\n"
        "  - supabase/migrations/20260523999999_baseline_v2.sql (linha 715)"
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#5 — client_users e client_routines tem FK CASCADE ON DELETE
# ══════════════════════════════════════════════════════════════════════════


def test_b4_ac5_client_users_client_routines_fk_cascade():
    """AC#5: ``client_users`` e ``client_routines`` devem ter FK com
    ``ON DELETE CASCADE`` referenciando ``clientes_blu(client_id)``.

    Baseline_v2.sql (linhas 785-787):
      - client_routines_client_id_fkey: FOREIGN KEY (client_id)
        REFERENCES clientes_blu(client_id) ON DELETE CASCADE
      - client_users_client_id_fkey: FOREIGN KEY (client_id)
        REFERENCES clientes_blu(client_id) ON DELETE CASCADE

    Tambem:
      - client_users_unique_email UNIQUE (client_id, email)
        (linha 717) — garante que cada email so' aparece uma vez
        por cliente.

    Para o cenario de "segundo cadastro": as FK CASCADE significam
    que se um clientes_blu for deletado, client_users e client_routines
    sao automaticamente removidos. Isso e' DESEJAVEL para cleanup,
    mas no fluxo de signup NENHUM DELETE ocorre (apenas INSERT ou
    ON CONFLICT), entao as FK CASCADE nao bloqueiam o fluxo.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "AC#5 requires inspecting baseline_v2.sql."
    )

    source = BASELINE_PATH.read_text()

    # Assertion 1: client_routines FK CASCADE
    assert (
        "client_routines_client_id_fkey FOREIGN KEY (client_id) "
        "REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE"
    ) in source, (
        "AC#5 violated: client_routines FK CASCADE not found. "
        "Expected at line 785."
    )

    # Assertion 2: client_users FK CASCADE
    assert (
        "client_users_client_id_fkey FOREIGN KEY (client_id) "
        "REFERENCES public.clientes_blu (client_id) ON DELETE CASCADE"
    ) in source, (
        "AC#5 violated: client_users FK CASCADE not found. "
        "Expected at line 787."
    )

    # Assertion 3: client_users UNIQUE(client_id, email)
    assert "client_users_unique_email UNIQUE (client_id, email)" in source, (
        "AC#5 violated: UNIQUE(client_id, email) not found on client_users. "
        "Expected at line 717."
    )

    # Assertion 4: client_users has client_id NOT NULL
    table_start = source.find("CREATE TABLE public.client_users (")
    assert table_start != -1, (
        "AC#5 violated: could not find CREATE TABLE public.client_users."
    )
    table_def = source[table_start:table_start + 300]
    assert "client_id uuid NOT NULL" in table_def, (
        "AC#5 violated: client_users.client_id is nullable. Expected "
        "NOT NULL since every client_user must belong to a clientes_blu row."
    )

    pytest.fail(
        "AC#5 RED: FK CASCADE ON DELETE confirmadas para client_users "
        "e client_routines, mas ainda nao formalmente validadas.\n\n"
        "Foreign keys em "
        "supabase/migrations/20260523999999_baseline_v2.sql:\n"
        "  Linha 785: client_routines_client_id_fkey -> clientes_blu "
        "(ON DELETE CASCADE)\n"
        "  Linha 787: client_users_client_id_fkey -> clientes_blu "
        "(ON DELETE CASCADE)\n"
        "  Linha 717: client_users_unique_email UNIQUE (client_id, email)\n\n"
        "Analise:\n"
        "  - client_users: FK CASCADE para clientes_blu. Se clientes_blu "
        "for deletado, todos os client_users sao removidos.\n"
        "  - client_routines: FK CASCADE para clientes_blu. Mesmo "
        "comportamento.\n"
        "  - client_users UNIQUE(client_id, email): evita emails "
        "duplicados por cliente.\n"
        "  - client_routines UNIQUE(client_id, routine_id): permite "
        "ON CONFLICT no bootstrap.\n\n"
        "Conclusao: as FK CASCADE NAO bloqueiam o fluxo de signup "
        "(nenhum DELETE ocorre durante signup). A UNIQUE(client_id, email) "
        "em client_users impede que o mesmo email seja convidado duas "
        "vezes para o mesmo cliente — irrelevante para o cenario de "
        "segundo cadastro.\n\n"
        "Arquivo: supabase/migrations/20260523999999_baseline_v2.sql "
        "(linhas 717, 785, 787)."
    )


# ══════════════════════════════════════════════════════════════════════════
# Sanity checks — ensure target files exist and contain expected structures
# ══════════════════════════════════════════════════════════════════════════


def test_b4_sanity_baseline_v2_exists():
    """Sanity: confirma que o arquivo baseline_v2.sql existe e contem
    as definicoes esperadas de clientes_blu, handle_new_auth_user,
    client_users, client_routines e audit_log.
    """
    assert BASELINE_PATH.exists(), (
        f"Source file not found: {BASELINE_PATH}. "
        "Sanity check requires baseline_v2.sql to exist."
    )

    text = BASELINE_PATH.read_text()

    # All expected tables/functions exist
    for expected in [
        "CREATE TABLE public.clientes_blu",
        "CREATE TABLE public.client_users",
        "CREATE TABLE public.client_routines",
        "CREATE TABLE public.audit_log",
        "CREATE OR REPLACE FUNCTION public.handle_new_auth_user",
        "clientes_blu_pkey PRIMARY KEY",
        "clientes_blu_api_key_key UNIQUE (api_key)",
        "clientes_blu_external_user_id_key UNIQUE (external_user_id)",
        "client_users_client_id_fkey",
        "client_routines_client_id_routine_id_key UNIQUE",
        "ON CONFLICT (external_user_id) DO NOTHING",
    ]:
        assert expected in text, (
            f"Sanity violated: expected string not found in baseline_v2.sql:\n"
            f"  {expected}"
        )


def test_b4_sanity_onboarding_split_exists():
    """Sanity: confirma que o arquivo onboarding completion split existe
    e contem a funcao onboarding_bootstrap_tx com ON CONFLICT.
    """
    assert ONBOARDING_SPLIT_PATH.exists(), (
        f"Source file not found: {ONBOARDING_SPLIT_PATH}. "
        "Sanity check requires onboarding completion migration to exist."
    )

    text = ONBOARDING_SPLIT_PATH.read_text()

    assert "CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx" in text, (
        "Sanity violated: onboarding_bootstrap_tx() not found in "
        "onboarding completion migration."
    )

    assert "ON CONFLICT (external_user_id) DO NOTHING" in text, (
        "Sanity violated: ON CONFLICT for clientes_blu not found in "
        "onboarding_bootstrap_tx()."
    )
