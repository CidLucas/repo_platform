"""RED test for behavior B-5 — Cadeia de scroll do AppShell (shell/main/screen).

GOAL:
    A app blu_v3 tem um layout de 3 camadas aninhadas responsaveis
    pelo scroll da área de conteúdo:

        <html><body>  → height:100%
          <div class="shell">  → height:100vh; overflow:hidden
            <main class="main">  → flex child, deve permitir shrink
              <div class="screen …">  → flex column, deve permitir shrink
                conteúdo scrollable interno (ex.: .pb, .rcol)

    Para que a árvore inteira de scroll funcione — sem o conteúdo
    "estourar" a viewport inteira quando uma página é mais alta que
    a tela — os containers flex (.main, .screen) PRECISAM permitir
    encolhimento.  Isso é feito com a propriedade CSS ``min-height:
    0``, que sobrescreve o default de flex items (``min-height:
    auto``) que, no Chrome/Firefox, faz o item crescer até caber o
    conteúdo, quebrando o scroll do pai.

    Sem ``min-height:0`` em .main e .screen, a página inteira rola
    (window scroll) em vez do scroll interno do .shell.  O resultado
    é a topbar/sidebar "fugindo" da tela e o conteúdo do room
    aparecendo por baixo delas.

BEHAVIOR:
    B-5 — Cadeia de scroll AppShell: ``.main`` e ``.screen`` em
    ``global.css`` devem ter ``min-height: 0`` para que o scroll
    funcione em camadas (window → shell → main → screen → content),
    sem o conteúdo forçar a viewport a crescer.

    **Estado atual (RED):**
    - ``.main`` (linha ~115) tem ``overflow:hidden; height:100%`` mas
      NAO tem ``min-height:0``.  Sem isso, como .main é flex item de
      .shell (que é display:grid com row ``1fr``), o conteúdo pode
      forçar .main a crescer além do espaço disponível.
    - ``.screen`` (linha ~118) tem ``display:none; height:100%;
      flex-direction:column; overflow:hidden`` mas NAO tem
      ``min-height:0``.  O mesmo problema: como flex item de .main,
      o conteúdo de um .screen ativo pode forçar .main a crescer.

    **Estado alvo (GREEN):**
    - ``.main{overflow:hidden;height:100%;min-height:0;}`` — passa a
      permitir encolhimento.
    - ``.screen{...; min-height:0;}`` — passa a permitir
      encolhimento.
    - A cadeia completa: ``html,body{height:100%}`` +
      ``.shell{height:100vh;overflow:hidden}`` + ``.main{min-height:0}``
      + ``.screen{min-height:0}`` fica intacta.

    Os outros elementos da cadeia JÁ estao corretos (NAO precisam
    de mudanca):
    - ``.shell{...;height:100vh;overflow:hidden;}`` (linha 79) — OK.
    - ``.rcol{...;min-height:0;overflow-y:auto;...}`` (linha 198) — OK.
    - ``AppShell.tsx`` (linhas 127/130/131) tem ``<div className="shell">``,
      ``<main className="main">`` e ``<div className={`screen...}>`` — OK.

AC (Acceptance Criteria):
    AC#1 — ``.main`` em ``global.css`` tem ``min-height: 0`` (RED).
    AC#2 — ``.screen`` em ``global.css`` tem ``min-height: 0`` (RED).
    AC#3 — ``.shell`` em ``global.css`` tem ``overflow: hidden``
            (GREEN, ja existe na linha 79).
    AC#4 — Cadeia completa de scroll em ``global.css``:
              html,body tem height:100%,
              .shell tem height:100vh + overflow:hidden,
              .main tem min-height:0,
              .screen tem min-height:0.
            (RED — quebra em .main e .screen).
    AC#5 — ``.rcol`` em ``global.css`` rola (overflow-y: auto)
            (GREEN, ja existe na linha 198).
    AC#6 — ``AppShell.tsx`` tem a estrutura
              ``<div className="shell"> <main className="main">
               <div className={`screen...`}>``
            (GREEN, ja existe).

DECISAO:
    Estratégia: source_inspection (regex sobre o CSS e o JSX).
    Arquivos alvos:
      - apps/blu_v3/src/styles/global.css
      - apps/blu_v3/src/components/shell/AppShell.tsx

Anti-Goals (must NOT be violated):
    1. NAO modificar código de produção — o teste é puramente
       estático.  A implementação da feature será feita na fase
       GREEN.
    2. NAO importar ou executar código TypeScript/React — o teste
       apenas lê os arquivos como texto e usa regex.
    3. NAO usar fixtures de DB ou rede — o teste é determinístico
       e roda sem rede.
    4. NAO exigir mudanças em .shell, .rcol, .pb, etc — apenas
       .main e .screen precisam de min-height:0.  Os outros ja
       estao OK.
    5. NAO exigir mudanças no ``AppShell.tsx`` (já tem a estrutura
       certa).
"""

import re
from pathlib import Path

import pytest


# ── Constants: paths da interface pública sob teste ──────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

GLOBAL_CSS_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "styles"
    / "global.css"
)

APPSHELL_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shell"
    / "AppShell.tsx"
)


# ── Override do root conftest (teste puramente estático) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção ────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o arquivo e devolve o conteúdo como string única."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-5 (cadeia de scroll AppShell) exige que "
        f"este arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


def _get_css_block(css_content: str, selector: str) -> str:
    """Devolve o body da PRIMEIRA regra CSS cujo seletor bate
    exatamente com ``selector`` (ex.: ``.main``).  Retorna ``""`` se
    nenhuma regra for encontrada.  O body é tudo entre ``{`` e o
    próximo ``}`` no mesmo nível.
    """
    escaped = re.escape(selector)
    match = re.search(
        rf"{escaped}\s*\{{([^}}]*)\}}",
        css_content,
    )
    if match is None:
        return ""
    return match.group(1)


# ── AC#1 — .main tem min-height:0 ─────────────────────────────────


def test_b5_ac1_main_min_height_zero():
    """AC#1: A regra CSS ``.main{...}`` em ``global.css`` DEVE
    conter a propriedade ``min-height: 0`` (e nada mais que
    conflite — qualquer valor != 0 faz o flex item nao encolher).

    Antes (RED): ``global.css`` linha 115 tem
        ``.main{overflow:hidden;height:100%;}``
    sem ``min-height:0``.  Como .main é flex item do .shell
    (display:grid com row ``1fr``), sem ``min-height:0`` o default
    ``min-height:auto`` faz o conteúdo "empurrar" .main além da
    altura disponível, quebrando o scroll interno.

    Depois (GREEN): ``.main{overflow:hidden;height:100%;min-height:0;}``
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".main")
    assert block, (
        f"Pre-condicao violada: regra ``.main{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"min-height\s*:\s*0\b", block):
        pytest.fail(
            "AC#1 violada — RED.  A regra ``.main{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``min-height: 0``.\n\n"
            f"Regra atual: ``.main{{{block}}}``\n\n"
            "O behavior B-5 (cadeia de scroll AppShell) exige que "
            "``min-height: 0`` seja adicionado a ``.main`` para que "
            "o flex item permita encolhimento.  Sem isso, o default "
            "``min-height: auto`` faz o conteúdo do .main crescer "
            "além do espaço disponível no .shell, quebrando o "
            "scroll interno e fazendo a página inteira rolar (window "
            "scroll em vez de scroll do .shell).\n\n"
            "GREEN deve alterar a regra para:\n"
            "  .main{overflow:hidden;height:100%;min-height:0;}\n\n"
            "ATENCAO: o teste verifica especificamente a presença de "
            "``min-height: 0`` dentro do bloco ``.main{...}`` "
            "(primeira ocorrencia).  Adicionar a propriedade em uma "
            "regra mais específica (ex.: ``main .main`` ou media "
            "query) NAO satisfaz este AC — a propriedade deve estar "
            "na regra base ``.main{...}``."
        )


# ── AC#2 — .screen tem min-height:0 ────────────────────────────────


def test_b5_ac2_screen_min_height_zero():
    """AC#2: A regra CSS ``.screen{...}`` em ``global.css`` DEVE
    conter ``min-height: 0``.

    Antes (RED): ``global.css`` linha 118 tem
        ``.screen{display:none;height:100%;flex-direction:column;overflow:hidden;}``
    sem ``min-height:0``.  Como .screen é flex column dentro de
    .main (que é flex item do .shell), sem ``min-height:0`` o
    conteúdo de uma página (ex.: FinanceiroRoom com várias tabelas)
    força .main a crescer.

    Depois (GREEN): ``.screen{display:none;height:100%;flex-direction:column;overflow:hidden;min-height:0;}``
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".screen")
    assert block, (
        f"Pre-condicao violada: regra ``.screen{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"min-height\s*:\s*0\b", block):
        pytest.fail(
            "AC#2 violada — RED.  A regra ``.screen{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``min-height: 0``.\n\n"
            f"Regra atual: ``.screen{{{block}}}``\n\n"
            "O behavior B-5 (cadeia de scroll AppShell) exige que "
            "``min-height: 0`` seja adicionado a ``.screen`` para "
            "que o flex column permita encolhimento dentro de "
            "``.main``.  Sem isso, o conteúdo de uma página "
            "FinanceiroRoom / EstrategiaRoom pode estourar a "
            "viewport e fazer a página inteira rolar.\n\n"
            "GREEN deve alterar a regra para:\n"
            "  .screen{display:none;height:100%;flex-direction:column;"
            "overflow:hidden;min-height:0;}\n\n"
            "ATENCAO: o teste verifica a PRIMEIRA ocorrencia de "
            "``.screen{...}`` (a regra base, nao a de media query "
            "na linha 916).  Adicionar ``min-height: 0`` apenas na "
            "media query NAO satisfaz este AC — a propriedade deve "
            "estar na regra base."
        )


# ── AC#3 — .shell tem overflow:hidden ──────────────────────────────


def test_b5_ac3_shell_overflow_hidden():
    """AC#3: A regra CSS ``.shell{...}`` em ``global.css`` DEVE ter
    ``overflow: hidden`` para que o conteúdo não vaze para fora do
    viewport.

    Estado atual (GREEN): ``global.css`` linha 79 tem
        ``.shell{position:relative;z-index:1;display:grid;grid-template-columns:var(--sw) 1fr;grid-template-rows:var(--th) 1fr;height:100vh;overflow:hidden;}``
    ja contem ``overflow:hidden``.  O teste passa enquanto isso for
    verdade.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".shell")
    assert block, (
        f"Pre-condicao violada: regra ``.shell{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"overflow\s*:\s*hidden\b", block):
        pytest.fail(
            "AC#3 violada.  A regra ``.shell{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``overflow: hidden``.\n\n"
            f"Regra atual: ``.shell{{{block}}}``\n\n"
            "O behavior B-5 (cadeia de scroll AppShell) exige que "
            "``.shell`` tenha ``overflow: hidden`` para que a "
            "viewport nao cresca alem de 100vh.  Sem isso, o "
            "conteúdo do .main/.screen estende o .shell e a pagina "
            "inteira rola (window scroll).\n\n"
            "GREEN deve garantir que a regra ``.shell{...}`` "
            "contenha a propriedade ``overflow:hidden`` "
            "(junto com ``height:100vh``)."
        )


# ── AC#4 — Cadeia completa de scroll ───────────────────────────────


def test_b5_ac4_full_scroll_chain():
    """AC#4: A cadeia completa de scroll do AppShell deve estar
    integra em ``global.css``:

      1. ``html,body{height:100%}``            — base da viewport.
      2. ``.shell{height:100vh; overflow:hidden}`` — limita o shell
         à altura da viewport, sem propagar overflow.
      3. ``.main{min-height:0}``                — permite encolhimento
         como flex item do .shell (display:grid com row 1fr).
      4. ``.screen{min-height:0}``             — permite encolhimento
         como flex item do .main (flex column).

    A falha de qualquer elo quebra a cadeia: o conteudo de uma pagina
    alta (ex.: FinanceiroRoom com graficos) força o .main/.screen
    a crescer alem do 100vh, e a pagina inteira comeca a rolar no
    window em vez de rolar dentro do .shell.

    Estado atual (RED): os elos 3 e 4 estao quebrados — ``.main`` e
    ``.screen`` nao tem ``min-height: 0``.  Elos 1 e 2 estao OK.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    # Elo 1: html,body tem height:100%
    if not re.search(
        r"html\s*,\s*body\s*\{[^}]*height\s*:\s*100%",
        css_content,
    ):
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 1.\n\n"
            "A regra ``html,body{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            "``height: 100%``.  Sem isso, ``<body>`` nao ocupa a "
            "viewport inteira e o ``.shell{height:100vh}`` fica "
            "sem referencia para 100vh.\n\n"
            "GREEN deve garantir a regra:\n"
            "  html,body{height:100%;}"
        )

    # Elo 2: .shell tem height:100vh + overflow:hidden
    shell_block = _get_css_block(css_content, ".shell")
    if not shell_block:
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 2.\n\n"
            f"Regra ``.shell{{...}}`` nao encontrada em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
        )
    if not re.search(r"height\s*:\s*100vh\b", shell_block):
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 2.\n\n"
            "A regra ``.shell{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``height: 100vh`` (regra atual: ``.shell{{{shell_block}}}``).\n\n"
            "Sem ``height: 100vh`` no .shell, o conteudo do .main "
            "pode esticar o .shell alem da viewport e a pagina "
            "inteira rola no window."
        )
    if not re.search(r"overflow\s*:\s*hidden\b", shell_block):
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 2.\n\n"
            "A regra ``.shell{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} tem "
            "``height: 100vh`` mas NAO tem ``overflow: hidden``.\n\n"
            "Sem ``overflow: hidden``, o conteudo que vaza do .shell "
            "vaza para o body e a pagina inteira rola no window."
        )

    # Elo 3: .main tem min-height:0
    main_block = _get_css_block(css_content, ".main")
    if not main_block:
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 3.\n\n"
            f"Regra ``.main{{...}}`` nao encontrada em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
        )
    if not re.search(r"min-height\s*:\s*0\b", main_block):
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 3.\n\n"
            "A regra ``.main{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``min-height: 0`` (regra atual: ``.main{{{main_block}}}``).\n\n"
            "Sem ``min-height: 0`` em .main (que é flex item do "
            ".shell display:grid com row ``1fr``), o default "
            "``min-height: auto`` faz o conteudo do .main crescer "
            "alem do espaço disponível.  A pagina inteira comeca a "
            "rolar no window.\n\n"
            "GREEN deve adicionar ``min-height: 0`` a regra "
            "``.main{...}`` (o mesmo fix do AC#1)."
        )

    # Elo 4: .screen tem min-height:0
    screen_block = _get_css_block(css_content, ".screen")
    if not screen_block:
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 4.\n\n"
            f"Regra ``.screen{{...}}`` nao encontrada em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
        )
    if not re.search(r"min-height\s*:\s*0\b", screen_block):
        pytest.fail(
            "AC#4 violada — RED.  Cadeia de scroll quebrada no elo 4.\n\n"
            "A regra ``.screen{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``min-height: 0`` (regra atual: ``.screen{{{screen_block}}}``).\n\n"
            "Sem ``min-height: 0`` em .screen (que é flex column "
            "dentro de .main), o conteudo de uma pagina alta "
            "(ex.: FinanceiroRoom) força .main a crescer alem do "
            "100vh.  A pagina inteira comeca a rolar no window.\n\n"
            "GREEN deve adicionar ``min-height: 0`` a regra "
            "``.screen{...}`` (o mesmo fix do AC#2)."
        )


# ── AC#5 — .rcol rola ──────────────────────────────────────────────


def test_b5_ac5_rcol_scrolls():
    """AC#5: A regra CSS ``.rcol{...}`` em ``global.css`` DEVE ter
    ``overflow-y: auto`` para que a coluna direita do
    HomePage/rooms faca scroll interno (em vez de esticar o
    grid do .home-grid/.room-grid).

    Estado atual (GREEN): ``global.css`` linha 198 tem
        ``.rcol{grid-column:2;grid-row:1;display:flex;flex-direction:column;gap:9px;min-height:0;overflow-y:auto;position:relative;}``
    ja contem ``overflow-y: auto``.  O teste passa enquanto isso
    for verdade.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".rcol")
    assert block, (
        f"Pre-condicao violada: regra ``.rcol{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"overflow-y\s*:\s*auto\b", block):
        pytest.fail(
            "AC#5 violada.  A regra ``.rcol{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``overflow-y: auto``.\n\n"
            f"Regra atual: ``.rcol{{{block}}}``\n\n"
            "O behavior B-5 (cadeia de scroll AppShell) exige que "
            "``.rcol`` (coluna direita do HomePage/rooms) faca "
            "scroll interno.  Sem ``overflow-y: auto``, o conteudo "
            "de .rcol (cards de Agenda, KPIs, etc.) estica o "
            "``grid-template-rows: 1fr 120px`` do .home-grid/"
            ".room-grid e o conteudo é cortado.\n\n"
            "GREEN deve adicionar ``overflow-y: auto`` a regra "
            "``.rcol{...}``."
        )


# ── AC#6 — Estrutura do AppShell ───────────────────────────────────


def test_b5_ac6_appshell_structure():
    """AC#6: O componente ``AppShell.tsx`` em
    ``apps/blu_v3/src/components/shell/`` DEVE ter a estrutura
    HTML de 3 camadas usada pela cadeia de scroll:

      1. ``<div className="shell">``         — wrapper externo.
      2. ``<main className="main">``          — area de conteudo.
      3. ``<div className={`screen...`} …>``  — cada pagina
         (``screen.on`` é a ativa, ``screen`` sem ``.on`` fica
         ``display:none``).

    Estado atual (GREEN): ``AppShell.tsx`` (linhas 127, 130, 131)
    ja tem os 3 elementos.  O teste passa enquanto isso for
    verdade.
    """
    content = _read_text(APPSHELL_PATH)

    if not re.search(r'<div\s+className\s*=\s*["\']shell["\']', content):
        pytest.fail(
            "AC#6 violada.  O componente ``AppShell`` em "
            f"{APPSHELL_PATH.relative_to(REPO_ROOT)} NAO contem "
            "um ``<div className=\"shell\">`` como wrapper externo.\n\n"
            "A cadeia de scroll do B-5 exige essa tag como ponto de "
            "partida (é onde o ``.shell{height:100vh;overflow:hidden}`` "
            "do CSS é aplicado).  Sem ela, o .main fica solto e o "
            "scroll quebra.\n\n"
            "GREEN deve garantir que o JSX raiz seja:\n"
            "  <div className=\"shell\">"
        )

    if not re.search(r'<main\s+className\s*=\s*["\']main["\']', content):
        pytest.fail(
            "AC#6 violada.  O componente ``AppShell`` em "
            f"{APPSHELL_PATH.relative_to(REPO_ROOT)} NAO contem "
            "um ``<main className=\"main\">`` envolvendo os screens.\n\n"
            "A tag ``<main>`` é o flex item do .shell onde os "
            "``<div className={`screen...`}>`` sao montados.  Sem "
            "ela, a regra CSS ``.main{...}`` nao é aplicada a "
            "nenhum elemento e a cadeia de scroll quebra.\n\n"
            "GREEN deve garantir que os screens estejam dentro de:\n"
            "  <main className=\"main\">\n    …screens…\n  </main>"
        )

    if not re.search(
        r'<div\s+className\s*=\s*\{\s*`screen',
        content,
    ):
        pytest.fail(
            "AC#6 violada.  O componente ``AppShell`` em "
            f"{APPSHELL_PATH.relative_to(REPO_ROOT)} NAO contem "
            "nenhum ``<div className={`screen…`}>`` (com template "
            "literal para alternar ``.on``).\n\n"
            "Cada página da app deve ser um ``<div className={`screen${on('…') ? ' on' : ''}`}>`` "
            "dentro do ``<main className=\"main\">``.  A regra CSS "
            "``.screen{display:none}`` + ``.screen.on{display:flex}`` "
            "(em global.css linhas 118-119) é o que esconde/"
            "mostra cada página.\n\n"
            "GREEN deve garantir que cada page seja um:\n"
            "  <div className={`screen${on('home') ? ' on' : ''}`} id=\"s-home\">\n"
            "    …\n  </div>"
        )
