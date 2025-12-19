import asyncio
import os
import json
import pytest

from tools.monitoring_service import WebMonitorService


@pytest.mark.asyncio
async def test_monitor_feature_with_mocked_search(tmp_path, monkeypatch):
    domain = "example.com"
    state_dir = tmp_path.as_posix()
    svc = WebMonitorService(domain, state_dir=state_dir)

    async def fake_bm25(query_terms, pattern="*/*", topk=20, threshold=0.3, source="cc+sitemap"):
        # return fake hits
        return [
            {"url": "https://example.com/products/1", "relevance_score": 0.9, "head_data": {"title": "Product 1"}},
            {"url": "https://example.com/products/2", "relevance_score": 0.8, "head_data": {"title": "Product 2"}},
        ]

    monkeypatch.setattr(svc, "_bm25_search", fake_bm25)

    resp = await svc.monitor_feature("produtos em destaque")
    assert resp["summary"]["total_found"] == 2
    # state file created
    state_file = os.path.join(state_dir, f"{domain.replace('/', '_')}_known.json")
    assert os.path.exists(state_file)
    with open(state_file, "r") as f:
        data = json.load(f)
    assert "https://example.com/products/1" in data


@pytest.mark.asyncio
async def test_monitor_keywords_empty_when_no_search(tmp_path):
    domain = "example.org"
    state_dir = tmp_path.as_posix()
    svc = WebMonitorService(domain, state_dir=state_dir)

    async def fake_bm25_empty(*args, **kwargs):
        return []

    svc._bm25_search = fake_bm25_empty
    resp = await svc.monitor_keywords(["something random"])
    assert resp["summary"]["total_found"] == 0
