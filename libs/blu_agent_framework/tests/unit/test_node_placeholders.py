import pytest

from blu_agent_framework import nodes


@pytest.mark.asyncio
async def test_execute_tool_placeholder_fails_fast_by_default(monkeypatch):
    monkeypatch.delenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", raising=False)

    with pytest.raises(NotImplementedError, match="execute_tool"):
        await nodes.execute_tool_node({"tool_to_execute": "x", "tool_args": {}})


@pytest.mark.asyncio
async def test_execute_tool_placeholder_returns_sentinel_when_disabled(monkeypatch):
    monkeypatch.setenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", "0")

    result = await nodes.execute_tool_node({"tool_to_execute": "x", "tool_args": {}})

    assert result["_placeholder"] is True
    assert result["node"] == "execute_tool"


@pytest.mark.asyncio
async def test_execute_single_tool_placeholder_returns_sentinel_when_disabled(monkeypatch):
    monkeypatch.setenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", "false")

    result = await nodes.execute_single_tool_node({"tool_call": {"name": "abc"}})

    assert result["_placeholder"] is True
    assert result["node"] == "execute_single_tool"
    assert result["tool_results"][0]["_placeholder"] is True


@pytest.mark.asyncio
async def test_respond_placeholder_fails_fast_by_default(monkeypatch):
    monkeypatch.delenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", raising=False)

    with pytest.raises(NotImplementedError, match="respond"):
        await nodes.respond_node({"messages": []})


# --- BL-002: precedência config > env var ---


class _FakeConfig:
    def __init__(self, fail_on_placeholders: bool):
        self.fail_on_placeholders = fail_on_placeholders


def test_fail_on_placeholders_config_true_overrides_env(monkeypatch):
    """config.fail_on_placeholders=True deve falhar mesmo com env var desligada."""
    monkeypatch.setenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", "0")
    cfg = _FakeConfig(fail_on_placeholders=True)
    assert nodes._fail_on_placeholders(cfg) is True


def test_fail_on_placeholders_config_false_overrides_env(monkeypatch):
    """config.fail_on_placeholders=False deve retornar False mesmo com env var ligada."""
    monkeypatch.delenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", raising=False)
    cfg = _FakeConfig(fail_on_placeholders=False)
    assert nodes._fail_on_placeholders(cfg) is False


def test_fail_on_placeholders_env_wins_when_no_config(monkeypatch):
    """Sem config, env var controla o comportamento."""
    monkeypatch.setenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", "0")
    assert nodes._fail_on_placeholders() is False


def test_fail_on_placeholders_default_true_when_no_config_no_env(monkeypatch):
    """Sem config nem env var, padrão é True (fail-fast)."""
    monkeypatch.delenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", raising=False)
    assert nodes._fail_on_placeholders() is True


@pytest.mark.asyncio
async def test_execute_tool_respects_config_false(monkeypatch):
    """config.fail_on_placeholders=False via config object → sentinel, não exception."""
    monkeypatch.delenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", raising=False)
    # env default seria True, mas config deve sobrescrever
    # nodes.execute_tool_node não recebe config diretamente ainda —
    # este teste valida a função auxiliar que será usada pelo builder.
    cfg = _FakeConfig(fail_on_placeholders=False)
    assert nodes._fail_on_placeholders(cfg) is False

