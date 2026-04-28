"""Phase 4 — Reports & Document Generation tests.

Covers:
  • report_format_adapters: markdown ok, pdf/xlsx lazy-import error path
  • generate_report_core happy path (LLM + supabase mocked)
  • generate_report_core failure path (LLM raises → status='failed')
  • _fetch_indicator_block dispatches via get_indicator_block_for RPC
  • reports_dispatch_router: scans due schedules + advances next_run_at
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_TPA_SRC = Path(__file__).resolve().parent.parent / "services" / "tool_pool_api" / "src"
if str(_TPA_SRC) not in sys.path:
    sys.path.insert(0, str(_TPA_SRC))


# ---------------------------------------------------------------------------
# Mock helpers (mirror Phase 3B harness shape)
# ---------------------------------------------------------------------------


class _Resp(SimpleNamespace):
    pass


class _Q:
    def __init__(self, store: dict, table: str):
        self._store = store
        self._table = table
        self._filters: list[tuple[str, str, object]] = []
        self._update_payload: dict | None = None
        self._insert_payload: list[dict] | dict | None = None
        self._upsert_payload: list[dict] | dict | None = None
        self._upsert_kwargs: dict = {}
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._single = False
        self._delete = False

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, list(vals)))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def or_(self, *_a, **_kw):
        return self

    @property
    def not_(self):
        return self

    def is_(self, col, val):
        self._filters.append(("is", col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def single(self):
        self._single = True
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def upsert(self, payload, **kwargs):
        self._upsert_payload = payload
        self._upsert_kwargs = kwargs
        return self

    def delete(self):
        self._delete = True
        return self

    def execute(self):
        rows = list(self._store.get(self._table, []))
        for op, col, val in self._filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "in":
                rows = [r for r in rows if r.get(col) in val]
            elif op == "gte":
                rows = [r for r in rows if (r.get(col) or "") >= val]
            elif op == "is" and val is None:
                rows = [r for r in rows if r.get(col) is None]

        if self._update_payload is not None:
            for r in rows:
                r.update(self._update_payload)
            return _Resp(data=rows)

        if self._delete:
            self._store[self._table] = [
                r for r in self._store.get(self._table, []) if r not in rows
            ]
            return _Resp(data=rows)

        if self._insert_payload is not None:
            payloads = (
                self._insert_payload
                if isinstance(self._insert_payload, list)
                else [self._insert_payload]
            )
            inserted = []
            for p in payloads:
                row = dict(p)
                row.setdefault("id", str(uuid.uuid4()))
                row.setdefault("created_at", datetime.now(UTC).isoformat())
                self._store.setdefault(self._table, []).append(row)
                inserted.append(row)
            return _Resp(data=inserted)

        if self._upsert_payload is not None:
            payloads = (
                self._upsert_payload
                if isinstance(self._upsert_payload, list)
                else [self._upsert_payload]
            )
            upserted = []
            for p in payloads:
                row = dict(p)
                row.setdefault("id", str(uuid.uuid4()))
                row.setdefault("created_at", datetime.now(UTC).isoformat())
                self._store.setdefault(self._table, []).append(row)
                upserted.append(row)
            return _Resp(data=upserted)

        if self._order:
            rows = sorted(
                rows,
                key=lambda r: r.get(self._order[0]) or "",
                reverse=self._order[1],
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._single:
            return _Resp(data=rows[0] if rows else None)
        return _Resp(data=rows)


class _DB:
    def __init__(self, rpc_responses: dict | None = None):
        self.store: dict[str, list[dict]] = {}
        self.rpc_calls: list[tuple[str, dict]] = []
        self._rpc_responses = rpc_responses or {}

    def table(self, name):
        return _Q(self.store, name)

    def rpc(self, name, params=None):
        self.rpc_calls.append((name, params or {}))
        canned = self._rpc_responses.get(name)

        class _R:
            def execute(_inner_self):
                return _Resp(data=canned)

        return _R()


# ---------------------------------------------------------------------------
# Section 1 · report_format_adapters
# ---------------------------------------------------------------------------


class TestFormatAdapters:
    def test_markdown_returns_utf8_bytes(self):
        from tool_pool_api.server.tool_modules.report_format_adapters import to_markdown

        body, mime, fname = to_markdown(markdown_body="# Olá\n\nbody")
        assert mime == "text/markdown"
        assert fname.endswith(".md")
        assert body.decode("utf-8").startswith("# Olá")

    def test_pdf_raises_when_reportlab_missing(self, monkeypatch):
        from tool_pool_api.server.tool_modules import report_format_adapters as adapters
        from fastmcp.exceptions import ToolError

        # Force ImportError by hiding reportlab
        monkeypatch.setitem(sys.modules, "reportlab", None)
        with pytest.raises(ToolError):
            adapters.to_pdf(markdown_body="# x", title="t")

    def test_xlsx_raises_when_openpyxl_missing(self, monkeypatch):
        from tool_pool_api.server.tool_modules import report_format_adapters as adapters
        from fastmcp.exceptions import ToolError

        monkeypatch.setitem(sys.modules, "openpyxl", None)
        with pytest.raises(ToolError):
            adapters.to_xlsx(
                markdown_body="# x", title="t", indicators={"a": 1}
            )


# ---------------------------------------------------------------------------
# Section 2 · generate_report_core
# ---------------------------------------------------------------------------


class TestGenerateReportCore:
    @pytest.mark.asyncio
    async def test_happy_path_writes_run_and_audit(self, monkeypatch):
        from tool_pool_api.server.tool_modules import report_module

        client_id = str(uuid.uuid4())
        db = _DB(
            rpc_responses={
                "get_indicator_block_for": {
                    "receita_total": 12345.67,
                    "ticket_medio": 200.0,
                }
            }
        )
        monkeypatch.setattr(
            report_module, "get_supabase_client", lambda: db
        )

        # Stub LLM: return a non-empty markdown
        fake_msg = SimpleNamespace(content="# Relatório\n\nConteúdo")
        fake_model = SimpleNamespace(ainvoke=AsyncMock(return_value=fake_msg))
        monkeypatch.setattr(
            "blu_llm_service.get_model", lambda **_kw: fake_model
        )

        result = await report_module.generate_report_core(
            cliente_id=client_id,
            template_id="mensal_comercial",
            format="markdown",
            period="30d",
            requested_by=client_id,
        )

        assert result["status"] == "success"
        assert result["format"] == "markdown"
        assert result["template_id"] == "mensal_comercial"
        # Run row inserted then updated to success
        assert len(db.store["report_runs"]) == 1
        run = db.store["report_runs"][0]
        assert run["status"] == "success"
        assert run["output_metadata"]["template_id"] == "mensal_comercial"
        assert "payload_b64" in run["output_metadata"]
        # Indicator dispatcher was called
        assert any(name == "get_indicator_block_for" for name, _ in db.rpc_calls)
        # Audit log emitted
        assert any(name == "record_audit" for name, _ in db.rpc_calls)

    @pytest.mark.asyncio
    async def test_failure_marks_run_failed_with_error_message(self, monkeypatch):
        from tool_pool_api.server.tool_modules import report_module
        from fastmcp.exceptions import ToolError

        client_id = str(uuid.uuid4())
        db = _DB(rpc_responses={"get_indicator_block_for": {}})
        monkeypatch.setattr(report_module, "get_supabase_client", lambda: db)

        # LLM raises
        fake_model = SimpleNamespace(
            ainvoke=AsyncMock(side_effect=RuntimeError("boom"))
        )
        monkeypatch.setattr(
            "blu_llm_service.get_model", lambda **_kw: fake_model
        )

        with pytest.raises(ToolError):
            await report_module.generate_report_core(
                cliente_id=client_id,
                template_id="estoque_critico",
                format="markdown",
                period="30d",
            )

        assert len(db.store["report_runs"]) == 1
        run = db.store["report_runs"][0]
        assert run["status"] == "failed"
        assert "boom" in (run.get("error_message") or "")
        # Audit failure entry
        audit_calls = [
            params for name, params in db.rpc_calls if name == "record_audit"
        ]
        assert any(p.get("p_outcome") == "failure" for p in audit_calls)


# ---------------------------------------------------------------------------
# Section 3 · _fetch_indicator_block dispatches the right RPC
# ---------------------------------------------------------------------------


class TestIndicatorDispatcher:
    def test_calls_get_indicator_block_for(self):
        from tool_pool_api.server.tool_modules import report_module

        db = _DB(
            rpc_responses={
                "get_indicator_block_for": {"x": 1, "y": 2},
            }
        )
        out = report_module._fetch_indicator_block(
            db,
            client_id="abc",
            template_id="caixa_semanal",
            period="7d",
        )
        assert out == {"x": 1, "y": 2}
        assert db.rpc_calls[0][0] == "get_indicator_block_for"
        assert db.rpc_calls[0][1] == {
            "p_client_id": "abc",
            "p_template_id": "caixa_semanal",
            "p_period": "7d",
        }


# ---------------------------------------------------------------------------
# Section 4 · reports_dispatch_router scans + advances next_run_at
# ---------------------------------------------------------------------------


class TestReportsDispatchRouter:
    def test_run_scheduled_advances_next_run_at(self, monkeypatch):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from tool_pool_api.api import reports_dispatch_router as rdr

        client_id = str(uuid.uuid4())
        schedule_id = str(uuid.uuid4())
        due = [
            {
                "id": schedule_id,
                "client_id": client_id,
                "template_id": "mensal_comercial",
                "period": "30d",
                "format": "markdown",
                "cadence": "monthly",
            }
        ]
        db = _DB(rpc_responses={"list_due_report_schedules": due})
        db.store["report_schedules"] = [
            {
                "id": schedule_id,
                "client_id": client_id,
                "template_id": "mensal_comercial",
                "cadence": "monthly",
                "enabled": True,
                "last_run_at": None,
                "next_run_at": "2020-01-01T00:00:00+00:00",
            }
        ]
        monkeypatch.setattr(rdr, "get_supabase_client", lambda: db)

        # Stub the core so we don't hit LLM/network. The dispatch router
        # imports `generate_report_core` lazily from the report_module, so
        # we patch the source module directly.
        async def _fake_core(**kwargs):
            return {
                "run_id": str(uuid.uuid4()),
                "status": "success",
                "template_id": kwargs["template_id"],
                "format": kwargs.get("format") or "markdown",
                "period": kwargs.get("period") or "30d",
                "output_url": None,
                "output_metadata": {},
            }

        from tool_pool_api.server.tool_modules import report_module
        monkeypatch.setattr(report_module, "generate_report_core", _fake_core)
        monkeypatch.setenv("REPORTS_DISPATCH_TOKEN", "secret")

        app = FastAPI()
        app.include_router(rdr.router)
        client = TestClient(app)

        resp = client.post(
            "/internal/reports/run-scheduled",
            headers={"Authorization": "Bearer secret"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["scanned"] == 1
        assert body["generated"] == 1

        # last_run_at + next_run_at were advanced
        sched = db.store["report_schedules"][0]
        assert sched["last_run_at"] is not None
        assert sched["next_run_at"] != "2020-01-01T00:00:00+00:00"

    def test_run_scheduled_rejects_bad_token(self, monkeypatch):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from tool_pool_api.api import reports_dispatch_router as rdr

        monkeypatch.setenv("REPORTS_DISPATCH_TOKEN", "secret")

        app = FastAPI()
        app.include_router(rdr.router)
        client = TestClient(app)

        resp = client.post(
            "/internal/reports/run-scheduled",
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401
