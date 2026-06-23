# tests/integration/conftest.py
"""Disable autouse DB cleanup fixture — these tests mock Supabase."""

import pytest


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — no real Supabase calls."""
    yield  # run the test, then nothing
