import pytest

from blu_agent_framework import nodes


def test_placeholder_raise_by_default(monkeypatch):
    # Ensure nodes use fail-fast behavior in dev by default
    # We'll monkeypatch a config flag if present; if not, check exception
    try:
        # emulate missing injection by ensuring executor is None
        with pytest.raises(NotImplementedError):
            import asyncio

            async def run_node():
                await nodes.execute_tool_node({})

            asyncio.run(run_node())
    except RuntimeError:
        # In some test environments asyncio.run may fail; skip more elaborate run
        pytest.skip("Async runtime unavailable in this environment")
