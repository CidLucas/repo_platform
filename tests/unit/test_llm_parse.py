import pytest

from blu_agent_framework.utils.llm_parse import parse_first_json


def test_fenced_json_parsing():
    text = "Here is the plan:\n```json\n{\"steps\": [ {\"id\": 1} ] }\n```\nThanks"
    parsed = parse_first_json(text)
    assert isinstance(parsed, dict)
    assert "steps" in parsed


def test_inline_json_parsing():
    text = "Result: {\"status\": \"ok\"} end"
    parsed = parse_first_json(text)
    assert parsed == {"status": "ok"}


def test_noisy_json_with_markdown():
    text = "Response:\n```\nSome text\n{\"k\": \"v\"}\n```\nOther"
    parsed = parse_first_json(text)
    assert parsed == {"k": "v"}


def test_multiple_json_objects():
    text = "First: {\"a\": 1} Second: {\"b\": 2}"
    parsed = parse_first_json(text)
    assert parsed == {"a": 1}


def test_malformed_json_returns_none():
    text = "Broken: {\"a\":, }"
    parsed = parse_first_json(text)
    assert parsed is None
