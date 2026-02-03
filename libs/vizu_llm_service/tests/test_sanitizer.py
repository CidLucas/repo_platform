import pytest

from vizu_llm_service.client import sanitize_observation


def make_msg(i):
    return {
        "content": f"msg{i}",
        "id": str(i),
        "response_metadata": {"model": "m", "done": True, "total_duration": 1234, "extra": "x"},
    }


def test_sanitize_observation_truncates_and_removes_internal():
    obs = {
        "messages": [make_msg(i) for i in range(10)],
        "_internal_context": {"id": "secret"},
        "safe_context": {"nome_empresa": "Acme"},
    }

    sanitized = sanitize_observation(obs, max_messages=3)

    assert "_internal_context" not in sanitized
    assert isinstance(sanitized.get("messages"), list)
    assert len(sanitized["messages"]) == 3
    # messages are last 3
    assert sanitized["messages"][0]["content"] == "msg7"
    # response_metadata trimmed
    rm = sanitized["messages"][0]["response_metadata"]
    assert rm.get("model") == "m"
    assert "total_duration" not in rm
    assert "extra" not in rm


def test_sanitize_non_mapping_returns_input():
    x = "not a mapping"
    assert sanitize_observation(x, max_messages=2) == x
