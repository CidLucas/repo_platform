"""RED test for behavior B1 — remove dead code duplicates DUP-F1-01 and DUP-F1-02.

GOAL:
    The file ``memory_module.py`` must contain exactly ONE definition of each
    validation helper (``_validate_snapshot_frontmatter`` and
    ``_validate_snapshot_body``). Currently the file contains two copies of
    each (legacy + new), which is dead code duplication that must be removed.

BEHAVIOR:
    B1 — remove dead code DUP-F1-01 / DUP-F1-02 (duplicate definitions of
    ``_validate_snapshot_frontmatter`` and ``_validate_snapshot_body``).

AC (Acceptance Criteria):
    - Exactly one definition of ``_validate_snapshot_frontmatter`` exists.
    - Exactly one definition of ``_validate_snapshot_body`` exists.

DECISION:
    fix_and_extend
    Target file: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = (
    REPO_ROOT
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "server"
    / "tool_modules"
    / "memory_module.py"
)


def _count_definitions(source: str, function_name: str) -> int:
    """Count ``def <function_name>`` occurrences in *source*."""
    needle = f"def {function_name}"
    return source.count(needle)


class TestRemoveDeadCodeDuplicates:
    """The memory_module.py must not contain duplicate function definitions."""

    @pytest.fixture(scope="class")
    def source(self) -> str:
        assert TARGET_FILE.exists(), f"Target file missing: {TARGET_FILE}"
        return TARGET_FILE.read_text(encoding="utf-8")

    def test_single_definition_of__validate_snapshot_frontmatter(self, source: str) -> None:
        count = _count_definitions(source, "_validate_snapshot_frontmatter")
        assert count == 1, (
            f"Expected exactly 1 definition of `_validate_snapshot_frontmatter`, "
            f"found {count}. Duplicate definition (DUP-F1-01) must be removed."
        )

    def test_single_definition_of__validate_snapshot_body(self, source: str) -> None:
        count = _count_definitions(source, "_validate_snapshot_body")
        assert count == 1, (
            f"Expected exactly 1 definition of `_validate_snapshot_body`, "
            f"found {count}. Duplicate definition (DUP-F1-02) must be removed."
        )
