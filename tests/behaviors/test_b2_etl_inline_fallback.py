"""RED test for behavior B2 — ETL Execution: Inline Fallback.

GOAL:
    Garantir que ``supabase/functions/run-csv-etl/index.ts`` contém
    lógica de **fallback inline** que aciona o ETL de CSV
    (``sincronizar_csv_cliente``) imediatamente após criar o registro
    em ``analytics_v2.reg_jobs``, sem depender exclusivamente do
    ``pg_cron`` para iniciar o processamento.

BEHAVIOR:
    B2 — ETL Execution: Inline Fallback.

    O edge function ``run-csv-etl`` (Deno + Supabase) cria uma linha
    em ``analytics_v2.reg_jobs`` com ``status='pending'`` e devolve
    ``job_id`` ao frontend.  Em ambientes onde o ``pg_cron`` esteja
    indisponível, atrasado, com a fila congestionada ou com o
    agendamento ``sincronizar-csv-cliente`` removido por engano, o
    job ficaria preso em ``pending`` por minutos.  O behavior B2
    exige um caminho de **fallback inline** que invoque
    ``public.sincronizar_csv_cliente(p_job_id)`` ainda no contexto
    da request, de modo que o ETL rode imediatamente para o
    cliente que acabou de submeter o CSV.

AC (Acceptance Criteria):
    AC#1 — Após o bloco que insere em ``analytics_v2.reg_jobs`` (o
    insert com ``job_type: 'csv_sync'``), o arquivo ``index.ts``
    deve conter uma chamada inline
    ``svc.rpc("sincronizar_csv_cliente", { p_job_id: ... })`` (ou
    forma equivalente como ``.rpc('sincronizar_csv_cliente', ...)``)
    passando o ``job_id`` recém-criado.

DECISÃO:
    Estratégia: source_inspection (regex sobre o arquivo .ts)
    Arquivo alvo: supabase/functions/run-csv-etl/index.ts

Anti-Goals (must NOT be violated):
    1. NÃO alterar o arquivo ``index.ts`` neste behavior — o teste
       é puramente estático.  A implementação do fallback será
       feita na fase GREEN.
    2. NÃO exigir execução real do ETL ou acesso ao Supabase —
       este behavior valida apenas a presença do ``.rpc(...)`` no
       código-fonte do edge function.
    3. NÃO depender de fixtures de banco de dados — o teste é
       determinístico e roda sem rede.

Estado atual: RED — ``supabase/functions/run-csv-etl/index.ts``
termina o handler em ``return json({ ..., message: "CSV sync job
queued. ETL will start within ~1 minute." })`` (linha ~287) sem
nenhuma chamada ``svc.rpc("sincronizar_csv_cliente", ...)`` após o
insert em ``reg_jobs``.  O teste falha com ``pytest.fail`` em
pt-BR até que o fallback inline seja adicionado (fase GREEN).
"""

import re
from pathlib import Path

import pytest


# ── Constants: a interface pública sob teste ───────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ETL_FUNCTION_PATH = (
    REPO_ROOT
    / "supabase"
    / "functions"
    / "run-csv-etl"
    / "index.ts"
)

TARGET_RPC = "sincronizar_csv_cliente"

# Marcador que delimita o início do bloco do job insert: procuramos
# o fallback inline APÓS este ponto do arquivo.  Usamos uma substring
# estável que aparece no insert real (``job_type: "csv_sync"``)
# combinado com ``status: "pending"`` para reduzir falsos positivos
# (ex.: comentários sobre outros jobs).
JOB_INSERT_MARKER = 'job_type: "csv_sync"'

# Janela (em caracteres) examinada após o ``JOB_INSERT_MARKER`` para
# detectar uma chamada ``.rpc(`` com a função alvo.  4000 chars é
# folga generosa para cobrir o handler inteiro (o arquivo tem ~305
# linhas, ~10k chars), mantendo o teste rápido.
_RPC_SEARCH_WINDOW = 4000


# ── Override do root conftest (teste puramente estático) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    puro I/O de arquivo, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção do TypeScript ─────────────────────────────────


def _etl_source_text() -> str:
    """Lê o edge function e devolve o conteúdo como string única."""
    assert ETL_FUNCTION_PATH.exists(), (
        f"Edge function não encontrada em {ETL_FUNCTION_PATH}. "
        "O behavior B2 exige que este arquivo exista no repositório."
    )
    return ETL_FUNCTION_PATH.read_text()


def _slice_after_job_insert(src: str) -> str:
    """Devolve o trecho do arquivo que vem **depois** do bloco de
    insert em ``reg_jobs`` (delimitado por ``JOB_INSERT_MARKER``),
    limitado a ``_RPC_SEARCH_WINDOW`` caracteres.

    Se o marcador não for encontrado, devolve string vazia —
    cabendo ao teste falhar com mensagem clara.
    """
    idx = src.find(JOB_INSERT_MARKER)
    if idx < 0:
        return ""
    return src[idx : idx + _RPC_SEARCH_WINDOW]


def _has_inline_rpc(window: str) -> bool:
    """Detecta a presença de uma chamada inline
    ``svc.rpc("sincronizar_csv_cliente", { p_job_id: ... })`` (ou
    variantes equivalentes com aspas simples, ``client.rpc``,
    espaços, etc.) dentro da ``window``.

    Aceita tanto ``svc.rpc(...)`` quanto ``.rpc(...)`` desde que
    o **primeiro argumento** da chamada seja o nome da função
    alvo (``sincronizar_csv_cliente``), entre aspas simples ou
    duplas.
    """
    # Forma "canônica": svc.rpc("sincronizar_csv_cliente", { p_job_id: ... })
    # ou client.rpc("sincronizar_csv_cliente", ...)
    pattern_double = re.compile(
        r"\.rpc\(\s*[\"']" + re.escape(TARGET_RPC) + r"[\"']",
        re.IGNORECASE,
    )
    if pattern_double.search(window):
        return True

    # Forma tolerante a whitespace/quebras de linha entre o nome do
    # client (``svc``/``client``/etc.) e o ``.rpc(``:
    pattern_loose = re.compile(
        r"\.rpc\(\s*[\"']" + re.escape(TARGET_RPC) + r"[\"']",
        re.IGNORECASE | re.DOTALL,
    )
    return bool(pattern_loose.search(window))


# ── O behavior sob teste ──────────────────────────────────────────────


def test_b2_ac1_inline_fallback_sem_pg_cron():
    """AC#1: ``run-csv-etl/index.ts`` deve chamar inline
    ``svc.rpc("sincronizar_csv_cliente", { p_job_id: ... })`` (ou
    equivalente) **após** criar o job em ``analytics_v2.reg_jobs``,
    servindo como fallback caso o ``pg_cron`` esteja atrasado,
    indisponível ou sem o agendamento correspondente.

    Falha (RED) enquanto o handler apenas enfileirar o job e
    retornar a mensagem "...ETL will start within ~1 minute."
    """
    src = _etl_source_text()

    # Pré-condição de sanidade: o insert em reg_jobs precisa existir
    # no arquivo, caso contrário este teste não faria sentido (a AC
    # é "APÓS criar o reg_jobs").
    assert JOB_INSERT_MARKER in src, (
        f"Esperava encontrar o marcador de insert de job "
        f"({JOB_INSERT_MARKER!r}) em "
        f"{ETL_FUNCTION_PATH.relative_to(REPO_ROOT)}, mas ele não "
        "está lá.  O behavior B2 pressupõe que o edge function já "
        "cria um reg_jobs com job_type='csv_sync'."
    )

    after_insert = _slice_after_job_insert(src)
    assert after_insert, (
        "Não foi possível fatiar o arquivo após o insert de reg_jobs; "
        "verifique a constante JOB_INSERT_MARKER no teste."
    )

    if not _has_inline_rpc(after_insert):
        pytest.fail(
            "AC#1 violado: o edge function "
            f"{ETL_FUNCTION_PATH.relative_to(REPO_ROOT)} "
            "cria um reg_jobs (job_type='csv_sync') mas NÃO possui "
            "fallback inline.  O handler termina em "
            "'return json({ success: true, ..., message: "
            "\"CSV sync job queued. ETL will start within ~1 minute.\""
            " })' sem chamar svc.rpc(\"sincronizar_csv_cliente\", "
            "{ p_job_id: <job_id> }) no mesmo request.  Em ambientes "
            "onde o pg_cron estiver atrasado, indisponível ou sem o "
            "agendamento 'sincronizar-csv-cliente', o job ficará "
            "preso em status='pending' por minutos.  Implemente o "
            "fallback adicionando — logo após o insert em reg_jobs "
            "e antes do return final — uma chamada inline do tipo "
            "await svc.rpc('sincronizar_csv_cliente', { p_job_id: "
            "job.job_id }); (envolva em try/catch para não quebrar "
            "a request se o RPC falhar — o pg_cron continua sendo "
            "o caminho primário)."
        )
