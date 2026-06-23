"""RED tests for _extract_entity_references from memory_module.py.

This is the TDD RED phase: _extract_entity_references does NOT yet exist
in memory_module.py, so the test file must fail with AttributeError at
load time.

What the function must do (GREEN phase contract):
    _extract_entity_references(markdown_text: str) -> list[dict]

    Scans a markdown string for entity references encoded as
    ``[label](entity_type:entity_name)`` and returns a list of dicts of
    the form::

        {"entity_type": <str>, "entity_name": <str>, "label": <str>,
         "span": (start, end)}

    Only entity_types from the canonical set are accepted:
        skill, client, contact, supplier, user,
        snapshot, routine, agent_result, agent_metadata

    Unknown entity_types are ignored.  Duplicate references are
    preserved (callers can de-duplicate if needed).

Isolation pattern
-----------------
The function is loaded from ``memory_module.py`` source via ``exec()``,
mirroring the isolation pattern from ``test_diff_module.py`` and
``test_memory_module_embedding.py``.  This avoids triggering the full
``tool_pool_api`` import chain (Supabase, FastMCP, etc.) which is not
needed for unit-testing a pure-Python regex/parser helper.
"""

import pytest


# ---------------------------------------------------------------------------
# 1. Load _extract_entity_references in isolation (exec pattern)
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    __file__.split("/tests/unit/")[0]
    + "/src/tool_pool_api/server/tool_modules/memory_module.py"
)

# Stubs for the lightweight dependencies the function may use.
import logging  # noqa: E402
import re  # noqa: E402
from typing import Any  # noqa: E402

_logger_stub = logging.getLogger("test_extract_entity_references")

_NAMESPACE: dict[str, Any] = {
    "__name__": "memory_module_isolated",
    "re": re,
    "logging": logging,
    "logger": _logger_stub,
}


def _load_extract_entity_references():
    """Extract ``_extract_entity_references`` from memory_module.py source.

    Follows the same exec()-based isolation pattern as
    ``test_diff_module._load_module_functions`` so the unit test does
    not pull in the full tool_pool_api dependency tree.

    Returns the loaded function.

    Raises:
        AttributeError: if ``_extract_entity_references`` is not defined
            in ``memory_module.py`` (this is the expected RED state).
    """
    import pathlib

    mod_path = pathlib.Path(_MODULE_PATH)
    source = mod_path.read_text()

    # Try both sync and async defs to be future-proof.
    marker_async = "async def _extract_entity_references("
    marker_sync = "def _extract_entity_references("

    idx_async = source.find(marker_async)
    idx_sync = source.find(marker_sync)

    if idx_async == -1 and idx_sync == -1:
        # RED state: function does not exist.  Surface an AttributeError
        # so the test failure is unambiguous about the missing symbol.
        raise AttributeError(
            "_extract_entity_references is not defined in memory_module.py. "
            "Expected a (possibly async) function with signature "
            "_extract_entity_references(markdown_text: str) -> list[dict]."
        )

    idx = idx_async if idx_async != -1 else idx_sync
    lines = source[idx:].split("\n")
    fn_lines: list[str] = []
    in_fn = False

    for line in lines:
        stripped = line.rstrip()
        if not stripped and not in_fn:
            continue
        if "def _extract_entity_references(" in line:
            in_fn = True
            fn_lines.append(stripped)
            continue
        if in_fn:
            if stripped == "":
                fn_lines.append("")
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0 and (
                stripped.startswith("async def ")
                or stripped.startswith("def ")
                or stripped.startswith("@")
                or stripped.startswith("# ---")
            ):
                break
            fn_lines.append(stripped)

    fn_source = "\n".join(fn_lines)
    exec(fn_source, _NAMESPACE)
    return _NAMESPACE["_extract_entity_references"]


# Module-level load — fails fast with AttributeError in the RED state.
_extract_entity_references = _load_extract_entity_references()


# ---------------------------------------------------------------------------
# 2. Constants for the contract under test
# ---------------------------------------------------------------------------

_VALID_ENTITY_TYPES: frozenset[str] = frozenset(
    {"skill", "client", "contact", "supplier", "user",
     "snapshot", "routine", "agent_result", "agent_metadata"}
)


# ---------------------------------------------------------------------------
# 3. Tests
# ---------------------------------------------------------------------------


class TestExtractEntityReferencesExists:
    """The function must be importable from memory_module.py."""

    def test_function_is_defined(self):
        """_extract_entity_references must be defined as a callable."""
        assert callable(_extract_entity_references), (
            "_extract_entity_references must be a callable"
        )


class TestExtractEntityReferencesBasic:
    """Basic extraction of single and multiple references."""

    def test_extracts_single_reference(self):
        """A markdown link with entity_type:entity_name is extracted."""
        text = "See [Acme profile](client:acme-corp) for details."
        refs = _extract_entity_references(text)
        assert len(refs) == 1
        assert refs[0]["entity_type"] == "client"
        assert refs[0]["entity_name"] == "acme-corp"

    def test_extracts_multiple_references(self):
        """All references in a multi-reference document are returned."""
        text = (
            "Contacts: [Acme](client:acme-corp) and [Beta](client:beta-co). "
            "Owner: [Maria](user:maria-silva)."
        )
        refs = _extract_entity_references(text)
        assert len(refs) == 3
        types = {(r["entity_type"], r["entity_name"]) for r in refs}
        assert ("client", "acme-corp") in types
        assert ("client", "beta-co") in types
        assert ("user", "maria-silva") in types

    def test_extracts_all_valid_entity_types(self):
        """Every canonical entity_type can be referenced."""
        for et in _VALID_ENTITY_TYPES:
            text = f"Ref: [x]({et}:sample-name)"
            refs = _extract_entity_references(text)
            assert len(refs) == 1, f"failed for entity_type={et}"
            assert refs[0]["entity_type"] == et
            assert refs[0]["entity_name"] == "sample-name"


class TestExtractEntityReferencesNoMatch:
    """Documents that contain no entity references."""

    def test_plain_text_returns_empty(self):
        """Plain prose with no entity links returns []."""
        text = "This is just normal text with no entity references."
        assert _extract_entity_references(text) == []

    def test_empty_string_returns_empty(self):
        """Empty input returns empty list."""
        assert _extract_entity_references("") == []

    def test_unrelated_markdown_links_ignored(self):
        """Markdown links that are NOT entity_type:entity_name are ignored."""
        text = "[google](https://example.com) and [anchor](#section-1)"
        assert _extract_entity_references(text) == []

    def test_unknown_entity_type_ignored(self):
        """entity_types outside the canonical set are ignored."""
        text = "Refs: [a](bogus:foo) and [b](unknown:bar)"
        assert _extract_entity_references(text) == []


class TestExtractEntityReferencesLabel:
    """The link label is preserved in the result."""

    def test_label_captured(self):
        """The visible label of the markdown link is captured."""
        text = "Contact [Acme Corporation](client:acme-corp) today."
        refs = _extract_entity_references(text)
        assert len(refs) == 1
        assert refs[0]["label"] == "Acme Corporation"

    def test_label_with_special_chars(self):
        """Labels with hyphens, dots, accents are preserved verbatim."""
        text = "[José's Bakery — est. 2010.](client:jose-bakery)"
        refs = _extract_entity_references(text)
        assert len(refs) == 1
        assert refs[0]["label"] == "José's Bakery — est. 2010."


class TestExtractEntityReferencesSpan:
    """A character span (start, end) is reported for each reference."""

    def test_span_points_into_source(self):
        """span[0] is start and span[1] is end of the reference in source."""
        text = "Before [Acme](client:acme) after."
        refs = _extract_entity_references(text)
        assert len(refs) == 1
        start, end = refs[0]["span"]
        assert text[start:end] == "[Acme](client:acme)"

    def test_span_in_full_document(self):
        """span is correct even when references appear mid-document."""
        text = (
            "Intro paragraph about the company.\n\n"
            "## Section\n"
            "More text here [Acme](client:acme).\n"
        )
        refs = _extract_entity_references(text)
        assert len(refs) == 1
        start, end = refs[0]["span"]
        assert text[start:end] == "[Acme](client:acme)"


class TestExtractEntityReferencesDedup:
    """Duplicate references are reported as the function decides."""

    def test_duplicates_preserved_or_deduped(self):
        """Result is a list — duplicates may be present or not, but
        both are acceptable so long as at least one occurrence is reported."""
        text = "[Acme](client:acme) and again [Acme](client:acme)."
        refs = _extract_entity_references(text)
        assert len(refs) >= 1
        assert all(r["entity_type"] == "client" for r in refs)
        assert all(r["entity_name"] == "acme" for r in refs)


class TestExtractEntityReferencesRealistic:
    """Realistic report-style markdown."""

    def test_weekly_report_extracts_references(self):
        """A typical weekly report surfaces its referenced entities."""
        text = (
            "# Weekly Report — W23\n\n"
            "Cliente: [Acme Corp](client:acme-corp)\n"
            "Contato principal: [Maria Silva](contact:maria-silva)\n"
            "Vendedor: [João](user:joao-santos)\n"
            "Snapshot: [Finance W22](snapshot:financeiro:semanal:2025-W22)\n"
        )
        refs = _extract_entity_references(text)
        assert len(refs) == 4
        names = {r["entity_name"] for r in refs}
        assert "acme-corp" in names
        assert "maria-silva" in names
        assert "joao-santos" in names
        assert "financeiro:semanal:2025-W22" in names
