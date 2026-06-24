"""RED test for behavior B5 — fix _prune_old_versions delete bottleneck.

GOAL:
    O prune de versões antigas (``_prune_old_versions`` em
    ``version_module.py``) é chamado em dois hot paths — depois de cada
    ``_archive_memory_version`` e de cada ``_store_memory_version`` —
    e está implementado como um loop de N ``.delete()`` round-trips
    para o Supabase, um por id a remover.  Quando a tabela está no
    limite (50 versões) e mais 10 são inseridas, o prune faz 10
    ``.execute()`` sequenciais.  Isso é o gargalo: em um cliente
    ativo que gera muitas versões por hora, o loop multiplica a
    latência do Supabase por N.

BEHAVIOR:
    B5 — ``_prune_old_versions`` deve usar um único ``.delete()`` em
    batch via ``.in_("id", [...])`` em vez de um loop per-row.

    Hoje (RED) o código faz:

        for vid in to_delete:
            await db.schema("public").table(_VERSION_TABLE) \
                .delete().eq("id", vid).eq("client_id", client_id).execute()

    O contrato GREEN esperado é:

        await db.schema("public").table(_VERSION_TABLE) \
            .delete().in_("id", to_delete) \
            .eq("client_id", client_id).execute()

    Aceitação:
        AC#9 — ``_prune_old_versions`` faz exatamente 1 chamada a
               ``.execute()`` no chain do ``.delete()`` quando há
               versões a remover (batch), e 0 quando ``total <= max``.

DECISION:
    Estratégia: fix
    Arquivo alvo:
        services/tool_pool_api/src/tool_pool_api/server/tool_modules/version_module.py
    Função alvo: ``_prune_old_versions`` (linha ~414)
    Substituir o ``for vid in to_delete: ...`` por um único
    ``delete().in_("id", to_delete).eq("client_id", client_id).execute()``.

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura pública de ``_prune_old_versions``.
    2. NÃO alterar o contrato de retorno (número inteiro de versões
       removidas).
    3. NÃO introduzir dependência real do Supabase — o teste usa
       ``exec()`` isolation e ``AsyncMock``.
    4. NÃO alterar a função ``_archive_memory_version`` ou
       ``_store_memory_version`` — B5 é exclusivamente sobre o prune.

Estado atual: RED — o loop per-row chama ``.execute()`` N vezes
(uma por id).  O teste falha com AssertionError ao contar o número
de chamadas a ``.execute()`` no chain do ``.delete()`` ou ao verificar
que ``.in_("id", ...)`` foi invocado.  A GREEN vai consolidar tudo
em uma única chamada batch.
"""

import re
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Paths ────────────────────────────────────────────────────────────────


# ── Override root conftest cleanup (pure unit test, no DB teardown) ──────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test uses mocked Supabase only."""
    yield


# ── exec() isolation loader ──────────────────────────────────────────────
# Mirrors the pattern in tests/behaviors/test_b1_flush_logic.py and
# tests/behaviors/test_b3_lifecycle_fields_export.py: parse out the
# constants/helpers that ``_prune_old_versions`` references, then exec
# only the function body in a controlled namespace.


_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()

_NAMESPACE: dict = {
    "__name__": "version_module",
    "json": __import__("json"),
    "logging": __import__("logging"),
    "hashlib": __import__("hashlib"),
    "difflib": __import__("difflib"),
    "Any": __import__("typing").Any,
    "logger": _stub_logger,
    "Context": MagicMock,
    "FastMCP": MagicMock,
    "ToolError": type("ToolError", (Exception,), {}),
    "mcp_inject_client_id": MagicMock(return_value=lambda fn: fn),
    "get_supabase_client": _stub_get_supabase_client,
    "register_module": MagicMock(return_value=lambda fn: fn),
}


VERSION_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "server"
    / "tool_modules"
    / "version_module.py"
)


def _load_prune_function() -> callable:
    """Extract ``_prune_old_versions`` from version_module.py source.

    Pulls in the minimum surface area the function needs:
        - _VALID_ENTITY_TYPES  (used by _validate_entity_type)
        - _VERSION_TABLE       (the table name)
        - _validate_entity_type
        - _normalize_entity_name
    Then exec's only the function body.
    """
    assert VERSION_MODULE_PATH.exists(), (
        f"Source file not found: {VERSION_MODULE_PATH}"
    )
    source = VERSION_MODULE_PATH.read_text(encoding="utf-8")

    # 1) Extract _VALID_ENTITY_TYPES constant
    vt_marker = "_VALID_ENTITY_TYPES: frozenset[str] = frozenset("
    vt_idx = source.find(vt_marker)
    assert vt_idx != -1, "Could not find _VALID_ENTITY_TYPES"
    vt_lines = []
    for vline in source[vt_idx:].split("\n"):
        vt_lines.append(vline.rstrip())
        if ")" in vline and not vline.strip().startswith("#"):
            break
    exec("\n".join(vt_lines), _NAMESPACE)

    # 2) Extract helpers: _validate_entity_type, _normalize_entity_name
    for helper_name in ("_validate_entity_type", "_normalize_entity_name"):
        helper_marker = f"def {helper_name}("
        hidx = source.find(helper_marker)
        if hidx == -1:
            continue
        h_lines = []
        in_fn = False
        for hline in source[hidx:].split("\n"):
            hs = hline.rstrip()
            if f"def {helper_name}(" in hs:
                in_fn = True
                h_lines.append(hs)
                continue
            if in_fn:
                if hs == "":
                    h_lines.append("")
                    continue
                hindent = len(hline) - len(hline.lstrip())
                if hindent == 0 and hs and not hs.strip().startswith("#"):
                    break
                h_lines.append(hs)
        exec("\n".join(h_lines), _NAMESPACE)

    # 3) Extract _VERSION_TABLE constant
    vt_const_marker = '_VERSION_TABLE = "shared_business_memory_versions"'
    vtc_idx = source.find(vt_const_marker)
    assert vtc_idx != -1, "Could not find _VERSION_TABLE"
    exec(
        source[vtc_idx : vtc_idx + len(vt_const_marker) + 1],
        _NAMESPACE,
    )

    # 3b) Extract _MAX_VERSIONS_PER_KEY constant (used as default arg)
    mvp_marker = "_MAX_VERSIONS_PER_KEY = "
    mvp_idx = source.find(mvp_marker)
    assert mvp_idx != -1, "Could not find _MAX_VERSIONS_PER_KEY"
    mvp_line = source[mvp_idx:].split("\n", 1)[0]
    exec(mvp_line, _NAMESPACE)

    # 4) Extract _prune_old_versions function body
    marker = "async def _prune_old_versions("
    idx = source.find(marker)
    assert idx != -1, f"Could not find '{marker}'"

    # Walk back to the preceding section comment
    fn_start = source.rfind("#", 0, idx)
    assert fn_start != -1, "Could not find section comment start"

    fn_lines: list[str] = []
    in_fn = False
    for line in source[fn_start:].split("\n"):
        stripped = line.rstrip()
        if not stripped and not in_fn:
            continue
        if "async def _prune_old_versions(" in line:
            in_fn = True
            fn_lines.append(stripped)
            continue
        if in_fn:
            if stripped == "":
                fn_lines.append("")
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0 and stripped.startswith("# -------"):
                break
            if indent == 0 and (
                stripped.startswith("async def ")
                or stripped.startswith("@")
                or stripped.startswith("def ")
            ):
                break
            fn_lines.append(stripped)

    fn_source = "\n".join(fn_lines)
    exec(fn_source, _NAMESPACE)
    return _NAMESPACE["_prune_old_versions"]


_prune_old_versions = _load_prune_function()


# ── Supabase chain mock helpers ──────────────────────────────────────────


class _DeleteCallRecorder:
    """Wraps a delete chain and records each call to .in_ / .execute().

    ``_prune_old_versions`` does:
        db.schema("public").table("shared_business_memory_versions")
            .select("id").eq(...).eq(...).eq(...).eq(...).order(...).execute()

    and then, after computing to_delete, does (per row in the buggy
    implementation):
        db.schema("public").table("shared_business_memory_versions")
            .delete().eq("id", vid).eq("client_id", client_id).execute()

    This recorder lets the test count how many times the delete branch
    was executed and whether ``.in_("id", [...])`` was used.
    """

    def __init__(self) -> None:
        self.in_calls: list[list] = []
        self.eq_calls: list[tuple[str, object]] = []
        self.execute_calls: int = 0

    def install_on(self, table_mock: MagicMock) -> None:
        """Wire the recorder into the table-level delete() chain.

        Each call to ``table_mock.delete()`` returns a fresh chain object
        that captures ``.in_``, ``.eq`` and ``.execute``.  The buggy
        per-row implementation invokes ``.delete()`` once per id (so
        ``execute_calls`` ends up > 1), while the batch implementation
        invokes ``.delete()`` once and then ``.in_("id", [...]).execute()``
        (so ``execute_calls`` == 1 and ``in_calls`` is non-empty).
        """
        recorder = self

        def _delete_factory() -> MagicMock:
            chain = MagicMock()
            chain.in_.side_effect = (
                lambda col, values: recorder.in_calls.append(list(values))
                or chain
            )
            chain.eq.side_effect = (
                lambda col, val: recorder.eq_calls.append((col, val))
                or chain
            )

            async def _execute() -> MagicMock:
                recorder.execute_calls += 1
                result = MagicMock()
                result.data = []
                return result

            chain.execute = _execute
            return chain

        table_mock.delete.side_effect = _delete_factory


def _make_list_result(rows: list[dict]) -> MagicMock:
    """Build a mock Supabase execute() result with a list in .data."""
    mock_result = MagicMock()
    mock_result.data = rows
    return mock_result


def _setup_select_chain(
    mock_supabase: MagicMock,
    *,
    rows: list[dict],
    table_mock: MagicMock,
) -> None:
    """Wire the SELECT chain so the ``.execute()`` returns ``rows``.

    Mirrors the chain used by ``_prune_old_versions``:
        .select("id").eq(c1, v1).eq(c2, v2).eq(c3, v3).eq(c4, v4)
        .order("version", desc=False).execute()
    """
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.order.return_value = table_mock

    select_result = _make_list_result(rows)

    async def _select_execute() -> MagicMock:
        return select_result

    # IMPORTANT: this ``execute`` is the one called from the SELECT
    # branch.  We need to keep it separate from the DELETE recorder's
    # execute, so the recorder owns table_mock.delete side effect, and
    # we install the SELECT execute AFTER the recorder is installed
    # (so the recorder's side_effect on ``.delete`` is preserved).
    table_mock.execute = _select_execute


def _sample_version_rows(total: int) -> list[dict]:
    """Build ``total`` version rows ordered oldest→newest (version asc)."""
    return [
        {"id": f"v{i:03d}", "version": i} for i in range(1, total + 1)
    ]


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_supabase():
    """Mock Supabase client returning a chainable query builder."""
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


@pytest.fixture
def delete_recorder():
    """A fresh ``_DeleteCallRecorder`` per test."""
    return _DeleteCallRecorder()


# ── Source-level guard ───────────────────────────────────────────────────


def test_b5_source_prune_uses_in_clause():
    """Source-level guard: the body of ``_prune_old_versions`` must
    contain a ``.in_(`` call on the ``_VERSION_TABLE`` delete chain.

    This catches the bug even if the test runtime cannot introspect
    ``MagicMock`` side-effects (e.g. if a refactor moves the chain
    into a helper).
    """
    assert VERSION_MODULE_PATH.exists()
    source = VERSION_MODULE_PATH.read_text(encoding="utf-8")

    body_marker = "async def _prune_old_versions("
    idx = source.find(body_marker)
    assert idx != -1, "Could not locate _prune_old_versions"

    # Take a generous window: from the function header to the next
    # blank line followed by a top-level ``# ---`` or top-level def.
    window = source[idx : idx + 6000]
    assert ".in_(" in window, (
        "Behavior B5 / AC#9 violated: _prune_old_versions body must use "
        "a batch `.in_(...)` clause on the delete chain instead of a "
        "per-row `.eq(\"id\", vid)` loop. Source does not contain "
        "`.in_(` inside the function window."
    )

    # Anti-goal: the per-row delete loop must be gone.
    assert not re.search(
        r"for\s+\w+\s+in\s+to_delete\s*:",
        window,
    ), (
        "Behavior B5 / AC#9 violated: _prune_old_versions still contains "
        "a `for ... in to_delete:` loop. The batch implementation must "
        "delete ALL ids in a single Supabase call."
    )


# ── Behavior tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_b5_prune_uses_batch_delete_with_in_clause(
    mock_supabase, delete_recorder
):
    """AC#9 — the delete branch of ``_prune_old_versions`` must use a
    batch ``.in_("id", [...])`` call.

    Setup: 60 versions, max_versions=50 → 10 must be deleted.
    The batch implementation invokes ``.delete()`` once, then
    ``.in_("id", [10 ids])`` and then ``.execute()`` once.

    The buggy per-row implementation invokes ``.delete()`` 10 times
    (one per id) and never calls ``.in_``.
    """
    # Build the full table mock and wire up the recorder.
    table_mock = MagicMock()
    schema_mock = MagicMock()
    schema_mock.table.return_value = table_mock
    mock_supabase.schema.return_value = schema_mock

    delete_recorder.install_on(table_mock)

    rows = _sample_version_rows(total=60)
    _setup_select_chain(
        mock_supabase, rows=rows, table_mock=table_mock
    )

    client_id = str(uuid.uuid4())
    deleted = await _prune_old_versions(
        client_id=client_id,
        entity_type="snapshot",
        entity_name="customer_a",
        key="address",
        max_versions=50,
    )

    # 1. Returned count is still 10 — the public contract is preserved.
    assert deleted == 10, (
        f"_prune_old_versions must return 10 (60 - 50), got {deleted}. "
        f"Behavior B5 must not change the return-value contract."
    )

    # 2. The batch ``.in_(...)`` clause was actually used.
    assert delete_recorder.in_calls, (
        "AC#9 violated: _prune_old_versions never called .in_() on the "
        "delete chain. The current implementation loops over ids and "
        "issues one .delete().eq('id', vid) per row. B5 requires a "
        "single batch .delete().in_('id', [...]).execute() call. "
        f"Got in_calls={delete_recorder.in_calls!r}, "
        f"execute_calls={delete_recorder.execute_calls}"
    )

    # 3. The .in_ call targeted the ``id`` column with all 10 ids.
    in_target_col, in_target_values = None, None
    for col, vals in delete_recorder.in_calls:
        if col == "id":
            in_target_col = col
            in_target_values = vals
            break
    assert in_target_col == "id", (
        f"AC#9 violated: .in_() was called on column {in_target_col!r}, "
        "expected 'id'. All batched delete ids must be sent through the "
        "'id' column of shared_business_memory_versions."
    )
    assert sorted(in_target_values) == [f"v{i:03d}" for i in range(1, 11)], (
        f"AC#9 violated: .in_('id', values) must contain exactly the 10 "
        f"oldest version ids (v001..v010), got {sorted(in_target_values)!r}."
    )


@pytest.mark.asyncio
async def test_b5_prune_uses_single_execute_call(
    mock_supabase, delete_recorder
):
    """AC#9 — the delete branch must call ``.execute()`` exactly once
    when there are versions to prune.

    With 60 versions and max=50, the buggy loop calls .execute() 10
    times. The batch implementation must call it exactly once.
    """
    table_mock = MagicMock()
    schema_mock = MagicMock()
    schema_mock.table.return_value = table_mock
    mock_supabase.schema.return_value = schema_mock

    delete_recorder.install_on(table_mock)

    rows = _sample_version_rows(total=60)
    _setup_select_chain(
        mock_supabase, rows=rows, table_mock=table_mock
    )

    client_id = str(uuid.uuid4())
    deleted = await _prune_old_versions(
        client_id=client_id,
        entity_type="snapshot",
        entity_name="customer_a",
        key="address",
        max_versions=50,
    )

    assert deleted == 10, (
        f"Expected 10 deletions, got {deleted}. The prune count must "
        f"match (total - max_versions)."
    )

    assert delete_recorder.execute_calls == 1, (
        f"AC#9 violated: _prune_old_versions called .execute() on the "
        f"delete chain {delete_recorder.execute_calls} time(s); expected "
        f"exactly 1 (batch delete). The current per-row loop calls "
        f".execute() once per id — a 10× latency tax on the Supabase "
        f"hot path. B5 must collapse this into a single batch call."
    )


@pytest.mark.asyncio
async def test_b5_prune_below_limit_issues_no_delete(
    mock_supabase, delete_recorder
):
    """AC#9 (zero case) — when ``total <= max_versions`` the function
    must return 0 and NOT issue any delete.

    Both buggy and GREEN implementations satisfy this, but we lock it
    in as a regression guard so a future refactor doesn't accidentally
    issue a delete in the zero-prune path.
    """
    table_mock = MagicMock()
    schema_mock = MagicMock()
    schema_mock.table.return_value = table_mock
    mock_supabase.schema.return_value = schema_mock

    delete_recorder.install_on(table_mock)

    rows = _sample_version_rows(total=10)
    _setup_select_chain(
        mock_supabase, rows=rows, table_mock=table_mock
    )

    client_id = str(uuid.uuid4())
    deleted = await _prune_old_versions(
        client_id=client_id,
        entity_type="snapshot",
        entity_name="customer_a",
        key="address",
        max_versions=50,
    )

    assert deleted == 0
    assert delete_recorder.execute_calls == 0, (
        f"AC#9 violated: when total (10) <= max_versions (50), the "
        f"delete chain must not be invoked at all. Got "
        f"execute_calls={delete_recorder.execute_calls}."
    )
    assert delete_recorder.in_calls == [], (
        f"AC#9 violated: .in_() must not be called when no prune is "
        f"needed. Got in_calls={delete_recorder.in_calls!r}."
    )


@pytest.mark.asyncio
async def test_b5_prune_uses_supabase_default_when_max_omitted(
    mock_supabase, delete_recorder
):
    """AC#9 — calling ``_prune_old_versions`` without ``max_versions``
    must still batch the delete (default is 50).

    Setup: 55 versions → 5 must be deleted in a single batch.
    """
    table_mock = MagicMock()
    schema_mock = MagicMock()
    schema_mock.table.return_value = table_mock
    mock_supabase.schema.return_value = schema_mock

    delete_recorder.install_on(table_mock)

    rows = _sample_version_rows(total=55)
    _setup_select_chain(
        mock_supabase, rows=rows, table_mock=table_mock
    )

    client_id = str(uuid.uuid4())
    deleted = await _prune_old_versions(
        client_id=client_id,
        entity_type="snapshot",
        entity_name="customer_b",
        key="phone",
    )

    assert deleted == 5
    assert delete_recorder.execute_calls == 1, (
        f"AC#9 violated (default max): expected 1 batched .execute() "
        f"call, got {delete_recorder.execute_calls}."
    )
    assert delete_recorder.in_calls, (
        "AC#9 violated (default max): .in_() was never called on the "
        "delete chain. B5 requires a batch delete even when max_versions "
        "falls back to the default 50."
    )
