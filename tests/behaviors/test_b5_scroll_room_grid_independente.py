"""RED test for behavior B-5 — Scroll independente da area central
(room-grid) em relacao a sidebar (rcol) e room header (rh).

GOAL:
    O layout do blu_v3 tem tres regioes verticais dentro da area de
    conteudo de cada ``.screen`` (Home, Financeiro, Estrategia, etc.):

        ┌──────────────────── .screen (overflow:hidden) ────────────────────┐
        │ ┌── .rh (room header) ─────────────────────────────────────────┐ │
        │ │  flex-shrink:0  →  NAO cresce, NAO rola                     │ │
        │ ├──────────────────────────────────────────────────────────────┤ │
        │ │ ┌── .home-grid / .room-grid (wrapper) ─────────────────────┐ │ │
        │ │ │   ATUAL: overflow:hidden  →  PROBLEMA                   │ │ │
        │ │ │   ALVO:  overflow-y:auto  →  scroll interno              │ │ │
        │ │ │  ┌── coluna 1 (lcol / bstrip) ──┐  ┌── .rcol (col 2) ──┐│ │ │
        │ │ │  │  conteudo principal         │  │  overflow-y:auto   ││ │ │
        │ │ │  │                             │  │  (scroll INDEP.)   ││ │ │
        │ │ │  └────────────────────────────┘  └────────────────────┘│ │ │
        │ │ └─────────────────────────────────────────────────────────┘ │ │
        │ └──────────────────────────────────────────────────────────────┘ │
        └────────────────────────────────────────────────────────────────────┘

    Cada ``.panel`` dentro do grid tem um ``.pb`` (panel body) com
    ``overflow-y: auto`` para scroll INTERNO do painel.

    O problema e' o wrapper ``.room-grid`` (linha 123): ele tem
    ``overflow: hidden`` e impede que o CONJUNTO da area central
    (``lcol`` + ``rcol``) faca scroll quando o conteudo de
    ``lcol`` (listas grandes, varios paineis) ultrapassa a altura
    disponivel.  Como o wrapper nao rola, o conteudo extra
    "empurra" o grid, esticando o ``.screen`` alem do 100vh — a
    pagina inteira comeca a rolar no window, arrastando a
    sidebar (``rcol``) e o room header (``rh``) junto.

    **Correcao:** trocar ``overflow: hidden`` por ``overflow-y:
    auto`` na regra ``.home-grid,.room-grid{...}`` (linha 123),
    mantendo o resto da cadeia de scroll intacta:
    - ``.screen{overflow:hidden}`` (linha 118) — continua sem
      scroll de pagina.
    - ``.rcol{overflow-y:auto}`` (linha 198) — sidebar JA rola
      independentemente.
    - ``.rh{flex-shrink:0}`` (linha 312) — header JA fica fixo.
    - ``.pb{overflow-y:auto}`` (linha 136) — corpo do painel JA
      rola internamente.
    - ``@media(max-width:768px) .home-grid,.room-grid{overflow:visible}``
      (linha 920) — em mobile o grid e' single-column e NAO
      deve bloquear scroll da pagina.

BEHAVIOR:
    B-5 — Scroll independente da area central: a regra
    ``.home-grid,.room-grid{...}`` em ``global.css`` deve ter
    ``overflow-y: auto`` (em vez de ``overflow: hidden``) para
    que a coluna esquerda (``lcol``) faca scroll interno sem
    arrastar a sidebar (``rcol``) nem o room header (``rh``).

    **Estado atual (RED em AC#1, GREEN nos demais):**
    - ``.home-grid,.room-grid{...;overflow:hidden;}`` (linha 123)
      — NAO tem ``overflow-y: auto``.  RED.
    - ``.rcol{...;overflow-y:auto;...}`` (linha 198) — OK.
    - ``.rh{...;flex-shrink:0;}`` (linha 312) — OK.
    - ``.pb{...;overflow-y:auto;...}`` (linha 136) — OK.
    - ``.screen{...;overflow:hidden;}`` (linha 118) — OK.
    - Em ``@media(max-width:768px)`` (linha 910+), a regra
      ``.home-grid,.room-grid{...;overflow:visible;}`` (linha 920)
      — OK.

    **Estado alvo (GREEN em todos os ACs):**
    - ``.home-grid,.room-grid{flex:1;min-height:0;display:grid;
       grid-template-columns:1fr var(--rcol-w);
       grid-template-rows:1fr 120px;gap:20px;padding:18px;
       overflow-y:auto;}``  (overflow:hidden → overflow-y:auto).

AC (Acceptance Criteria):
    AC#1 (RED) — ``.room-grid{...}`` em ``global.css`` (parte da regra
                  composta ``.home-grid,.room-grid``) DEVE conter
                  ``overflow-y: auto``.  Atualmente tem
                  ``overflow: hidden`` (linha 123) — RED.
    AC#2 (GREEN) — ``.rcol{...}`` em ``global.css`` JA contem
                  ``overflow-y: auto`` (linha 198) — sidebar rola
                  independentemente.
    AC#3 (GREEN) — ``.rh{...}`` em ``global.css`` JA contem
                  ``flex-shrink: 0`` (linha 312) — header NAO
                  encolhe/rola.
    AC#4 (GREEN) — ``.pb{...}`` em ``global.css`` JA contem
                  ``overflow-y: auto`` (linha 136) — corpo de
                  cada painel rola internamente.
    AC#5 (GREEN) — ``.screen{...}`` em ``global.css`` JA contem
                  ``overflow: hidden`` (linha 118) — o screen
                  NAO rola como um todo (o scroll fica nos
                  filhos .room-grid / .rcol / .pb).
    AC#6 (GREEN) — Dentro de ``@media(max-width:768px)`` (linha
                  910+), a regra ``.home-grid,.room-grid{...}``
                  (linha 920) JA contem ``overflow: visible`` —
                  em mobile o grid e' single-column e NAO deve
                  bloquear scroll da pagina.

DECISAO:
    Estrategia: source_inspection (regex sobre o CSS).
    Arquivo alvo:
      - apps/blu_v3/src/styles/global.css

Anti-Goals (must NOT be violated):
    1. NAO modificar codigo de producao — o teste e' puramente
       estatico.  A implementacao da feature sera' feita na fase
       GREEN.
    2. NAO importar ou executar codigo TypeScript/React — o teste
       apenas le' o CSS como texto e usa regex.
    3. NAO usar fixtures de DB ou rede — o teste e' deterministico
       e roda sem rede.
    4. NAO exigir mudancas em .rcol, .rh, .pb, .screen ou na media
       query — apenas a regra ``.home-grid,.room-grid`` precisa
       da troca ``overflow:hidden`` → ``overflow-y:auto``.  Os
       outros ja estao OK.
    5. NAO exigir mudancas estruturais no JSX do room — o teste
       verifica APENAS a propriedade CSS.
"""

import re
from pathlib import Path

import pytest


# ── Constants: paths da interface publica sob teste ──────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

GLOBAL_CSS_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "styles"
    / "global.css"
)


# ── Override do root conftest (teste puramente estatico) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e'
    pura inspecao de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspecao ────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Le' o arquivo e devolve o conteudo como string unica."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-5 (scroll independente do .room-grid) "
        f"exige que este arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


def _get_css_block(css_content: str, selector: str) -> str:
    """Devolve o body da PRIMEIRA regra CSS cujo seletor bate
    com ``selector`` (ex.: ``.room-grid``).  Retorna ``""`` se
    nenhuma regra for encontrada.  O body e' tudo entre ``{`` e
    o proximo ``}`` no mesmo nivel.

    ATENCAO: o seletor ``.room-grid`` aparece dentro de uma regra
    composta (``.home-grid,.room-grid{...}``).  Este helper faz
    match na posicao do seletor (mesmo que precedido por virgula
    + outro seletor), e captura o body da regra.  Resultado: a
    string retornada e' o conteudo da regra composta, o que e'
    exatamente o que os ACs precisam verificar.
    """
    escaped = re.escape(selector)
    match = re.search(
        rf"{escaped}\s*\{{([^}}]*)\}}",
        css_content,
    )
    if match is None:
        return ""
    return match.group(1)


def _get_media_query_block(css_content: str, media_query: str) -> str:
    """Devolve o body do PRIMEIRO bloco ``@media (media_query) { ... }``
    encontrado no CSS.  Retorna ``""`` se nenhum bloco for encontrado.

    Usado por AC#6 para localizar a regra ``.home-grid,.room-grid``
    DENTRO da media query ``@media(max-width:768px)``, sem confundir
    com a regra base de mesmo nome (linha 123, desktop).
    """
    escaped_mq = re.escape(media_query)
    match = re.search(
        rf"@media\s*\(\s*{escaped_mq}\s*\)\s*\{{(.*?)\n\}}",
        css_content,
        re.DOTALL,
    )
    if match is None:
        return ""
    return match.group(1)


# ── AC#1 (RED) — .room-grid tem overflow-y:auto ────────────────────


def test_b5_ac1_room_grid_overflow_y_auto():
    """AC#1: A regra CSS ``.home-grid,.room-grid{...}`` em
    ``global.css`` (linha 123) DEVE conter a propriedade
    ``overflow-y: auto`` para que a area central (coluna
    esquerda do room) faca scroll interno independente da
    sidebar (``.rcol``) e do room header (``.rh``).

    Antes (RED): ``global.css`` linha 123 tem
        ``.home-grid,.room-grid{flex:1;min-height:0;display:grid;
        grid-template-columns:1fr var(--rcol-w);
        grid-template-rows:1fr 120px;gap:20px;padding:18px;
        overflow:hidden;}``
    O wrapper tem ``overflow: hidden``, o que IMPEDE scroll
    interno do grid.  Quando a coluna esquerda (``lcol``) tem
    conteudo longo (muitos paineis, listas grandes, tabelas),
    ela NAO rola dentro do grid — em vez disso, o grid e'
    empurrado alem da altura disponivel, o ``.screen`` (que tem
    ``overflow:hidden``) corta o conteudo, OU o conteudo vaza
    para fora do ``.screen`` esticando a pagina inteira (window
    scroll).  Em ambos os casos, a sidebar (``rcol``) e o room
    header (``rh``) sao arrastados junto.

    Depois (GREEN): ``.home-grid,.room-grid{...;overflow-y:auto;}``
    — o grid passa a rolar verticalmente, e ``lcol``/``rcol``/
    ``rh`` mantem suas posicoes relativas (sidebar e header
    fixos no topo, apenas a area central rola).
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".room-grid")
    assert block, (
        f"Pre-condicao violada: regra contendo ``.room-grid{{...}}`` "
        f"nao encontrada em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}.  "
        f"O behavior B-5 espera a regra composta "
        f"``.home-grid,.room-grid{{...}}`` (linha 123)."
    )

    if not re.search(r"overflow-y\s*:\s*auto\b", block):
        pytest.fail(
            "AC#1 violada — RED.  A regra "
            "``.home-grid,.room-grid{...}`` (que define "
            "``.room-grid``) em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            "``overflow-y: auto``.\n\n"
            f"Regra atual: ``.home-grid,.room-grid{{{block}}}``\n\n"
            "O behavior B-5 (scroll independente do .room-grid) "
            "exige que o wrapper ``.room-grid`` da area central "
            "tenha ``overflow-y: auto`` para que o conteudo da "
            "coluna esquerda (``lcol`` — varios paineis, listas "
            "longas) faca scroll INTERNO sem arrastar a sidebar "
            "(``.rcol``) nem o room header (``.rh``).\n\n"
            "Por que isto importa: a regra atual tem "
            "``overflow: hidden``, o que BLOQUEIA qualquer scroll "
            "do wrapper.  Como o ``.screen`` (linha 118) tambem "
            "tem ``overflow: hidden``, o conteudo que nao cabe e' "
            "cortado silenciosamente OU, pior, vaza para fora do "
            "``.screen`` e estica a pagina inteira (window scroll) "
            "— arrastando a sidebar e o room header junto.  O "
            "resultado e' a experiencia classica de 'a pagina "
            "inteira rola em vez da area central'.\n\n"
            "GREEN deve alterar a regra para:\n"
            "  .home-grid,.room-grid{flex:1;min-height:0;\n"
            "    display:grid;grid-template-columns:1fr var(--rcol-w);\n"
            "    grid-template-rows:1fr 120px;gap:20px;padding:18px;\n"
            "    overflow-y:auto;}   ←  overflow:hidden → overflow-y:auto\n\n"
            "ATENCAO: o teste verifica especificamente a PRESENCA de "
            "``overflow-y: auto`` dentro do bloco "
            "``.home-grid,.room-grid{...}``.  Apenas remover o "
            "``overflow: hidden`` NAO satisfaz este AC — a "
            "propriedade ``overflow-y: auto`` deve ser adicionada "
            "explicitamente.  A media query de mobile (linha 920) "
            "permanece inalterada com ``overflow: visible`` (veja "
            "AC#6)."
        )


# ── AC#2 (GREEN) — .rcol tem overflow-y:auto ──────────────────────


def test_b5_ac2_rcol_overflow_y_auto():
    """AC#2: A regra CSS ``.rcol{...}`` em ``global.css`` (linha 198)
    JA contem ``overflow-y: auto`` — verificacao de que a coluna
    direita (sidebar do room) JA rola independentemente.

    Estado atual (GREEN): ``global.css`` linha 198 tem
        ``.rcol{grid-column:2;grid-row:1;display:flex;flex-direction:
        column;gap:9px;min-height:0;overflow-y:auto;position:relative;}``
    ja contem ``overflow-y: auto``.  O teste passa enquanto isso
    for verdade.  Se a propriedade for removida acidentalmente
    durante o fix do AC#1, este teste falha, sinalizando uma
    regressao na sidebar.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".rcol")
    assert block, (
        f"Pre-condicao violada: regra ``.rcol{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"overflow-y\s*:\s*auto\b", block):
        pytest.fail(
            "AC#2 violada.  A regra ``.rcol{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``overflow-y: auto``.\n\n"
            f"Regra atual: ``.rcol{{{block}}}``\n\n"
            "O behavior B-5 (scroll independente do .room-grid) "
            "EXIGE que ``.rcol`` (coluna direita / sidebar do room) "
            "tenha ``overflow-y: auto`` para fazer scroll interno "
            "independente.  Sem isso, o conteudo de ``.rcol`` "
            "(cards de Agenda, KPIs, atalhos) esticaria o "
            "``grid-template-rows: 1fr 120px`` do .room-grid e o "
            "conteudo seria cortado.\n\n"
            "GREEN deve adicionar (ou restaurar) ``overflow-y: auto`` "
            "na regra ``.rcol{...}``.  NAO mexa nesta regra durante "
            "o fix do AC#1 — ela JA esta correta."
        )


# ── AC#3 (GREEN) — .rh tem flex-shrink:0 ──────────────────────────


def test_b5_ac3_rh_flex_shrink_zero():
    """AC#3: A regra CSS ``.rh{...}`` em ``global.css`` (linha 312)
    JA contem ``flex-shrink: 0`` — verificacao de que o room
    header (titulo + botoes da pagina atual) JA fica fixo no
    topo do ``.screen`` e NAO e' arrastado quando o .room-grid
    rola (depois do fix do AC#1).

    Estado atual (GREEN): ``global.css`` linha 312 tem
        ``.rh{display:flex;align-items:center;gap:11px;padding:11px
        14px 10px;border-bottom:1px solid var(--gb);background:
        rgba(5,7,14,.45);backdrop-filter:blur(16px);flex-shrink:0;}``
    ja contem ``flex-shrink: 0``.  O teste passa enquanto isso
    for verdade.  Se a propriedade for removida acidentalmente
    durante o fix do AC#1, este teste falha, sinalizando que o
    header vai encolher/rolar junto com a area central.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".rh")
    assert block, (
        f"Pre-condicao violada: regra ``.rh{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"flex-shrink\s*:\s*0\b", block):
        pytest.fail(
            "AC#3 violada.  A regra ``.rh{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``flex-shrink: 0``.\n\n"
            f"Regra atual: ``.rh{{{block}}}``\n\n"
            "O behavior B-5 (scroll independente do .room-grid) "
            "EXIGE que ``.rh`` (room header — titulo + botoes de "
            "acao da pagina atual) tenha ``flex-shrink: 0`` para "
            "ficar FIXO no topo do ``.screen``.  Sem isso, quando o "
            "``.room-grid`` (depois do fix do AC#1) comecar a "
            "rolar, o header sera' encolhido pelo flex layout e "
            "parte dele desaparecera' da tela.\n\n"
            "GREEN deve adicionar (ou restaurar) ``flex-shrink: 0`` "
            "na regra ``.rh{...}``.  NAO mexa nesta regra durante "
            "o fix do AC#1 — ela JA esta correta."
        )


# ── AC#4 (GREEN) — .pb tem overflow-y:auto ────────────────────────


def test_b5_ac4_pb_overflow_y_auto():
    """AC#4: A regra CSS ``.pb{...}`` em ``global.css`` (linha 136)
    JA contem ``overflow-y: auto`` — verificacao de que o corpo
    de cada ``.panel`` (``.pb`` = panel body) JA permite scroll
    INTERNO ao painel.  Isso e' o que faz listas/tabelas dentro
    de um unico painel rolarem sem esticar o painel em si.

    Estado atual (GREEN): ``global.css`` linha 136 tem
        ``.pb{flex:1;overflow-y:auto;min-height:0;}``
    ja contem ``overflow-y: auto``.  O teste passa enquanto isso
    for verdade.  Se a propriedade for removida acidentalmente
    durante o fix do AC#1, este teste falha, sinalizando que o
    scroll interno de cada painel quebrou.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".pb")
    assert block, (
        f"Pre-condicao violada: regra ``.pb{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"overflow-y\s*:\s*auto\b", block):
        pytest.fail(
            "AC#4 violada.  A regra ``.pb{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``overflow-y: auto``.\n\n"
            f"Regra atual: ``.pb{{{block}}}``\n\n"
            "O behavior B-5 (scroll independente do .room-grid) "
            "EXIGE que ``.pb`` (panel body — area de conteudo de "
            "cada ``.panel``) tenha ``overflow-y: auto`` para fazer "
            "scroll INTERNO ao painel.  Sem isso, listas e tabelas "
            "dentro de um unico painel (ex.: lista de transacoes "
            "no FinanceiroRoom) esticariam o painel ate' forcar o "
            "``.room-grid`` (ou o ``.screen``) a crescer.\n\n"
            "GREEN deve adicionar (ou restaurar) ``overflow-y: auto`` "
            "na regra ``.pb{...}``.  NAO mexa nesta regra durante "
            "o fix do AC#1 — ela JA esta correta."
        )


# ── AC#5 (GREEN) — .screen tem overflow:hidden ─────────────────────


def test_b5_ac5_screen_overflow_hidden():
    """AC#5: A regra CSS ``.screen{...}`` em ``global.css`` (linha 118)
    JA contem ``overflow: hidden`` — verificacao de que o
    container ``.screen`` (cada pagina: Home, Financeiro,
    Estrategia, etc.) NAO rola como um todo.  O scroll e'
    delegado aos filhos ``.room-grid`` (AC#1) / ``.rcol`` (AC#2) /
    ``.pb`` (AC#4).

    Estado atual (GREEN): ``global.css`` linha 118 tem
        ``.screen{display:none;height:100%;flex-direction:column;
        overflow:hidden;}``
    ja contem ``overflow: hidden``.  O teste passa enquanto isso
    for verdade.  Se a propriedade for trocada por ``auto``
    acidentalmente, o scroll do ``.screen`` competiria com o
    scroll do ``.room-grid`` e a UX quebraria.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    block = _get_css_block(css_content, ".screen")
    assert block, (
        f"Pre-condicao violada: regra ``.screen{{...}}`` nao encontrada "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}."
    )

    if not re.search(r"overflow\s*:\s*hidden\b", block):
        pytest.fail(
            "AC#5 violada.  A regra ``.screen{...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``overflow: hidden``.\n\n"
            f"Regra atual: ``.screen{{{block}}}``\n\n"
            "O behavior B-5 (scroll independente do .room-grid) "
            "EXIGE que ``.screen`` (cada pagina do app) mantenha "
            "``overflow: hidden`` para que o scroll seja DELEGADO "
            "aos filhos ``.room-grid`` / ``.rcol`` / ``.pb``, e NAO "
            "compita com eles no nivel do ``.screen``.\n\n"
            "Se ``.screen`` tiver ``overflow: auto`` (ou visivel), "
            "o scroll da pagina inteira passaria a ser possivel "
            "no nivel do .screen — competindo com o scroll do "
            "``.room-grid`` (apos o fix do AC#1) e fazendo a "
            "sidebar (``.rcol``) e o header (``.rh``) "
            "desaparecerem da tela quando o usuario rola para "
            "baixo.\n\n"
            "GREEN deve GARANTIR que a regra ``.screen{...}`` "
            "contenha ``overflow: hidden`` (junto com ``height:100%`` "
            "e ``flex-direction:column``).  NAO mexa nesta regra "
            "durante o fix do AC#1 — ela JA esta correta."
        )


# ── AC#6 (GREEN) — media query .home-grid,.room-grid tem overflow:visible ──


def test_b5_ac6_media_query_room_grid_overflow_visible():
    """AC#6: Dentro do bloco ``@media(max-width:768px){...}`` em
    ``global.css`` (linha 910+), a regra
    ``.home-grid,.room-grid{...}`` (linha 920) JA contem
    ``overflow: visible`` — verificacao de que em MOBILE o grid
    e' single-column e NAO bloqueia o scroll da pagina inteira.

    Em desktop, o ``.room-grid`` tem 2 colunas (``grid-template-
    columns:1fr var(--rcol-w)``) e precisa de ``overflow-y:auto``
    (AC#1) para scroll interno.  Em mobile (max-width:768px), o
    grid e' forcado a single-column (``grid-template-columns:1fr``)
    e o conteudo empilhado precisa ser scrollavel ATE' o final da
    pagina.  Por isso a media query usa ``overflow:visible``
    (junto com ``height:auto`` e ``grid-auto-rows:auto``) — senao
    o scroll da pagina em mobile quebraria.

    Estado atual (GREEN): ``global.css`` linha 920 tem
        ``.home-grid,.room-grid{grid-template-columns:1fr;grid-
        template-rows:none;grid-auto-rows:auto;height:auto;
        overflow:visible;}``
    ja contem ``overflow: visible``.  O teste passa enquanto isso
    for verdade.  Se a propriedade for trocada acidentalmente
    durante o fix do AC#1, o scroll em mobile quebraria.
    """
    css_content = _read_text(GLOBAL_CSS_PATH)

    # 1) Localizar o bloco @media(max-width:768px){...}
    mq_body = _get_media_query_block(css_content, "max-width:768px")
    assert mq_body, (
        f"Pre-condicao violada: bloco ``@media(max-width:768px){{...}}`` "
        f"nao encontrado em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}.  "
        f"O behavior B-5 espera esta media query para a versao mobile "
        f"do .home-grid/.room-grid."
    )

    # 2) Dentro do bloco da media query, localizar a regra
    #    ``.home-grid,.room-grid{...}``.
    inner_match = re.search(
        r"\.home-grid\s*,\s*\.room-grid\s*\{([^}]*)\}",
        mq_body,
    )
    assert inner_match, (
        f"Pre-condicao violada: regra ``.home-grid,.room-grid{{...}}`` "
        f"nao encontrada DENTRO do bloco ``@media(max-width:768px){{...}}`` "
        f"em {GLOBAL_CSS_PATH.relative_to(REPO_ROOT)}.  "
        f"Esperada na linha 920."
    )

    block = inner_match.group(1)

    if not re.search(r"overflow\s*:\s*visible\b", block):
        pytest.fail(
            "AC#6 violada.  A regra ``.home-grid,.room-grid{...}`` "
            "DENTRO de ``@media(max-width:768px){...}`` em "
            f"{GLOBAL_CSS_PATH.relative_to(REPO_ROOT)} NAO contem "
            f"``overflow: visible``.\n\n"
            f"Regra atual: ``.home-grid,.room-grid{{{block}}}``\n\n"
            "O behavior B-5 (scroll independente do .room-grid) "
            "EXIGE que em mobile (max-width:768px) o grid tenha "
            "``overflow: visible`` (junto com ``height:auto`` e "
            "``grid-auto-rows:auto``) para que o conteudo "
            "single-column empilhado seja scrollavel ATE' o final "
            "da pagina.\n\n"
            "Se a media query usar ``overflow: hidden`` ou "
            "``overflow-y: auto``, o conteudo de mobile sera' "
            "cortado (porque o .screen acima tem ``overflow:"
            "hidden`` tambem, vide AC#5) e o usuario nao podera' "
            "ver os paineis inferiores (Calendario, Lista de "
            "tarefas, etc.).\n\n"
            "GREEN deve GARANTIR que a regra dentro da media query "
            "contenha ``overflow: visible``.  NAO mexa nesta regra "
            "durante o fix do AC#1 — ela JA esta correta.  O fix "
            "do AC#1 afeta APENAS a regra base de "
            "``.home-grid,.room-grid`` (linha 123), nao a versao "
            "de media query (linha 920)."
        )
