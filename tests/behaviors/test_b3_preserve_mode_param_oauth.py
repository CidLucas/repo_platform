"""RED test — B-2 (BATCH #215): Preservar ?mode= apos OAuth callback.

GOAL:
    ``AuthContext.tsx`` em ``packages/blu-auth/src/AuthContext.tsx`` linha
    ~147 usa:
        ``window.history.replaceState(null, '', window.location.pathname)``
    que descarta query params (ex: ``?mode=login``) apos o callback OAuth.

    O fix GREEN sera:
        ``window.history.replaceState(
            null, '', window.location.pathname + window.location.search
        )``

BEHAVIOR:
    "B-2 — Preservar query params (?mode=, etc.) apos OAuth callback.
    AuthContext.tsx deve usar ``window.location.pathname +
    window.location.search`` em vez de apenas ``window.location.pathname``
    no ``replaceState`` que limpa o hash ``#access_token=`` apos login
    OAuth (linha ~147).

    O ``onAuthStateChange`` detecta que ha params OAuth no hash/search,
    e faz ``replaceState`` para limpar o hash.  Mas atualmente usa apenas
    ``pathname``, perdendo qualquer query param como ``?mode=login`` que
    a app precise preservar.  O fix e concatenar
    ``window.location.search``."

    Estado atual (BEFORE — RED):
        AuthContext.tsx L147 usa:
            ``window.history.replaceState(null, '', window.location.pathname)``
        SEM concatenar ``window.location.search``.

    Estado esperado (AFTER — GREEN):
        AuthContext.tsx L147 usara:
            ``window.history.replaceState(
                null, '', window.location.pathname + window.location.search
            )``

AC (Acceptance Criteria):
    AC#1 — ``window.location.pathname + window.location.search`` usado no
            ``replaceState`` (nao apenas ``pathname``).
    AC#2 — O bloco de ``if (hasOAuthParams)`` ainda limpa o hash OAuth
            (``replaceState`` continua funcionando).
    AC#3 — ``window.location.search`` preserva o ``?`` prefixo
            (JS inclui automaticamente).
    AC#4 — O fluxo de OAuth callback continua intacto
            (nao quebra ``cal_oauth_pending`` nem ``drive_oauth_pending``).
    AC#5 — ``hasOAuthParams`` detection continua igual
            (``hash.includes('access_token')`` || ``search.includes('code=')``).

Anti-Goals:
    1. NAO modificar codigo de producao (AuthContext.tsx).
    2. NAO executar/parsear TypeScript — somente inspecao textual com regex.
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

SOURCE = (
    REPO_ROOT
    / "packages"
    / "blu-auth"
    / "src"
    / "AuthContext.tsx"
)


# ── Override do root conftest (teste puramente estatico) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e
    pura inspecao textual do arquivo TSX, sem teardown no Supabase, sem
    rede, sem parser TypeScript, sem execucao de codigo React.
    """
    yield


# ── Helpers de inspecao textual ───────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o arquivo TSX como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Source file not found: {path}.  "
        "O behavior B-2 (BATCH #215) exige que o arquivo "
        "packages/blu-auth/src/AuthContext.tsx exista no repo."
    )
    return path.read_text(encoding="utf-8")


def _extract_onauthstatechange_block(source: str) -> str:
    """Extrai o bloco do callback ``onAuthStateChange`` a partir do
    anchor ``const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {``
    ate o fechamento do callback.  Usa heuristica por contagem de
    chaves: a partir do anchor, conta ``{`` vs ``}`` ate balancear.

    Retorna o texto completo do callback (incluindo a assinatura).
    """
    anchor = (
        "const { data: { subscription } } = "
        "supabase.auth.onAuthStateChange((_event, session) => {"
    )
    start = source.find(anchor)
    assert start >= 0, (
        "[RED] B-2 (BATCH #215) — nao foi possivel localizar o anchor "
        "`const { data: { subscription } } = "
        "supabase.auth.onAuthStateChange((_event, session) => {` "
        "em AuthContext.tsx.  O coder precisa preservar esta assinatura "
        "ao refatorar o bloco."
    )
    # Atencao: a linha do anchor tem OUTROS `{` antes do `{` de
    # abertura do callback (no destructure `const { data: { subscription } }`).
    # O `{` que abre o callback e o ULTIMO `{` da linha.  Para localizar
    # a abertura correta, restringimos a busca ate a quebra de linha.
    line_end = source.find("\n", start)
    if line_end < 0:
        line_end = len(source)
    open_brace_pos = source.rfind("{", start, line_end)
    assert open_brace_pos >= 0 and open_brace_pos >= start, (
        "[RED] B-2 (BATCH #215) — anchor do `onAuthStateChange` "
        "encontrado, mas a chave `{` de abertura do callback nao foi "
        "localizada na mesma linha.  Estrutura inesperada em "
        "AuthContext.tsx."
    )

    depth = 0
    end = open_brace_pos
    for i in range(open_brace_pos, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    assert depth == 0, (
        "[RED] B-2 (BATCH #215) — chaves do callback `onAuthStateChange` "
        "nao balancearam ate o fim do arquivo.  Estrutura inesperada em "
        "AuthContext.tsx — o coder deve manter o callback bem-formado."
    )

    return source[start:end]


# ── Teste principal (RED) — cobre todos os ACs de B-2 ────────────────


@pytest.mark.behaviors
def test_b3_preserve_mode_param_oauth_red() -> None:
    """B-2 (BATCH #215) — RED.  Falha enquanto o ``replaceState`` em
    ``AuthContext.tsx`` nao preservar o ``window.location.search``
    (query params como ``?mode=login``) apos o callback OAuth.

    Esta funcao agrega a verificacao de TODOS os ACs em uma unica
    assercao: coleta todas as deficiencias e dispara ``pytest.fail``
    com mensagem consolidada em pt-BR listando o que falta para GREEN.
    """
    source = _read_source(SOURCE)
    callback_block = _extract_onauthstatechange_block(source)

    problemas: list[str] = []

    # ── AC#1 — replaceState usa pathname + search (NAO apenas pathname) ──
    # Para o teste ser RED, esperamos que `pathname + search` NAO esteja
    # presente, mas que `pathname` sozinho esteja dentro de um
    # replaceState (codigo atual).
    has_pathname_plus_search = bool(
        re.search(
            r"window\.location\.pathname\s*\+\s*window\.location\.search",
            callback_block,
        )
    )

    if not has_pathname_plus_search:
        problemas.append(
            "AC#1 — `replaceState` NAO esta preservando o query string "
            "OAuth.  O codigo atual usa `window.location.pathname` "
            "sozinho (ex: `window.history.replaceState(null, '', "
            "window.location.pathname)`), descartando query params "
            "como `?mode=login`.  O fix GREEN e concatenar "
            "`window.location.pathname + window.location.search` no "
            "argumento do `replaceState` que limpa o hash OAuth."
        )

    # ── AC#2 — replaceState ainda existe e limpa o hash OAuth ──
    # Procuramos o mecanismo `window.history.replaceState(` dentro do
    # callback.  A existencia do mecanismo e o `if (hasOAuthParams)` em
    # volta dele sao ambos exigidos.
    has_replacestate = bool(
        re.search(
            r"window\.history\.replaceState\s*\(",
            callback_block,
        )
    )
    has_if_has_oauth_params = bool(
        re.search(
            r"if\s*\(\s*hasOAuthParams\s*\)\s*\{",
            callback_block,
        )
    )
    # O `if` deve estar dentro do callback e envolver o `replaceState`.
    if_has_oauth_block_match = re.search(
        r"if\s*\(\s*hasOAuthParams\s*\)\s*\{[^}]*window\.history\.replaceState[^}]*\}",
        callback_block,
        re.DOTALL,
    )
    has_replacestate_inside_if = bool(if_has_oauth_block_match)

    if not (has_replacestate and has_if_has_oauth_params and has_replacestate_inside_if):
        missing: list[str] = []
        if not has_replacestate:
            missing.append("`window.history.replaceState(` mecanismo")
        if not has_if_has_oauth_params:
            missing.append("`if (hasOAuthParams) { ... }` bloco")
        if not has_replacestate_inside_if:
            missing.append(
                "replaceState dentro do bloco `if (hasOAuthParams) { ... }`"
            )
        problemas.append(
            "AC#2 — o mecanismo de limpeza do hash OAuth via "
            "`window.history.replaceState` dentro do bloco "
            "`if (hasOAuthParams) { ... }` NAO esta intacto.  "
            f"Faltando: {', '.join(missing)}.  A limpeza do hash "
            "OAuth precisa continuar funcionando — o fix so muda o "
            "argumento do replaceState, nao remove o mecanismo."
        )

    # ── AC#3 — search preserva o `?` prefixo (uso direto, sem slicing) ──
    # Garantimos que o codigo NAO faca `.slice(1)` ou similar sobre
    # `window.location.search`, e que o uso seja concatenacao direta.
    # Verifica que NAO ha manipulacao manual de slicing no search
    # dentro do callback (GREEN deve usar search direto).
    has_search_slicing = bool(
        re.search(
            r"window\.location\.search\.slice\s*\(",
            callback_block,
        )
    )
    has_search_direct_concat = bool(
        re.search(
            r"window\.location\.pathname\s*\+\s*window\.location\.search(?!\.slice)",
            callback_block,
        )
    )

    if has_search_slicing:
        problemas.append(
            "AC#3 — detectado `window.location.search.slice(...)` no "
            "callback `onAuthStateChange`.  O fix GREEN deve usar "
            "`window.location.search` diretamente (JS ja inclui o `?` "
            "no prefixo), sem `.slice(1)` manual."
        )
    elif not has_search_direct_concat:
        problemas.append(
            "AC#3 — `window.location.search` NAO esta sendo concatenado "
            "diretamente com `window.location.pathname`.  O JS ja "
            "preserva o `?` prefixo em `window.location.search`; "
            "basta concatenar (sem `.slice(1)` manual) para preservar "
            "query params como `?mode=login`."
        )

    # ── AC#4 — fluxo OAuth callback intacto (cal_oauth_pending, drive_oauth_pending) ──
    has_cal_oauth_pending = bool(
        re.search(
            r"cal_oauth_pending",
            callback_block,
        )
    )
    has_drive_oauth_pending = bool(
        re.search(
            r"drive_oauth_pending",
            callback_block,
        )
    )
    has_on_calendar_token = bool(
        re.search(
            r"onCalendarToken",
            callback_block,
        )
    )
    has_on_drive_token = bool(
        re.search(
            r"onDriveToken",
            callback_block,
        )
    )
    has_provider_refresh_token = bool(
        re.search(
            r"provider_refresh_token",
            callback_block,
        )
    )

    if not (
        has_cal_oauth_pending
        and has_drive_oauth_pending
        and has_on_calendar_token
        and has_on_drive_token
        and has_provider_refresh_token
    ):
        missing: list[str] = []
        if not has_cal_oauth_pending:
            missing.append("`cal_oauth_pending` (sessionStorage flag)")
        if not has_drive_oauth_pending:
            missing.append("`drive_oauth_pending` (sessionStorage flag)")
        if not has_on_calendar_token:
            missing.append("`onCalendarToken` (callback para calendar OAuth)")
        if not has_on_drive_token:
            missing.append("`onDriveToken` (callback para drive OAuth)")
        if not has_provider_refresh_token:
            missing.append(
                "`provider_refresh_token` (campo do session capturado "
                "no callback OAuth)"
            )
        problemas.append(
            "AC#4 — fluxo OAuth callback NAO esta intacto no callback "
            f"`onAuthStateChange`.  Faltando: {', '.join(missing)}.  "
            "O fix do replaceState NAO pode quebrar a logica de "
            "captura de tokens do Calendar/Drive OAuth.  Os flags "
            "`cal_oauth_pending` e `drive_oauth_pending` no "
            "sessionStorage, os callbacks `onCalendarToken` / "
            "`onDriveToken`, e o campo `provider_refresh_token` "
            "precisam permanecer no callback."
        )

    # ── AC#5 — hasOAuthParams detection continua igual ──
    has_hash_includes_access_token = bool(
        re.search(
            r"window\.location\.hash\.includes\s*\(\s*['\"]access_token['\"]\s*\)",
            callback_block,
        )
    )
    has_search_includes_code = bool(
        re.search(
            r"window\.location\.search\.includes\s*\(\s*['\"]code=['\"]\s*\)",
            callback_block,
        )
    )
    has_has_oauth_params_decl = bool(
        re.search(
            r"const\s+hasOAuthParams\s*=",
            callback_block,
        )
    )

    if not (
        has_hash_includes_access_token
        and has_search_includes_code
        and has_has_oauth_params_decl
    ):
        missing: list[str] = []
        if not has_has_oauth_params_decl:
            missing.append("`const hasOAuthParams = ...` declaracao")
        if not has_hash_includes_access_token:
            missing.append(
                "`window.location.hash.includes('access_token')` "
                "na deteccao"
            )
        if not has_search_includes_code:
            missing.append(
                "`window.location.search.includes('code=')` na deteccao"
            )
        problemas.append(
            "AC#5 — deteccao `hasOAuthParams` NAO esta intacta no "
            f"callback `onAuthStateChange`.  Faltando: {', '.join(missing)}.  "
            "A logica `hash.includes('access_token') || "
            "search.includes('code=')` precisa ser preservada — o fix "
            "so muda o argumento do `replaceState`, nao a deteccao."
        )

    # ── Agrega todas as deficiencias ─────────────────────────────────
    if problemas:
        cabecalho = (
            "[RED] B-2 (BATCH #215) — AuthContext.tsx replaceState "
            "preservando query params OAuth — "
            f"{len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  - {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
