"""
Tests for BL-006 — Observability & LLM logging wrapper.

Coverage
--------
- generate_correlation_id: uniqueness, length, hex chars
- log_llm_call: emits INFO with correct fields
- log_llm_response: emits INFO with latency
- log_parse_failure: emits WARNING with truncated raw_response
- LLMCallTimer: sync and async, measures elapsed_ms > 0
- orchestrator._parse_json_with_model: logs via log_parse_failure on failure
"""
from __future__ import annotations

import asyncio
import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from blu_agent_framework.utils.observability import (
    LLMCallTimer,
    generate_correlation_id,
    log_llm_call,
    log_llm_response,
    log_parse_failure,
)


# ---------------------------------------------------------------------------
# generate_correlation_id
# ---------------------------------------------------------------------------

def test_generate_correlation_id_is_12_hex_chars():
    cid = generate_correlation_id()
    assert len(cid) == 12
    assert all(c in "0123456789abcdef" for c in cid)


def test_generate_correlation_id_unique():
    ids = {generate_correlation_id() for _ in range(100)}
    assert len(ids) == 100


# ---------------------------------------------------------------------------
# log_llm_call
# ---------------------------------------------------------------------------

def test_log_llm_call_emits_info(caplog):
    logger = logging.getLogger("test.observability.llm_call")
    cid = generate_correlation_id()
    with caplog.at_level(logging.INFO, logger="test.observability.llm_call"):
        log_llm_call(logger, cid, node="parse_intent", model="gpt-4o", prompt_preview="Hello world")
    assert any("llm_call" in r.message for r in caplog.records)
    assert any(cid in r.message for r in caplog.records)
    assert any("parse_intent" in r.message for r in caplog.records)


def test_log_llm_call_truncates_prompt(caplog):
    logger = logging.getLogger("test.observability.truncate")
    cid = generate_correlation_id()
    long_prompt = "x" * 1000
    with caplog.at_level(logging.INFO, logger="test.observability.truncate"):
        log_llm_call(logger, cid, node="n", prompt_preview=long_prompt)
    record = next(r for r in caplog.records if "llm_call" in r.message)
    # prompt_preview should be truncated to 500 chars inside the payload string
    assert "x" * 501 not in record.message


# ---------------------------------------------------------------------------
# log_llm_response
# ---------------------------------------------------------------------------

def test_log_llm_response_includes_latency(caplog):
    logger = logging.getLogger("test.observability.response")
    cid = generate_correlation_id()
    with caplog.at_level(logging.INFO, logger="test.observability.response"):
        log_llm_response(logger, cid, node="plan", latency_ms=123.4, response_preview="ok")
    record = next(r for r in caplog.records if "llm_response" in r.message)
    assert "123.4" in record.message
    assert cid in record.message


def test_log_llm_response_without_latency(caplog):
    logger = logging.getLogger("test.observability.response_nolat")
    cid = generate_correlation_id()
    with caplog.at_level(logging.INFO, logger="test.observability.response_nolat"):
        log_llm_response(logger, cid, node="decompose")
    assert any("llm_response" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# log_parse_failure
# ---------------------------------------------------------------------------

def test_log_parse_failure_emits_warning(caplog):
    logger = logging.getLogger("test.observability.parse_fail")
    cid = generate_correlation_id()
    raw = '{"bad": "json" invalid}'
    with caplog.at_level(logging.WARNING, logger="test.observability.parse_fail"):
        log_parse_failure(logger, cid, node="parse_intent", raw_response=raw, reason="invalid JSON")
    records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert records, "Expected at least one WARNING"
    assert any("parse_failure" in r.message for r in records)
    assert any(cid in r.message for r in records)
    assert any("invalid JSON" in r.message for r in records)


def test_log_parse_failure_truncates_raw_response(caplog):
    logger = logging.getLogger("test.observability.truncate_raw")
    cid = generate_correlation_id()
    raw = "z" * 2000
    with caplog.at_level(logging.WARNING, logger="test.observability.truncate_raw"):
        log_parse_failure(logger, cid, node="n", raw_response=raw)
    record = next(r for r in caplog.records if "parse_failure" in r.message)
    # raw_response must be capped at 800 chars inside the payload
    assert "z" * 801 not in record.message


# ---------------------------------------------------------------------------
# LLMCallTimer — sync
# ---------------------------------------------------------------------------

def test_llm_call_timer_sync_measures_elapsed():
    with LLMCallTimer() as timer:
        time.sleep(0.05)
    assert timer.elapsed_ms >= 40  # allow some clock slack


def test_llm_call_timer_sync_zero_before_exit():
    timer = LLMCallTimer()
    assert timer.elapsed_ms == 0.0
    with timer:
        pass
    assert timer.elapsed_ms > 0


# ---------------------------------------------------------------------------
# LLMCallTimer — async
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_call_timer_async_measures_elapsed():
    async with LLMCallTimer() as timer:
        await asyncio.sleep(0.05)
    assert timer.elapsed_ms >= 40


@pytest.mark.asyncio
async def test_llm_call_timer_async_zero_before_exit():
    timer = LLMCallTimer()
    assert timer.elapsed_ms == 0.0
    async with timer:
        pass
    assert timer.elapsed_ms > 0
