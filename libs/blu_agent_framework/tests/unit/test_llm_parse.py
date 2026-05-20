"""
Unit tests for blu_agent_framework.utils.llm_parse.parse_first_json.

Covers:
- fenced JSON (```json ... ```)
- inline JSON (plain {...} in text)
- noisy prefix/suffix around valid JSON
- multiple JSON objects (must return first)
- malformed / unparseable input returns None
- empty / None-like input returns None
"""
import pytest

from blu_agent_framework.utils.llm_parse import parse_first_json


class TestFencedJson:
    def test_plain_fenced_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = parse_first_json(text)
        assert result == {"key": "value"}

    def test_fenced_block_no_lang_tag(self):
        text = '```\n{"foo": 1}\n```'
        result = parse_first_json(text)
        assert result == {"foo": 1}

    def test_fenced_block_with_surrounding_text(self):
        text = "Here is the plan:\n```json\n{\"step\": \"analyze\"}\n```\nDone."
        result = parse_first_json(text)
        assert result == {"step": "analyze"}

    def test_fenced_block_with_nested_object(self):
        text = '```json\n{"outer": {"inner": 42}}\n```'
        result = parse_first_json(text)
        assert result == {"outer": {"inner": 42}}


class TestInlineJson:
    def test_plain_inline_json(self):
        result = parse_first_json('{"action": "done"}')
        assert result == {"action": "done"}

    def test_inline_with_prefix_text(self):
        text = 'The answer is: {"complexity": "simple", "plan": []}'
        result = parse_first_json(text)
        assert result is not None
        assert result["complexity"] == "simple"

    def test_inline_with_suffix_text(self):
        text = '{"ok": true} and more text here'
        result = parse_first_json(text)
        assert result == {"ok": True}


class TestNoisyInput:
    def test_noisy_prefix_and_suffix(self):
        text = "LLM output blah blah\n\n{\"result\": 99}\n\nExtra junk."
        result = parse_first_json(text)
        assert result is not None
        assert result["result"] == 99

    def test_trailing_comma_cleanup(self):
        # Trailing comma before closing brace is invalid JSON but common in LLM output
        text = '{"a": 1, "b": 2,}'
        result = parse_first_json(text)
        assert result is not None
        assert result["a"] == 1

    def test_trailing_comma_in_nested(self):
        text = '{"items": [1, 2,]}'
        result = parse_first_json(text)
        assert result is not None
        assert result["items"] == [1, 2]


class TestMultipleJsonObjects:
    def test_returns_first_json_object(self):
        text = '{"first": 1} some text {"second": 2}'
        result = parse_first_json(text)
        assert result == {"first": 1}

    def test_fenced_first_then_inline(self):
        text = '```json\n{"fenced": true}\n```\n{"inline": true}'
        result = parse_first_json(text)
        assert result == {"fenced": True}


class TestMalformedInput:
    def test_returns_none_on_unclosed_brace(self):
        result = parse_first_json('{"unclosed": "brace"')
        assert result is None

    def test_returns_none_on_empty_string(self):
        result = parse_first_json("")
        assert result is None

    def test_returns_none_on_plain_text(self):
        result = parse_first_json("no json here at all")
        assert result is None

    def test_returns_none_on_array_only(self):
        # parse_first_json targets objects ({...}), not bare arrays
        result = parse_first_json("[1, 2, 3]")
        assert result is None

    def test_returns_none_on_invalid_values(self):
        # undefined is not valid JSON
        result = parse_first_json('{"key": undefined}')
        assert result is None


class TestOrchestatorShapes:
    """Verify parse_first_json handles realistic orchestrator LLM output shapes."""

    def test_parse_intent_fenced(self):
        text = (
            "Sure, here's the classification:\n"
            "```json\n"
            '{"complexity": "simple", "involved_domains": ["sql"], "plan": []}\n'
            "```"
        )
        result = parse_first_json(text)
        assert result is not None
        assert result["complexity"] == "simple"
        assert result["involved_domains"] == ["sql"]

    def test_decompose_result_inline(self):
        text = '{"sub_tasks": ["fetch data", "analyze"], "reasoning": "two steps needed"}'
        result = parse_first_json(text)
        assert result is not None
        assert "sub_tasks" in result

    def test_plan_result_with_trailing_comma(self):
        text = (
            "```json\n"
            '{"steps": [{"skill_slug": "sql", "task": "run query",}]}\n'
            "```"
        )
        result = parse_first_json(text)
        assert result is not None
        assert result["steps"][0]["skill_slug"] == "sql"
