"""RED test for behavior B1 — pg_cron schedule para sincronizar_csv_cliente.

GOAL:
    Garantir que a migration baseline declara um agendamento do pg_cron
    (``cron.schedule(...)``) cuja ``command`` invoca
    ``public.sincronizar_csv_cliente(...)``, de modo que o ETL de CSV
    dos clientes seja executado periodicamente sem intervenção manual.

BEHAVIOR:
    B1 — pg_cron schedule para sincronizar_csv_cliente.

    A função ``public.sincronizar_csv_cliente(p_job_id uuid)`` é definida
    no baseline (linha ~4284 de
    ``supabase/migrations/20260523999999_baseline_v2.sql``) e processa
    um job de ingestão CSV por vez.  Para que o pipeline rode de forma
    autônoma, ela precisa ser chamada por um job do ``pg_cron`` (ex.:
    ``cron.schedule(jobname, '*/N * * * *', 'SELECT ...')``).

AC (Acceptance Criteria):
    AC#1 — Existe, no baseline, uma chamada ``cron.schedule(...)`` cuja
    ``command`` referencia ``sincronizar_csv_cliente`` (tipicamente
    ``SELECT public.sincronizar_csv_cliente(<uuid candidato>);`` ou
    um ``SELECT`` que varre a tabela de jobs pendentes e delega à
    função).

DECISÃO:
    Estratégia: source_inspection
    Arquivo alvo: supabase/migrations/20260523999999_baseline_v2.sql

Anti-Goals (must NOT be violated):
    1. NÃO criar um novo arquivo de migration — o teste valida o baseline
       existente.  Agendamentos adicionais podem existir em migrations
       ``proposed/``; este behavior é estritamente sobre o baseline.
    2. NÃO exigir que ``sincronizar_csv_cliente`` seja executado em
       produção — o teste é puramente estático (regex sobre o arquivo).
    3. NÃO dependender de Supabase / pg_cron em runtime.

Estado atual: RED — o baseline define ``public.sincronizar_csv_cliente``
(linha 4284) mas NÃO registra nenhum ``cron.schedule(...)`` apontando
para ela.  O teste falha com ``pytest.fail`` em pt-BR até que o baseline
ganhe um agendamento explícito (fase GREEN).
"""

import re
from pathlib import Path

import pytest


# ── Constants: a interface pública sob teste ───────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

TARGET_FUNCTION = "sincronizar_csv_cliente"

# Janela (em caracteres) examinada após cada ``cron.schedule(`` para
# detectar uma referência à função alvo.  1500 chars é folga generosa
# para assinaturas posicional ou nomeada (``command => '...'``).
_CRON_SCHEDULE_WINDOW = 1500


# ── Override do root conftest (teste puramente estático) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    puro I/O de arquivo, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção do SQL ────────────────────────────────────────


def _baseline_text() -> str:
    """Lê o baseline e devolve o conteúdo como string única."""
    assert BASELINE_PATH.exists(), (
        f"Baseline não encontrado em {BASELINE_PATH}. "
        "O behavior B1 exige que este arquivo exista no repositório."
    )
    return BASELINE_PATH.read_text()


def _find_cron_schedule_windows(sql: str) -> list[str]:
    """Devolve a lista de janelas de texto iniciadas em cada
    ``cron.schedule(`` encontrada no SQL (limitadas por
    ``_CRON_SCHEDULE_WINDOW`` caracteres).
    """
    return [
        sql[idx : idx + _CRON_SCHEDULE_WINDOW]
        for idx in range(len(sql))
        if sql.startswith("cron.schedule(", idx)
    ]


# ── O behavior sob teste ──────────────────────────────────────────────


def test_b1_baseline_agenda_sincronizar_csv_cliente_via_pg_cron():
    """AC#1: o baseline deve conter ``cron.schedule(...)`` cuja ``command``
    invoca ``sincronizar_csv_cliente``.

    Falha (RED) enquanto o baseline definir a função mas não registrar
    nenhum agendamento para ela.
    """
    sql = _baseline_text()

    # Pré-condição de sanidade: a função precisa existir no baseline,
    # caso contrário este teste não faria sentido.
    assert re.search(
        rf"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.{TARGET_FUNCTION}",
        sql,
        re.IGNORECASE,
    ), (
        f"Esperava encontrar a definição de public.{TARGET_FUNCTION} "
        f"no baseline {BASELINE_PATH}, mas ela não está lá.  Este "
        "behavior pressupõe que a função já existe."
    )

    cron_windows = _find_cron_schedule_windows(sql)

    # Pelo menos um ``cron.schedule(`` precisa referenciar a função alvo.
    matching = [
        window
        for window in cron_windows
        if TARGET_FUNCTION in window
    ]

    if not matching:
        pytest.fail(
            "AC#1 violado: o baseline "
            f"{BASELINE_PATH.relative_to(REPO_ROOT)} "
            "define public.sincronizar_csv_cliente(...) mas não "
            "registra nenhum cron.schedule(...) cuja 'command' "
            "invoque a função.  O ETL de CSV dos clientes não será "
            "executado periodicamente até que um agendamento do "
            "pg_cron (ex.: "
            "cron.schedule('sincronizar-csv-cliente', '*/N * * * *', "
            f"'SELECT public.{TARGET_FUNCTION}(...)')) seja declarado "
            "no baseline."
        )

    # Guarda extra: a referência deve ser uma chamada (parêntese
    # aberto após o nome), não apenas menção em comentário.
    assert any(
        re.search(rf"\b{TARGET_FUNCTION}\s*\(", window)
        for window in matching
    ), (
        "AC#1 violado: a referência a "
        f"{TARGET_FUNCTION} dentro de um cron.schedule(...) não parece "
        "ser uma chamada de função (esperava '<nome>(').  Janelas "
        f"encontradas: {matching!r}."
    )
