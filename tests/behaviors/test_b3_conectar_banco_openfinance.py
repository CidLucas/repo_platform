"""RED test for behavior B-3 — Botao 'Conectar Banco' no Contas do Financeiro (BKL-024) (NAO implementado).

GOAL:
    Validar que o botao explicito 'Conectar Banco' (Open Finance) na secao
    'Contas' do quadro Financeiro **NAO esta implementado** no estado
    atual do repositorio.

    O behavior B-3 (a ser entregue em fase GREEN) deve:
      1) Ter um botao com o texto 'Conectar Banco' posicionado dentro ou
         proximo do <CollapsiblePanel id="fin-contas"> (Contas do Financeiro)
      2) O botao deve ser usado para acionar o fluxo de integracao via
         Open Finance (Pluggy / `goWithTab('admin', 'Admin', 'integracoes')`
         ou `openChatWith(...)` dedicado)
      3) O botao deve ser explicito (texto 'Conectar Banco' legivel) —
         nao apenas um '+' generico com classe `ph-add` que abre chat
         generico.

BEHAVIOR:
    B-3 — Botao 'Conectar Banco' no Contas do Financeiro (BKL-024):
    O quadro Financeiro deve oferecer um botao explicito 'Conectar Banco'
    no painel 'Contas' (id="fin-contas"), permitindo ao usuario iniciar
    o fluxo de integracao via Open Finance sem depender de um botao
    generico '+' que abre o chat com mensagem vaga.

    **Estado atual (RED):** o painel 'Contas' so tem um botao generico
    '+' (classe `ph-add`) que chama `openChatWith('Quero adicionar uma
    nova conta bancaria')`. Nao ha botao explicito 'Conectar Banco' nem
    chamada explicita ao fluxo Open Finance (`goWithTab('admin', 'Admin',
    'integracoes')` ou equivalente).

AC (Acceptance Criteria):
    AC#3 — Existe um botao 'Conectar Banco' (texto explicito) dentro ou
            adjacente ao <CollapsiblePanel id="fin-contas"> no
            FinanceiroRoom.tsx, e esse botao NAO eh o botao generico
            `ph-add` com '+' que abre chat generico.

Estado atual: RED — AC#3 violada. Nao existe o botao 'Conectar Banco'
no FinanceiroRoom.tsx. O teste falha com pytest.fail() e mensagem
detalhada em pt-BR explicando exatamente o que falta para a feature
ser GREEN.

Anti-Goals:
    1. NAO modificar codigo de producao (sao apenas testes estaticos).
    2. NAO executar / parsear TypeScript — so inspecao textual com regex.
    3. NAO usar mocks, Supabase, browser testing, jsdom.
    4. NAO quebrar funcionalidade existente (decisoes, compromissos, etc.).
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent.parent

FINANCEIRO_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "FinanceiroRoom.tsx"
)


# ── Override do root conftest (teste puramente estatico) ─────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste eh
    pura inspecao de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspecao do TypeScript ────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Le o arquivo e devolve o conteudo como string unica."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-3 (botao 'Conectar Banco' no Financeiro) exige "
        f"que este arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


def _find_fin_contas_panel_range(source: str) -> tuple[int, int] | None:
    """Encontra o bloco <CollapsiblePanel id="fin-contas" ...>...</CollapsiblePanel>
    no codigo-fonte de FinanceiroRoom.tsx e retorna a tupla (start, end)
    com o offset de caracteres.

    Retorna None se o painel nao for encontrado.
    """
    pattern = (
        r'<CollapsiblePanel\b[^>]*\bid\s*=\s*["\']fin-contas["\'][^>]*>'
        r".*?"
        r"</CollapsiblePanel\s*>"
    )
    match = re.search(pattern, source, re.DOTALL)
    if match is None:
        return None
    return (match.start(), match.end())


def _has_explicit_conectar_banco_button(source: str) -> bool:
    """Verifica se existe um botao <button>...</button> cujo conteudo
    textual explicito seja 'Conectar Banco' (case-insensitive, ignorando
    espacos extras). Aceita texto puro, templates e concatenacoes.

    NAO aceita o botao generico 'ph-add' com '+' ou '＋' — esse eh o
    estado RED atual.
    """
    pattern = (
        r"<button\b[^>]*>"
        r"(?:[^<]|<(?!/button\s*>))*?"
        r"Conectar\s+Banco"
        r"(?:[^<]|<(?!/button\s*>))*?"
        r"</button\s*>"
    )
    return bool(re.search(pattern, source, re.IGNORECASE | re.DOTALL))


def _has_ph_add_button_with_plus(source: str) -> bool:
    """Detecta o botao generico RED atual: <button className="ph-add" ...>＋</button>
    ou <button ... ph-add ...>+</button> dentro do painel fin-contas (ou
    no arquivo inteiro, ja que eh um marcador do estado RED)."""
    pattern = (
        r'<button\b[^>]*className\s*=\s*["\']ph-add["\'][^>]*>'
        r"(?:[^<]|<(?!/button\s*>))*?"
        r"[+＋]"
        r"(?:[^<]|<(?!/button\s*>))*?"
        r"</button\s*>"
    )
    return bool(re.search(pattern, source, re.DOTALL))


# ── AC#3 — Botao 'Conectar Banco' no painel fin-contas (RED) ────────────────


def test_b3_ac3_conectar_banco_openfinance():
    """AC#3: Existe um botao explicito 'Conectar Banco' dentro ou adjacente
    ao <CollapsiblePanel id="fin-contas"> no FinanceiroRoom.tsx, e esse
    botao NAO eh o botao generico `ph-add` com '+' que abre chat generico.

    Estado GREEN esperado:
      - Ha um <button>...</button> com o texto 'Conectar Banco' (ou
        equivalente: 'Conectar conta', 'Conectar Open Finance') dentro
        do <CollapsiblePanel id="fin-contas"> ou no action prop do
        proprio painel.
      - Esse botao dispara o fluxo de Open Finance — tipicamente
        `goWithTab('admin', 'Admin', 'integracoes')` ou
        `openChatWith('Quero conectar minha conta bancaria via Open
        Finance')`.

    Estado RED atual:
      - O painel fin-contas tem apenas o botao generico
        <button className="ph-add" onClick={() => openChatWith('Quero
        adicionar uma nova conta bancaria')}>＋</button>.
      - Nao existe nenhum botao com o texto 'Conectar Banco' em
        FinanceiroRoom.tsx.

    Falha (RED) enquanto o botao explicito 'Conectar Banco' nao existir.
    """
    source = _read_text(FINANCEIRO_ROOM_PATH)

    # 1) Garante que o painel fin-contas existe (sanity check)
    panel_range = _find_fin_contas_panel_range(source)
    if panel_range is None:
        pytest.fail(
            "FinanceiroRoom.tsx NAO contem nenhum <CollapsiblePanel "
            "id=\"fin-contas\">.  "
            "Esperado: o painel 'Contas' do Financeiro existe com id "
            "\"fin-contas\" e DEVE ter um botao explicito 'Conectar "
            "Banco' no action prop ou dentro do conteudo do painel.  "
            "\n\n"
            "O QUE FALTA para a feature B-3 (BKL-024) ser GREEN:\n"
            "  - Criar (ou restaurar) o <CollapsiblePanel id=\"fin-contas\" "
            "icon=\"🏦\" title=\"Contas\">.\n"
            "  - Dentro do action prop do painel, adicionar um botao "
            "explicito 'Conectar Banco'."
        )

    # 2) Verifica se existe o botao explicito 'Conectar Banco'
    if _has_explicit_conectar_banco_button(source):
        return  # GREEN — botao explicito presente

    # 3) Estado RED — botao explicito ausente. Coleta evidencia do estado atual.
    panel_text = source[panel_range[0]:panel_range[1]]

    # Procura a action prop do painel para mostrar exatamente o que esta
    # la hoje.
    action_match = re.search(
        r'action\s*=\s*\{([^}]*)\}',
        panel_text,
        re.DOTALL,
    )
    action_text = action_match.group(0) if action_match else "(action prop nao encontrado)"

    has_ph_add = _has_ph_add_button_with_plus(source)

    pytest.fail(
        f"FinanceiroRoom.tsx NAO contem nenhum botao explicito 'Conectar "
        f"Banco' (ou 'Conectar conta' / 'Conectar Open Finance').  "
        f"\n\n"
        f"ESTADO ATUAL (RED) — o que foi encontrado no painel fin-contas:\n"
        f"  - action prop do <CollapsiblePanel id=\"fin-contas\">:\n"
        f"      {action_text.strip()}\n"
        f"  - Botao generico `ph-add` com '+' presente: "
        f"{'SIM' if has_ph_add else 'NAO'}\n"
        f"\n"
        f"O QUE FALTA para a feature B-3 (BKL-024) ser GREEN:\n"
        f"  1) SUBSTITUIR (ou complementar) o botao generico `ph-add` "
        f"com '+' por um botao explicito 'Conectar Banco'.\n"
        f"     Exemplo de action prop GREEN:\n"
        f"       action={{{{\n"
        f"         <button\n"
        f"           className=\"btn bp\"\n"
        f"           onClick={{{{() => goWithTab('admin', 'Admin', "
        f"'integracoes')}}}}\n"
        f"         >\n"
        f"           🏦 Conectar Banco\n"
        f"         </button>\n"
        f"       }}}}\n"
        f"  2) O botao deve estar DENTRO do action prop do "
        f"<CollapsiblePanel id=\"fin-contas\"> (sera visivel no header "
        f"do painel, sempre que o painel estiver expandido OU mesmo "
        f"quando colapsado, dependendo do layout do CollapsiblePanel).\n"
        f"  3) O onClick do botao deve disparar o fluxo de integracao "
        f"Open Finance. Duas opcoes aceitas:\n"
        f"       a) goWithTab('admin', 'Admin', 'integracoes') — leva o "
        f"usuario direto para a aba de Integracoes da AdminScreen, "
        f"onde o card 'Open Finance' (provider 'polp') aciona o widget "
        f"Pluggy.\n"
        f"       b) openChatWith('Quero conectar minha conta bancaria "
        f"via Open Finance') — abre o chat com mensagem especifica "
        f"(NAO usar a mensagem generica 'Quero adicionar uma nova "
        f"conta bancaria').\n"
        f"  4) O texto do botao deve ser 'Conectar Banco' (explicito) — "
        f"NAO '+', '＋', '+ Nova conta' ou similares sem o termo "
        f"'Conectar Banco'.\n"
        f"\n"
        f"REFERENCIAS no codigo:\n"
        f"  - AdminScreen.tsx ja tem o card 'Open Finance' (provider "
        f"'polp') na aba de Integracoes — o botao 'Conectar Banco' "
        f"deve LEVAR o usuario para la.\n"
        f"  - O painel fin-contas esta em FinanceiroRoom.tsx por volta "
        f"da linha 708."
    )
