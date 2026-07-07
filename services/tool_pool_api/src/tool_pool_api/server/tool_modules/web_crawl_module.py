"""Web crawl module — deep website crawling for content extraction and context building.

Unlike web_monitor_module (which detects page updates via an external service),
this module uses crawl4ai directly to extract full content from websites.
Used during onboarding (context pipeline) and by agents for research.
"""

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

_CRAWL_TIMEOUT = 150  # seconds per crawl session (deep crawl of ~30 pages takes 40-90s)
_BROWSER_ARGS = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


async def _reset_crawl4ai_playwright() -> None:
    """Clear crawl4ai's process-wide playwright singleton.

    crawl4ai's BrowserManager caches the playwright driver connection at class
    level (`_playwright_instance`). If a crawl is cancelled mid-flight (our
    wait_for timeout) or the driver dies, the cached connection is left broken
    and every subsequent chromium.launch in this process fails with
    TargetClosedError until the singleton is discarded.
    """
    try:
        from crawl4ai.browser_manager import BrowserManager
    except ImportError:
        return
    inst = getattr(BrowserManager, "_playwright_instance", None)
    if inst is not None:
        try:
            await inst.stop()
        except Exception:
            pass
        BrowserManager._playwright_instance = None


async def _run_crawl(url: str, max_depth: int, max_pages: int) -> list[dict[str, Any]]:
    """Core crawl logic. Returns list of {url, markdown, title} dicts."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
    except ImportError as e:
        raise ToolError(
            "crawl4ai is not available in this environment. "
            "Ensure the tool_pool_api image has been rebuilt with crawl4ai installed."
        ) from e
    from playwright._impl._errors import TargetClosedError

    browser_cfg = BrowserConfig(headless=True, extra_args=_BROWSER_ARGS)
    crawl_cfg = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=False,
        ),
        markdown_generator=None,  # use default markdown extractor
        word_count_threshold=50,   # skip pages with almost no content
        page_timeout=30000,        # 30s per page
    )

    async def _attempt() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            crawl_results = await asyncio.wait_for(
                crawler.arun(url=url, config=crawl_cfg),
                timeout=_CRAWL_TIMEOUT,
            )
            # arun with deep crawl returns a list
            if not isinstance(crawl_results, list):
                crawl_results = [crawl_results]

            for r in crawl_results:
                if not r.success:
                    logger.debug("Page failed: %s — %s", getattr(r, "url", "?"), getattr(r, "error_message", ""))
                    continue
                md = (r.markdown or "").strip()
                if not md:
                    continue
                results.append(
                    {
                        "url": r.url,
                        "title": (r.metadata or {}).get("title", ""),
                        "markdown": md,
                    }
                )
        return results

    try:
        return await _attempt()
    except TargetClosedError:
        # Poisoned playwright singleton from an earlier cancelled crawl —
        # reset and retry once with a fresh driver connection.
        logger.warning("[web_crawl] TargetClosedError — resetting crawl4ai playwright and retrying")
        await _reset_crawl4ai_playwright()
        return await _attempt()
    except (TimeoutError, asyncio.CancelledError):
        # The cancelled crawl may have left the shared driver broken;
        # reset so the NEXT call in this process starts clean.
        await _reset_crawl4ai_playwright()
        raise


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register web crawling tools using crawl4ai directly."""

    async def crawl_website(
        url: str,
        max_depth: int = 2,
        max_pages: int = 20,
    ) -> dict:
        """Crawl a website and return structured Markdown content from all pages.

        Args:
            url: Starting URL (e.g. "https://example.com"). http:// is added if missing.
            max_depth: BFS depth (1 = only root page, 2 = root + one level of links, etc.)
            max_pages: Maximum number of pages to crawl.

        Returns:
            {"pages": [...], "total_pages": N, "root_url": url}
        """
        if not url.strip():
            raise ToolError("url must not be empty.")
        if max_depth < 1 or max_depth > 5:
            raise ToolError("max_depth must be between 1 and 5.")
        if max_pages < 1 or max_pages > 100:
            raise ToolError("max_pages must be between 1 and 100.")

        url = _normalize_url(url)
        logger.info("[web_crawl] crawl_website url=%s depth=%d pages=%d", url, max_depth, max_pages)

        try:
            pages = await _run_crawl(url, max_depth=max_depth, max_pages=max_pages)
        except TimeoutError:
            raise ToolError(f"Crawl timed out after {_CRAWL_TIMEOUT}s for {url}.")
        except Exception as exc:
            logger.exception("crawl_website failed: %s", exc)
            raise ToolError(f"Crawl failed: {exc}") from exc

        return {
            "root_url": url,
            "total_pages": len(pages),
            "pages": pages,
        }

    async def extract_company_context(url: str) -> dict:
        """Deep-crawl a company website and return a single merged Markdown document
        summarising: what the company does, its products/services, target audience,
        tone of voice, and any pricing or contact information found.

        Designed for onboarding context pipelines and agent research tasks.

        Args:
            url: Company website URL or domain (e.g. "minhaempresa.com.br").

        Returns:
            {"markdown": str, "source_pages": [str], "root_url": str}
        """
        if not url.strip():
            raise ToolError("url must not be empty.")

        url = _normalize_url(url)
        logger.info("[web_crawl] extract_company_context url=%s", url)

        try:
            pages = await _run_crawl(url, max_depth=3, max_pages=30)
        except TimeoutError:
            raise ToolError(f"Crawl timed out after {_CRAWL_TIMEOUT}s for {url}.")
        except Exception as exc:
            logger.exception("extract_company_context failed: %s", exc)
            raise ToolError(f"Crawl failed: {exc}") from exc

        if not pages:
            return {
                "root_url": url,
                "source_pages": [],
                "markdown": "",
            }

        # Build a single merged Markdown document
        sections: list[str] = []
        source_urls: list[str] = []
        for page in pages:
            source_urls.append(page["url"])
            title = page["title"] or page["url"]
            sections.append(f"## {title}\n\nFonte: {page['url']}\n\n{page['markdown']}")

        merged = "\n\n---\n\n".join(sections)

        return {
            "root_url": url,
            "source_pages": source_urls,
            "markdown": merged,
        }

    mcp.tool(
        name="crawl_website",
        description=(
            """**Purpose:** Deep-crawl a website using BFS traversal and return structured Markdown content.

**When to use this tool:**
- Research: "What does this company offer?"
- Competitive analysis: crawl competitor sites for features/pricing
- Content extraction for knowledge base ingestion
- Any time you need more than just the homepage of a website

**Input:**
- url: Website URL or bare domain ("example.com")
- max_depth: BFS depth (default 2; 1=homepage only, 3=deep crawl)
- max_pages: Cap on pages crawled (default 20, max 100)

**Output:**
- pages: list of {url, title, markdown} for each successfully crawled page
- total_pages: number of pages returned

**Examples:**
- "crawl stripe.com pricing page" → url="stripe.com/pricing", max_depth=1
- "research everything about acme.com" → url="acme.com", max_depth=3, max_pages=50"""
        ),
    )(crawl_website)

    mcp.tool(
        name="extract_company_context",
        description=(
            """**Purpose:** Deep-crawl a company website and return a single merged Markdown document
describing the company: products/services, target audience, tone of voice, pricing, and contacts.

**When to use this tool:**
- Onboarding: build initial context document for a new client
- Agent research: understand a prospect or client before a meeting
- Any task requiring a comprehensive overview of a company from its website

**Input:**
- url: Company website URL or domain ("minhaempresa.com.br")

**Output:**
- markdown: merged Markdown document from all pages found
- source_pages: list of URLs crawled
- root_url: normalised starting URL

**Examples:**
- "get context for distribuidora.com.br"
- "research everything about client's website before the meeting"
- "build company profile from their site" """
        ),
    )(extract_company_context)

    logger.info("[Web Crawl Module] crawl_website + extract_company_context registered.")
    return ["crawl_website", "extract_company_context"]
