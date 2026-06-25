"""RED test for behavior B-5 — Abas Conhecimento + Config unificada.

GOAL:
    Adicionar aba "Conhecimento" à EstrategiaRoom e unificar a aba Config
    para incluir RoutineConfigSection tanto para "documentos" quanto para
    "estrategia", com estado independente por domínio.

BEHAVIOR:
    B-5 — Abas Conhecimento + Config (BibliotecaRoom + RoutineConfig unificada).

    After the fix:
    - A nova aba "Conhecimento" importa e renderiza <BibliotecaRoom />.
    - A aba "Config" inclui <RoutineConfigSection domain="documentos" /> E
      <RoutineConfigSection domain="estrategia" />, com estado de config
      independente para cada domínio.

AC (Acceptance Criteria):
    AC#1 — Conhecimento tab importa e renderiza <BibliotecaRoom />.
    AC#2 — Config tab exibe <RoutineConfigSection> para AMBOS os domínios
           (documentos E estrategia).
    AC#3 — Estado de config para cada domínio é independente (variáveis/
           setups distintos por domain).

Estado atual (antes da correção):
    O componente EstrategiaRoom.tsx tem 4 abas:
    'decisoes', 'analises', 'historico', 'config'
    (labels: "Decisões", "Análises", "Histórico", "Config")
    com <RoutineConfigSection domain="estrategia" /> e SEM BibliotecaRoom.
"""

import pathlib
import re

import pytest


# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

_ESTRATEGIA_ROOM_PATH = _APP_SRC / "pages" / "app" / "EstrategiaRoom.tsx"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Tests -----------------------------------------------------------


class TestB5ConhecimentoConfig:
    """B-5: Abas Conhecimento + Config unificada (BibliotecaRoom + RoutineConfig)."""

    # -----------------------------------------------------------------
    # AC#1 — Conhecimento tab importa e renderiza <BibliotecaRoom />
    #   Esse teste é RED no código atual: EstrategiaRoom.tsx não importa
    #   BibliotecaRoom nem renderiza <BibliotecaRoom> em JSX.
    # -----------------------------------------------------------------

    def test_bibliotecaroom_e_importada_ou_referenciada(self):
        """AC#1: 'BibliotecaRoom' deve aparecer no fonte (import ou referência)."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        if "BibliotecaRoom" not in source:
            pytest.fail(
                "AC#1 violado: O identificador 'BibliotecaRoom' não foi "
                "encontrado em EstrategiaRoom.tsx. A aba 'Conhecimento' "
                "precisa importar o componente BibliotecaRoom e/ou "
                "renderizá-lo no JSX."
            )

    def test_bibliotecaroom_e_renderizada_no_jsx(self):
        """AC#1: '<BibliotecaRoom' deve aparecer no JSX (tag de uso)."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        if "<BibliotecaRoom" not in source:
            pytest.fail(
                "AC#1 violado: A tag '<BibliotecaRoom' não foi encontrada "
                "no JSX de EstrategiaRoom.tsx. A aba 'Conhecimento' deve "
                "renderizar o componente BibliotecaRoom como conteúdo da aba."
            )

    def test_bibliotecaroom_ac1_completo(self):
        """AC#1 (consolidado): tanto o identificador quanto a tag JSX
        devem estar presentes; falha detalhada se qualquer um faltar."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        has_identifier = "BibliotecaRoom" in source
        has_jsx_tag = "<BibliotecaRoom" in source

        if not (has_identifier and has_jsx_tag):
            missing = []
            if not has_identifier:
                missing.append(
                    "identificador 'BibliotecaRoom' (esperado em import)"
                )
            if not has_jsx_tag:
                missing.append(
                    "tag JSX '<BibliotecaRoom' (esperado na aba Conhecimento)"
                )
            pytest.fail(
                "AC#1 violado: faltando em EstrategiaRoom.tsx -> "
                + "; ".join(missing)
                + ". A aba 'Conhecimento' deve importar BibliotecaRoom "
                "e renderizar <BibliotecaRoom /> dentro do bloco da aba."
            )

    # -----------------------------------------------------------------
    # AC#2 — Config tab exibe <RoutineConfigSection> para AMBOS os
    #         domínios: documentos E estrategia.
    #   Esse teste é RED no código atual: só há
    #   <RoutineConfigSection domain="estrategia" />.
    # -----------------------------------------------------------------

    def test_possui_routineconfigsection_para_documentos(self):
        """AC#2: 'domain="documentos"' deve aparecer em EstrategiaRoom.tsx."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        if 'domain="documentos"' not in source:
            pytest.fail(
                "AC#2 violado: 'domain=\"documentos\"' não foi encontrado "
                "em EstrategiaRoom.tsx. A aba Config deve incluir "
                "<RoutineConfigSection domain=\"documentos\" /> para que "
                "rotinas do domínio de documentos sejam configuráveis."
            )

    def test_possui_routineconfigsection_para_estrategia(self):
        """AC#2: 'domain="estrategia"' deve aparecer em EstrategiaRoom.tsx."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        if 'domain="estrategia"' not in source:
            pytest.fail(
                "AC#2 violado: 'domain=\"estrategia\"' não foi encontrado "
                "em EstrategiaRoom.tsx. A aba Config deve manter "
                "<RoutineConfigSection domain=\"estrategia\" /> para que "
                "rotinas do domínio de estratégia continuem configuráveis."
            )

    def test_total_routineconfig_section_eh_maior_ou_igual_a_2(self):
        """AC#2: devem existir >= 2 ocorrências de 'RoutineConfigSection'
        no fonte (uma por domínio)."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        occurrences = len(re.findall(r"RoutineConfigSection", source))
        if occurrences < 2:
            pytest.fail(
                f"AC#2 violado: foram encontradas {occurrences} ocorrências "
                f"de 'RoutineConfigSection' em EstrategiaRoom.tsx, mas o "
                f"mínimo esperado é 2 (uma para domain=\"documentos\" e "
                f"outra para domain=\"estrategia\"). A aba Config precisa "
                f"ser unificada para cobrir ambos os domínios."
            )

    def test_ac2_config_cobre_ambos_dominios(self):
        """AC#2 (consolidado): ambos os domínios devem estar cobertos na aba
        Config; falha detalhada se qualquer um faltar."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        has_documentos = 'domain="documentos"' in source
        has_estrategia = 'domain="estrategia"' in source
        occurrences = len(re.findall(r"RoutineConfigSection", source))

        if not (has_documentos and has_estrategia and occurrences >= 2):
            missing = []
            if not has_documentos:
                missing.append('domain="documentos"')
            if not has_estrategia:
                missing.append('domain="estrategia"')
            if occurrences < 2:
                missing.append(
                    f"pelo menos 2 ocorrências de 'RoutineConfigSection' "
                    f"(encontradas: {occurrences})"
                )
            pytest.fail(
                "AC#2 violado: a aba Config de EstrategiaRoom.tsx não está "
                "unificada. Faltando: " + "; ".join(missing) + "."
            )

    # -----------------------------------------------------------------
    # AC#3 — Estado de config para cada domínio é independente
    #   Esse teste é RED no código atual: existe um único setup de
    #   estado de config (apenas para 'estrategia'). Precisamos ver
    #   setups distintos / variáveis por domínio.
    # -----------------------------------------------------------------

    def test_estado_config_domain_especifico_para_documentos(self):
        """AC#3: deve haver setup/uso de estado de config específico
        para o domínio 'documentos' (variável ou referência distinta)."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        # Procura por padrões como: configDocumentos, configDocs,
        # useState(..., 'documentos'), ou referências a 'documentos'
        # no contexto de config.
        patterns_documentos = [
            r"config[A-Za-z]*[Dd]ocumentos",
            r"[Cc]onfig.*['\"]documentos['\"]",
            r"['\"]documentos['\"].*[Cc]onfig",
            r"[Cc]onfigDocumentos",
        ]
        has_doc_state = any(
            re.search(p, source) is not None for p in patterns_documentos
        )

        if not has_doc_state:
            pytest.fail(
                "AC#3 violado: não foi encontrado estado de config "
                "específico para o domínio 'documentos' em "
                "EstrategiaRoom.tsx. O estado de config precisa ser "
                "independente por domínio (ex.: variável de estado "
                "separada para 'documentos' vs 'estrategia')."
            )

    def test_estado_config_independente_por_dominio(self):
        """AC#3 (consolidado): deve haver pelo menos 2 referências
        distintas a domínios no contexto de config — comprovando
        independência de estado entre documentos e estrategia."""
        source = _read(_ESTRATEGIA_ROOM_PATH)

        # Conta referências distintas a domínios em contexto de config
        doc_refs = len(re.findall(r"['\"]documentos['\"]", source))
        est_refs = len(re.findall(r"['\"]estrategia['\"]", source))

        # Pelo menos 2 referências a domínios no contexto de config
        # (uma para documentos e outra para estrategia).
        if doc_refs < 1 or est_refs < 1:
            missing = []
            if doc_refs < 1:
                missing.append("nenhuma referência a 'documentos'")
            if est_refs < 1:
                missing.append("nenhuma referência a 'estrategia'")
            pytest.fail(
                "AC#3 violado: estado de config não parece ser "
                "independente por domínio em EstrategiaRoom.tsx. "
                "Faltando: " + "; ".join(missing) + "."
            )

        # Verifica que as referências aparecem em blocos distintos
        # (setup de useState/setConfig/setState com nomes diferentes).
        # Procura padrões de variáveis distintas associadas a cada domínio.
        config_var_patterns = [
            r"config[A-Z]?[A-Za-z]*\s*=\s*useState",
            r"setConfig[A-Z]?[A-Za-z]*",
            r"const\s+\[config",
        ]
        has_distinct_setup = any(
            re.search(p, source) is not None for p in config_var_patterns
        )

        if not has_distinct_setup:
            pytest.fail(
                "AC#3 violado: não foi possível identificar setups de "
                "estado distintos para config por domínio em "
                "EstrategiaRoom.tsx. Cada domínio (documentos, estrategia) "
                "deve ter sua própria variável de estado de config "
                "(ex.: configDocumentos vs configEstrategia, ou dois "
                "useState/setConfig separados)."
            )
