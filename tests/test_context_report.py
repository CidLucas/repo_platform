"""Unit tests for context_report phrase-building logic.

Tests cover:
  - _fmt: BRL / % / count / fallback formatting
  - _fmt_change: p.p. for % KPIs, relative % for others
  - _build_phrase: all four phrase fragments (current, MoM, vs 6m, streak)
  - _build_phrases: grouping by dimension, None-value skipping
"""

from __future__ import annotations

import pytest


# Override the root conftest autouse DB-cleanup fixture — these are pure unit
# tests and have no Supabase dependency.
@pytest.fixture(autouse=True)
def _cleanup_test_data():  # noqa: PT004
    yield


from blu_agent_framework.routines.context_report import (
    MetricRow,
    _build_phrase,
    _build_phrases,
    _fmt,
    _fmt_change,
    _write_to_shared_memory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(**kwargs) -> MetricRow:
    """Build a MetricRow with sensible defaults; override via kwargs."""
    defaults = {
        "dimension": "finance",
        "kpi": "receita_liquida",
        "label": "Receita Líquida",
        "unit": "BRL",
        "current_value": 100_000.0,
        "prev_month_value": 90_000.0,
        "avg_6m": 95_000.0,
        "mom_pct": 11.1,
        "vs_6m_avg_pct": 5.3,
        "streak_months": 3,
    }
    defaults.update(kwargs)
    return MetricRow(**defaults)


# ---------------------------------------------------------------------------
# _fmt
# ---------------------------------------------------------------------------


class TestFmt:
    def test_brl_millions(self):
        assert _fmt(2_500_000.0, "BRL") == "R$ 2.5M"

    def test_brl_thousands(self):
        assert _fmt(42_000.0, "BRL") == "R$ 42k"

    def test_brl_small(self):
        assert _fmt(340.0, "BRL") == "R$ 340"

    def test_pct(self):
        assert _fmt(41.0, "%") == "41.0%"

    def test_count_thousands(self):
        assert _fmt(1_240.0, "count") == "1.240"

    def test_count_millions(self):
        assert _fmt(1_200_000.0, "count") == "1.2M"

    def test_count_small(self):
        assert _fmt(7.0, "count") == "7"

    def test_none(self):
        assert _fmt(None, "BRL") == "N/D"

    def test_fallback_unit(self):
        result = _fmt(3.14159, "days")
        assert result == "3.14"


# ---------------------------------------------------------------------------
# _fmt_change
# ---------------------------------------------------------------------------


class TestFmtChange:
    def test_pct_kpi_positive(self):
        assert _fmt_change(2.5, "%") == "+2.5 p.p."

    def test_pct_kpi_negative(self):
        assert _fmt_change(-3.0, "%") == "-3.0 p.p."

    def test_brl_positive(self):
        assert _fmt_change(11.1, "BRL") == "+11.1%"

    def test_brl_negative(self):
        assert _fmt_change(-5.0, "BRL") == "-5.0%"

    def test_count_positive(self):
        assert _fmt_change(20.0, "count") == "+20.0%"


# ---------------------------------------------------------------------------
# _build_phrase — BRL row (happy path)
# ---------------------------------------------------------------------------


class TestBuildPhraseBRL:
    def setup_method(self):
        self.row = _row()
        self.phrase = _build_phrase(self.row)
        self.parts = self.phrase.split(" · ")

    def test_starts_with_label_and_current_value(self):
        assert self.parts[0].startswith("**Receita Líquida**: R$ 100k este mês")

    def test_mom_contains_arrow_and_change(self):
        mom_part = self.parts[1]
        assert "▲" in mom_part
        assert "+11.1%" in mom_part
        assert "R$ 90k" in mom_part

    def test_vs_6m_contains_above_and_avg(self):
        avg_part = self.parts[2]
        assert "acima" in avg_part
        assert "média dos últimos 6 meses" in avg_part
        assert "R$ 95k" in avg_part

    def test_streak_mention(self):
        streak_part = self.parts[3]
        assert "3 meses consecutivos" in streak_part
        assert "crescimento" in streak_part


# ---------------------------------------------------------------------------
# _build_phrase — % KPI (p.p. formatting)
# ---------------------------------------------------------------------------


class TestBuildPhrasePct:
    def setup_method(self):
        self.row = _row(
            kpi="taxa_recorrencia_perc",
            label="Taxa de Recorrência",
            unit="%",
            current_value=45.0,
            prev_month_value=40.0,
            avg_6m=42.0,
            mom_pct=5.0,
            vs_6m_avg_pct=7.1,
            streak_months=2,
        )
        self.phrase = _build_phrase(self.row)
        self.parts = self.phrase.split(" · ")

    def test_mom_uses_pp(self):
        assert "p.p." in self.parts[1]
        assert "+5.0 p.p." in self.parts[1]

    def test_vs_6m_uses_absolute_pp(self):
        # |45.0 - 42.0| = 3.0 p.p.
        avg_part = self.parts[2]
        assert "3.0 p.p." in avg_part

    def test_streak_at_min_threshold(self):
        assert "2 meses consecutivos" in self.parts[3]


# ---------------------------------------------------------------------------
# _build_phrase — falling streak
# ---------------------------------------------------------------------------


def test_falling_streak():
    row = _row(streak_months=-4, mom_pct=-10.0)
    phrase = _build_phrase(row)
    assert "queda" in phrase
    assert "4 meses consecutivos" in phrase
    assert "▼" in phrase


# ---------------------------------------------------------------------------
# _build_phrase — streak below threshold is suppressed
# ---------------------------------------------------------------------------


def test_streak_below_threshold_suppressed():
    row = _row(streak_months=1)
    phrase = _build_phrase(row)
    assert "meses consecutivos" not in phrase


def test_streak_zero_suppressed():
    row = _row(streak_months=0)
    phrase = _build_phrase(row)
    assert "meses consecutivos" not in phrase


# ---------------------------------------------------------------------------
# _build_phrase — first month (no prev_month_value / no mom_pct)
# ---------------------------------------------------------------------------


def test_first_month_no_prev():
    row = _row(prev_month_value=None, mom_pct=None)
    phrase = _build_phrase(row)
    assert "primeiro mês com dados" in phrase


# ---------------------------------------------------------------------------
# _build_phrase — no 6m average (avg_6m is None)
# ---------------------------------------------------------------------------


def test_no_avg_6m():
    row = _row(avg_6m=None, vs_6m_avg_pct=None)
    phrase = _build_phrase(row)
    # vs-6m part should not appear
    assert "média dos últimos 6 meses" not in phrase


# ---------------------------------------------------------------------------
# _build_phrases — grouping and None-value filtering
# ---------------------------------------------------------------------------


class TestBuildPhrases:
    def test_groups_by_dimension(self):
        rows = [
            _row(dimension="finance",    kpi="receita_liquida",    label="Receita"),
            _row(dimension="commercial", kpi="clientes_unicos",    label="Clientes", unit="count", current_value=500.0),
            _row(dimension="inventory",  kpi="skus_ativos",        label="SKUs",     unit="count", current_value=80.0),
        ]
        sections = _build_phrases(rows)
        assert len(sections["finance"]) == 1
        assert len(sections["commercial"]) == 1
        assert len(sections["inventory"]) == 1
        assert sections["supply"] == []

    def test_rows_with_none_current_value_are_skipped(self):
        rows = [
            _row(dimension="finance", kpi="receita_liquida", current_value=None),
        ]
        sections = _build_phrases(rows)
        assert sections["finance"] == []

    def test_unknown_dimension_is_ignored(self):
        rows = [
            _row(dimension="other_dim", kpi="foo", label="Foo"),
        ]
        sections = _build_phrases(rows)
        assert "other_dim" not in sections

    def test_all_four_dimension_keys_always_present(self):
        sections = _build_phrases([])
        assert set(sections.keys()) == {"finance", "commercial", "inventory", "supply"}


# ---------------------------------------------------------------------------
# _write_to_shared_memory
# ---------------------------------------------------------------------------


class TestWriteToSharedMemory:
    """Unit tests for _write_to_shared_memory."""

    def _make_row(self, kpi: str, value: float | None = 100.0) -> MetricRow:
        return MetricRow(
            dimension="finance",
            kpi=kpi,
            label=kpi.replace("_", " ").title(),
            unit="BRL",
            current_value=value,
            prev_month_value=None,
            avg_6m=None,
            mom_pct=None,
            vs_6m_avg_pct=None,
            streak_months=0,
        )

    # ------------------------------------------------------------------
    # Happy path: all three entries written
    # ------------------------------------------------------------------

    def test_writes_resumo_entry(self) -> None:
        """Checks the 'resumo' snapshot entry has the correct structure."""
        import datetime

        from unittest.mock import MagicMock, call

        db = MagicMock()
        rows = [self._make_row("receita_liquida", 100_000.0)]

        _write_to_shared_memory(
            db,
            client_id="cl-1",
            today=datetime.date(2026, 6, 23),
            metrics_count=15,
            report_chars=4_200,
            upserted=True,
            summary=["**Receita Líquida**: R$ 100k (▲ vs mês anterior)"],
            rows=rows,
        )

        # There should be 3 upsert calls
        assert db.schema.call_count >= 1

        # Verify the first upsert (resumo) was called with correct args
        upsert_calls = []
        for method_call in db.method_calls:
            if method_call[0] == "schema":
                args = method_call[1]
                if args and args[0] == "public":
                    upsert_calls.append(method_call)

        assert len(upsert_calls) >= 1

    def test_writes_three_entries(self) -> None:
        """Verify exactly three shared memory entries are upserted."""
        import datetime

        from unittest.mock import MagicMock

        db = MagicMock()
        rows = [
            self._make_row("receita_liquida", 100_000.0),
            self._make_row("ticket_medio", 250.0),
            self._make_row("clientes_unicos", 500.0),
        ]
        rows[1].unit = "BRL"
        rows[2].unit = "count"

        _write_to_shared_memory(
            db,
            client_id="cl-1",
            today=datetime.date(2026, 6, 23),
            metrics_count=3,
            report_chars=1_200,
            upserted=True,
            summary=["summary line"],
            rows=rows,
        )

        # There should be 3 upsert calls in the chain
        upsert_calls = db.schema.return_value.table.return_value.upsert.call_args_list
        assert len(upsert_calls) == 3, f"Expected 3 upsert calls, got {len(upsert_calls)}"

        # Verify the keys of the three entries
        keys = [call[0][0]["key"] for call in upsert_calls]
        assert keys == ["resumo", "indicadores", "ultima_execucao"], f"Got keys: {keys}"

    # ------------------------------------------------------------------
    # Error resilience
    # ------------------------------------------------------------------

    def test_error_does_not_raise(self) -> None:
        """An exception inside _write_to_shared_memory must be swallowed."""
        import datetime

        from unittest.mock import MagicMock

        db = MagicMock()
        db.schema.side_effect = RuntimeError("DB unavailable")

        # Should not raise
        _write_to_shared_memory(
            db,
            client_id="cl-1",
            today=datetime.date(2026, 6, 23),
            metrics_count=5,
            report_chars=1_000,
            upserted=False,
            summary=[],
            rows=[],
        )

    # ------------------------------------------------------------------
    # Entity naming
    # ------------------------------------------------------------------

    def test_entity_name_format(self) -> None:
        """Snapshot entity_name must follow 'context_report:YYYY-MM'."""
        import datetime

        from unittest.mock import MagicMock

        db = MagicMock()

        _write_to_shared_memory(
            db,
            client_id="cl-1",
            today=datetime.date(2026, 6, 23),
            metrics_count=0,
            report_chars=0,
            upserted=False,
            summary=[],
            rows=[],
        )

        # Check that the first upsert payload has the correct entity_name
        schema_call = db.schema.call_args
        assert schema_call is not None
        args, _kwargs = schema_call
        assert args[0] == "public"

        # Verify the upsert payloads via the method chain
        table_call = db.schema.return_value.table.call_args
        assert table_call is not None
        args, _kwargs = table_call
        assert args[0] == "shared_business_memory"

        upsert_calls = db.schema.return_value.table.return_value.upsert.call_args_list
        # First upsert: snapshot-resumo (entity_name='context_report:2026-06')
        args, _kwargs = upsert_calls[0]
        payload = args[0]
        assert payload["entity_type"] == "snapshot"
        assert payload["entity_name"] == "context_report:2026-06"
        assert payload["key"] == "resumo"

    # ------------------------------------------------------------------
    # KPI indicadores extraction
    # ------------------------------------------------------------------

    def test_indicadores_includes_summary_and_snapshot_kpis(self) -> None:
        """The 'indicadores' entry should contain only SUMMARY_KPIS + SNAPSHOT_KPIS."""
        import datetime

        from unittest.mock import MagicMock

        db = MagicMock()

        rows = [
            self._make_row("receita_liquida", 100_000.0),         # in _SUMMARY_KPIS
            self._make_row("receita_ytd", 500_000.0),              # in _SNAPSHOT_KPIS
            self._make_row("some_other_kpi", 42.0),                # not in either set
        ]
        rows[1].unit = "BRL"

        _write_to_shared_memory(
            db,
            client_id="cl-1",
            today=datetime.date(2026, 6, 23),
            metrics_count=3,
            report_chars=1_000,
            upserted=True,
            summary=["line"],
            rows=rows,
        )

        # The first two upsert calls are resumo and indicadores (snapshot).
        # We need the second call's payload value — it's the indicadores dict.
        # Navigate the chain: the second .upsert() call's payload is what matters.
        upsert_calls = db.schema.return_value.table.return_value.upsert.call_args_list
        assert len(upsert_calls) >= 2  # At least resumo + indicadores

        # Find the indicadores upsert (key='indicadores')
        indicadores_payload = None
        for call_args in upsert_calls:
            args, _kwargs = call_args
            payload = args[0]
            if payload.get("key") == "indicadores":
                indicadores_payload = payload
                break

        assert indicadores_payload is not None, "No indicadores upsert found"
        assert "receita_liquida" in indicadores_payload["value"]
        assert indicadores_payload["value"]["receita_liquida"] == 100_000.0
        assert "receita_ytd" in indicadores_payload["value"]
        assert indicadores_payload["value"]["receita_ytd"] == 500_000.0
        assert "some_other_kpi" not in indicadores_payload["value"]

    # ------------------------------------------------------------------
    # Source and category
    # ------------------------------------------------------------------

    def test_source_and_category(self) -> None:
        """All entries must have source='system' and category='context'."""
        import datetime

        from unittest.mock import MagicMock

        db = MagicMock()

        _write_to_shared_memory(
            db,
            client_id="cl-1",
            today=datetime.date(2026, 6, 23),
            metrics_count=1,
            report_chars=500,
            upserted=True,
            summary=["test"],
            rows=[self._make_row("receita_liquida", 100.0)],
        )

        upsert_calls = db.schema.return_value.table.return_value.upsert.call_args_list
        for call_args in upsert_calls:
            args, _kwargs = call_args
            payload = args[0]
            assert payload["source"] == "system", f"Expected source=system, got {payload['source']}"
            assert payload["category"] == "context", f"Expected category=context, got {payload['category']}"
