"""RED test for behavior B-3 AC#5 — Upsert dim_clientes sem cpf_cnpj.

GOAL:
    Garantir que a função ``public.sincronizar_csv_cliente(p_job_id uuid)``
    (definida em ``supabase/migrations/20260523999999_baseline_v2.sql``)
    trata corretamente clientes **sem** ``cpf_cnpj`` (clientes anónimos)
    no UPSERT em ``analytics_v2.dim_clientes``, evitando duplicatas.

BEHAVIOR:
    B-3 — AC#5: dim_clientes upsert com e sem cpf_cnpj.

    A função ``sincronizar_csv_cliente`` faz upsert em
    ``analytics_v2.dim_clientes`` com:
      ON CONFLICT (client_id, cpf_cnpj) WHERE cpf_cnpj IS NOT NULL
      DO UPDATE SET ...

    A cláusula ``WHERE cpf_cnpj IS NOT NULL`` faz com que o ``ON CONFLICT``
    **não se aplique** quando ``cpf_cnpj`` é NULL.  Para estas linhas
    (clientes anónimos identificados apenas pelo nome), cada execução
    gera um NOVO registro, criando duplicatas na dimensão.

    O código de busca pós-insert (linha ~4439-4446) tem uma tentativa
    de fallback:
      OR (v_cliente_cpf_cnpj IS NULL AND nome = v_cliente_nome)
    Mas sem uma constraint UNIQUE (client_id, nome) ou um segundo
    ``ON CONFLICT (client_id, nome)``, o fallback não previne que
    múltiplas linhas com o mesmo nome e sem cpf_cnpj sejam inseridas.

AC (Acceptance Criteria):
    AC#5 — A função ``sincronizar_csv_cliente`` deve ter lógica que
    previne duplicatas em ``analytics_v2.dim_clientes`` para clientes
    **sem** ``cpf_cnpj``.  Pode ser:
      - ``ON CONFLICT (client_id, nome) DO UPDATE SET`` (segundo
        conflito para anonymous), ou
      - ``ON CONFLICT (client_id, COALESCE(cpf_cnpj, nome))`` usando
        índice funcional, ou
      - Uma constraint ``UNIQUE (client_id, nome)`` na tabela
        ``dim_clientes`` com tratamento de NULL, ou
      - Merge lógico explícito (SELECT + UPDATE/INSERT) que evite
        duplicatas por nome quando cpf_cnpj é NULL.

DECISÃO:
    Estratégia: source_inspection (regex sobre o arquivo .sql)
    Arquivo alvo: supabase/migrations/20260523999999_baseline_v2.sql

Anti-Goals (must NOT be violated):
    1. NÃO modificar arquivos de produção — teste puramente estático.
    2. NÃO exigir execução real do ETL ou acesso ao Supabase.
    3. NÃO depender de fixtures de banco de dados.
    4. NÃO mockar nada.

Estado atual: TRUE RED — o baseline (linha ~4431) usa:
    ON CONFLICT (client_id, cpf_cnpj) WHERE cpf_cnpj IS NOT NULL
  Esta cláusula NÃO se aplica a clientes anónimos (cpf_cnpj IS NULL),
  e não há segundo mecanismo de conflito ou constraint para evitar
  duplicatas nestes casos.
"""

import re
from pathlib import Path

import pytest


# ── Constants ───────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

TARGET_FUNCTION = "sincronizar_csv_cliente"


# ── Override do root conftest ──────────────────────────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    puro I/O de arquivo, sem necessidade de teardown no Supabase."""
    yield


# ── Helpers de inspeção do SQL ────────────────────────────────────────


def _baseline_text() -> str:
    """Lê o baseline e devolve o conteúdo como string única."""
    assert BASELINE_PATH.exists(), (
        f"Baseline não encontrado em {BASELINE_PATH}. "
        "O behavior B-3 AC#5 exige que este arquivo exista."
    )
    return BASELINE_PATH.read_text()


def _slice_function_body(sql: str, function_name: str) -> str:
    """Devolve o corpo da função ``public.<function_name>(...)`` no
    baseline (entre os marcadores ``$function$``), ou string vazia."""
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\."
        + re.escape(function_name)
        + r"\s*\([^)]*\).*?\$function\$\s*(.*?)\s*\$function\$\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)
    if not match:
        return ""
    return match.group(1)


def _extract_insert_block(function_body: str) -> str:
    """Devolve o bloco INSERT INTO analytics_v2.dim_clientes ... ON
    CONFLICT ... encontrado no function_body (até o próximo ';' que
    encerra o statement composto), ou string vazia."""
    pattern = re.compile(
        r"INSERT\s+INTO\s+analytics_v2\.dim_clientes\b[^;]*;",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(function_body)
    if not match:
        return ""
    return match.group(0)


# ── O behavior sob teste ──────────────────────────────────────────────


def test_b3_ac5_upsert_dim_clientes_sem_cpf_cnpj():
    """AC#5: o upsert em dim_clientes deve tratar clientes sem cpf_cnpj
    (anónimos), evitando duplicatas quando o nome é o mesmo.

    Falha (RED) enquanto o único ON CONFLICT for restrito a
    ``cpf_cnpj IS NOT NULL`` e não houver segundo mecanismo de
    unicidade para clientes anónimos.
    """
    sql = _baseline_text()
    function_body = _slice_function_body(sql, TARGET_FUNCTION)

    assert function_body, (
        f"Esperava encontrar a definição de public.{TARGET_FUNCTION} "
        f"(delimitada por $function$ ... $function$;) no baseline "
        f"{BASELINE_PATH}, mas ela não está lá."
    )

    insert_block = _extract_insert_block(function_body)
    assert insert_block, (
        f"Não foi encontrado INSERT INTO analytics_v2.dim_clientes "
        f"no corpo de public.{TARGET_FUNCTION}.  O behavior B-3 AC#5 "
        "pressupõe que este INSERT existe."
    )

    # ── (1) Verifica se o UNICO ON CONFLICT existente usa
    #     WHERE cpf_cnpj IS NOT NULL — o que EXCLUI clientes anónimos.

    conflict_cpfcnpj_not_null = re.search(
        r"ON\s+CONFLICT\s*\(\s*client_id\s*,\s*cpf_cnpj\s*\)"
        r"\s*WHERE\s+cpf_cnpj\s+IS\s+NOT\s+NULL",
        insert_block,
        re.IGNORECASE,
    )

    # ── (2) Verifica se existe ALGUM mecanismo alternativo para
    #     anónimos: ON CONFLICT (client_id, nome),
    #     ON CONFLICT (client_id, COALESCE(cpf_cnpj, nome)),
    #     ou UNIQUE (client_id, nome) mencionado.

    conflict_by_name = re.search(
        r"ON\s+CONFLICT\s*\(\s*client_id\s*,\s*nome\s*\)",
        insert_block,
        re.IGNORECASE,
    )
    conflict_by_coalesce = re.search(
        r"ON\s+CONFLICT\s*\([^)]*COALESCE\s*\([^)]*cpf_cnpj[^)]*nome[^)]*\)",
        insert_block,
        re.IGNORECASE,
    )
    unique_client_name = re.search(
        r"UNIQUE\s*\(\s*client_id\s*,\s*nome\s*\)",
        sql,  # escopo maior: pode estar na definição da tabela
        re.IGNORECASE,
    )

    has_anonymous_protection = bool(
        conflict_by_name or conflict_by_coalesce or unique_client_name
    )

    # ── (3) Lógica de decisão ──────────────────────────────────────

    if conflict_cpfcnpj_not_null and not has_anonymous_protection:
        pytest.fail(
            "AC#5 violado: a função "
            f"public.{TARGET_FUNCTION} (baseline "
            f"{BASELINE_PATH.relative_to(REPO_ROOT)}) usa "
            "'ON CONFLICT (client_id, cpf_cnpj) WHERE cpf_cnpj "
            "IS NOT NULL' como ÚNICA proteção contra duplicatas "
            "em analytics_v2.dim_clientes.\n\n"
            "Isso significa que clientes identificados APENAS pelo "
            "nome (cpf_cnpj IS NULL) — clientes anónimos ou "
            "pessoas físicas sem CPF no CSV — NÃO são cobertos "
            "pela cláusula de conflito.  Cada re-upload do mesmo "
            "CSV (ou linhas com nomes repetidos sem CPF) cria uma "
            "NOVA linha em dim_clientes, gerando duplicatas.\n\n"
            "Consequências observáveis:\n"
            "  - get_commercial_top_clients retorna R$ 0 ou valores "
            "incorretos porque o JOIN ft.customer_id = dc.customer_id "
            "encontra múltiplas linhas para o mesmo cliente anónimo\n"
            "  - Indicadores de clientes únicos (clientes_unicos, "
            "clientes_novos, clientes_recorrentes) inflam "
            "artificialmente\n"
            "  - Segmentos (get_customer_segments) mostram contagens "
            "distorcidas\n\n"
            "Para corrigir (fase GREEN), implemente um dos seguintes "
            "mecanismos:\n"
            "  A) Adicionar um segundo ON CONFLICT:\n"
            "       INSERT INTO analytics_v2.dim_clientes (...) "
            "VALUES (...)\n"
            "       ON CONFLICT (client_id, cpf_cnpj) "
            "WHERE cpf_cnpj IS NOT NULL DO UPDATE SET ...;\n"
            "     -- Fallback para anónimos:\n"
            "     INSERT INTO analytics_v2.dim_clientes (...) "
            "VALUES (...)\n"
            "     ON CONFLICT (client_id, nome) "
            "WHERE cpf_cnpj IS NULL DO UPDATE SET ...;\n"
            "  B) Migração que adiciona UNIQUE (client_id, nome) "
            "à dim_clientes (se clinicamente aceitável para o "
            "domínio)\n"
            "  C) Merge lógico: SELECT → se existir por nome, "
            "UPDATE; senão INSERT (em vez de INSERT com ON CONFLICT)"
        )

    elif not conflict_cpfcnpj_not_null and not has_anonymous_protection:
        pytest.fail(
            "AC#5 violado: o 'INSERT INTO analytics_v2.dim_clientes' "
            "em public.{TARGET_FUNCTION} NÃO possui NENHUMA cláusula "
            "ON CONFLICT ou mecanismo de unicidade.  Sem proteção "
            "contra duplicatas, cada execução gera novas linhas em "
            "dim_clientes para todos os clientes, independentemente "
            "de terem ou não cpf_cnpj."
        )
