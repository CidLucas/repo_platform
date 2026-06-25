"""RED test — B-4 (BATCH #215): Fluxo completo de login/redirect — 7 cenários.

GOAL:
    Testar funcionalmente o fluxo completo de login/redirect do onboarding,
    cobrindo os 3 sinais da RPC ``is_onboarded_client()`` + retorno de OAuth.
    Usa source-inspection sobre a migration SQL (para os 3 sinais) e sobre
    ``OnboardingApp.tsx`` (para o tratamento de retorno de OAuth).

BEHAVIOR:
    "B-4 — Fluxo completo de login/redirect: a RPC
    ``public.is_onboarded_client()`` (definida na migration
    ``20260625_p13_is_onboarded_client.sql``) implementa 3 sinais de
    onboarding, e o ``OnboardingApp.tsx`` trata corretamente o retorno
    de OAuth (``onboarding_returning_to_data``)."

    3 sinais da RPC:
        1. ``onboarding_completed_at IS NOT NULL`` em clientes_blu →
           onboarded (true), redirect /app.
        2. Cliente tem ``data_sources`` ativos (sync_status IN
           ('ready','success','synced')) → onboarded (true), redirect
           /app.
        3. Cliente tem ``enabled_agents`` + conta > 1h (created_at <
           now() - interval '1 hour') → onboarded (true), redirect /app.
        Se get_my_client_id() retornar NULL → não onboarded (false),
        mostra onboarding.
        Se nenhum sinal bater → não onboarded (false), mostra onboarding.

    E no OnboardingApp.tsx:
        - Quando localStorage tem ``onboarding_returning_to_data``,
          restaura step='data' e remove o flag.

    Estado atual (BEFORE — RED):
        A migration ``20260625_p13_is_onboarded_client.sql`` NÃO existe —
        o coder ainda não criou a migration com a RPC. Portanto, os ACs
        baseados no SQL falham (TRUE RED). O AC#7 (OAuth return) já está
        implementado e deve passar (GREEN).

    Estado esperado (AFTER — GREEN):
        A migration existirá com a RPC implementando os 3 sinais, e o
        OnboardingApp.tsx preservará o tratamento de retorno de OAuth.

AC (Acceptance Criteria) — 7 cenários:

    AC#1 (Cenário 1 — Novo usuário sem client_id):
        A RPC chama ``get_my_client_id()`` internamente e retorna
        ``false`` quando o resultado é NULL (usuário sem clientes_blu).
        Evidência no SQL: ``get_my_client_id()`` + tratamento de NULL.

    AC#2 (Cenário 2 — onboarding_completed_at setado, sinal 1):
        A RPC verifica ``onboarding_completed_at IS NOT NULL`` em
        ``clientes_blu`` e retorna ``true`` quando setado.
        Evidência no SQL: ``onboarding_completed_at`` +
        ``IS NOT NULL`` ou equivalente.

    AC#3 (Cenário 3 — data_sources ativos, sinal 2):
        A RPC usa ``EXISTS`` com subquery em ``client_data_sources``
        filtrando por ``sync_status`` IN ('ready','success','synced').
        Evidência no SQL: ``client_data_sources`` + ``sync_status``.

    AC#4 (Cenário 4 — enabled_agents + conta > 1h, sinal 3):
        A RPC usa ``EXISTS`` com subquery em ``client_enabled_agents``
        E condição ``created_at < now() - interval '1 hour'``.
        Evidência no SQL: ``client_enabled_agents`` +
        ``interval '1 hour'`` (ou ``interval '1 hour'``).

    AC#5 (Cenário 5 — enabled_agents mas conta < 1h):
        A condição de idade (> 1h) está ACOPLADA ao sinal 3, não
        separada — ``enabled_agents`` SÓ conta com conta > 1h.
        Evidência no SQL: A condição ``created_at < now() - interval
        '1 hour'`` (ou similar) aparece na mesma cláusula lógica que
        ``client_enabled_agents``.

    AC#6 (Cenário 6 — Nenhum sinal):
        A RPC retorna ``false`` como default/final quando nenhum dos
        3 sinais é satisfeito.
        Evidência no SQL: ``RETURN false`` ou ``RETURN COALESCE(...,
        false)`` no final.

    AC#7 (Cenário 7 — Retorno de Drive OAuth):
        O ``OnboardingApp.tsx`` preserva o tratamento de
        ``onboarding_returning_to_data`` no localStorage:
        - ``localStorage.getItem('onboarding_returning_to_data')``
        - ``localStorage.removeItem('onboarding_returning_to_data')``
        - ``setStep('data')``

Anti-Goals:
    1. NÃO modificar código de produção (migration SQL ou OnboardingApp.tsx).
    2. NÃO executar/parsear SQL ou JSX — somente inspeção textual com regex.
    3. NÃO usar mocks, Supabase ou banco de dados.
    4. NÃO quebrar funcionalidade existente.
    5. NÃO relaxar o teste para que ele passe — precisa ser TRUE RED agora
       (AC#1–AC#6 falham porque a migration não existe; AC#7 deve passar).
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

ONBOARDING_APP_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)


# ── Override do root conftest (teste puramente estático) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção textual, sem teardown no Supabase, sem rede,
    sem execução de SQL ou JSX.
    """
    yield


# ── Helpers de inspeção textual ───────────────────────────────────────


def _read_source(path: Path) -> str:
    """Lê o arquivo como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Source file not found: {path}.  "
        "O behavior B-4 (BATCH #215) exige que este arquivo exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os 7 ACs de B-4 ──────────────


@pytest.mark.behaviors
def test_b4_completo_login_redirect_red() -> None:
    """B-4 (BATCH #215) — RED.  Falha enquanto a migration
    ``20260625_p13_is_onboarded_client.sql`` não existir (AC#1–AC#6) ou
    enquanto o tratamento de retorno de OAuth no OnboardingApp.tsx
    estiver ausente (AC#7).

    Agrega a verificação de TODOS os 7 ACs em uma única asserção:
    coleta todas as deficiências e dispara ``pytest.fail`` com mensagem
    consolidada em pt-BR listando o que falta para GREEN.
    """
    problemas: list[str] = []

    # ── Preâmbulo: verifica existencia dos arquivos ──────────────────

    # A migration NAO existe (TRUE RED para AC#1–AC#6)
    migration_exists = MIGRATION_PATH.is_file()

    if not migration_exists:
        problemas.append(
            "[ARQUIVO AUSENTE] AC#1–AC#6 — A migration "
            "`supabase/migrations/applied/20260625_p13_is_onboarded_client.sql` "
            "NAO existe.  O coder precisa criar a migration com a RPC "
            "`public.is_onboarded_client()` (B-1) e o UPDATE de backfill "
            "(B-2) antes que estes ACs possam passar."
        )
        # Não tenta ler o arquivo — pula para AC#7
        source_sql = ""
    else:
        source_sql = _read_source(MIGRATION_PATH)

    # O OnboardingApp DEVE existir (GREEN para AC#7)
    onboarding_exists = ONBOARDING_APP_PATH.is_file()
    if not onboarding_exists:
        problemas.append(
            "[ARQUIVO AUSENTE] AC#7 — O arquivo "
            "`apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx` "
            "NAO existe.  Sem ele, o tratamento de retorno de OAuth "
            "nao pode ser verificado."
        )

    # ── AC#1 — get_my_client_id() + tratamento de NULL ──────────────

    if migration_exists:
        has_get_my_client_id = bool(
            re.search(r"get_my_client_id\s*\(", source_sql)
        )
        # Procura por RETURN false / COALESCE(... false) / WHEN NULL
        # nas proximidades de get_my_client_id
        has_null_handling = bool(
            re.search(
                r"get_my_client_id.*?(?:NULL|RETURN\s+false|COALESCE)",
                source_sql,
                re.IGNORECASE | re.DOTALL,
            )
        )

        if not has_get_my_client_id:
            problemas.append(
                "AC#1 — `get_my_client_id()` NAO chamada no corpo da "
                "RPC.  A funcao precisa obter o client_id do usuario "
                "autenticado como primeiro passo."
            )
        if not has_null_handling:
            problemas.append(
                "AC#1 — A RPC NAO trata o caso de `get_my_client_id()` "
                "retornar NULL.  Quando o usuario nao tem clientes_blu, "
                "a RPC deve retornar false para que o onboarding seja "
                "exibido (Cenario 1 — novo usuario sem client_id)."
            )

    # ── AC#2 — onboarding_completed_at IS NOT NULL (sinal 1) ─────────

    if migration_exists:
        has_signal_1 = bool(
            re.search(
                r"onboarding_completed_at\s+IS\s+NOT\s+NULL",
                source_sql,
                re.IGNORECASE,
            )
        )

        if not has_signal_1:
            problemas.append(
                "AC#2 — Sinal 1 (`onboarding_completed_at IS NOT NULL`) "
                "NAO encontrado no corpo da RPC.  Clientes que ja "
                "completaram o onboarding (onboarding_completed_at "
                "preenchido) devem ser considerados onboarded (Cenario 2)."
            )

    # ── AC#3 — EXISTS em client_data_sources com sync_status (sinal 2) ─

    if migration_exists:
        has_data_sources = bool(
            re.search(
                r"client_data_sources",
                source_sql,
                re.IGNORECASE,
            )
        )
        has_sync_status = bool(
            re.search(
                r"sync_status",
                source_sql,
                re.IGNORECASE,
            )
        )

        if not has_data_sources:
            problemas.append(
                "AC#3 — Sinal 2 (`EXISTS` em `client_data_sources`) "
                "NAO encontrado no corpo da RPC.  Clientes com fontes "
                "de dados ativas devem ser considerados onboarded "
                "(Cenario 3)."
            )
        elif not has_sync_status:
            problemas.append(
                "AC#3 — Sinal 2: a subquery em `client_data_sources` "
                "NAO filtra por `sync_status`.  Apenas fontes com "
                "status 'ready', 'success' ou 'synced' devem contar "
                "como dados ativos."
            )

    # ── AC#4 — EXISTS em client_enabled_agents + conta > 1h (sinal 3) ─

    has_enabled_agents = False
    has_age_check = False
    if migration_exists:
        has_enabled_agents = bool(
            re.search(
                r"client_enabled_agents",
                source_sql,
                re.IGNORECASE,
            )
        )
        has_age_check = bool(
            re.search(
                r"interval\s+'1\s*hour'",
                source_sql,
                re.IGNORECASE,
            )
        )

        if not has_enabled_agents:
            problemas.append(
                "AC#4 — Sinal 3 (`EXISTS` em `client_enabled_agents`) "
                "NAO encontrado no corpo da RPC.  Clientes com enabled "
                "agents ativos + conta > 1h devem ser considerados "
                "onboarded (Cenario 4)."
            )
        if not has_age_check:
            problemas.append(
                "AC#4 — Sinal 3: a condicao de idade (`interval '1 hour'` "
                "ou similar) NAO encontrada no corpo da RPC.  Apenas "
                "contas com mais de 1 hora de atividade podem ser "
                "consideradas onboarded via este sinal."
            )

    # ── AC#5 — idade ACOPLADA ao enabled_agents (conta < 1h nao conta) ─

    if migration_exists:
        # Verifica se enabled_agents E age_check aparecem na MESMA
        # clausula (WHERE ou AND), garantindo que enabled_agents SO
        # conta se a conta tiver mais de 1h.
        has_coupled = bool(
            re.search(
                r"enabled_agents.*?interval\s+'1\s*hour'",
                source_sql,
                re.IGNORECASE | re.DOTALL,
            )
            or re.search(
                r"interval\s+'1\s*hour'.*?enabled_agents",
                source_sql,
                re.IGNORECASE | re.DOTALL,
            )
        )

        if has_enabled_agents and has_age_check and not has_coupled:
            problemas.append(
                "AC#5 — As condicoes de `client_enabled_agents` e "
                "`interval '1 hour'` estao PRESENTES MAS NAO "
                "ACOPLADAS na mesma clausula logica.  Clientes com "
                "enabled_agents mas conta < 1h NAO devem ser "
                "considerados onboarded (Cenario 5).  A condicao de "
                "idade precisa fazer parte da mesma condicao que "
                "verifica enabled_agents."
            )

    # ── AC#6 — RETURN false como default (nenhum sinal) ──────────────

    if migration_exists:
        has_default_false = bool(
            re.search(
                r"RETURN\s+(?:COALESCE\s*\([^)]*,\s*)?false\b",
                source_sql,
                re.IGNORECASE,
            )
        )

        if not has_default_false:
            problemas.append(
                "AC#6 — A RPC NAO possui um `RETURN false` (ou "
                "`COALESCE(..., false)`) como default/final.  Quando "
                "nenhum dos 3 sinais for satisfeito, a RPC deve "
                "retornar false para que o onboarding seja exibido "
                "(Cenario 6 — sem nenhum sinal)."
            )

    # ── AC#7 — Retorno de Drive OAuth (onboarding_returning_to_data) ──

    if onboarding_exists:
        onboarding_source = _read_source(ONBOARDING_APP_PATH)

        # Localiza o bloco do useEffect de redirect
        redirect_block_match = re.search(
            r"// When user is authenticated at the auth step.*?"
            r"},\s*\[user\?\.id,\s*loading,\s*step,\s*navigate\]\)",
            onboarding_source,
            re.DOTALL,
        )

        if redirect_block_match is None:
            problemas.append(
                "AC#7 — Pre-condicao: NAO foi possivel localizar o "
                "useEffect de redirect no OnboardingApp.tsx (bloco "
                "entre o comment 'When user is authenticated' e a "
                "dependencia [user?.id, loading, step, navigate]).  "
                "Este bloco e necessario para verificar o tratamento "
                "de retorno de OAuth."
            )
        else:
            redirect_block = redirect_block_match.group(0)

            # AC#7a — localStorage.getItem('onboarding_returning_to_data')
            has_getitem = bool(
                re.search(
                    r"localStorage\.getItem\(['\"]onboarding_returning_to_data['\"]\)",
                    redirect_block,
                )
            )
            # AC#7b — localStorage.removeItem('onboarding_returning_to_data')
            has_removeitem = bool(
                re.search(
                    r"localStorage\.removeItem\(['\"]onboarding_returning_to_data['\"]\)",
                    redirect_block,
                )
            )
            # AC#7c — setStep('data')
            has_setstep_data = bool(
                re.search(
                    r"setStep\(['\"]data['\"]\)",
                    redirect_block,
                )
            )

            missing_oauth: list[str] = []
            if not has_getitem:
                missing_oauth.append(
                    "`localStorage.getItem('onboarding_returning_to_data')` "
                    "para detectar retorno de OAuth"
                )
            if not has_removeitem:
                missing_oauth.append(
                    "`localStorage.removeItem('onboarding_returning_to_data')` "
                    "para limpar o flag apos uso"
                )
            if not has_setstep_data:
                missing_oauth.append(
                    "`setStep('data')` para restaurar o step"
                )

            if missing_oauth:
                problemas.append(
                    "AC#7 — Tratamento de retorno de Drive OAuth "
                    f"INCOMPLETO.  Faltando: {', '.join(missing_oauth)}.  "
                    "Quando o usuario volta do OAuth do Google Drive "
                    "com o flag `onboarding_returning_to_data` no "
                    "localStorage, o effect deve restaurar step='data' "
                    "e remover o flag.  Isto ja esta implementado no "
                    "codigo atual e DEVE ser preservado."
                )

    # ── Agrega todas as deficiências ─────────────────────────────────

    if problemas:
        cabecalho = (
            "[RED] B-4 (BATCH #215) — Fluxo completo de login/redirect "
            f"— {len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  ✗ {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
