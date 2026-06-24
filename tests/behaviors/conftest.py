"""Conftest for behaviors tests.

Overrides the root conftest's autouse fixture that requires Supabase,
since behavior-level tests are source-analysis tests that don't need DB.
"""
import pytest


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """No-op override: behavior tests don't touch the database."""
    yield
