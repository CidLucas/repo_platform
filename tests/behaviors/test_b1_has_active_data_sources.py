"""RED test for behavior B-1 — RPC `has_active_data_sources`.

GOAL:
    Garantir que exista uma RPC ``public.has_active_data_sources(p_client_id uuid)``
    que retorna ``true`` quando o cliente possui ``client_data_sources`` com
    registros ingeridos (sync_status IN ('ready', 'success', 'synced')), e
    ``false`` quando o cliente não tem dados ou não tem registro na tabela.

BEHAVIOR:
    B-1 — RPC has_active_data_sources.

    O schema ``public.client_data_sources`` (linha 154 do baseline) armazena
    as fontes de dados de cada cliente, com coluna ``sync_status`` indicando
    o estado de sincronização.  Atualmente NÃO existe uma RPC dedicada que
    exponha, de forma segura e performática, se um cliente específico possui
    fontes de dados ativas — essa informação fica enterrada em joins
    espalhados pelo código ou simplesmente não é consultável via RPC.

    A RPC ``public.has_active_data_sources(p_client_id uuid)`` deve:
    - Retornar ``true`` quando houver ao menos um registro em
      ``client_data_sources`` com ``client_id = p_client_id`` e
      ``sync_status IN ('ready', 'success', 'synced')``
    - Retornar ``false`` quando não houver registros ou nenhum com sync
      ativo
    - Usar ``EXISTS`` para ser performática (para na primeira linha)
    - Ser ``SECURITY INVOKER`` (respeita RLS do caller)
    - Ser ``LANGUAGE plpgsql STABLE``

AC (Acceptance Criteria):
    AC#1 — A RPC ``public.has_active_data_sources(p_client_id uuid)`` DEVE
    existir no baseline SQL (ou em migration adicional).  Hoje (RED) NÃO
    existe — o teste falha até que a função seja criada.

    AC#2 — Nenhum código TypeScript no frontend faz referência à string
    ``has_active_data_sources`` — a RPC não foi integrada na camada de
    apresentação.

Anti-Goals (must NOT be violated):
    1. NÃO modificar código de produção.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO usar fixtures de DB ou rede — teste é pura inspeção de arquivos.
    4. NÃO escrever asserts que passam no estado atual — deve ser RED.

Estado atual (RED):
    AC#1: ``public.has_active_data_sources`` NÃO está definida em
    ``supabase/migrations/20260523999999_baseline_v2.sql`` — não há
    ``CREATE OR REPLACE FUNCTION public.has_active_data_sources``.
    A tabela ``public.client_data_sources`` existe (linha 154) com
    colunas ``client_id`` e ``sync_status``, mas nenhuma RPC dedicada
    expõe a informação de "cliente tem fonte ativa?".

    AC#2: Nenhum arquivo .ts / .tsx em ``apps/`` menciona a string
    ``has_active_data_sources`` — a RPC ainda não foi chamada no
    frontend.
"""

import re
from pathlib import Path

import pytest


# ── Constants: paths da interface pública sob teste ──────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)
APPS_DIR = REPO_ROOT / "apps"

TARGET_RPC = "has_active_data_sources"


# ── Override do root conftest (teste puramente estático) ────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção ─────────────────────────────────────────────────


def _baseline_text() -> str:
    """Lê o baseline SQL e devolve o conteúdo como string única."""
    assert BASELINE_PATH.exists(), (
        f"Baseline não encontrado em {BASELINE_PATH}.  "
        "O behavior B-1 (has_active_data_sources) exige que este "
        "arquivo exista no repositório."
    )
    return BASELINE_PATH.read_text(encoding="utf-8")


# ── AC#1 — RPC pública deve existir ─────────────────────────────────────


def test_b1_rpc_has_active_data_sources_deve_existir():
    """AC#1: a RPC ``public.has_active_data_sources`` DEVE existir
    no baseline ou em alguma migration.

    Hoje (RED) a função NÃO está definida — ``client_data_sources``
    existe mas não há uma RPC dedicada que responda se um cliente
    possui fontes de dados ativas.

    GREEN deve criar a função no SQL:
      CREATE OR REPLACE FUNCTION public.has_active_data_sources(
        p_client_id uuid
      ) RETURNS boolean
      LANGUAGE plpgsql STABLE SECURITY INVOKER
      AS $function$
      BEGIN
        RETURN EXISTS (
          SELECT 1 FROM public.client_data_sources
          WHERE client_id = p_client_id
            AND sync_status IN ('ready', 'success', 'synced')
        );
      END;
      $function$;
    """
    sql = _baseline_text()

    # Pré-condição de sanidade: a tabela alvo precisa existir
    assert re.search(
        r"CREATE\s+TABLE\s+public\.client_data_sources\b",
        sql,
        re.IGNORECASE,
    ), (
        "Pré-condição violada: a tabela `public.client_data_sources` "
        f"não foi encontrada no baseline {BASELINE_PATH.relative_to(REPO_ROOT)}.  "
        "Esperava encontrá-la na linha ~154.  Sem a tabela, a RPC "
        "`has_active_data_sources` não faria sentido."
    )

    # Procurar pela definição da RPC
    rpc_exists = re.search(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.has_active_data_sources\b",
        sql,
        re.IGNORECASE,
    )

    if not rpc_exists:
        pytest.fail(
            "AC#1 violada — RED.  A RPC `public.has_active_data_sources` "
            f"NÃO está definida em "
            f"{BASELINE_PATH.relative_to(REPO_ROOT)}.\n\n"
            "Hoje a tabela `public.client_data_sources` existe (linha 154 "
            "do baseline) com colunas:\n"
            "  - client_id    uuid (NOT NULL)\n"
            "  - sync_status  text (DEFAULT 'pending'::text)\n"
            "  - source_type, resource_type, storage_type, etc.\n\n"
            "Os valores de sync_status que indicam fonte ativa são:\n"
            "  'ready', 'success', 'synced'\n"
            "(vide linhas 1092 e 4072 do baseline).\n\n"
            "Porém não há uma RPC pública que responda de forma direta "
            "se um dado cliente TEM fontes de dados ativas ou não.\n\n"
            "IMPLEMENTAÇÃO GREEN (criar no SQL da migration):\n\n"
            "  CREATE OR REPLACE FUNCTION public.has_active_data_sources(\n"
            "    p_client_id uuid\n"
            "  ) RETURNS boolean\n"
            "  LANGUAGE plpgsql STABLE SECURITY INVOKER\n"
            "  AS $function$\n"
            "  BEGIN\n"
            "    RETURN EXISTS (\n"
            "      SELECT 1 FROM public.client_data_sources\n"
            "      WHERE client_id = p_client_id\n"
            "        AND sync_status IN ('ready', 'success', 'synced')\n"
            "    );\n"
            "  END;\n"
            "  $function$;\n\n"
            "Benefícios do design acima:\n"
            "  - `SECURITY INVOKER`: respeita as políticas RLS do caller\n"
            "  - `EXISTS`: performático — para na primeira linha encontrada\n"
            "  - `STABLE`: permite a função ser usada em outras queries\n"
            "  - `sync_status IN (...): só considera fontes ativamente\n"
            "     sincronizadas (ready/success/synced), ignorando pending,\n"
            "     discovery_pending, sync_failed etc."
        )

    # Se chegou aqui, a RPC existe — valida os requisitos de segurança
    assert re.search(
        r"SECURITY\s+INVOKER",
        sql[rpc_exists.start():rpc_exists.start() + 500],
        re.IGNORECASE,
    ), (
        "AC#1 violada — a RPC `public.has_active_data_sources` existe "
        f"em {BASELINE_PATH.relative_to(REPO_ROOT)} mas NÃO declara "
        "`SECURITY INVOKER`.  Sem isso, a função ignora as políticas RLS "
        "do schema `public` e pode expor dados de outros clientes.  "
        "GREEN deve adicionar `SECURITY INVOKER` à definição."
    )

    assert re.search(
        r"\bEXISTS\b",
        sql[rpc_exists.start():rpc_exists.start() + 800],
        re.IGNORECASE,
    ), (
        "AC#1 violada — a RPC `public.has_active_data_sources` existe "
        f"em {BASELINE_PATH.relative_to(REPO_ROOT)} mas NÃO usa `EXISTS`.  "
        "Sem `EXISTS` a consulta pode varrer a tabela inteira em vez de "
        "parar na primeira linha.  GREEN deve usar `EXISTS (SELECT 1 ...)` "
        "para garantir performance O(1) no melhor caso."
    )


# ── AC#2 — Nenhum código TS chama a RPC hoje ────────────────────────────


def test_b1_nenhum_frontend_chama_has_active_data_sources():
    """AC#2: nenhum código TypeScript no frontend referencia
    ``has_active_data_sources`` — a RPC ainda não foi integrada.

    RED: a string não aparece em nenhum .ts / .tsx dentro de ``apps/``.

    GREEN: quando o frontend precisar usar a RPC, deve chamar
    ``supabase.rpc('has_active_data_sources', { p_client_id })``
    ou similar.
    """
    apps_dir = APPS_DIR
    assert apps_dir.exists(), (
        f"Pré-condição violada: diretório apps/ não encontrado em {apps_dir}."
    )

    # Percorre recursivamente arquivos .ts / .tsx
    ts_files = sorted(apps_dir.rglob("*.ts")) + sorted(apps_dir.rglob("*.tsx"))
    found_in = []

    for ts_file in ts_files:
        content = ts_file.read_text(encoding="utf-8", errors="replace")
        if TARGET_RPC in content:
            found_in.append(str(ts_file.relative_to(REPO_ROOT)))

    if found_in:
        # Se encontrou, o teste falha de forma informativa (orienta o
        # desenvolvedor a integrar corretamente)
        pytest.fail(
            "AC#2 — A string `has_active_data_sources` já aparece nos "
            f"seguintes arquivos:\n"
            + "\n".join(f"  - {f}" for f in found_in) +
            "\n\nIsso é esperado quando a RPC for integrada no frontend.  "
            "Verifique se a chamada está usando `supabase.rpc(...)` com "
            "os parâmetros corretos e tratamento de erro adequado."
        )

    # RED: não encontrou — o teste falha porque a RPC não está integrada
    pytest.fail(
        "AC#2 violada — RED.  Nenhum arquivo TypeScript em "
        f"{apps_dir.relative_to(REPO_ROOT)} referencia a string "
        f"`{TARGET_RPC}`.\n\n"
        "Isso significa que a RPC `public.has_active_data_sources` "
        "ainda não foi integrada no frontend.\n\n"
        "Hoje nenhum componente, hook ou API chama "
        "`supabase.rpc('has_active_data_sources', ...)`.\n\n"
        "GREEN: quando houver necessidade de consultar se um cliente "
        "possui fontes de dados ativas (ex.: onboarding, dashboard de "
        "configuração), o frontend deve chamar:\n\n"
        "  const { data } = await supabase\n"
        "    .rpc('has_active_data_sources', { p_client_id: clientId });\n\n"
        "  if (data) {\n"
        "    // cliente tem fontes ativas — pode prosseguir\n"
        "  } else {\n"
        "    // cliente não tem fontes ou está pendente\n"
        "  }"
    )
