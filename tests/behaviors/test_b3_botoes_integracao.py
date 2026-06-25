"""RED test for behavior B-3 (BKL-023, BKL-025) — Botões de integração visíveis.

GOAL:
    Painel "Contas" no FinanceiroRoom deve ter botão "Conectar Banco" visível
    (em vez do tiny "+" atual). Painel de config da AgendaRoom deve ter botão
    "Adicionar Integração" visível sem scroll.

BEHAVIOR:
    B-3 — Os botões de integração devem estar visíveis nas salas Financeiro
    (Contas) e Agenda (config), sem necessidade de scroll, e o botão do
    Financeiro deve chamar openChatWith com contexto adequado.

AC (Acceptance Criteria):
    AC#1 — FinanceiroRoom: CollapsiblePanel "Contas" (id="fin-contas") deve
           ter botão visível com texto "Conectar Banco" (classe "btn", não
           "ph-add"), substituindo o tiny "+".
    AC#2 — FinanceiroRoom: O botão "Conectar Banco" deve chamar openChatWith
           com contexto adequado (ex: 'Quero conectar minha conta bancária').
    AC#3 — AgendaRoom: Na aba "config" (id="ag-config"), deve haver botão
           "Adicionar Integração" visível no topo, antes/fora da área
           scrollável (overflowY:"auto").

ESTADO ATUAL (RED):
    - FinanceiroRoom (linha 708): <button className="ph-add">＋</button> —
      tiny "+" em vez de botão estilizado "Conectar Banco".
    - AgendaRoom (linha 250-252): config tab só tem <RoutineConfigSection
      domain="agenda" /> — sem botão "Adicionar Integração".

ESTADO ALVO (GREEN):
    - FinanceiroRoom: <button className="btn bp" ...>Conectar Banco</button>
      no CollapsiblePanel "Contas".
    - AgendaRoom config tab: botão "Adicionar Integração" fixo no topo, fora
      da área scrollável.

Anti-Goals (must NOT be violated):
    1. NAO remover outros botões existentes (← Início, + Nova Missão, etc.)
    2. NAO quebrar as queries/estados existentes da FinanceiroRoom
       (polpAccounts, accounts, consolidatedBalance, etc.)
    3. NAO quebrar as queries/estados existentes da AgendaRoom
       (integrations, scheduleQ, approvals, etc.)
    4. NAO introduzir mocks, dependências de DB ou imports do módulo React
       no teste — o teste é puramente source-inspection.
    5. NAO remover o CollapsiblePanel "Contas" (id="fin-contas") da sidebar
       da FinanceiroRoom.
    6. NAO remover o RoutineConfigSection da aba config da AgendaRoom.

Estratégia de teste (source-inspection):
    - Lê cada TSX como texto puro (Path.read_text).
    - Aplica regex para localizar o painel Contas e o botão.
    - Verifica o texto do botão, classe CSS e chamada a openChatWith.
    - Verifica a presença do botão "Adicionar Integração" na aba config da
      AgendaRoom, antes da área scrollável.
    - Não toca DB, não monta mocks, não importa o módulo React.
    - Falha com pytest.fail() em pt-BR enquanto não implementado (RED) e
      passa quando o Coder implementar (GREEN).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

FINANCEIRO_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "FinanceiroRoom.tsx"
AGENDA_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "AgendaRoom.tsx"


# ── Source-level helpers ───────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Lê o código-fonte TSX como texto puro."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _find_contas_panel_block(source: str) -> str | None:
    """Extrai o bloco do CollapsiblePanel 'Contas' (id='fin-contas').

    Retorna o conteúdo do painel (do <CollapsiblePanel ao </CollapsiblePanel>),
    ou None se não encontrado.
    """
    # Procura pelo CollapsiblePanel com id="fin-contas"
    m = re.search(
        r'<CollapsiblePanel[^>]*id\s*=\s*"fin-contas"[^>]*>.*?</CollapsiblePanel>',
        source,
        re.DOTALL,
    )
    return m.group(0) if m else None


def _find_config_tab_block(source: str) -> str | None:
    """Extrai o bloco da aba config (id='ag-config') da AgendaRoom.

    Busca por id="ag-config" no source e extrai o bloco <div>...</div>
    pelo aninhamento correto de tags, independente de template literals
    no className.
    """
    # Encontra a div com id="ag-config"
    m = re.search(r'<div[^>]*id\s*=\s*"ag-config"[^>]*>', source)
    if not m:
        return None

    div_start = m.start()
    # Percorre o source a partir do início da div, contando aninhamento
    depth = 0
    i = div_start
    while i < len(source):
        if source[i:i+4] == '<div' and not source[i:i+5] == '</div':
            # Check it's an opening <div (not </div)
            # skip past the tag name
            j = i + 4
            # Find the end of the tag (> or />)
            while j < len(source) and source[j] not in ('>', '<'):
                j += 1
            if j < len(source) and source[j] == '>':
                depth += 1
                i = j + 1
            else:
                i += 1
        elif source[i:i+6] == '</div>':
            depth -= 1
            i += 6
            if depth == 0:
                return source[div_start:i]
        else:
            i += 1
    return None


def _find_pb_block(source: str) -> str | None:
    """Extrai o bloco className='pb' da AgendaRoom (área scrollável)."""
    m = re.search(
        r'<div\s+className\s*=\s*"pb"[^>]*>.*?</div>',
        source,
        re.DOTALL,
    )
    return m.group(0) if m else None


# ── Tests ─────────────────────────────────────────────────────────────────


def test_b3_ac1_conectar_banco_visible() -> None:
    """AC#1 — FinanceiroRoom: botão 'Conectar Banco' visível no painel Contas.

    O CollapsiblePanel "Contas" (id='fin-contas') deve ter um botão
    estilizado com classe "btn" (não "ph-add") e texto "Conectar Banco"
    ou "Adicionar Conta", substituindo o tiny "+" atual.
    """
    source = _read_source(FINANCEIRO_PATH)
    panel_block = _find_contas_panel_block(source)

    assert panel_block is not None, (
        "RED — AC#1: CollapsiblePanel 'Contas' (id=fin-contas) não encontrado "
        "em FinanceiroRoom.tsx.\n"
        "  Esperado: <CollapsiblePanel id=\"fin-contas\" ...> presente.\n"
        "  O arquivo deve manter o painel Contas com id='fin-contas'."
    )

    # Verifica que o painel NÃO tem o botão tiny "+" (ph-add)
    has_ph_add = bool(re.search(r'className\s*=\s*"ph-add"', panel_block))
    assert not has_ph_add, (
        "RED — AC#1: O painel Contas AINDA usa botão tiny '+' (className='ph-add').\n"
        "  Esperado: botão estilizado <button className=\"btn ...\">Conectar Banco</button>\n"
        "  em vez de <button className=\"ph-add\">＋</button>.\n"
        "  O Coder deve substituir o tiny '+' por um botão 'Conectar Banco' estilizado."
    )

    # Verifica que existe um botão com texto "Conectar Banco" ou "Adicionar Conta"
    has_conectar_banco = bool(re.search(
        r'Conectar\s*Banco|Adicionar\s*Conta',
        panel_block,
    ))
    assert has_conectar_banco, (
        "RED — AC#1: Nenhum botão com texto 'Conectar Banco' ou 'Adicionar Conta' "
        "encontrado no painel Contas.\n"
        f"  Conteúdo atual do painel:\n  {panel_block[:400]}...\n"
        "  Esperado: <button className=\"btn bp\" ...>Conectar Banco</button>\n"
        "  O Coder deve adicionar um botão estilizado com o texto adequado."
    )

    # Verifica que o botão usa classe "btn" (estilizada, não ph-add)
    button_block_match = re.search(
        r'<button[^>]*>(?:Conectar\s*Banco|Adicionar\s*Conta)',
        panel_block,
    )
    if button_block_match:
        full_button = panel_block[button_block_match.start():button_block_match.end() + 80]
        has_btn_class = bool(re.search(r'className\s*=\s*"[^"]*\bbtn\b[^"]*"', full_button))
        assert has_btn_class, (
            "RED — AC#1: Botão 'Conectar Banco' encontrado mas não usa className='btn ...'.\n"
            f"  Botão atual: {full_button[:120]}...\n"
            "  Esperado: botão estilizado com classe 'btn' (ex: 'btn bp').\n"
            "  O Coder deve usar as classes de botão do design system."
        )


def test_b3_ac2_conectar_banco_openchatwith() -> None:
    """AC#2 — FinanceiroRoom: botão 'Conectar Banco' chama openChatWith.

    O botão com texto "Conectar Banco" ou "Adicionar Conta" no painel Contas
    deve chamar openChatWith() com contexto adequado
    (ex: 'Quero conectar minha conta bancária').

    NOTA: Este teste falha (RED) enquanto o botão "Conectar Banco" não existir.
    O tiny "+" com ph-add que já chama openChatWith NÃO satisfaz este AC,
    pois deve ser substituído por um botão estilizado.
    """
    source = _read_source(FINANCEIRO_PATH)
    panel_block = _find_contas_panel_block(source)

    assert panel_block is not None, (
        "RED — AC#2: CollapsiblePanel 'Contas' (id=fin-contas) não encontrado "
        "em FinanceiroRoom.tsx.\n"
        "  Esperado: painel presente para verificar openChatWith."
    )

    # Verifica se já existe "Conectar Banco" ou "Adicionar Conta" no painel
    has_conectar = bool(re.search(r'Conectar\s*Banco|Adicionar\s*Conta', panel_block))
    if not has_conectar:
        pytest.fail(
            "RED — AC#2: Botão 'Conectar Banco' / 'Adicionar Conta' não encontrado "
            "no painel Contas.\n"
            "  O botão tiny '+' existente (ph-add) já chama openChatWith, mas "
            "precisa ser SUBSTITUÍDO por um botão estilizado.\n"
            "  Esperado: <button className=\"btn bp\" ... onClick={() => openChatWith('...')}>\n"
            "  Conectar Banco</button>\n"
            "  O Coder deve substituir o tiny '+' e garantir que o novo botão "
            "chame openChatWith com contexto adequado."
        )

    # Agora que sabemos que o botão existe, verifica openChatWith no MESMO contexto
    # Procura por um padrão: <button ... onClick=...>Conectar Banco</button>
    # ou <button ...>Conectar Banco</button> com onClick próximo
    btn_with_openchat = re.search(
        r'Conectar\s*Banco[^<]*</button>',
        panel_block,
    )
    if not btn_with_openchat:
        btn_with_openchat = re.search(
            r'Adicionar\s*Conta[^<]*</button>',
            panel_block,
        )

    if btn_with_openchat:
        # Encontra o início do <button que contém este texto
        button_start = panel_block.rfind('<button', 0, btn_with_openchat.start())
        if button_start >= 0:
            button_html = panel_block[button_start:btn_with_openchat.end()]
            has_openchat = bool(re.search(r'openChatWith\s*\(', button_html))
            assert has_openchat, (
                "RED — AC#2: Botão 'Conectar Banco' encontrado mas SEM chamada "
                "a openChatWith.\n"
                f"  Botão: {button_html[:200]}...\n"
                "  Esperado: onClick={() => openChatWith('...')} no botão.\n"
                "  O Coder deve conectar o onClick ao openChatWith com "
                "contexto de conta bancária."
            )
            # Verifica contexto relevante
            arg_match = re.search(r"openChatWith\s*\(\s*'([^']*)'", button_html)
            if arg_match:
                arg = arg_match.group(1).lower()
                has_context = any(kw in arg for kw in ['conta', 'banco', 'conectar', 'bancár', 'bancar', 'integr'])
                assert has_context, (
                    "RED — AC#2: openChatWith encontrado no botão 'Conectar Banco', "
                    "mas o argumento não contém contexto relevante.\n"
                    f"  Argumento: '{arg_match.group(1)}'\n"
                    "  Esperado: contexto com 'conta bancária', 'banco' ou "
                    "'conectar'.\n"
                    "  O Coder deve usar contexto adequado."
                )


def test_b3_ac3_adicionar_integracao() -> None:
    """AC#3 — AgendaRoom: botão 'Adicionar Integração' visível na aba config.

    Na aba "config" (id='ag-config') da AgendaRoom, deve haver um botão
    "Adicionar Integração" visível no topo, fora da área scrollável (antes
    do overflowY:'auto' no className='pb' ou fixo/sticky).
    """
    source = _read_source(AGENDA_PATH)
    config_block = _find_config_tab_block(source)

    assert config_block is not None, (
        "RED — AC#3: Aba config (id=ag-config) não encontrada em AgendaRoom.tsx.\n"
        "  Esperado: <div className=\"tc...\" id=\"ag-config\"> presente.\n"
        "  A aba config deve conter RoutineConfigSection + botão Adicionar Integração."
    )

    # Verifica que "Adicionar Integração" (ou "Adicionar integração") aparece
    # no bloco da aba config
    has_adicionar = bool(re.search(
        r'Adicionar\s*[Ii]ntegra[cç][aã]o',
        config_block,
    ))
    assert has_adicionar, (
        "RED — AC#3: Botão 'Adicionar Integração' não encontrado na aba config "
        "da AgendaRoom.\n"
        "  Esperado: botão estilizado 'Adicionar Integração' no topo da aba config,\n"
        "  fora da área scrollável.\n"
        f"  Conteúdo atual da aba:\n  {config_block[:400]}...\n"
        "  O Coder deve adicionar o botão na aba config da AgendaRoom, "
        "antes/fora do conteúdo scrollável."
    )

    # Verifica que o RoutineConfigSection continua presente (anti-goal #6)
    has_routine_config = bool(re.search(
        r'RoutineConfigSection\s+domain\s*=\s*"agenda"',
        config_block,
    ))
    assert has_routine_config, (
        "RED — AC#3 (anti-goal): RoutineConfigSection domain='agenda' foi REMOVIDO "
        "da aba config da AgendaRoom.\n"
        "  ANTI-GOAL VIOLATED: o RoutineConfigSection deve ser PRESERVADO.\n"
        "  O Coder deve adicionar o botão 'Adicionar Integração' SEM remover\n"
        "  o RoutineConfigSection existente."
    )

    # Verifica que o botão está ANTES da área scrollável
    # A área scrollável é o div com className="pb" e overflowY:'auto'
    pb_block = _find_pb_block(source)
    if pb_block:
        # Encontra a posição do config tab e do pb block no source
        config_start = source.find('id="ag-config"')
        pb_start = source.find('className="pb"')

        # O botão Adicionar Integração deve estar antes do pb block,
        # ou o pb block não deve conter o config tab content
        if config_start < pb_start:
            # config tab está renderizado DENTRO do pb block
            # Nesse caso, o botão deve estar antes do overflowY
            # Ou usamos position:sticky
            has_sticky_or_overflow = bool(re.search(
                r'position\s*:\s*sticky|overflowY\s*:\s*auto',
                config_block,
            ))
            # Se não tem sticky, verifica se o botão está antes do scroll container
            if not has_sticky_or_overflow:
                pytest.fail(
                    "RED — AC#3: Botão 'Adicionar Integração' encontrado, mas pode estar "
                    "dentro da área scrollável.\n"
                    "  Esperado: botão fixo no topo (position:sticky) ou posicionado "
                    "fora da área com overflowY:'auto'.\n"
                    "  O Coder deve garantir que o botão esteja sempre visível sem scroll,\n"
                    "  seja usando position:sticky no topo ou renderizando fora do "
                    "container scrollável."
                )
