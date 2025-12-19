"""Monitoring module exposing crawl4ai-backed monitoring tools."""

import logging
from typing import Sequence

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.core.config import get_settings
from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

settings = get_settings()
_BASE_URL = (settings.TOOLS_SERVICE_BASE_URL or "http://tools:8000").rstrip("/")
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def _build_monitor_params(
    overrides: Sequence[tuple[str, str]],
    domain: str | None = None,
) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    if domain:
        params.append(("domain", domain))
    params.extend(overrides)
    return params


async def _call_tools_service(path: str, params: list[tuple[str, str]]) -> dict:
    url = f"{_BASE_URL}{path}"
    logger.debug("Calling monitoring service %s with params %s", url, params)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or exc.response.reason_phrase
        logger.warning("Monitoring service returned %s: %s", exc.response.status_code, detail)
        raise ToolError("Monitoring service error: %s" % detail) from exc
    except httpx.RequestError as exc:
        logger.exception("Monitoring service unreachable: %s", exc)
        raise ToolError("Monitoring service unreachable: %s" % exc) from exc


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register monitoring tools that proxy to the external tools service."""

    async def monitor_feature(domain: str, query: str) -> dict:
        if not query.strip():
            raise ToolError("Query must contain at least one character.")
        params = _build_monitor_params([("query", query)], domain)
        return await _call_tools_service("/monitor-feature", params)

    async def monitor_keywords(domain: str, keywords: list[str]) -> dict:
        if not keywords:
            raise ToolError("Provide at least one keyword to monitor.")
        overrides = [("keywords", kw) for kw in keywords]
        params = _build_monitor_params(overrides, domain)
        return await _call_tools_service("/monitor-keywords", params)

    async def monitor_company(company: str, domains: list[str] | None = None) -> dict:
        if not company.strip():
            raise ToolError("Company name must not be empty.")
        overrides = [("company", company)]
        if domains:
            overrides.extend(("domains", d) for d in domains)
        params = _build_monitor_params(overrides)
        return await _call_tools_service("/monitor-company", params)

    mcp.tool(
        name="monitor_feature",
        description=(
            "Monitor feature/flagship pages for a domain using semantic crawl4ai search. "
            "Params: domain, query"
        ),
    )(monitor_feature)

    mcp.tool(
        name="monitor_keywords",
        description=(
            "Search a domain for the supplied keywords or phrases. "
            "Params: domain, keywords (list of strings)"
        ),
    )(monitor_keywords)

    mcp.tool(
        name="monitor_company",
        description=(
            "Track brand/company mentions across domains. "
            "Params: company, domains (optional list; defaults to the provided company domain)"
        ),
    )(monitor_company)

    logger.info("[Web Monitor Module] Monitoring tools registered.")
    return ["monitor_feature", "monitor_keywords", "monitor_company"]
