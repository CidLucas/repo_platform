"""
Integration-style tests: verify that after the BL-001 fix the orchestrator
private helpers correctly parse realistic LLM outputs via parse_first_json.

These tests use the internal _parse_json_with_model helper (new, replacing the
old _parse_json) and assert correct pydantic model instances are returned.

Key regression: the old _parse_json used text.rfind("}") which fails when the
LLM wraps the JSON in extra trailing text like:
    {"complexity": "simple"} Here is my explanation...
because rfind lands on the last "}" in the explanation, not in the JSON.
"""
import pytest

from blu_agent_framework.orchestrator import (
    DecomposeResult,
    ParseIntentResult,
    PlanResult,
    _parse_json_with_model,  # new function (replaces _parse_json)
)


class TestParseJsonWithModel:
    """Tests for _parse_json_with_model — the refactored orchestrator parser."""

    def test_plain_fenced_parse_intent(self):
        text = (
            "```json\n"
            '{"complexity": "simple", "involved_domains": ["sql"], "plan": []}\n'
            "```"
        )
        result = _parse_json_with_model(text, ParseIntentResult)
        assert result is not None
        assert result.complexity == "simple"
        assert result.involved_domains == ["sql"]

    def test_inline_noisy_parse_intent(self):
        """Old rfind parser would fail here because trailing text contains '}'."""
        text = (
            'The answer is: {"complexity": "complex", "involved_domains": ["rfq"]}'
            " which I classified as complex."
        )
        result = _parse_json_with_model(text, ParseIntentResult)
        assert result is not None
        assert result.complexity == "complex"

    def test_rfind_regression_case(self):
        """
        The old _parse_json used rfind('}') — this case has extra closing braces
        in the trailing text and would have caused a json.JSONDecodeError.
        """
        text = (
            '{"complexity": "uncertain", "involved_domains": [], "clarification": "Hmm?"}'
            " (closing brace} is a character in my explanation)"
        )
        result = _parse_json_with_model(text, ParseIntentResult)
        assert result is not None
        assert result.complexity == "uncertain"

    def test_decompose_result_fenced(self):
        text = (
            "```json\n"
            '{"sub_tasks": [{"id": "t1", "domain": "sql", "description": "query", "depends_on": []}]}\n'
            "```"
        )
        result = _parse_json_with_model(text, DecomposeResult)
        assert result is not None
        assert len(result.sub_tasks) == 1
        assert result.sub_tasks[0]["id"] == "t1"

    def test_returns_none_on_malformed(self):
        result = _parse_json_with_model("no json here", ParseIntentResult)
        assert result is None

    def test_returns_none_on_schema_mismatch(self):
        # Valid JSON but missing required fields → pydantic should reject
        result = _parse_json_with_model('{"unexpected_field": 1}', ParseIntentResult)
        assert result is None

    def test_plan_result_with_trailing_comma(self):
        text = (
            "```json\n"
            '{"plan": [{"id": "s1", "skill_slug": "data-analyst", "task": "run query",}]}\n'
            "```"
        )
        result = _parse_json_with_model(text, PlanResult)
        assert result is not None
        assert result.plan[0].skill_slug == "data-analyst"
