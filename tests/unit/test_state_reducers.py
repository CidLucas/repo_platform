import pytest
from langchain_core.messages import HumanMessage

from blu_agent_framework.state import (
    _cap_skill_results,
    _cap_tool_results,
    add_messages,
    create_initial_state,
)


def test_add_messages_cap_and_order():
    left = [HumanMessage(content=str(i)) for i in range(50)]
    right = [HumanMessage(content=str(i)) for i in range(20)]
    combined = add_messages(left, right)
    # _MAX_MESSAGES = 60 -> final list length 60 and contains most recent messages
    assert len(combined) == 60
    assert combined[-1].content == "19"


def test_cap_tool_results():
    left = [{"id": i} for i in range(20)]
    right = [{"id": i} for i in range(20, 40)]
    combined = _cap_tool_results(left, right)
    assert len(combined) == 30


def test_cap_skill_results():
    left = [{"id": i} for i in range(10)]
    right = [{"id": i} for i in range(10, 35)]
    combined = _cap_skill_results(left, right)
    assert len(combined) == 20


def test_create_initial_state_defaults():
    s = create_initial_state("sid", "cid")
    assert s["session_id"] == "sid"
    assert s["client_id"] == "cid"
    assert s["turn_count"] == 0
