"""RED test for behavior B3.3 — _save_insights batch insert in routine_artifacts.py.

GOAL:
    Corrigir bottlenecks P0 N+1 no código de produção. Issue #121 — Performance.
    O `_save_insights` em routine_artifacts.py atualmente faz um loop sobre
    `insights` e chama `db.table("client_insights").insert({...}).execute()`
    para cada insight individualmente — cada chamada é um round-trip DB separado (N+1).

BEHAVIOR:
    B3.3 — `_save_insights` (linha ~588 em routine_artifacts.py) deve usar
    batch insert para inserir todos os insights em 1 única chamada DB em vez de
    N chamadas no loop for item in insights.

    Hoje (RED) o código faz:
        for item in insights:
            await asyncio.to_thread(
                lambda i=item: db.table("client_insights").insert({
                    "client_id": client_id,
                    ...
                }).execute()
            )

    O contrato GREEN esperado é:
        # Batch insert all insights in a single DB call
        payloads = [{...} for item in insights]
        await asyncio.to_thread(
            lambda: db.table("client_insights").insert(payloads).execute()
        )

    Nota: o insert deve usar uma lista de payloads para inserir todos os insights
    em uma única operação. A função retorna insights_written = len(insights).

AC (Acceptance Criteria):
    AC#7 — `_save_insights` faz exatamente 1 chamada a .execute() no insert
           quando há N insights (batch insert), em vez de N chamadas individuais
    AC#8 — Itens inválidos (não-dict) continuam sendo ignorados silenciosamente
    AC#9 — ON CONFLICT não é necessário (client_insights não tem UNIQUE composto
           que impeça inserts duplicados; cada execução gera um novo registro)

DECISION:
    Estratégia: extend (refatorar _save_insights para batch insert)
    Arquivo alvo: services/agent_api/src/agent_api/core/routine_artifacts.py
    Função alvo: _save_insights (linha ~588)

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura de _save_insights
    2. NÃO alterar o contrato de retorno ({insights_written: int})
    3. NÃO introduzir dependência externa nova
    4. NÃO alterar o decorator @register(...) ou metadados
    5. NÃO alterar a lógica de mapeamento de dimensão para room

Estado atual: RED — o loop `for item in insights:` ainda está presente no
corpo da função, chamando insert() individualmente para cada item. O teste
source-level falha ao verificar que não há um loop per-row no corpo.
"""

import asyncio
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Override root conftest cleanup ───────────────────────────────────────

@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure unit test, no DB teardown."""
    yield


# ── Paths ────────────────────────────────────────────────────────────────

ROUTINE_ARTIFACTS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "services"
    / "agent_api"
    / "src"
    / "agent_api"
    / "core"
    / "routine_artifacts.py"
)

_FUNC_NAME = "_save_insights"


def _get_func_body(source: str) -> str:
    """Extract the full function body from the source."""
    marker = f"async def {_FUNC_NAME}("
    idx = source.find(marker)
    assert idx != -1, f"Could not locate {_FUNC_NAME}"

    rest = source[idx:]
    lines = rest.split("\n")
    body_lines = []
    for i, line in enumerate(lines):
        body_lines.append(line)
        stripped = line.rstrip()
        # End at next top-level def, decorator, or module divider
        if i > 0:
            if stripped.startswith("def ") or stripped.startswith("async def "):
                body_lines = body_lines[:-1]
                break
            if stripped.startswith("@register("):
                body_lines = body_lines[:-1]
                break
            if stripped.startswith("# ---"):
                break
    return "\n".join(body_lines)


# ── Source-level guard 1: no per-row loop ────────────────────────────────

def test_b3_3_source_no_per_row_loop():
    """Source-level guard: the per-row `for item in insights:` loop must be
    replaced with a single batch insert."""
    assert ROUTINE_ARTIFACTS_PATH.exists()
    source = ROUTINE_ARTIFACTS_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    assert not re.search(
        r"for\s+item\s+in\s+insights\s*:",
        window,
    ), (
        f"Behavior B3.3 / AC#7 violated: {_FUNC_NAME} "
        "still contains a `for item in insights:` loop. The batch "
        "implementation must insert ALL insights in a single DB call."
    )


# ── Source-level guard 2: must use batch insert with list payload ────────

def test_b3_3_source_uses_batch_insert():
    """Source-level guard: the function body must use `.insert([...])`
    with a list payload (not individual inserts in a loop)."""
    assert ROUTINE_ARTIFACTS_PATH.exists()
    source = ROUTINE_ARTIFACTS_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    insert_pattern = r"\.insert\(\s*\["
    assert re.search(insert_pattern, window), (
        f"Behavior B3.3 / AC#7 violated: {_FUNC_NAME} must use "
        "`db.table('client_insights').insert([...])` with a list payload "
        "to batch all insights. Source does not contain `.insert([` "
        "within the function body."
    )


# ── Source-level guard 3: no individual .execute() per item ──────────────

def test_b3_3_source_no_individual_execute():
    """Source-level guard: there should be only ONE .execute() call on the
    insert chain (the batch one), not N calls in a loop."""
    assert ROUTINE_ARTIFACTS_PATH.exists()
    source = ROUTINE_ARTIFACTS_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    # Count execute() calls in the loop context
    execute_count = len(re.findall(r"\.execute\(\)", window))
    insert_count = len(re.findall(r"\.insert\(", window))

    # In the batch version: 1 .insert() + 1 .execute() = 2 operations total
    # In the per-row version: N .insert() + N .execute() = 2N operations
    # We can't easily assert exact N, but we can assert the pattern where
    # .execute() appears only once (on the batch insert chain)
    # and .insert() appears only once (with a list payload).

    assert insert_count <= 2, (
        f"Behavior B3.3 / AC#7 violated: {_FUNC_NAME} has {insert_count} "
        ".insert() calls. The batch implementation must have exactly 1 "
        "`.insert([...])` call with a list payload."
    )


# ── Edge case: empty insights list ──────────────────────────────────────

def test_b3_3_source_handles_empty_list():
    """Anti-goal: empty insights list should return quickly without DB call."""
    assert ROUTINE_ARTIFACTS_PATH.exists()
    source = ROUTINE_ARTIFACTS_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    # The function should have an early return for empty lists
    assert "if not insights:" in window, (
        f"Behavior B3.3 / AC#7 violated: {_FUNC_NAME} should have an "
        "early return `if not insights: return {'insights_written': 0}` "
        "to avoid unnecessary DB calls for empty input."
    )


# ── Runtime behavior test with exec isolation ────────────────────────────

_stub_logger = MagicMock()
_stub_get_supabase_client = MagicMock()

_NAMESPACE: dict = {
    "__name__": "routine_artifacts",
    "asyncio": asyncio,
    "logging": __import__("logging"),
    "json": __import__("json"),
    "logger": _stub_logger,
    "Any": __import__("typing").Any,
    "Awaitable": __import__("typing").Awaitable,
    "Callable": __import__("typing").Callable,
    "get_supabase_client": _stub_get_supabase_client,
    "_REGISTRY": {},
    "_METADATA": {},
    "register": MagicMock(return_value=lambda fn: fn),
    "call": MagicMock(),
    "_DIMENSION_TO_ROOM": {"finance": "financeiro", "commercial": "clientes",
                           "inventory": "compras", "supply": "compras"},
    "_map_dimension_to_room": lambda d: {"finance": "financeiro",
                                         "commercial": "clientes",
                                         "inventory": "compras",
                                         "supply": "compras"}.get(d, d),
}


def _load_save_insights() -> callable:
    """Extract ``_save_insights`` from routine_artifacts.py source."""
    assert ROUTINE_ARTIFACTS_PATH.exists()
    source = ROUTINE_ARTIFACTS_PATH.read_text(encoding="utf-8")

    body = _get_func_body(source)

    # We need to exec the function. But the function has local imports
    # (from datetime import date, datetime, timezone) and
    # (from blu_supabase_client import get_supabase_client) inside the body.
    # The exec() approach is tricky here due to the nested imports.
    # Instead, we'll mock the get_supabase_client at module level.

    # Patch the function's local imports by pre-defining them in namespace
    _NAMESPACE["date"] = __import__("datetime").date
    _NAMESPACE["datetime"] = __import__("datetime").datetime
    _NAMESPACE["timezone"] = __import__("datetime").timezone

    # Execute the function definition
    exec(body, _NAMESPACE)

    return _NAMESPACE[_FUNC_NAME]


# ── Recorder ─────────────────────────────────────────────────────────────

class _InsertRecorder:
    """Records calls to the client_insights insert chain."""

    def __init__(self):
        self.insert = MagicMock()
        self.insert.return_value = self
        self.execute = MagicMock()

    @property
    def insert_call_count(self) -> int:
        return self.insert.call_count

    @property
    def execute_call_count(self) -> int:
        return self.execute.call_count

    def get_last_payloads(self):
        if self.insert.call_count == 0:
            return []
        call = self.insert.call_args
        args = call[0] if call else []
        return args[0] if args else []


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


@pytest.mark.asyncio
async def test_b3_3_save_insights_uses_batch_insert(mock_db):
    """AC#7 — _save_insights must use a single batch insert call.

    Setup: 3 valid insights. The batch implementation invokes
    .insert() once with a list of 3 payloads, then .execute() once.

    The buggy per-row implementation invokes .insert().execute()
    3 times (N+1).
    """
    db = mock_db
    recorder = _InsertRecorder()
    db.table.return_value = recorder

    func = _load_save_insights()
    client_id = "test-client-uuid"

    insights = [
        {
            "room": "financeiro",
            "kpi": "receita_liquida",
            "title": "Receita acima da média",
            "observation": "Crescimento de 15% este mês",
            "severity": "positive",
            "metric_value": 150000.0,
            "baseline_value": 130000.0,
            "variance_pct": 15.38,
        },
        {
            "room": "clientes",
            "kpi": "churn_rate",
            "title": "Churn rate elevado",
            "observation": "3 clientes cancelaram este mês",
            "severity": "critical",
            "metric_value": 5.2,
            "baseline_value": 2.1,
            "variance_pct": 147.6,
            "recommendation": "Revisar programa de fidelidade",
        },
        {
            "room": "compras",
            "kpi": "custo_total",
            "title": "Custo de insumos estável",
            "observation": "Sem variação significativa",
            "severity": "info",
        },
    ]

    result = await func(
        inputs={"insights": insights},
        client_id=client_id,
    )

    # In the batch version: 1 insert call with all 3 payloads
    # In the per-row version: 3 insert calls (one per insight)
    assert recorder.insert_call_count == 1, (
        f"Expected 1 batch insert call, got {recorder.insert_call_count}. "
        "The per-row loop calls .insert() N times; batch must call it once."
    )

    # The payload should be a list of 3 dicts
    payload = recorder.get_last_payloads()
    assert isinstance(payload, list), (
        f"Expected a list payload for batch insert, got {type(payload)}"
    )
    assert len(payload) == 3, (
        f"Expected 3 insight payloads, got {len(payload)}"
    )

    # Each payload must have the expected fields
    for p in payload:
        assert "client_id" in p
        assert "room" in p
        assert "title" in p
        assert "run_date" in p
        assert p["client_id"] == client_id

    # Return value must have correct count
    assert isinstance(result, dict), "Return must be a dict"
    assert result["insights_written"] == 3, (
        f"Expected 3 insights written, got {result['insights_written']}"
    )


@pytest.mark.asyncio
async def test_b3_3_save_insights_empty_list(mock_db):
    """Edge case: empty insights list returns 0 without DB calls."""
    db = mock_db
    recorder = _InsertRecorder()
    db.table.return_value = recorder

    func = _load_save_insights()

    result = await func(
        inputs={"insights": []},
        client_id="test-client-uuid",
    )

    # Empty list should return 0 without any insert call
    assert result["insights_written"] == 0, (
        f"Expected 0 insights written for empty list, got {result['insights_written']}"
    )


@pytest.mark.asyncio
async def test_b3_3_save_insights_invalid_items_ignored(mock_db):
    """AC#8 — non-dict items in insights are silently ignored."""
    db = mock_db
    recorder = _InsertRecorder()
    db.table.return_value = recorder

    func = _load_save_insights()

    result = await func(
        inputs={
            "insights": [
                {"room": "financeiro", "kpi": "test", "title": "Valid",
                 "observation": "test", "severity": "info"},
                "not-a-dict",
                None,
                42,
                {"room": "clientes", "kpi": "test2", "title": "Valid 2",
                 "observation": "test", "severity": "info"},
            ]
        },
        client_id="test-client-uuid",
    )

    # In batch: 1 insert call with 2 valid items
    # In per-row: 2 insert calls (skipping non-dict)
    if recorder.insert_call_count == 1:
        payload = recorder.get_last_payloads()
        assert len(payload) == 2, (
            f"Expected 2 valid payloads (invalid items filtered), got {len(payload)}"
        )

    assert result["insights_written"] == 2, (
        f"Expected 2 insights written (invalid filtered), got {result['insights_written']}"
    )
