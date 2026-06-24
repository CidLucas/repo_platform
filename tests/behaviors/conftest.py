"""Conftest for behavior tests — overrides root conftest cleanup.

Behavior tests are unit-level source-inspection tests that don't need
Supabase connectivity. The root conftest has an autouse cleanup fixture
that requires a Supabase client; this override prevents that fixture from
running.
"""

import pytest


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure unit tests, no DB needed."""
    yield
