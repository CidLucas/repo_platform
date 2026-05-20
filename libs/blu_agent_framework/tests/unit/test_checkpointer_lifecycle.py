"""
BL-003 — _CheckpointerAdapter lifecycle tests.

All tests are fully offline (no Redis required): the adapter is constructed
directly with mock inner objects.
"""

import pytest

from blu_agent_framework.checkpointer import _CheckpointerAdapter


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class _MockSyncCM:
    """Simulates a sync context-manager RedisSaver factory."""

    def __init__(self):
        self.entered = False
        self.exited = False
        self._saver = _MockSaver()

    def __enter__(self):
        self.entered = True
        return self._saver

    def __exit__(self, *args):
        self.exited = True


class _MockAsyncCM:
    """Simulates an async context-manager factory."""

    def __init__(self):
        self.entered = False
        self.exited = False
        self._saver = _MockSaver()

    async def __aenter__(self):
        self.entered = True
        return self._saver

    async def __aexit__(self, *args):
        self.exited = True


class _MockSaver:
    """Minimal inner saver with close / aclose tracking."""

    def __init__(self):
        self.closed = False
        self.aclosed = False

    def get_next_version(self):
        return 1

    def get_tuple(self, config):
        return None

    def put(self, *a, **kw):
        return None

    def close(self):
        self.closed = True

    async def aclose(self):
        self.aclosed = True


# ---------------------------------------------------------------------------
# Sync context-manager tests
# ---------------------------------------------------------------------------


def test_sync_ctx_manager_enter_returns_adapter():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    with adapter as cp:
        assert cp is adapter


def test_sync_ctx_manager_calls_close():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    with adapter:
        pass
    assert inner.closed is True


def test_close_delegates_to_inner_cm_exit():
    cm = _MockSyncCM()
    adapter = _CheckpointerAdapter(cm._saver, _cm=cm)
    adapter.close()
    assert cm.exited is True


def test_close_is_idempotent():
    """Second close() must not raise even if cm is gone."""
    cm = _MockSyncCM()
    adapter = _CheckpointerAdapter(cm._saver, _cm=cm)
    adapter.close()
    adapter.close()  # should not raise
    assert cm.exited is True


def test_close_without_cm_uses_inner_close():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)  # no _cm
    adapter.close()
    assert inner.closed is True


# ---------------------------------------------------------------------------
# Async context-manager tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_ctx_manager_enter_returns_adapter():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    async with adapter as cp:
        assert cp is adapter


@pytest.mark.asyncio
async def test_async_ctx_manager_calls_aclose():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    async with adapter:
        pass
    assert inner.aclosed is True


@pytest.mark.asyncio
async def test_aclose_delegates_to_inner_cm_aexit():
    cm = _MockAsyncCM()
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner, _cm=cm)
    await adapter.aclose()
    assert cm.exited is True


@pytest.mark.asyncio
async def test_aclose_falls_back_to_sync_exit_when_no_aexit():
    """If cm only has __exit__ (sync), aclose() must still call it."""
    cm = _MockSyncCM()
    adapter = _CheckpointerAdapter(cm._saver, _cm=cm)
    await adapter.aclose()
    assert cm.exited is True


@pytest.mark.asyncio
async def test_aclose_is_idempotent():
    cm = _MockAsyncCM()
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner, _cm=cm)
    await adapter.aclose()
    await adapter.aclose()  # should not raise
    assert cm.exited is True


@pytest.mark.asyncio
async def test_aclose_without_cm_uses_inner_aclose():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)  # no _cm
    await adapter.aclose()
    assert inner.aclosed is True


# ---------------------------------------------------------------------------
# Proxy / delegation tests
# ---------------------------------------------------------------------------


def test_get_next_version_delegated():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    assert adapter.get_next_version() == 1


@pytest.mark.asyncio
async def test_aget_tuple_wraps_sync_get_tuple():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    result = await adapter.aget_tuple({"configurable": {}})
    assert result is None  # _MockSaver.get_tuple returns None


@pytest.mark.asyncio
async def test_aput_wraps_sync_put():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    result = await adapter.aput()
    assert result is None  # _MockSaver.put returns None


def test_getattr_unknown_raises():
    inner = _MockSaver()
    adapter = _CheckpointerAdapter(inner)
    with pytest.raises(AttributeError):
        _ = adapter.nonexistent_attribute_xyz
