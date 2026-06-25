"""RED test for behavior B-1 — Reestruturar abas do EstrategiaRoom.

GOAL:
    Reestruturar o sistema de abas do EstrategiaRoom para usar a nova
    taxonomia: objetivos | documentos | conhecimento | config.

BEHAVIOR:
    B-1 — Reestruturar abas do EstrategiaRoom — Substituir o sistema de
    4 abas antigas ('decisoes' | 'analises' | 'historico' | 'config') pelo
    novo modelo unificado com 4 abas:
        objetivos | documentos | conhecimento | config

    Antes (RED):
        - type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
        - Labels: Decisões, Análises, Histórico, Config
        - Renderização: {(['decisoes', 'analises', 'historico', 'config']
          as Tab[]).map(...)}
        - Painéis condicionais: tc${tab === 'decisoes' ? ' on' : ''}, etc.

    Depois (GREEN):
        - type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'
        - Labels: Objetivos, Documentos, Conhecimento, Config
        - Renderização: {(['objetivos', 'documentos', 'conhecimento',
          'config'] as Tab[]).map(...)}
        - Painéis condicionais: tc${tab === 'objetivos' ? ' on' : ''}, etc.
        - onClick={() => setTab(t)} mantém navegação.

AC (Acceptance Criteria):
    AC#1 — type Tab define os 4 novos valores:
            'objetivos' | 'documentos' | 'conhecimento' | 'config'.
    AC#2 — Template renderiza 4 abas com labels:
            Objetivos, Documentos, Conhecimento, Config.
    AC#3 — Cada aba tem onClick que chama setTab para navegar.
    AC#4 — Visibilidade dos painéis condicionais usa o padrão
            tc${tab === '<novo-valor>' ? ' on' : ''}.
    AC#5 — Tabs antigas ('decisoes', 'analises', 'historico', 'painel',
            'base') foram completamente removidas do type Tab e do
            array de renderização.

Anti-Goals (must NOT be violated):
    1. NÃO modificar código de produção.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO usar fixtures de DB ou rede — teste é pura inspeção de
       arquivos (source-inspection).
"""

import re
from pathlib import Path

import pytest


# ── Constants: caminhos da interface pública sob teste ──────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ESTRATEGIA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Override do root conftest (teste puramente estático) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção ────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o arquivo e devolve o conteúdo como string única."""
    assert path.exists(), (
        f"Arquivo não encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-1 (Reestruturar abas do EstrategiaRoom) exige "
        f"que este arquivo exista no repositório."
    )
    return path.read_text(encoding="utf-8")


# ── Teste único cobrindo AC#1 a AC#5 ───────────────────────────────────────


def test_b1_ac1_to_ac5_restruturar_abas_estrategiaroom():
    """B-1: Reestruturar abas do EstrategiaRoom — AC#1 a AC#5.

    Este teste cobre simultaneamente as 5 ACs do behavior B-1.  A
    primeira AC violada faz o teste falhar com pytest.fail() em
    pt-BR.  O teste é RED na implementação atual porque o type Tab
    ainda usa os valores antigos ('decisoes' | 'analises' |
    'historico' | 'config') e os labels são Decisões/Análises/
    Histórico/Config.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    rel_path = ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)

    # ── Localiza o type Tab ────────────────────────────────────────────
    tab_match = re.search(
        r"type\s+Tab\s*=\s*([\s\S]*?)(?:;|\n\s*\n)",
        content,
    )
    if not tab_match:
        pytest.fail(
            f"AC#1 violada — RED.  O type Tab NÃO foi encontrado em "
            f"{rel_path}.\n\n"
            f"O behavior B-1 exige que exista 'type Tab = ...' "
            f"definindo os 4 valores: 'objetivos' | 'documentos' | "
            f"'conhecimento' | 'config'.\n\n"
            f"GREEN deve declarar:\n"
            f"  type Tab = 'objetivos' | 'documentos' | "
            f"'conhecimento' | 'config'"
        )
    tab_type_block = tab_match.group(1)

    # ── AC#1: type Tab deve ter os 4 NOVOS valores ─────────────────────
    novos_valores = ["objetivos", "documentos", "conhecimento", "config"]
    for valor in novos_valores:
        if not re.search(rf"['\"]{valor}['\"]", tab_type_block):
            pytest.fail(
                f"AC#1 violada — RED.  O valor '{valor}' NÃO está "
                f"presente no type Tab em {rel_path}.\n\n"
                f"Type Tab atual: {tab_type_block.strip()}\n\n"
                f"Era esperado que type Tab contivesse todos os 4 "
                f"novos valores:\n"
                f"  type Tab = 'objetivos' | 'documentos' | "
                f"'conhecimento' | 'config'\n\n"
                f"GREEN deve substituir:\n"
                f"  - 'decisoes'/'painel' → 'objetivos'\n"
                f"  - 'analises'         → 'documentos'\n"
                f"  - 'historico'/'base' → 'conhecimento'\n"
                f"  - 'config'           → 'config' (mantido)"
            )

    # ── AC#2: labels Objetivos | Documentos | Conhecimento | Config ────
    labels_esperados = ["Objetivos", "Documentos", "Conhecimento", "Config"]
    for label in labels_esperados:
        if f"'{label}'" not in content and f'"{label}"' not in content:
            pytest.fail(
                f"AC#2 violada — RED.  O label '{label}' NÃO foi "
                f"encontrado no template em {rel_path}.\n\n"
                f"Era esperado que as 4 abas renderizassem os labels:\n"
                f"  Objetivos | Documentos | Conhecimento | Config\n\n"
                f"GREEN deve substituir os labels antigos:\n"
                f"  'Decisões'  → 'Objetivos'\n"
                f"  'Análises'  → 'Documentos'\n"
                f"  'Histórico' → 'Conhecimento'\n"
                f"  'Config'    → 'Config'  (mantido)"
            )

    # ── AC#3: onClick que chama setTab para navegar ────────────────────
    onclick_settab = re.search(
        r"onClick\s*=\s*\{\s*\(\s*\)\s*=>\s*setTab\s*\(",
        content,
    )
    if not onclick_settab:
        pytest.fail(
            f"AC#3 violada — RED.  Nenhum handler onClick chamando "
            f"setTab(...) foi encontrado em {rel_path}.\n\n"
            f"Era esperado que cada aba tivesse "
            f"onClick={{() => setTab(t)}} para navegação.\n\n"
            f"GREEN deve manter/atualizar o handler para que o parâmetro "
            f"t seja um dos novos valores: 'objetivos', 'documentos', "
            f"'conhecimento', 'config'."
        )

    # ── AC#4: visibilidade dos painéis via tc$ ─────────────────────────
    # O padrão atual é: <div className={`tc${tab === '<valor>' ? ' on' : ''}`}>
    # Verifica que existe PELO MENOS UM painel condicional usando os
    # NOVOS valores do type Tab.
    tc_novos_valores = re.findall(
        r"tc\$\{tab\s*===\s*['\"](objetivos|documentos|conhecimento|config)['\"]",
        content,
    )
    if not tc_novos_valores:
        pytest.fail(
            f"AC#4 violada — RED.  Nenhum painel condicional "
            f"tc${{tab === '<novo-valor>' ? ' on' : ''}} usando os "
            f"novos valores foi encontrado em {rel_path}.\n\n"
            f"Era esperado que houvesse blocos como:\n"
            f"  <div className={{`tc${{tab === 'objetivos' ? ' on' : ''}}`}}>\n"
            f"  <div className={{`tc${{tab === 'documentos' ? ' on' : ''}}`}}>\n"
            f"  <div className={{`tc${{tab === 'conhecimento' ? ' on' : ''}}`}}>\n"
            f"  <div className={{`tc${{tab === 'config' ? ' on' : ''}}`}}>\n\n"
            f"GREEN deve usar os novos valores do type Tab na "
            f"visibilidade condicional dos painéis."
        )

    # ── AC#5: tabs antigas removidas ───────────────────────────────────
    # Verifica que 'decisoes', 'analises', 'historico', 'painel' e 'base'
    # NÃO aparecem mais como valores no type Tab nem no array de
    # renderização das abas.
    valores_antigos_tab = ["decisoes", "analises", "historico", "painel", "base"]
    for antigo in valores_antigos_tab:
        if re.search(rf"['\"]{antigo}['\"]", tab_type_block):
            pytest.fail(
                f"AC#5 violada — RED.  O valor antigo '{antigo}' AINDA "
                f"está presente no type Tab em {rel_path}.\n\n"
                f"Type Tab atual: {tab_type_block.strip()}\n\n"
                f"Os valores antigos ('decisoes', 'analises', "
                f"'historico', 'painel', 'base') devem ser "
                f"substituídos pelos novos ('objetivos', 'documentos', "
                f"'conhecimento', 'config')."
            )

    # Verifica também que os valores antigos não aparecem no array
    # usado para renderizar as abas (ex: {([...]) as Tab[]).map(...)})
    array_match = re.search(
        r"\[\s*((?:['\"][^'\"]+['\"](?:\s*,\s*)?)+)\s*\]\s*as\s+Tab\s*\[\s*\]",
        content,
    )
    if array_match:
        array_block = array_match.group(1)
        for antigo in valores_antigos_tab:
            if re.search(rf"['\"]{antigo}['\"]", array_block):
                pytest.fail(
                    f"AC#5 violada — RED.  O valor antigo '{antigo}' "
                    f"AINDA está presente no array de renderização "
                    f"das abas em {rel_path}.\n\n"
                    f"Array de tabs atual: {array_block.strip()}\n\n"
                    f"O array de renderização deve usar apenas os novos "
                    f"valores: 'objetivos', 'documentos', 'conhecimento', "
                    f"'config'."
                )

    # Verifica que labels antigos não estão presentes no template
    labels_antigos = ["Decisões", "Análises", "Histórico"]
    for antigo in labels_antigos:
        if f"'{antigo}'" in content or f'"{antigo}"' in content:
            pytest.fail(
                f"AC#5 violada — RED.  O label antigo '{antigo}' AINDA "
                f"está presente no template em {rel_path}.\n\n"
                f"Os labels antigos (Decisões, Análises, Histórico) "
                f"devem ser substituídos pelos novos (Objetivos, "
                f"Documentos, Conhecimento)."
            )
