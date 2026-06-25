"""RED test for behavior B-4 — Botao 'Adicionar Integracao' na Agenda fixo/sticky (BKL-025) (NAO implementado).

GOAL:
    Validar que a feature de tornar o botao 'Adicionar integracao' da Agenda
    fixo/sticky (sempre visivel, fora do CollapsiblePanel) **NAO esta
    implementada** no estado atual do repositorio.

    O behavior B-4 (a ser entregue em fase GREEN) deve:
      1) Ter o botao 'Adicionar integracao' posicionado como sticky/fixed
         (position: sticky ou position: fixed no className ou style do
         botao ou de seu container direto)
      2) Ter o botao 'Adicionar integracao' FORA de qualquer
         <CollapsiblePanel> (para que nao seja escondido/colapsado)
      3) Garantir que existe pelo menos um botao 'Adicionar integracao'
         FORA de qualquer CollapsiblePanel (o botao visivel sempre)

BEHAVIOR:
    B-4 — Botao 'Adicionar Integracao' na Agenda fixo/sticky (BKL-025):
    O botao 'Adicionar integracao' deve estar sempre visivel na Agenda,
    com posicionamento sticky/fixed, e fora do <CollapsiblePanel> de
    'Calendarios' para que nao seja escondido quando o painel for
    colapsado pelo usuario.

    **Estado atual (RED):** o botao esta DENTRO do
    <CollapsiblePanel id="agenda-calendarios">, sem posicionamento
    sticky/fixed. Quando o usuario colapsa o painel 'Calendarios', o
    botao 'Adicionar integracao' fica invisivel, dificultando o
    onboarding de novas fontes.

AC (Acceptance Criteria):
    AC#1 — O botao 'Adicionar integracao' NAO esta posicionado como
            sticky/fixo (nao tem className ou style indicando
            position:sticky ou position:fixed).
    AC#2 — O botao 'Adicionar integracao' esta DENTRO de um
            CollapsiblePanel (ou seja, pode ser escondido/colapsado).
    AC#3 — Nao existe um botao 'Adicionar integracao' DUPLICADO fora
            do CollapsiblePanel (o unico botao esta dentro do panel).

Estado atual: RED — todas as ACs violadas. O botao esta dentro do
CollapsiblePanel, sem sticky/fixed, e nao ha botao duplicado fora.
Cada teste falha com pytest.fail() e mensagem detalhada em pt-BR
explicando exatamente o que falta para a feature ser GREEN.

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

AGENDA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "AgendaRoom.tsx"
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
        f"O behavior B-4 (botao fixo/sticky na Agenda) exige que este "
        f"arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


def _find_button_positions(source: str) -> list[tuple[int, int]]:
    """Encontra todas as ocorrencias do botao 'Adicionar integracao'
    no codigo-fonte e retorna lista de tuplas (start, end) com as
    posicoes (offset de caracteres) do elemento <button>...</button>
    completo.

    Aceita tanto 'integracao' quanto 'integração' (com ou sem acento).
    O botao pode ser multi-linha (atributos em varias linhas).
    """
    pattern = (
        r"<button\b[^>]*>"                              # abertura <button ...>
        r"(?:[^<]|<(?!/button\s*>))*?"                  # conteudo (sem abrir </button>)
        r"Adicionar\s+integra[çc][ãa]o"                # texto do botao
        r"(?:[^<]|<(?!/button\s*>))*?"                  # resto do conteudo
        r"</button\s*>"                                 # fechamento
    )
    return [
        (m.start(), m.end())
        for m in re.finditer(pattern, source, re.DOTALL | re.IGNORECASE)
    ]


def _button_has_sticky_or_fixed(source: str, start: int, end: int) -> bool:
    """Verifica se o elemento <button> tem indicacao de position:sticky
    ou position:fixed no style ou className.

    Tambem checa o container direto (ate 400 chars antes) para o caso
    de a sticky/fixed ser aplicada em um <div> wrapper.
    """
    button_text = source[start:end]

    # 1) position: 'sticky' / position: 'fixed' no style inline (objeto TS)
    if re.search(
        r"position\s*:\s*['\"]?(?:sticky|fixed)\b",
        button_text,
        re.IGNORECASE,
    ):
        return True

    # 2) className contendo 'sticky' ou 'fixed' como palavra (Tailwind)
    if re.search(
        r"className\s*=\s*\{?\{?[`'\"][^`'\"}]*\b(?:sticky|fixed)\b[^`'\"}]*[`'\"]\}?\}?",
        button_text,
        re.IGNORECASE,
    ):
        return True

    # 3) style={{ position: 'sticky', ... }} (objeto JSX)
    if re.search(
        r"style\s*=\s*\{\{[^}]*position\s*:\s*['\"]?(?:sticky|fixed)\b",
        button_text,
        re.IGNORECASE,
    ):
        return True

    # 4) container direto (ate 400 chars antes) com sticky/fixed
    window_start = max(0, start - 400)
    window = source[window_start:start]

    # Procura o ultimo <div ou <span aberto sem fechamento antes do botao
    if re.search(r"position\s*:\s*['\"]?(?:sticky|fixed)\b", window, re.IGNORECASE):
        return True
    if re.search(
        r"style\s*=\s*\{\{[^}]*position\s*:\s*['\"]?(?:sticky|fixed)\b",
        window,
        re.IGNORECASE,
    ):
        return True

    return False


def _find_collapsible_panel_ranges(source: str) -> list[tuple[int, int]]:
    """Encontra todos os blocos <CollapsiblePanel ...>...</CollapsiblePanel>
    no codigo-fonte e retorna lista de tuplas (start, end) com as
    posicoes (offset de caracteres).

    Usa non-greedy match — assume que os paineis nao estao aninhados.
    """
    pattern = r"<CollapsiblePanel\b[^>]*>.*?</CollapsiblePanel\s*>"
    return [
        (m.start(), m.end())
        for m in re.finditer(pattern, source, re.DOTALL)
    ]


def _is_position_inside_any_panel(pos: int, panel_ranges: list[tuple[int, int]]) -> bool:
    """Verifica se a posicao (offset) esta dentro de algum CollapsiblePanel."""
    for p_start, p_end in panel_ranges:
        if p_start <= pos < p_end:
            return True
    return False


# ── AC#1 — Botao NAO esta sticky/fixed (RED: o botao DEVERIA estar sticky) ──


def test_b4_ac1_botao_nao_sticky():
    """AC#1: O botao 'Adicionar integracao' NAO esta posicionado como
    sticky/fixo (nao tem className ou style indicando position:sticky
    ou position:fixed).

    Estado GREEN esperado: o botao (ou seu container direto) tem
    position: 'sticky' ou position: 'fixed' no style, ou uma classe
    CSS com sticky/fixed (Tailwind: className="... sticky ...").

    Falha (RED) enquanto o botao nao tiver posicionamento sticky/fixed.
    """
    source = _read_text(AGENDA_ROOM_PATH)

    button_positions = _find_button_positions(source)

    if not button_positions:
        pytest.fail(
            "AgendaRoom.tsx NAO contem nenhum botao 'Adicionar integracao'.  "
            "Esperado: pelo menos um botao com o texto 'Adicionar integracao' "
            "(ou 'Adicionar integração') que DEVE ter position:sticky ou "
            "position:fixed no style/className.  "
            "Sugestao de implementacao GREEN: adicionar "
            "style={{ position: 'sticky', top: 0 }} ao botao ou ao seu "
            "container direto (<div> wrapper)."
        )

    # Verifica se PELO MENOS UM botao tem sticky/fixed
    botoes_com_sticky = [
        (s, e) for s, e in button_positions
        if _button_has_sticky_or_fixed(source, s, e)
    ]

    if botoes_com_sticky:
        return  # GREEN — pelo menos um botao tem sticky/fixed

    # Nenhum botao tem sticky/fixed (estado RED atual)
    pytest.fail(
        f"AgendaRoom.tsx tem {len(button_positions)} botao(s) "
        f"'Adicionar integracao', mas NENHUM possui position:sticky ou "
        f"position:fixed no className ou style.  "
        f"\n\n"
        f"O QUE FALTA para a feature B-4 (BKL-025) ser GREEN:\n"
        f"  - Adicionar position: 'sticky' (ou 'fixed') ao style do botao\n"
        f"    Exemplo: style={{{{ position: 'sticky', top: 0, zIndex: 10 }}}}\n"
        f"  - OU adicionar a classe 'sticky' (Tailwind) ao className do botao\n"
        f"    Exemplo: className=\"btn bs sticky\"\n"
        f"  - OU envolver o botao em um <div style={{{{ position: 'sticky' }}}}> "
        f"para que o container direto tenha o posicionamento fixo."
    )


# ── AC#2 — Botao esta DENTRO de CollapsiblePanel (RED: DEVERIA estar fora) ──


def test_b4_ac2_botao_dentro_collapsible():
    """AC#2: O botao 'Adicionar integracao' esta DENTRO de um
    CollapsiblePanel (ou seja, pode ser escondido/colapsado).

    Estado GREEN esperado: o botao 'Adicionar integracao' esta FORA de
    qualquer <CollapsiblePanel>, em um local fixo/sticky do layout da
    Agenda, para que nunca seja escondido quando o usuario colapsar o
    painel 'Calendarios' (id="agenda-calendarios").

    Falha (RED) enquanto o botao estiver dentro de um CollapsiblePanel.
    """
    source = _read_text(AGENDA_ROOM_PATH)

    button_positions = _find_button_positions(source)
    panel_ranges = _find_collapsible_panel_ranges(source)

    if not button_positions:
        pytest.fail(
            "AgendaRoom.tsx NAO contem nenhum botao 'Adicionar integracao'.  "
            "Esperado: um botao com o texto 'Adicionar integracao' que "
            "DEVE estar FORA de qualquer <CollapsiblePanel> para ser "
            "sempre visivel na Agenda."
        )

    # Verifica se TODOS os botoes estao dentro de paineis (estado RED atual)
    botoes_dentro_de_paineis = [
        (s, e) for s, e in button_positions
        if _is_position_inside_any_panel(s, panel_ranges)
    ]
    botoes_fora_de_paineis = [
        (s, e) for s, e in button_positions
        if not _is_position_inside_any_panel(s, panel_ranges)
    ]

    if botoes_fora_de_paineis and not botoes_dentro_de_paineis:
        return  # GREEN — todos os botoes estao fora

    # Pelo menos um botao (ou todos) estao dentro de um CollapsiblePanel
    painel_mais_proximo = None
    if botoes_dentro_de_paineis:
        btn_start = botoes_dentro_de_paineis[0][0]
        for p_start, p_end in panel_ranges:
            if p_start <= btn_start < p_end:
                painel_mais_proximo = (p_start, p_end)
                break

    painel_id = "desconhecido"
    if painel_mais_proximo is not None:
        painel_trecho = source[painel_mais_proximo[0]:painel_mais_proximo[1]]
        id_match = re.search(r'id\s*=\s*["\']([^"\']+)["\']', painel_trecho)
        if id_match:
            painel_id = id_match.group(1)

    pytest.fail(
        f"AgendaRoom.tsx tem {len(button_positions)} botao(s) "
        f"'Adicionar integracao', dos quais {len(botoes_dentro_de_paineis)} "
        f"estao DENTRO de <CollapsiblePanel>.  "
        f"O botao problematico esta dentro do painel id='{painel_id}'.  "
        f"\n\n"
        f"O QUE FALTA para a feature B-4 (BKL-025) ser GREEN:\n"
        f"  - MOVER o botao 'Adicionar integracao' para FORA do "
        f"<CollapsiblePanel id=\"{painel_id}\">.\n"
        f"  - Posicionar o botao em um local fixo/sticky do layout da "
        f"Agenda (por exemplo, no header '.rh' ou em uma barra superior "
        f"da coluna direita '.rcol', acima de todos os CollapsiblePanel).\n"
        f"  - Assim, quando o usuario colapsar o painel 'Calendarios', "
        f"o botao 'Adicionar integracao' continuara visivel."
    )


# ── AC#3 — NAO existe botao duplicado fora do CollapsiblePanel (RED) ────────


def test_b4_ac3_sem_botao_fora_panel():
    """AC#3: Nao existe um botao 'Adicionar integracao' DUPLICADO fora
    do CollapsiblePanel (o unico botao esta dentro do panel).

    Estado GREEN esperado: existe PELO MENOS UM botao 'Adicionar
    integracao' posicionado FORA de qualquer <CollapsiblePanel>, em
    local fixo/sticky, para que o usuario sempre tenha acesso rapido a
    integracao de novas fontes (Google Calendar, Outlook, Notion, etc.)
    sem precisar abrir o painel 'Calendarios'.

    Falha (RED) enquanto nao houver nenhum botao fora de CollapsiblePanel.
    """
    source = _read_text(AGENDA_ROOM_PATH)

    button_positions = _find_button_positions(source)
    panel_ranges = _find_collapsible_panel_ranges(source)

    if not button_positions:
        pytest.fail(
            "AgendaRoom.tsx NAO contem nenhum botao 'Adicionar integracao'.  "
            "Esperado: pelo menos um botao 'Adicionar integracao' "
            "posicionado FORA de qualquer <CollapsiblePanel> na Agenda.  "
            "\n\n"
            "O QUE FALTA para a feature B-4 (BKL-025) ser GREEN:\n"
            "  - Criar um botao 'Adicionar integracao' em um local fixo "
            "do layout da Agenda (header '.rh', ou acima dos "
            "CollapsiblePanel na coluna '.rcol')."
        )

    # Verifica se existe PELO MENOS UM botao fora de qualquer painel
    botoes_fora = [
        (s, e) for s, e in button_positions
        if not _is_position_inside_any_panel(s, panel_ranges)
    ]

    if botoes_fora:
        return  # GREEN — existe pelo menos um botao fora

    # Todos os botoes estao dentro de paineis (estado RED atual)
    pytest.fail(
        f"AgendaRoom.tsx tem {len(button_positions)} botao(s) "
        f"'Adicionar integracao', mas TODOS estao DENTRO de "
        f"<CollapsiblePanel>. Nao existe nenhum botao 'Adicionar "
        f"integracao' visivel FORA do panel.  "
        f"\n\n"
        f"O QUE FALTA para a feature B-4 (BKL-025) ser GREEN:\n"
        f"  - Adicionar um botao DUPLICADO 'Adicionar integracao' FORA "
        f"do <CollapsiblePanel id=\"agenda-calendarios\">.\n"
        f"  - Sugestao: posicionar o botao no header da Agenda "
        f"(<div className=\"rh\">) ou em uma barra sticky acima da "
        f"coluna direita, com position: 'sticky' para que sempre "
        f"esteja visivel ao rolar a pagina.\n"
        f"  - O botao duplicado deve ter o mesmo onClick do original: "
        f"onClick={{{{() => goWithTab('admin', 'Admin', 'integracoes')}}}}."
    )
