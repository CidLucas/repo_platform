"""
BL-005 — State reducer tests.

Moved from /tests/unit/test_state_reducers.py (repo root) to the
blu_agent_framework package so coverage is collected in the right scope.

Covers:
  - add_messages: append + rolling-window cap (_MAX_MESSAGES = 60)
  - _cap_tool_results: append + cap at 30
  - _cap_skill_results: append + cap at 20
  - create_initial_state: field defaults
  - edge cases: empty left, empty right, both empty, exact-cap boundary
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from blu_agent_framework.state import (
    _cap_skill_results,
    _cap_tool_results,
    add_messages,
    create_initial_state,
)

# ---------------------------------------------------------------------------
# add_messages
# ---------------------------------------------------------------------------

_MAX_MESSAGES = 60
_MAX_TOOL     = 30
_MAX_SKILL    = 20


class TestAddMessages:
    def test_append_and_cap(self):
        left  = [HumanMessage(content=str(i)) for i in range(50)]
        right = [HumanMessage(content=str(i)) for i in range(20)]
        combined = add_messages(left, right)
        assert len(combined) == _MAX_MESSAGES
        assert combined[-1].content == "19"

    def test_empty_left(self):
        right = [HumanMessage(content="x")]
        result = add_messages([], right)
        assert len(result) == 1
        assert result[0].content == "x"

    def test_empty_right(self):
        left = [HumanMessage(content="a"), HumanMessage(content="b")]
        result = add_messages(left, [])
        assert result == left

    def test_both_empty(self):
        assert add_messages([], []) == []

    def test_exact_cap_boundary(self):
        """left + right == _MAX_MESSAGES: no truncation."""
        left  = [HumanMessage(content=str(i)) for i in range(30)]
        right = [HumanMessage(content=str(i)) for i in range(30)]
        result = add_messages(left, right)
        assert len(result) == _MAX_MESSAGES

    def test_over_cap_keeps_most_recent(self):
        """When over cap, the tail (most recent) messages are kept."""
        left  = [HumanMessage(content=f"old-{i}") for i in range(60)]
        right = [HumanMessage(content=f"new-{i}") for i in range(10)]
        result = add_messages(left, right)
        assert len(result) == _MAX_MESSAGES
        # last 10 must be the "new" messages
        for i, msg in enumerate(result[-10:]):
            assert msg.content == f"new-{i}"

    def test_preserves_message_types(self):
        left  = [HumanMessage(content="hi")]
        right = [AIMessage(content="hello")]
        result = add_messages(left, right)
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)


# ---------------------------------------------------------------------------
# _cap_tool_results
# ---------------------------------------------------------------------------


class TestCapToolResults:
    def test_basic_cap(self):
        left  = [{"id": i} for i in range(20)]
        right = [{"id": i} for i in range(20, 40)]
        combined = _cap_tool_results(left, right)
        assert len(combined) == _MAX_TOOL

    def test_empty_left(self):
        right = [{"id": 0}]
        assert _cap_tool_results([], right) == [{"id": 0}]

    def test_empty_right(self):
        left = [{"id": 0}]
        assert _cap_tool_results(left, []) == [{"id": 0}]

    def test_both_empty(self):
        assert _cap_tool_results([], []) == []

    def test_exact_boundary_no_truncation(self):
        left  = [{"id": i} for i in range(15)]
        right = [{"id": i} for i in range(15)]
        assert len(_cap_tool_results(left, right)) == _MAX_TOOL

    def test_over_cap_keeps_most_recent(self):
        left  = [{"id": i, "tag": "old"} for i in range(30)]
        right = [{"id": i, "tag": "new"} for i in range(5)]
        result = _cap_tool_results(left, right)
        assert len(result) == _MAX_TOOL
        assert result[-1]["tag"] == "new"


# ---------------------------------------------------------------------------
# _cap_skill_results
# ---------------------------------------------------------------------------


class TestCapSkillResults:
    def test_basic_cap(self):
        left  = [{"id": i} for i in range(10)]
        right = [{"id": i} for i in range(10, 35)]
        combined = _cap_skill_results(left, right)
        assert len(combined) == _MAX_SKILL

    def test_empty_left(self):
        right = [{"id": 0}]
        assert _cap_skill_results([], right) == [{"id": 0}]

    def test_empty_right(self):
        left = [{"id": 0}]
        assert _cap_skill_results(left, []) == [{"id": 0}]

    def test_both_empty(self):
        assert _cap_skill_results([], []) == []

    def test_exact_boundary_no_truncation(self):
        left  = [{"id": i} for i in range(10)]
        right = [{"id": i} for i in range(10)]
        assert len(_cap_skill_results(left, right)) == _MAX_SKILL

    def test_over_cap_keeps_most_recent(self):
        left  = [{"id": i, "tag": "old"} for i in range(20)]
        right = [{"id": i, "tag": "new"} for i in range(5)]
        result = _cap_skill_results(left, right)
        assert len(result) == _MAX_SKILL
        assert result[-1]["tag"] == "new"


# ---------------------------------------------------------------------------
# create_initial_state
# ---------------------------------------------------------------------------


class TestCreateInitialState:
    def test_session_and_client_ids(self):
        s = create_initial_state("sid", "cid")
        assert s["session_id"] == "sid"
        assert s["client_id"] == "cid"

    def test_turn_count_starts_at_zero(self):
        s = create_initial_state("s", "c")
        assert s["turn_count"] == 0

    def test_messages_empty_list(self):
        s = create_initial_state("s", "c")
        assert s["messages"] == []

    def test_ended_false(self):
        s = create_initial_state("s", "c")
        assert s.get("ended") is False or s.get("ended") is None

    def test_extra_kwargs_merged(self):
        s = create_initial_state("s", "c", channel="whatsapp")
        assert s["channel"] == "whatsapp"
