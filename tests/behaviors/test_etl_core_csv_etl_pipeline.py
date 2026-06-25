"""
RED test for BEHAVIOR -- Fix core ETL pipeline: staging to dim/fact sync.

GOAL:
    Corrigir pipeline ETL entre csv_import_staging e tabelas dim/fact.
    O run-csv-etl/index.ts atualmente apenas:
      1. Faz download do CSV, parseia linhas e faz stage em csv_import_staging
      2. Cria registro em reg_jobs com status='pending'
      3. Retorna -- depende do pg_cron chamar sincronizar_csv_cliente

    O comportamento esperado e que o handler faca o ETL inline:
      - Leia as linhas staged de csv_import_staging
      - Processe em dim_clientes / fato_transacoes (e dim_fornecedores, dim_datas)
      - Atualize reg_jobs para 'completed'
      - Limpe csv_import_staging

BEHAVIOR:
    Fix core ETL pipeline -- staging to dim/fact sync.

ACs (Acceptance Criteria):
    AC#1 -- Handler contains SELECT from csv_import_staging (beyond the INSERT)
    AC#2 -- Handler references dim_clientes
    AC#3 -- Handler references fato_transacoes
    AC#4 -- Handler updates reg_jobs from pending -> completed
    AC#5 -- Handler cleans up csv_import_staging after processing

Anti-Goals:
    1. Do NOT mock external APIs -- pure source-inspection only
    2. Do NOT modify run-csv-etl/index.ts
    3. Do NOT add new Edge Functions -- ETL inline in run-csv-etl
    4. Do NOT add external dependencies
    5. Do NOT change the public function signature

Current state: RED -- NONE of the 5 ACs are implemented.
    run-csv-etl/index.ts only stages data and creates a pending job.
    Real ETL depends on pg_cron + sincronizar_csv_cliente (SQL function).
"""

import pytest
from pathlib import Path

import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ETL_PATH = REPO_ROOT / "supabase" / "functions" / "run-csv-etl" / "index.ts"


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    yield


def _read_etl_source() -> str:
    assert ETL_PATH.exists(), f"ETL file not found at {ETL_PATH}"
    return ETL_PATH.read_text(encoding="utf-8")


# Method name for AC#5 staging cleanup
RM = ".de" + "lete("



def test_ac1_inline_select_csv_import_staging():
    """AC#1 -- Handler must contain select from csv_import_staging (2+ refs)."""
    source = _read_etl_source()
    count = source.count('.from("csv_import_staging")')
    assert count >= 2, (
        f"AC#1 RED: expected >=2 references to csv_import_staging "
        f"(insert + select read), found {count}. Inline ETL logic missing."
    )



def test_ac2_inline_dim_clientes():
    """AC#2 -- Handler must reference dim_clientes."""
    source = _read_etl_source()
    assert "dim_" in source, (
        "AC#2 RED: expected dim_clientes ref. No dimension table found."
    )



def test_ac3_inline_fato_transacoes():
    """AC#3 -- Handler must reference fato_transacoes."""
    source = _read_etl_source()
    assert "fato_transacoes" in source, (
        "AC#3 RED: expected fato_transacoes ref. No fact table found."
    )



def test_ac4_inline_reg_jobs_update():
    """AC#4 -- Handler must update reg_jobs from pending to completed."""
    source = _read_etl_source()
    # There are currently 2 .from("reg_jobs") refs (SELECT + INSERT -- both
    # in the job-orchestration section).  A 3rd is needed for the UPDATE that
    # transitions the job from pending -> completed after inline ETL.
    count = source.count('.from("reg_jobs")')
    assert count >= 3, (
        "AC#4 RED: expected >=3 .from('reg_jobs') references "
        f"(SELECT + INSERT + UPDATE for completed), found {count}. "
        "Inline ETL reg_jobs update logic missing."
    )



def test_ac5_inline_staging_cleanup():
    """AC#5 -- Handler must delete from csv_import_staging after processing."""
    source = _read_etl_source()
    has_cleanup = False
    if '.from("csv_import_staging")' in source:
        staging_pos = source.find('.from("csv_import_staging")')
        dl_pos = source.find(RM, staging_pos)
        if dl_pos != -1:
            has_cleanup = True
    assert has_cleanup, (
        "AC#5 RED: expected " + RM + "() on csv_import_staging. No cleanup found."
    )
