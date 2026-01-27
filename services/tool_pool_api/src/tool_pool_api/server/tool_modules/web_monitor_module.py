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
        raise ToolError(f"Monitoring service error: {detail}") from exc
    except httpx.RequestError as exc:
        logger.exception("Monitoring service unreachable: %s", exc)
        raise ToolError(f"Monitoring service unreachable: {exc}") from exc


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
            """
**Purpose:** Monitor specific feature or flagship pages on a website using semantic search.

**When to use this tool:**
- User wants to track specific pages or features on a competitor's website
- User asks "what features does [website] have?"
- User wants to monitor changes to specific pages over time
- Business intelligence/competitive analysis requests

**Input format:**
- domain: (string) The website domain to monitor (e.g., "example.com")
- query: (string) Semantic search query describing the feature or page

**Examples:**
- "monitor pricing page on stripe.com"
- "what new features has github.com launched recently?"
- "track the careers page on google.com"""
        ),
    )(monitor_feature)

    mcp.tool(
        name="monitor_keywords",
        description=(
            """**Purpose:** Search a website for specific keywords or phrases.

**When to use this tool:**
- User wants to check if a website mentions certain keywords
- Content auditing or keyword presence checking
- Competitive keyword research
- Brand mention tracking on specific sites

**Input format:**
- domain: (string) Website domain to search
- keywords: (list of strings) Keywords to search for

**Examples:**
- "check if apple.com mentions 'privacy' and 'security'"
- "search for 'AI' and 'machine learning' on openai.com"
- "see if amazon.com mentions 'same-day delivery"""
        ),
    )(monitor_keywords)

    mcp.tool(
        name="monitor_company",
        description=(
            """**Purpose:** Track brand/company mentions across multiple websites.

**When to use this tool:**
- User wants to monitor brand reputation
- Track company mentions across the web
- Competitive intelligence for specific companies
- News/media monitoring for brands

**Input format:**
- company: (string) Company name to track
- domains: (optional list of strings) Specific domains to monitor (defaults to company's domain)

**Examples:**
- "monitor mentions of Tesla across automotive websites"
- "track OpenAI mentions on tech blogs"
- "monitor Starbucks brand mentions"""
        ),
    )(monitor_company)

    logger.info("[Web Monitor Module] Monitoring tools registered.")
    return ["monitor_feature", "monitor_keywords", "monitor_company"]
