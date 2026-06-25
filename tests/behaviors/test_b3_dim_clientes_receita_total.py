"""RED test for behavior B-3 — dim_clientes.receita_total populated by CSV ETL.

GOAL:
    AC#2 (B-3) — Após o ETL inline de ``run-csv-etl``, cada registro de
    ``dim_clientes`` deve ter o campo ``receita_total`` preenchido com a
    soma (``SUM(valor)``) de ``fato_transacoes`` agregada por cliente.
    Sem isso, ``dim_clientes`` não reflete a receita gerada por cada
    cliente, e qualquer query analítica (ranking, ticket médio,
    segmentação RFM) que dependa de ``receita_total`` retorna valor
    zerado ou NULL.

BEHAVIOR:
    B-3 — O upsert de ``dim_clientes`` em
    ``supabase/functions/run-csv-etl/index.ts`` deve incluir
    ``receita_total`` (calculado como ``SUM(valor)`` de
    ``fato_transacoes`` agrupado por cliente) além dos campos
    identificadores/endereço já mapeados
    (``client_id``, ``cpf_cnpj``, ``nome``, ``telefone``,
    ``endereco_cidade``, ``endereco_uf``).

    No estado atual (RED), o bloco de upsert de ``dim_clientes`` em
    ``index.ts`` mapeia apenas:
        - client_id
        - cpf_cnpj
        - nome
        - telefone
        - endereco_cidade
        - endereco_uf
    e NÃO inclui ``receita_total``. Isso significa que mesmo após o
    ETL rodar, ``dim_clientes.receita_total`` permanece em seu valor
    default (``0`` ou ``NULL``), tornando a tabela inútil para qualquer
    agregação financeira por cliente.

    Após a correção (GREEN), o handler deve popular
    ``dim_clientes.receita_total`` (e demais campos derivados) durante
    o upsert — por exemplo, agregando ``SUM(fato_transacoes.valor)``
    por ``client_id`` + ``cpf_cnpj`` e adicionando a coluna
    ``receita_total`` ao ``INSERT ... ON CONFLICT DO UPDATE`` ou ao
    payload enviado ao RPC ``sincronizar_csv_cliente``.

AC (Acceptance Criteria):
    AC#2 — ``supabase/functions/run-csv-etl/index.ts`` contém a string
           ``receita_total`` no contexto do upsert (ou do payload
           enviado a ``sincronizar_csv_cliente``) que materializa
           ``dim_clientes`` a partir de ``csv_import_staging`` e
           ``fato_transacoes``.

Anti-Goals (must NOT be violated):
    1. NÃO introduzir mocks de DB ou rede — o teste é puramente
       ``source-inspection`` sobre o texto de
       ``supabase/functions/run-csv-etl/index.ts``.
    2. NÃO alterar a assinatura HTTP pública do ``run-csv-etl`` —
       apenas enriquecer o payload do upsert de ``dim_clientes``.
    3. NÃO introduzir nova dependência no Edge Function — a agregação
       pode ser feita via SQL (``SUM(valor) GROUP BY client_id,
       cpf_cnpj``) ou via pós-processamento em memória do retorno do
       RPC, mas a string ``receita_total`` precisa estar literalmente
       presente no arquivo.

Estado atual: RED — o arquivo
``supabase/functions/run-csv-etl/index.ts`` não contém a string
``receita_total`` em nenhum lugar. O teste falha com ``AssertionError``
na forma pt-BR abaixo até que a fase GREEN adicione o campo
``receita_total`` ao bloco de upsert (ou ao payload enviado ao RPC
``sincronizar_csv_cliente``) que materializa ``dim_clientes``.
"""

from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ETL_PATH = REPO_ROOT / "supabase" / "functions" / "run-csv-etl" / "index.ts"


# ── Override root conftest cleanup (pure source-inspection test) ────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é pura inspeção de código, sem DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_etl_source() -> str:
    """Lê o conteúdo de ``supabase/functions/run-csv-etl/index.ts``.

    Falha imediatamente se o arquivo não existir — o teste só faz
    sentido se o Edge Function ``run-csv-etl`` estiver presente no
    repositório.
    """
    assert ETL_PATH.exists(), f"Arquivo do ETL não encontrado: {ETL_PATH}"
    return ETL_PATH.read_text(encoding="utf-8")


# ── Testes (AC#2) ────────────────────────────────────────────────────────


def test_b3_ac2_dim_clientes_has_receita_total():
    """AC#2 — ``supabase/functions/run-csv-etl/index.ts`` deve
    referenciar ``receita_total`` no bloco que materializa
    ``dim_clientes`` (upsert ou payload do RPC).

    No estado atual (RED) o arquivo não contém a string
    ``receita_total`` em lugar nenhum — o upsert de ``dim_clientes``
    mapeia apenas ``client_id``, ``cpf_cnpj``, ``nome``, ``telefone``,
    ``endereco_cidade`` e ``endereco_uf``, deixando a coluna
    ``receita_total`` da tabela com o valor default (``0``/``NULL``).
    Sem esse campo, qualquer query analítica que dependa de
    ``dim_clientes.receita_total`` (ranking de clientes, ticket médio,
    segmentação RFM, curvas ABC) retorna zerado e a tabela perde a
    função de ``fato por cliente``.

    A correção (GREEN) deve introduzir a string ``receita_total`` no
    arquivo — tipicamente dentro do bloco ``INSERT INTO
    analytics_v2.dim_clientes`` (como nova coluna no ``ON CONFLICT DO
    UPDATE``) ou como parte do payload enviado a
    ``svc.rpc('sincronizar_csv_cliente', ...)`` — garantindo que a
    agregação ``SUM(valor) GROUP BY client_id, cpf_cnpj`` seja
    materializada em ``dim_clientes`` ao final do ETL.
    """
    source = _read_etl_source()

    has_receita_total = "receita_total" in source

    assert has_receita_total, (
        "AC#2 violado — RED. O arquivo "
        "supabase/functions/run-csv-etl/index.ts NÃO contém "
        "'receita_total' no bloco de upsert de dim_clientes. "
        "Atualmente o dimClientesRows mapeia apenas: client_id, "
        "cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf — "
        "sem receita_total. A implementação GREEN deve adicionar "
        "receita_total = SUM(valor) agregado de fato_transacoes por "
        "cliente no upsert de dim_clientes. Sem receita_total, "
        "dim_clientes não reflete a receita gerada por cada cliente. "
        f"Arquivo inspecionado: {ETL_PATH}"
    )
