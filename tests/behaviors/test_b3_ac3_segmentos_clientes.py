"""RED test for behavior B-3 AC#3 — Segmentos de clientes populados.

GOAL:
    Garantir que a função ``public.sincronizar_csv_cliente`` (baseline)
    popula as colunas de segmentação ``nivel_cluster`` e
    ``pontuacao_cluster`` em ``analytics_v2.dim_clientes``, de modo
    que a RPC ``get_customer_segments`` (baseline linha ~2296)
    retorne segmentos distintos (não apenas 'Indefinido').

BEHAVIOR:
    B-3 — AC#3: Segmentos de clientes são populados.

AC (Acceptance Criteria):
    AC#3 — O INSERT INTO ``analytics_v2.dim_clientes`` dentro de
    ``sincronizar_csv_cliente`` deve popular (ou o ETL deve computar
    posteriormente) as colunas ``nivel_cluster`` e/ou
    ``pontuacao_cluster``, para que a RPC ``get_customer_segments``
    possa agrupar clientes em segmentos distintos.

DECISÃO:
    Estratégia: source_inspection (regex sobre o .sql)
    Arquivo alvo: supabase/migrations/20260523999999_baseline_v2.sql

Estado atual (TRUE RED):
    O ``INSERT INTO analytics_v2.dim_clientes`` no baseline
    (linha ~4425) popula apenas: client_id, cpf_cnpj, nome, telefone,
    endereco_cidade, endereco_uf, atualizado_em.
    NÃO popula: nivel_cluster, pontuacao_cluster.
    Como resultado, a RPC ``get_customer_segments`` (linha ~2296)
    agrupa todos os clientes como 'Indefinido' (COALESCE NULL),
    e a "Caixa de Segmentos" não é populada (BKL-029).

Anti-Goals:
    1. NÃO modificar arquivos de produção.
    2. NÃO exigir execução real do Supabase.
    3. NÃO depender de fixtures de banco de dados.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

TARGET_FUNCTION = "sincronizar_csv_cliente"

# Colunas de segmentação que deveriam ser populadas
SEGMENT_COLUMNS = ("nivel_cluster", "pontuacao_cluster")


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    yield


def _baseline_text() -> str:
    assert BASELINE_PATH.exists(), (
        f"Baseline não encontrado em {BASELINE_PATH}."
    )
    return BASELINE_PATH.read_text()


def _slice_function_body(sql: str, function_name: str) -> str:
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\."
        + re.escape(function_name)
        + r"\s*\([^)]*\).*?\$function\$\s*(.*?)\s*\$function\$\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)
    return match.group(1) if match else ""


def _extract_insert_into_dim_clientes(function_body: str) -> str:
    """Extrai o bloco INSERT INTO analytics_v2.dim_clientes (...)
    ate o ponto-e-virgula que o encerra."""
    pattern = re.compile(
        r"INSERT\s+INTO\s+analytics_v2\.dim_clientes\s*\([^)]*\)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(function_body)
    return match.group(0) if match else ""


def _get_rpc_get_customer_segments(sql: str) -> str:
    """Extrai o corpo da RPC get_customer_segments."""
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.get_customer_segments"
        r".*?\$function\$\s*(.*?)\s*\$function\$\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)
    return match.group(1) if match else ""


def test_b3_ac3_segmentos_clientes_populados():
    """AC#3: O INSERT em dim_clientes deve popular nivel_cluster e
    pontuacao_cluster, OU deve existir lógica ETL pós-insert que
    compute estes campos.

    Falha (RED) se:
      - O INSERT atual não lista nivel_cluster nem pontuacao_cluster
      - E não há UPDATE posterior no mesmo corpo que compute clusters
    """
    sql = _baseline_text()

    # ── (1) Verifica o INSERT em dim_clientes ──────────────────────
    function_body = _slice_function_body(sql, TARGET_FUNCTION)
    assert function_body, (
        f"Função public.{TARGET_FUNCTION} não encontrada no baseline."
    )

    insert_clause = _extract_insert_into_dim_clientes(function_body)
    assert insert_clause, (
        f"Não foi encontrado INSERT INTO analytics_v2.dim_clientes "
        f"no corpo de public.{TARGET_FUNCTION}."
    )

    # ── (2) Verifica colunas de segmentação no INSERT ──────────────
    present_in_insert = [
        col for col in SEGMENT_COLUMNS
        if re.search(rf"\b{re.escape(col)}\b", insert_clause, re.IGNORECASE)
    ]

    # ── (3) Verifica se há UPDATE posterior que compute clusters ──
    # Procura por UPDATE analytics_v2.dim_clientes SET nivel_cluster
    # ou UPDATE SET pontuacao_cluster no corpo da função
    has_update_cluster = bool(
        re.search(
            r"UPDATE\s+analytics_v2\.dim_clientes\s+SET\s+.*\bnivel_cluster\b",
            function_body,
            re.IGNORECASE | re.DOTALL,
        )
    )

    # Também verifica se get_customer_segments tem lógica de
    # segmentação (RFM, cluster, etc.) que depende de dados da
    # dimensão — se a RPC espera que o ETL compute clusters,
    # mas o ETL nunca os computa, o problema persiste.
    rpc_segments = _get_rpc_get_customer_segments(sql)
    # A RPC faz GROUP BY nivel_cluster. Se nivel_cluster nunca é
    # populado, tudo cai em 'Indefinido'.
    has_rfm_or_cluster_logic = bool(
        re.search(
            r"\b(SELECT|INSERT|UPDATE).*nivel_cluster\b",
            function_body,
            re.IGNORECASE | re.DOTALL,
        )
    )

    # ── (4) Decisão ───────────────────────────────────────────────

    if not present_in_insert and not has_update_cluster and not has_rfm_or_cluster_logic:
        pytest.fail(
            "AC#3 violado: o INSERT INTO analytics_v2.dim_clientes "
            f"em public.{TARGET_FUNCTION} (baseline "
            f"{BASELINE_PATH.relative_to(REPO_ROOT)}) NÃO popula "
            "as colunas de segmentação "
            f"{SEGMENT_COLUMNS[0]} / {SEGMENT_COLUMNS[1]}.\n\n"
            "Colunas atualmente populadas no INSERT:\n"
            f"  {insert_clause}\n\n"
            "Além disso, não há UPDATE posterior no corpo da função "
            "que compute clusters, nem lógica de segmentação (RFM, "
            "recência, frequência) que alimente nivel_cluster.\n\n"
            "Consequência direta: a RPC get_customer_segments "
            "(linha ~2296) faz:\n"
            "  GROUP BY COALESCE(dc.nivel_cluster, 'Indefinido')\n"
            "  → TODOS os clientes caem no segmento 'Indefinido'\n"
            "  → Caixa de Segmentos nunca é populada (BKL-029)\n\n"
            "Correção sugerida (GREEN):\n"
            "  1. Adicionar lógica de segmentação no ETL:\n"
            "     - Computar recência (dias desde última compra)\n"
            "     - Computar frequência (total_pedidos, "
            "frequencia_mensal)\n"
            "     - Classificar em clusters: 'Alto Valor', "
            "'Recorrente', 'Novo', 'Em Risco', 'Inativo' etc.\n"
            "  2. Populando nivel_cluster e pontuacao_cluster no "
            "INSERT ou via UPDATE após o loop.\n\n"
            "Ou, como alternativa mais curta:\n"
            "  3. Adicionar coluna de segmento default no INSERT "
            "(ex.: nivel_cluster = 'Indefinido' é o default "
            "implícito via NULL) mas garantir que a lógica de "
            "cluster seja executada EM ALGUM PONTO do pipeline."
        )

    elif not present_in_insert and not has_update_cluster:
        # Tem lógica de cluster em algum lugar (RPC ou outro local)
        # mas ainda não no INSERT — fallback mais suave
        pytest.fail(
            "AC#3 parcialmente violado: o INSERT em dim_clientes "
            f"em public.{TARGET_FUNCTION} não popula "
            f"{SEGMENT_COLUMNS[0]}/{SEGMENT_COLUMNS[1]} diretamente. "
            "Embora exista lógica de cluster em outro ponto, "
            "a população inicial já deveria incluir estes campos "
            "para que get_customer_segments funcione corretamente."
        )
