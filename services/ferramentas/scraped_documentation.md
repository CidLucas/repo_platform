# Documentação de Crawl4ai Documentation

## Fonte: https://docs.crawl4ai.com/

> **Note** : If you're looking for the old documentation, you can access it [here](https://old.docs.crawl4ai.com).

## 🎯 New: Adaptive Web Crawling

Crawl4AI now features intelligent adaptive crawling that knows when to stop! Using advanced information foraging algorithms, it determines when sufficient information has been gathered to answer your query.
[Learn more about Adaptive Crawling →](https://docs.crawl4ai.com/core/adaptive-crawling/)

## Quick Start

Here's a quick example to show you how easy it is to use Crawl4AI with its asynchronous capabilities:

```
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    # Create an instance of AsyncWebCrawler
    async with AsyncWebCrawler() as crawler:
        # Run the crawler on a URL
        result = await crawler.arun(url="https://crawl4ai.com")

        # Print the extracted content
        print(result.markdown)

# Run the async main function
asyncio.run(main())
Copy
```

---

## Video Tutorial

---

## What Does Crawl4AI Do?

Crawl4AI is a feature-rich crawler and scraper that aims to:

1. **Generate Clean Markdown** : Perfect for RAG pipelines or direct ingestion into LLMs.
2. **Structured Extraction** : Parse repeated patterns with CSS, XPath, or LLM-based extraction.
3. **Advanced Browser Control** : Hooks, proxies, stealth modes, session re-use—fine-grained control.
4. **High Performance** : Parallel crawling, chunk-based extraction, real-time use cases.
5. **Open Source** : No forced API keys, no paywalls—everyone can access their data.
   **Core Philosophies** : - **Democratize Data** : Free to use, transparent, and highly configurable.

- **LLM Friendly** : Minimally processed, well-structured text, images, and metadata, so AI models can easily consume it.

---

## Documentation Structure

To help you get started, we’ve organized our docs into clear sections:

- **Setup & Installation**
  Basic instructions to install Crawl4AI via pip or Docker.
- **Quick Start**
  A hands-on introduction showing how to do your first crawl, generate Markdown, and do a simple extraction.
- **Core**
  Deeper guides on single-page crawling, advanced browser/crawler parameters, content filtering, and caching.
- **Advanced**
  Explore link & media handling, lazy loading, hooking & authentication, proxies, session management, and more.
- **Extraction**
  Detailed references for no-LLM (CSS, XPath) vs. LLM-based strategies, chunking, and clustering approaches.
- **API Reference**
  Find the technical specifics of each class and method, including `AsyncWebCrawler`, `arun()`, and `CrawlResult`.

Throughout these sections, you’ll find code samples you can **copy-paste** into your environment. If something is missing or unclear, raise an issue or PR.

---

## How You Can Support

- **Star & Fork**: If you find Crawl4AI helpful, star the repo on GitHub or fork it to add your own features.
- **File Issues** : Encounter a bug or missing feature? Let us know by filing an issue, so we can improve.
- **Pull Requests** : Whether it’s a small fix, a big feature, or better docs—contributions are always welcome.
- **Join Discord** : Come chat about web scraping, crawling tips, or AI workflows with the community.
- **Spread the Word** : Mention Crawl4AI in your blog posts, talks, or on social media.

**Our mission** : to empower everyone—students, researchers, entrepreneurs, data scientists—to access, parse, and shape the world’s data with speed, cost-efficiency, and creative freedom.

---

> **Note** : If you're looking for the old documentation, you can access it [here](https://old.docs.crawl4ai.com).

## 🎯 New: Adaptive Web Crawling

Crawl4AI now features intelligent adaptive crawling that knows when to stop! Using advanced information foraging algorithms, it determines when sufficient information has been gathered to answer your query.
[Learn more about Adaptive Crawling →](https://docs.crawl4ai.com/core/adaptive-crawling/)

## Quick Start

Here's a quick example to show you how easy it is to use Crawl4AI with its asynchronous capabilities:

```
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    # Create an instance of AsyncWebCrawler
    async with AsyncWebCrawler() as crawler:
        # Run the crawler on a URL
        result = await crawler.arun(url="https://crawl4ai.com")

        # Print the extracted content
        print(result.markdown)

# Run the async main function
asyncio.run(main())
Copy
```

---

## Video Tutorial

---

## What Does Crawl4AI Do?

Crawl4AI is a feature-rich crawler and scraper that aims to:

1. **Generate Clean Markdown** : Perfect for RAG pipelines or direct ingestion into LLMs.
2. **Structured Extraction** : Parse repeated patterns with CSS, XPath, or LLM-based extraction.
3. **Advanced Browser Control** : Hooks, proxies, stealth modes, session re-use—fine-grained control.
4. **High Performance** : Parallel crawling, chunk-based extraction, real-time use cases.
5. **Open Source** : No forced API keys, no paywalls—everyone can access their data.
   **Core Philosophies** : - **Democratize Data** : Free to use, transparent, and highly configurable.

- **LLM Friendly** : Minimally processed, well-structured text, images, and metadata, so AI models can easily consume it.

---

## Documentation Structure

To help you get started, we’ve organized our docs into clear sections:

- **Setup & Installation**
  Basic instructions to install Crawl4AI via pip or Docker.
- **Quick Start**
  A hands-on introduction showing how to do your first crawl, generate Markdown, and do a simple extraction.
- **Core**
  Deeper guides on single-page crawling, advanced browser/crawler parameters, content filtering, and caching.
- **Advanced**
  Explore link & media handling, lazy loading, hooking & authentication, proxies, session management, and more.
- **Extraction**
  Detailed references for no-LLM (CSS, XPath) vs. LLM-based strategies, chunking, and clustering approaches.
- **API Reference**
  Find the technical specifics of each class and method, including `AsyncWebCrawler`, `arun()`, and `CrawlResult`.

Throughout these sections, you’ll find code samples you can **copy-paste** into your environment. If something is missing or unclear, raise an issue or PR.

---

## How You Can Support

- **Star & Fork**: If you find Crawl4AI helpful, star the repo on GitHub or fork it to add your own features.
- **File Issues** : Encounter a bug or missing feature? Let us know by filing an issue, so we can improve.
- **Pull Requests** : Whether it’s a small fix, a big feature, or better docs—contributions are always welcome.
- **Join Discord** : Come chat about web scraping, crawling tips, or AI workflows with the community.
- **Spread the Word** : Mention Crawl4AI in your blog posts, talks, or on social media.

**Our mission** : to empower everyone—students, researchers, entrepreneurs, data scientists—to access, parse, and shape the world’s data with speed, cost-efficiency, and creative freedom.

---

## Quick Links

- **[GitHub Repo](https://github.com/unclecode/crawl4ai)**
- **[Installation Guide](https://docs.crawl4ai.com/core/installation/)**
- **[Quick Start](https://docs.crawl4ai.com/core/quickstart/)**
- **[API Reference](https://docs.crawl4ai.com/api/async-webcrawler/)**
- **[Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)**

Thank you for joining me on this journey. Let’s keep building an **open, democratic** approach to data extraction and AI together.
Happy Crawling!
— _Unclecode, Founder & Maintainer of Crawl4AI_

#### On this page

- [🎯 New: Adaptive Web Crawling](https://docs.crawl4ai.com/#new-adaptive-web-crawling)
- [Quick Start](https://docs.crawl4ai.com/#quick-start)
- [Video Tutorial](https://docs.crawl4ai.com/#video-tutorial)
- [What Does Crawl4AI Do?](https://docs.crawl4ai.com/#what-does-crawl4ai-do)
- [Documentation Structure](https://docs.crawl4ai.com/#documentation-structure)
- [How You Can Support](https://docs.crawl4ai.com/#how-you-can-support)
- [Quick Links](https://docs.crawl4ai.com/#quick-links)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/api/arun

```
{"detail":"Not Found"}
```

---

## Fonte: https://docs.crawl4ai.com/api/c4a-script-reference

```
{"detail":"Not Found"}
```

---

## Fonte: https://docs.crawl4ai.com/api/arun_many

```
{"detail":"Not Found"}
```

---

## Fonte: https://docs.crawl4ai.com/api/async-webcrawler

```
{"detail":"Not Found"}
```

---

## Fonte: https://docs.crawl4ai.com/advanced/network-console-capture

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/network-console-capture/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - Network & Console Capture
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Network Requests & Console Message Capturing](https://docs.crawl4ai.com/advanced/network-console-capture/#network-requests-console-message-capturing)
- [Configuration](https://docs.crawl4ai.com/advanced/network-console-capture/#configuration)
- [Example Usage](https://docs.crawl4ai.com/advanced/network-console-capture/#example-usage)
- [Captured Data Structure](https://docs.crawl4ai.com/advanced/network-console-capture/#captured-data-structure)
- [Key Benefits](https://docs.crawl4ai.com/advanced/network-console-capture/#key-benefits)
- [Use Cases](https://docs.crawl4ai.com/advanced/network-console-capture/#use-cases)

# Network Requests & Console Message Capturing

Crawl4AI can capture all network requests and browser console messages during a crawl, which is invaluable for debugging, security analysis, or understanding page behavior.

## Configuration

To enable network and console capturing, use these configuration options:

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

# Enable both network request capture and console message capture
config = CrawlerRunConfig(
    capture_network_requests=True,  # Capture all network requests and responses
    capture_console_messages=True   # Capture all browser console output
)
Copy
```

## Example Usage

```
import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Enable both network request capture and console message capture
    config = CrawlerRunConfig(
        capture_network_requests=True,
        capture_console_messages=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=config
        )

        if result.success:
            # Analyze network requests
            if result.network_requests:
                print(f"Captured {len(result.network_requests)} network events")

                # Count request types
                request_count = len([r for r in result.network_requests if r.get("event_type") == "request"])
                response_count = len([r for r in result.network_requests if r.get("event_type") == "response"])
                failed_count = len([r for r in result.network_requests if r.get("event_type") == "request_failed"])

                print(f"Requests: {request_count}, Responses: {response_count}, Failed: {failed_count}")

                # Find API calls
                api_calls = [r for r in result.network_requests
                            if r.get("event_type") == "request" and "api" in r.get("url", "")]
                if api_calls:
                    print(f"Detected {len(api_calls)} API calls:")
                    for call in api_calls[:3]:  # Show first 3
                        print(f"  - {call.get('method')} {call.get('url')}")

            # Analyze console messages
            if result.console_messages:
                print(f"Captured {len(result.console_messages)} console messages")

                # Group by type
                message_types = {}
                for msg in result.console_messages:
                    msg_type = msg.get("type", "unknown")
                    message_types[msg_type] = message_types.get(msg_type, 0) + 1

                print("Message types:", message_types)

                # Show errors (often the most important)
                errors = [msg for msg in result.console_messages if msg.get("type") == "error"]
                if errors:
                    print(f"Found {len(errors)} console errors:")
                    for err in errors[:2]:  # Show first 2
                        print(f"  - {err.get('text', '')[:100]}")

            # Export all captured data to a file for detailed analysis
            with open("network_capture.json", "w") as f:
                json.dump({
                    "url": result.url,
                    "network_requests": result.network_requests or [],
                    "console_messages": result.console_messages or []
                }, f, indent=2)

            print("Exported detailed capture data to network_capture.json")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

## Captured Data Structure

### Network Requests

The `result.network_requests` contains a list of dictionaries, each representing a network event with these common fields:
Field | Description
---|---
`event_type` | Type of event: `"request"`, `"response"`, or `"request_failed"`
`url` | The URL of the request
`timestamp` | Unix timestamp when the event was captured

#### Request Event Fields

```
{
  "event_type": "request",
  "url": "https://example.com/api/data.json",
  "method": "GET",
  "headers": {"User-Agent": "...", "Accept": "..."},
  "post_data": "key=value&otherkey=value",
  "resource_type": "fetch",
  "is_navigation_request": false,
  "timestamp": 1633456789.123
}
Copy
```

#### Response Event Fields

```
{
  "event_type": "response",
  "url": "https://example.com/api/data.json",
  "status": 200,
  "status_text": "OK",
  "headers": {"Content-Type": "application/json", "Cache-Control": "..."},
  "from_service_worker": false,
  "request_timing": {"requestTime": 1234.56, "receiveHeadersEnd": 1234.78},
  "timestamp": 1633456789.456
}
Copy
```

#### Failed Request Event Fields

```
{
  "event_type": "request_failed",
  "url": "https://example.com/missing.png",
  "method": "GET",
  "resource_type": "image",
  "failure_text": "net::ERR_ABORTED 404",
  "timestamp": 1633456789.789
}
Copy
```

### Console Messages

The `result.console_messages` contains a list of dictionaries, each representing a console message with these common fields:
Field | Description
---|---
`type` | Message type: `"log"`, `"error"`, `"warning"`, `"info"`, etc.
`text` | The message text
`timestamp` | Unix timestamp when the message was captured

#### Console Message Example

```
{
  "type": "error",
  "text": "Uncaught TypeError: Cannot read property 'length' of undefined",
  "location": "https://example.com/script.js:123:45",
  "timestamp": 1633456790.123
}
Copy
```

## Key Benefits

- **Full Request Visibility** : Capture all network activity including:
- Requests (URLs, methods, headers, post data)
- Responses (status codes, headers, timing)
- Failed requests (with error messages)
- **Console Message Access** : View all JavaScript console output:
- Log messages
- Warnings
- Errors with stack traces
- Developer debugging information
- **Debugging Power** : Identify issues such as:
- Failed API calls or resource loading
- JavaScript errors affecting page functionality
- CORS or other security issues
- Hidden API endpoints and data flows
- **Security Analysis** : Detect:
- Unexpected third-party requests
- Data leakage in request payloads
- Suspicious script behavior
- **Performance Insights** : Analyze:
- Request timing data
- Resource loading patterns
- Potential bottlenecks

## Use Cases

1. **API Discovery** : Identify hidden endpoints and data flows in single-page applications
2. **Debugging** : Track down JavaScript errors affecting page functionality
3. **Security Auditing** : Detect unwanted third-party requests or data leakage
4. **Performance Analysis** : Identify slow-loading resources
5. **Ad/Tracker Analysis** : Detect and catalog advertising or tracking calls

This capability is especially valuable for complex sites with heavy JavaScript, single-page applications, or when you need to understand the exact communication happening between a browser and servers.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/network-console-capture/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/network-console-capture/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/network-console-capture/)

ESC to close

#### On this page

- [Configuration](https://docs.crawl4ai.com/advanced/network-console-capture/#configuration)
- [Example Usage](https://docs.crawl4ai.com/advanced/network-console-capture/#example-usage)
- [Captured Data Structure](https://docs.crawl4ai.com/advanced/network-console-capture/#captured-data-structure)
- [Network Requests](https://docs.crawl4ai.com/advanced/network-console-capture/#network-requests)
- [Request Event Fields](https://docs.crawl4ai.com/advanced/network-console-capture/#request-event-fields)
- [Response Event Fields](https://docs.crawl4ai.com/advanced/network-console-capture/#response-event-fields)
- [Failed Request Event Fields](https://docs.crawl4ai.com/advanced/network-console-capture/#failed-request-event-fields)
- [Console Messages](https://docs.crawl4ai.com/advanced/network-console-capture/#console-messages)
- [Console Message Example](https://docs.crawl4ai.com/advanced/network-console-capture/#console-message-example)
- [Key Benefits](https://docs.crawl4ai.com/advanced/network-console-capture/#key-benefits)
- [Use Cases](https://docs.crawl4ai.com/advanced/network-console-capture/#use-cases)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/proxy-security

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/proxy-security/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - Proxy & Security
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Proxy](https://docs.crawl4ai.com/advanced/proxy-security/#proxy)
- [Basic Proxy Setup](https://docs.crawl4ai.com/advanced/proxy-security/#basic-proxy-setup)
- [Authenticated Proxy](https://docs.crawl4ai.com/advanced/proxy-security/#authenticated-proxy)
- [Rotating Proxies](https://docs.crawl4ai.com/advanced/proxy-security/#rotating-proxies)

# Proxy

## Basic Proxy Setup

Simple proxy configuration with `BrowserConfig`:

```
from crawl4ai.async_configs import BrowserConfig

# Using HTTP proxy
browser_config = BrowserConfig(proxy_config={"server": "http://proxy.example.com:8080"})
async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(url="https://example.com")

# Using SOCKS proxy
browser_config = BrowserConfig(proxy_config={"server": "socks5://proxy.example.com:1080"})
async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(url="https://example.com")
Copy
```

## Authenticated Proxy

Use an authenticated proxy with `BrowserConfig`:

```
from crawl4ai.async_configs import BrowserConfig

browser_config = BrowserConfig(proxy_config={
    "server": "http://[host]:[port]",
    "username": "[username]",
    "password": "[password]",
})
async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(url="https://example.com")
Copy
```

## Rotating Proxies

Example using a proxy rotation service dynamically:

```
import re
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    RoundRobinProxyStrategy,
)
import asyncio
from crawl4ai import ProxyConfig
async def main():
    # Load proxies and create rotation strategy
    proxies = ProxyConfig.from_env()
    #eg: export PROXIES="ip1:port1:username1:password1,ip2:port2:username2:password2"
    if not proxies:
        print("No proxies found in environment. Set PROXIES env variable!")
        return

    proxy_strategy = RoundRobinProxyStrategy(proxies)

    # Create configs
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        proxy_rotation_strategy=proxy_strategy
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        urls = ["https://httpbin.org/ip"] * (len(proxies) * 2)  # Test each proxy twice

        print("\n📈 Initializing crawler with proxy rotation...")
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("\n🚀 Starting batch crawl with proxy rotation...")
            results = await crawler.arun_many(
                urls=urls,
                config=run_config
            )
            for result in results:
                if result.success:
                    ip_match = re.search(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}', result.html)
                    current_proxy = run_config.proxy_config if run_config.proxy_config else None

                    if current_proxy and ip_match:
                        print(f"URL {result.url}")
                        print(f"Proxy {current_proxy.server} -> Response IP: {ip_match.group(0)}")
                        verified = ip_match.group(0) == current_proxy.ip
                        if verified:
                            print(f"✅ Proxy working! IP matches: {current_proxy.ip}")
                        else:
                            print("❌ Proxy failed or IP mismatch!")
                    print("---")

asyncio.run(main())
Copy
```

Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/proxy-security/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/proxy-security/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/proxy-security/)

ESC to close

#### On this page

- [Basic Proxy Setup](https://docs.crawl4ai.com/advanced/proxy-security/#basic-proxy-setup)
- [Authenticated Proxy](https://docs.crawl4ai.com/advanced/proxy-security/#authenticated-proxy)
- [Rotating Proxies](https://docs.crawl4ai.com/advanced/proxy-security/#rotating-proxies)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/pdf-parsing

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/pdf-parsing/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - PDF Parsing
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [PDF Processing Strategies](https://docs.crawl4ai.com/advanced/pdf-parsing/#pdf-processing-strategies)
- [PDFCrawlerStrategy](https://docs.crawl4ai.com/advanced/pdf-parsing/#pdfcrawlerstrategy)
- [PDFContentScrapingStrategy](https://docs.crawl4ai.com/advanced/pdf-parsing/#pdfcontentscrapingstrategy)

# PDF Processing Strategies

Crawl4AI provides specialized strategies for handling and extracting content from PDF files. These strategies allow you to seamlessly integrate PDF processing into your crawling workflows, whether the PDFs are hosted online or stored locally.

## `PDFCrawlerStrategy`

### Overview

`PDFCrawlerStrategy` is an implementation of `AsyncCrawlerStrategy` designed specifically for PDF documents. Instead of interpreting the input URL as an HTML webpage, this strategy treats it as a pointer to a PDF file. It doesn't perform deep crawling or HTML parsing itself but rather prepares the PDF source for a dedicated PDF scraping strategy. Its primary role is to identify the PDF source (web URL or local file) and pass it along the processing pipeline in a way that `AsyncWebCrawler` can handle.

### When to Use

Use `PDFCrawlerStrategy` when you need to: - Process PDF files using the `AsyncWebCrawler`. - Handle PDFs from both web URLs (e.g., `https://example.com/document.pdf`) and local file paths (e.g., `file:///path/to/your/document.pdf`). - Integrate PDF content extraction into a unified `CrawlResult` object, allowing consistent handling of PDF data alongside web page data.

### Key Methods and Their Behavior

- **`__init__(self, logger: AsyncLogger = None)`**:
  - Initializes the strategy.
  - `logger`: An optional `AsyncLogger` instance (from `crawl4ai.async_logger`) for logging purposes.
- **`async crawl(self, url: str, **kwargs) -> AsyncCrawlResponse`\*\*:
  - This method is called by the `AsyncWebCrawler` during the `arun` process.
  - It takes the `url` (which should point to a PDF) and creates a minimal `AsyncCrawlResponse`.
  - The `html` attribute of this response is typically empty or a placeholder, as the actual PDF content processing is deferred to the `PDFContentScrapingStrategy` (or a similar PDF-aware scraping strategy).
  - It sets `response_headers` to indicate "application/pdf" and `status_code` to 200.
- **`async close(self)`**:
  - A method for cleaning up any resources used by the strategy. For `PDFCrawlerStrategy`, this is usually minimal.
- **`async __aenter__(self)`/`async __aexit__(self, exc_type, exc_val, exc_tb)`** :
  - Enables asynchronous context management for the strategy, allowing it to be used with `async with`.

### Example Usage

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.processors.pdf import PDFCrawlerStrategy, PDFContentScrapingStrategy

async def main():
    # Initialize the PDF crawler strategy
    pdf_crawler_strategy = PDFCrawlerStrategy()

    # PDFCrawlerStrategy is typically used in conjunction with PDFContentScrapingStrategy
    # The scraping strategy handles the actual PDF content extraction
    pdf_scraping_strategy = PDFContentScrapingStrategy()
    run_config = CrawlerRunConfig(scraping_strategy=pdf_scraping_strategy)

    async with AsyncWebCrawler(crawler_strategy=pdf_crawler_strategy) as crawler:
        # Example with a remote PDF URL
        pdf_url = "https://arxiv.org/pdf/2310.06825.pdf" # A public PDF from arXiv

        print(f"Attempting to process PDF: {pdf_url}")
        result = await crawler.arun(url=pdf_url, config=run_config)

        if result.success:
            print(f"Successfully processed PDF: {result.url}")
            print(f"Metadata Title: {result.metadata.get('title', 'N/A')}")
            # Further processing of result.markdown, result.media, etc.
            # would be done here, based on what PDFContentScrapingStrategy extracts.
            if result.markdown and hasattr(result.markdown, 'raw_markdown'):
                print(f"Extracted text (first 200 chars): {result.markdown.raw_markdown[:200]}...")
            else:
                print("No markdown (text) content extracted.")
        else:
            print(f"Failed to process PDF: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### Pros and Cons

**Pros:** - Enables `AsyncWebCrawler` to handle PDF sources directly using familiar `arun` calls. - Provides a consistent interface for specifying PDF sources (URLs or local paths). - Abstracts the source handling, allowing a separate scraping strategy to focus on PDF content parsing.
**Cons:** - Does not perform any PDF data extraction itself; it strictly relies on a compatible scraping strategy (like `PDFContentScrapingStrategy`) to process the PDF. - Has limited utility on its own; most of its value comes from being paired with a PDF-specific content scraping strategy.

---

## `PDFContentScrapingStrategy`

### Overview

`PDFContentScrapingStrategy` is an implementation of `ContentScrapingStrategy` designed to extract text, metadata, and optionally images from PDF documents. It is intended to be used in conjunction with a crawler strategy that can provide it with a PDF source, such as `PDFCrawlerStrategy`. This strategy uses the `NaivePDFProcessorStrategy` internally to perform the low-level PDF parsing.

### When to Use

Use `PDFContentScrapingStrategy` when your `AsyncWebCrawler` (often configured with `PDFCrawlerStrategy`) needs to: - Extract textual content page by page from a PDF document. - Retrieve standard metadata embedded within the PDF (e.g., title, author, subject, creation date, page count). - Optionally, extract images contained within the PDF pages. These images can be saved to a local directory or made available for further processing. - Produce a `ScrapingResult` that can be converted into a `CrawlResult`, making PDF content accessible in a manner similar to HTML web content (e.g., text in `result.markdown`, metadata in `result.metadata`).

### Key Configuration Attributes

When initializing `PDFContentScrapingStrategy`, you can configure its behavior using the following attributes: - **`extract_images: bool = False`**: If`True` , the strategy will attempt to extract images from the PDF. - **`save_images_locally: bool = False`**: If`True` (and `extract_images` is also `True`), extracted images will be saved to disk in the `image_save_dir`. If `False`, image data might be available in another form (e.g., base64, depending on the underlying processor) but not saved as separate files by this strategy. - **`image_save_dir: str = None`**: Specifies the directory where extracted images should be saved if`save_images_locally` is `True`. If `None`, a default or temporary directory might be used. - **`batch_size: int = 4`**: Defines how many PDF pages are processed in a single batch. This can be useful for managing memory when dealing with very large PDF documents. -**`logger: AsyncLogger = None`**: An optional`AsyncLogger` instance for logging.

### Key Methods and Their Behavior

- **`__init__(self, save_images_locally: bool = False, extract_images: bool = False, image_save_dir: str = None, batch_size: int = 4, logger: AsyncLogger = None)`**:
  - Initializes the strategy with configurations for image handling, batch processing, and logging. It sets up an internal `NaivePDFProcessorStrategy` instance which performs the actual PDF parsing.
- **`scrap(self, url: str, html: str, **params) -> ScrapingResult`\*\*:
  - This is the primary synchronous method called by the crawler (via `ascrap`) to process the PDF.
  - `url`: The path or URL to the PDF file (provided by `PDFCrawlerStrategy` or similar).
  - `html`: Typically an empty string when used with `PDFCrawlerStrategy`, as the content is a PDF, not HTML.
  - It first ensures the PDF is accessible locally (downloads it to a temporary file if `url` is remote).
  - It then uses its internal PDF processor to extract text, metadata, and images (if configured).
  - The extracted information is compiled into a `ScrapingResult` object:
    - `cleaned_html`: Contains an HTML-like representation of the PDF, where each page's content is often wrapped in a `<div>` with page number information.
    - `media`: A dictionary where `media["images"]` will contain information about extracted images if `extract_images` was `True`.
    - `links`: A dictionary where `links["urls"]` can contain URLs found within the PDF content.
    - `metadata`: A dictionary holding PDF metadata (e.g., title, author, num_pages).
- **`async ascrap(self, url: str, html: str, **kwargs) -> ScrapingResult`\*\*:
  - The asynchronous version of `scrap`. Under the hood, it typically runs the synchronous `scrap` method in a separate thread using `asyncio.to_thread` to avoid blocking the event loop.
- **`_get_pdf_path(self, url: str) -> str`**:
  - A private helper method to manage PDF file access. If the `url` is remote (http/https), it downloads the PDF to a temporary local file and returns its path. If `url` indicates a local file (`file://` or a direct path), it resolves and returns the local path.

### Example Usage

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.processors.pdf import PDFCrawlerStrategy, PDFContentScrapingStrategy
import os # For creating image directory

async def main():
    # Define the directory for saving extracted images
    image_output_dir = "./my_pdf_images"
    os.makedirs(image_output_dir, exist_ok=True)

    # Configure the PDF content scraping strategy
    # Enable image extraction and specify where to save them
    pdf_scraping_cfg = PDFContentScrapingStrategy(
        extract_images=True,
        save_images_locally=True,
        image_save_dir=image_output_dir,
        batch_size=2 # Process 2 pages at a time for demonstration
    )

    # The PDFCrawlerStrategy is needed to tell AsyncWebCrawler how to "crawl" a PDF
    pdf_crawler_cfg = PDFCrawlerStrategy()

    # Configure the overall crawl run
    run_cfg = CrawlerRunConfig(
        scraping_strategy=pdf_scraping_cfg # Use our PDF scraping strategy
    )

    # Initialize the crawler with the PDF-specific crawler strategy
    async with AsyncWebCrawler(crawler_strategy=pdf_crawler_cfg) as crawler:
        pdf_url = "https://arxiv.org/pdf/2310.06825.pdf" # Example PDF

        print(f"Starting PDF processing for: {pdf_url}")
        result = await crawler.arun(url=pdf_url, config=run_cfg)

        if result.success:
            print("\n--- PDF Processing Successful ---")
            print(f"Processed URL: {result.url}")

            print("\n--- Metadata ---")
            for key, value in result.metadata.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")

            if result.markdown and hasattr(result.markdown, 'raw_markdown'):
                print(f"\n--- Extracted Text (Markdown Snippet) ---")
                print(result.markdown.raw_markdown[:500].strip() + "...")
            else:
                print("\nNo text (markdown) content extracted.")

            if result.media and result.media.get("images"):
                print(f"\n--- Image Extraction ---")
                print(f"Extracted {len(result.media['images'])} image(s).")
                for i, img_info in enumerate(result.media["images"][:2]): # Show info for first 2 images
                    print(f"  Image {i+1}:")
                    print(f"    Page: {img_info.get('page')}")
                    print(f"    Format: {img_info.get('format', 'N/A')}")
                    if img_info.get('path'):
                        print(f"    Saved at: {img_info.get('path')}")
            else:
                print("\nNo images were extracted (or extract_images was False).")
        else:
            print(f"\n--- PDF Processing Failed ---")
            print(f"Error: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### Pros and Cons

**Pros:** - Provides a comprehensive way to extract text, metadata, and (optionally) images from PDF documents. - Handles both remote PDFs (via URL) and local PDF files. - Configurable image extraction allows saving images to disk or accessing their data. - Integrates smoothly with the `CrawlResult` object structure, making PDF-derived data accessible in a way consistent with web-scraped data. - The `batch_size` parameter can help in managing memory consumption when processing large or numerous PDF pages.
**Cons:** - Extraction quality and performance can vary significantly depending on the PDF's complexity, encoding, and whether it's image-based (scanned) or text-based. - Image extraction can be resource-intensive (both CPU and disk space if `save_images_locally` is true). - Relies on `NaivePDFProcessorStrategy` internally, which might have limitations with very complex layouts, encrypted PDFs, or forms compared to more sophisticated PDF parsing libraries. Scanned PDFs will not yield text unless an OCR step is performed (which is not part of this strategy by default). - Link extraction from PDFs can be basic and depends on how hyperlinks are embedded in the document.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/pdf-parsing/)

ESC to close

#### On this page

- [PDFCrawlerStrategy](https://docs.crawl4ai.com/advanced/pdf-parsing/#pdfcrawlerstrategy)
- [Overview](https://docs.crawl4ai.com/advanced/pdf-parsing/#overview)
- [When to Use](https://docs.crawl4ai.com/advanced/pdf-parsing/#when-to-use)
- [Key Methods and Their Behavior](https://docs.crawl4ai.com/advanced/pdf-parsing/#key-methods-and-their-behavior)
- [Example Usage](https://docs.crawl4ai.com/advanced/pdf-parsing/#example-usage)
- [Pros and Cons](https://docs.crawl4ai.com/advanced/pdf-parsing/#pros-and-cons)
- [PDFContentScrapingStrategy](https://docs.crawl4ai.com/advanced/pdf-parsing/#pdfcontentscrapingstrategy)
- [Overview](https://docs.crawl4ai.com/advanced/pdf-parsing/#overview_1)
- [When to Use](https://docs.crawl4ai.com/advanced/pdf-parsing/#when-to-use_1)
- [Key Configuration Attributes](https://docs.crawl4ai.com/advanced/pdf-parsing/#key-configuration-attributes)
- [Key Methods and Their Behavior](https://docs.crawl4ai.com/advanced/pdf-parsing/#key-methods-and-their-behavior_1)
- [Example Usage](https://docs.crawl4ai.com/advanced/pdf-parsing/#example-usage_1)
- [Pros and Cons](https://docs.crawl4ai.com/advanced/pdf-parsing/#pros-and-cons_1)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/session-management

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/session-management/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - Session Management
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Session Management](https://docs.crawl4ai.com/advanced/session-management/#session-management)
- [Basic Session Usage](https://docs.crawl4ai.com/advanced/session-management/#basic-session-usage)
- [Dynamic Content with Sessions](https://docs.crawl4ai.com/advanced/session-management/#dynamic-content-with-sessions)
- [Example 1: Basic Session-Based Crawling](https://docs.crawl4ai.com/advanced/session-management/#example-1-basic-session-based-crawling)
- [Advanced Technique 1: Custom Execution Hooks](https://docs.crawl4ai.com/advanced/session-management/#advanced-technique-1-custom-execution-hooks)
- [Advanced Technique 2: Integrated JavaScript Execution and Waiting](https://docs.crawl4ai.com/advanced/session-management/#advanced-technique-2-integrated-javascript-execution-and-waiting)

# Session Management

Session management in Crawl4AI is a powerful feature that allows you to maintain state across multiple requests, making it particularly suitable for handling complex multi-step crawling tasks. It enables you to reuse the same browser tab (or page object) across sequential actions and crawls, which is beneficial for:

- **Performing JavaScript actions before and after crawling.**
- **Executing multiple sequential crawls faster** without needing to reopen tabs or allocate memory repeatedly.

**Note:** This feature is designed for sequential workflows and is not suitable for parallel operations.

---

#### Basic Session Usage

Use `BrowserConfig` and `CrawlerRunConfig` to maintain state with a `session_id`:

```
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async with AsyncWebCrawler() as crawler:
    session_id = "my_session"

    # Define configurations
    config1 = CrawlerRunConfig(
        url="https://example.com/page1", session_id=session_id
    )
    config2 = CrawlerRunConfig(
        url="https://example.com/page2", session_id=session_id
    )

    # First request
    result1 = await crawler.arun(config=config1)

    # Subsequent request using the same session
    result2 = await crawler.arun(config=config2)

    # Clean up when done
    await crawler.crawler_strategy.kill_session(session_id)
Copy
```

---

#### Dynamic Content with Sessions

Here's an example of crawling GitHub commits across multiple pages while preserving session state:

```
from crawl4ai.async_configs import CrawlerRunConfig
from crawl4ai import JsonCssExtractionStrategy
from crawl4ai.cache_context import CacheMode

async def crawl_dynamic_content():
    url = "https://github.com/microsoft/TypeScript/commits/main"
    session_id = "wait_for_session"
    all_commits = []

    js_next_page = """
    const commits = document.querySelectorAll('li[data-testid="commit-row-item"] h4');
    if (commits.length > 0) {
        window.lastCommit = commits[0].textContent.trim();
    }
    const button = document.querySelector('a[data-testid="pagination-next-button"]');
    if (button) {button.click(); console.log('button clicked') }
    """

    wait_for = """() => {
        const commits = document.querySelectorAll('li[data-testid="commit-row-item"] h4');
        if (commits.length === 0) return false;
        const firstCommit = commits[0].textContent.trim();
        return firstCommit !== window.lastCommit;
    }"""

    schema = {
        "name": "Commit Extractor",
        "baseSelector": "li[data-testid='commit-row-item']",
        "fields": [
            {
                "name": "title",
                "selector": "h4 a",
                "type": "text",
                "transform": "strip",
            },
        ],
    }
    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)


    browser_config = BrowserConfig(
        verbose=True,
        headless=False,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for page in range(3):
            crawler_config = CrawlerRunConfig(
                session_id=session_id,
                css_selector="li[data-testid='commit-row-item']",
                extraction_strategy=extraction_strategy,
                js_code=js_next_page if page > 0 else None,
                wait_for=wait_for if page > 0 else None,
                js_only=page > 0,
                cache_mode=CacheMode.BYPASS,
                capture_console_messages=True,
            )

            result = await crawler.arun(url=url, config=crawler_config)

            if result.console_messages:
                print(f"Page {page + 1} console messages:", result.console_messages)

            if result.extracted_content:
                # print(f"Page {page + 1} result:", result.extracted_content)
                commits = json.loads(result.extracted_content)
                all_commits.extend(commits)
                print(f"Page {page + 1}: Found {len(commits)} commits")
            else:
                print(f"Page {page + 1}: No content extracted")

        print(f"Successfully crawled {len(all_commits)} commits across 3 pages")
        # Clean up session
        await crawler.crawler_strategy.kill_session(session_id)
Copy
```

---

## Example 1: Basic Session-Based Crawling

A simple example using session-based crawling:

```
import asyncio
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.cache_context import CacheMode

async def basic_session_crawl():
    async with AsyncWebCrawler() as crawler:
        session_id = "dynamic_content_session"
        url = "https://example.com/dynamic-content"

        for page in range(3):
            config = CrawlerRunConfig(
                url=url,
                session_id=session_id,
                js_code="document.querySelector('.load-more-button').click();" if page > 0 else None,
                css_selector=".content-item",
                cache_mode=CacheMode.BYPASS
            )

            result = await crawler.arun(config=config)
            print(f"Page {page + 1}: Found {result.extracted_content.count('.content-item')} items")

        await crawler.crawler_strategy.kill_session(session_id)

asyncio.run(basic_session_crawl())
Copy
```

This example shows: 1. Reusing the same `session_id` across multiple requests. 2. Executing JavaScript to load more content dynamically. 3. Properly closing the session to free resources.

---

## Advanced Technique 1: Custom Execution Hooks

> Warning: You might feel confused by the end of the next few examples 😅, so make sure you are comfortable with the order of the parts before you start this.
> Use custom hooks to handle complex scenarios, such as waiting for content to load dynamically:

```
async def advanced_session_crawl_with_hooks():
    first_commit = ""

    async def on_execution_started(page):
        nonlocal first_commit
        try:
            while True:
                await page.wait_for_selector("li.commit-item h4")
                commit = await page.query_selector("li.commit-item h4")
                commit = await commit.evaluate("(element) => element.textContent").strip()
                if commit and commit != first_commit:
                    first_commit = commit
                    break
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Warning: New content didn't appear: {e}")

    async with AsyncWebCrawler() as crawler:
        session_id = "commit_session"
        url = "https://github.com/example/repo/commits/main"
        crawler.crawler_strategy.set_hook("on_execution_started", on_execution_started)

        js_next_page = """document.querySelector('a.pagination-next').click();"""

        for page in range(3):
            config = CrawlerRunConfig(
                url=url,
                session_id=session_id,
                js_code=js_next_page if page > 0 else None,
                css_selector="li.commit-item",
                js_only=page > 0,
                cache_mode=CacheMode.BYPASS
            )

            result = await crawler.arun(config=config)
            print(f"Page {page + 1}: Found {len(result.extracted_content)} commits")

        await crawler.crawler_strategy.kill_session(session_id)

asyncio.run(advanced_session_crawl_with_hooks())
Copy
```

This technique ensures new content loads before the next action.

---

## Advanced Technique 2: Integrated JavaScript Execution and Waiting

Combine JavaScript execution and waiting logic for concise handling of dynamic content:

```
async def integrated_js_and_wait_crawl():
    async with AsyncWebCrawler() as crawler:
        session_id = "integrated_session"
        url = "https://github.com/example/repo/commits/main"

        js_next_page_and_wait = """
        (async () => {
            const getCurrentCommit = () => document.querySelector('li.commit-item h4').textContent.trim();
            const initialCommit = getCurrentCommit();
            document.querySelector('a.pagination-next').click();
            while (getCurrentCommit() === initialCommit) {
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        })();
        """

        for page in range(3):
            config = CrawlerRunConfig(
                url=url,
                session_id=session_id,
                js_code=js_next_page_and_wait if page > 0 else None,
                css_selector="li.commit-item",
                js_only=page > 0,
                cache_mode=CacheMode.BYPASS
            )

            result = await crawler.arun(config=config)
            print(f"Page {page + 1}: Found {len(result.extracted_content)} commits")

        await crawler.crawler_strategy.kill_session(session_id)

asyncio.run(integrated_js_and_wait_crawl())
Copy
```

---

#### Common Use Cases for Sessions

1. **Authentication Flows** : Login and interact with secured pages.
2. **Pagination Handling** : Navigate through multiple pages.
3. **Form Submissions** : Fill forms, submit, and process results.
4. **Multi-step Processes** : Complete workflows that span multiple actions.
5. **Dynamic Content Navigation** : Handle JavaScript-rendered or event-triggered content.
   Page Copy
   Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/session-management/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/session-management/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/session-management/)

ESC to close

#### On this page

- [Basic Session Usage](https://docs.crawl4ai.com/advanced/session-management/#basic-session-usage)
- [Dynamic Content with Sessions](https://docs.crawl4ai.com/advanced/session-management/#dynamic-content-with-sessions)
- [Example 1: Basic Session-Based Crawling](https://docs.crawl4ai.com/advanced/session-management/#example-1-basic-session-based-crawling)
- [Advanced Technique 1: Custom Execution Hooks](https://docs.crawl4ai.com/advanced/session-management/#advanced-technique-1-custom-execution-hooks)
- [Advanced Technique 2: Integrated JavaScript Execution and Waiting](https://docs.crawl4ai.com/advanced/session-management/#advanced-technique-2-integrated-javascript-execution-and-waiting)
- [Common Use Cases for Sessions](https://docs.crawl4ai.com/advanced/session-management/#common-use-cases-for-sessions)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/identity-based-crawling

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/identity-based-crawling/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - Identity Based Crawling
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Preserve Your Identity with Crawl4AI](https://docs.crawl4ai.com/advanced/identity-based-crawling/#preserve-your-identity-with-crawl4ai)
- [1. Managed Browsers: Your Digital Identity Solution](https://docs.crawl4ai.com/advanced/identity-based-crawling/#1-managed-browsers-your-digital-identity-solution)
- [3. Using Managed Browsers in Crawl4AI](https://docs.crawl4ai.com/advanced/identity-based-crawling/#3-using-managed-browsers-in-crawl4ai)
- [4. Magic Mode: Simplified Automation](https://docs.crawl4ai.com/advanced/identity-based-crawling/#4-magic-mode-simplified-automation)
- [5. Comparing Managed Browsers vs. Magic Mode](https://docs.crawl4ai.com/advanced/identity-based-crawling/#5-comparing-managed-browsers-vs-magic-mode)
- [6. Using the BrowserProfiler Class](https://docs.crawl4ai.com/advanced/identity-based-crawling/#6-using-the-browserprofiler-class)
- [7. Locale, Timezone, and Geolocation Control](https://docs.crawl4ai.com/advanced/identity-based-crawling/#7-locale-timezone-and-geolocation-control)
- [8. Summary](https://docs.crawl4ai.com/advanced/identity-based-crawling/#8-summary)

# Preserve Your Identity with Crawl4AI

Crawl4AI empowers you to navigate and interact with the web using your **authentic digital identity** , ensuring you’re recognized as a human and not mistaken for a bot. This tutorial covers:

1. **Managed Browsers** – The recommended approach for persistent profiles and identity-based crawling.
2. **Magic Mode** – A simplified fallback solution for quick automation without persistent identity.

---

## 1. Managed Browsers: Your Digital Identity Solution

**Managed Browsers** let developers create and use **persistent browser profiles**. These profiles store local storage, cookies, and other session data, letting you browse as your **real self** —complete with logins, preferences, and cookies.

### Key Benefits

- **Authentic Browsing Experience** : Retain session data and browser fingerprints as though you’re a normal user.
- **Effortless Configuration** : Once you log in or solve CAPTCHAs in your chosen data directory, you can re-run crawls without repeating those steps.
- **Empowered Data Access** : If you can see the data in your own browser, you can automate its retrieval with your genuine identity.

---

Below is a **partial update** to your **Managed Browsers** tutorial, specifically the section about **creating a user-data directory** using **Playwright’s Chromium** binary rather than a system-wide Chrome/Edge. We’ll show how to **locate** that binary and launch it with a `--user-data-dir` argument to set up your profile. You can then point `BrowserConfig.user_data_dir` to that folder for subsequent crawls.

---

### Creating a User Data Directory (Command-Line Approach via Playwright)

If you installed Crawl4AI (which installs Playwright under the hood), you already have a Playwright-managed Chromium on your system. Follow these steps to launch that **Chromium** from your command line, specifying a **custom** data directory:

1. **Find** the Playwright Chromium binary: - On most systems, installed browsers go under a `~/.cache/ms-playwright/` folder or similar path.

- To see an overview of installed browsers, run:

```
python -m playwright install --dry-run
Copy
```

or

```
playwright install --dry-run
Copy
```

(depending on your environment). This shows where Playwright keeps Chromium.

- For instance, you might see a path like:

```
~/.cache/ms-playwright/chromium-1234/chrome-linux/chrome
Copy
```

on Linux, or a corresponding folder on macOS/Windows.

2. **Launch** the Playwright Chromium binary with a **custom** user-data directory:

```
# Linux example
~/.cache/ms-playwright/chromium-1234/chrome-linux/chrome \
    --user-data-dir=/home/<you>/my_chrome_profile
Copy
```

```
# macOS example (Playwright’s internal binary)
~/Library/Caches/ms-playwright/chromium-1234/chrome-mac/Chromium.app/Contents/MacOS/Chromium \
    --user-data-dir=/Users/<you>/my_chrome_profile
Copy
```

```
# Windows example (PowerShell/cmd)
"C:\Users\<you>\AppData\Local\ms-playwright\chromium-1234\chrome-win\chrome.exe" ^
    --user-data-dir="C:\Users\<you>\my_chrome_profile"
Copy
```

**Replace** the path with the actual subfolder indicated in your `ms-playwright` cache structure.

- This **opens** a fresh Chromium with your new or existing data folder.
- **Log into** any sites or configure your browser the way you want.
- **Close** when done—your profile data is saved in that folder.

3. **Use** that folder in **`BrowserConfig.user_data_dir`**:

```
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

browser_config = BrowserConfig(
    headless=True,
    use_managed_browser=True,
    user_data_dir="/home/<you>/my_chrome_profile",
    browser_type="chromium"
)
Copy
```

- Next time you run your code, it reuses that folder—**preserving** your session data, cookies, local storage, etc.

---

## 3. Using Managed Browsers in Crawl4AI

Once you have a data directory with your session data, pass it to **`BrowserConfig`**:

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def main():
    # 1) Reference your persistent data directory
    browser_config = BrowserConfig(
        headless=True,             # 'True' for automated runs
        verbose=True,
        use_managed_browser=True,  # Enables persistent browser strategy
        browser_type="chromium",
        user_data_dir="/path/to/my-chrome-profile"
    )

    # 2) Standard crawl config
    crawl_config = CrawlerRunConfig(
        wait_for="css:.logged-in-content"
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="https://example.com/private", config=crawl_config)
        if result.success:
            print("Successfully accessed private data with your identity!")
        else:
            print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### Workflow

1. **Login** externally (via CLI or your normal Chrome with `--user-data-dir=...`).
2. **Close** that browser.
3. **Use** the same folder in `user_data_dir=` in Crawl4AI.
4. **Crawl** – The site sees your identity as if you’re the same user who just logged in.

---

## 4. Magic Mode: Simplified Automation

If you **don’t** need a persistent profile or identity-based approach, **Magic Mode** offers a quick way to simulate human-like browsing without storing long-term data.

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(
        url="https://example.com",
        config=CrawlerRunConfig(
            magic=True,  # Simplifies a lot of interaction
            remove_overlay_elements=True,
            page_timeout=60000
        )
    )
Copy
```

**Magic Mode** :

- Simulates a user-like experience
- Randomizes user agent & navigator
- Randomizes interactions & timings
- Masks automation signals
- Attempts pop-up handling

**But** it’s no substitute for **true** user-based sessions if you want a fully legitimate identity-based solution.

---

## 5. Comparing Managed Browsers vs. Magic Mode

| Feature                 | **Managed Browsers**                                     | **Magic Mode**                                      |
| ----------------------- | -------------------------------------------------------- | --------------------------------------------------- |
| **Session Persistence** | Full localStorage/cookies retained in user_data_dir      | No persistent data (fresh each run)                 |
| **Genuine Identity**    | Real user profile with full rights & preferences         | Emulated user-like patterns, but no actual identity |
| **Complex Sites**       | Best for login-gated sites or heavy config               | Simple tasks, minimal login or config needed        |
| **Setup**               | External creation of user_data_dir, then use in Crawl4AI | Single-line approach (`magic=True`)                 |
| **Reliability**         | Extremely consistent (same data across runs)             | Good for smaller tasks, can be less stable          |

---

## 6. Using the BrowserProfiler Class

Crawl4AI provides a dedicated `BrowserProfiler` class for managing browser profiles, making it easy to create, list, and delete profiles for identity-based browsing.

### Creating and Managing Profiles with BrowserProfiler

The `BrowserProfiler` class offers a comprehensive API for browser profile management:

```
import asyncio
from crawl4ai import BrowserProfiler

async def manage_profiles():
    # Create a profiler instance
    profiler = BrowserProfiler()

    # Create a profile interactively - opens a browser window
    profile_path = await profiler.create_profile(
        profile_name="my-login-profile"  # Optional: name your profile
    )

    print(f"Profile saved at: {profile_path}")

    # List all available profiles
    profiles = profiler.list_profiles()

    for profile in profiles:
        print(f"Profile: {profile['name']}")
        print(f"  Path: {profile['path']}")
        print(f"  Created: {profile['created']}")
        print(f"  Browser type: {profile['type']}")

    # Get a specific profile path by name
    specific_profile = profiler.get_profile_path("my-login-profile")

    # Delete a profile when no longer needed
    success = profiler.delete_profile("old-profile-name")

asyncio.run(manage_profiles())
Copy
```

**How profile creation works:** 1. A browser window opens for you to interact with 2. You log in to websites, set preferences, etc. 3. When you're done, press 'q' in the terminal to close the browser 4. The profile is saved in the Crawl4AI profiles directory 5. You can use the returned path with `BrowserConfig.user_data_dir`

### Interactive Profile Management

The `BrowserProfiler` also offers an interactive management console that guides you through profile creation, listing, and deletion:

```
import asyncio
from crawl4ai import BrowserProfiler, AsyncWebCrawler, BrowserConfig

# Define a function to use a profile for crawling
async def crawl_with_profile(profile_path, url):
    browser_config = BrowserConfig(
        headless=True,
        use_managed_browser=True,
        user_data_dir=profile_path
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url)
        return result

async def main():
    # Create a profiler instance
    profiler = BrowserProfiler()

    # Launch the interactive profile manager
    # Passing the crawl function as a callback adds a "crawl with profile" option
    await profiler.interactive_manager(crawl_callback=crawl_with_profile)

asyncio.run(main())
Copy
```

### Legacy Methods

For backward compatibility, the previous methods on `ManagedBrowser` are still available, but they delegate to the new `BrowserProfiler` class:

```
from crawl4ai.browser_manager import ManagedBrowser

# These methods still work but use BrowserProfiler internally
profiles = ManagedBrowser.list_profiles()
Copy
```

### Complete Example

See the full example in `docs/examples/identity_based_browsing.py` for a complete demonstration of creating and using profiles for authenticated browsing using the new `BrowserProfiler` class.

---

## 7. Locale, Timezone, and Geolocation Control

In addition to using persistent profiles, Crawl4AI supports customizing your browser's locale, timezone, and geolocation settings. These features enhance your identity-based browsing experience by allowing you to control how websites perceive your location and regional settings.

### Setting Locale and Timezone

You can set the browser's locale and timezone through `CrawlerRunConfig`:

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(
        url="https://example.com",
        config=CrawlerRunConfig(
            # Set browser locale (language and region formatting)
            locale="fr-FR",  # French (France)

            # Set browser timezone
            timezone_id="Europe/Paris",

            # Other normal options...
            magic=True,
            page_timeout=60000
        )
    )
Copy
```

**How it works:** - `locale` affects language preferences, date formats, number formats, etc. - `timezone_id` affects JavaScript's Date object and time-related functionality - These settings are applied when creating the browser context and maintained throughout the session

### Configuring Geolocation

Control the GPS coordinates reported by the browser's geolocation API:

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, GeolocationConfig

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(
        url="https://maps.google.com",  # Or any location-aware site
        config=CrawlerRunConfig(
            # Configure precise GPS coordinates
            geolocation=GeolocationConfig(
                latitude=48.8566,   # Paris coordinates
                longitude=2.3522,
                accuracy=100        # Accuracy in meters (optional)
            ),

            # This site will see you as being in Paris
            page_timeout=60000
        )
    )
Copy
```

**Important notes:** - When `geolocation` is specified, the browser is automatically granted permission to access location - Websites using the Geolocation API will receive the exact coordinates you specify - This affects map services, store locators, delivery services, etc. - Combined with the appropriate `locale` and `timezone_id`, you can create a fully consistent location profile

### Combining with Managed Browsers

These settings work perfectly with managed browsers for a complete identity solution:

```
from crawl4ai import (
    AsyncWebCrawler, BrowserConfig, CrawlerRunConfig,
    GeolocationConfig
)

browser_config = BrowserConfig(
    use_managed_browser=True,
    user_data_dir="/path/to/my-profile",
    browser_type="chromium"
)

crawl_config = CrawlerRunConfig(
    # Location settings
    locale="es-MX",                  # Spanish (Mexico)
    timezone_id="America/Mexico_City",
    geolocation=GeolocationConfig(
        latitude=19.4326,            # Mexico City
        longitude=-99.1332
    )
)

async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(url="https://example.com", config=crawl_config)
Copy
```

Combining persistent profiles with precise geolocation and region settings gives you complete control over your digital identity.

## 8. Summary

- **Create** your user-data directory either:
- By launching Chrome/Chromium externally with `--user-data-dir=/some/path`
- Or by using the built-in `BrowserProfiler.create_profile()` method
- Or through the interactive interface with `profiler.interactive_manager()`
- **Log in** or configure sites as needed, then close the browser
- **Reference** that folder in `BrowserConfig(user_data_dir="...")` + `use_managed_browser=True`
- **Customize** identity aspects with `locale`, `timezone_id`, and `geolocation`
- **List and reuse** profiles with `BrowserProfiler.list_profiles()`
- **Manage** your profiles with the dedicated `BrowserProfiler` class
- Enjoy **persistent** sessions that reflect your real identity
- If you only need quick, ephemeral automation, **Magic Mode** might suffice

**Recommended** : Always prefer a **Managed Browser** for robust, identity-based crawling and simpler interactions with complex sites. Use **Magic Mode** for quick tasks or prototypes where persistent data is unnecessary.
With these approaches, you preserve your **authentic** browsing environment, ensuring the site sees you exactly as a normal user—no repeated logins or wasted time.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/identity-based-crawling/)

ESC to close

#### On this page

- [1. Managed Browsers: Your Digital Identity Solution](https://docs.crawl4ai.com/advanced/identity-based-crawling/#1-managed-browsers-your-digital-identity-solution)
- [Key Benefits](https://docs.crawl4ai.com/advanced/identity-based-crawling/#key-benefits)
- [Creating a User Data Directory (Command-Line Approach via Playwright)](https://docs.crawl4ai.com/advanced/identity-based-crawling/#creating-a-user-data-directory-command-line-approach-via-playwright)
- [3. Using Managed Browsers in Crawl4AI](https://docs.crawl4ai.com/advanced/identity-based-crawling/#3-using-managed-browsers-in-crawl4ai)
- [Workflow](https://docs.crawl4ai.com/advanced/identity-based-crawling/#workflow)
- [4. Magic Mode: Simplified Automation](https://docs.crawl4ai.com/advanced/identity-based-crawling/#4-magic-mode-simplified-automation)
- [5. Comparing Managed Browsers vs. Magic Mode](https://docs.crawl4ai.com/advanced/identity-based-crawling/#5-comparing-managed-browsers-vs-magic-mode)
- [6. Using the BrowserProfiler Class](https://docs.crawl4ai.com/advanced/identity-based-crawling/#6-using-the-browserprofiler-class)
- [Creating and Managing Profiles with BrowserProfiler](https://docs.crawl4ai.com/advanced/identity-based-crawling/#creating-and-managing-profiles-with-browserprofiler)
- [Interactive Profile Management](https://docs.crawl4ai.com/advanced/identity-based-crawling/#interactive-profile-management)
- [Legacy Methods](https://docs.crawl4ai.com/advanced/identity-based-crawling/#legacy-methods)
- [Complete Example](https://docs.crawl4ai.com/advanced/identity-based-crawling/#complete-example)
- [7. Locale, Timezone, and Geolocation Control](https://docs.crawl4ai.com/advanced/identity-based-crawling/#7-locale-timezone-and-geolocation-control)
- [Setting Locale and Timezone](https://docs.crawl4ai.com/advanced/identity-based-crawling/#setting-locale-and-timezone)
- [Configuring Geolocation](https://docs.crawl4ai.com/advanced/identity-based-crawling/#configuring-geolocation)
- [Combining with Managed Browsers](https://docs.crawl4ai.com/advanced/identity-based-crawling/#combining-with-managed-browsers)
- [8. Summary](https://docs.crawl4ai.com/advanced/identity-based-crawling/#8-summary)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/ssl-certificate

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/ssl-certificate/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - SSL Certificate
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [SSLCertificate Reference](https://docs.crawl4ai.com/advanced/ssl-certificate/#sslcertificate-reference)
- [1. Overview](https://docs.crawl4ai.com/advanced/ssl-certificate/#1-overview)
- [2. Construction & Fetching](https://docs.crawl4ai.com/advanced/ssl-certificate/#2-construction-fetching)
- [3. Common Properties](https://docs.crawl4ai.com/advanced/ssl-certificate/#3-common-properties)
- [4. Export Methods](https://docs.crawl4ai.com/advanced/ssl-certificate/#4-export-methods)
- [5. Example Usage in Crawl4AI](https://docs.crawl4ai.com/advanced/ssl-certificate/#5-example-usage-in-crawl4ai)
- [6. Notes & Best Practices](https://docs.crawl4ai.com/advanced/ssl-certificate/#6-notes-best-practices)

# `SSLCertificate` Reference

The **`SSLCertificate`**class encapsulates an SSL certificate’s data and allows exporting it in various formats (PEM, DER, JSON, or text). It’s used within**Crawl4AI** whenever you set **`fetch_ssl_certificate=True`**in your**`CrawlerRunConfig`**.

## 1. Overview

**Location** : `crawl4ai/ssl_certificate.py`

```
class SSLCertificate:
    """
    Represents an SSL certificate with methods to export in various formats.

    Main Methods:
    - from_url(url, timeout=10)
    - from_file(file_path)
    - from_binary(binary_data)
    - to_json(filepath=None)
    - to_pem(filepath=None)
    - to_der(filepath=None)
    ...

    Common Properties:
    - issuer
    - subject
    - valid_from
    - valid_until
    - fingerprint
    """
Copy
```

### Typical Use Case

1. You **enable** certificate fetching in your crawl by:

```
CrawlerRunConfig(fetch_ssl_certificate=True, ...)
Copy
```

2. After `arun()`, if `result.ssl_certificate` is present, it’s an instance of **`SSLCertificate`**.
3. You can **read** basic properties (issuer, subject, validity) or **export** them in multiple formats.

---

## 2. Construction & Fetching

### 2.1 **`from_url(url, timeout=10)`**

Manually load an SSL certificate from a given URL (port 443). Typically used internally, but you can call it directly if you want:

```
cert = SSLCertificate.from_url("https://example.com")
if cert:
    print("Fingerprint:", cert.fingerprint)
Copy
```

### 2.2 **`from_file(file_path)`**

Load from a file containing certificate data in ASN.1 or DER. Rarely needed unless you have local cert files:

```
cert = SSLCertificate.from_file("/path/to/cert.der")
Copy
```

### 2.3 **`from_binary(binary_data)`**

Initialize from raw binary. E.g., if you captured it from a socket or another source:

```
cert = SSLCertificate.from_binary(raw_bytes)
Copy
```

---

## 3. Common Properties

After obtaining a **`SSLCertificate`**instance (e.g.`result.ssl_certificate` from a crawl), you can read:

1. **`issuer`**_(dict)_

- E.g. `{"CN": "My Root CA", "O": "..."}` 2. **`subject`**_(dict)_
- E.g. `{"CN": "example.com", "O": "ExampleOrg"}` 3. **`valid_from`**_(str)_
- NotBefore date/time. Often in ASN.1/UTC format. 4. **`valid_until`**_(str)_
- NotAfter date/time. 5. **`fingerprint`**_(str)_
- The SHA-256 digest (lowercase hex).
- E.g. `"d14d2e..."`

---

## 4. Export Methods

Once you have a **`SSLCertificate`**object, you can**export** or **inspect** it:

### 4.1 **`to_json(filepath=None)`→`Optional[str]`**

- Returns a JSON string containing the parsed certificate fields.
- If `filepath` is provided, saves it to disk instead, returning `None`.

**Usage** :

```
json_data = cert.to_json()  # returns JSON string
cert.to_json("certificate.json")  # writes file, returns None
Copy
```

### 4.2 **`to_pem(filepath=None)`→`Optional[str]`**

- Returns a PEM-encoded string (common for web servers).
- If `filepath` is provided, saves it to disk instead.

```
pem_str = cert.to_pem()              # in-memory PEM string
cert.to_pem("/path/to/cert.pem")     # saved to file
Copy
```

### 4.3 **`to_der(filepath=None)`→`Optional[bytes]`**

- Returns the original DER (binary ASN.1) bytes.
- If `filepath` is specified, writes the bytes there instead.

```
der_bytes = cert.to_der()
cert.to_der("certificate.der")
Copy
```

### 4.4 (Optional) **`export_as_text()`**

- If you see a method like `export_as_text()`, it typically returns an OpenSSL-style textual representation.
- Not always needed, but can help for debugging or manual inspection.

---

## 5. Example Usage in Crawl4AI

Below is a minimal sample showing how the crawler obtains an SSL cert from a site, then reads or exports it. The code snippet:

```
import asyncio
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def main():
    tmp_dir = "tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    config = CrawlerRunConfig(
        fetch_ssl_certificate=True,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com", config=config)
        if result.success and result.ssl_certificate:
            cert = result.ssl_certificate
            # 1. Basic Info
            print("Issuer CN:", cert.issuer.get("CN", ""))
            print("Valid until:", cert.valid_until)
            print("Fingerprint:", cert.fingerprint)

            # 2. Export
            cert.to_json(os.path.join(tmp_dir, "certificate.json"))
            cert.to_pem(os.path.join(tmp_dir, "certificate.pem"))
            cert.to_der(os.path.join(tmp_dir, "certificate.der"))

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

## 6. Notes & Best Practices

1. **Timeout** : `SSLCertificate.from_url` internally uses a default **10s** socket connect and wraps SSL.
2. **Binary Form** : The certificate is loaded in ASN.1 (DER) form, then re-parsed by `OpenSSL.crypto`.
3. **Validation** : This does **not** validate the certificate chain or trust store. It only fetches and parses.
4. **Integration** : Within Crawl4AI, you typically just set `fetch_ssl_certificate=True` in `CrawlerRunConfig`; the final result’s `ssl_certificate` is automatically built.
5. **Export** : If you need to store or analyze a cert, the `to_json` and `to_pem` are quite universal.

---

### Summary

- **`SSLCertificate`**is a convenience class for capturing and exporting the**TLS certificate** from your crawled site(s).
- Common usage is in the **`CrawlResult.ssl_certificate`**field, accessible after setting`fetch_ssl_certificate=True`.
- Offers quick access to essential certificate details (`issuer`, `subject`, `fingerprint`) and is easy to export (PEM, DER, JSON) for further analysis or server usage.

Use it whenever you need **insight** into a site’s certificate or require some form of cryptographic or compliance check.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/ssl-certificate/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/ssl-certificate/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/ssl-certificate/)

ESC to close

#### On this page

- [1. Overview](https://docs.crawl4ai.com/advanced/ssl-certificate/#1-overview)
- [Typical Use Case](https://docs.crawl4ai.com/advanced/ssl-certificate/#typical-use-case)
- [2. Construction & Fetching](https://docs.crawl4ai.com/advanced/ssl-certificate/#2-construction-fetching)
- [2.1 from_url(url, timeout=10)](https://docs.crawl4ai.com/advanced/ssl-certificate/#21-from_urlurl-timeout10)
- [2.2 from_file(file_path)](https://docs.crawl4ai.com/advanced/ssl-certificate/#22-from_filefile_path)
- [2.3 from_binary(binary_data)](https://docs.crawl4ai.com/advanced/ssl-certificate/#23-from_binarybinary_data)
- [3. Common Properties](https://docs.crawl4ai.com/advanced/ssl-certificate/#3-common-properties)
- [4. Export Methods](https://docs.crawl4ai.com/advanced/ssl-certificate/#4-export-methods)
- [4.1 to_json(filepath=None) → Optional[str]](https://docs.crawl4ai.com/advanced/ssl-certificate/#41-to_jsonfilepathnone-optionalstr)
- [4.2 to_pem(filepath=None) → Optional[str]](https://docs.crawl4ai.com/advanced/ssl-certificate/#42-to_pemfilepathnone-optionalstr)
- [4.3 to_der(filepath=None) → Optional[bytes]](https://docs.crawl4ai.com/advanced/ssl-certificate/#43-to_derfilepathnone-optionalbytes)
- [4.4 (Optional) export_as_text()](https://docs.crawl4ai.com/advanced/ssl-certificate/#44-optional-export_as_text)
- [5. Example Usage in Crawl4AI](https://docs.crawl4ai.com/advanced/ssl-certificate/#5-example-usage-in-crawl4ai)
- [6. Notes & Best Practices](https://docs.crawl4ai.com/advanced/ssl-certificate/#6-notes-best-practices)
- [Summary](https://docs.crawl4ai.com/advanced/ssl-certificate/#summary)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/api/crawl-result

```
{"detail":"Not Found"}
```

---

## Fonte: https://docs.crawl4ai.com/advanced/file-downloading

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/file-downloading/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - File Downloading
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Download Handling in Crawl4AI](https://docs.crawl4ai.com/advanced/file-downloading/#download-handling-in-crawl4ai)
- [Enabling Downloads](https://docs.crawl4ai.com/advanced/file-downloading/#enabling-downloads)
- [Specifying Download Location](https://docs.crawl4ai.com/advanced/file-downloading/#specifying-download-location)
- [Triggering Downloads](https://docs.crawl4ai.com/advanced/file-downloading/#triggering-downloads)
- [Accessing Downloaded Files](https://docs.crawl4ai.com/advanced/file-downloading/#accessing-downloaded-files)
- [Example: Downloading Multiple Files](https://docs.crawl4ai.com/advanced/file-downloading/#example-downloading-multiple-files)
- [Important Considerations](https://docs.crawl4ai.com/advanced/file-downloading/#important-considerations)

# Download Handling in Crawl4AI

This guide explains how to use Crawl4AI to handle file downloads during crawling. You'll learn how to trigger downloads, specify download locations, and access downloaded files.

## Enabling Downloads

To enable downloads, set the `accept_downloads` parameter in the `BrowserConfig` object and pass it to the crawler.

```
from crawl4ai.async_configs import BrowserConfig, AsyncWebCrawler

async def main():
    config = BrowserConfig(accept_downloads=True)  # Enable downloads globally
    async with AsyncWebCrawler(config=config) as crawler:
        # ... your crawling logic ...

asyncio.run(main())
Copy
```

## Specifying Download Location

Specify the download directory using the `downloads_path` attribute in the `BrowserConfig` object. If not provided, Crawl4AI defaults to creating a "downloads" directory inside the `.crawl4ai` folder in your home directory.

```
from crawl4ai.async_configs import BrowserConfig
import os

downloads_path = os.path.join(os.getcwd(), "my_downloads")  # Custom download path
os.makedirs(downloads_path, exist_ok=True)

config = BrowserConfig(accept_downloads=True, downloads_path=downloads_path)

async def main():
    async with AsyncWebCrawler(config=config) as crawler:
        result = await crawler.arun(url="https://example.com")
        # ...
Copy
```

## Triggering Downloads

Downloads are typically triggered by user interactions on a web page, such as clicking a download button. Use `js_code` in `CrawlerRunConfig` to simulate these actions and `wait_for` to allow sufficient time for downloads to start.

```
from crawl4ai.async_configs import CrawlerRunConfig

config = CrawlerRunConfig(
    js_code="""
        const downloadLink = document.querySelector('a[href$=".exe"]');
        if (downloadLink) {
            downloadLink.click();
        }
    """,
    wait_for=5  # Wait 5 seconds for the download to start
)

result = await crawler.arun(url="https://www.python.org/downloads/", config=config)
Copy
```

## Accessing Downloaded Files

The `downloaded_files` attribute of the `CrawlResult` object contains paths to downloaded files.

```
if result.downloaded_files:
    print("Downloaded files:")
    for file_path in result.downloaded_files:
        print(f"- {file_path}")
        file_size = os.path.getsize(file_path)
        print(f"- File size: {file_size} bytes")
else:
    print("No files downloaded.")
Copy
```

## Example: Downloading Multiple Files

```
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
import os
from pathlib import Path

async def download_multiple_files(url: str, download_path: str):
    config = BrowserConfig(accept_downloads=True, downloads_path=download_path)
    async with AsyncWebCrawler(config=config) as crawler:
        run_config = CrawlerRunConfig(
            js_code="""
                const downloadLinks = document.querySelectorAll('a[download]');
                for (const link of downloadLinks) {
                    link.click();
                    // Delay between clicks
                    await new Promise(r => setTimeout(r, 2000));
                }
            """,
            wait_for=10  # Wait for all downloads to start
        )
        result = await crawler.arun(url=url, config=run_config)

        if result.downloaded_files:
            print("Downloaded files:")
            for file in result.downloaded_files:
                print(f"- {file}")
        else:
            print("No files downloaded.")

# Usage
download_path = os.path.join(Path.home(), ".crawl4ai", "downloads")
os.makedirs(download_path, exist_ok=True)

asyncio.run(download_multiple_files("https://www.python.org/downloads/windows/", download_path))
Copy
```

## Important Considerations

- **Browser Context:** Downloads are managed within the browser context. Ensure `js_code` correctly targets the download triggers on the webpage.
- **Timing:** Use `wait_for` in `CrawlerRunConfig` to manage download timing.
- **Error Handling:** Handle errors to manage failed downloads or incorrect paths gracefully.
- **Security:** Scan downloaded files for potential security threats before use.

This revised guide ensures consistency with the `Crawl4AI` codebase by using `BrowserConfig` and `CrawlerRunConfig` for all download-related configurations. Let me know if further adjustments are needed!
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/file-downloading/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/file-downloading/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/file-downloading/)

ESC to close

#### On this page

- [Enabling Downloads](https://docs.crawl4ai.com/advanced/file-downloading/#enabling-downloads)
- [Specifying Download Location](https://docs.crawl4ai.com/advanced/file-downloading/#specifying-download-location)
- [Triggering Downloads](https://docs.crawl4ai.com/advanced/file-downloading/#triggering-downloads)
- [Accessing Downloaded Files](https://docs.crawl4ai.com/advanced/file-downloading/#accessing-downloaded-files)
- [Example: Downloading Multiple Files](https://docs.crawl4ai.com/advanced/file-downloading/#example-downloading-multiple-files)
- [Important Considerations](https://docs.crawl4ai.com/advanced/file-downloading/#important-considerations)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/undetected-browser

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/undetected-browser/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - Undetected Browser
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Undetected Browser Mode](https://docs.crawl4ai.com/advanced/undetected-browser/#undetected-browser-mode)
- [Overview](https://docs.crawl4ai.com/advanced/undetected-browser/#overview)
- [Anti-Bot Features Comparison](https://docs.crawl4ai.com/advanced/undetected-browser/#anti-bot-features-comparison)
- [When to Use Each Approach](https://docs.crawl4ai.com/advanced/undetected-browser/#when-to-use-each-approach)
- [Stealth Mode](https://docs.crawl4ai.com/advanced/undetected-browser/#stealth-mode)
- [Undetected Browser Mode](https://docs.crawl4ai.com/advanced/undetected-browser/#undetected-browser-mode_1)
- [Combining Both Features](https://docs.crawl4ai.com/advanced/undetected-browser/#combining-both-features)
- [Examples](https://docs.crawl4ai.com/advanced/undetected-browser/#examples)
- [Browser Adapter Pattern](https://docs.crawl4ai.com/advanced/undetected-browser/#browser-adapter-pattern)
- [Best Practices](https://docs.crawl4ai.com/advanced/undetected-browser/#best-practices)
- [Advanced Usage Tips](https://docs.crawl4ai.com/advanced/undetected-browser/#advanced-usage-tips)
- [Installation](https://docs.crawl4ai.com/advanced/undetected-browser/#installation)
- [Limitations](https://docs.crawl4ai.com/advanced/undetected-browser/#limitations)
- [Troubleshooting](https://docs.crawl4ai.com/advanced/undetected-browser/#troubleshooting)
- [Future Plans](https://docs.crawl4ai.com/advanced/undetected-browser/#future-plans)
- [Conclusion](https://docs.crawl4ai.com/advanced/undetected-browser/#conclusion)
- [See Also](https://docs.crawl4ai.com/advanced/undetected-browser/#see-also)

# Undetected Browser Mode

## Overview

Crawl4AI offers two powerful anti-bot features to help you access websites with bot detection:

1. **Stealth Mode** - Uses playwright-stealth to modify browser fingerprints and behaviors
2. **Undetected Browser Mode** - Advanced browser adapter with deep-level patches for sophisticated bot detection

This guide covers both features and helps you choose the right approach for your needs.

## Anti-Bot Features Comparison

| Feature              | Regular Browser | Stealth Mode | Undetected Browser |
| -------------------- | --------------- | ------------ | ------------------ |
| WebDriver Detection  | ❌              | ✅           | ✅                 |
| Navigator Properties | ❌              | ✅           | ✅                 |
| Plugin Emulation     | ❌              | ✅           | ✅                 |
| CDP Detection        | ❌              | Partial      | ✅                 |
| Deep Browser Patches | ❌              | ❌           | ✅                 |
| Performance Impact   | None            | Minimal      | Moderate           |
| Setup Complexity     | None            | None         | Minimal            |

## When to Use Each Approach

### Use Regular Browser + Stealth Mode When:

- Sites have basic bot detection (checking navigator.webdriver, plugins, etc.)
- You need good performance with basic protection
- Sites check for common automation indicators

### Use Undetected Browser When:

- Sites employ sophisticated bot detection services (Cloudflare, DataDome, etc.)
- Stealth mode alone isn't sufficient
- You're willing to trade some performance for better evasion

### Best Practice: Progressive Enhancement

1. **Start with** : Regular browser + Stealth mode
2. **If blocked** : Switch to Undetected browser
3. **If still blocked** : Combine Undetected browser + Stealth mode

## Stealth Mode

Stealth mode is the simpler anti-bot solution that works with both regular and undetected browsers:

```
from crawl4ai import AsyncWebCrawler, BrowserConfig

# Enable stealth mode with regular browser
browser_config = BrowserConfig(
    enable_stealth=True,  # Simple flag to enable
    headless=False       # Better for avoiding detection
)

async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun("https://example.com")
Copy
```

### What Stealth Mode Does:

- Removes `navigator.webdriver` flag
- Modifies browser fingerprints
- Emulates realistic plugin behavior
- Adjusts navigator properties
- Fixes common automation leaks

## Undetected Browser Mode

For sites with sophisticated bot detection that stealth mode can't bypass, use the undetected browser adapter:

### Key Features

- **Drop-in Replacement** : Uses the same API as regular browser mode
- **Enhanced Stealth** : Built-in patches to evade common detection methods
- **Browser Adapter Pattern** : Seamlessly switch between regular and undetected modes
- **Automatic Installation** : `crawl4ai-setup` installs all necessary browser dependencies

### Quick Start

```
import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    UndetectedAdapter
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

async def main():
    # Create the undetected adapter
    undetected_adapter = UndetectedAdapter()

    # Create browser config
    browser_config = BrowserConfig(
        headless=False,  # Headless mode can be detected easier
        verbose=True,
    )

    # Create the crawler strategy with undetected adapter
    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=undetected_adapter
    )

    # Create the crawler with our custom strategy
    async with AsyncWebCrawler(
        crawler_strategy=crawler_strategy,
        config=browser_config
    ) as crawler:
        # Your crawling code here
        result = await crawler.arun(
            url="https://example.com",
            config=CrawlerRunConfig()
        )
        print(result.markdown[:500])

asyncio.run(main())
Copy
```

## Combining Both Features

For maximum evasion, combine stealth mode with undetected browser:

```
from crawl4ai import AsyncWebCrawler, BrowserConfig, UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

# Create browser config with stealth enabled
browser_config = BrowserConfig(
    enable_stealth=True,  # Enable stealth mode
    headless=False
)

# Create undetected adapter
adapter = UndetectedAdapter()

# Create strategy with both features
strategy = AsyncPlaywrightCrawlerStrategy(
    browser_config=browser_config,
    browser_adapter=adapter
)

async with AsyncWebCrawler(
    crawler_strategy=strategy,
    config=browser_config
) as crawler:
    result = await crawler.arun("https://protected-site.com")
Copy
```

## Examples

### Example 1: Basic Stealth Mode

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def test_stealth_mode():
    # Simple stealth mode configuration
    browser_config = BrowserConfig(
        enable_stealth=True,
        headless=False
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://bot.sannysoft.com",
            config=CrawlerRunConfig(screenshot=True)
        )

        if result.success:
            print("✓ Successfully accessed bot detection test site")
            # Save screenshot to verify detection results
            if result.screenshot:
                import base64
                with open("stealth_test.png", "wb") as f:
                    f.write(base64.b64decode(result.screenshot))
                print("✓ Screenshot saved - check for green (passed) tests")

asyncio.run(test_stealth_mode())
Copy
```

### Example 2: Undetected Browser Mode

```
import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    UndetectedAdapter
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy


async def main():
    # Create browser config
    browser_config = BrowserConfig(
        headless=False,
        verbose=True,
    )

    # Create the undetected adapter
    undetected_adapter = UndetectedAdapter()

    # Create the crawler strategy with the undetected adapter
    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=undetected_adapter
    )

    # Create the crawler with our custom strategy
    async with AsyncWebCrawler(
        crawler_strategy=crawler_strategy,
        config=browser_config
    ) as crawler:
        # Configure the crawl
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter()
            ),
            capture_console_messages=True,  # Test adapter console capture
        )

        # Test on a site that typically detects bots
        print("Testing undetected adapter...")
        result: CrawlResult = await crawler.arun(
            url="https://www.helloworld.org",
            config=crawler_config
        )

        print(f"Status: {result.status_code}")
        print(f"Success: {result.success}")
        print(f"Console messages captured: {len(result.console_messages or [])}")
        print(f"Markdown content (first 500 chars):\n{result.markdown.raw_markdown[:500]}")


if __name__ == "__main__":
    asyncio.run(main())
Copy
```

## Browser Adapter Pattern

The undetected browser support is implemented using an adapter pattern, allowing seamless switching between different browser implementations:

```
# Regular browser adapter (default)
from crawl4ai import PlaywrightAdapter
regular_adapter = PlaywrightAdapter()

# Undetected browser adapter
from crawl4ai import UndetectedAdapter
undetected_adapter = UndetectedAdapter()
Copy
```

The adapter handles: - JavaScript execution - Console message capture - Error handling - Browser-specific optimizations

## Best Practices

1. **Avoid Headless Mode** : Detection is easier in headless mode

```
browser_config = BrowserConfig(headless=False)
Copy
```

2. **Use Reasonable Delays** : Don't rush through pages

```
crawler_config = CrawlerRunConfig(
    wait_time=3.0,  # Wait 3 seconds after page load
    delay_before_return_html=2.0  # Additional delay
)
Copy
```

3. **Rotate User Agents** : You can customize user agents

```
browser_config = BrowserConfig(
    headers={"User-Agent": "your-user-agent"}
)
Copy
```

4. **Handle Failures Gracefully** : Some sites may still detect and block

```
if not result.success:
    print(f"Crawl failed: {result.error_message}")
Copy
```

## Advanced Usage Tips

### Progressive Detection Handling

```
async def crawl_with_progressive_evasion(url):
    # Step 1: Try regular browser with stealth
    browser_config = BrowserConfig(
        enable_stealth=True,
        headless=False
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url)
        if result.success and "Access Denied" not in result.html:
            return result

    # Step 2: If blocked, try undetected browser
    print("Regular + stealth blocked, trying undetected browser...")

    adapter = UndetectedAdapter()
    strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=adapter
    )

    async with AsyncWebCrawler(
        crawler_strategy=strategy,
        config=browser_config
    ) as crawler:
        result = await crawler.arun(url)
        return result
Copy
```

## Installation

The undetected browser dependencies are automatically installed when you run:

```
crawl4ai-setup
Copy
```

This command installs all necessary browser dependencies for both regular and undetected modes.

## Limitations

- **Performance** : Slightly slower than regular mode due to additional patches
- **Headless Detection** : Some sites can still detect headless mode
- **Resource Usage** : May use more resources than regular mode
- **Not 100% Guaranteed** : Advanced anti-bot services are constantly evolving

## Troubleshooting

### Browser Not Found

Run the setup command:

```
crawl4ai-setup
Copy
```

### Detection Still Occurring

Try combining with other features:

```
crawler_config = CrawlerRunConfig(
    simulate_user=True,  # Add user simulation
    magic=True,  # Enable magic mode
    wait_time=5.0,  # Longer waits
)
Copy
```

### Performance Issues

If experiencing slow performance:

```
# Use selective undetected mode only for protected sites
if is_protected_site(url):
    adapter = UndetectedAdapter()
else:
    adapter = PlaywrightAdapter()  # Default adapter
Copy
```

## Future Plans

**Note** : In future versions of Crawl4AI, we may enable stealth mode and undetected browser by default to provide better out-of-the-box success rates. For now, users should explicitly enable these features when needed.

## Conclusion

Crawl4AI provides flexible anti-bot solutions:

1. **Start Simple** : Use regular browser + stealth mode for most sites
2. **Escalate if Needed** : Switch to undetected browser for sophisticated protection
3. **Combine for Maximum Effect** : Use both features together when facing the toughest challenges

Remember: - Always respect robots.txt and website terms of service - Use appropriate delays to avoid overwhelming servers - Consider the performance trade-offs of each approach - Test progressively to find the minimum necessary evasion level

## See Also

- [Advanced Features](https://docs.crawl4ai.com/advanced/advanced-features/) - Overview of all advanced features
- [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/) - Using proxies with anti-bot features
- [Session Management](https://docs.crawl4ai.com/advanced/session-management/) - Maintaining sessions across requests
- [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/) - Additional anti-detection strategies

Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/undetected-browser/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/undetected-browser/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/undetected-browser/)

ESC to close

#### On this page

- [Overview](https://docs.crawl4ai.com/advanced/undetected-browser/#overview)
- [Anti-Bot Features Comparison](https://docs.crawl4ai.com/advanced/undetected-browser/#anti-bot-features-comparison)
- [When to Use Each Approach](https://docs.crawl4ai.com/advanced/undetected-browser/#when-to-use-each-approach)
- [Use Regular Browser + Stealth Mode When:](https://docs.crawl4ai.com/advanced/undetected-browser/#use-regular-browser-stealth-mode-when)
- [Use Undetected Browser When:](https://docs.crawl4ai.com/advanced/undetected-browser/#use-undetected-browser-when)
- [Best Practice: Progressive Enhancement](https://docs.crawl4ai.com/advanced/undetected-browser/#best-practice-progressive-enhancement)
- [Stealth Mode](https://docs.crawl4ai.com/advanced/undetected-browser/#stealth-mode)
- [What Stealth Mode Does:](https://docs.crawl4ai.com/advanced/undetected-browser/#what-stealth-mode-does)
- [Undetected Browser Mode](https://docs.crawl4ai.com/advanced/undetected-browser/#undetected-browser-mode_1)
- [Key Features](https://docs.crawl4ai.com/advanced/undetected-browser/#key-features)
- [Quick Start](https://docs.crawl4ai.com/advanced/undetected-browser/#quick-start)
- [Combining Both Features](https://docs.crawl4ai.com/advanced/undetected-browser/#combining-both-features)
- [Examples](https://docs.crawl4ai.com/advanced/undetected-browser/#examples)
- [Example 1: Basic Stealth Mode](https://docs.crawl4ai.com/advanced/undetected-browser/#example-1-basic-stealth-mode)
- [Example 2: Undetected Browser Mode](https://docs.crawl4ai.com/advanced/undetected-browser/#example-2-undetected-browser-mode)
- [Browser Adapter Pattern](https://docs.crawl4ai.com/advanced/undetected-browser/#browser-adapter-pattern)
- [Best Practices](https://docs.crawl4ai.com/advanced/undetected-browser/#best-practices)
- [Advanced Usage Tips](https://docs.crawl4ai.com/advanced/undetected-browser/#advanced-usage-tips)
- [Progressive Detection Handling](https://docs.crawl4ai.com/advanced/undetected-browser/#progressive-detection-handling)
- [Installation](https://docs.crawl4ai.com/advanced/undetected-browser/#installation)
- [Limitations](https://docs.crawl4ai.com/advanced/undetected-browser/#limitations)
- [Troubleshooting](https://docs.crawl4ai.com/advanced/undetected-browser/#troubleshooting)
- [Browser Not Found](https://docs.crawl4ai.com/advanced/undetected-browser/#browser-not-found)
- [Detection Still Occurring](https://docs.crawl4ai.com/advanced/undetected-browser/#detection-still-occurring)
- [Performance Issues](https://docs.crawl4ai.com/advanced/undetected-browser/#performance-issues)
- [Future Plans](https://docs.crawl4ai.com/advanced/undetected-browser/#future-plans)
- [Conclusion](https://docs.crawl4ai.com/advanced/undetected-browser/#conclusion)
- [See Also](https://docs.crawl4ai.com/advanced/undetected-browser/#see-also)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/advanced-features

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/advanced-features/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - Overview
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Overview of Some Important Advanced Features](https://docs.crawl4ai.com/advanced/advanced-features/#overview-of-some-important-advanced-features)
- [1. Proxy Usage](https://docs.crawl4ai.com/advanced/advanced-features/#1-proxy-usage)
- [2. Capturing PDFs & Screenshots](https://docs.crawl4ai.com/advanced/advanced-features/#2-capturing-pdfs-screenshots)
- [3. Handling SSL Certificates](https://docs.crawl4ai.com/advanced/advanced-features/#3-handling-ssl-certificates)
- [4. Custom Headers](https://docs.crawl4ai.com/advanced/advanced-features/#4-custom-headers)
- [5. Session Persistence & Local Storage](https://docs.crawl4ai.com/advanced/advanced-features/#5-session-persistence-local-storage)
- [6. Robots.txt Compliance](https://docs.crawl4ai.com/advanced/advanced-features/#6-robotstxt-compliance)
- [Putting It All Together](https://docs.crawl4ai.com/advanced/advanced-features/#putting-it-all-together)
- [7. Anti-Bot Features (Stealth Mode & Undetected Browser)](https://docs.crawl4ai.com/advanced/advanced-features/#7-anti-bot-features-stealth-mode-undetected-browser)
- [Conclusion & Next Steps](https://docs.crawl4ai.com/advanced/advanced-features/#conclusion-next-steps)

# Overview of Some Important Advanced Features

(Proxy, PDF, Screenshot, SSL, Headers, & Storage State)
Crawl4AI offers multiple power-user features that go beyond simple crawling. This tutorial covers:

1. **Proxy Usage**
2. **Capturing PDFs & Screenshots**
3. **Handling SSL Certificates**
4. **Custom Headers**
5. **Session Persistence & Local Storage**
6. **Robots.txt Compliance**
   > **Prerequisites**
   >
   > - You have a basic grasp of [AsyncWebCrawler Basics](https://docs.crawl4ai.com/core/simple-crawling/)
   > - You know how to run or configure your Python environment with Playwright installed

---

## 1. Proxy Usage

If you need to route your crawl traffic through a proxy—whether for IP rotation, geo-testing, or privacy—Crawl4AI supports it via `BrowserConfig.proxy_config`.

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def main():
    browser_cfg = BrowserConfig(
        proxy_config={
            "server": "http://proxy.example.com:8080",
            "username": "myuser",
            "password": "mypass",
        },
        headless=True
    )
    crawler_cfg = CrawlerRunConfig(
        verbose=True
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(
            url="https://www.whatismyip.com/",
            config=crawler_cfg
        )
        if result.success:
            print("[OK] Page fetched via proxy.")
            print("Page HTML snippet:", result.html[:200])
        else:
            print("[ERROR]", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key Points**

- **`proxy_config`**expects a dict with`server` and optional auth credentials.
- Many commercial proxies provide an HTTP/HTTPS “gateway” server that you specify in `server`.
- If your proxy doesn’t need auth, omit `username`/`password`.

---

## 2. Capturing PDFs & Screenshots

Sometimes you need a visual record of a page or a PDF “printout.” Crawl4AI can do both in one pass:

```
import os, asyncio
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

async def main():
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        screenshot=True,
        pdf=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/List_of_common_misconceptions",
            config=run_config
        )
        if result.success:
            print(f"Screenshot data present: {result.screenshot is not None}")
            print(f"PDF data present: {result.pdf is not None}")

            if result.screenshot:
                print(f"[OK] Screenshot captured, size: {len(result.screenshot)} bytes")
                with open("wikipedia_screenshot.png", "wb") as f:
                    f.write(b64decode(result.screenshot))
            else:
                print("[WARN] Screenshot data is None.")

            if result.pdf:
                print(f"[OK] PDF captured, size: {len(result.pdf)} bytes")
                with open("wikipedia_page.pdf", "wb") as f:
                    f.write(result.pdf)
            else:
                print("[WARN] PDF data is None.")

        else:
            print("[ERROR]", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Why PDF + Screenshot?**

- Large or complex pages can be slow or error-prone with “traditional” full-page screenshots.
- Exporting a PDF is more reliable for very long pages. Crawl4AI automatically converts the first PDF page into an image if you request both.
  **Relevant Parameters**
- **`pdf=True`**: Exports the current page as a PDF (base64-encoded in`result.pdf`).
- **`screenshot=True`**: Creates a screenshot (base64-encoded in`result.screenshot`).
- **`scan_full_page`**or advanced hooking can further refine how the crawler captures content.

---

## 3. Handling SSL Certificates

If you need to verify or export a site’s SSL certificate—for compliance, debugging, or data analysis—Crawl4AI can fetch it during the crawl:

```
import asyncio, os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def main():
    tmp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    config = CrawlerRunConfig(
        fetch_ssl_certificate=True,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com", config=config)

        if result.success and result.ssl_certificate:
            cert = result.ssl_certificate
            print("\nCertificate Information:")
            print(f"Issuer (CN): {cert.issuer.get('CN', '')}")
            print(f"Valid until: {cert.valid_until}")
            print(f"Fingerprint: {cert.fingerprint}")

            # Export in multiple formats:
            cert.to_json(os.path.join(tmp_dir, "certificate.json"))
            cert.to_pem(os.path.join(tmp_dir, "certificate.pem"))
            cert.to_der(os.path.join(tmp_dir, "certificate.der"))

            print("\nCertificate exported to JSON/PEM/DER in 'tmp' folder.")
        else:
            print("[ERROR] No certificate or crawl failed.")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key Points**

- **`fetch_ssl_certificate=True`**triggers certificate retrieval.
- `result.ssl_certificate` includes methods (`to_json`, `to_pem`, `to_der`) for saving in various formats (handy for server config, Java keystores, etc.).

---

## 4. Custom Headers

Sometimes you need to set custom headers (e.g., language preferences, authentication tokens, or specialized user-agent strings). You can do this in multiple ways:

```
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    # Option 1: Set headers at the crawler strategy level
    crawler1 = AsyncWebCrawler(
        # The underlying strategy can accept headers in its constructor
        crawler_strategy=None  # We'll override below for clarity
    )
    crawler1.crawler_strategy.update_user_agent("MyCustomUA/1.0")
    crawler1.crawler_strategy.set_custom_headers({
        "Accept-Language": "fr-FR,fr;q=0.9"
    })
    result1 = await crawler1.arun("https://www.example.com")
    print("Example 1 result success:", result1.success)

    # Option 2: Pass headers directly to `arun()`
    crawler2 = AsyncWebCrawler()
    result2 = await crawler2.arun(
        url="https://www.example.com",
        headers={"Accept-Language": "es-ES,es;q=0.9"}
    )
    print("Example 2 result success:", result2.success)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Notes**

- Some sites may react differently to certain headers (e.g., `Accept-Language`).
- If you need advanced user-agent randomization or client hints, see [Identity-Based Crawling (Anti-Bot)](https://docs.crawl4ai.com/advanced/identity-based-crawling/) or use `UserAgentGenerator`.

---

## 5. Session Persistence & Local Storage

Crawl4AI can preserve cookies and localStorage so you can continue where you left off—ideal for logging into sites or skipping repeated auth flows.

### 5.1 `storage_state`

```
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    storage_dict = {
        "cookies": [
            {
                "name": "session",
                "value": "abcd1234",
                "domain": "example.com",
                "path": "/",
                "expires": 1699999999.0,
                "httpOnly": False,
                "secure": False,
                "sameSite": "None"
            }
        ],
        "origins": [
            {
                "origin": "https://example.com",
                "localStorage": [
                    {"name": "token", "value": "my_auth_token"}
                ]
            }
        ]
    }

    # Provide the storage state as a dictionary to start "already logged in"
    async with AsyncWebCrawler(
        headless=True,
        storage_state=storage_dict
    ) as crawler:
        result = await crawler.arun("https://example.com/protected")
        if result.success:
            print("Protected page content length:", len(result.html))
        else:
            print("Failed to crawl protected page")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### 5.2 Exporting & Reusing State

You can sign in once, export the browser context, and reuse it later—without re-entering credentials.

- **`await context.storage_state(path="my_storage.json")`**: Exports cookies, localStorage, etc. to a file.
- Provide `storage_state="my_storage.json"` on subsequent runs to skip the login step.

**See** : [Detailed session management tutorial](https://docs.crawl4ai.com/advanced/session-management/) or [Explanations → Browser Context & Managed Browser](https://docs.crawl4ai.com/advanced/identity-based-crawling/) for more advanced scenarios (like multi-step logins, or capturing after interactive pages).

---

## 6. Robots.txt Compliance

Crawl4AI supports respecting robots.txt rules with efficient caching:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Enable robots.txt checking in config
    config = CrawlerRunConfig(
        check_robots_txt=True  # Will check and respect robots.txt rules
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            "https://example.com",
            config=config
        )

        if not result.success and result.status_code == 403:
            print("Access denied by robots.txt")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key Points** - Robots.txt files are cached locally for efficiency - Cache is stored in `~/.crawl4ai/robots/robots_cache.db` - Cache has a default TTL of 7 days - If robots.txt can't be fetched, crawling is allowed - Returns 403 status code if URL is disallowed

---

## Putting It All Together

Here’s a snippet that combines multiple “advanced” features (proxy, PDF, screenshot, SSL, custom headers, and session reuse) into one run. Normally, you’d tailor each setting to your project’s needs.

```
import os, asyncio
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    # 1. Browser config with proxy + headless
    browser_cfg = BrowserConfig(
        proxy_config={
            "server": "http://proxy.example.com:8080",
            "username": "myuser",
            "password": "mypass",
        },
        headless=True,
    )

    # 2. Crawler config with PDF, screenshot, SSL, custom headers, and ignoring caches
    crawler_cfg = CrawlerRunConfig(
        pdf=True,
        screenshot=True,
        fetch_ssl_certificate=True,
        cache_mode=CacheMode.BYPASS,
        headers={"Accept-Language": "en-US,en;q=0.8"},
        storage_state="my_storage.json",  # Reuse session from a previous sign-in
        verbose=True,
    )

    # 3. Crawl
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(
            url = "https://secure.example.com/protected",
            config=crawler_cfg
        )

        if result.success:
            print("[OK] Crawled the secure page. Links found:", len(result.links.get("internal", [])))

            # Save PDF & screenshot
            if result.pdf:
                with open("result.pdf", "wb") as f:
                    f.write(b64decode(result.pdf))
            if result.screenshot:
                with open("result.png", "wb") as f:
                    f.write(b64decode(result.screenshot))

            # Check SSL cert
            if result.ssl_certificate:
                print("SSL Issuer CN:", result.ssl_certificate.issuer.get("CN", ""))
        else:
            print("[ERROR]", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

---

## 7. Anti-Bot Features (Stealth Mode & Undetected Browser)

Crawl4AI provides two powerful features to bypass bot detection:

### 7.1 Stealth Mode

Stealth mode uses playwright-stealth to modify browser fingerprints and behaviors. Enable it with a simple flag:

```
browser_config = BrowserConfig(
    enable_stealth=True,  # Activates stealth mode
    headless=False
)
Copy
```

**When to use** : Sites with basic bot detection (checking navigator.webdriver, plugins, etc.)

### 7.2 Undetected Browser

For advanced bot detection, use the undetected browser adapter:

```
from crawl4ai import UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

# Create undetected adapter
adapter = UndetectedAdapter()
strategy = AsyncPlaywrightCrawlerStrategy(
    browser_config=browser_config,
    browser_adapter=adapter
)

async with AsyncWebCrawler(crawler_strategy=strategy, config=browser_config) as crawler:
    # Your crawling code
Copy
```

**When to use** : Sites with sophisticated bot detection (Cloudflare, DataDome, etc.)

### 7.3 Combining Both

For maximum evasion, combine stealth mode with undetected browser:

```
browser_config = BrowserConfig(
    enable_stealth=True,  # Enable stealth
    headless=False
)

adapter = UndetectedAdapter()  # Use undetected browser
Copy
```

### Choosing the Right Approach

| Detection Level     | Recommended Approach      |
| ------------------- | ------------------------- |
| No protection       | Regular browser           |
| Basic checks        | Regular + Stealth mode    |
| Advanced protection | Undetected browser        |
| Maximum evasion     | Undetected + Stealth mode |

**Best Practice** : Start with regular browser + stealth mode. Only use undetected browser if needed, as it may be slightly slower.
See [Undetected Browser Mode](https://docs.crawl4ai.com/advanced/undetected-browser/) for detailed examples.

---

## Conclusion & Next Steps

You've now explored several **advanced** features:

- **Proxy Usage**
- **PDF & Screenshot** capturing for large or critical pages
- **SSL Certificate** retrieval & exporting
- **Custom Headers** for language or specialized requests
- **Session Persistence** via storage state
- **Robots.txt Compliance**
- **Anti-Bot Features** (Stealth Mode & Undetected Browser)

With these power tools, you can build robust scraping workflows that mimic real user behavior, handle secure sites, capture detailed snapshots, manage sessions across multiple runs, and bypass bot detection—streamlining your entire data collection pipeline.
**Note** : In future versions, we may enable stealth mode and undetected browser by default. For now, users should explicitly enable these features when needed.
**Last Updated** : 2025-01-17
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/advanced-features/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/advanced-features/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/advanced-features/)

ESC to close

#### On this page

- [1. Proxy Usage](https://docs.crawl4ai.com/advanced/advanced-features/#1-proxy-usage)
- [2. Capturing PDFs & Screenshots](https://docs.crawl4ai.com/advanced/advanced-features/#2-capturing-pdfs-screenshots)
- [3. Handling SSL Certificates](https://docs.crawl4ai.com/advanced/advanced-features/#3-handling-ssl-certificates)
- [4. Custom Headers](https://docs.crawl4ai.com/advanced/advanced-features/#4-custom-headers)
- [5. Session Persistence & Local Storage](https://docs.crawl4ai.com/advanced/advanced-features/#5-session-persistence-local-storage)
- [5.1 storage_state](https://docs.crawl4ai.com/advanced/advanced-features/#51-storage_state)
- [5.2 Exporting & Reusing State](https://docs.crawl4ai.com/advanced/advanced-features/#52-exporting-reusing-state)
- [6. Robots.txt Compliance](https://docs.crawl4ai.com/advanced/advanced-features/#6-robotstxt-compliance)
- [Putting It All Together](https://docs.crawl4ai.com/advanced/advanced-features/#putting-it-all-together)
- [7. Anti-Bot Features (Stealth Mode & Undetected Browser)](https://docs.crawl4ai.com/advanced/advanced-features/#7-anti-bot-features-stealth-mode-undetected-browser)
- [7.1 Stealth Mode](https://docs.crawl4ai.com/advanced/advanced-features/#71-stealth-mode)
- [7.2 Undetected Browser](https://docs.crawl4ai.com/advanced/advanced-features/#72-undetected-browser)
- [7.3 Combining Both](https://docs.crawl4ai.com/advanced/advanced-features/#73-combining-both)
- [Choosing the Right Approach](https://docs.crawl4ai.com/advanced/advanced-features/#choosing-the-right-approach)
- [Conclusion & Next Steps](https://docs.crawl4ai.com/advanced/advanced-features/#conclusion-next-steps)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/crawl-dispatcher

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - Crawl Dispatcher
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/#crawl-dispatcher)

# Crawl Dispatcher

We’re excited to announce a **Crawl Dispatcher** module that can handle **thousands** of crawling tasks simultaneously. By efficiently managing system resources (memory, CPU, network), this dispatcher ensures high-performance data extraction at scale. It also provides **real-time monitoring** of each crawler’s status, memory usage, and overall progress.
Stay tuned—this feature is **coming soon** in an upcoming release of Crawl4AI! For the latest news, keep an eye on our changelogs and follow [@unclecode](https://twitter.com/unclecode) on X.
Below is a **sample** of how the dispatcher’s performance monitor might look in action:
![Crawl Dispatcher Performance Monitor](https://docs.crawl4ai.com/assets/images/dispatcher.png)
We can’t wait to bring you this streamlined, **scalable** approach to multi-URL crawling—**watch this space** for updates!
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)

ESC to close

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/api/parameters

```
{"detail":"Not Found"}
```

---

## Fonte: https://docs.crawl4ai.com/advanced/lazy-loading

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/lazy-loading/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - Lazy Loading
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Handling Lazy-Loaded Images](https://docs.crawl4ai.com/advanced/lazy-loading/#handling-lazy-loaded-images)
- [Example: Ensuring Lazy Images Appear](https://docs.crawl4ai.com/advanced/lazy-loading/#example-ensuring-lazy-images-appear)
- [Combining with Other Link & Media Filters](https://docs.crawl4ai.com/advanced/lazy-loading/#combining-with-other-link-media-filters)
- [Tips & Troubleshooting](https://docs.crawl4ai.com/advanced/lazy-loading/#tips-troubleshooting)

## Handling Lazy-Loaded Images

Many websites now load images **lazily** as you scroll. If you need to ensure they appear in your final crawl (and in `result.media`), consider:

1. **`wait_for_images=True`**– Wait for images to fully load.
2. **`scan_full_page`**– Force the crawler to scroll the entire page, triggering lazy loads.
3. **`scroll_delay`**– Add small delays between scroll steps.
   **Note** : If the site requires multiple “Load More” triggers or complex interactions, see the [Page Interaction docs](https://docs.crawl4ai.com/core/page-interaction/). For sites with virtual scrolling (Twitter/Instagram style), see the [Virtual Scroll docs](https://docs.crawl4ai.com/advanced/virtual-scroll/).

### Example: Ensuring Lazy Images Appear

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.async_configs import CacheMode

async def main():
    config = CrawlerRunConfig(
        # Force the crawler to wait until images are fully loaded
        wait_for_images=True,

        # Option 1: If you want to automatically scroll the page to load images
        scan_full_page=True,  # Tells the crawler to try scrolling the entire page
        scroll_delay=0.5,     # Delay (seconds) between scroll steps

        # Option 2: If the site uses a 'Load More' or JS triggers for images,
        # you can also specify js_code or wait_for logic here.

        cache_mode=CacheMode.BYPASS,
        verbose=True
    )

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun("https://www.example.com/gallery", config=config)

        if result.success:
            images = result.media.get("images", [])
            print("Images found:", len(images))
            for i, img in enumerate(images[:5]):
                print(f"[Image {i}] URL: {img['src']}, Score: {img.get('score','N/A')}")
        else:
            print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Explanation** :

- **`wait_for_images=True`**
  The crawler tries to ensure images have finished loading before finalizing the HTML.
- **`scan_full_page=True`**
  Tells the crawler to attempt scrolling from top to bottom. Each scroll step helps trigger lazy loading.
- **`scroll_delay=0.5`**
  Pause half a second between each scroll step. Helps the site load images before continuing.

**When to Use** :

- **Lazy-Loading** : If images appear only when the user scrolls into view, `scan_full_page` + `scroll_delay` helps the crawler see them.
- **Heavier Pages** : If a page is extremely long, be mindful that scanning the entire page can be slow. Adjust `scroll_delay` or the max scroll steps as needed.

---

## Combining with Other Link & Media Filters

You can still combine **lazy-load** logic with the usual **exclude_external_images** , **exclude_domains** , or link filtration:

```
config = CrawlerRunConfig(
    wait_for_images=True,
    scan_full_page=True,
    scroll_delay=0.5,

    # Filter out external images if you only want local ones
    exclude_external_images=True,

    # Exclude certain domains for links
    exclude_domains=["spammycdn.com"],
)
Copy
```

This approach ensures you see **all** images from the main domain while ignoring external ones, and the crawler physically scrolls the entire page so that lazy-loading triggers.

---

## Tips & Troubleshooting

1. **Long Pages**

- Setting `scan_full_page=True` on extremely long or infinite-scroll pages can be resource-intensive.
- Consider using [hooks](https://docs.crawl4ai.com/core/page-interaction/) or specialized logic to load specific sections or “Load More” triggers repeatedly.

2. **Mixed Image Behavior**

- Some sites load images in batches as you scroll. If you’re missing images, increase your `scroll_delay` or call multiple partial scrolls in a loop with JS code or hooks.

3. **Combining with Dynamic Wait**

- If the site has a placeholder that only changes to a real image after a certain event, you might do `wait_for="css:img.loaded"` or a custom JS `wait_for`.

4. **Caching**

- If `cache_mode` is enabled, repeated crawls might skip some network fetches. If you suspect caching is missing new images, set `cache_mode=CacheMode.BYPASS` for fresh fetches.

---

With **lazy-loading** support, **wait_for_images** , and **scan_full_page** settings, you can capture the entire gallery or feed of images you expect—even if the site only loads them as the user scrolls. Combine these with the standard media filtering and domain exclusion for a complete link & media handling strategy.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/lazy-loading/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/lazy-loading/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/lazy-loading/)

ESC to close

#### On this page

- [Handling Lazy-Loaded Images](https://docs.crawl4ai.com/advanced/lazy-loading/#handling-lazy-loaded-images)
- [Example: Ensuring Lazy Images Appear](https://docs.crawl4ai.com/advanced/lazy-loading/#example-ensuring-lazy-images-appear)
- [Combining with Other Link & Media Filters](https://docs.crawl4ai.com/advanced/lazy-loading/#combining-with-other-link-media-filters)
- [Tips & Troubleshooting](https://docs.crawl4ai.com/advanced/lazy-loading/#tips-troubleshooting)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/multi-url-crawling

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/multi-url-crawling/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - Multi-URL Crawling
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Advanced Multi-URL Crawling with Dispatchers](https://docs.crawl4ai.com/advanced/multi-url-crawling/#advanced-multi-url-crawling-with-dispatchers)
- [1. Introduction](https://docs.crawl4ai.com/advanced/multi-url-crawling/#1-introduction)
- [2. Core Components](https://docs.crawl4ai.com/advanced/multi-url-crawling/#2-core-components)
- [3. Available Dispatchers](https://docs.crawl4ai.com/advanced/multi-url-crawling/#3-available-dispatchers)
- [4. Usage Examples](https://docs.crawl4ai.com/advanced/multi-url-crawling/#4-usage-examples)
- [5. Dispatch Results](https://docs.crawl4ai.com/advanced/multi-url-crawling/#5-dispatch-results)
- [6. URL-Specific Configurations](https://docs.crawl4ai.com/advanced/multi-url-crawling/#6-url-specific-configurations)
- [7. Summary](https://docs.crawl4ai.com/advanced/multi-url-crawling/#7-summary)

# Advanced Multi-URL Crawling with Dispatchers

> **Heads Up** : Crawl4AI supports advanced dispatchers for **parallel** or **throttled** crawling, providing dynamic rate limiting and memory usage checks. The built-in `arun_many()` function uses these dispatchers to handle concurrency efficiently.

## 1. Introduction

When crawling many URLs:

- **Basic** : Use `arun()` in a loop (simple but less efficient)
- **Better** : Use `arun_many()`, which efficiently handles multiple URLs with proper concurrency control
- **Best** : Customize dispatcher behavior for your specific needs (memory management, rate limits, etc.)

**Why Dispatchers?**

- **Adaptive** : Memory-based dispatchers can pause or slow down based on system resources
- **Rate-limiting** : Built-in rate limiting with exponential backoff for 429/503 responses
- **Real-time Monitoring** : Live dashboard of ongoing tasks, memory usage, and performance
- **Flexibility** : Choose between memory-adaptive or semaphore-based concurrency

---

## 2. Core Components

### 2.1 Rate Limiter

```
class RateLimiter:
    def __init__(
        # Random delay range between requests
        base_delay: Tuple[float, float] = (1.0, 3.0),

        # Maximum backoff delay
        max_delay: float = 60.0,

        # Retries before giving up
        max_retries: int = 3,

        # Status codes triggering backoff
        rate_limit_codes: List[int] = [429, 503]
    )
Copy
```

Here’s the revised and simplified explanation of the **RateLimiter** , focusing on constructor parameters and adhering to your markdown style and mkDocs guidelines.

#### RateLimiter Constructor Parameters

The **RateLimiter** is a utility that helps manage the pace of requests to avoid overloading servers or getting blocked due to rate limits. It operates internally to delay requests and handle retries but can be configured using its constructor parameters.
**Parameters of the`RateLimiter` constructor:**

1. **`base_delay`**(`Tuple[float, float]` , default: `(1.0, 3.0)`)
   The range for a random delay (in seconds) between consecutive requests to the same domain.

- A random delay is chosen between `base_delay[0]` and `base_delay[1]` for each request.
- This prevents sending requests at a predictable frequency, reducing the chances of triggering rate limits.

**Example:**
If `base_delay = (2.0, 5.0)`, delays could be randomly chosen as `2.3s`, `4.1s`, etc.

---

2. **`max_delay`**(`float` , default: `60.0`)
   The maximum allowable delay when rate-limiting errors occur.

- When servers return rate-limit responses (e.g., 429 or 503), the delay increases exponentially with jitter.
- The `max_delay` ensures the delay doesn’t grow unreasonably high, capping it at this value.

**Example:**
For a `max_delay = 30.0`, even if backoff calculations suggest a delay of `45s`, it will cap at `30s`.

---

3. **`max_retries`**(`int` , default: `3`)
   The maximum number of retries for a request if rate-limiting errors occur.

- After encountering a rate-limit response, the `RateLimiter` retries the request up to this number of times.
- If all retries fail, the request is marked as failed, and the process continues.

**Example:**
If `max_retries = 3`, the system retries a failed request three times before giving up.

---

4. **`rate_limit_codes`**(`List[int]` , default: `[429, 503]`)
   A list of HTTP status codes that trigger the rate-limiting logic.

- These status codes indicate the server is overwhelmed or actively limiting requests.
- You can customize this list to include other codes based on specific server behavior.

**Example:**
If `rate_limit_codes = [429, 503, 504]`, the crawler will back off on these three error codes.

---

**How to Use the`RateLimiter` :**
Here’s an example of initializing and using a `RateLimiter` in your project:

```
from crawl4ai import RateLimiter

# Create a RateLimiter with custom settings
rate_limiter = RateLimiter(
    base_delay=(2.0, 4.0),  # Random delay between 2-4 seconds
    max_delay=30.0,         # Cap delay at 30 seconds
    max_retries=5,          # Retry up to 5 times on rate-limiting errors
    rate_limit_codes=[429, 503]  # Handle these HTTP status codes
)

# RateLimiter will handle delays and retries internally
# No additional setup is required for its operation
Copy
```

The `RateLimiter` integrates seamlessly with dispatchers like `MemoryAdaptiveDispatcher` and `SemaphoreDispatcher`, ensuring requests are paced correctly without user intervention. Its internal mechanisms manage delays and retries to avoid overwhelming servers while maximizing efficiency.

### 2.2 Crawler Monitor

The CrawlerMonitor provides real-time visibility into crawling operations:

```
from crawl4ai import CrawlerMonitor, DisplayMode
monitor = CrawlerMonitor(
    # Maximum rows in live display
    max_visible_rows=15,

    # DETAILED or AGGREGATED view
    display_mode=DisplayMode.DETAILED
)
Copy
```

**Display Modes** :

1. **DETAILED** : Shows individual task status, memory usage, and timing
2. **AGGREGATED** : Displays summary statistics and overall progress

---

## 3. Available Dispatchers

### 3.1 MemoryAdaptiveDispatcher (Default)

Automatically manages concurrency based on system memory usage:

```
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher

dispatcher = MemoryAdaptiveDispatcher(
    memory_threshold_percent=90.0,  # Pause if memory exceeds this
    check_interval=1.0,             # How often to check memory
    max_session_permit=10,          # Maximum concurrent tasks
    rate_limiter=RateLimiter(       # Optional rate limiting
        base_delay=(1.0, 2.0),
        max_delay=30.0,
        max_retries=2
    ),
    monitor=CrawlerMonitor(         # Optional monitoring
        max_visible_rows=15,
        display_mode=DisplayMode.DETAILED
    )
)
Copy
```

**Constructor Parameters:**

1. **`memory_threshold_percent`**(`float` , default: `90.0`)
   Specifies the memory usage threshold (as a percentage). If system memory usage exceeds this value, the dispatcher pauses crawling to prevent system overload.
2. **`check_interval`**(`float` , default: `1.0`)
   The interval (in seconds) at which the dispatcher checks system memory usage.
3. **`max_session_permit`**(`int` , default: `10`)
   The maximum number of concurrent crawling tasks allowed. This ensures resource limits are respected while maintaining concurrency.
4. **`memory_wait_timeout`**(`float` , default: `600.0`) Optional timeout (in seconds). If memory usage exceeds `memory_threshold_percent` for longer than this duration, a `MemoryError` is raised.
5. **`rate_limiter`**(`RateLimiter` , default: `None`)
   Optional rate-limiting logic to avoid server-side blocking (e.g., for handling 429 or 503 errors). See **RateLimiter** for details.
6. **`monitor`**(`CrawlerMonitor` , default: `None`)
   Optional monitoring for real-time task tracking and performance insights. See **CrawlerMonitor** for details.

---

### 3.2 SemaphoreDispatcher

Provides simple concurrency control with a fixed limit:

```
from crawl4ai.async_dispatcher import SemaphoreDispatcher

dispatcher = SemaphoreDispatcher(
    max_session_permit=20,         # Maximum concurrent tasks
    rate_limiter=RateLimiter(      # Optional rate limiting
        base_delay=(0.5, 1.0),
        max_delay=10.0
    ),
    monitor=CrawlerMonitor(        # Optional monitoring
        max_visible_rows=15,
        display_mode=DisplayMode.DETAILED
    )
)
Copy
```

**Constructor Parameters:**

1. **`max_session_permit`**(`int` , default: `20`)
   The maximum number of concurrent crawling tasks allowed, irrespective of semaphore slots.
2. **`rate_limiter`**(`RateLimiter` , default: `None`)
   Optional rate-limiting logic to avoid overwhelming servers. See **RateLimiter** for details.
3. **`monitor`**(`CrawlerMonitor` , default: `None`)
   Optional monitoring for tracking task progress and resource usage. See **CrawlerMonitor** for details.

---

## 4. Usage Examples

### 4.1 Batch Processing (Default)

```
async def crawl_batch():
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        stream=False  # Default: get all results at once
    )

    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=10,
        monitor=CrawlerMonitor(
            display_mode=DisplayMode.DETAILED
        )
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Get all results at once
        results = await crawler.arun_many(
            urls=urls,
            config=run_config,
            dispatcher=dispatcher
        )

        # Process all results after completion
        for result in results:
            if result.success:
                await process_result(result)
            else:
                print(f"Failed to crawl {result.url}: {result.error_message}")
Copy
```

**Review:**

- **Purpose:** Executes a batch crawl with all URLs processed together after crawling is complete.
- **Dispatcher:** Uses `MemoryAdaptiveDispatcher` to manage concurrency and system memory.
- **Stream:** Disabled (`stream=False`), so all results are collected at once for post-processing.
- **Best Use Case:** When you need to analyze results in bulk rather than individually during the crawl.

---

### 4.2 Streaming Mode

```
async def crawl_streaming():
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        stream=True  # Enable streaming mode
    )

    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=10,
        monitor=CrawlerMonitor(
            display_mode=DisplayMode.DETAILED
        )
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Process results as they become available
        async for result in await crawler.arun_many(
            urls=urls,
            config=run_config,
            dispatcher=dispatcher
        ):
            if result.success:
                # Process each result immediately
                await process_result(result)
            else:
                print(f"Failed to crawl {result.url}: {result.error_message}")
Copy
```

**Review:**

- **Purpose:** Enables streaming to process results as soon as they’re available.
- **Dispatcher:** Uses `MemoryAdaptiveDispatcher` for concurrency and memory management.
- **Stream:** Enabled (`stream=True`), allowing real-time processing during crawling.
- **Best Use Case:** When you need to act on results immediately, such as for real-time analytics or progressive data storage.

---

### 4.3 Semaphore-based Crawling

```
async def crawl_with_semaphore(urls):
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    dispatcher = SemaphoreDispatcher(
        semaphore_count=5,
        rate_limiter=RateLimiter(
            base_delay=(0.5, 1.0),
            max_delay=10.0
        ),
        monitor=CrawlerMonitor(
            max_visible_rows=15,
            display_mode=DisplayMode.DETAILED
        )
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls,
            config=run_config,
            dispatcher=dispatcher
        )
        return results
Copy
```

**Review:**

- **Purpose:** Uses `SemaphoreDispatcher` to limit concurrency with a fixed number of slots.
- **Dispatcher:** Configured with a semaphore to control parallel crawling tasks.
- **Rate Limiter:** Prevents servers from being overwhelmed by pacing requests.
- **Best Use Case:** When you want precise control over the number of concurrent requests, independent of system memory.

---

### 4.4 Robots.txt Consideration

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def main():
    urls = [
        "https://example1.com",
        "https://example2.com",
        "https://example3.com"
    ]

    config = CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        check_robots_txt=True,  # Will respect robots.txt for each URL
        semaphore_count=3      # Max concurrent requests
    )

    async with AsyncWebCrawler() as crawler:
        async for result in crawler.arun_many(urls, config=config):
            if result.success:
                print(f"Successfully crawled {result.url}")
            elif result.status_code == 403 and "robots.txt" in result.error_message:
                print(f"Skipped {result.url} - blocked by robots.txt")
            else:
                print(f"Failed to crawl {result.url}: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Review:**

- **Purpose:** Ensures compliance with `robots.txt` rules for ethical and legal web crawling.
- **Configuration:** Set `check_robots_txt=True` to validate each URL against `robots.txt` before crawling.
- **Dispatcher:** Handles requests with concurrency limits (`semaphore_count=3`).
- **Best Use Case:** When crawling websites that strictly enforce robots.txt policies or for responsible crawling practices.

---

## 5. Dispatch Results

Each crawl result includes dispatch information:

```
@dataclass
class DispatchResult:
    task_id: str
    memory_usage: float
    peak_memory: float
    start_time: datetime
    end_time: datetime
    error_message: str = ""
Copy
```

Access via `result.dispatch_result`:

```
for result in results:
    if result.success:
        dr = result.dispatch_result
        print(f"URL: {result.url}")
        print(f"Memory: {dr.memory_usage:.1f}MB")
        print(f"Duration: {dr.end_time - dr.start_time}")
Copy
```

## 6. URL-Specific Configurations

When crawling diverse content types, you often need different configurations for different URLs. For example: - PDFs need specialized extraction - Blog pages benefit from content filtering - Dynamic sites need JavaScript execution - API endpoints need JSON parsing

### 6.1 Basic URL Pattern Matching

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, MatchMode
from crawl4ai.processors.pdf import PDFContentScrapingStrategy
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def crawl_mixed_content():
    # Configure different strategies for different content
    configs = [
        # PDF files - specialized extraction
        CrawlerRunConfig(
            url_matcher="*.pdf",
            scraping_strategy=PDFContentScrapingStrategy()
        ),

        # Blog/article pages - content filtering
        CrawlerRunConfig(
            url_matcher=["*/blog/*", "*/article/*"],
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(threshold=0.48)
            )
        ),

        # Dynamic pages - JavaScript execution
        CrawlerRunConfig(
            url_matcher=lambda url: 'github.com' in url,
            js_code="window.scrollTo(0, 500);"
        ),

        # API endpoints - JSON extraction
        CrawlerRunConfig(
            url_matcher=lambda url: 'api' in url or url.endswith('.json'),
            # Custome settings for JSON extraction
        ),

        # Default config for everything else
        CrawlerRunConfig()  # No url_matcher means it matches ALL URLs (fallback)
    ]

    # Mixed URLs
    urls = [
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "https://blog.python.org/",
        "https://github.com/microsoft/playwright",
        "https://httpbin.org/json",
        "https://example.com/"
    ]

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(
            urls=urls,
            config=configs  # Pass list of configs
        )

        for result in results:
            print(f"{result.url}: {len(result.markdown)} chars")
Copy
```

### 6.2 Advanced Pattern Matching

**Important** : A `CrawlerRunConfig` without `url_matcher` (or with `url_matcher=None`) matches ALL URLs. This makes it perfect as a default/fallback configuration.
The `url_matcher` parameter supports three types of patterns:

#### Glob Patterns (Strings)

```
# Simple patterns
"*.pdf"                    # Any PDF file
"*/api/*"                  # Any URL with /api/ in path
"https://*.example.com/*"  # Subdomain matching
"*://example.com/blog/*"   # Any protocol
Copy
```

#### Custom Functions

```
# Complex logic with lambdas
lambda url: url.startswith('https://') and 'secure' in url
lambda url: len(url) > 50 and url.count('/') > 5
lambda url: any(domain in url for domain in ['api.', 'data.', 'feed.'])
Copy
```

#### Mixed Lists with AND/OR Logic

```
# Combine multiple conditions
CrawlerRunConfig(
    url_matcher=[
        "https://*",                        # Must be HTTPS
        lambda url: 'internal' in url,      # Must contain 'internal'
        lambda url: not url.endswith('.pdf') # Must not be PDF
    ],
    match_mode=MatchMode.AND  # ALL conditions must match
)
Copy
```

### 6.3 Practical Example: News Site Crawler

```
async def crawl_news_site():
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        rate_limiter=RateLimiter(base_delay=(1.0, 2.0))
    )

    configs = [
        # Homepage - light extraction
        CrawlerRunConfig(
            url_matcher=lambda url: url.rstrip('/') == 'https://news.ycombinator.com',
            css_selector="nav, .headline",
            extraction_strategy=None
        ),

        # Article pages - full extraction
        CrawlerRunConfig(
            url_matcher="*/article/*",
            extraction_strategy=CosineStrategy(
                semantic_filter="article content",
                word_count_threshold=100
            ),
            screenshot=True,
            excluded_tags=["nav", "aside", "footer"]
        ),

        # Author pages - metadata focus
        CrawlerRunConfig(
            url_matcher="*/author/*",
            extraction_strategy=JsonCssExtractionStrategy({
                "name": "h1.author-name",
                "bio": ".author-bio",
                "articles": "article.post-card h2"
            })
        ),

        # Everything else
        CrawlerRunConfig()
    ]

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(
            urls=news_urls,
            config=configs,
            dispatcher=dispatcher
        )
Copy
```

### 6.4 Best Practices

1. **Order Matters** : Configs are evaluated in order - put specific patterns before general ones
2. **Default Config Behavior** :
3. A config without `url_matcher` matches ALL URLs
4. Always include a default config as the last item if you want to handle all URLs
5. Without a default config, unmatched URLs will fail with "No matching configuration found"
6. **Test Your Patterns** : Use the config's `is_match()` method to test patterns:

```
config = CrawlerRunConfig(url_matcher="*.pdf")
print(config.is_match("https://example.com/doc.pdf"))  # True

default_config = CrawlerRunConfig()  # No url_matcher
print(default_config.is_match("https://any-url.com"))  # True - matches everything!
Copy
```

7. **Optimize for Performance** :
8. Disable JS for static content
9. Skip screenshots for data APIs
10. Use appropriate extraction strategies

## 7. Summary

1. **Two Dispatcher Types** :

- MemoryAdaptiveDispatcher (default): Dynamic concurrency based on memory
- SemaphoreDispatcher: Fixed concurrency limit

2. **Optional Components** :

- RateLimiter: Smart request pacing and backoff
- CrawlerMonitor: Real-time progress visualization

3. **Key Benefits** :

- Automatic memory management
- Built-in rate limiting
- Live progress monitoring
- Flexible concurrency control

Choose the dispatcher that best fits your needs:

- **MemoryAdaptiveDispatcher** : For large crawls or limited resources
- **SemaphoreDispatcher** : For simple, fixed-concurrency scenarios

Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/multi-url-crawling/)

ESC to close

#### On this page

- [1. Introduction](https://docs.crawl4ai.com/advanced/multi-url-crawling/#1-introduction)
- [2. Core Components](https://docs.crawl4ai.com/advanced/multi-url-crawling/#2-core-components)
- [2.1 Rate Limiter](https://docs.crawl4ai.com/advanced/multi-url-crawling/#21-rate-limiter)
- [RateLimiter Constructor Parameters](https://docs.crawl4ai.com/advanced/multi-url-crawling/#ratelimiter-constructor-parameters)
- [2.2 Crawler Monitor](https://docs.crawl4ai.com/advanced/multi-url-crawling/#22-crawler-monitor)
- [3. Available Dispatchers](https://docs.crawl4ai.com/advanced/multi-url-crawling/#3-available-dispatchers)
- [3.1 MemoryAdaptiveDispatcher (Default)](https://docs.crawl4ai.com/advanced/multi-url-crawling/#31-memoryadaptivedispatcher-default)
- [3.2 SemaphoreDispatcher](https://docs.crawl4ai.com/advanced/multi-url-crawling/#32-semaphoredispatcher)
- [4. Usage Examples](https://docs.crawl4ai.com/advanced/multi-url-crawling/#4-usage-examples)
- [4.1 Batch Processing (Default)](https://docs.crawl4ai.com/advanced/multi-url-crawling/#41-batch-processing-default)
- [4.2 Streaming Mode](https://docs.crawl4ai.com/advanced/multi-url-crawling/#42-streaming-mode)
- [4.3 Semaphore-based Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/#43-semaphore-based-crawling)
- [4.4 Robots.txt Consideration](https://docs.crawl4ai.com/advanced/multi-url-crawling/#44-robotstxt-consideration)
- [5. Dispatch Results](https://docs.crawl4ai.com/advanced/multi-url-crawling/#5-dispatch-results)
- [6. URL-Specific Configurations](https://docs.crawl4ai.com/advanced/multi-url-crawling/#6-url-specific-configurations)
- [6.1 Basic URL Pattern Matching](https://docs.crawl4ai.com/advanced/multi-url-crawling/#61-basic-url-pattern-matching)
- [6.2 Advanced Pattern Matching](https://docs.crawl4ai.com/advanced/multi-url-crawling/#62-advanced-pattern-matching)
- [Glob Patterns (Strings)](https://docs.crawl4ai.com/advanced/multi-url-crawling/#glob-patterns-strings)
- [Custom Functions](https://docs.crawl4ai.com/advanced/multi-url-crawling/#custom-functions)
- [Mixed Lists with AND/OR Logic](https://docs.crawl4ai.com/advanced/multi-url-crawling/#mixed-lists-with-andor-logic)
- [6.3 Practical Example: News Site Crawler](https://docs.crawl4ai.com/advanced/multi-url-crawling/#63-practical-example-news-site-crawler)
- [6.4 Best Practices](https://docs.crawl4ai.com/advanced/multi-url-crawling/#64-best-practices)
- [7. Summary](https://docs.crawl4ai.com/advanced/multi-url-crawling/#7-summary)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/hooks-auth

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/hooks-auth/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - Hooks & Auth
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Hooks & Auth in AsyncWebCrawler](https://docs.crawl4ai.com/advanced/hooks-auth/#hooks-auth-in-asyncwebcrawler)
- [Example: Using Hooks in AsyncWebCrawler](https://docs.crawl4ai.com/advanced/hooks-auth/#example-using-hooks-in-asyncwebcrawler)
- [Hook Lifecycle Summary](https://docs.crawl4ai.com/advanced/hooks-auth/#hook-lifecycle-summary)
- [When to Handle Authentication](https://docs.crawl4ai.com/advanced/hooks-auth/#when-to-handle-authentication)
- [Additional Considerations](https://docs.crawl4ai.com/advanced/hooks-auth/#additional-considerations)
- [Conclusion](https://docs.crawl4ai.com/advanced/hooks-auth/#conclusion)

# Hooks & Auth in AsyncWebCrawler

Crawl4AI’s **hooks** let you customize the crawler at specific points in the pipeline:

1. **`on_browser_created`**– After browser creation.
2. **`on_page_context_created`**– After a new context & page are created.
3. **`before_goto`**– Just before navigating to a page.
4. **`after_goto`**– Right after navigation completes.
5. **`on_user_agent_updated`**– Whenever the user agent changes.
6. **`on_execution_started`**– Once custom JavaScript execution begins.
7. **`before_retrieve_html`**– Just before the crawler retrieves final HTML.
8. **`before_return_html`**– Right before returning the HTML content.
   **Important** : Avoid heavy tasks in `on_browser_created` since you don’t yet have a page context. If you need to _log in_ , do so in **`on_page_context_created`**.
   > note "Important Hook Usage Warning" **Avoid Misusing Hooks** : Do not manipulate page objects in the wrong hook or at the wrong time, as it can crash the pipeline or produce incorrect results. A common mistake is attempting to handle authentication prematurely—such as creating or closing pages in `on_browser_created`.
   > **Use the Right Hook for Auth** : If you need to log in or set tokens, use `on_page_context_created`. This ensures you have a valid page/context to work with, without disrupting the main crawling flow.
   > **Identity-Based Crawling** : For robust auth, consider identity-based crawling (or passing a session ID) to preserve state. Run your initial login steps in a separate, well-defined process, then feed that session to your main crawl—rather than shoehorning complex authentication into early hooks. Check out [Identity-Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/) for more details.
   > **Be Cautious** : Overwriting or removing elements in the wrong hook can compromise the final crawl. Keep hooks focused on smaller tasks (like route filters, custom headers), and let your main logic (crawling, data extraction) proceed normally.
   > Below is an example demonstration.

---

## Example: Using Hooks in AsyncWebCrawler

```
import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from playwright.async_api import Page, BrowserContext

async def main():
    print("🔗 Hooks Example: Demonstrating recommended usage")

    # 1) Configure the browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )

    # 2) Configure the crawler run
    crawler_run_config = CrawlerRunConfig(
        js_code="window.scrollTo(0, document.body.scrollHeight);",
        wait_for="body",
        cache_mode=CacheMode.BYPASS
    )

    # 3) Create the crawler instance
    crawler = AsyncWebCrawler(config=browser_config)

    #
    # Define Hook Functions
    #

    async def on_browser_created(browser, **kwargs):
        # Called once the browser instance is created (but no pages or contexts yet)
        print("[HOOK] on_browser_created - Browser created successfully!")
        # Typically, do minimal setup here if needed
        return browser

    async def on_page_context_created(page: Page, context: BrowserContext, **kwargs):
        # Called right after a new page + context are created (ideal for auth or route config).
        print("[HOOK] on_page_context_created - Setting up page & context.")

        # Example 1: Route filtering (e.g., block images)
        async def route_filter(route):
            if route.request.resource_type == "image":
                print(f"[HOOK] Blocking image request: {route.request.url}")
                await route.abort()
            else:
                await route.continue_()

        await context.route("**", route_filter)

        # Example 2: (Optional) Simulate a login scenario
        # (We do NOT create or close pages here, just do quick steps if needed)
        # e.g., await page.goto("https://example.com/login")
        # e.g., await page.fill("input[name='username']", "testuser")
        # e.g., await page.fill("input[name='password']", "password123")
        # e.g., await page.click("button[type='submit']")
        # e.g., await page.wait_for_selector("#welcome")
        # e.g., await context.add_cookies([...])
        # Then continue

        # Example 3: Adjust the viewport
        await page.set_viewport_size({"width": 1080, "height": 600})
        return page

    async def before_goto(
        page: Page, context: BrowserContext, url: str, **kwargs
    ):
        # Called before navigating to each URL.
        print(f"[HOOK] before_goto - About to navigate: {url}")
        # e.g., inject custom headers
        await page.set_extra_http_headers({
            "Custom-Header": "my-value"
        })
        return page

    async def after_goto(
        page: Page, context: BrowserContext,
        url: str, response, **kwargs
    ):
        # Called after navigation completes.
        print(f"[HOOK] after_goto - Successfully loaded: {url}")
        # e.g., wait for a certain element if we want to verify
        try:
            await page.wait_for_selector('.content', timeout=1000)
            print("[HOOK] Found .content element!")
        except:
            print("[HOOK] .content not found, continuing anyway.")
        return page

    async def on_user_agent_updated(
        page: Page, context: BrowserContext,
        user_agent: str, **kwargs
    ):
        # Called whenever the user agent updates.
        print(f"[HOOK] on_user_agent_updated - New user agent: {user_agent}")
        return page

    async def on_execution_started(page: Page, context: BrowserContext, **kwargs):
        # Called after custom JavaScript execution begins.
        print("[HOOK] on_execution_started - JS code is running!")
        return page

    async def before_retrieve_html(page: Page, context: BrowserContext, **kwargs):
        # Called before final HTML retrieval.
        print("[HOOK] before_retrieve_html - We can do final actions")
        # Example: Scroll again
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        return page

    async def before_return_html(
        page: Page, context: BrowserContext, html: str, **kwargs
    ):
        # Called just before returning the HTML in the result.
        print(f"[HOOK] before_return_html - HTML length: {len(html)}")
        return page

    #
    # Attach Hooks
    #

    crawler.crawler_strategy.set_hook("on_browser_created", on_browser_created)
    crawler.crawler_strategy.set_hook(
        "on_page_context_created", on_page_context_created
    )
    crawler.crawler_strategy.set_hook("before_goto", before_goto)
    crawler.crawler_strategy.set_hook("after_goto", after_goto)
    crawler.crawler_strategy.set_hook(
        "on_user_agent_updated", on_user_agent_updated
    )
    crawler.crawler_strategy.set_hook(
        "on_execution_started", on_execution_started
    )
    crawler.crawler_strategy.set_hook(
        "before_retrieve_html", before_retrieve_html
    )
    crawler.crawler_strategy.set_hook(
        "before_return_html", before_return_html
    )

    await crawler.start()

    # 4) Run the crawler on an example page
    url = "https://example.com"
    result = await crawler.arun(url, config=crawler_run_config)

    if result.success:
        print("\nCrawled URL:", result.url)
        print("HTML length:", len(result.html))
    else:
        print("Error:", result.error_message)

    await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

## Hook Lifecycle Summary

1. **`on_browser_created`**:

- Browser is up, but **no** pages or contexts yet.
- Light setup only—don’t try to open or close pages here (that belongs in `on_page_context_created`).

2. **`on_page_context_created`**:

- Perfect for advanced **auth** or route blocking.
- You have a **page** + **context** ready but haven’t navigated to the target URL yet.

3. **`before_goto`**:

- Right before navigation. Typically used for setting **custom headers** or logging the target URL.

4. **`after_goto`**:

- After page navigation is done. Good place for verifying content or waiting on essential elements.

5. **`on_user_agent_updated`**:

- Whenever the user agent changes (for stealth or different UA modes).

6. **`on_execution_started`**:

- If you set `js_code` or run custom scripts, this runs once your JS is about to start.

7. **`before_retrieve_html`**:

- Just before the final HTML snapshot is taken. Often you do a final scroll or lazy-load triggers here.

8. **`before_return_html`**:

- The last hook before returning HTML to the `CrawlResult`. Good for logging HTML length or minor modifications.

---

## When to Handle Authentication

**Recommended** : Use **`on_page_context_created`**if you need to:

- Navigate to a login page or fill forms
- Set cookies or localStorage tokens
- Block resource routes to avoid ads

This ensures the newly created context is under your control **before** `arun()` navigates to the main URL.

---

## Additional Considerations

- **Session Management** : If you want multiple `arun()` calls to reuse a single session, pass `session_id=` in your `CrawlerRunConfig`. Hooks remain the same.
- **Performance** : Hooks can slow down crawling if they do heavy tasks. Keep them concise.
- **Error Handling** : If a hook fails, the overall crawl might fail. Catch exceptions or handle them gracefully.
- **Concurrency** : If you run `arun_many()`, each URL triggers these hooks in parallel. Ensure your hooks are thread/async-safe.

---

## Conclusion

Hooks provide **fine-grained** control over:

- **Browser** creation (light tasks only)
- **Page** and **context** creation (auth, route blocking)
- **Navigation** phases
- **Final HTML** retrieval

Follow the recommended usage: - **Login** or advanced tasks in `on_page_context_created`

- **Custom headers** or logs in `before_goto` / `after_goto`
- **Scrolling** or final checks in `before_retrieve_html` / `before_return_html`
  Page Copy
  Page Copy
  - [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/hooks-auth/)

ESC to close

#### On this page

- [Example: Using Hooks in AsyncWebCrawler](https://docs.crawl4ai.com/advanced/hooks-auth/#example-using-hooks-in-asyncwebcrawler)
- [Hook Lifecycle Summary](https://docs.crawl4ai.com/advanced/hooks-auth/#hook-lifecycle-summary)
- [When to Handle Authentication](https://docs.crawl4ai.com/advanced/hooks-auth/#when-to-handle-authentication)
- [Additional Considerations](https://docs.crawl4ai.com/advanced/hooks-auth/#additional-considerations)
- [Conclusion](https://docs.crawl4ai.com/advanced/hooks-auth/#conclusion)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/adaptive-strategies

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/adaptive-strategies/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - Adaptive Strategies
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Advanced Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/#advanced-adaptive-strategies)
- [Overview](https://docs.crawl4ai.com/advanced/adaptive-strategies/#overview)
- [The Three-Layer Scoring System](https://docs.crawl4ai.com/advanced/adaptive-strategies/#the-three-layer-scoring-system)
- [Link Ranking Algorithm](https://docs.crawl4ai.com/advanced/adaptive-strategies/#link-ranking-algorithm)
- [Domain-Specific Configurations](https://docs.crawl4ai.com/advanced/adaptive-strategies/#domain-specific-configurations)
- [Performance Optimization](https://docs.crawl4ai.com/advanced/adaptive-strategies/#performance-optimization)
- [Debugging & Analysis](https://docs.crawl4ai.com/advanced/adaptive-strategies/#debugging-analysis)
- [Custom Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/#custom-strategies)
- [Best Practices](https://docs.crawl4ai.com/advanced/adaptive-strategies/#best-practices)
- [Next Steps](https://docs.crawl4ai.com/advanced/adaptive-strategies/#next-steps)

# Advanced Adaptive Strategies

## Overview

While the default adaptive crawling configuration works well for most use cases, understanding the underlying strategies and scoring mechanisms allows you to fine-tune the crawler for specific domains and requirements.

## The Three-Layer Scoring System

### 1. Coverage Score

Coverage measures how comprehensively your knowledge base covers the query terms and related concepts.

#### Mathematical Foundation

```
Coverage(K, Q) = Σ(t ∈ Q) score(t, K) / |Q|

where score(t, K) = doc_coverage(t) × (1 + freq_boost(t))
Copy
```

#### Components

- **Document Coverage** : Percentage of documents containing the term
- **Frequency Boost** : Logarithmic bonus for term frequency
- **Query Decomposition** : Handles multi-word queries intelligently

#### Tuning Coverage

```
# For technical documentation with specific terminology
config = AdaptiveConfig(
    confidence_threshold=0.85,  # Require high coverage
    top_k_links=5              # Cast wider net
)

# For general topics with synonyms
config = AdaptiveConfig(
    confidence_threshold=0.6,   # Lower threshold
    top_k_links=2              # More focused
)
Copy
```

### 2. Consistency Score

Consistency evaluates whether the information across pages is coherent and non-contradictory.

#### How It Works

1. Extracts key statements from each document
2. Compares statements across documents
3. Measures agreement vs. contradiction
4. Returns normalized score (0-1)

#### Practical Impact

- **High consistency ( >0.8)**: Information is reliable and coherent
- **Medium consistency (0.5-0.8)** : Some variation, but generally aligned
- **Low consistency ( <0.5)**: Conflicting information, need more sources

### 3. Saturation Score

Saturation detects when new pages stop providing novel information.

#### Detection Algorithm

```
# Tracks new unique terms per page
new_terms_page_1 = 50
new_terms_page_2 = 30  # 60% of first
new_terms_page_3 = 15  # 50% of second
new_terms_page_4 = 5   # 33% of third
# Saturation detected: rapidly diminishing returns
Copy
```

#### Configuration

```
config = AdaptiveConfig(
    min_gain_threshold=0.1  # Stop if <10% new information
)
Copy
```

## Link Ranking Algorithm

### Expected Information Gain

Each uncrawled link is scored based on:

```
ExpectedGain(link) = Relevance × Novelty × Authority
Copy
```

#### 1. Relevance Scoring

Uses BM25 algorithm on link preview text:

```
relevance = BM25(link.preview_text, query)
Copy
```

Factors: - Term frequency in preview - Inverse document frequency - Preview length normalization

#### 2. Novelty Estimation

Measures how different the link appears from already-crawled content:

```
novelty = 1 - max_similarity(preview, knowledge_base)
Copy
```

Prevents crawling duplicate or highly similar pages.

#### 3. Authority Calculation

URL structure and domain analysis:

```
authority = f(domain_rank, url_depth, url_structure)
Copy
```

Factors: - Domain reputation - URL depth (fewer slashes = higher authority) - Clean URL structure

## Domain-Specific Configurations

### Technical Documentation

```
tech_doc_config = AdaptiveConfig(
    confidence_threshold=0.85,
    max_pages=30,
    top_k_links=3,
    min_gain_threshold=0.05  # Keep crawling for small gains
)
Copy
```

Rationale: - High threshold ensures comprehensive coverage - Lower gain threshold captures edge cases - Moderate link following for depth

### News & Articles

```
news_config = AdaptiveConfig(
    confidence_threshold=0.6,
    max_pages=10,
    top_k_links=5,
    min_gain_threshold=0.15  # Stop quickly on repetition
)
Copy
```

Rationale: - Lower threshold (articles often repeat information) - Higher gain threshold (avoid duplicate stories) - More links per page (explore different perspectives)

### E-commerce

```
ecommerce_config = AdaptiveConfig(
    confidence_threshold=0.7,
    max_pages=20,
    top_k_links=2,
    min_gain_threshold=0.1
)
Copy
```

Rationale: - Balanced threshold for product variations - Focused link following (avoid infinite products) - Standard gain threshold

### Research & Academic

```
research_config = AdaptiveConfig(
    confidence_threshold=0.9,
    max_pages=50,
    top_k_links=4,
    min_gain_threshold=0.02  # Very low - capture citations
)
Copy
```

Rationale: - Very high threshold for completeness - Many pages allowed for thorough research - Very low gain threshold to capture references

## Performance Optimization

### Memory Management

```
# For large crawls, use streaming
config = AdaptiveConfig(
    max_pages=100,
    save_state=True,
    state_path="large_crawl.json"
)

# Periodically clean state
if len(state.knowledge_base) > 1000:
    # Keep only the top 500 most relevant docs
    top_content = adaptive.get_relevant_content(top_k=500)
    keep_indices = {d["index"] for d in top_content}
    state.knowledge_base = [
        doc for i, doc in enumerate(state.knowledge_base) if i in keep_indices
    ]
Copy
```

### Parallel Processing

```
# Use multiple start points
start_urls = [
    "https://docs.example.com/intro",
    "https://docs.example.com/api",
    "https://docs.example.com/guides"
]

# Crawl in parallel
tasks = [
    adaptive.digest(url, query)
    for url in start_urls
]
results = await asyncio.gather(*tasks)
Copy
```

## Debugging & Analysis

### Enable Verbose Logging

```
import logging

logging.basicConfig(level=logging.DEBUG)
adaptive = AdaptiveCrawler(crawler, config, verbose=True)
Copy
```

### Analyze Crawl Patterns

```
# After crawling
state = await adaptive.digest(start_url, query)

# Analyze link selection
print("Link selection order:")
for i, url in enumerate(state.crawl_order):
    print(f"{i+1}. {url}")

# Analyze term discovery
print("\nTerm discovery rate:")
for i, new_terms in enumerate(state.new_terms_history):
    print(f"Page {i+1}: {new_terms} new terms")

# Analyze score progression
print("\nScore progression:")
print(f"Coverage: {state.metrics['coverage_history']}")
print(f"Saturation: {state.metrics['saturation_history']}")
Copy
```

### Export for Analysis

```
# Export detailed metrics
import json

metrics = {
    "query": query,
    "total_pages": len(state.crawled_urls),
    "confidence": adaptive.confidence,
    "coverage_stats": adaptive.coverage_stats,
    "crawl_order": state.crawl_order,
    "term_frequencies": dict(state.term_frequencies),
    "new_terms_history": state.new_terms_history
}

with open("crawl_analysis.json", "w") as f:
    json.dump(metrics, f, indent=2)
Copy
```

## Custom Strategies

### Implementing a Custom Strategy

```
from crawl4ai.adaptive_crawler import CrawlStrategy

class DomainSpecificStrategy(CrawlStrategy):
    def calculate_coverage(self, state: CrawlState) -> float:
        # Custom coverage calculation
        # e.g., weight certain terms more heavily
        pass

    def calculate_consistency(self, state: CrawlState) -> float:
        # Custom consistency logic
        # e.g., domain-specific validation
        pass

    def rank_links(self, links: List[Link], state: CrawlState) -> List[Link]:
        # Custom link ranking
        # e.g., prioritize specific URL patterns
        pass

# Use custom strategy
adaptive = AdaptiveCrawler(
    crawler,
    config=config,
    strategy=DomainSpecificStrategy()
)
Copy
```

### Combining Strategies

```
class HybridStrategy(CrawlStrategy):
    def __init__(self):
        self.strategies = [
            TechnicalDocStrategy(),
            SemanticSimilarityStrategy(),
            URLPatternStrategy()
        ]

    def calculate_confidence(self, state: CrawlState) -> float:
        # Weighted combination of strategies
        scores = [s.calculate_confidence(state) for s in self.strategies]
        weights = [0.5, 0.3, 0.2]
        return sum(s * w for s, w in zip(scores, weights))
Copy
```

## Best Practices

### 1. Start Conservative

Begin with default settings and adjust based on results:

```
# Start with defaults
result = await adaptive.digest(url, query)

# Analyze and adjust
if adaptive.confidence < 0.7:
    config.max_pages += 10
    config.confidence_threshold -= 0.1
Copy
```

### 2. Monitor Resource Usage

```
import psutil

# Check memory before large crawls
memory_percent = psutil.virtual_memory().percent
if memory_percent > 80:
    config.max_pages = min(config.max_pages, 20)
Copy
```

### 3. Use Domain Knowledge

```
# For API documentation
if "api" in start_url:
    config.top_k_links = 2  # APIs have clear structure

# For blogs
if "blog" in start_url:
    config.min_gain_threshold = 0.2  # Avoid similar posts
Copy
```

### 4. Validate Results

```
# Always validate the knowledge base
relevant_content = adaptive.get_relevant_content(top_k=10)

# Check coverage
query_terms = set(query.lower().split())
covered_terms = set()

for doc in relevant_content:
    content_lower = doc['content'].lower()
    for term in query_terms:
        if term in content_lower:
            covered_terms.add(term)

coverage_ratio = len(covered_terms) / len(query_terms)
print(f"Query term coverage: {coverage_ratio:.0%}")
Copy
```

## Next Steps

- Explore [Custom Strategy Implementation](https://docs.crawl4ai.com/advanced/tutorials/custom-adaptive-strategies.md)
- Learn about [Knowledge Base Management](https://docs.crawl4ai.com/advanced/tutorials/knowledge-base-management.md)
- See [Performance Benchmarks](https://docs.crawl4ai.com/advanced/benchmarks/adaptive-performance.md)

Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/adaptive-strategies/)

ESC to close

#### On this page

- [Overview](https://docs.crawl4ai.com/advanced/adaptive-strategies/#overview)
- [The Three-Layer Scoring System](https://docs.crawl4ai.com/advanced/adaptive-strategies/#the-three-layer-scoring-system)
- [1. Coverage Score](https://docs.crawl4ai.com/advanced/adaptive-strategies/#1-coverage-score)
- [Mathematical Foundation](https://docs.crawl4ai.com/advanced/adaptive-strategies/#mathematical-foundation)
- [Components](https://docs.crawl4ai.com/advanced/adaptive-strategies/#components)
- [Tuning Coverage](https://docs.crawl4ai.com/advanced/adaptive-strategies/#tuning-coverage)
- [2. Consistency Score](https://docs.crawl4ai.com/advanced/adaptive-strategies/#2-consistency-score)
- [How It Works](https://docs.crawl4ai.com/advanced/adaptive-strategies/#how-it-works)
- [Practical Impact](https://docs.crawl4ai.com/advanced/adaptive-strategies/#practical-impact)
- [3. Saturation Score](https://docs.crawl4ai.com/advanced/adaptive-strategies/#3-saturation-score)
- [Detection Algorithm](https://docs.crawl4ai.com/advanced/adaptive-strategies/#detection-algorithm)
- [Configuration](https://docs.crawl4ai.com/advanced/adaptive-strategies/#configuration)
- [Link Ranking Algorithm](https://docs.crawl4ai.com/advanced/adaptive-strategies/#link-ranking-algorithm)
- [Expected Information Gain](https://docs.crawl4ai.com/advanced/adaptive-strategies/#expected-information-gain)
- [1. Relevance Scoring](https://docs.crawl4ai.com/advanced/adaptive-strategies/#1-relevance-scoring)
- [2. Novelty Estimation](https://docs.crawl4ai.com/advanced/adaptive-strategies/#2-novelty-estimation)
- [3. Authority Calculation](https://docs.crawl4ai.com/advanced/adaptive-strategies/#3-authority-calculation)
- [Domain-Specific Configurations](https://docs.crawl4ai.com/advanced/adaptive-strategies/#domain-specific-configurations)
- [Technical Documentation](https://docs.crawl4ai.com/advanced/adaptive-strategies/#technical-documentation)
- [News & Articles](https://docs.crawl4ai.com/advanced/adaptive-strategies/#news-articles)
- [E-commerce](https://docs.crawl4ai.com/advanced/adaptive-strategies/#e-commerce)
- [Research & Academic](https://docs.crawl4ai.com/advanced/adaptive-strategies/#research-academic)
- [Performance Optimization](https://docs.crawl4ai.com/advanced/adaptive-strategies/#performance-optimization)
- [Memory Management](https://docs.crawl4ai.com/advanced/adaptive-strategies/#memory-management)
- [Parallel Processing](https://docs.crawl4ai.com/advanced/adaptive-strategies/#parallel-processing)
- [Debugging & Analysis](https://docs.crawl4ai.com/advanced/adaptive-strategies/#debugging-analysis)
- [Enable Verbose Logging](https://docs.crawl4ai.com/advanced/adaptive-strategies/#enable-verbose-logging)
- [Analyze Crawl Patterns](https://docs.crawl4ai.com/advanced/adaptive-strategies/#analyze-crawl-patterns)
- [Export for Analysis](https://docs.crawl4ai.com/advanced/adaptive-strategies/#export-for-analysis)
- [Custom Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/#custom-strategies)
- [Implementing a Custom Strategy](https://docs.crawl4ai.com/advanced/adaptive-strategies/#implementing-a-custom-strategy)
- [Combining Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/#combining-strategies)
- [Best Practices](https://docs.crawl4ai.com/advanced/adaptive-strategies/#best-practices)
- [1. Start Conservative](https://docs.crawl4ai.com/advanced/adaptive-strategies/#1-start-conservative)
- [2. Monitor Resource Usage](https://docs.crawl4ai.com/advanced/adaptive-strategies/#2-monitor-resource-usage)
- [3. Use Domain Knowledge](https://docs.crawl4ai.com/advanced/adaptive-strategies/#3-use-domain-knowledge)
- [4. Validate Results](https://docs.crawl4ai.com/advanced/adaptive-strategies/#4-validate-results)
- [Next Steps](https://docs.crawl4ai.com/advanced/adaptive-strategies/#next-steps)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/advanced/virtual-scroll

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/advanced/virtual-scroll/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - Virtual Scroll
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/#virtual-scroll)
- [Understanding Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/#understanding-virtual-scroll)
- [Basic Usage](https://docs.crawl4ai.com/advanced/virtual-scroll/#basic-usage)
- [Configuration Parameters](https://docs.crawl4ai.com/advanced/virtual-scroll/#configuration-parameters)
- [Real-World Examples](https://docs.crawl4ai.com/advanced/virtual-scroll/#real-world-examples)
- [Virtual Scroll vs scan_full_page](https://docs.crawl4ai.com/advanced/virtual-scroll/#virtual-scroll-vs-scan_full_page)
- [Combining with Extraction](https://docs.crawl4ai.com/advanced/virtual-scroll/#combining-with-extraction)
- [Performance Tips](https://docs.crawl4ai.com/advanced/virtual-scroll/#performance-tips)
- [How It Works Internally](https://docs.crawl4ai.com/advanced/virtual-scroll/#how-it-works-internally)
- [Error Handling](https://docs.crawl4ai.com/advanced/virtual-scroll/#error-handling)
- [Complete Example](https://docs.crawl4ai.com/advanced/virtual-scroll/#complete-example)

# Virtual Scroll

Modern websites increasingly use **virtual scrolling** (also called windowed rendering or viewport rendering) to handle large datasets efficiently. This technique only renders visible items in the DOM, replacing content as users scroll. Popular examples include Twitter's timeline, Instagram's feed, and many data tables.
Crawl4AI's Virtual Scroll feature automatically detects and handles these scenarios, ensuring you capture **all content** , not just what's initially visible.

## Understanding Virtual Scroll

### The Problem

Traditional infinite scroll **appends** new content to existing content. Virtual scroll **replaces** content to maintain performance:

```
Traditional Scroll:          Virtual Scroll:
┌─────────────┐             ┌─────────────┐
│ Item 1      │             │ Item 11     │  <- Items 1-10 removed
│ Item 2      │             │ Item 12     │  <- Only visible items
│ ...         │             │ Item 13     │     in DOM
│ Item 10     │             │ Item 14     │
│ Item 11 NEW │             │ Item 15     │
│ Item 12 NEW │             └─────────────┘
└─────────────┘
DOM keeps growing           DOM size stays constant
Copy
```

Without proper handling, crawlers only capture the currently visible items, missing the rest of the content.

### Three Scrolling Scenarios

Crawl4AI's Virtual Scroll detects and handles three scenarios:

1. **No Change** - Content doesn't update on scroll (static page or end reached)
2. **Content Appended** - New items added to existing ones (traditional infinite scroll)
3. **Content Replaced** - Items replaced with new ones (true virtual scroll)

Only scenario 3 requires special handling, which Virtual Scroll automates.

## Basic Usage

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, VirtualScrollConfig

# Configure virtual scroll
virtual_config = VirtualScrollConfig(
    container_selector="#feed",      # CSS selector for scrollable container
    scroll_count=20,                 # Number of scrolls to perform
    scroll_by="container_height",    # How much to scroll each time
    wait_after_scroll=0.5           # Wait time (seconds) after each scroll
)

# Use in crawler configuration
config = CrawlerRunConfig(
    virtual_scroll_config=virtual_config
)

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url="https://example.com", config=config)
    # result.html contains ALL items from the virtual scroll
Copy
```

## Configuration Parameters

### VirtualScrollConfig

| Parameter            | Type           | Default              | Description                               |
| -------------------- | -------------- | -------------------- | ----------------------------------------- |
| `container_selector` | `str`          | Required             | CSS selector for the scrollable container |
| `scroll_count`       | `int`          | `10`                 | Maximum number of scrolls to perform      |
| `scroll_by`          | `str` or `int` | `"container_height"` | Scroll amount per step                    |
| `wait_after_scroll`  | `float`        | `0.5`                | Seconds to wait after each scroll         |

### Scroll By Options

- `"container_height"` - Scroll by the container's visible height
- `"page_height"` - Scroll by the viewport height
- `500` (integer) - Scroll by exact pixel amount

## Real-World Examples

### Twitter-like Timeline

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, VirtualScrollConfig, BrowserConfig

async def crawl_twitter_timeline():
    # Twitter replaces tweets as you scroll
    virtual_config = VirtualScrollConfig(
        container_selector="[data-testid='primaryColumn']",
        scroll_count=30,
        scroll_by="container_height",
        wait_after_scroll=1.0  # Twitter needs time to load
    )

    browser_config = BrowserConfig(headless=True)  # Set to False to watch it work
    config = CrawlerRunConfig(
        virtual_scroll_config=virtual_config
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://twitter.com/search?q=AI",
            config=config
        )

        # Extract tweet count
        import re
        tweets = re.findall(r'data-testid="tweet"', result.html)
        print(f"Captured {len(tweets)} tweets")
Copy
```

### Instagram Grid

```
async def crawl_instagram_grid():
    # Instagram uses virtualized grid for performance
    virtual_config = VirtualScrollConfig(
        container_selector="article",  # Main feed container
        scroll_count=50,               # More scrolls for grid layout
        scroll_by=800,                 # Fixed pixel scrolling
        wait_after_scroll=0.8
    )

    config = CrawlerRunConfig(
        virtual_scroll_config=virtual_config,
        screenshot=True  # Capture final state
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.instagram.com/explore/tags/photography/",
            config=config
        )

        # Count posts
        posts = result.html.count('class="post"')
        print(f"Captured {posts} posts from virtualized grid")
Copy
```

### Mixed Content (News Feed)

Some sites mix static and virtualized content:

```
async def crawl_mixed_feed():
    # Featured articles stay, regular articles virtualize
    virtual_config = VirtualScrollConfig(
        container_selector=".main-feed",
        scroll_count=25,
        scroll_by="container_height",
        wait_after_scroll=0.5
    )

    config = CrawlerRunConfig(
        virtual_scroll_config=virtual_config
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.example.com",
            config=config
        )

        # Featured articles remain throughout
        featured = result.html.count('class="featured-article"')
        regular = result.html.count('class="regular-article"')

        print(f"Featured (static): {featured}")
        print(f"Regular (virtualized): {regular}")
Copy
```

## Virtual Scroll vs scan_full_page

Both features handle dynamic content, but serve different purposes:
Feature | Virtual Scroll | scan_full_page
---|---|---
**Purpose** | Capture content that's replaced during scroll | Load content that's appended during scroll
**Use Case** | Twitter, Instagram, virtual tables | Traditional infinite scroll, lazy-loaded images
**DOM Behavior** | Replaces elements | Adds elements
**Memory Usage** | Efficient (merges content) | Can grow large
**Configuration** | Requires container selector | Works on full page

### When to Use Which?

Use **Virtual Scroll** when: - Content disappears as you scroll (Twitter timeline) - DOM element count stays relatively constant - You need ALL items from a virtualized list - Container-based scrolling (not full page)
Use **scan_full_page** when: - Content accumulates as you scroll - Images load lazily - Simple "load more" behavior - Full page scrolling

## Combining with Extraction

Virtual Scroll works seamlessly with extraction strategies:

```
from crawl4ai import LLMExtractionStrategy, LLMConfig

# Define extraction schema
schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "author": {"type": "string"},
            "content": {"type": "string"},
            "timestamp": {"type": "string"}
        }
    }
}

# Configure both virtual scroll and extraction
config = CrawlerRunConfig(
    virtual_scroll_config=VirtualScrollConfig(
        container_selector="#timeline",
        scroll_count=20
    ),
    extraction_strategy=LLMExtractionStrategy(
        llm_config=LLMConfig(provider="openai/gpt-4o-mini"),
        schema=schema
    )
)

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url="...", config=config)

    # Extracted data from ALL scrolled content
    import json
    posts = json.loads(result.extracted_content)
    print(f"Extracted {len(posts)} posts from virtual scroll")
Copy
```

## Performance Tips

1. **Container Selection** : Be specific with selectors. Using the correct container improves performance.
2. **Scroll Count** : Start conservative and increase as needed:

```
# Start with fewer scrolls
virtual_config = VirtualScrollConfig(
    container_selector="#feed",
    scroll_count=10  # Test with 10, increase if needed
)
Copy
```

3. **Wait Times** : Adjust based on site speed:

```
# Fast sites
wait_after_scroll=0.2

# Slower sites or heavy content
wait_after_scroll=1.5
Copy
```

4. **Debug Mode** : Set `headless=False` to watch scrolling:

```
browser_config = BrowserConfig(headless=False)
async with AsyncWebCrawler(config=browser_config) as crawler:
    # Watch the scrolling happen
Copy
```

## How It Works Internally

1. **Detection Phase** : Scrolls and compares HTML to detect behavior
2. **Capture Phase** : For replaced content, stores HTML chunks at each position
3. **Merge Phase** : Combines all chunks, removing duplicates based on text content
4. **Result** : Complete HTML with all unique items

The deduplication uses normalized text (lowercase, no spaces/symbols) to ensure accurate merging without false positives.

## Error Handling

Virtual Scroll handles errors gracefully:

```
# If container not found or scrolling fails
result = await crawler.arun(url="...", config=config)

if result.success:
    # Virtual scroll worked or wasn't needed
    print(f"Captured {len(result.html)} characters")
else:
    # Crawl failed entirely
    print(f"Error: {result.error_message}")
Copy
```

If the container isn't found, crawling continues normally without virtual scroll.

## Complete Example

See our [comprehensive example](https://docs.crawl4ai.com/docs/examples/virtual_scroll_example.py) that demonstrates: - Twitter-like feeds - Instagram grids

- Traditional infinite scroll - Mixed content scenarios - Performance comparisons

```
# Run the examples
cd docs/examples
python virtual_scroll_example.py
Copy
```

The example includes a local test server with different scrolling behaviors for experimentation.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/advanced/virtual-scroll/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/advanced/virtual-scroll/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/advanced/virtual-scroll/)

ESC to close

#### On this page

- [Understanding Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/#understanding-virtual-scroll)
- [The Problem](https://docs.crawl4ai.com/advanced/virtual-scroll/#the-problem)
- [Three Scrolling Scenarios](https://docs.crawl4ai.com/advanced/virtual-scroll/#three-scrolling-scenarios)
- [Basic Usage](https://docs.crawl4ai.com/advanced/virtual-scroll/#basic-usage)
- [Configuration Parameters](https://docs.crawl4ai.com/advanced/virtual-scroll/#configuration-parameters)
- [VirtualScrollConfig](https://docs.crawl4ai.com/advanced/virtual-scroll/#virtualscrollconfig)
- [Scroll By Options](https://docs.crawl4ai.com/advanced/virtual-scroll/#scroll-by-options)
- [Real-World Examples](https://docs.crawl4ai.com/advanced/virtual-scroll/#real-world-examples)
- [Twitter-like Timeline](https://docs.crawl4ai.com/advanced/virtual-scroll/#twitter-like-timeline)
- [Instagram Grid](https://docs.crawl4ai.com/advanced/virtual-scroll/#instagram-grid)
- [Mixed Content (News Feed)](https://docs.crawl4ai.com/advanced/virtual-scroll/#mixed-content-news-feed)
- [Virtual Scroll vs scan_full_page](https://docs.crawl4ai.com/advanced/virtual-scroll/#virtual-scroll-vs-scan_full_page)
- [When to Use Which?](https://docs.crawl4ai.com/advanced/virtual-scroll/#when-to-use-which)
- [Combining with Extraction](https://docs.crawl4ai.com/advanced/virtual-scroll/#combining-with-extraction)
- [Performance Tips](https://docs.crawl4ai.com/advanced/virtual-scroll/#performance-tips)
- [How It Works Internally](https://docs.crawl4ai.com/advanced/virtual-scroll/#how-it-works-internally)
- [Error Handling](https://docs.crawl4ai.com/advanced/virtual-scroll/#error-handling)
- [Complete Example](https://docs.crawl4ai.com/advanced/virtual-scroll/#complete-example)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/api/strategies

```
{"detail":"Not Found"}
```

---

## Fonte: https://docs.crawl4ai.com/apps

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/apps/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - Demo Apps
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [🚀 Crawl4AI Interactive Apps](https://docs.crawl4ai.com/apps/#crawl4ai-interactive-apps)
- [🎯 Available Apps](https://docs.crawl4ai.com/apps/#available-apps)
- [🚀 Why Use These Apps?](https://docs.crawl4ai.com/apps/#why-use-these-apps)
- [📢 Stay Updated](https://docs.crawl4ai.com/apps/#stay-updated)

# 🚀 Crawl4AI Interactive Apps

Welcome to the Crawl4AI Apps Hub - your gateway to interactive tools and demos that make web scraping more intuitive and powerful.

## 🛠️ Interactive Tools for Modern Web Scraping

Our apps are designed to make Crawl4AI more accessible and powerful. Whether you're learning browser automation, designing extraction strategies, or building complex scrapers, these tools provide visual, interactive ways to work with Crawl4AI's features.

## 🎯 Available Apps

Available

### 🎨 C4A-Script Interactive Editor

A visual, block-based programming environment for creating browser automation scripts. Perfect for beginners and experts alike!

- Drag-and-drop visual programming
- Real-time JavaScript generation
- Interactive tutorials
- Export to C4A-Script or JavaScript
- Live preview capabilities

[Launch Editor →](https://docs.crawl4ai.com/apps/c4a-script/)
Available

### 🧠 LLM Context Builder

Generate optimized context files for your favorite LLM when working with Crawl4AI. Get focused, relevant documentation based on your needs.

- Modular context generation
- Memory, reasoning & examples perspectives
- Component-based selection
- Vibe coding preset
- Download custom contexts

[Launch Builder →](https://docs.crawl4ai.com/apps/llmtxt/)
Coming Soon

### 🕸️ Web Scraping Playground

Test your scraping strategies on real websites with instant feedback. See how different configurations affect your results.

- Live website testing
- Side-by-side result comparison
- Performance metrics
- Export configurations

[Coming Soon](https://docs.crawl4ai.com/apps/)
Available

### 🔍 Crawl4AI Assistant (Chrome Extension)

Visual schema builder Chrome extension - click on webpage elements to generate extraction schemas and Python code!

- Visual element selection
- Container & field selection modes
- Smart selector generation
- Complete Python code generation
- One-click installation

[Install Extension →](https://docs.crawl4ai.com/apps/crawl4ai-assistant/)
Coming Soon

### 🧪 Extraction Lab

Experiment with different extraction strategies and see how they perform on your content. Compare LLM vs CSS vs XPath approaches.

- Strategy comparison tools
- Performance benchmarks
- Cost estimation for LLM strategies
- Best practice recommendations

[Coming Soon](https://docs.crawl4ai.com/apps/)
Coming Soon

### 🤖 AI Prompt Designer

Craft and test prompts for LLM-based extraction. See how different prompts affect extraction quality and costs.

- Prompt templates library
- A/B testing interface
- Token usage calculator
- Quality metrics

[Coming Soon](https://docs.crawl4ai.com/apps/)
Coming Soon

### 📊 Crawl Monitor

Real-time monitoring dashboard for your crawling operations. Track performance, debug issues, and optimize your scrapers.

- Real-time crawl statistics
- Error tracking and debugging
- Resource usage monitoring
- Historical analytics

[Coming Soon](https://docs.crawl4ai.com/apps/)

## 🚀 Why Use These Apps?

### 🎯 **Accelerate Learning**

Visual tools help you understand Crawl4AI's concepts faster than reading documentation alone.

### 💡 **Reduce Development Time**

Generate working code instantly instead of writing everything from scratch.

### 🔍 **Improve Quality**

Test and refine your approach before deploying to production.

### 🤝 **Community Driven**

These tools are built based on user feedback. Have an idea? [Let us know](https://github.com/unclecode/crawl4ai/issues)!

## 📢 Stay Updated

Want to know when new apps are released?

- ⭐ [Star us on GitHub](https://github.com/unclecode/crawl4ai) to get notifications
- 🐦 Follow [@unclecode](https://twitter.com/unclecode) for announcements
- 💬 Join our [Discord community](https://discord.gg/crawl4ai) for early access

---

Developer Resources
Building your own tools with Crawl4AI? Check out our [API Reference](https://docs.crawl4ai.com/api/async-webcrawler/) and [Integration Guide](https://docs.crawl4ai.com/advanced/advanced-features/) for comprehensive documentation.

#### On this page

- [🛠️ Interactive Tools for Modern Web Scraping](https://docs.crawl4ai.com/apps/#toc-heading-0--interactive-tools-for-modern-web-scraping)
- [🎯 Available Apps](https://docs.crawl4ai.com/apps/#available-apps)
- [🎨 C4A-Script Interactive Editor](https://docs.crawl4ai.com/apps/#toc-heading-2--c4a-script-interactive-editor)
- [🧠 LLM Context Builder](https://docs.crawl4ai.com/apps/#toc-heading-3--llm-context-builder)
- [🕸️ Web Scraping Playground](https://docs.crawl4ai.com/apps/#toc-heading-4--web-scraping-playground)
- [🔍 Crawl4AI Assistant (Chrome Extension)](https://docs.crawl4ai.com/apps/#toc-heading-5--crawl4ai-assistant-chrome-extension)
- [🧪 Extraction Lab](https://docs.crawl4ai.com/apps/#toc-heading-6--extraction-lab)
- [🤖 AI Prompt Designer](https://docs.crawl4ai.com/apps/#toc-heading-7--ai-prompt-designer)
- [📊 Crawl Monitor](https://docs.crawl4ai.com/apps/#toc-heading-8--crawl-monitor)
- [🚀 Why Use These Apps?](https://docs.crawl4ai.com/apps/#why-use-these-apps)
- [🎯 Accelerate Learning](https://docs.crawl4ai.com/apps/#accelerate-learning)
- [💡 Reduce Development Time](https://docs.crawl4ai.com/apps/#reduce-development-time)
- [🔍 Improve Quality](https://docs.crawl4ai.com/apps/#improve-quality)
- [🤝 Community Driven](https://docs.crawl4ai.com/apps/#community-driven)
- [📢 Stay Updated](https://docs.crawl4ai.com/apps/#stay-updated)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/apps/c4a-script

## Welcome to C4A-Script Tutorial!

C4A-Script is a simple language for web automation. This interactive tutorial will teach you:

- How to handle popups and banners
- Form filling and navigation
- Advanced automation techniques

Start Tutorial Skip

#### Edit Event

Command Type CLICK DOUBLE_CLICK RIGHT_CLICK TYPE SET SCROLL WAIT
Selector
Value
Direction UP DOWN LEFT RIGHT
Cancel Save

## C4A-Script Editor

📚 📋 🗑 🧩 ▶Run ⏺Record 📊

```
xxxxxxxxxx
```

1
1

```
​
```

### Recording Timeline

← Back Select All Clear Generate Script
Navigation
Wait
Mouse Actions
Keyboard
Control Flow
Variables
Procedures
Comments
Console Generated JS
$ Ready to run C4A scripts...
📋 ✏️

```
// JavaScript will appear here...
```

## Playground

🔄 ⛶
Step 1 of 9 Welcome
Let's start by waiting for the page to load.
← Previous Next →
×

---

## Fonte: https://docs.crawl4ai.com/core/page-interaction

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/page-interaction/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - Page Interaction
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/#page-interaction)
- [1. JavaScript Execution](https://docs.crawl4ai.com/core/page-interaction/#1-javascript-execution)
- [2. Wait Conditions](https://docs.crawl4ai.com/core/page-interaction/#2-wait-conditions)
- [3. Handling Dynamic Content](https://docs.crawl4ai.com/core/page-interaction/#3-handling-dynamic-content)
- [4. Timing Control](https://docs.crawl4ai.com/core/page-interaction/#4-timing-control)
- [5. Multi-Step Interaction Example](https://docs.crawl4ai.com/core/page-interaction/#5-multi-step-interaction-example)
- [6. Combine Interaction with Extraction](https://docs.crawl4ai.com/core/page-interaction/#6-combine-interaction-with-extraction)
- [7. Relevant CrawlerRunConfig Parameters](https://docs.crawl4ai.com/core/page-interaction/#7-relevant-crawlerrunconfig-parameters)
- [8. Conclusion](https://docs.crawl4ai.com/core/page-interaction/#8-conclusion)
- [9. Virtual Scrolling](https://docs.crawl4ai.com/core/page-interaction/#9-virtual-scrolling)

# Page Interaction

Crawl4AI provides powerful features for interacting with **dynamic** webpages, handling JavaScript execution, waiting for conditions, and managing multi-step flows. By combining **js_code** , **wait_for** , and certain **CrawlerRunConfig** parameters, you can:

1. Click “Load More” buttons
2. Fill forms and submit them
3. Wait for elements or data to appear
4. Reuse sessions across multiple steps

Below is a quick overview of how to do it.

---

## 1. JavaScript Execution

### Basic Execution

**`js_code`**in**`CrawlerRunConfig`**accepts either a single JS string or a list of JS snippets.
**Example** : We’ll scroll to the bottom of the page, then optionally click a “Load More” button.

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Single JS command
    config = CrawlerRunConfig(
        js_code="window.scrollTo(0, document.body.scrollHeight);"
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com",  # Example site
            config=config
        )
        print("Crawled length:", len(result.cleaned_html))

    # Multiple commands
    js_commands = [
        "window.scrollTo(0, document.body.scrollHeight);",
        # 'More' link on Hacker News
        "document.querySelector('a.morelink')?.click();",
    ]
    config = CrawlerRunConfig(js_code=js_commands)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com",  # Another pass
            config=config
        )
        print("After scroll+click, length:", len(result.cleaned_html))

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Relevant`CrawlerRunConfig` params**: - **`js_code`**: A string or list of strings with JavaScript to run after the page loads. -**`js_only`**: If set to`True` on subsequent calls, indicates we’re continuing an existing session without a new full navigation.

- **`session_id`**: If you want to keep the same page across multiple calls, specify an ID.

---

## 2. Wait Conditions

### 2.1 CSS-Based Waiting

Sometimes, you just want to wait for a specific element to appear. For example:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    config = CrawlerRunConfig(
        # Wait for at least 30 items on Hacker News
        wait_for="css:.athing:nth-child(30)"
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com",
            config=config
        )
        print("We have at least 30 items loaded!")
        # Rough check
        print("Total items in HTML:", result.cleaned_html.count("athing"))

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key param** : - **`wait_for="css:..."`**: Tells the crawler to wait until that CSS selector is present.

### 2.2 JavaScript-Based Waiting

For more complex conditions (e.g., waiting for content length to exceed a threshold), prefix `js:`:

```
wait_condition = """() => {
    const items = document.querySelectorAll('.athing');
    return items.length > 50;  // Wait for at least 51 items
}"""

config = CrawlerRunConfig(wait_for=f"js:{wait_condition}")
Copy
```

**Behind the Scenes** : Crawl4AI keeps polling the JS function until it returns `true` or a timeout occurs.

---

## 3. Handling Dynamic Content

Many modern sites require **multiple steps** : scrolling, clicking “Load More,” or updating via JavaScript. Below are typical patterns.

### 3.1 Load More Example (Hacker News “More” Link)

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Step 1: Load initial Hacker News page
    config = CrawlerRunConfig(
        wait_for="css:.athing:nth-child(30)"  # Wait for 30 items
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com",
            config=config
        )
        print("Initial items loaded.")

        # Step 2: Let's scroll and click the "More" link
        load_more_js = [
            "window.scrollTo(0, document.body.scrollHeight);",
            # The "More" link at page bottom
            "document.querySelector('a.morelink')?.click();"
        ]

        next_page_conf = CrawlerRunConfig(
            js_code=load_more_js,
            wait_for="""js:() => {
                return document.querySelectorAll('.athing').length > 30;
            }""",
            # Mark that we do not re-navigate, but run JS in the same session:
            js_only=True,
            session_id="hn_session"
        )

        # Re-use the same crawler session
        result2 = await crawler.arun(
            url="https://news.ycombinator.com",  # same URL but continuing session
            config=next_page_conf
        )
        total_items = result2.cleaned_html.count("athing")
        print("Items after load-more:", total_items)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key params** : - **`session_id="hn_session"`**: Keep the same page across multiple calls to`arun()`. - **`js_only=True`**: We’re not performing a full reload, just applying JS in the existing page. -**`wait_for`**with`js:` : Wait for item count to grow beyond 30.

---

### 3.2 Form Interaction

If the site has a search or login form, you can fill fields and submit them with **`js_code`**. For instance, if GitHub had a local search form:

```
js_form_interaction = """
document.querySelector('#your-search').value = 'TypeScript commits';
document.querySelector('form').submit();
"""

config = CrawlerRunConfig(
    js_code=js_form_interaction,
    wait_for="css:.commit"
)
result = await crawler.arun(url="https://github.com/search", config=config)
Copy
```

**In reality** : Replace IDs or classes with the real site’s form selectors.

---

## 4. Timing Control

1. **`page_timeout`**(ms): Overall page load or script execution time limit.
2. **`delay_before_return_html`**(seconds): Wait an extra moment before capturing the final HTML.
3. **`mean_delay`** & **`max_range`**: If you call`arun_many()` with multiple URLs, these add a random pause between each request.
   **Example** :

```
config = CrawlerRunConfig(
    page_timeout=60000,  # 60s limit
    delay_before_return_html=2.5
)
Copy
```

---

## 5. Multi-Step Interaction Example

Below is a simplified script that does multiple “Load More” clicks on GitHub’s TypeScript commits page. It **re-uses** the same session to accumulate new commits each time. The code includes the relevant **`CrawlerRunConfig`**parameters you’d rely on.

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def multi_page_commits():
    browser_cfg = BrowserConfig(
        headless=False,  # Visible for demonstration
        verbose=True
    )
    session_id = "github_ts_commits"

    base_wait = """js:() => {
        const commits = document.querySelectorAll('li.Box-sc-g0xbh4-0 h4');
        return commits.length > 0;
    }"""

    # Step 1: Load initial commits
    config1 = CrawlerRunConfig(
        wait_for=base_wait,
        session_id=session_id,
        cache_mode=CacheMode.BYPASS,
        # Not using js_only yet since it's our first load
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(
            url="https://github.com/microsoft/TypeScript/commits/main",
            config=config1
        )
        print("Initial commits loaded. Count:", result.cleaned_html.count("commit"))

        # Step 2: For subsequent pages, we run JS to click 'Next Page' if it exists
        js_next_page = """
        const selector = 'a[data-testid="pagination-next-button"]';
        const button = document.querySelector(selector);
        if (button) button.click();
        """

        # Wait until new commits appear
        wait_for_more = """js:() => {
            const commits = document.querySelectorAll('li.Box-sc-g0xbh4-0 h4');
            if (!window.firstCommit && commits.length>0) {
                window.firstCommit = commits[0].textContent;
                return false;
            }
            // If top commit changes, we have new commits
            const topNow = commits[0]?.textContent.trim();
            return topNow && topNow !== window.firstCommit;
        }"""

        for page in range(2):  # let's do 2 more "Next" pages
            config_next = CrawlerRunConfig(
                session_id=session_id,
                js_code=js_next_page,
                wait_for=wait_for_more,
                js_only=True,       # We're continuing from the open tab
                cache_mode=CacheMode.BYPASS
            )
            result2 = await crawler.arun(
                url="https://github.com/microsoft/TypeScript/commits/main",
                config=config_next
            )
            print(f"Page {page+2} commits count:", result2.cleaned_html.count("commit"))

        # Optionally kill session
        await crawler.crawler_strategy.kill_session(session_id)

async def main():
    await multi_page_commits()

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key Points** :

- **`session_id`**: Keep the same page open.
- **`js_code`**+**`wait_for`**+**`js_only=True`**: We do partial refreshes, waiting for new commits to appear.
- **`cache_mode=CacheMode.BYPASS`**ensures we always see fresh data each step.

---

## 6. Combine Interaction with Extraction

Once dynamic content is loaded, you can attach an **`extraction_strategy`**(like`JsonCssExtractionStrategy` or `LLMExtractionStrategy`). For example:

```
from crawl4ai import JsonCssExtractionStrategy

schema = {
    "name": "Commits",
    "baseSelector": "li.Box-sc-g0xbh4-0",
    "fields": [
        {"name": "title", "selector": "h4.markdown-title", "type": "text"}
    ]
}
config = CrawlerRunConfig(
    session_id="ts_commits_session",
    js_code=js_next_page,
    wait_for=wait_for_more,
    extraction_strategy=JsonCssExtractionStrategy(schema)
)
Copy
```

When done, check `result.extracted_content` for the JSON.

---

## 7. Relevant `CrawlerRunConfig` Parameters

Below are the key interaction-related parameters in `CrawlerRunConfig`. For a full list, see [Configuration Parameters](https://docs.crawl4ai.com/api/parameters/).

- **`js_code`**: JavaScript to run after initial load.
- **`js_only`**: If`True` , no new page navigation—only JS in the existing session.
- **`wait_for`**: CSS (`"css:..."`) or JS (`"js:..."`) expression to wait for.
- **`session_id`**: Reuse the same page across calls.
- **`cache_mode`**: Whether to read/write from the cache or bypass.
- **`remove_overlay_elements`**: Remove certain popups automatically.
- **`simulate_user`,`override_navigator` , `magic`**: Anti-bot or “human-like” interactions.

---

## 8. Conclusion

Crawl4AI’s **page interaction** features let you:

1. **Execute JavaScript** for scrolling, clicks, or form filling.
2. **Wait** for CSS or custom JS conditions before capturing data.
3. **Handle** multi-step flows (like “Load More”) with partial reloads or persistent sessions.
4. Combine with **structured extraction** for dynamic sites.
   With these tools, you can scrape modern, interactive webpages confidently. For advanced hooking, user simulation, or in-depth config, check the [API reference](https://docs.crawl4ai.com/api/parameters/) or related advanced docs. Happy scripting!

---

## 9. Virtual Scrolling

For sites that use **virtual scrolling** (where content is replaced rather than appended as you scroll, like Twitter or Instagram), Crawl4AI provides a dedicated `VirtualScrollConfig`:

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, VirtualScrollConfig

async def crawl_twitter_timeline():
    # Configure virtual scroll for Twitter-like feeds
    virtual_config = VirtualScrollConfig(
        container_selector="[data-testid='primaryColumn']",  # Twitter's main column
        scroll_count=30,                # Scroll 30 times
        scroll_by="container_height",   # Scroll by container height each time
        wait_after_scroll=1.0          # Wait 1 second after each scroll
    )

    config = CrawlerRunConfig(
        virtual_scroll_config=virtual_config
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://twitter.com/search?q=AI",
            config=config
        )
        # result.html now contains ALL tweets from the virtual scroll
Copy
```

### Virtual Scroll vs JavaScript Scrolling

| Feature               | Virtual Scroll                     | JS Code Scrolling                    |
| --------------------- | ---------------------------------- | ------------------------------------ |
| **Use Case**          | Content replaced during scroll     | Content appended or simple scroll    |
| **Configuration**     | `VirtualScrollConfig` object       | `js_code` with scroll commands       |
| **Automatic Merging** | Yes - merges all unique content    | No - captures final state only       |
| **Best For**          | Twitter, Instagram, virtual tables | Traditional pages, load more buttons |

For detailed examples and configuration options, see the [Virtual Scroll documentation](https://docs.crawl4ai.com/advanced/virtual-scroll/).
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/page-interaction/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/page-interaction/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/page-interaction/)

ESC to close

#### On this page

- [1. JavaScript Execution](https://docs.crawl4ai.com/core/page-interaction/#1-javascript-execution)
- [Basic Execution](https://docs.crawl4ai.com/core/page-interaction/#basic-execution)
- [2. Wait Conditions](https://docs.crawl4ai.com/core/page-interaction/#2-wait-conditions)
- [2.1 CSS-Based Waiting](https://docs.crawl4ai.com/core/page-interaction/#21-css-based-waiting)
- [2.2 JavaScript-Based Waiting](https://docs.crawl4ai.com/core/page-interaction/#22-javascript-based-waiting)
- [3. Handling Dynamic Content](https://docs.crawl4ai.com/core/page-interaction/#3-handling-dynamic-content)
- [3.1 Load More Example (Hacker News “More” Link)](https://docs.crawl4ai.com/core/page-interaction/#31-load-more-example-hacker-news-more-link)
- [3.2 Form Interaction](https://docs.crawl4ai.com/core/page-interaction/#32-form-interaction)
- [4. Timing Control](https://docs.crawl4ai.com/core/page-interaction/#4-timing-control)
- [5. Multi-Step Interaction Example](https://docs.crawl4ai.com/core/page-interaction/#5-multi-step-interaction-example)
- [6. Combine Interaction with Extraction](https://docs.crawl4ai.com/core/page-interaction/#6-combine-interaction-with-extraction)
- [7. Relevant CrawlerRunConfig Parameters](https://docs.crawl4ai.com/core/page-interaction/#7-relevant-crawlerrunconfig-parameters)
- [8. Conclusion](https://docs.crawl4ai.com/core/page-interaction/#8-conclusion)
- [9. Virtual Scrolling](https://docs.crawl4ai.com/core/page-interaction/#9-virtual-scrolling)
- [Virtual Scroll vs JavaScript Scrolling](https://docs.crawl4ai.com/core/page-interaction/#virtual-scroll-vs-javascript-scrolling)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/adaptive-crawling

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/adaptive-crawling/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - Adaptive Crawling
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Adaptive Web Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/#adaptive-web-crawling)
- [Introduction](https://docs.crawl4ai.com/core/adaptive-crawling/#introduction)
- [Key Concepts](https://docs.crawl4ai.com/core/adaptive-crawling/#key-concepts)
- [Quick Start](https://docs.crawl4ai.com/core/adaptive-crawling/#quick-start)
- [Crawling Strategies](https://docs.crawl4ai.com/core/adaptive-crawling/#crawling-strategies)
- [When to Use Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/#when-to-use-adaptive-crawling)
- [Understanding the Output](https://docs.crawl4ai.com/core/adaptive-crawling/#understanding-the-output)
- [Persistence and Resumption](https://docs.crawl4ai.com/core/adaptive-crawling/#persistence-and-resumption)
- [Best Practices](https://docs.crawl4ai.com/core/adaptive-crawling/#best-practices)
- [Examples](https://docs.crawl4ai.com/core/adaptive-crawling/#examples)
- [Next Steps](https://docs.crawl4ai.com/core/adaptive-crawling/#next-steps)
- [FAQ](https://docs.crawl4ai.com/core/adaptive-crawling/#faq)

# Adaptive Web Crawling

## Introduction

Traditional web crawlers follow predetermined patterns, crawling pages blindly without knowing when they've gathered enough information. **Adaptive Crawling** changes this paradigm by introducing intelligence into the crawling process.
Think of it like research: when you're looking for information, you don't read every book in the library. You stop when you've found sufficient information to answer your question. That's exactly what Adaptive Crawling does for web scraping.

## Key Concepts

### The Problem It Solves

When crawling websites for specific information, you face two challenges: 1. **Under-crawling** : Stopping too early and missing crucial information 2. **Over-crawling** : Wasting resources by crawling irrelevant pages
Adaptive Crawling solves both by using a three-layer scoring system that determines when you have "enough" information.

### How It Works

The AdaptiveCrawler uses three metrics to measure information sufficiency:

- **Coverage** : How well your collected pages cover the query terms
- **Consistency** : Whether the information is coherent across pages
- **Saturation** : Detecting when new pages aren't adding new information

When these metrics indicate sufficient information has been gathered, crawling stops automatically.

## Quick Start

### Basic Usage

```
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        # Create an adaptive crawler (config is optional)
        adaptive = AdaptiveCrawler(crawler)

        # Start crawling with a query
        result = await adaptive.digest(
            start_url="https://docs.python.org/3/",
            query="async context managers"
        )

        # View statistics
        adaptive.print_stats()

        # Get the most relevant content
        relevant_pages = adaptive.get_relevant_content(top_k=5)
        for page in relevant_pages:
            print(f"- {page['url']} (score: {page['score']:.2f})")
Copy
```

### Configuration Options

```
from crawl4ai import AdaptiveConfig

config = AdaptiveConfig(
    confidence_threshold=0.8,    # Stop when 80% confident (default: 0.7)
    max_pages=30,               # Maximum pages to crawl (default: 20)
    top_k_links=5,              # Links to follow per page (default: 3)
    min_gain_threshold=0.05     # Minimum expected gain to continue (default: 0.1)
)

adaptive = AdaptiveCrawler(crawler, config)
Copy
```

## Crawling Strategies

Adaptive Crawling supports two distinct strategies for determining information sufficiency:

### Statistical Strategy (Default)

The statistical strategy uses pure information theory and term-based analysis:

- **Fast and efficient** - No API calls or model loading
- **Term-based coverage** - Analyzes query term presence and distribution
- **No external dependencies** - Works offline
- **Best for** : Well-defined queries with specific terminology

```
# Default configuration uses statistical strategy
config = AdaptiveConfig(
    strategy="statistical",  # This is the default
    confidence_threshold=0.8
)
Copy
```

### Embedding Strategy

The embedding strategy uses semantic embeddings for deeper understanding:

- **Semantic understanding** - Captures meaning beyond exact term matches
- **Query expansion** - Automatically generates query variations
- **Gap-driven selection** - Identifies semantic gaps in knowledge
- **Validation-based stopping** - Uses held-out queries to validate coverage
- **Best for** : Complex queries, ambiguous topics, conceptual understanding

```
# Configure embedding strategy
config = AdaptiveConfig(
    strategy="embedding",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # Default
    n_query_variations=10,  # Generate 10 query variations
    embedding_min_confidence_threshold=0.1  # Stop if completely irrelevant
)

# With custom LLM provider for query expansion (recommended)
from crawl4ai import LLMConfig

config = AdaptiveConfig(
    strategy="embedding",
    embedding_llm_config=LLMConfig(
        provider='openai/text-embedding-3-small',
        api_token='your-api-key',
        temperature=0.7
    )
)

# Alternative: Dictionary format (backward compatible)
config = AdaptiveConfig(
    strategy="embedding",
    embedding_llm_config={
        'provider': 'openai/text-embedding-3-small',
        'api_token': 'your-api-key'
    }
)
Copy
```

### Strategy Comparison

| Feature                 | Statistical                    | Embedding              |
| ----------------------- | ------------------------------ | ---------------------- |
| **Speed**               | Very fast                      | Moderate (API calls)   |
| **Cost**                | Free                           | Depends on provider    |
| **Accuracy**            | Good for exact terms           | Excellent for concepts |
| **Dependencies**        | None                           | Embedding model/API    |
| **Query Understanding** | Literal                        | Semantic               |
| **Best Use Case**       | Technical docs, specific terms | Research, broad topics |

### Embedding Strategy Configuration

The embedding strategy offers fine-tuned control through several parameters:

```
config = AdaptiveConfig(
    strategy="embedding",

    # Model configuration
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    embedding_llm_config=None,  # Use for API-based embeddings

    # Query expansion
    n_query_variations=10,  # Number of query variations to generate

    # Coverage parameters
    embedding_coverage_radius=0.2,  # Distance threshold for coverage
    embedding_k_exp=3.0,  # Exponential decay factor (higher = stricter)

    # Stopping criteria
    embedding_min_relative_improvement=0.1,  # Min improvement to continue
    embedding_validation_min_score=0.3,  # Min validation score
    embedding_min_confidence_threshold=0.1,  # Below this = irrelevant

    # Link selection
    embedding_overlap_threshold=0.85,  # Similarity for deduplication

    # Display confidence mapping
    embedding_quality_min_confidence=0.7,  # Min displayed confidence
    embedding_quality_max_confidence=0.95  # Max displayed confidence
)
Copy
```

### Handling Irrelevant Queries

The embedding strategy can detect when a query is completely unrelated to the content:

```
# This will stop quickly with low confidence
result = await adaptive.digest(
    start_url="https://docs.python.org/3/",
    query="how to cook pasta"  # Irrelevant to Python docs
)

# Check if query was irrelevant
if result.metrics.get('is_irrelevant', False):
    print("Query is unrelated to the content!")
Copy
```

## When to Use Adaptive Crawling

### Perfect For:

- **Research Tasks** : Finding comprehensive information about a topic
- **Question Answering** : Gathering sufficient context to answer specific queries
- **Knowledge Base Building** : Creating focused datasets for AI/ML applications
- **Competitive Intelligence** : Collecting complete information about specific products/features

### Not Recommended For:

- **Full Site Archiving** : When you need every page regardless of content
- **Structured Data Extraction** : When targeting specific, known page patterns
- **Real-time Monitoring** : When you need continuous updates

## Understanding the Output

### Confidence Score

The confidence score (0-1) indicates how sufficient the gathered information is: - **0.0-0.3** : Insufficient information, needs more crawling - **0.3-0.6** : Partial information, may answer basic queries - **0.6-0.7** : Good coverage, can answer most queries - **0.7-1.0** : Excellent coverage, comprehensive information

### Statistics Display

```
adaptive.print_stats(detailed=False)  # Summary table
adaptive.print_stats(detailed=True)   # Detailed metrics
Copy
```

The summary shows: - Pages crawled vs. confidence achieved - Coverage, consistency, and saturation scores - Crawling efficiency metrics

## Persistence and Resumption

### Saving Progress

```
config = AdaptiveConfig(
    save_state=True,
    state_path="my_crawl_state.json"
)

# Crawl will auto-save progress
result = await adaptive.digest(start_url, query)
Copy
```

### Resuming a Crawl

```
# Resume from saved state
result = await adaptive.digest(
    start_url,
    query,
    resume_from="my_crawl_state.json"
)
Copy
```

### Exporting Knowledge Base

```
# Export collected pages to JSONL
adaptive.export_knowledge_base("knowledge_base.jsonl")

# Import into another session
new_adaptive = AdaptiveCrawler(crawler)
new_adaptive.import_knowledge_base("knowledge_base.jsonl")
Copy
```

## Best Practices

### 1. Query Formulation

- Use specific, descriptive queries
- Include key terms you expect to find
- Avoid overly broad queries

### 2. Threshold Tuning

- Start with default (0.7) for general use
- Lower to 0.5-0.6 for exploratory crawling
- Raise to 0.8+ for exhaustive coverage

### 3. Performance Optimization

- Use appropriate `max_pages` limits
- Adjust `top_k_links` based on site structure
- Enable caching for repeat crawls

### 4. Link Selection

- The crawler prioritizes links based on:
- Relevance to query
- Expected information gain
- URL structure and depth

## Examples

### Research Assistant

```
# Gather information about a programming concept
result = await adaptive.digest(
    start_url="https://realpython.com",
    query="python decorators implementation patterns"
)

# Get the most relevant excerpts
for doc in adaptive.get_relevant_content(top_k=3):
    print(f"\nFrom: {doc['url']}")
    print(f"Relevance: {doc['score']:.2%}")
    print(doc['content'][:500] + "...")
Copy
```

### Knowledge Base Builder

```
# Build a focused knowledge base about machine learning
queries = [
    "supervised learning algorithms",
    "neural network architectures",
    "model evaluation metrics"
]

for query in queries:
    await adaptive.digest(
        start_url="https://scikit-learn.org/stable/",
        query=query
    )

# Export combined knowledge base
adaptive.export_knowledge_base("ml_knowledge.jsonl")
Copy
```

### API Documentation Crawler

```
# Intelligently crawl API documentation
config = AdaptiveConfig(
    confidence_threshold=0.85,  # Higher threshold for completeness
    max_pages=30
)

adaptive = AdaptiveCrawler(crawler, config)
result = await adaptive.digest(
    start_url="https://api.example.com/docs",
    query="authentication endpoints rate limits"
)
Copy
```

## Next Steps

- Learn about [Advanced Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
- Explore the [AdaptiveCrawler API Reference](https://docs.crawl4ai.com/api/adaptive-crawler/)
- See more [Examples](https://github.com/unclecode/crawl4ai/tree/main/docs/examples/adaptive_crawling)

## FAQ

**Q: How is this different from traditional crawling?** A: Traditional crawling follows fixed patterns (BFS/DFS). Adaptive crawling makes intelligent decisions about which links to follow and when to stop based on information gain.
**Q: Can I use this with JavaScript-heavy sites?** A: Yes! AdaptiveCrawler inherits all capabilities from AsyncWebCrawler, including JavaScript execution.
**Q: How does it handle large websites?** A: The algorithm naturally limits crawling to relevant sections. Use `max_pages` as a safety limit.
**Q: Can I customize the scoring algorithms?** A: Advanced users can implement custom strategies. See [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/).
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/adaptive-crawling/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/adaptive-crawling/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/adaptive-crawling/)

ESC to close

#### On this page

- [Introduction](https://docs.crawl4ai.com/core/adaptive-crawling/#introduction)
- [Key Concepts](https://docs.crawl4ai.com/core/adaptive-crawling/#key-concepts)
- [The Problem It Solves](https://docs.crawl4ai.com/core/adaptive-crawling/#the-problem-it-solves)
- [How It Works](https://docs.crawl4ai.com/core/adaptive-crawling/#how-it-works)
- [Quick Start](https://docs.crawl4ai.com/core/adaptive-crawling/#quick-start)
- [Basic Usage](https://docs.crawl4ai.com/core/adaptive-crawling/#basic-usage)
- [Configuration Options](https://docs.crawl4ai.com/core/adaptive-crawling/#configuration-options)
- [Crawling Strategies](https://docs.crawl4ai.com/core/adaptive-crawling/#crawling-strategies)
- [Statistical Strategy (Default)](https://docs.crawl4ai.com/core/adaptive-crawling/#statistical-strategy-default)
- [Embedding Strategy](https://docs.crawl4ai.com/core/adaptive-crawling/#embedding-strategy)
- [Strategy Comparison](https://docs.crawl4ai.com/core/adaptive-crawling/#strategy-comparison)
- [Embedding Strategy Configuration](https://docs.crawl4ai.com/core/adaptive-crawling/#embedding-strategy-configuration)
- [Handling Irrelevant Queries](https://docs.crawl4ai.com/core/adaptive-crawling/#handling-irrelevant-queries)
- [When to Use Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/#when-to-use-adaptive-crawling)
- [Perfect For:](https://docs.crawl4ai.com/core/adaptive-crawling/#perfect-for)
- [Not Recommended For:](https://docs.crawl4ai.com/core/adaptive-crawling/#not-recommended-for)
- [Understanding the Output](https://docs.crawl4ai.com/core/adaptive-crawling/#understanding-the-output)
- [Confidence Score](https://docs.crawl4ai.com/core/adaptive-crawling/#confidence-score)
- [Statistics Display](https://docs.crawl4ai.com/core/adaptive-crawling/#statistics-display)
- [Persistence and Resumption](https://docs.crawl4ai.com/core/adaptive-crawling/#persistence-and-resumption)
- [Saving Progress](https://docs.crawl4ai.com/core/adaptive-crawling/#saving-progress)
- [Resuming a Crawl](https://docs.crawl4ai.com/core/adaptive-crawling/#resuming-a-crawl)
- [Exporting Knowledge Base](https://docs.crawl4ai.com/core/adaptive-crawling/#exporting-knowledge-base)
- [Best Practices](https://docs.crawl4ai.com/core/adaptive-crawling/#best-practices)
- [1. Query Formulation](https://docs.crawl4ai.com/core/adaptive-crawling/#1-query-formulation)
- [2. Threshold Tuning](https://docs.crawl4ai.com/core/adaptive-crawling/#2-threshold-tuning)
- [3. Performance Optimization](https://docs.crawl4ai.com/core/adaptive-crawling/#3-performance-optimization)
- [4. Link Selection](https://docs.crawl4ai.com/core/adaptive-crawling/#4-link-selection)
- [Examples](https://docs.crawl4ai.com/core/adaptive-crawling/#examples)
- [Research Assistant](https://docs.crawl4ai.com/core/adaptive-crawling/#research-assistant)
- [Knowledge Base Builder](https://docs.crawl4ai.com/core/adaptive-crawling/#knowledge-base-builder)
- [API Documentation Crawler](https://docs.crawl4ai.com/core/adaptive-crawling/#api-documentation-crawler)
- [Next Steps](https://docs.crawl4ai.com/core/adaptive-crawling/#next-steps)
- [FAQ](https://docs.crawl4ai.com/core/adaptive-crawling/#faq)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/deep-crawling

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/deep-crawling/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - Deep Crawling
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/#deep-crawling)
- [1. Quick Example](https://docs.crawl4ai.com/core/deep-crawling/#1-quick-example)
- [2. Understanding Deep Crawling Strategy Options](https://docs.crawl4ai.com/core/deep-crawling/#2-understanding-deep-crawling-strategy-options)
- [3. Streaming vs. Non-Streaming Results](https://docs.crawl4ai.com/core/deep-crawling/#3-streaming-vs-non-streaming-results)
- [4. Filtering Content with Filter Chains](https://docs.crawl4ai.com/core/deep-crawling/#4-filtering-content-with-filter-chains)
- [5. Using Scorers for Prioritized Crawling](https://docs.crawl4ai.com/core/deep-crawling/#5-using-scorers-for-prioritized-crawling)
- [6. Advanced Filtering Techniques](https://docs.crawl4ai.com/core/deep-crawling/#6-advanced-filtering-techniques)
- [7. Building a Complete Advanced Crawler](https://docs.crawl4ai.com/core/deep-crawling/#7-building-a-complete-advanced-crawler)
- [8. Limiting and Controlling Crawl Size](https://docs.crawl4ai.com/core/deep-crawling/#8-limiting-and-controlling-crawl-size)
- [9. Common Pitfalls & Tips](https://docs.crawl4ai.com/core/deep-crawling/#9-common-pitfalls-tips)
- [10. Summary & Next Steps](https://docs.crawl4ai.com/core/deep-crawling/#10-summary-next-steps)

# Deep Crawling

One of Crawl4AI's most powerful features is its ability to perform **configurable deep crawling** that can explore websites beyond a single page. With fine-tuned control over crawl depth, domain boundaries, and content filtering, Crawl4AI gives you the tools to extract precisely the content you need.
In this tutorial, you'll learn:

1. How to set up a **Basic Deep Crawler** with BFS strategy
2. Understanding the difference between **streamed and non-streamed** output
3. Implementing **filters and scorers** to target specific content
4. Creating **advanced filtering chains** for sophisticated crawls
5. Using **BestFirstCrawling** for intelligent exploration prioritization

> **Prerequisites**
>
> - You’ve completed or read [AsyncWebCrawler Basics](https://docs.crawl4ai.com/core/simple-crawling/) to understand how to run a simple crawl.
> - You know how to configure `CrawlerRunConfig`.

---

## 1. Quick Example

Here's a minimal code snippet that implements a basic deep crawl using the **BFSDeepCrawlStrategy** :

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

async def main():
    # Configure a 2-level deep crawl
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://example.com", config=config)

        print(f"Crawled {len(results)} pages in total")

        # Access individual results
        for result in results[:3]:  # Show first 3 results
            print(f"URL: {result.url}")
            print(f"Depth: {result.metadata.get('depth', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**What's happening?**

- `BFSDeepCrawlStrategy(max_depth=2, include_external=False)` instructs Crawl4AI to: - Crawl the starting page (depth 0) plus 2 more levels - Stay within the same domain (don't follow external links) - Each result contains metadata like the crawl depth - Results are returned as a list after all crawling is complete

---

## 2. Understanding Deep Crawling Strategy Options

### 2.1 BFSDeepCrawlStrategy (Breadth-First Search)

The **BFSDeepCrawlStrategy** uses a breadth-first approach, exploring all links at one depth before moving deeper:

```
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

# Basic configuration
strategy = BFSDeepCrawlStrategy(
    max_depth=2,               # Crawl initial page + 2 levels deep
    include_external=False,    # Stay within the same domain
    max_pages=50,              # Maximum number of pages to crawl (optional)
    score_threshold=0.3,       # Minimum score for URLs to be crawled (optional)
)
Copy
```

**Key parameters:** - **`max_depth`**: Number of levels to crawl beyond the starting page -**`include_external`**: Whether to follow links to other domains -**`max_pages`**: Maximum number of pages to crawl (default: infinite) -**`score_threshold`**: Minimum score for URLs to be crawled (default: -inf) -**`filter_chain`**: FilterChain instance for URL filtering -**`url_scorer`**: Scorer instance for evaluating URLs

### 2.2 DFSDeepCrawlStrategy (Depth-First Search)

The **DFSDeepCrawlStrategy** uses a depth-first approach, explores as far down a branch as possible before backtracking.

```
from crawl4ai.deep_crawling import DFSDeepCrawlStrategy

# Basic configuration
strategy = DFSDeepCrawlStrategy(
    max_depth=2,               # Crawl initial page + 2 levels deep
    include_external=False,    # Stay within the same domain
    max_pages=30,              # Maximum number of pages to crawl (optional)
    score_threshold=0.5,       # Minimum score for URLs to be crawled (optional)
)
Copy
```

**Key parameters:** - **`max_depth`**: Number of levels to crawl beyond the starting page -**`include_external`**: Whether to follow links to other domains -**`max_pages`**: Maximum number of pages to crawl (default: infinite) -**`score_threshold`**: Minimum score for URLs to be crawled (default: -inf) -**`filter_chain`**: FilterChain instance for URL filtering -**`url_scorer`**: Scorer instance for evaluating URLs

### 2.3 BestFirstCrawlingStrategy (⭐️ - Recommended Deep crawl strategy)

For more intelligent crawling, use **BestFirstCrawlingStrategy** with scorers to prioritize the most relevant pages:

```
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

# Create a scorer
scorer = KeywordRelevanceScorer(
    keywords=["crawl", "example", "async", "configuration"],
    weight=0.7
)

# Configure the strategy
strategy = BestFirstCrawlingStrategy(
    max_depth=2,
    include_external=False,
    url_scorer=scorer,
    max_pages=25,              # Maximum number of pages to crawl (optional)
)
Copy
```

This crawling approach: - Evaluates each discovered URL based on scorer criteria - Visits higher-scoring pages first - Helps focus crawl resources on the most relevant content - Can limit total pages crawled with `max_pages` - Does not need `score_threshold` as it naturally prioritizes by score

---

## 3. Streaming vs. Non-Streaming Results

Crawl4AI can return results in two modes:

### 3.1 Non-Streaming Mode (Default)

```
config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=1),
    stream=False  # Default behavior
)

async with AsyncWebCrawler() as crawler:
    # Wait for ALL results to be collected before returning
    results = await crawler.arun("https://example.com", config=config)

    for result in results:
        process_result(result)
Copy
```

**When to use non-streaming mode:** - You need the complete dataset before processing - You're performing batch operations on all results together - Crawl time isn't a critical factor

### 3.2 Streaming Mode

```
config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=1),
    stream=True  # Enable streaming
)

async with AsyncWebCrawler() as crawler:
    # Returns an async iterator
    async for result in await crawler.arun("https://example.com", config=config):
        # Process each result as it becomes available
        process_result(result)
Copy
```

**Benefits of streaming mode:** - Process results immediately as they're discovered - Start working with early results while crawling continues - Better for real-time applications or progressive display - Reduces memory pressure when handling many pages

---

## 4. Filtering Content with Filter Chains

Filters help you narrow down which pages to crawl. Combine multiple filters using **FilterChain** for powerful targeting.

### 4.1 Basic URL Pattern Filter

```
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter

# Only follow URLs containing "blog" or "docs"
url_filter = URLPatternFilter(patterns=["*blog*", "*docs*"])

config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(
        max_depth=1,
        filter_chain=FilterChain([url_filter])
    )
)
Copy
```

### 4.2 Combining Multiple Filters

```
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    URLPatternFilter,
    DomainFilter,
    ContentTypeFilter
)

# Create a chain of filters
filter_chain = FilterChain([
    # Only follow URLs with specific patterns
    URLPatternFilter(patterns=["*guide*", "*tutorial*"]),

    # Only crawl specific domains
    DomainFilter(
        allowed_domains=["docs.example.com"],
        blocked_domains=["old.docs.example.com"]
    ),

    # Only include specific content types
    ContentTypeFilter(allowed_types=["text/html"])
])

config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(
        max_depth=2,
        filter_chain=filter_chain
    )
)
Copy
```

### 4.3 Available Filter Types

Crawl4AI includes several specialized filters:

- **`URLPatternFilter`**: Matches URL patterns using wildcard syntax
- **`DomainFilter`**: Controls which domains to include or exclude
- **`ContentTypeFilter`**: Filters based on HTTP Content-Type
- **`ContentRelevanceFilter`**: Uses similarity to a text query
- **`SEOFilter`**: Evaluates SEO elements (meta tags, headers, etc.)

---

## 5. Using Scorers for Prioritized Crawling

Scorers assign priority values to discovered URLs, helping the crawler focus on the most relevant content first.

### 5.1 KeywordRelevanceScorer

```
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy

# Create a keyword relevance scorer
keyword_scorer = KeywordRelevanceScorer(
    keywords=["crawl", "example", "async", "configuration"],
    weight=0.7  # Importance of this scorer (0.0 to 1.0)
)

config = CrawlerRunConfig(
    deep_crawl_strategy=BestFirstCrawlingStrategy(
        max_depth=2,
        url_scorer=keyword_scorer
    ),
    stream=True  # Recommended with BestFirstCrawling
)

# Results will come in order of relevance score
async with AsyncWebCrawler() as crawler:
    async for result in await crawler.arun("https://example.com", config=config):
        score = result.metadata.get("score", 0)
        print(f"Score: {score:.2f} | {result.url}")
Copy
```

**How scorers work:** - Evaluate each discovered URL before crawling - Calculate relevance based on various signals - Help the crawler make intelligent choices about traversal order

---

## 6. Advanced Filtering Techniques

### 6.1 SEO Filter for Quality Assessment

The **SEOFilter** helps you identify pages with strong SEO characteristics:

```
from crawl4ai.deep_crawling.filters import FilterChain, SEOFilter

# Create an SEO filter that looks for specific keywords in page metadata
seo_filter = SEOFilter(
    threshold=0.5,  # Minimum score (0.0 to 1.0)
    keywords=["tutorial", "guide", "documentation"]
)

config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(
        max_depth=1,
        filter_chain=FilterChain([seo_filter])
    )
)
Copy
```

### 6.2 Content Relevance Filter

The **ContentRelevanceFilter** analyzes the actual content of pages:

```
from crawl4ai.deep_crawling.filters import FilterChain, ContentRelevanceFilter

# Create a content relevance filter
relevance_filter = ContentRelevanceFilter(
    query="Web crawling and data extraction with Python",
    threshold=0.7  # Minimum similarity score (0.0 to 1.0)
)

config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(
        max_depth=1,
        filter_chain=FilterChain([relevance_filter])
    )
)
Copy
```

This filter: - Measures semantic similarity between query and page content - It's a BM25-based relevance filter using head section content

---

## 7. Building a Complete Advanced Crawler

This example combines multiple techniques for a sophisticated crawl:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    DomainFilter,
    URLPatternFilter,
    ContentTypeFilter
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

async def run_advanced_crawler():
    # Create a sophisticated filter chain
    filter_chain = FilterChain([
        # Domain boundaries
        DomainFilter(
            allowed_domains=["docs.example.com"],
            blocked_domains=["old.docs.example.com"]
        ),

        # URL patterns to include
        URLPatternFilter(patterns=["*guide*", "*tutorial*", "*blog*"]),

        # Content type filtering
        ContentTypeFilter(allowed_types=["text/html"])
    ])

    # Create a relevance scorer
    keyword_scorer = KeywordRelevanceScorer(
        keywords=["crawl", "example", "async", "configuration"],
        weight=0.7
    )

    # Set up the configuration
    config = CrawlerRunConfig(
        deep_crawl_strategy=BestFirstCrawlingStrategy(
            max_depth=2,
            include_external=False,
            filter_chain=filter_chain,
            url_scorer=keyword_scorer
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        stream=True,
        verbose=True
    )

    # Execute the crawl
    results = []
    async with AsyncWebCrawler() as crawler:
        async for result in await crawler.arun("https://docs.example.com", config=config):
            results.append(result)
            score = result.metadata.get("score", 0)
            depth = result.metadata.get("depth", 0)
            print(f"Depth: {depth} | Score: {score:.2f} | {result.url}")

    # Analyze the results
    print(f"Crawled {len(results)} high-value pages")
    print(f"Average score: {sum(r.metadata.get('score', 0) for r in results) / len(results):.2f}")

    # Group by depth
    depth_counts = {}
    for result in results:
        depth = result.metadata.get("depth", 0)
        depth_counts[depth] = depth_counts.get(depth, 0) + 1

    print("Pages crawled by depth:")
    for depth, count in sorted(depth_counts.items()):
        print(f"  Depth {depth}: {count} pages")

if __name__ == "__main__":
    asyncio.run(run_advanced_crawler())
Copy
```

---

## 8. Limiting and Controlling Crawl Size

### 8.1 Using max_pages

You can limit the total number of pages crawled with the `max_pages` parameter:

```
# Limit to exactly 20 pages regardless of depth
strategy = BFSDeepCrawlStrategy(
    max_depth=3,
    max_pages=20
)
Copy
```

This feature is useful for: - Controlling API costs - Setting predictable execution times - Focusing on the most important content - Testing crawl configurations before full execution

### 8.2 Using score_threshold

For BFS and DFS strategies, you can set a minimum score threshold to only crawl high-quality pages:

```
# Only follow links with scores above 0.4
strategy = DFSDeepCrawlStrategy(
    max_depth=2,
    url_scorer=KeywordRelevanceScorer(keywords=["api", "guide", "reference"]),
    score_threshold=0.4  # Skip URLs with scores below this value
)
Copy
```

Note that for BestFirstCrawlingStrategy, score_threshold is not needed since pages are already processed in order of highest score first.

## 9. Common Pitfalls & Tips

1.**Set realistic limits.** Be cautious with `max_depth` values > 3, which can exponentially increase crawl size. Use `max_pages` to set hard limits. 2.**Don't neglect the scoring component.** BestFirstCrawling works best with well-tuned scorers. Experiment with keyword weights for optimal prioritization. 3.**Be a good web citizen.** Respect robots.txt. (disabled by default) 4.**Handle page errors gracefully.** Not all pages will be accessible. Check `result.status` when processing results. 5.**Balance breadth vs. depth.** Choose your strategy wisely - BFS for comprehensive coverage, DFS for deep exploration, BestFirst for focused relevance-based crawling. 6.**Preserve HTTPS for security.** If crawling HTTPS sites that redirect to HTTP, use `preserve_https_for_internal_links=True` to maintain secure connections:

```
config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=2),
    preserve_https_for_internal_links=True  # Keep HTTPS even if server redirects to HTTP
)
Copy
```

This is especially useful for security-conscious crawling or when dealing with sites that support both protocols.

---

## 10. Summary & Next Steps

In this **Deep Crawling with Crawl4AI** tutorial, you learned to:

- Configure **BFSDeepCrawlStrategy** , **DFSDeepCrawlStrategy** , and **BestFirstCrawlingStrategy**
- Process results in streaming or non-streaming mode
- Apply filters to target specific content
- Use scorers to prioritize the most relevant pages
- Limit crawls with `max_pages` and `score_threshold` parameters
- Build a complete advanced crawler with combined techniques

With these tools, you can efficiently extract structured data from websites at scale, focusing precisely on the content you need for your specific use case.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/deep-crawling/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/deep-crawling/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/deep-crawling/)

ESC to close

#### On this page

- [1. Quick Example](https://docs.crawl4ai.com/core/deep-crawling/#1-quick-example)
- [2. Understanding Deep Crawling Strategy Options](https://docs.crawl4ai.com/core/deep-crawling/#2-understanding-deep-crawling-strategy-options)
- [2.1 BFSDeepCrawlStrategy (Breadth-First Search)](https://docs.crawl4ai.com/core/deep-crawling/#21-bfsdeepcrawlstrategy-breadth-first-search)
- [2.2 DFSDeepCrawlStrategy (Depth-First Search)](https://docs.crawl4ai.com/core/deep-crawling/#22-dfsdeepcrawlstrategy-depth-first-search)
- [2.3 BestFirstCrawlingStrategy (⭐️ - Recommended Deep crawl strategy)](https://docs.crawl4ai.com/core/deep-crawling/#23-bestfirstcrawlingstrategy-recommended-deep-crawl-strategy)
- [3. Streaming vs. Non-Streaming Results](https://docs.crawl4ai.com/core/deep-crawling/#3-streaming-vs-non-streaming-results)
- [3.1 Non-Streaming Mode (Default)](https://docs.crawl4ai.com/core/deep-crawling/#31-non-streaming-mode-default)
- [3.2 Streaming Mode](https://docs.crawl4ai.com/core/deep-crawling/#32-streaming-mode)
- [4. Filtering Content with Filter Chains](https://docs.crawl4ai.com/core/deep-crawling/#4-filtering-content-with-filter-chains)
- [4.1 Basic URL Pattern Filter](https://docs.crawl4ai.com/core/deep-crawling/#41-basic-url-pattern-filter)
- [4.2 Combining Multiple Filters](https://docs.crawl4ai.com/core/deep-crawling/#42-combining-multiple-filters)
- [4.3 Available Filter Types](https://docs.crawl4ai.com/core/deep-crawling/#43-available-filter-types)
- [5. Using Scorers for Prioritized Crawling](https://docs.crawl4ai.com/core/deep-crawling/#5-using-scorers-for-prioritized-crawling)
- [5.1 KeywordRelevanceScorer](https://docs.crawl4ai.com/core/deep-crawling/#51-keywordrelevancescorer)
- [6. Advanced Filtering Techniques](https://docs.crawl4ai.com/core/deep-crawling/#6-advanced-filtering-techniques)
- [6.1 SEO Filter for Quality Assessment](https://docs.crawl4ai.com/core/deep-crawling/#61-seo-filter-for-quality-assessment)
- [6.2 Content Relevance Filter](https://docs.crawl4ai.com/core/deep-crawling/#62-content-relevance-filter)
- [7. Building a Complete Advanced Crawler](https://docs.crawl4ai.com/core/deep-crawling/#7-building-a-complete-advanced-crawler)
- [8. Limiting and Controlling Crawl Size](https://docs.crawl4ai.com/core/deep-crawling/#8-limiting-and-controlling-crawl-size)
- [8.1 Using max_pages](https://docs.crawl4ai.com/core/deep-crawling/#81-using-max_pages)
- [8.2 Using score_threshold](https://docs.crawl4ai.com/core/deep-crawling/#82-using-score_threshold)
- [9. Common Pitfalls & Tips](https://docs.crawl4ai.com/core/deep-crawling/#9-common-pitfalls-tips)
- [10. Summary & Next Steps](https://docs.crawl4ai.com/core/deep-crawling/#10-summary-next-steps)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/ask-ai

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/ask-ai/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- Ask AI
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

> Feedback

##### Search

xClose
Type to start searching

---

## Fonte: https://docs.crawl4ai.com/core/docker-deployment

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/docker-deployment/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - Docker Deployment
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Crawl4AI Docker Guide 🐳](https://docs.crawl4ai.com/core/docker-deployment/#crawl4ai-docker-guide)
- [Table of Contents](https://docs.crawl4ai.com/core/docker-deployment/#table-of-contents)
- [Prerequisites](https://docs.crawl4ai.com/core/docker-deployment/#prerequisites)
- [Installation](https://docs.crawl4ai.com/core/docker-deployment/#installation)
- [MCP (Model Context Protocol) Support](https://docs.crawl4ai.com/core/docker-deployment/#mcp-model-context-protocol-support)
- [Additional API Endpoints](https://docs.crawl4ai.com/core/docker-deployment/#additional-api-endpoints)
- [User-Provided Hooks API](https://docs.crawl4ai.com/core/docker-deployment/#user-provided-hooks-api)
- [Dockerfile Parameters](https://docs.crawl4ai.com/core/docker-deployment/#dockerfile-parameters)
- [Using the API](https://docs.crawl4ai.com/core/docker-deployment/#using-the-api)
- [Metrics & Monitoring](https://docs.crawl4ai.com/core/docker-deployment/#metrics-monitoring)
- [Server Configuration](https://docs.crawl4ai.com/core/docker-deployment/#server-configuration)
- [Getting Help](https://docs.crawl4ai.com/core/docker-deployment/#getting-help)
- [Summary](https://docs.crawl4ai.com/core/docker-deployment/#summary)

# Crawl4AI Docker Guide 🐳

## Table of Contents

- [Prerequisites](https://docs.crawl4ai.com/core/docker-deployment/#prerequisites)
- [Installation](https://docs.crawl4ai.com/core/docker-deployment/#installation)
- [Option 1: Using Pre-built Docker Hub Images (Recommended)](https://docs.crawl4ai.com/core/docker-deployment/#option-1-using-pre-built-docker-hub-images-recommended)
- [Option 2: Using Docker Compose](https://docs.crawl4ai.com/core/docker-deployment/#option-2-using-docker-compose)
- [Option 3: Manual Local Build & Run](https://docs.crawl4ai.com/core/docker-deployment/#option-3-manual-local-build--run)
- [Dockerfile Parameters](https://docs.crawl4ai.com/core/docker-deployment/#dockerfile-parameters)
- [Using the API](https://docs.crawl4ai.com/core/docker-deployment/#using-the-api)
- [Playground Interface](https://docs.crawl4ai.com/core/docker-deployment/#playground-interface)
- [Python SDK](https://docs.crawl4ai.com/core/docker-deployment/#python-sdk)
- [Understanding Request Schema](https://docs.crawl4ai.com/core/docker-deployment/#understanding-request-schema)
- [REST API Examples](https://docs.crawl4ai.com/core/docker-deployment/#rest-api-examples)
- [Additional API Endpoints](https://docs.crawl4ai.com/core/docker-deployment/#additional-api-endpoints)
- [HTML Extraction Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#html-extraction-endpoint)
- [Screenshot Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#screenshot-endpoint)
- [PDF Export Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#pdf-export-endpoint)
- [JavaScript Execution Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#javascript-execution-endpoint)
- [Library Context Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#library-context-endpoint)
- [MCP (Model Context Protocol) Support](https://docs.crawl4ai.com/core/docker-deployment/#mcp-model-context-protocol-support)
- [What is MCP?](https://docs.crawl4ai.com/core/docker-deployment/#what-is-mcp)
- [Connecting via MCP](https://docs.crawl4ai.com/core/docker-deployment/#connecting-via-mcp)
- [Using with Claude Code](https://docs.crawl4ai.com/core/docker-deployment/#using-with-claude-code)
- [Available MCP Tools](https://docs.crawl4ai.com/core/docker-deployment/#available-mcp-tools)
- [Testing MCP Connections](https://docs.crawl4ai.com/core/docker-deployment/#testing-mcp-connections)
- [MCP Schemas](https://docs.crawl4ai.com/core/docker-deployment/#mcp-schemas)
- [Metrics & Monitoring](https://docs.crawl4ai.com/core/docker-deployment/#metrics--monitoring)
- [Deployment Scenarios](https://docs.crawl4ai.com/core/docker-deployment/#deployment-scenarios)
- [Complete Examples](https://docs.crawl4ai.com/core/docker-deployment/#complete-examples)
- [Server Configuration](https://docs.crawl4ai.com/core/docker-deployment/#server-configuration)
- [Understanding config.yml](https://docs.crawl4ai.com/core/docker-deployment/#understanding-configyml)
- [JWT Authentication](https://docs.crawl4ai.com/core/docker-deployment/#jwt-authentication)
- [Configuration Tips and Best Practices](https://docs.crawl4ai.com/core/docker-deployment/#configuration-tips-and-best-practices)
- [Customizing Your Configuration](https://docs.crawl4ai.com/core/docker-deployment/#customizing-your-configuration)
- [Configuration Recommendations](https://docs.crawl4ai.com/core/docker-deployment/#configuration-recommendations)
- [Getting Help](https://docs.crawl4ai.com/core/docker-deployment/#getting-help)
- [Summary](https://docs.crawl4ai.com/core/docker-deployment/#summary)

## Prerequisites

Before we dive in, make sure you have: - Docker installed and running (version 20.10.0 or higher), including `docker compose` (usually bundled with Docker Desktop). - `git` for cloning the repository. - At least 4GB of RAM available for the container (more recommended for heavy use). - Python 3.10+ (if using the Python SDK). - Node.js 16+ (if using the Node.js examples).

> 💡 **Pro tip** : Run `docker info` to check your Docker installation and available resources.

## Installation

We offer several ways to get the Crawl4AI server running. The quickest way is to use our pre-built Docker Hub images.

### Option 1: Using Pre-built Docker Hub Images (Recommended)

Pull and run images directly from Docker Hub without building locally.

#### 1. Pull the Image

Our latest release is `0.7.3`. Images are built with multi-arch manifests, so Docker automatically pulls the correct version for your system.

> 💡 **Note** : The `latest` tag points to the stable `0.7.3` version.

```
# Pull the latest version
docker pull unclecode/crawl4ai:0.7.3

# Or pull using the latest tag
docker pull unclecode/crawl4ai:latest
Copy
```

#### 2. Setup Environment (API Keys)

If you plan to use LLMs, create a `.llm.env` file in your working directory:

```
# Create a .llm.env file with your API keys
cat > .llm.env << EOL
# OpenAI
OPENAI_API_KEY=sk-your-key

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-key

# Other providers as needed
# DEEPSEEK_API_KEY=your-deepseek-key
# GROQ_API_KEY=your-groq-key
# TOGETHER_API_KEY=your-together-key
# MISTRAL_API_KEY=your-mistral-key
# GEMINI_API_TOKEN=your-gemini-token

# Optional: Global LLM settings
# LLM_PROVIDER=openai/gpt-4o-mini
# LLM_TEMPERATURE=0.7
# LLM_BASE_URL=https://api.custom.com/v1

# Optional: Provider-specific overrides
# OPENAI_TEMPERATURE=0.5
# OPENAI_BASE_URL=https://custom-openai.com/v1
# ANTHROPIC_TEMPERATURE=0.3
EOL
Copy
```

> 🔑 **Note** : Keep your API keys secure! Never commit `.llm.env` to version control.

#### 3. Run the Container

- **Basic run:**

```
docker run -d \
  -p 11235:11235 \
  --name crawl4ai \
  --shm-size=1g \
  unclecode/crawl4ai:latest
Copy
```

- **With LLM support:**

```
# Make sure .llm.env is in the current directory
docker run -d \
  -p 11235:11235 \
  --name crawl4ai \
  --env-file .llm.env \
  --shm-size=1g \
  unclecode/crawl4ai:latest
Copy
```

> The server will be available at `http://localhost:11235`. Visit `/playground` to access the interactive testing interface.

#### 4. Stopping the Container

```
docker stop crawl4ai && docker rm crawl4ai
Copy
```

#### Docker Hub Versioning Explained

- **Image Name:** `unclecode/crawl4ai`
- **Tag Format:** `LIBRARY_VERSION[-SUFFIX]` (e.g., `0.7.3`)
  - `LIBRARY_VERSION`: The semantic version of the core `crawl4ai` Python library
  - `SUFFIX`: Optional tag for release candidates (``) and revisions (`r1`)
- **`latest`Tag:** Points to the most recent stable version
- **Multi-Architecture Support:** All images support both `linux/amd64` and `linux/arm64` architectures through a single tag

### Option 2: Using Docker Compose

Docker Compose simplifies building and running the service, especially for local development and testing.

#### 1. Clone Repository

```
git clone https://github.com/unclecode/crawl4ai.git
cd crawl4ai
Copy
```

#### 2. Environment Setup (API Keys)

If you plan to use LLMs, copy the example environment file and add your API keys. This file should be in the **project root directory**.

```
# Make sure you are in the 'crawl4ai' root directory
cp deploy/docker/.llm.env.example .llm.env

# Now edit .llm.env and add your API keys
Copy
```

**Flexible LLM Provider Configuration:**
The Docker setup now supports flexible LLM provider configuration through a hierarchical system:

1. **API Request Parameters** (Highest Priority): Specify per request

```
{
  "url": "https://example.com",
  "f": "llm",
  "provider": "groq/mixtral-8x7b",
  "temperature": 0.7,
  "base_url": "https://api.custom.com/v1"
}
Copy
```

2. **Provider-Specific Environment Variables** : Override for specific providers

```
# In your .llm.env file:
OPENAI_TEMPERATURE=0.5
OPENAI_BASE_URL=https://custom-openai.com/v1
ANTHROPIC_TEMPERATURE=0.3
Copy
```

3. **Global Environment Variables** : Set defaults for all providers

```
# In your .llm.env file:
LLM_PROVIDER=anthropic/claude-3-opus
LLM_TEMPERATURE=0.7
LLM_BASE_URL=https://api.proxy.com/v1
Copy
```

4. **Config File Default** : Falls back to `config.yml` (default: `openai/gpt-4o-mini`)

The system automatically selects the appropriate API key based on the provider. LiteLLM handles finding the correct environment variable for each provider (e.g., OPENAI_API_KEY for OpenAI, GEMINI_API_TOKEN for Google Gemini, etc.).
**Supported LLM Parameters:** - `provider`: LLM provider and model (e.g., "openai/gpt-4", "anthropic/claude-3-opus") - `temperature`: Controls randomness (0.0-2.0, lower = more focused, higher = more creative) - `base_url`: Custom API endpoint for proxy servers or alternative endpoints

#### 3. Build and Run with Compose

The `docker-compose.yml` file in the project root provides a simplified approach that automatically handles architecture detection using buildx.

- **Run Pre-built Image from Docker Hub:**

```
# Pulls and runs the release candidate from Docker Hub
# Automatically selects the correct architecture
IMAGE=unclecode/crawl4ai:latest docker compose up -d
Copy
```

- **Build and Run Locally:**

```
# Builds the image locally using Dockerfile and runs it
# Automatically uses the correct architecture for your machine
docker compose up --build -d
Copy
```

- **Customize the Build:**

```
# Build with all features (includes torch and transformers)
INSTALL_TYPE=all docker compose up --build -d

# Build with GPU support (for AMD64 platforms)
ENABLE_GPU=true docker compose up --build -d
Copy
```

> The server will be available at `http://localhost:11235`.

#### 4. Stopping the Service

```
# Stop the service
docker compose down
Copy
```

### Option 3: Manual Local Build & Run

If you prefer not to use Docker Compose for direct control over the build and run process.

#### 1. Clone Repository & Setup Environment

Follow steps 1 and 2 from the Docker Compose section above (clone repo, `cd crawl4ai`, create `.llm.env` in the root).

#### 2. Build the Image (Multi-Arch)

Use `docker buildx` to build the image. Crawl4AI now uses buildx to handle multi-architecture builds automatically.

```
# Make sure you are in the 'crawl4ai' root directory
# Build for the current architecture and load it into Docker
docker buildx build -t crawl4ai-local:latest --load .

# Or build for multiple architectures (useful for publishing)
docker buildx build --platform linux/amd64,linux/arm64 -t crawl4ai-local:latest --load .

# Build with additional options
docker buildx build \
  --build-arg INSTALL_TYPE=all \
  --build-arg ENABLE_GPU=false \
  -t crawl4ai-local:latest --load .
Copy
```

#### 3. Run the Container

- **Basic run (no LLM support):**

```
docker run -d \
  -p 11235:11235 \
  --name crawl4ai-standalone \
  --shm-size=1g \
  crawl4ai-local:latest
Copy
```

- **With LLM support:**

```
# Make sure .llm.env is in the current directory (project root)
docker run -d \
  -p 11235:11235 \
  --name crawl4ai-standalone \
  --env-file .llm.env \
  --shm-size=1g \
  crawl4ai-local:latest
Copy
```

> The server will be available at `http://localhost:11235`.

#### 4. Stopping the Manual Container

```
docker stop crawl4ai-standalone && docker rm crawl4ai-standalone
Copy
```

---

## MCP (Model Context Protocol) Support

Crawl4AI server includes support for the Model Context Protocol (MCP), allowing you to connect the server's capabilities directly to MCP-compatible clients like Claude Code.

### What is MCP?

MCP is an open protocol that standardizes how applications provide context to LLMs. It allows AI models to access external tools, data sources, and services through a standardized interface.

### Connecting via MCP

The Crawl4AI server exposes two MCP endpoints:

- **Server-Sent Events (SSE)** : `http://localhost:11235/mcp/sse`
- **WebSocket** : `ws://localhost:11235/mcp/ws`

### Using with Claude Code

You can add Crawl4AI as an MCP tool provider in Claude Code with a simple command:

```
# Add the Crawl4AI server as an MCP provider
claude mcp add --transport sse c4ai-sse http://localhost:11235/mcp/sse

# List all MCP providers to verify it was added
claude mcp list
Copy
```

Once connected, Claude Code can directly use Crawl4AI's capabilities like screenshot capture, PDF generation, and HTML processing without having to make separate API calls.

### Available MCP Tools

When connected via MCP, the following tools are available:

- `md` - Generate markdown from web content
- `html` - Extract preprocessed HTML
- `screenshot` - Capture webpage screenshots
- `pdf` - Generate PDF documents
- `execute_js` - Run JavaScript on web pages
- `crawl` - Perform multi-URL crawling
- `ask` - Query the Crawl4AI library context

### Testing MCP Connections

You can test the MCP WebSocket connection using the test file included in the repository:

```
# From the repository root
python tests/mcp/test_mcp_socket.py
Copy
```

### MCP Schemas

Access the MCP tool schemas at `http://localhost:11235/mcp/schema` for detailed information on each tool's parameters and capabilities.

---

## Additional API Endpoints

In addition to the core `/crawl` and `/crawl/stream` endpoints, the server provides several specialized endpoints:

### HTML Extraction Endpoint

```
POST /html
Copy
```

Crawls the URL and returns preprocessed HTML optimized for schema extraction.

```
{
  "url": "https://example.com"
}
Copy
```

### Screenshot Endpoint

```
POST /screenshot
Copy
```

Captures a full-page PNG screenshot of the specified URL.

```
{
  "url": "https://example.com",
  "screenshot_wait_for": 2,
  "output_path": "/path/to/save/screenshot.png"
}
Copy
```

- `screenshot_wait_for`: Optional delay in seconds before capture (default: 2)
- `output_path`: Optional path to save the screenshot (recommended)

### PDF Export Endpoint

```
POST /pdf
Copy
```

Generates a PDF document of the specified URL.

```
{
  "url": "https://example.com",
  "output_path": "/path/to/save/document.pdf"
}
Copy
```

- `output_path`: Optional path to save the PDF (recommended)

### JavaScript Execution Endpoint

```
POST /execute_js
Copy
```

Executes JavaScript snippets on the specified URL and returns the full crawl result.

```
{
  "url": "https://example.com",
  "scripts": [
    "return document.title",
    "return Array.from(document.querySelectorAll('a')).map(a => a.href)"
  ]
}
Copy
```

- `scripts`: List of JavaScript snippets to execute sequentially

---

## User-Provided Hooks API

The Docker API supports user-provided hook functions, allowing you to customize the crawling behavior by injecting your own Python code at specific points in the crawling pipeline. This powerful feature enables authentication, performance optimization, and custom content extraction without modifying the server code.

> ⚠️ **IMPORTANT SECURITY WARNING** : - **Never use hooks with untrusted code or on untrusted websites** - **Be extremely careful when crawling sites that might be phishing or malicious** - **Hook code has access to page context and can interact with the website** - **Always validate and sanitize any data extracted through hooks** - **Never expose credentials or sensitive data in hook code** - **Consider running the Docker container in an isolated network when testing**

### Hook Information Endpoint

```
GET /hooks/info
Copy
```

Returns information about available hook points and their signatures:

```
curl http://localhost:11235/hooks/info
Copy
```

### Available Hook Points

The API supports 8 hook points that match the local SDK:
Hook Point | Parameters | Description | Best Use Cases
---|---|---|---
`on_browser_created` | `browser` | After browser instance creation | Light setup tasks
`on_page_context_created` | `page, context` | After page/context creation | **Authentication, cookies, route blocking**
`before_goto` | `page, context, url` | Before navigating to URL | Custom headers, logging
`after_goto` | `page, context, url, response` | After navigation completes | Verification, waiting for elements
`on_user_agent_updated` | `page, context, user_agent` | When user agent changes | UA-specific logic
`on_execution_started` | `page, context` | When JS execution begins | JS-related setup
`before_retrieve_html` | `page, context` | Before getting final HTML | **Scrolling, lazy loading**
`before_return_html` | `page, context, html` | Before returning HTML | Final modifications, metrics

### Using Hooks in Requests

Add hooks to any crawl request by including the `hooks` parameter:

```
{
  "urls": ["https://httpbin.org/html"],
  "hooks": {
    "code": {
      "hook_point_name": "async def hook(...): ...",
      "another_hook": "async def hook(...): ..."
    },
    "timeout": 30  // Optional, default 30 seconds (max 120)
  }
}
Copy
```

### Hook Examples with Real URLs

#### 1. Authentication with Cookies (GitHub)

```
import requests

# Example: Setting GitHub session cookie (use your actual session)
hooks_code = {
    "on_page_context_created": """
async def hook(page, context, **kwargs):
    # Add authentication cookies for GitHub
    # WARNING: Never hardcode real credentials!
    await context.add_cookies([
        {
            'name': 'user_session',
            'value': 'your_github_session_token',  # Replace with actual token
            'domain': '.github.com',
            'path': '/',
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Lax'
        }
    ])
    return page
"""
}

response = requests.post("http://localhost:11235/crawl", json={
    "urls": ["https://github.com/settings/profile"],  # Protected page
    "hooks": {"code": hooks_code, "timeout": 30}
})
Copy
```

#### 2. Basic Authentication (httpbin.org for testing)

```
# Safe testing with httpbin.org (a service designed for HTTP testing)
hooks_code = {
    "before_goto": """
async def hook(page, context, url, **kwargs):
    import base64
    # httpbin.org/basic-auth expects username="user" and password="passwd"
    credentials = base64.b64encode(b"user:passwd").decode('ascii')

    await page.set_extra_http_headers({
        'Authorization': f'Basic {credentials}'
    })
    return page
"""
}

response = requests.post("http://localhost:11235/crawl", json={
    "urls": ["https://httpbin.org/basic-auth/user/passwd"],
    "hooks": {"code": hooks_code, "timeout": 15}
})
Copy
```

#### 3. Performance Optimization (News Sites)

```
# Example: Optimizing crawling of news sites like CNN or BBC
hooks_code = {
    "on_page_context_created": """
async def hook(page, context, **kwargs):
    # Block images, fonts, and media to speed up crawling
    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda route: route.abort())
    await context.route("**/*.{woff,woff2,ttf,otf,eot}", lambda route: route.abort())
    await context.route("**/*.{mp4,webm,ogg,mp3,wav,flac}", lambda route: route.abort())

    # Block common tracking and ad domains
    await context.route("**/googletagmanager.com/*", lambda route: route.abort())
    await context.route("**/google-analytics.com/*", lambda route: route.abort())
    await context.route("**/doubleclick.net/*", lambda route: route.abort())
    await context.route("**/facebook.com/tr/*", lambda route: route.abort())
    await context.route("**/amazon-adsystem.com/*", lambda route: route.abort())

    # Disable CSS animations for faster rendering
    await page.add_style_tag(content='''
        *, *::before, *::after {
            animation-duration: 0s !important;
            transition-duration: 0s !important;
        }
    ''')

    return page
"""
}

response = requests.post("http://localhost:11235/crawl", json={
    "urls": ["https://www.bbc.com/news"],  # Heavy news site
    "hooks": {"code": hooks_code, "timeout": 30}
})
Copy
```

#### 4. Handling Infinite Scroll (Twitter/X)

```
# Example: Scrolling on Twitter/X (requires authentication)
hooks_code = {
    "before_retrieve_html": """
async def hook(page, context, **kwargs):
    # Scroll to load more tweets
    previous_height = 0
    for i in range(5):  # Limit scrolls to avoid infinite loop
        current_height = await page.evaluate("document.body.scrollHeight")
        if current_height == previous_height:
            break  # No more content to load

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)  # Wait for content to load
        previous_height = current_height

    return page
"""
}

# Note: Twitter requires authentication for most content
response = requests.post("http://localhost:11235/crawl", json={
    "urls": ["https://twitter.com/nasa"],  # Public profile
    "hooks": {"code": hooks_code, "timeout": 30}
})
Copy
```

#### 5. E-commerce Login (Example Pattern)

```
# SECURITY WARNING: This is a pattern example.
# Never use real credentials in code!
# Always use environment variables or secure vaults.

hooks_code = {
    "on_page_context_created": """
async def hook(page, context, **kwargs):
    # Example pattern for e-commerce sites
    # DO NOT use real credentials here!

    # Navigate to login page first
    await page.goto("https://example-shop.com/login")

    # Wait for login form to load
    await page.wait_for_selector("#email", timeout=5000)

    # Fill login form (use environment variables in production!)
    await page.fill("#email", "test@example.com")  # Never use real email
    await page.fill("#password", "test_password")   # Never use real password

    # Handle "Remember Me" checkbox if present
    try:
        await page.uncheck("#remember_me")  # Don't remember on shared systems
    except:
        pass

    # Submit form
    await page.click("button[type='submit']")

    # Wait for redirect after login
    await page.wait_for_url("**/account/**", timeout=10000)

    return page
"""
}
Copy
```

#### 6. Extracting Structured Data (Wikipedia)

```
# Safe example using Wikipedia
hooks_code = {
    "after_goto": """
async def hook(page, context, url, response, **kwargs):
    # Wait for Wikipedia content to load
    await page.wait_for_selector("#content", timeout=5000)
    return page
""",

    "before_retrieve_html": """
async def hook(page, context, **kwargs):
    # Extract structured data from Wikipedia infobox
    metadata = await page.evaluate('''() => {
        const infobox = document.querySelector('.infobox');
        if (!infobox) return null;

        const data = {};
        const rows = infobox.querySelectorAll('tr');

        rows.forEach(row => {
            const header = row.querySelector('th');
            const value = row.querySelector('td');
            if (header && value) {
                data[header.innerText.trim()] = value.innerText.trim();
            }
        });

        return data;
    }''')

    if metadata:
        print("Extracted metadata:", metadata)

    return page
"""
}

response = requests.post("http://localhost:11235/crawl", json={
    "urls": ["https://en.wikipedia.org/wiki/Python_(programming_language)"],
    "hooks": {"code": hooks_code, "timeout": 20}
})
Copy
```

### Security Best Practices

> 🔒 **Critical Security Guidelines** :

1. **Never Trust User Input** : If accepting hook code from users, always validate and sandbox it
2. **Avoid Phishing Sites** : Never use hooks on suspicious or unverified websites
3. **Protect Credentials** :
4. Never hardcode passwords, tokens, or API keys in hook code
5. Use environment variables or secure secret management
6. Rotate credentials regularly
7. **Network Isolation** : Run the Docker container in an isolated network when testing
8. **Audit Hook Code** : Always review hook code before execution
9. **Limit Permissions** : Use the least privileged access needed
10. **Monitor Execution** : Check hook execution logs for suspicious behavior
11. **Timeout Protection** : Always set reasonable timeouts (default 30s)

### Hook Response Information

When hooks are used, the response includes detailed execution information:

```
{
  "success": true,
  "results": [...],
  "hooks": {
    "status": {
      "status": "success",  // or "partial" or "failed"
      "attached_hooks": ["on_page_context_created", "before_retrieve_html"],
      "validation_errors": [],
      "successfully_attached": 2,
      "failed_validation": 0
    },
    "execution_log": [
      {
        "hook_point": "on_page_context_created",
        "status": "success",
        "execution_time": 0.523,
        "timestamp": 1234567890.123
      }
    ],
    "errors": [],  // Any runtime errors
    "summary": {
      "total_executions": 2,
      "successful": 2,
      "failed": 0,
      "timed_out": 0,
      "success_rate": 100.0
    }
  }
}
Copy
```

### Error Handling

The hooks system is designed to be resilient:

1. **Validation Errors** : Caught before execution (syntax errors, wrong parameters)
2. **Runtime Errors** : Handled gracefully - crawl continues with original page object
3. **Timeout Protection** : Hooks automatically terminated after timeout (configurable 1-120s)

### Complete Example: Safe Multi-Hook Crawling

```
import requests
import json
import os

# Safe example using httpbin.org for testing
hooks_code = {
    "on_page_context_created": """
async def hook(page, context, **kwargs):
    # Set viewport and test cookies
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await context.add_cookies([
        {"name": "test_cookie", "value": "test_value", "domain": ".httpbin.org", "path": "/"}
    ])

    # Block unnecessary resources for httpbin
    await context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
    return page
""",

    "before_goto": """
async def hook(page, context, url, **kwargs):
    # Add custom headers for testing
    await page.set_extra_http_headers({
        "X-Test-Header": "crawl4ai-test",
        "Accept-Language": "en-US,en;q=0.9"
    })
    print(f"[HOOK] Navigating to: {url}")
    return page
""",

    "before_retrieve_html": """
async def hook(page, context, **kwargs):
    # Simple scroll for any lazy-loaded content
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    return page
"""
}

# Make the request to safe testing endpoints
response = requests.post("http://localhost:11235/crawl", json={
    "urls": [
        "https://httpbin.org/html",
        "https://httpbin.org/json"
    ],
    "hooks": {
        "code": hooks_code,
        "timeout": 30
    },
    "crawler_config": {
        "cache_mode": "bypass"
    }
})

# Check results
if response.status_code == 200:
    data = response.json()

    # Check hook execution
    if data['hooks']['status']['status'] == 'success':
        print(f"✅ All {len(data['hooks']['status']['attached_hooks'])} hooks executed successfully")
        print(f"Execution stats: {data['hooks']['summary']}")

    # Process crawl results
    for result in data['results']:
        print(f"Crawled: {result['url']} - Success: {result['success']}")
else:
    print(f"Error: {response.status_code}")
Copy
```

> 💡 **Remember** : Always test your hooks on safe, known websites first before using them on production sites. Never crawl sites that you don't have permission to access or that might be malicious.

---

## Dockerfile Parameters

You can customize the image build process using build arguments (`--build-arg`). These are typically used via `docker buildx build` or within the `docker-compose.yml` file.

```
# Example: Build with 'all' features using buildx
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg INSTALL_TYPE=all \
  -t yourname/crawl4ai-all:latest \
  --load \
  . # Build from root context
Copy
```

### Build Arguments Explained

| Argument      | Description                              | Default            | Options                                  |
| ------------- | ---------------------------------------- | ------------------ | ---------------------------------------- |
| INSTALL_TYPE  | Feature set                              | `default`          | `default`, `all`, `torch`, `transformer` |
| ENABLE_GPU    | GPU support (CUDA for AMD64)             | `false`            | `true`, `false`                          |
| APP_HOME      | Install path inside container (advanced) | `/app`             | any valid path                           |
| USE_LOCAL     | Install library from local source        | `true`             | `true`, `false`                          |
| GITHUB_REPO   | Git repo to clone if USE_LOCAL=false     | _(see Dockerfile)_ | any git URL                              |
| GITHUB_BRANCH | Git branch to clone if USE_LOCAL=false   | `main`             | any branch name                          |

_(Note: PYTHON_VERSION is fixed by the`FROM` instruction in the Dockerfile)_

### Build Best Practices

1. **Choose the Right Install Type**
   - `default`: Basic installation, smallest image size. Suitable for most standard web scraping and markdown generation.
   - `all`: Full features including `torch` and `transformers` for advanced extraction strategies (e.g., CosineStrategy, certain LLM filters). Significantly larger image. Ensure you need these extras.
2. **Platform Considerations**
   - Use `buildx` for building multi-architecture images, especially for pushing to registries.
   - Use `docker compose` profiles (`local-amd64`, `local-arm64`) for easy platform-specific local builds.
3. **Performance Optimization**
   - The image automatically includes platform-specific optimizations (OpenMP for AMD64, OpenBLAS for ARM64).

---

## Using the API

Communicate with the running Docker server via its REST API (defaulting to `http://localhost:11235`). You can use the Python SDK or make direct HTTP requests.

### Playground Interface

A built-in web playground is available at `http://localhost:11235/playground` for testing and generating API requests. The playground allows you to:

1. Configure `CrawlerRunConfig` and `BrowserConfig` using the main library's Python syntax
2. Test crawling operations directly from the interface
3. Generate corresponding JSON for REST API requests based on your configuration

This is the easiest way to translate Python configuration to JSON requests when building integrations.

### Python SDK

Install the SDK: `pip install crawl4ai`

```
import asyncio
from crawl4ai.docker_client import Crawl4aiDockerClient
from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode # Assuming you have crawl4ai installed

async def main():
    # Point to the correct server port
    async with Crawl4aiDockerClient(base_url="http://localhost:11235", verbose=True) as client:
        # If JWT is enabled on the server, authenticate first:
        # await client.authenticate("user@example.com") # See Server Configuration section

        # Example Non-streaming crawl
        print("--- Running Non-Streaming Crawl ---")
        results = await client.crawl(
            ["https://httpbin.org/html"],
            browser_config=BrowserConfig(headless=True), # Use library classes for config aid
            crawler_config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        )
        if results: # client.crawl returns None on failure
          print(f"Non-streaming results success: {results.success}")
          if results.success:
              for result in results: # Iterate through the CrawlResultContainer
                  print(f"URL: {result.url}, Success: {result.success}")
        else:
            print("Non-streaming crawl failed.")


        # Example Streaming crawl
        print("\n--- Running Streaming Crawl ---")
        stream_config = CrawlerRunConfig(stream=True, cache_mode=CacheMode.BYPASS)
        try:
            async for result in await client.crawl( # client.crawl returns an async generator for streaming
                ["https://httpbin.org/html", "https://httpbin.org/links/5/0"],
                browser_config=BrowserConfig(headless=True),
                crawler_config=stream_config
            ):
                print(f"Streamed result: URL: {result.url}, Success: {result.success}")
        except Exception as e:
            print(f"Streaming crawl failed: {e}")


        # Example Get schema
        print("\n--- Getting Schema ---")
        schema = await client.get_schema()
        print(f"Schema received: {bool(schema)}") # Print whether schema was received

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

_(SDK parameters like timeout, verify_ssl etc. remain the same)_

### Second Approach: Direct API Calls

Crucially, when sending configurations directly via JSON, they **must** follow the `{"type": "ClassName", "params": {...}}` structure for any non-primitive value (like config objects or strategies). Dictionaries must be wrapped as `{"type": "dict", "value": {...}}`.
_(Keep the detailed explanation of Configuration Structure, Basic Pattern, Simple vs Complex, Strategy Pattern, Complex Nested Example, Quick Grammar Overview, Important Rules, Pro Tip)_

#### More Examples _(Ensure Schema example uses type/value wrapper)_

**Advanced Crawler Configuration** _(Keep example, ensure cache_mode uses valid enum value like "bypass")_
**Extraction Strategy**

```
{
    "crawler_config": {
        "type": "CrawlerRunConfig",
        "params": {
            "extraction_strategy": {
                "type": "JsonCssExtractionStrategy",
                "params": {
                    "schema": {
                        "type": "dict",
                        "value": {
                           "baseSelector": "article.post",
                           "fields": [
                               {"name": "title", "selector": "h1", "type": "text"},
                               {"name": "content", "selector": ".content", "type": "html"}
                           ]
                         }
                    }
                }
            }
        }
    }
}
Copy
```

**LLM Extraction Strategy** _(Keep example, ensure schema uses type/value wrapper)_ _(Keep Deep Crawler Example)_

### LLM Configuration Examples

The Docker API supports dynamic LLM configuration through multiple levels:

#### Temperature Control

Temperature affects the randomness of LLM responses (0.0 = deterministic, 2.0 = very creative):

```
import requests

# Low temperature for factual extraction
response = requests.post(
    "http://localhost:11235/md",
    json={
        "url": "https://example.com",
        "f": "llm",
        "q": "Extract all dates and numbers from this page",
        "temperature": 0.2  # Very focused, deterministic
    }
)

# High temperature for creative tasks
response = requests.post(
    "http://localhost:11235/md",
    json={
        "url": "https://example.com",
        "f": "llm",
        "q": "Write a creative summary of this content",
        "temperature": 1.2  # More creative, varied responses
    }
)
Copy
```

#### Custom API Endpoints

Use custom base URLs for proxy servers or alternative API endpoints:

```
# Using a local LLM server
response = requests.post(
    "http://localhost:11235/md",
    json={
        "url": "https://example.com",
        "f": "llm",
        "q": "Extract key information",
        "provider": "ollama/llama2",
        "base_url": "http://localhost:11434/v1"
    }
)
Copy
```

#### Dynamic Provider Selection

Switch between providers based on task requirements:

```
async def smart_extraction(url: str, content_type: str):
    """Select provider and temperature based on content type"""

    configs = {
        "technical": {
            "provider": "openai/gpt-4",
            "temperature": 0.3,
            "query": "Extract technical specifications and code examples"
        },
        "creative": {
            "provider": "anthropic/claude-3-opus",
            "temperature": 0.9,
            "query": "Create an engaging narrative summary"
        },
        "quick": {
            "provider": "groq/mixtral-8x7b",
            "temperature": 0.5,
            "query": "Quick summary in bullet points"
        }
    }

    config = configs.get(content_type, configs["quick"])

    response = await httpx.post(
        "http://localhost:11235/md",
        json={
            "url": url,
            "f": "llm",
            "q": config["query"],
            "provider": config["provider"],
            "temperature": config["temperature"]
        }
    )

    return response.json()
Copy
```

### REST API Examples

Update URLs to use port `11235`.

#### Simple Crawl

```
import requests

# Configuration objects converted to the required JSON structure
browser_config_payload = {
    "type": "BrowserConfig",
    "params": {"headless": True}
}
crawler_config_payload = {
    "type": "CrawlerRunConfig",
    "params": {"stream": False, "cache_mode": "bypass"} # Use string value of enum
}

crawl_payload = {
    "urls": ["https://httpbin.org/html"],
    "browser_config": browser_config_payload,
    "crawler_config": crawler_config_payload
}
response = requests.post(
    "http://localhost:11235/crawl", # Updated port
    # headers={"Authorization": f"Bearer {token}"},  # If JWT is enabled
    json=crawl_payload
)
print(f"Status Code: {response.status_code}")
if response.ok:
    print(response.json())
else:
    print(f"Error: {response.text}")
Copy
```

#### Streaming Results

```
import json
import httpx # Use httpx for async streaming example

async def test_stream_crawl(token: str = None): # Made token optional
    """Test the /crawl/stream endpoint with multiple URLs."""
    url = "http://localhost:11235/crawl/stream" # Updated port
    payload = {
        "urls": [
            "https://httpbin.org/html",
            "https://httpbin.org/links/5/0",
        ],
        "browser_config": {
            "type": "BrowserConfig",
            "params": {"headless": True, "viewport": {"type": "dict", "value": {"width": 1200, "height": 800}}} # Viewport needs type:dict
        },
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {"stream": True, "cache_mode": "bypass"}
        }
    }

    headers = {}
    # if token:
    #    headers = {"Authorization": f"Bearer {token}"} # If JWT is enabled

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, headers=headers, timeout=120.0) as response:
                print(f"Status: {response.status_code} (Expected: 200)")
                response.raise_for_status() # Raise exception for bad status codes

                # Read streaming response line-by-line (NDJSON)
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            # Check for completion marker
                            if data.get("status") == "completed":
                                print("Stream completed.")
                                break
                            print(f"Streamed Result: {json.dumps(data, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON line: {line}")

    except httpx.HTTPStatusError as e:
         print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Error in streaming crawl test: {str(e)}")

# To run this example:
# import asyncio
# asyncio.run(test_stream_crawl())
Copy
```

---

## Metrics & Monitoring

Keep an eye on your crawler with these endpoints:

- `/health` - Quick health check
- `/metrics` - Detailed Prometheus metrics
- `/schema` - Full API schema

Example health check:

```
curl http://localhost:11235/health
Copy
```

---

_(Deployment Scenarios and Complete Examples sections remain the same, maybe update links if examples moved)_

---

## Server Configuration

The server's behavior can be customized through the `config.yml` file.

### Understanding config.yml

The configuration file is loaded from `/app/config.yml` inside the container. By default, the file from `deploy/docker/config.yml` in the repository is copied there during the build.
Here's a detailed breakdown of the configuration options (using defaults from `deploy/docker/config.yml`):

```
# Application Configuration
app:
  title: "Crawl4AI API"
  version: "1.0.0" # Consider setting this to match library version, e.g., "0.5.1"
  host: "0.0.0.0"
  port: 8020 # NOTE: This port is used ONLY when running server.py directly. Gunicorn overrides this (see supervisord.conf).
  reload: False # Default set to False - suitable for production
  timeout_keep_alive: 300

# Default LLM Configuration
llm:
  provider: "openai/gpt-4o-mini"  # Can be overridden by LLM_PROVIDER env var
  # api_key: sk-...  # If you pass the API key directly (not recommended)
  # temperature and base_url are controlled via environment variables or request parameters

# Redis Configuration (Used by internal Redis server managed by supervisord)
redis:
  host: "localhost"
  port: 6379
  db: 0
  password: ""
  # ... other redis options ...

# Rate Limiting Configuration
rate_limiting:
  enabled: True
  default_limit: "1000/minute"
  trusted_proxies: []
  storage_uri: "memory://"  # Use "redis://localhost:6379" if you need persistent/shared limits

# Security Configuration
security:
  enabled: false # Master toggle for security features
  jwt_enabled: false # Enable JWT authentication (requires security.enabled=true)
  https_redirect: false # Force HTTPS (requires security.enabled=true)
  trusted_hosts: ["*"] # Allowed hosts (use specific domains in production)
  headers: # Security headers (applied if security.enabled=true)
    x_content_type_options: "nosniff"
    x_frame_options: "DENY"
    content_security_policy: "default-src 'self'"
    strict_transport_security: "max-age=63072000; includeSubDomains"

# Crawler Configuration
crawler:
  memory_threshold_percent: 95.0
  rate_limiter:
    base_delay: [1.0, 2.0] # Min/max delay between requests in seconds for dispatcher
  timeouts:
    stream_init: 30.0  # Timeout for stream initialization
    batch_process: 300.0 # Timeout for non-streaming /crawl processing

# Logging Configuration
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Observability Configuration
observability:
  prometheus:
    enabled: True
    endpoint: "/metrics"
  health_check:
    endpoint: "/health"
Copy
```

_(JWT Authentication section remains the same, just note the default port is now 11235 for requests)_
_(Configuration Tips and Best Practices remain the same)_

### Customizing Your Configuration

You can override the default `config.yml`.

#### Method 1: Modify Before Build

1. Edit the `deploy/docker/config.yml` file in your local repository clone.
2. Build the image using `docker buildx` or `docker compose --profile local-... up --build`. The modified file will be copied into the image.

#### Method 2: Runtime Mount (Recommended for Custom Deploys)

1. Create your custom configuration file, e.g., `my-custom-config.yml` locally. Ensure it contains all necessary sections.
2. Mount it when running the container:
   - **Using`docker run` :**

```
# Assumes my-custom-config.yml is in the current directory
docker run -d -p 11235:11235 \
  --name crawl4ai-custom-config \
  --env-file .llm.env \
  --shm-size=1g \
  -v $(pwd)/my-custom-config.yml:/app/config.yml \
  unclecode/crawl4ai:latest # Or your specific tag
Copy
```

     * **Using`docker-compose.yml` :** Add a `volumes` section to the service definition:

```
services:
  crawl4ai-hub-amd64: # Or your chosen service
    image: unclecode/crawl4ai:latest
    profiles: ["hub-amd64"]
    <<: *base-config
    volumes:
      # Mount local custom config over the default one in the container
      - ./my-custom-config.yml:/app/config.yml
      # Keep the shared memory volume from base-config
      - /dev/shm:/dev/shm
Copy
```

_(Note: Ensure`my-custom-config.yml` is in the same directory as `docker-compose.yml`)_

> 💡 When mounting, your custom file _completely replaces_ the default one. Ensure it's a valid and complete configuration.

### Configuration Recommendations

1. **Security First** 🔒
2. Always enable security in production
3. Use specific trusted_hosts instead of wildcards
4. Set up proper rate limiting to protect your server
5. Consider your environment before enabling HTTPS redirect
6. **Resource Management** 💻
7. Adjust memory_threshold_percent based on available RAM
8. Set timeouts according to your content size and network conditions
9. Use Redis for rate limiting in multi-container setups
10. **Monitoring** 📊
11. Enable Prometheus if you need metrics
12. Set DEBUG logging in development, INFO in production
13. Regular health check monitoring is crucial
14. **Performance Tuning** ⚡
15. Start with conservative rate limiter delays
16. Increase batch_process timeout for large content
17. Adjust stream_init timeout based on initial response times

## Getting Help

We're here to help you succeed with Crawl4AI! Here's how to get support:

- 📖 Check our [full documentation](https://docs.crawl4ai.com)
- 🐛 Found a bug? [Open an issue](https://github.com/unclecode/crawl4ai/issues)
- 💬 Join our [Discord community](https://discord.gg/crawl4ai)
- ⭐ Star us on GitHub to show support!

## Summary

In this guide, we've covered everything you need to get started with Crawl4AI's Docker deployment: - Building and running the Docker container - Configuring the environment

- Using the interactive playground for testing - Making API requests with proper typing - Using the Python SDK - Leveraging specialized endpoints for screenshots, PDFs, and JavaScript execution - Connecting via the Model Context Protocol (MCP) - Monitoring your deployment
  The new playground interface at `http://localhost:11235/playground` makes it much easier to test configurations and generate the corresponding JSON for API requests.
  For AI application developers, the MCP integration allows tools like Claude Code to directly access Crawl4AI's capabilities without complex API handling.
  Remember, the examples in the `examples` folder are your friends - they show real-world usage patterns that you can adapt for your needs.
  Keep exploring, and don't hesitate to reach out if you need help! We're building something amazing together. 🚀
  Happy crawling! 🕷️
  Page Copy
  Page Copy
  - [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/docker-deployment/)
  - [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/docker-deployment/)
  - [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/docker-deployment/)

ESC to close

#### On this page

- [Table of Contents](https://docs.crawl4ai.com/core/docker-deployment/#table-of-contents)
- [Prerequisites](https://docs.crawl4ai.com/core/docker-deployment/#prerequisites)
- [Installation](https://docs.crawl4ai.com/core/docker-deployment/#installation)
- [Option 1: Using Pre-built Docker Hub Images (Recommended)](https://docs.crawl4ai.com/core/docker-deployment/#option-1-using-pre-built-docker-hub-images-recommended)
- [1. Pull the Image](https://docs.crawl4ai.com/core/docker-deployment/#1-pull-the-image)
- [2. Setup Environment (API Keys)](https://docs.crawl4ai.com/core/docker-deployment/#2-setup-environment-api-keys)
- [3. Run the Container](https://docs.crawl4ai.com/core/docker-deployment/#3-run-the-container)
- [4. Stopping the Container](https://docs.crawl4ai.com/core/docker-deployment/#4-stopping-the-container)
- [Docker Hub Versioning Explained](https://docs.crawl4ai.com/core/docker-deployment/#docker-hub-versioning-explained)
- [Option 2: Using Docker Compose](https://docs.crawl4ai.com/core/docker-deployment/#option-2-using-docker-compose)
- [1. Clone Repository](https://docs.crawl4ai.com/core/docker-deployment/#1-clone-repository)
- [2. Environment Setup (API Keys)](https://docs.crawl4ai.com/core/docker-deployment/#2-environment-setup-api-keys)
- [3. Build and Run with Compose](https://docs.crawl4ai.com/core/docker-deployment/#3-build-and-run-with-compose)
- [4. Stopping the Service](https://docs.crawl4ai.com/core/docker-deployment/#4-stopping-the-service)
- [Option 3: Manual Local Build & Run](https://docs.crawl4ai.com/core/docker-deployment/#option-3-manual-local-build-run)
- [1. Clone Repository & Setup Environment](https://docs.crawl4ai.com/core/docker-deployment/#1-clone-repository-setup-environment)
- [2. Build the Image (Multi-Arch)](https://docs.crawl4ai.com/core/docker-deployment/#2-build-the-image-multi-arch)
- [3. Run the Container](https://docs.crawl4ai.com/core/docker-deployment/#3-run-the-container_1)
- [4. Stopping the Manual Container](https://docs.crawl4ai.com/core/docker-deployment/#4-stopping-the-manual-container)
- [MCP (Model Context Protocol) Support](https://docs.crawl4ai.com/core/docker-deployment/#mcp-model-context-protocol-support)
- [What is MCP?](https://docs.crawl4ai.com/core/docker-deployment/#what-is-mcp)
- [Connecting via MCP](https://docs.crawl4ai.com/core/docker-deployment/#connecting-via-mcp)
- [Using with Claude Code](https://docs.crawl4ai.com/core/docker-deployment/#using-with-claude-code)
- [Available MCP Tools](https://docs.crawl4ai.com/core/docker-deployment/#available-mcp-tools)
- [Testing MCP Connections](https://docs.crawl4ai.com/core/docker-deployment/#testing-mcp-connections)
- [MCP Schemas](https://docs.crawl4ai.com/core/docker-deployment/#mcp-schemas)
- [Additional API Endpoints](https://docs.crawl4ai.com/core/docker-deployment/#additional-api-endpoints)
- [HTML Extraction Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#html-extraction-endpoint)
- [Screenshot Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#screenshot-endpoint)
- [PDF Export Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#pdf-export-endpoint)
- [JavaScript Execution Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#javascript-execution-endpoint)
- [User-Provided Hooks API](https://docs.crawl4ai.com/core/docker-deployment/#user-provided-hooks-api)
- [Hook Information Endpoint](https://docs.crawl4ai.com/core/docker-deployment/#hook-information-endpoint)
- [Available Hook Points](https://docs.crawl4ai.com/core/docker-deployment/#available-hook-points)
- [Using Hooks in Requests](https://docs.crawl4ai.com/core/docker-deployment/#using-hooks-in-requests)
- [Hook Examples with Real URLs](https://docs.crawl4ai.com/core/docker-deployment/#hook-examples-with-real-urls)
- [1. Authentication with Cookies (GitHub)](https://docs.crawl4ai.com/core/docker-deployment/#1-authentication-with-cookies-github)
- [2. Basic Authentication (httpbin.org for testing)](https://docs.crawl4ai.com/core/docker-deployment/#2-basic-authentication-httpbinorg-for-testing)
- [3. Performance Optimization (News Sites)](https://docs.crawl4ai.com/core/docker-deployment/#3-performance-optimization-news-sites)
- [4. Handling Infinite Scroll (Twitter/X)](https://docs.crawl4ai.com/core/docker-deployment/#4-handling-infinite-scroll-twitterx)
- [5. E-commerce Login (Example Pattern)](https://docs.crawl4ai.com/core/docker-deployment/#5-e-commerce-login-example-pattern)
- [6. Extracting Structured Data (Wikipedia)](https://docs.crawl4ai.com/core/docker-deployment/#6-extracting-structured-data-wikipedia)
- [Security Best Practices](https://docs.crawl4ai.com/core/docker-deployment/#security-best-practices)
- [Hook Response Information](https://docs.crawl4ai.com/core/docker-deployment/#hook-response-information)
- [Error Handling](https://docs.crawl4ai.com/core/docker-deployment/#error-handling)
- [Complete Example: Safe Multi-Hook Crawling](https://docs.crawl4ai.com/core/docker-deployment/#complete-example-safe-multi-hook-crawling)
- [Dockerfile Parameters](https://docs.crawl4ai.com/core/docker-deployment/#dockerfile-parameters)
- [Build Arguments Explained](https://docs.crawl4ai.com/core/docker-deployment/#build-arguments-explained)
- [Build Best Practices](https://docs.crawl4ai.com/core/docker-deployment/#build-best-practices)
- [Using the API](https://docs.crawl4ai.com/core/docker-deployment/#using-the-api)
- [Playground Interface](https://docs.crawl4ai.com/core/docker-deployment/#playground-interface)
- [Python SDK](https://docs.crawl4ai.com/core/docker-deployment/#python-sdk)
- [Second Approach: Direct API Calls](https://docs.crawl4ai.com/core/docker-deployment/#second-approach-direct-api-calls)
- [More Examples (Ensure Schema example uses type/value wrapper)](https://docs.crawl4ai.com/core/docker-deployment/#more-examples-ensure-schema-example-uses-typevalue-wrapper)
- [LLM Configuration Examples](https://docs.crawl4ai.com/core/docker-deployment/#llm-configuration-examples)
- [Temperature Control](https://docs.crawl4ai.com/core/docker-deployment/#temperature-control)
- [Custom API Endpoints](https://docs.crawl4ai.com/core/docker-deployment/#custom-api-endpoints)
- [Dynamic Provider Selection](https://docs.crawl4ai.com/core/docker-deployment/#dynamic-provider-selection)
- [REST API Examples](https://docs.crawl4ai.com/core/docker-deployment/#rest-api-examples)
- [Simple Crawl](https://docs.crawl4ai.com/core/docker-deployment/#simple-crawl)
- [Streaming Results](https://docs.crawl4ai.com/core/docker-deployment/#streaming-results)
- [Metrics & Monitoring](https://docs.crawl4ai.com/core/docker-deployment/#metrics-monitoring)
- [Server Configuration](https://docs.crawl4ai.com/core/docker-deployment/#server-configuration)
- [Understanding config.yml](https://docs.crawl4ai.com/core/docker-deployment/#understanding-configyml)
- [Customizing Your Configuration](https://docs.crawl4ai.com/core/docker-deployment/#customizing-your-configuration)
- [Method 1: Modify Before Build](https://docs.crawl4ai.com/core/docker-deployment/#method-1-modify-before-build)
- [Method 2: Runtime Mount (Recommended for Custom Deploys)](https://docs.crawl4ai.com/core/docker-deployment/#method-2-runtime-mount-recommended-for-custom-deploys)
- [Configuration Recommendations](https://docs.crawl4ai.com/core/docker-deployment/#configuration-recommendations)
- [Getting Help](https://docs.crawl4ai.com/core/docker-deployment/#getting-help)
- [Summary](https://docs.crawl4ai.com/core/docker-deployment/#summary)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/installation

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/installation/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - Installation
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Installation & Setup (2023 Edition)](https://docs.crawl4ai.com/core/installation/#installation-setup-2023-edition)
- [1. Basic Installation](https://docs.crawl4ai.com/core/installation/#1-basic-installation)
- [2. Initial Setup & Diagnostics](https://docs.crawl4ai.com/core/installation/#2-initial-setup-diagnostics)
- [3. Verifying Installation: A Simple Crawl (Skip this step if you already run crawl4ai-doctor)](https://docs.crawl4ai.com/core/installation/#3-verifying-installation-a-simple-crawl-skip-this-step-if-you-already-run-crawl4ai-doctor)
- [4. Advanced Installation (Optional)](https://docs.crawl4ai.com/core/installation/#4-advanced-installation-optional)
- [5. Docker (Experimental)](https://docs.crawl4ai.com/core/installation/#5-docker-experimental)
- [6. Local Server Mode (Legacy)](https://docs.crawl4ai.com/core/installation/#6-local-server-mode-legacy)
- [Summary](https://docs.crawl4ai.com/core/installation/#summary)

# Installation & Setup (2023 Edition)

## 1. Basic Installation

```
pip install crawl4ai
Copy
```

This installs the **core** Crawl4AI library along with essential dependencies. **No** advanced features (like transformers or PyTorch) are included yet.

## 2. Initial Setup & Diagnostics

### 2.1 Run the Setup Command

After installing, call:

```
crawl4ai-setup
Copy
```

**What does it do?** - Installs or updates required browser dependencies for both regular and undetected modes - Performs OS-level checks (e.g., missing libs on Linux) - Confirms your environment is ready to crawl

### 2.2 Diagnostics

Optionally, you can run **diagnostics** to confirm everything is functioning:

```
crawl4ai-doctor
Copy
```

This command attempts to: - Check Python version compatibility - Verify Playwright installation - Inspect environment variables or library conflicts
If any issues arise, follow its suggestions (e.g., installing additional system packages) and re-run `crawl4ai-setup`.

---

## 3. Verifying Installation: A Simple Crawl (Skip this step if you already run `crawl4ai-doctor`)

Below is a minimal Python script demonstrating a **basic** crawl. It uses our new **`BrowserConfig`**and**`CrawlerRunConfig`**for clarity, though no custom settings are passed in this example:

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.example.com",
        )
        print(result.markdown[:300])  # Show the first 300 characters of extracted text

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Expected** outcome: - A headless browser session loads `example.com` - Crawl4AI returns ~300 characters of markdown.
If errors occur, rerun `crawl4ai-doctor` or manually ensure Playwright is installed correctly.

---

## 4. Advanced Installation (Optional)

**Warning** : Only install these **if you truly need them**. They bring in larger dependencies, including big models, which can increase disk usage and memory load significantly.

### 4.1 Torch, Transformers, or All

- **Text Clustering (Torch)**

```
pip install crawl4ai[torch]
crawl4ai-setup
Copy
```

Installs PyTorch-based features (e.g., cosine similarity or advanced semantic chunking).

- **Transformers**

```
pip install crawl4ai[transformer]
crawl4ai-setup
Copy
```

Adds Hugging Face-based summarization or generation strategies.

- **All Features**

```
pip install crawl4ai[all]
crawl4ai-setup
Copy
```

#### (Optional) Pre-Fetching Models

```
crawl4ai-download-models
Copy
```

This step caches large models locally (if needed). **Only do this** if your workflow requires them.

---

## 5. Docker (Experimental)

We provide a **temporary** Docker approach for testing. **It’s not stable and may break** with future releases. We plan a major Docker revamp in a future stable version, 2025 Q1. If you still want to try:

```
docker pull unclecode/crawl4ai:basic
docker run -p 11235:11235 unclecode/crawl4ai:basic
Copy
```

You can then make POST requests to `http://localhost:11235/crawl` to perform crawls. **Production usage** is discouraged until our new Docker approach is ready (planned in Jan or Feb 2025).

---

## 6. Local Server Mode (Legacy)

Some older docs mention running Crawl4AI as a local server. This approach has been **partially replaced** by the new Docker-based prototype and upcoming stable server release. You can experiment, but expect major changes. Official local server instructions will arrive once the new Docker architecture is finalized.

---

## Summary

1. **Install** with `pip install crawl4ai` and run `crawl4ai-setup`. 2. **Diagnose** with `crawl4ai-doctor` if you see errors. 3. **Verify** by crawling `example.com` with minimal `BrowserConfig` + `CrawlerRunConfig`. 4. **Advanced** features (Torch, Transformers) are **optional** —avoid them if you don’t need them (they significantly increase resource usage). 5. **Docker** is **experimental** —use at your own risk until the stable version is released. 6. **Local server** references in older docs are largely deprecated; a new solution is in progress.
   **Got questions?** Check [GitHub issues](https://github.com/unclecode/crawl4ai/issues) for updates or ask the community!
   Page Copy
   Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/installation/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/installation/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/installation/)

ESC to close

#### On this page

- [1. Basic Installation](https://docs.crawl4ai.com/core/installation/#1-basic-installation)
- [2. Initial Setup & Diagnostics](https://docs.crawl4ai.com/core/installation/#2-initial-setup-diagnostics)
- [2.1 Run the Setup Command](https://docs.crawl4ai.com/core/installation/#21-run-the-setup-command)
- [2.2 Diagnostics](https://docs.crawl4ai.com/core/installation/#22-diagnostics)
- [3. Verifying Installation: A Simple Crawl (Skip this step if you already run crawl4ai-doctor)](https://docs.crawl4ai.com/core/installation/#3-verifying-installation-a-simple-crawl-skip-this-step-if-you-already-run-crawl4ai-doctor)
- [4. Advanced Installation (Optional)](https://docs.crawl4ai.com/core/installation/#4-advanced-installation-optional)
- [4.1 Torch, Transformers, or All](https://docs.crawl4ai.com/core/installation/#41-torch-transformers-or-all)
- [(Optional) Pre-Fetching Models](https://docs.crawl4ai.com/core/installation/#optional-pre-fetching-models)
- [5. Docker (Experimental)](https://docs.crawl4ai.com/core/installation/#5-docker-experimental)
- [6. Local Server Mode (Legacy)](https://docs.crawl4ai.com/core/installation/#6-local-server-mode-legacy)
- [Summary](https://docs.crawl4ai.com/core/installation/#summary)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/examples

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/examples/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- Code Examples
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Code Examples](https://docs.crawl4ai.com/core/examples/#code-examples)
- [Getting Started Examples](https://docs.crawl4ai.com/core/examples/#getting-started-examples)
- [Browser & Crawling Features](https://docs.crawl4ai.com/core/examples/#browser-crawling-features)
- [Advanced Crawling & Deep Crawling](https://docs.crawl4ai.com/core/examples/#advanced-crawling-deep-crawling)
- [Extraction Strategies](https://docs.crawl4ai.com/core/examples/#extraction-strategies)
- [E-commerce & Specialized Crawling](https://docs.crawl4ai.com/core/examples/#e-commerce-specialized-crawling)
- [Anti-Bot & Stealth Features](https://docs.crawl4ai.com/core/examples/#anti-bot-stealth-features)
- [Customization & Security](https://docs.crawl4ai.com/core/examples/#customization-security)
- [Docker & Deployment](https://docs.crawl4ai.com/core/examples/#docker-deployment)
- [Application Examples](https://docs.crawl4ai.com/core/examples/#application-examples)
- [Content Generation & Markdown](https://docs.crawl4ai.com/core/examples/#content-generation-markdown)
- [Running the Examples](https://docs.crawl4ai.com/core/examples/#running-the-examples)
- [Contributing New Examples](https://docs.crawl4ai.com/core/examples/#contributing-new-examples)

# Code Examples

This page provides a comprehensive list of example scripts that demonstrate various features and capabilities of Crawl4AI. Each example is designed to showcase specific functionality, making it easier for you to understand how to implement these features in your own projects.

## Getting Started Examples

| Example          | Description                                                                                                                                                                                                                                                            | Link                                                                                                    |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Hello World      | A simple introductory example demonstrating basic usage of AsyncWebCrawler with JavaScript execution and content filtering.                                                                                                                                            | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/hello_world.py)               |
| Quickstart       | A comprehensive collection of examples showcasing various features including basic crawling, content cleaning, link analysis, JavaScript execution, CSS selectors, media handling, custom hooks, proxy configuration, screenshots, and multiple extraction strategies. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/quickstart.py)                |
| Quickstart Set 1 | Basic examples for getting started with Crawl4AI.                                                                                                                                                                                                                      | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/quickstart_examples_set_1.py) |
| Quickstart Set 2 | More advanced examples for working with Crawl4AI.                                                                                                                                                                                                                      | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/quickstart_examples_set_2.py) |

## Browser & Crawling Features

| Example                    | Description                                                                       | Link                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Built-in Browser           | Demonstrates how to use the built-in browser capabilities.                        | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/builtin_browser_example.py)                |
| Browser Optimization       | Focuses on browser performance optimization techniques.                           | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/browser_optimization_example.py)           |
| arun vs arun_many          | Compares the `arun` and `arun_many` methods for single vs. multiple URL crawling. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/arun_vs_arun_many.py)                      |
| Multiple URLs              | Shows how to crawl multiple URLs asynchronously.                                  | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/async_webcrawler_multiple_urls_example.py) |
| Page Interaction           | Guide on interacting with dynamic elements through clicks.                        | [View Guide](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/tutorial_dynamic_clicks.md)               |
| Crawler Monitor            | Shows how to monitor the crawler's activities and status.                         | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/crawler_monitor_example.py)                |
| Full Page Screenshot & PDF | Guide on capturing full-page screenshots and PDFs from massive webpages.          | [View Guide](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/full_page_screenshot_and_pdf_export.md)   |

## Advanced Crawling & Deep Crawling

| Example                 | Description                                                                                                                                                                      | Link                                                                                                          |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Deep Crawling           | An extensive tutorial on deep crawling capabilities, demonstrating BFS and BestFirst strategies, stream vs. non-stream execution, filters, scorers, and advanced configurations. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/deepcrawl_example.py)               |
| Virtual Scroll          | Comprehensive examples for handling virtualized scrolling on sites like Twitter, Instagram. Demonstrates different scrolling scenarios with local test server.                   | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/virtual_scroll_example.py)          |
| Adaptive Crawling       | Demonstrates intelligent crawling that automatically determines when sufficient information has been gathered.                                                                   | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/adaptive_crawling/)                 |
| Dispatcher              | Shows how to use the crawl dispatcher for advanced workload management.                                                                                                          | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/dispatcher_example.py)              |
| Storage State           | Tutorial on managing browser storage state for persistence.                                                                                                                      | [View Guide](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/storage_state_tutorial.md)         |
| Network Console Capture | Demonstrates how to capture and analyze network requests and console logs.                                                                                                       | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/network_console_capture_example.py) |

## Extraction Strategies

| Example               | Description                                                                                                                                       | Link                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Extraction Strategies | Demonstrates different extraction strategies with various input formats (markdown, HTML, fit_markdown) and JSON-based extractors (CSS and XPath). | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/extraction_strategies_examples.py)  |
| Scraping Strategies   | Compares the performance of different scraping strategies.                                                                                        | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/scraping_strategies_performance.py) |
| LLM Extraction        | Demonstrates LLM-based extraction specifically for OpenAI pricing data.                                                                           | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/llm_extraction_openai_pricing.py)   |
| LLM Markdown          | Shows how to use LLMs to generate markdown from crawled content.                                                                                  | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/llm_markdown_generator.py)          |
| Summarize Page        | Shows how to summarize web page content.                                                                                                          | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/summarize_page.py)                  |

## E-commerce & Specialized Crawling

| Example                   | Description                                                                                         | Link                                                                                                                         |
| ------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Amazon Product Extraction | Demonstrates how to extract structured product data from Amazon search results using CSS selectors. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/amazon_product_extraction_direct_url.py)           |
| Amazon with Hooks         | Shows how to use hooks with Amazon product extraction.                                              | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/amazon_product_extraction_using_hooks.py)          |
| Amazon with JavaScript    | Demonstrates using custom JavaScript for Amazon product extraction.                                 | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/amazon_product_extraction_using_use_javascript.py) |
| Crypto Analysis           | Demonstrates how to crawl and analyze cryptocurrency data.                                          | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/crypto_analysis_example.py)                        |
| SERP API                  | Demonstrates using Crawl4AI with search engine result pages.                                        | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/serp_api_project_11_feb.py)                        |

## Anti-Bot & Stealth Features

| Example                    | Description                                                                                      | Link                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Stealth Mode Quick Start   | Five practical examples showing how to use stealth mode for bypassing basic bot detection.       | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/stealth_mode_quick_start.py) |
| Stealth Mode Comprehensive | Comprehensive demonstration of stealth mode features with bot detection testing and comparisons. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/stealth_mode_example.py)     |
| Undetected Browser         | Simple example showing how to use the undetected browser adapter.                                | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/hello_world_undetected.py)   |
| Undetected Browser Demo    | Basic demo comparing regular and undetected browser modes.                                       | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/undetected_simple_demo.py)   |
| Undetected Tests           | Advanced tests comparing regular vs undetected browsers on various bot detection services.       | [View Folder](https://github.com/unclecode/crawl4ai/tree/main/docs/examples/undetectability/)          |

## Customization & Security

| Example                 | Description                                                                                          | Link                                                                                                   |
| ----------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Hooks                   | Illustrates how to use hooks at different stages of the crawling process for advanced customization. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/hooks_example.py)            |
| Identity-Based Browsing | Illustrates identity-based browsing configurations for authentic browsing experiences.               | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/identity_based_browsing.py)  |
| Proxy Rotation          | Shows how to use proxy rotation for web scraping and avoiding IP blocks.                             | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/proxy_rotation_demo.py)      |
| SSL Certificate         | Illustrates SSL certificate handling and verification.                                               | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/ssl_example.py)              |
| Language Support        | Shows how to handle different languages during crawling.                                             | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/language_support_example.py) |
| Geolocation             | Demonstrates how to use geolocation features.                                                        | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/use_geo_location.py)         |

## Docker & Deployment

| Example         | Description                                                                                    | Link                                                                                                 |
| --------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Docker Config   | Demonstrates how to create and use Docker configuration objects.                               | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/docker_config_obj.py)      |
| Docker Basic    | A test suite for Docker deployment, showcasing various functionalities through the Docker API. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/docker_example.py)         |
| Docker REST API | Shows how to interact with Crawl4AI Docker using REST API calls.                               | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/docker_python_rest_api.py) |
| Docker SDK      | Demonstrates using the Python SDK for Crawl4AI Docker.                                         | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/docker_python_sdk.py)      |

## Application Examples

| Example               | Description                                                    | Link                                                                                               |
| --------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Research Assistant    | Demonstrates how to build a research assistant using Crawl4AI. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/research_assistant.py)   |
| REST Call             | Shows how to make REST API calls with Crawl4AI.                | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/rest_call.py)            |
| Chainlit Integration  | Shows how to integrate Crawl4AI with Chainlit.                 | [View Guide](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/chainlit.md)            |
| Crawl4AI vs FireCrawl | Compares Crawl4AI with the FireCrawl library.                  | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/crawlai_vs_firecrawl.py) |

## Content Generation & Markdown

| Example                | Description                                                                     | Link                                                                                                                |
| ---------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Content Source         | Demonstrates how to work with different content sources in markdown generation. | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/markdown/content_source_example.py)       |
| Content Source (Short) | A simplified version of content source usage.                                   | [View Code](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/markdown/content_source_short_example.py) |
| Built-in Browser Guide | Guide for using the built-in browser capabilities.                              | [View Guide](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/README_BUILTIN_BROWSER.md)               |

## Running the Examples

To run any of these examples, you'll need to have Crawl4AI installed:

```
pip install crawl4ai
Copy
```

Then, you can run an example script like this:

```
python -m docs.examples.hello_world
Copy
```

For examples that require additional dependencies or environment variables, refer to the comments at the top of each file.
Some examples may require: - API keys (for LLM-based examples) - Docker setup (for Docker-related examples) - Additional dependencies (specified in the example files)

## Contributing New Examples

If you've created an interesting example that demonstrates a unique use case or feature of Crawl4AI, we encourage you to contribute it to our examples collection. Please see our [contribution guidelines](https://github.com/unclecode/crawl4ai/blob/main/CONTRIBUTORS.md) for more information.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/examples/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/examples/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/examples/)

ESC to close

#### On this page

- [Getting Started Examples](https://docs.crawl4ai.com/core/examples/#getting-started-examples)
- [Browser & Crawling Features](https://docs.crawl4ai.com/core/examples/#browser-crawling-features)
- [Advanced Crawling & Deep Crawling](https://docs.crawl4ai.com/core/examples/#advanced-crawling-deep-crawling)
- [Extraction Strategies](https://docs.crawl4ai.com/core/examples/#extraction-strategies)
- [E-commerce & Specialized Crawling](https://docs.crawl4ai.com/core/examples/#e-commerce-specialized-crawling)
- [Anti-Bot & Stealth Features](https://docs.crawl4ai.com/core/examples/#anti-bot-stealth-features)
- [Customization & Security](https://docs.crawl4ai.com/core/examples/#customization-security)
- [Docker & Deployment](https://docs.crawl4ai.com/core/examples/#docker-deployment)
- [Application Examples](https://docs.crawl4ai.com/core/examples/#application-examples)
- [Content Generation & Markdown](https://docs.crawl4ai.com/core/examples/#content-generation-markdown)
- [Running the Examples](https://docs.crawl4ai.com/core/examples/#running-the-examples)
- [Contributing New Examples](https://docs.crawl4ai.com/core/examples/#contributing-new-examples)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/browser-crawler-config

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/browser-crawler-config/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - Browser, Crawler & LLM Config
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Browser, Crawler & LLM Configuration (Quick Overview)](https://docs.crawl4ai.com/core/browser-crawler-config/#browser-crawler-llm-configuration-quick-overview)
- [1. BrowserConfig Essentials](https://docs.crawl4ai.com/core/browser-crawler-config/#1-browserconfig-essentials)
- [2. CrawlerRunConfig Essentials](https://docs.crawl4ai.com/core/browser-crawler-config/#2-crawlerrunconfig-essentials)
- [3. LLMConfig Essentials](https://docs.crawl4ai.com/core/browser-crawler-config/#3-llmconfig-essentials)
- [4. Putting It All Together](https://docs.crawl4ai.com/core/browser-crawler-config/#4-putting-it-all-together)
- [5. Next Steps](https://docs.crawl4ai.com/core/browser-crawler-config/#5-next-steps)
- [6. Conclusion](https://docs.crawl4ai.com/core/browser-crawler-config/#6-conclusion)

# Browser, Crawler & LLM Configuration (Quick Overview)

Crawl4AI's flexibility stems from two key classes:

1. **`BrowserConfig`**– Dictates**how** the browser is launched and behaves (e.g., headless or visible, proxy, user agent).
2. **`CrawlerRunConfig`**– Dictates**how** each **crawl** operates (e.g., caching, extraction, timeouts, JavaScript code to run, etc.).
3. **`LLMConfig`**- Dictates**how** LLM providers are configured. (model, api token, base url, temperature etc.)

In most examples, you create **one** `BrowserConfig` for the entire crawler session, then pass a **fresh** or re-used `CrawlerRunConfig` whenever you call `arun()`. This tutorial shows the most commonly used parameters. If you need advanced or rarely used fields, see the [Configuration Parameters](https://docs.crawl4ai.com/api/parameters/).

---

## 1. BrowserConfig Essentials

```
class BrowserConfig:
    def __init__(
        browser_type="chromium",
        headless=True,
        proxy_config=None,
        viewport_width=1080,
        viewport_height=600,
        verbose=True,
        use_persistent_context=False,
        user_data_dir=None,
        cookies=None,
        headers=None,
        user_agent=None,
        text_mode=False,
        light_mode=False,
        extra_args=None,
        enable_stealth=False,
        # ... other advanced parameters omitted here
    ):
        ...
Copy
```

### Key Fields to Note

1. **`browser_type`**
2. Options: `"chromium"`, `"firefox"`, or `"webkit"`.
3. Defaults to `"chromium"`.
4. If you need a different engine, specify it here.
5. **`headless`**
6. `True`: Runs the browser in headless mode (invisible browser).
7. `False`: Runs the browser in visible mode, which helps with debugging.
8. **`proxy_config`**
9. A dictionary with fields like:

```
{
    "server": "http://proxy.example.com:8080",
    "username": "...",
    "password": "..."
}
Copy
```

10. Leave as `None` if a proxy is not required.
11. **`viewport_width` & `viewport_height`**:
12. The initial window size.
13. Some sites behave differently with smaller or bigger viewports.
14. **`verbose`**:
15. If `True`, prints extra logs.
16. Handy for debugging.
17. **`use_persistent_context`**:
18. If `True`, uses a **persistent** browser profile, storing cookies/local storage across runs.
19. Typically also set `user_data_dir` to point to a folder.
20. **`cookies`** & **`headers`**:
21. If you want to start with specific cookies or add universal HTTP headers, set them here.
22. E.g. `cookies=[{"name": "session", "value": "abc123", "domain": "example.com"}]`.
23. **`user_agent`**:
24. Custom User-Agent string. If `None`, a default is used.
25. You can also set `user_agent_mode="random"` for randomization (if you want to fight bot detection).
26. **`text_mode`** & **`light_mode`**:
27. `text_mode=True` disables images, possibly speeding up text-only crawls.
28. `light_mode=True` turns off certain background features for performance.
29. **`extra_args`**:

    - Additional flags for the underlying browser.
    - E.g. `["--disable-extensions"]`.

30. **`enable_stealth`**:

    - If `True`, enables stealth mode using playwright-stealth.
    - Modifies browser fingerprints to avoid basic bot detection.
    - Default is `False`. Recommended for sites with bot protection.

### Helper Methods

Both configuration classes provide a `clone()` method to create modified copies:

```
# Create a base browser config
base_browser = BrowserConfig(
    browser_type="chromium",
    headless=True,
    text_mode=True
)

# Create a visible browser config for debugging
debug_browser = base_browser.clone(
    headless=False,
    verbose=True
)
Copy
```

**Minimal Example** :

```
from crawl4ai import AsyncWebCrawler, BrowserConfig

browser_conf = BrowserConfig(
    browser_type="firefox",
    headless=False,
    text_mode=True
)

async with AsyncWebCrawler(config=browser_conf) as crawler:
    result = await crawler.arun("https://example.com")
    print(result.markdown[:300])
Copy
```

---

## 2. CrawlerRunConfig Essentials

```
class CrawlerRunConfig:
    def __init__(
        word_count_threshold=200,
        extraction_strategy=None,
        markdown_generator=None,
        cache_mode=None,
        js_code=None,
        wait_for=None,
        screenshot=False,
        pdf=False,
        capture_mhtml=False,
        # Location and Identity Parameters
        locale=None,            # e.g. "en-US", "fr-FR"
        timezone_id=None,       # e.g. "America/New_York"
        geolocation=None,       # GeolocationConfig object
        # Resource Management
        enable_rate_limiting=False,
        rate_limit_config=None,
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=20,
        display_mode=None,
        verbose=True,
        stream=False,  # Enable streaming for arun_many()
        # ... other advanced parameters omitted
    ):
        ...
Copy
```

### Key Fields to Note

1. **`word_count_threshold`**:
2. The minimum word count before a block is considered.
3. If your site has lots of short paragraphs or items, you can lower it.
4. **`extraction_strategy`**:
5. Where you plug in JSON-based extraction (CSS, LLM, etc.).
6. If `None`, no structured extraction is done (only raw/cleaned HTML + markdown).
7. **`markdown_generator`**:
8. E.g., `DefaultMarkdownGenerator(...)`, controlling how HTML→Markdown conversion is done.
9. If `None`, a default approach is used.
10. **`cache_mode`**:
11. Controls caching behavior (`ENABLED`, `BYPASS`, `DISABLED`, etc.).
12. If `None`, defaults to some level of caching or you can specify `CacheMode.ENABLED`.
13. **`js_code`**:
14. A string or list of JS strings to execute.
15. Great for "Load More" buttons or user interactions.
16. **`wait_for`**:
17. A CSS or JS expression to wait for before extracting content.
18. Common usage: `wait_for="css:.main-loaded"` or `wait_for="js:() => window.loaded === true"`.
19. **`screenshot`**,**`pdf`**, & **`capture_mhtml`**:
20. If `True`, captures a screenshot, PDF, or MHTML snapshot after the page is fully loaded.
21. The results go to `result.screenshot` (base64), `result.pdf` (bytes), or `result.mhtml` (string).
22. **Location Parameters** :
23. **`locale`**: Browser's locale (e.g.,`"en-US"` , `"fr-FR"`) for language preferences
24. **`timezone_id`**: Browser's timezone (e.g.,`"America/New_York"` , `"Europe/Paris"`)
25. **`geolocation`**: GPS coordinates via`GeolocationConfig(latitude=48.8566, longitude=2.3522)`
26. See [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/#7-locale-timezone-and-geolocation-control)
27. **`verbose`**:
28. Logs additional runtime details.
29. Overlaps with the browser's verbosity if also set to `True` in `BrowserConfig`.
30. **`enable_rate_limiting`**:
31. If `True`, enables rate limiting for batch processing.
32. Requires `rate_limit_config` to be set.
33. **`memory_threshold_percent`**:

    - The memory threshold (as a percentage) to monitor.
    - If exceeded, the crawler will pause or slow down.

34. **`check_interval`**:

    - The interval (in seconds) to check system resources.
    - Affects how often memory and CPU usage are monitored.

35. **`max_session_permit`**:

    - The maximum number of concurrent crawl sessions.
    - Helps prevent overwhelming the system.

36. **`url_matcher`** & **`match_mode`**:

    - Enable URL-specific configurations when used with `arun_many()`.
    - Set `url_matcher` to patterns (glob, function, or list) to match specific URLs.
    - Use `match_mode` (OR/AND) to control how multiple patterns combine.
    - See [URL-Specific Configurations](https://docs.crawl4ai.com/api/arun_many/#url-specific-configurations) for examples.

37. **`display_mode`**:

    - The display mode for progress information (`DETAILED`, `BRIEF`, etc.).
    - Affects how much information is printed during the crawl.

### Helper Methods

The `clone()` method is particularly useful for creating variations of your crawler configuration:

```
# Create a base configuration
base_config = CrawlerRunConfig(
    cache_mode=CacheMode.ENABLED,
    word_count_threshold=200,
    wait_until="networkidle"
)

# Create variations for different use cases
stream_config = base_config.clone(
    stream=True,  # Enable streaming mode
    cache_mode=CacheMode.BYPASS
)

debug_config = base_config.clone(
    page_timeout=120000,  # Longer timeout for debugging
    verbose=True
)
Copy
```

The `clone()` method: - Creates a new instance with all the same settings - Updates only the specified parameters - Leaves the original configuration unchanged - Perfect for creating variations without repeating all parameters

---

## 3. LLMConfig Essentials

### Key fields to note

1. **`provider`**:
2. Which LLM provider to use.
3. Possible values are `"ollama/llama3","groq/llama3-70b-8192","groq/llama3-8b-8192", "openai/gpt-4o-mini" ,"openai/gpt-4o","openai/o1-mini","openai/o1-preview","openai/o3-mini","openai/o3-mini-high","anthropic/claude-3-haiku-20240307","anthropic/claude-3-opus-20240229","anthropic/claude-3-sonnet-20240229","anthropic/claude-3-5-sonnet-20240620","gemini/gemini-pro","gemini/gemini-1.5-pro","gemini/gemini-2.0-flash","gemini/gemini-2.0-flash-exp","gemini/gemini-2.0-flash-lite-preview-02-05","deepseek/deepseek-chat"`
   _(default:`"openai/gpt-4o-mini"`)_
4. **`api_token`**:
   _ Optional. When not provided explicitly, api_token will be read from environment variables based on provider. For example: If a gemini model is passed as provider then,`"GEMINI_API_KEY"` will be read from environment variables
   _ API token of LLM provider
   eg: `api_token = "gsk_1ClHGGJ7Lpn4WGybR7vNWGdyb3FY7zXEw3SCiy0BAVM9lL8CQv"` \* Environment variable - use with prefix "env:"
   eg:`api_token = "env: GROQ_API_KEY"`
5. **`base_url`**:
6. If your provider has a custom endpoint

```
llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY"))
Copy
```

## 4. Putting It All Together

In a typical scenario, you define **one** `BrowserConfig` for your crawler session, then create **one or more** `CrawlerRunConfig` & `LLMConfig` depending on each call's needs:

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig, LLMContentFilter, DefaultMarkdownGenerator
from crawl4ai import JsonCssExtractionStrategy

async def main():
    # 1) Browser config: headless, bigger viewport, no proxy
    browser_conf = BrowserConfig(
        headless=True,
        viewport_width=1280,
        viewport_height=720
    )

    # 2) Example extraction strategy
    schema = {
        "name": "Articles",
        "baseSelector": "div.article",
        "fields": [
            {"name": "title", "selector": "h2", "type": "text"},
            {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
        ]
    }
    extraction = JsonCssExtractionStrategy(schema)

    # 3) Example LLM content filtering

    gemini_config = LLMConfig(
        provider="gemini/gemini-1.5-pro",
        api_token = "env:GEMINI_API_TOKEN"
    )

    # Initialize LLM filter with specific instruction
    filter = LLMContentFilter(
        llm_config=gemini_config,  # or your preferred provider
        instruction="""
        Focus on extracting the core educational content.
        Include:
        - Key concepts and explanations
        - Important code examples
        - Essential technical details
        Exclude:
        - Navigation elements
        - Sidebars
        - Footer content
        Format the output as clean markdown with proper code blocks and headers.
        """,
        chunk_token_threshold=500,  # Adjust based on your needs
        verbose=True
    )

    md_generator = DefaultMarkdownGenerator(
        content_filter=filter,
        options={"ignore_links": True}
    )

    # 4) Crawler run config: skip cache, use extraction
    run_conf = CrawlerRunConfig(
        markdown_generator=md_generator,
        extraction_strategy=extraction,
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        # 4) Execute the crawl
        result = await crawler.arun(url="https://example.com/news", config=run_conf)

        if result.success:
            print("Extracted content:", result.extracted_content)
        else:
            print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

## 5. Next Steps

For a **detailed list** of available parameters (including advanced ones), see:

- [BrowserConfig, CrawlerRunConfig & LLMConfig Reference](https://docs.crawl4ai.com/api/parameters/)

You can explore topics like:

- **Custom Hooks & Auth** (Inject JavaScript or handle login forms).
- **Session Management** (Re-use pages, preserve state across multiple calls).
- **Magic Mode** or **Identity-based Crawling** (Fight bot detection by simulating user behavior).
- **Advanced Caching** (Fine-tune read/write cache modes).

---

## 6. Conclusion

**BrowserConfig** , **CrawlerRunConfig** and **LLMConfig** give you straightforward ways to define:

- **Which** browser to launch, how it should run, and any proxy or user agent needs.
- **How** each crawl should behave—caching, timeouts, JavaScript code, extraction strategies, etc.
- **Which** LLM provider to use, api token, temperature and base url for custom endpoints

Use them together for **clear, maintainable** code, and when you need more specialized behavior, check out the advanced parameters in the [reference docs](https://docs.crawl4ai.com/api/parameters/). Happy crawling!
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/browser-crawler-config/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/browser-crawler-config/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/browser-crawler-config/)

ESC to close

#### On this page

- [1. BrowserConfig Essentials](https://docs.crawl4ai.com/core/browser-crawler-config/#1-browserconfig-essentials)
- [Key Fields to Note](https://docs.crawl4ai.com/core/browser-crawler-config/#key-fields-to-note)
- [Helper Methods](https://docs.crawl4ai.com/core/browser-crawler-config/#helper-methods)
- [2. CrawlerRunConfig Essentials](https://docs.crawl4ai.com/core/browser-crawler-config/#2-crawlerrunconfig-essentials)
- [Key Fields to Note](https://docs.crawl4ai.com/core/browser-crawler-config/#key-fields-to-note_1)
- [Helper Methods](https://docs.crawl4ai.com/core/browser-crawler-config/#helper-methods_1)
- [3. LLMConfig Essentials](https://docs.crawl4ai.com/core/browser-crawler-config/#3-llmconfig-essentials)
- [Key fields to note](https://docs.crawl4ai.com/core/browser-crawler-config/#key-fields-to-note_2)
- [4. Putting It All Together](https://docs.crawl4ai.com/core/browser-crawler-config/#4-putting-it-all-together)
- [5. Next Steps](https://docs.crawl4ai.com/core/browser-crawler-config/#5-next-steps)
- [6. Conclusion](https://docs.crawl4ai.com/core/browser-crawler-config/#6-conclusion)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/c4a-script

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/c4a-script/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - C4A-Script
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [C4A-Script: Visual Web Automation Made Simple](https://docs.crawl4ai.com/core/c4a-script/#c4a-script-visual-web-automation-made-simple)
- [What is C4A-Script?](https://docs.crawl4ai.com/core/c4a-script/#what-is-c4a-script)
- [Getting Started: Your First Script](https://docs.crawl4ai.com/core/c4a-script/#getting-started-your-first-script)
- [Interactive Tutorial & Live Demo](https://docs.crawl4ai.com/core/c4a-script/#interactive-tutorial-live-demo)
- [Core Concepts](https://docs.crawl4ai.com/core/c4a-script/#core-concepts)
- [Command Categories](https://docs.crawl4ai.com/core/c4a-script/#command-categories)
- [Real-World Examples](https://docs.crawl4ai.com/core/c4a-script/#real-world-examples)
- [Visual Programming with Blockly](https://docs.crawl4ai.com/core/c4a-script/#visual-programming-with-blockly)
- [Advanced Features](https://docs.crawl4ai.com/core/c4a-script/#advanced-features)
- [Best Practices](https://docs.crawl4ai.com/core/c4a-script/#best-practices)
- [Getting Help](https://docs.crawl4ai.com/core/c4a-script/#getting-help)
- [What's Next?](https://docs.crawl4ai.com/core/c4a-script/#whats-next)

# C4A-Script: Visual Web Automation Made Simple

## What is C4A-Script?

C4A-Script is a powerful, human-readable domain-specific language (DSL) designed for web automation and interaction. Think of it as a simplified programming language that anyone can read and write, perfect for automating repetitive web tasks, testing user interfaces, or creating interactive demos.

### Why C4A-Script?

**Simple Syntax, Powerful Results**

```
# Navigate and interact in plain English
GO https://example.com
WAIT `#search-box` 5
TYPE "Hello World"
CLICK `button[type="submit"]`
Copy
```

**Visual Programming Support** C4A-Script comes with a built-in Blockly visual editor, allowing you to create scripts by dragging and dropping blocks - no coding experience required!
**Perfect for:** - **UI Testing** : Automate user interaction flows - **Demo Creation** : Build interactive product demonstrations

- **Data Entry** : Automate form filling and submissions - **Testing Workflows** : Validate complex user journeys - **Training** : Teach web automation without code complexity

## Getting Started: Your First Script

Let's create a simple script that searches for something on a website:

```
# My first C4A-Script
GO https://duckduckgo.com

# Wait for the search box to appear
WAIT `input[name="q"]` 10

# Type our search query
TYPE "Crawl4AI"

# Press Enter to search
PRESS Enter

# Wait for results
WAIT `.results` 5
Copy
```

That's it! In just a few lines, you've automated a complete search workflow.

## Interactive Tutorial & Live Demo

Want to learn by doing? We've got you covered:
**🚀[Live Demo](https://docs.crawl4ai.com/apps/c4a-script/)** - Try C4A-Script in your browser right now!
**📁[Tutorial Examples](https://github.com/unclecode/crawl4ai/blob/main/docs/examples/c4a_script/)** - Complete examples with source code

### Running the Tutorial Locally

The tutorial includes a Flask-based web interface with: - **Live Code Editor** with syntax highlighting - **Visual Blockly Editor** for drag-and-drop programming - **Recording Mode** to capture your actions and generate scripts - **Timeline View** to see and edit your automation steps

```
# Clone and navigate to the tutorial
cd docs/examples/c4a_script/tutorial/

# Install dependencies
pip install flask

# Launch the tutorial server
python app.py

# Open http://localhost:5000 in your browser
Copy
```

## Core Concepts

### Commands and Syntax

C4A-Script uses simple, English-like commands. Each command does one specific thing:

```
# Comments start with #
COMMAND parameter1 parameter2

# Most commands use CSS selectors in backticks
CLICK `#submit-button`

# Text content goes in quotes
TYPE "Hello, World!"

# Numbers are used directly
WAIT 3
Copy
```

### Selectors: Finding Elements

C4A-Script uses CSS selectors to identify elements on the page:

```
# By ID
CLICK `#login-button`

# By class
CLICK `.submit-btn`

# By attribute
CLICK `button[type="submit"]`

# By text content
CLICK `button:contains("Sign In")`

# Complex selectors
CLICK `.form-container input[name="email"]`
Copy
```

### Variables and Dynamic Content

Store and reuse values with variables:

```
# Set a variable
SETVAR username = "john@example.com"
SETVAR password = "secret123"

# Use variables (prefix with $)
TYPE $username
PRESS Tab
TYPE $password
Copy
```

## Command Categories

### 🧭 Navigation Commands

Move around the web like a user would:
Command | Purpose | Example
---|---|---
`GO` | Navigate to URL | `GO https://example.com`
`RELOAD` | Refresh current page | `RELOAD`
`BACK` | Go back in history | `BACK`
`FORWARD` | Go forward in history | `FORWARD`

### ⏱️ Wait Commands

Ensure elements are ready before interacting:
Command | Purpose | Example
---|---|---
`WAIT` | Wait for time/element/text | `WAIT 3` or `WAIT \`#element` 10`

### 🖱️ Mouse Commands

Click, drag, and move like a human:
Command | Purpose | Example
---|---|---
`CLICK` | Click element or coordinates | `CLICK \`button`` or`CLICK 100 200`
`DOUBLE_CLICK` | Double-click element |  `DOUBLE_CLICK \`.item ``
`RIGHT_CLICK` | Right-click element | `RIGHT_CLICK \`#menu``
`SCROLL`| Scroll in direction |`SCROLL DOWN 500`
`DRAG`| Drag from point to point |`DRAG 100 100 500 300`

### ⌨️ Keyboard Commands

Type text and press keys naturally:
Command | Purpose | Example
---|---|---
`TYPE` | Type text or variable | `TYPE "Hello"` or `TYPE $username`
`PRESS` | Press special keys | `PRESS Tab` or `PRESS Enter`
`CLEAR` | Clear input field | `CLEAR \`#search``
`SET`| Set input value directly | `SET \`#email` "user@example.com"`

### 🔀 Control Flow

Add logic and repetition to your scripts:
Command | Purpose | Example
---|---|---
`IF` | Conditional execution | `IF (EXISTS \`#popup`) THEN CLICK `#close``
`REPEAT`| Loop commands |`REPEAT (SCROLL DOWN 300, 5)`

### 💾 Variables & Advanced

Store data and execute custom code:
Command | Purpose | Example
---|---|---
`SETVAR` | Create variable | `SETVAR email = "test@example.com"`
`EVAL` | Execute JavaScript | `EVAL \`console.log('Hello')``

## Real-World Examples

### Example 1: Login Flow

```
# Complete login automation
GO https://myapp.com/login

# Wait for page to load
WAIT `#login-form` 5

# Fill credentials
CLICK `#email`
TYPE "user@example.com"
PRESS Tab
TYPE "mypassword"

# Submit form
CLICK `button[type="submit"]`

# Wait for dashboard
WAIT `.dashboard` 10
Copy
```

### Example 2: E-commerce Shopping

```
# Shopping automation with variables
SETVAR product = "laptop"
SETVAR budget = "1000"

GO https://shop.example.com
WAIT `#search-box` 3

# Search for product
TYPE $product
PRESS Enter
WAIT `.product-list` 5

# Filter by price
CLICK `.price-filter`
SET `#max-price` $budget
CLICK `.apply-filters`

# Select first result
WAIT `.product-item` 3
CLICK `.product-item:first-child`
Copy
```

### Example 3: Form Automation with Conditions

```
# Smart form filling with error handling
GO https://forms.example.com

# Check if user is already logged in
IF (EXISTS `.user-menu`) THEN GO https://forms.example.com/new
IF (NOT EXISTS `.user-menu`) THEN CLICK `#login-link`

# Fill form
WAIT `#contact-form` 5
SET `#name` "John Doe"
SET `#email` "john@example.com"
SET `#message` "Hello from C4A-Script!"

# Handle popup if it appears
IF (EXISTS `.cookie-banner`) THEN CLICK `.accept-cookies`

# Submit
CLICK `#submit-button`
WAIT `.success-message` 10
Copy
```

## Visual Programming with Blockly

C4A-Script includes a powerful visual programming interface built on Google Blockly. Perfect for:

- **Non-programmers** who want to create automation
- **Rapid prototyping** of automation workflows
- **Educational environments** for teaching automation concepts
- **Collaborative development** where visual representation helps communication

### Features:

- **Drag & Drop Interface**: Build scripts by connecting blocks
- **Real-time Sync** : Changes in visual mode instantly update the text script
- **Smart Block Types** : Blocks are categorized by function (Navigation, Actions, etc.)
- **Error Prevention** : Visual connections prevent syntax errors
- **Comment Support** : Add visual comment blocks for documentation

Try the visual editor in our [live demo](https://docs.crawl4ai.com/c4a-script/demo) or [local tutorial](https://docs.crawl4ai.com/examples/c4a_script/tutorial/).

## Advanced Features

### Recording Mode

The tutorial interface includes a recording feature that watches your browser interactions and automatically generates C4A-Script commands:

1. Click "Record" in the tutorial interface
2. Perform actions in the browser preview
3. Watch as C4A-Script commands are generated in real-time
4. Edit and refine the generated script

### Error Handling and Debugging

C4A-Script provides clear error messages and debugging information:

```
# Use comments for debugging
# This will wait up to 10 seconds for the element
WAIT `#slow-loading-element` 10

# Check if element exists before clicking
IF (EXISTS `#optional-button`) THEN CLICK `#optional-button`

# Use EVAL for custom debugging
EVAL `console.log("Current page title:", document.title)`
Copy
```

### Integration with Crawl4AI

C4A-Script integrates seamlessly with Crawl4AI's web crawling capabilities:

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

# Use C4A-Script for interaction before crawling
script = """
GO https://example.com
CLICK `#load-more-content`
WAIT `.dynamic-content` 5
"""

config = CrawlerRunConfig(
    js_code=script,
    wait_for=".dynamic-content"
)

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun("https://example.com", config=config)
    print(result.markdown)
Copy
```

## Best Practices

### 1. Always Wait for Elements

```
# Bad: Clicking immediately
CLICK `#button`

# Good: Wait for element to appear
WAIT `#button` 5
CLICK `#button`
Copy
```

### 2. Use Descriptive Comments

```
# Login to user account
GO https://myapp.com/login
WAIT `#login-form` 5

# Enter credentials
TYPE "user@example.com"
PRESS Tab
TYPE "password123"

# Submit and wait for redirect
CLICK `#submit-button`
WAIT `.dashboard` 10
Copy
```

### 3. Handle Variable Conditions

```
# Handle different page states
IF (EXISTS `.cookie-banner`) THEN CLICK `.accept-cookies`
IF (EXISTS `.popup-modal`) THEN CLICK `.close-modal`

# Proceed with main workflow
CLICK `#main-action`
Copy
```

### 4. Use Variables for Reusability

```
# Define once, use everywhere
SETVAR base_url = "https://myapp.com"
SETVAR test_email = "test@example.com"

GO $base_url/login
SET `#email` $test_email
Copy
```

## Getting Help

- **📖[Complete Examples](https://docs.crawl4ai.com/examples/c4a_script/)** - Real-world automation scripts
- **🎮[Interactive Tutorial](https://docs.crawl4ai.com/examples/c4a_script/tutorial/)** - Hands-on learning environment
- **📋[API Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)** - Detailed command documentation
- **🌐[Live Demo](https://docs.crawl4ai.com/c4a-script/demo)** - Try it in your browser

## What's Next?

Ready to dive deeper? Check out:

1. **[API Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)** - Complete command documentation
2. **[Tutorial Examples](https://docs.crawl4ai.com/examples/c4a_script/)** - Copy-paste ready scripts
3. **[Local Tutorial Setup](https://docs.crawl4ai.com/examples/c4a_script/tutorial/)** - Run the full development environment

C4A-Script makes web automation accessible to everyone. Whether you're a developer automating tests, a designer creating interactive demos, or a business user streamlining repetitive tasks, C4A-Script has the tools you need.
_Start automating today - your future self will thank you!_ 🚀

- [Crawl Result and Output](https://docs.crawl4ai.com/core/crawler-result/#crawl-result-and-output)
- [1. The CrawlResult Model](https://docs.crawl4ai.com/core/crawler-result/#1-the-crawlresult-model)
- [2. HTML Variants](https://docs.crawl4ai.com/core/crawler-result/#2-html-variants)
- [3. Markdown Generation](https://docs.crawl4ai.com/core/crawler-result/#3-markdown-generation)
- [4. Structured Extraction: extracted_content](https://docs.crawl4ai.com/core/crawler-result/#4-structured-extraction-extracted_content)
- [5. More Fields: Links, Media, Tables and More](https://docs.crawl4ai.com/core/crawler-result/#5-more-fields-links-media-tables-and-more)
- [6. Accessing These Fields](https://docs.crawl4ai.com/core/crawler-result/#6-accessing-these-fields)
- [7. Next Steps](https://docs.crawl4ai.com/core/crawler-result/#7-next-steps)

# Crawl Result and Output

When you call `arun()` on a page, Crawl4AI returns a **`CrawlResult`**object containing everything you might need—raw HTML, a cleaned version, optional screenshots or PDFs, structured extraction results, and more. This document explains those fields and how they map to different output types.

---

## 1. The `CrawlResult` Model

Below is the core schema. Each field captures a different aspect of the crawl’s result:

```
class MarkdownGenerationResult(BaseModel):
    raw_markdown: str
    markdown_with_citations: str
    references_markdown: str
    fit_markdown: Optional[str] = None
    fit_html: Optional[str] = None

class CrawlResult(BaseModel):
    url: str
    html: str
    fit_html: Optional[str] = None
    success: bool
    cleaned_html: Optional[str] = None
    media: Dict[str, List[Dict]] = {}
    links: Dict[str, List[Dict]] = {}
    downloaded_files: Optional[List[str]] = None
    js_execution_result: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    pdf: Optional[bytes] = None
    mhtml: Optional[str] = None
    markdown: Optional[Union[str, MarkdownGenerationResult]] = None
    extracted_content: Optional[str] = None
    metadata: Optional[dict] = None
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    response_headers: Optional[dict] = None
    status_code: Optional[int] = None
    ssl_certificate: Optional[SSLCertificate] = None
    dispatch_result: Optional[DispatchResult] = None
    redirected_url: Optional[str] = None
    network_requests: Optional[List[Dict[str, Any]]] = None
    console_messages: Optional[List[Dict[str, Any]]] = None
    tables: List[Dict] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
Copy
```

### Table: Key Fields in `CrawlResult`

| Field (Name & Type)                                        | Description                                                                                                                                                                                |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **url (`str`)**                                            | The final or actual URL crawled (in case of redirects).                                                                                                                                    |
| **html (`str`)**                                           | Original, unmodified page HTML. Good for debugging or custom processing.                                                                                                                   |
| **fit_html (`Optional[str]`)**                             | Preprocessed HTML optimized for extraction and content filtering.                                                                                                                          |
| **success (`bool`)**                                       | `True` if the crawl completed without major errors, else `False`.                                                                                                                          |
| **cleaned_html (`Optional[str]`)**                         | Sanitized HTML with scripts/styles removed; can exclude tags if configured via `excluded_tags` etc.                                                                                        |
| **media (`Dict[str, List[Dict]]`)**                        | Extracted media info (images, audio, etc.), each with attributes like `src`, `alt`, `score`, etc.                                                                                          |
| **links (`Dict[str, List[Dict]]`)**                        | Extracted link data, split by `internal` and `external`. Each link usually has `href`, `text`, etc.                                                                                        |
| **downloaded_files (`Optional[List[str]]`)**               | If `accept_downloads=True` in `BrowserConfig`, this lists the filepaths of saved downloads.                                                                                                |
| **js_execution_result (`Optional[Dict[str, Any]]`)**       | Results from JavaScript execution during crawling.                                                                                                                                         |
| **screenshot (`Optional[str]`)**                           | Screenshot of the page (base64-encoded) if `screenshot=True`.                                                                                                                              |
| **pdf (`Optional[bytes]`)**                                | PDF of the page if `pdf=True`.                                                                                                                                                             |
| **mhtml (`Optional[str]`)**                                | MHTML snapshot of the page if `capture_mhtml=True`. Contains the full page with all resources.                                                                                             |
| **markdown (`Optional[str or MarkdownGenerationResult]`)** | It holds a `MarkdownGenerationResult`. Over time, this will be consolidated into `markdown`. The generator can provide raw markdown, citations, references, and optionally `fit_markdown`. |
| **extracted_content (`Optional[str]`)**                    | The output of a structured extraction (CSS/LLM-based) stored as JSON string or other text.                                                                                                 |
| **metadata (`Optional[dict]`)**                            | Additional info about the crawl or extracted data.                                                                                                                                         |
| **error_message (`Optional[str]`)**                        | If `success=False`, contains a short description of what went wrong.                                                                                                                       |
| **session_id (`Optional[str]`)**                           | The ID of the session used for multi-page or persistent crawling.                                                                                                                          |
| **response_headers (`Optional[dict]`)**                    | HTTP response headers, if captured.                                                                                                                                                        |
| **status_code (`Optional[int]`)**                          | HTTP status code (e.g., 200 for OK).                                                                                                                                                       |
| **ssl_certificate (`Optional[SSLCertificate]`)**           | SSL certificate info if `fetch_ssl_certificate=True`.                                                                                                                                      |
| **dispatch_result (`Optional[DispatchResult]`)**           | Additional concurrency and resource usage information when crawling URLs in parallel.                                                                                                      |
| **redirected_url (`Optional[str]`)**                       | The URL after any redirects (different from `url` which is the final URL).                                                                                                                 |
| **network_requests (`Optional[List[Dict[str, Any]]]`)**    | List of network requests, responses, and failures captured during the crawl if `capture_network_requests=True`.                                                                            |
| **console_messages (`Optional[List[Dict[str, Any]]]`)**    | List of browser console messages captured during the crawl if `capture_console_messages=True`.                                                                                             |
| **tables (`List[Dict]`)**                                  | Table data extracted from HTML tables with structure `[{headers, rows, caption, summary}]`.                                                                                                |

---

## 2. HTML Variants

### `html`: Raw HTML

Crawl4AI preserves the exact HTML as `result.html`. Useful for:

- Debugging page issues or checking the original content.
- Performing your own specialized parse if needed.

### `cleaned_html`: Sanitized

If you specify any cleanup or exclusion parameters in `CrawlerRunConfig` (like `excluded_tags`, `remove_forms`, etc.), you’ll see the result here:

```
config = CrawlerRunConfig(
    excluded_tags=["form", "header", "footer"],
    keep_data_attributes=False
)
result = await crawler.arun("https://example.com", config=config)
print(result.cleaned_html)  # Freed of forms, header, footer, data-* attributes
Copy
```

---

## 3. Markdown Generation

### 3.1 `markdown`

- **`markdown`**: The current location for detailed markdown output, returning a**`MarkdownGenerationResult`**object.
- **`markdown_v2`**: Deprecated since v0.5.

**`MarkdownGenerationResult`**Fields:
Field | Description
---|---
**raw_markdown** | The basic HTML→Markdown conversion.
**markdown_with_citations** | Markdown including inline citations that reference links at the end.
**references_markdown** | The references/citations themselves (if `citations=True`).
**fit_markdown** | The filtered/“fit” markdown if a content filter was used.
**fit_html** | The filtered HTML that generated `fit_markdown`.

### 3.2 Basic Example with a Markdown Generator

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

config = CrawlerRunConfig(
    markdown_generator=DefaultMarkdownGenerator(
        options={"citations": True, "body_width": 80}  # e.g. pass html2text style options
    )
)
result = await crawler.arun(url="https://example.com", config=config)

md_res = result.markdown  # or eventually 'result.markdown'
print(md_res.raw_markdown[:500])
print(md_res.markdown_with_citations)
print(md_res.references_markdown)
Copy
```

**Note** : If you use a filter like `PruningContentFilter`, you’ll get `fit_markdown` and `fit_html` as well.

---

## 4. Structured Extraction: `extracted_content`

If you run a JSON-based extraction strategy (CSS, XPath, LLM, etc.), the structured data is **not** stored in `markdown`—it’s placed in **`result.extracted_content`**as a JSON string (or sometimes plain text).

### Example: CSS Extraction with `raw://` HTML

```
import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy

async def main():
    schema = {
        "name": "Example Items",
        "baseSelector": "div.item",
        "fields": [
            {"name": "title", "selector": "h2", "type": "text"},
            {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
        ]
    }
    raw_html = "<div class='item'><h2>Item 1</h2><a href='https://example.com/item1'>Link 1</a></div>"

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="raw://" + raw_html,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=JsonCssExtractionStrategy(schema)
            )
        )
        data = json.loads(result.extracted_content)
        print(data)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

Here: - `url="raw://..."` passes the HTML content directly, no network requests.

- The **CSS** extraction strategy populates `result.extracted_content` with the JSON array `[{"title": "...", "link": "..."}]`.

---

## 5. More Fields: Links, Media, Tables and More

### 5.1 `links`

A dictionary, typically with `"internal"` and `"external"` lists. Each entry might have `href`, `text`, `title`, etc. This is automatically captured if you haven’t disabled link extraction.

```
print(result.links["internal"][:3])  # Show first 3 internal links
Copy
```

### 5.2 `media`

Similarly, a dictionary with `"images"`, `"audio"`, `"video"`, etc. Each item could include `src`, `alt`, `score`, and more, if your crawler is set to gather them.

```
images = result.media.get("images", [])
for img in images:
    print("Image URL:", img["src"], "Alt:", img.get("alt"))
Copy
```

### 5.3 `tables`

The `tables` field contains structured data extracted from HTML tables found on the crawled page. Tables are analyzed based on various criteria to determine if they are actual data tables (as opposed to layout tables), including:

- Presence of thead and tbody sections
- Use of th elements for headers
- Column consistency
- Text density
- And other factors

Tables that score above the threshold (default: 7) are extracted and stored in result.tables.

### Accessing Table data:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.w3schools.com/html/html_tables.asp",
            config=CrawlerRunConfig(
                table_score_threshold=7  # Minimum score for table detection
            )
        )

        if result.success and result.tables:
            print(f"Found {len(result.tables)} tables")

            for i, table in enumerate(result.tables):
                print(f"\nTable {i+1}:")
                print(f"Caption: {table.get('caption', 'No caption')}")
                print(f"Headers: {table['headers']}")
                print(f"Rows: {len(table['rows'])}")

                # Print first few rows as example
                for j, row in enumerate(table['rows'][:3]):
                    print(f"  Row {j+1}: {row}")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### Configuring Table Extraction:

You can adjust the sensitivity of the table detection algorithm with:

```
config = CrawlerRunConfig(
    table_score_threshold=5  # Lower value = more tables detected (default: 7)
)
Copy
```

Each extracted table contains:

- `headers`: Column header names
- `rows`: List of rows, each containing cell values
- `caption`: Table caption text (if available)
- `summary`: Table summary attribute (if specified)

### Table Extraction Tips

- Not all HTML tables are extracted - only those detected as "data tables" vs. layout tables.
- Tables with inconsistent cell counts, nested tables, or those used purely for layout may be skipped.
- If you're missing tables, try adjusting the `table_score_threshold` to a lower value (default is 7).

The table detection algorithm scores tables based on features like consistent columns, presence of headers, text density, and more. Tables scoring above the threshold are considered data tables worth extracting.

### 5.4 `screenshot`, `pdf`, and `mhtml`

If you set `screenshot=True`, `pdf=True`, or `capture_mhtml=True` in **`CrawlerRunConfig`**, then:

- `result.screenshot` contains a base64-encoded PNG string.
- `result.pdf` contains raw PDF bytes (you can write them to a file).
- `result.mhtml` contains the MHTML snapshot of the page as a string (you can write it to a .mhtml file).

```
# Save the PDF
with open("page.pdf", "wb") as f:
    f.write(result.pdf)

# Save the MHTML
if result.mhtml:
    with open("page.mhtml", "w", encoding="utf-8") as f:
        f.write(result.mhtml)
Copy
```

The MHTML (MIME HTML) format is particularly useful as it captures the entire web page including all of its resources (CSS, images, scripts, etc.) in a single file, making it perfect for archiving or offline viewing.

### 5.5 `ssl_certificate`

If `fetch_ssl_certificate=True`, `result.ssl_certificate` holds details about the site’s SSL cert, such as issuer, validity dates, etc.

---

## 6. Accessing These Fields

After you run:

```
result = await crawler.arun(url="https://example.com", config=some_config)
Copy
```

Check any field:

```
if result.success:
    print(result.status_code, result.response_headers)
    print("Links found:", len(result.links.get("internal", [])))
    if result.markdown:
        print("Markdown snippet:", result.markdown.raw_markdown[:200])
    if result.extracted_content:
        print("Structured JSON:", result.extracted_content)
else:
    print("Error:", result.error_message)
Copy
```

**Deprecation** : Since v0.5 `result.markdown_v2`, `result.fit_html`,`result.fit_markdown` are deprecated. Use `result.markdown` instead! It holds `MarkdownGenerationResult`, which includes `fit_html` and `fit_markdown` as it's properties.

---

## 7. Next Steps

- **Markdown Generation** : Dive deeper into how to configure `DefaultMarkdownGenerator` and various filters.
- **Content Filtering** : Learn how to use `BM25ContentFilter` and `PruningContentFilter`.
- **Session & Hooks**: If you want to manipulate the page or preserve state across multiple `arun()` calls, see the hooking or session docs.
- **LLM Extraction** : For complex or unstructured content requiring AI-driven parsing, check the LLM-based strategies doc.

**Enjoy** exploring all that `CrawlResult` offers—whether you need raw HTML, sanitized output, markdown, or fully structured data, Crawl4AI has you covered!

- [Fit Markdown with Pruning & BM25](https://docs.crawl4ai.com/core/fit-markdown/#fit-markdown-with-pruning-bm25)
- [1. How “Fit Markdown” Works](https://docs.crawl4ai.com/core/fit-markdown/#1-how-fit-markdown-works)
- [2. PruningContentFilter](https://docs.crawl4ai.com/core/fit-markdown/#2-pruningcontentfilter)
- [3. BM25ContentFilter](https://docs.crawl4ai.com/core/fit-markdown/#3-bm25contentfilter)
- [4. Accessing the “Fit” Output](https://docs.crawl4ai.com/core/fit-markdown/#4-accessing-the-fit-output)
- [5. Code Patterns Recap](https://docs.crawl4ai.com/core/fit-markdown/#5-code-patterns-recap)
- [6. Combining with “word_count_threshold” & Exclusions](https://docs.crawl4ai.com/core/fit-markdown/#6-combining-with-word_count_threshold-exclusions)
- [7. Custom Filters](https://docs.crawl4ai.com/core/fit-markdown/#7-custom-filters)
- [8. Final Thoughts](https://docs.crawl4ai.com/core/fit-markdown/#8-final-thoughts)

# Fit Markdown with Pruning & BM25

**Fit Markdown** is a specialized **filtered** version of your page’s markdown, focusing on the most relevant content. By default, Crawl4AI converts the entire HTML into a broad **raw_markdown**. With fit markdown, we apply a **content filter** algorithm (e.g., **Pruning** or **BM25**) to remove or rank low-value sections—such as repetitive sidebars, shallow text blocks, or irrelevancies—leaving a concise textual “core.”

---

## 1. How “Fit Markdown” Works

### 1.1 The `content_filter`

In **`CrawlerRunConfig`**, you can specify a**`content_filter`**to shape how content is pruned or ranked before final markdown generation. A filter’s logic is applied**before** or **during** the HTML→Markdown process, producing:

- **`result.markdown.raw_markdown`**(unfiltered)
- **`result.markdown.fit_markdown`**(filtered or “fit” version)
- **`result.markdown.fit_html`**(the corresponding HTML snippet that produced`fit_markdown`)

### 1.2 Common Filters

1. **PruningContentFilter** – Scores each node by text density, link density, and tag importance, discarding those below a threshold.
2. **BM25ContentFilter** – Focuses on textual relevance using BM25 ranking, especially useful if you have a specific user query (e.g., “machine learning” or “food nutrition”).

---

## 2. PruningContentFilter

**Pruning** discards less relevant nodes based on **text density, link density, and tag importance**. It’s a heuristic-based approach—if certain sections appear too “thin” or too “spammy,” they’re pruned.

### 2.1 Usage Example

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    # Step 1: Create a pruning filter
    prune_filter = PruningContentFilter(
        # Lower → more content retained, higher → more content pruned
        threshold=0.45,
        # "fixed" or "dynamic"
        threshold_type="dynamic",
        # Ignore nodes with <5 words
        min_word_threshold=5
    )

    # Step 2: Insert it into a Markdown Generator
    md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)

    # Step 3: Pass it to CrawlerRunConfig
    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com",
            config=config
        )

        if result.success:
            # 'fit_markdown' is your pruned content, focusing on "denser" text
            print("Raw Markdown length:", len(result.markdown.raw_markdown))
            print("Fit Markdown length:", len(result.markdown.fit_markdown))
        else:
            print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### 2.2 Key Parameters

- **`min_word_threshold`**(int): If a block has fewer words than this, it’s pruned.
- **`threshold_type`**(str):
- `"fixed"` → each node must exceed `threshold` (0–1).
- `"dynamic"` → node scoring adjusts according to tag type, text/link density, etc.
- **`threshold`**(float, default ~0.48): The base or “anchor” cutoff.

**Algorithmic Factors** :

- **Text density** – Encourages blocks that have a higher ratio of text to overall content.
- **Link density** – Penalizes sections that are mostly links.
- **Tag importance** – e.g., an `<article>` or `<p>` might be more important than a `<div>`.
- **Structural context** – If a node is deeply nested or in a suspected sidebar, it might be deprioritized.

---

## 3. BM25ContentFilter

**BM25** is a classical text ranking algorithm often used in search engines. If you have a **user query** or rely on page metadata to derive a query, BM25 can identify which text chunks best match that query.

### 3.1 Usage Example

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import BM25ContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    # 1) A BM25 filter with a user query
    bm25_filter = BM25ContentFilter(
        user_query="startup fundraising tips",
        # Adjust for stricter or looser results
        bm25_threshold=1.2
    )

    # 2) Insert into a Markdown Generator
    md_generator = DefaultMarkdownGenerator(content_filter=bm25_filter)

    # 3) Pass to crawler config
    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com",
            config=config
        )
        if result.success:
            print("Fit Markdown (BM25 query-based):")
            print(result.markdown.fit_markdown)
        else:
            print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### 3.2 Parameters

- **`user_query`**(str, optional): E.g.`"machine learning"`. If blank, the filter tries to glean a query from page metadata.
- **`bm25_threshold`**(float, default 1.0):
- Higher → fewer chunks but more relevant.
- Lower → more inclusive.

> In more advanced scenarios, you might see parameters like `language`, `case_sensitive`, or `priority_tags` to refine how text is tokenized or weighted.

---

## 4. Accessing the “Fit” Output

After the crawl, your “fit” content is found in **`result.markdown.fit_markdown`**.

```
fit_md = result.markdown.fit_markdown
fit_html = result.markdown.fit_html
Copy
```

If the content filter is **BM25** , you might see additional logic or references in `fit_markdown` that highlight relevant segments. If it’s **Pruning** , the text is typically well-cleaned but not necessarily matched to a query.

---

## 5. Code Patterns Recap

### 5.1 Pruning

```
prune_filter = PruningContentFilter(
    threshold=0.5,
    threshold_type="fixed",
    min_word_threshold=10
)
md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)
config = CrawlerRunConfig(markdown_generator=md_generator)
Copy
```

### 5.2 BM25

```
bm25_filter = BM25ContentFilter(
    user_query="health benefits fruit",
    bm25_threshold=1.2
)
md_generator = DefaultMarkdownGenerator(content_filter=bm25_filter)
config = CrawlerRunConfig(markdown_generator=md_generator)
Copy
```

---

## 6. Combining with “word_count_threshold” & Exclusions

Remember you can also specify:

```
config = CrawlerRunConfig(
    word_count_threshold=10,
    excluded_tags=["nav", "footer", "header"],
    exclude_external_links=True,
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.5)
    )
)
Copy
```

Thus, **multi-level** filtering occurs:

1. The crawler’s `excluded_tags` are removed from the HTML first.
2. The content filter (Pruning, BM25, or custom) prunes or ranks the remaining text blocks.
3. The final “fit” content is generated in `result.markdown.fit_markdown`.

---

## 7. Custom Filters

If you need a different approach (like a specialized ML model or site-specific heuristics), you can create a new class inheriting from `RelevantContentFilter` and implement `filter_content(html)`. Then inject it into your **markdown generator** :

```
from crawl4ai.content_filter_strategy import RelevantContentFilter

class MyCustomFilter(RelevantContentFilter):
    def filter_content(self, html, min_word_threshold=None):
        # parse HTML, implement custom logic
        return [block for block in ... if ... some condition...]
Copy
```

**Steps** :

1. Subclass `RelevantContentFilter`.
2. Implement `filter_content(...)`.
3. Use it in your `DefaultMarkdownGenerator(content_filter=MyCustomFilter(...))`.

---

## 8. Final Thoughts

**Fit Markdown** is a crucial feature for:

- **Summaries** : Quickly get the important text from a cluttered page.
- **Search** : Combine with **BM25** to produce content relevant to a query.
- **AI Pipelines** : Filter out boilerplate so LLM-based extraction or summarization runs on denser text.

**Key Points** : - **PruningContentFilter** : Great if you just want the “meatiest” text without a user query.

- **BM25ContentFilter** : Perfect for query-based extraction or searching.
- Combine with **`excluded_tags`,`exclude_external_links` , `word_count_threshold`** to refine your final “fit” text.
- Fit markdown ends up in **`result.markdown.fit_markdown`**; eventually**`result.markdown.fit_markdown`**in future versions.
  With these tools, you can **zero in** on the text that truly matters, ignoring spammy or boilerplate content, and produce a concise, relevant “fit markdown” for your AI or data pipelines. Happy pruning and searching!
  - Last Updated: 2025-01-01

---

- [Crawl4AI Blog](https://docs.crawl4ai.com/blog/#crawl4ai-blog)
- [Featured Articles](https://docs.crawl4ai.com/blog/#featured-articles)
- [Latest Release](https://docs.crawl4ai.com/blog/#latest-release)
- [Project History](https://docs.crawl4ai.com/blog/#project-history)
- [Stay Updated](https://docs.crawl4ai.com/blog/#stay-updated)

# Crawl4AI Blog

Welcome to the Crawl4AI blog! Here you'll find detailed release notes, technical insights, and updates about the project. Whether you're looking for the latest improvements or want to dive deep into web crawling techniques, this is the place.

## Featured Articles

### [When to Stop Crawling: The Art of Knowing "Enough"](https://docs.crawl4ai.com/blog/articles/adaptive-crawling-revolution/)

_January 29, 2025_
Traditional crawlers are like tourists with unlimited time—they'll visit every street, every alley, every dead end. But what if your crawler could think like a researcher with a deadline? Discover how Adaptive Crawling revolutionizes web scraping by knowing when to stop. Learn about the three-layer intelligence system that evaluates coverage, consistency, and saturation to build focused knowledge bases instead of endless page collections.
[Read the full article →](https://docs.crawl4ai.com/blog/articles/adaptive-crawling-revolution/)

### [The LLM Context Protocol: Why Your AI Assistant Needs Memory, Reasoning, and Examples](https://docs.crawl4ai.com/blog/articles/llm-context-revolution/)

_January 24, 2025_
Ever wondered why your AI coding assistant struggles with your library despite comprehensive documentation? This article introduces the three-dimensional context protocol that transforms how AI understands code. Learn why memory, reasoning, and examples together create wisdom—not just information.
[Read the full article →](https://docs.crawl4ai.com/blog/articles/llm-context-revolution/)

## Latest Release

### [Crawl4AI v0.7.4 – The Intelligent Table Extraction & Performance Update](https://docs.crawl4ai.com/blog/release-v0.7.4.md)

_August 17, 2025_
Crawl4AI v0.7.4 introduces revolutionary LLM-powered table extraction with intelligent chunking, performance improvements for concurrent crawling, enhanced browser management, and critical stability fixes that make Crawl4AI more robust for production workloads.
Key highlights: - **🚀 LLMTableExtraction** : Revolutionary table extraction with intelligent chunking for massive tables - **⚡ Dispatcher Bug Fix** : Fixed sequential processing issue in arun_many for fast-completing tasks - **🧹 Memory Management Refactor** : Streamlined memory utilities and better resource management - **🔧 Browser Manager Fixes** : Resolved race conditions in concurrent page creation - **🔗 Advanced URL Processing** : Better handling of raw URLs and base tag link resolution
[Read full release notes →](https://docs.crawl4ai.com/blog/release-v0.7.4.md)

---

## Project History

Curious about how Crawl4AI has evolved? Check out our [complete changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md) for a detailed history of all versions and updates.

## Stay Updated

- Star us on [GitHub](https://github.com/unclecode/crawl4ai)
- Follow [@unclecode](https://twitter.com/unclecode) on Twitter
- Join our community discussions on GitHub

#### On this page

- [Featured Articles](https://docs.crawl4ai.com/blog/#featured-articles)
- [When to Stop Crawling: The Art of Knowing "Enough"](https://docs.crawl4ai.com/blog/#when-to-stop-crawling-the-art-of-knowing-enough)
- [The LLM Context Protocol: Why Your AI Assistant Needs Memory, Reasoning, and Examples](https://docs.crawl4ai.com/blog/#the-llm-context-protocol-why-your-ai-assistant-needs-memory-reasoning-and-examples)
- [Latest Release](https://docs.crawl4ai.com/blog/#latest-release)
- [Crawl4AI v0.7.4 – The Intelligent Table Extraction & Performance Update](https://docs.crawl4ai.com/blog/#crawl4ai-v074-the-intelligent-table-extraction-performance-update)
- [Project History](https://docs.crawl4ai.com/blog/#project-history)
- [Stay Updated](https://docs.crawl4ai.com/blog/#stay-updated)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/local-files

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/local-files/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - Local Files & Raw HTML
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Prefix-Based Input Handling in Crawl4AI](https://docs.crawl4ai.com/core/local-files/#prefix-based-input-handling-in-crawl4ai)
- [Crawling a Web URL](https://docs.crawl4ai.com/core/local-files/#crawling-a-web-url)
- [Crawling a Local HTML File](https://docs.crawl4ai.com/core/local-files/#crawling-a-local-html-file)
- [Crawling Raw HTML Content](https://docs.crawl4ai.com/core/local-files/#crawling-raw-html-content)
- [Complete Example](https://docs.crawl4ai.com/core/local-files/#complete-example)
- [Conclusion](https://docs.crawl4ai.com/core/local-files/#conclusion)

# Prefix-Based Input Handling in Crawl4AI

This guide will walk you through using the Crawl4AI library to crawl web pages, local HTML files, and raw HTML strings. We'll demonstrate these capabilities using a Wikipedia page as an example.

## Crawling a Web URL

To crawl a live web page, provide the URL starting with `http://` or `https://`, using a `CrawlerRunConfig` object:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

async def crawl_web():
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/apple",
            config=config
        )
        if result.success:
            print("Markdown Content:")
            print(result.markdown)
        else:
            print(f"Failed to crawl: {result.error_message}")

asyncio.run(crawl_web())
Copy
```

## Crawling a Local HTML File

To crawl a local HTML file, prefix the file path with `file://`.

```
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

async def crawl_local_file():
    local_file_path = "/path/to/apple.html"  # Replace with your file path
    file_url = f"file://{local_file_path}"
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=file_url, config=config)
        if result.success:
            print("Markdown Content from Local File:")
            print(result.markdown)
        else:
            print(f"Failed to crawl local file: {result.error_message}")

asyncio.run(crawl_local_file())
Copy
```

## Crawling Raw HTML Content

To crawl raw HTML content, prefix the HTML string with `raw:`.

```
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import CrawlerRunConfig

async def crawl_raw_html():
    raw_html = "<html><body><h1>Hello, World!</h1></body></html>"
    raw_html_url = f"raw:{raw_html}"
    config = CrawlerRunConfig(bypass_cache=True)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=raw_html_url, config=config)
        if result.success:
            print("Markdown Content from Raw HTML:")
            print(result.markdown)
        else:
            print(f"Failed to crawl raw HTML: {result.error_message}")

asyncio.run(crawl_raw_html())
Copy
```

---

# Complete Example

Below is a comprehensive script that:

1. Crawls the Wikipedia page for "Apple."
2. Saves the HTML content to a local file (`apple.html`).
3. Crawls the local HTML file and verifies the markdown length matches the original crawl.
4. Crawls the raw HTML content from the saved file and verifies consistency.

```
import os
import sys
import asyncio
from pathlib import Path
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

async def main():
    wikipedia_url = "https://en.wikipedia.org/wiki/apple"
    script_dir = Path(__file__).parent
    html_file_path = script_dir / "apple.html"

    async with AsyncWebCrawler() as crawler:
        # Step 1: Crawl the Web URL
        print("\n=== Step 1: Crawling the Wikipedia URL ===")
        web_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        result = await crawler.arun(url=wikipedia_url, config=web_config)

        if not result.success:
            print(f"Failed to crawl {wikipedia_url}: {result.error_message}")
            return

        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(result.html)
        web_crawl_length = len(result.markdown)
        print(f"Length of markdown from web crawl: {web_crawl_length}\n")

        # Step 2: Crawl from the Local HTML File
        print("=== Step 2: Crawling from the Local HTML File ===")
        file_url = f"file://{html_file_path.resolve()}"
        file_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        local_result = await crawler.arun(url=file_url, config=file_config)

        if not local_result.success:
            print(f"Failed to crawl local file {file_url}: {local_result.error_message}")
            return

        local_crawl_length = len(local_result.markdown)
        assert web_crawl_length == local_crawl_length, "Markdown length mismatch"
        print("✅ Markdown length matches between web and local file crawl.\n")

        # Step 3: Crawl Using Raw HTML Content
        print("=== Step 3: Crawling Using Raw HTML Content ===")
        with open(html_file_path, 'r', encoding='utf-8') as f:
            raw_html_content = f.read()
        raw_html_url = f"raw:{raw_html_content}"
        raw_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        raw_result = await crawler.arun(url=raw_html_url, config=raw_config)

        if not raw_result.success:
            print(f"Failed to crawl raw HTML content: {raw_result.error_message}")
            return

        raw_crawl_length = len(raw_result.markdown)
        assert web_crawl_length == raw_crawl_length, "Markdown length mismatch"
        print("✅ Markdown length matches between web and raw HTML crawl.\n")

        print("All tests passed successfully!")
    if html_file_path.exists():
        os.remove(html_file_path)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

# Conclusion

With the unified `url` parameter and prefix-based handling in **Crawl4AI** , you can seamlessly handle web URLs, local HTML files, and raw HTML content. Use `CrawlerRunConfig` for flexible and consistent configuration in all scenarios.

# Crawl4AI CLI Guide

## Table of Contents

- [Installation](https://docs.crawl4ai.com/core/cli/#installation)
- [Basic Usage](https://docs.crawl4ai.com/core/cli/#basic-usage)
- [Configuration](https://docs.crawl4ai.com/core/cli/#configuration)
- [Browser Configuration](https://docs.crawl4ai.com/core/cli/#browser-configuration)
- [Crawler Configuration](https://docs.crawl4ai.com/core/cli/#crawler-configuration)
- [Extraction Configuration](https://docs.crawl4ai.com/core/cli/#extraction-configuration)
- [Content Filtering](https://docs.crawl4ai.com/core/cli/#content-filtering)
- [Advanced Features](https://docs.crawl4ai.com/core/cli/#advanced-features)
- [LLM Q&A](https://docs.crawl4ai.com/core/cli/#llm-qa)
- [Structured Data Extraction](https://docs.crawl4ai.com/core/cli/#structured-data-extraction)
- [Content Filtering](https://docs.crawl4ai.com/core/cli/#content-filtering-1)
- [Output Formats](https://docs.crawl4ai.com/core/cli/#output-formats)
- [Examples](https://docs.crawl4ai.com/core/cli/#examples)
- [Configuration Reference](https://docs.crawl4ai.com/core/cli/#configuration-reference)
- [Best Practices & Tips](https://docs.crawl4ai.com/core/cli/#best-practices--tips)

## Installation

The Crawl4AI CLI will be installed automatically when you install the library.

## Basic Usage

The Crawl4AI CLI (`crwl`) provides a simple interface to the Crawl4AI library:

```
# Basic crawling
crwl https://example.com

# Get markdown output
crwl https://example.com -o markdown

# Verbose JSON output with cache bypass
crwl https://example.com -o json -v --bypass-cache

# See usage examples
crwl --example
Copy
```

## Quick Example of Advanced Usage

If you clone the repository and run the following command, you will receive the content of the page in JSON format according to a JSON-CSS schema:

```
crwl "https://www.infoq.com/ai-ml-data-eng/" -e docs/examples/cli/extract_css.yml -s docs/examples/cli/css_schema.json -o json;
Copy
```

## Configuration

### Browser Configuration

Browser settings can be configured via YAML file or command line parameters:

```
# browser.yml
headless: true
viewport_width: 1280
user_agent_mode: "random"
verbose: true
ignore_https_errors: true
Copy
```

```
# Using config file
crwl https://example.com -B browser.yml

# Using direct parameters
crwl https://example.com -b "headless=true,viewport_width=1280,user_agent_mode=random"
Copy
```

### Crawler Configuration

Control crawling behavior:

```
# crawler.yml
cache_mode: "bypass"
wait_until: "networkidle"
page_timeout: 30000
delay_before_return_html: 0.5
word_count_threshold: 100
scan_full_page: true
scroll_delay: 0.3
process_iframes: false
remove_overlay_elements: true
magic: true
verbose: true
Copy
```

```
# Using config file
crwl https://example.com -C crawler.yml

# Using direct parameters
crwl https://example.com -c "css_selector=#main,delay_before_return_html=2,scan_full_page=true"
Copy
```

### Extraction Configuration

Two types of extraction are supported:

1. CSS/XPath-based extraction:

```
# extract_css.yml
type: "json-css"
params:
  verbose: true
Copy
```

```
// css_schema.json
{
  "name": "ArticleExtractor",
  "baseSelector": ".article",
  "fields": [
    {
      "name": "title",
      "selector": "h1.title",
      "type": "text"
    },
    {
      "name": "link",
      "selector": "a.read-more",
      "type": "attribute",
      "attribute": "href"
    }
  ]
}
Copy
```

1. LLM-based extraction:

```
# extract_llm.yml
type: "llm"
provider: "openai/gpt-4"
instruction: "Extract all articles with their titles and links"
api_token: "your-token"
params:
  temperature: 0.3
  max_tokens: 1000
Copy
```

```
// llm_schema.json
{
  "title": "Article",
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "The title of the article"
    },
    "link": {
      "type": "string",
      "description": "URL to the full article"
    }
  }
}
Copy
```

## Advanced Features

### LLM Q&A

Ask questions about crawled content:

```
# Simple question
crwl https://example.com -q "What is the main topic discussed?"

# View content then ask questions
crwl https://example.com -o markdown  # See content first
crwl https://example.com -q "Summarize the key points"
crwl https://example.com -q "What are the conclusions?"

# Combined with advanced crawling
crwl https://example.com \
    -B browser.yml \
    -c "css_selector=article,scan_full_page=true" \
    -q "What are the pros and cons mentioned?"
Copy
```

First-time setup: - Prompts for LLM provider and API token - Saves configuration in `~/.crawl4ai/global.yml` - Supports various providers (openai/gpt-4, anthropic/claude-3-sonnet, etc.) - For case of `ollama` you do not need to provide API token. - See [LiteLLM Providers](https://docs.litellm.ai/docs/providers) for full list

### Structured Data Extraction

Extract structured data using CSS selectors:

```
crwl https://example.com \
    -e extract_css.yml \
    -s css_schema.json \
    -o json
Copy
```

Or using LLM-based extraction:

```
crwl https://example.com \
    -e extract_llm.yml \
    -s llm_schema.json \
    -o json
Copy
```

### Content Filtering

Filter content for relevance:

```
# filter_bm25.yml
type: "bm25"
query: "target content"
threshold: 1.0

# filter_pruning.yml
type: "pruning"
query: "focus topic"
threshold: 0.48
Copy
```

```
crwl https://example.com -f filter_bm25.yml -o markdown-fit
Copy
```

## Output Formats

- `all` - Full crawl result including metadata
- `json` - Extracted structured data (when using extraction)
- `markdown` / `md` - Raw markdown output
- `markdown-fit` / `md-fit` - Filtered markdown for better readability

## Complete Examples

1. Basic Extraction:

```
crwl https://example.com \
    -B browser.yml \
    -C crawler.yml \
    -o json
Copy
```

2. Structured Data Extraction:

```
crwl https://example.com \
    -e extract_css.yml \
    -s css_schema.json \
    -o json \
    -v
Copy
```

3. LLM Extraction with Filtering:

```
crwl https://example.com \
    -B browser.yml \
    -e extract_llm.yml \
    -s llm_schema.json \
    -f filter_bm25.yml \
    -o json
Copy
```

4. Interactive Q&A:

```
# First crawl and view
crwl https://example.com -o markdown

# Then ask questions
crwl https://example.com -q "What are the main points?"
crwl https://example.com -q "Summarize the conclusions"
Copy
```

## Best Practices & Tips

1. **Configuration Management** :
2. Keep common configurations in YAML files
3. Use CLI parameters for quick overrides
4. Store sensitive data (API tokens) in `~/.crawl4ai/global.yml`
5. **Performance Optimization** :
6. Use `--bypass-cache` for fresh content
7. Enable `scan_full_page` for infinite scroll pages
8. Adjust `delay_before_return_html` for dynamic content
9. **Content Extraction** :
10. Use CSS extraction for structured content
11. Use LLM extraction for unstructured content
12. Combine with filters for focused results
13. **Q &A Workflow**:
14. View content first with `-o markdown`
15. Ask specific questions
16. Use broader context with appropriate selectors

## Recap

The Crawl4AI CLI provides: - Flexible configuration via files and parameters - Multiple extraction strategies (CSS, XPath, LLM) - Content filtering and optimization - Interactive Q&A capabilities - Various output formats

# Markdown Generation Basics

One of Crawl4AI’s core features is generating **clean, structured markdown** from web pages. Originally built to solve the problem of extracting only the “actual” content and discarding boilerplate or noise, Crawl4AI’s markdown system remains one of its biggest draws for AI workflows.
In this tutorial, you’ll learn:

1. How to configure the **Default Markdown Generator**
2. How **content filters** (BM25 or Pruning) help you refine markdown and discard junk
3. The difference between raw markdown (`result.markdown`) and filtered markdown (`fit_markdown`)

> **Prerequisites**
>
> - You’ve completed or read [AsyncWebCrawler Basics](https://docs.crawl4ai.com/core/simple-crawling/) to understand how to run a simple crawl.
> - You know how to configure `CrawlerRunConfig`.

---

## 1. Quick Example

Here’s a minimal code snippet that uses the **DefaultMarkdownGenerator** with no additional filtering:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator()
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com", config=config)

        if result.success:
            print("Raw Markdown Output:\n")
            print(result.markdown)  # The unfiltered markdown from the page
        else:
            print("Crawl failed:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**What’s happening?**

- `CrawlerRunConfig( markdown_generator = DefaultMarkdownGenerator() )` instructs Crawl4AI to convert the final HTML into markdown at the end of each crawl.
- The resulting markdown is accessible via `result.markdown`.

---

## 2. How Markdown Generation Works

### 2.1 HTML-to-Text Conversion (Forked & Modified)

Under the hood, **DefaultMarkdownGenerator** uses a specialized HTML-to-text approach that:

- Preserves headings, code blocks, bullet points, etc.
- Removes extraneous tags (scripts, styles) that don’t add meaningful content.
- Can optionally generate references for links or skip them altogether.

A set of **options** (passed as a dict) allows you to customize precisely how HTML converts to markdown. These map to standard html2text-like configuration plus your own enhancements (e.g., ignoring internal links, preserving certain tags verbatim, or adjusting line widths).

### 2.2 Link Citations & References

By default, the generator can convert `<a href="...">` elements into `[text][1]` citations, then place the actual links at the bottom of the document. This is handy for research workflows that demand references in a structured manner.

### 2.3 Optional Content Filters

Before or after the HTML-to-Markdown step, you can apply a **content filter** (like BM25 or Pruning) to reduce noise and produce a “fit_markdown”—a heavily pruned version focusing on the page’s main text. We’ll cover these filters shortly.

---

## 3. Configuring the Default Markdown Generator

You can tweak the output by passing an `options` dict to `DefaultMarkdownGenerator`. For example:

```
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Example: ignore all links, don't escape HTML, and wrap text at 80 characters
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": True,
            "escape_html": False,
            "body_width": 80
        }
    )

    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com/docs", config=config)
        if result.success:
            print("Markdown:\n", result.markdown[:500])  # Just a snippet
        else:
            print("Crawl failed:", result.error_message)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
Copy
```

Some commonly used `options`:

- **`ignore_links`**(bool): Whether to remove all hyperlinks in the final markdown.
- **`ignore_images`**(bool): Remove all`![image]()` references.
- **`escape_html`**(bool): Turn HTML entities into text (default is often`True`).
- **`body_width`**(int): Wrap text at N characters.`0` or `None` means no wrapping.
- **`skip_internal_links`**(bool): If`True` , omit `#localAnchors` or internal links referencing the same page.
- **`include_sup_sub`**(bool): Attempt to handle`<sup>` / `<sub>` in a more readable way.

## 4. Selecting the HTML Source for Markdown Generation

The `content_source` parameter allows you to control which HTML content is used as input for markdown generation. This gives you flexibility in how the HTML is processed before conversion to markdown.

```
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Option 1: Use the raw HTML directly from the webpage (before any processing)
    raw_md_generator = DefaultMarkdownGenerator(
        content_source="raw_html",
        options={"ignore_links": True}
    )

    # Option 2: Use the cleaned HTML (after scraping strategy processing - default)
    cleaned_md_generator = DefaultMarkdownGenerator(
        content_source="cleaned_html",  # This is the default
        options={"ignore_links": True}
    )

    # Option 3: Use preprocessed HTML optimized for schema extraction
    fit_md_generator = DefaultMarkdownGenerator(
        content_source="fit_html",
        options={"ignore_links": True}
    )

    # Use one of the generators in your crawler config
    config = CrawlerRunConfig(
        markdown_generator=raw_md_generator  # Try each of the generators
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com", config=config)
        if result.success:
            print("Markdown:\n", result.markdown.raw_markdown[:500])
        else:
            print("Crawl failed:", result.error_message)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
Copy
```

### HTML Source Options

- **`"cleaned_html"`**(default): Uses the HTML after it has been processed by the scraping strategy. This HTML is typically cleaner and more focused on content, with some boilerplate removed.
- **`"raw_html"`**: Uses the original HTML directly from the webpage, before any cleaning or processing. This preserves more of the original content, but may include navigation bars, ads, footers, and other elements that might not be relevant to the main content.
- **`"fit_html"`**: Uses HTML preprocessed for schema extraction. This HTML is optimized for structured data extraction and may have certain elements simplified or removed.

### When to Use Each Option

- Use **`"cleaned_html"`**(default) for most cases where you want a balance of content preservation and noise removal.
- Use **`"raw_html"`**when you need to preserve all original content, or when the cleaning process is removing content you actually want to keep.
- Use **`"fit_html"`**when working with structured data or when you need HTML that's optimized for schema extraction.

---

## 5. Content Filters

**Content filters** selectively remove or rank sections of text before turning them into Markdown. This is especially helpful if your page has ads, nav bars, or other clutter you don’t want.

### 5.1 BM25ContentFilter

If you have a **search query** , BM25 is a good choice:

```
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import BM25ContentFilter
from crawl4ai import CrawlerRunConfig

bm25_filter = BM25ContentFilter(
    user_query="machine learning",
    bm25_threshold=1.2,
    language="english"
)

md_generator = DefaultMarkdownGenerator(
    content_filter=bm25_filter,
    options={"ignore_links": True}
)

config = CrawlerRunConfig(markdown_generator=md_generator)
Copy
```

- **`user_query`**: The term you want to focus on. BM25 tries to keep only content blocks relevant to that query.
- **`bm25_threshold`**: Raise it to keep fewer blocks; lower it to keep more.
- **`use_stemming`**_(default`True`)_: Whether to apply stemming to the query and content.
- **`language (str)`**: Language for stemming (default: 'english').

**No query provided?** BM25 tries to glean a context from page metadata, or you can simply treat it as a scorched-earth approach that discards text with low generic score. Realistically, you want to supply a query for best results.

### 5.2 PruningContentFilter

If you **don’t** have a specific query, or if you just want a robust “junk remover,” use `PruningContentFilter`. It analyzes text density, link density, HTML structure, and known patterns (like “nav,” “footer”) to systematically prune extraneous or repetitive sections.

```
from crawl4ai.content_filter_strategy import PruningContentFilter

prune_filter = PruningContentFilter(
    threshold=0.5,
    threshold_type="fixed",  # or "dynamic"
    min_word_threshold=50
)
Copy
```

- **`threshold`**: Score boundary. Blocks below this score get removed.
- **`threshold_type`**:
  - `"fixed"`: Straight comparison (`score >= threshold` keeps the block).
  - `"dynamic"`: The filter adjusts threshold in a data-driven manner.
- **`min_word_threshold`**: Discard blocks under N words as likely too short or unhelpful.

**When to Use PruningContentFilter**

- You want a broad cleanup without a user query.
- The page has lots of repeated sidebars, footers, or disclaimers that hamper text extraction.

### 5.3 LLMContentFilter

For intelligent content filtering and high-quality markdown generation, you can use the **LLMContentFilter**. This filter leverages LLMs to generate relevant markdown while preserving the original content's meaning and structure:

```
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMConfig, DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import LLMContentFilter

async def main():
    # Initialize LLM filter with specific instruction
    filter = LLMContentFilter(
        llm_config = LLMConfig(provider="openai/gpt-4o",api_token="your-api-token"), #or use environment variable
        instruction="""
        Focus on extracting the core educational content.
        Include:
        - Key concepts and explanations
        - Important code examples
        - Essential technical details
        Exclude:
        - Navigation elements
        - Sidebars
        - Footer content
        Format the output as clean markdown with proper code blocks and headers.
        """,
        chunk_token_threshold=4096,  # Adjust based on your needs
        verbose=True
    )
    md_generator = DefaultMarkdownGenerator(
        content_filter=filter,
        options={"ignore_links": True}
    )
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com", config=config)
        print(result.markdown.fit_markdown)  # Filtered markdown content
Copy
```

**Key Features:** - **Intelligent Filtering** : Uses LLMs to understand and extract relevant content while maintaining context - **Customizable Instructions** : Tailor the filtering process with specific instructions - **Chunk Processing** : Handles large documents by processing them in chunks (controlled by `chunk_token_threshold`) - **Parallel Processing** : For better performance, use smaller `chunk_token_threshold` (e.g., 2048 or 4096) to enable parallel processing of content chunks
**Two Common Use Cases:**

1. **Exact Content Preservation** :

```
filter = LLMContentFilter(
    instruction="""
    Extract the main educational content while preserving its original wording and substance completely.
    1. Maintain the exact language and terminology
    2. Keep all technical explanations and examples intact
    3. Preserve the original flow and structure
    4. Remove only clearly irrelevant elements like navigation menus and ads
    """,
    chunk_token_threshold=4096
)
Copy
```

2. **Focused Content Extraction** :

```
filter = LLMContentFilter(
    instruction="""
    Focus on extracting specific types of content:
    - Technical documentation
    - Code examples
    - API references
    Reformat the content into clear, well-structured markdown
    """,
    chunk_token_threshold=4096
)
Copy
```

> **Performance Tip** : Set a smaller `chunk_token_threshold` (e.g., 2048 or 4096) to enable parallel processing of content chunks. The default value is infinity, which processes the entire content as a single chunk.

---

## 6. Using Fit Markdown

When a content filter is active, the library produces two forms of markdown inside `result.markdown`:

1. **`raw_markdown`**: The full unfiltered markdown.
2. **`fit_markdown`**: A “fit” version where the filter has removed or trimmed noisy segments.

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

async def main():
    config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.6),
            options={"ignore_links": True}
        )
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://news.example.com/tech", config=config)
        if result.success:
            print("Raw markdown:\n", result.markdown)

            # If a filter is used, we also have .fit_markdown:
            md_object = result.markdown  # or your equivalent
            print("Filtered markdown:\n", md_object.fit_markdown)
        else:
            print("Crawl failed:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

## 7. The `MarkdownGenerationResult` Object

If your library stores detailed markdown output in an object like `MarkdownGenerationResult`, you’ll see fields such as:

- **`raw_markdown`**: The direct HTML-to-markdown transformation (no filtering).
- **`markdown_with_citations`**: A version that moves links to reference-style footnotes.
- **`references_markdown`**: A separate string or section containing the gathered references.
- **`fit_markdown`**: The filtered markdown if you used a content filter.
- **`fit_html`**: The corresponding HTML snippet used to generate`fit_markdown` (helpful for debugging or advanced usage).

**Example** :

```
md_obj = result.markdown  # your library’s naming may vary
print("RAW:\n", md_obj.raw_markdown)
print("CITED:\n", md_obj.markdown_with_citations)
print("REFERENCES:\n", md_obj.references_markdown)
print("FIT:\n", md_obj.fit_markdown)
Copy
```

**Why Does This Matter?**

- You can supply `raw_markdown` to an LLM if you want the entire text.
- Or feed `fit_markdown` into a vector database to reduce token usage.
- `references_markdown` can help you keep track of link provenance.

---

Below is a **revised section** under “Combining Filters (BM25 + Pruning)” that demonstrates how you can run **two** passes of content filtering without re-crawling, by taking the HTML (or text) from a first pass and feeding it into the second filter. It uses real code patterns from the snippet you provided for **BM25ContentFilter** , which directly accepts **HTML** strings (and can also handle plain text with minimal adaptation).

---

## 8. Combining Filters (BM25 + Pruning) in Two Passes

You might want to **prune out** noisy boilerplate first (with `PruningContentFilter`), and then **rank what’s left** against a user query (with `BM25ContentFilter`). You don’t have to crawl the page twice. Instead:

1. **First pass** : Apply `PruningContentFilter` directly to the raw HTML from `result.html` (the crawler’s downloaded HTML).
2. **Second pass** : Take the pruned HTML (or text) from step 1, and feed it into `BM25ContentFilter`, focusing on a user query.

### Two-Pass Example

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter, BM25ContentFilter
from bs4 import BeautifulSoup

async def main():
    # 1. Crawl with minimal or no markdown generator, just get raw HTML
    config = CrawlerRunConfig(
        # If you only want raw HTML, you can skip passing a markdown_generator
        # or provide one but focus on .html in this example
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com/tech-article", config=config)

        if not result.success or not result.html:
            print("Crawl failed or no HTML content.")
            return

        raw_html = result.html

        # 2. First pass: PruningContentFilter on raw HTML
        pruning_filter = PruningContentFilter(threshold=0.5, min_word_threshold=50)

        # filter_content returns a list of "text chunks" or cleaned HTML sections
        pruned_chunks = pruning_filter.filter_content(raw_html)
        # This list is basically pruned content blocks, presumably in HTML or text form

        # For demonstration, let's combine these chunks back into a single HTML-like string
        # or you could do further processing. It's up to your pipeline design.
        pruned_html = "\n".join(pruned_chunks)

        # 3. Second pass: BM25ContentFilter with a user query
        bm25_filter = BM25ContentFilter(
            user_query="machine learning",
            bm25_threshold=1.2,
            language="english"
        )

        # returns a list of text chunks
        bm25_chunks = bm25_filter.filter_content(pruned_html)

        if not bm25_chunks:
            print("Nothing matched the BM25 query after pruning.")
            return

        # 4. Combine or display final results
        final_text = "\n---\n".join(bm25_chunks)

        print("==== PRUNED OUTPUT (first pass) ====")
        print(pruned_html[:500], "... (truncated)")  # preview

        print("\n==== BM25 OUTPUT (second pass) ====")
        print(final_text[:500], "... (truncated)")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### What’s Happening?

1. **Raw HTML** : We crawl once and store the raw HTML in `result.html`.
2. **PruningContentFilter** : Takes HTML + optional parameters. It extracts blocks of text or partial HTML, removing headings/sections deemed “noise.” It returns a **list of text chunks**.
3. **Combine or Transform** : We join these pruned chunks back into a single HTML-like string. (Alternatively, you could store them in a list for further logic—whatever suits your pipeline.)
4. **BM25ContentFilter** : We feed the pruned string into `BM25ContentFilter` with a user query. This second pass further narrows the content to chunks relevant to “machine learning.”
   **No Re-Crawling** : We used `raw_html` from the first pass, so there’s no need to run `arun()` again—**no second network request**.

### Tips & Variations

- **Plain Text vs. HTML** : If your pruned output is mostly text, BM25 can still handle it; just keep in mind it expects a valid string input. If you supply partial HTML (like `"<p>some text</p>"`), it will parse it as HTML.
- **Chaining in a Single Pipeline** : If your code supports it, you can chain multiple filters automatically. Otherwise, manual two-pass filtering (as shown) is straightforward.
- **Adjust Thresholds** : If you see too much or too little text in step one, tweak `threshold=0.5` or `min_word_threshold=50`. Similarly, `bm25_threshold=1.2` can be raised/lowered for more or fewer chunks in step two.

### One-Pass Combination?

If your codebase or pipeline design allows applying multiple filters in one pass, you could do so. But often it’s simpler—and more transparent—to run them sequentially, analyzing each step’s result.
**Bottom Line** : By **manually chaining** your filtering logic in two passes, you get powerful incremental control over the final content. First, remove “global” clutter with Pruning, then refine further with BM25-based query relevance—without incurring a second network crawl.

---

## 9. Common Pitfalls & Tips

1. **No Markdown Output?**

- Make sure the crawler actually retrieved HTML. If the site is heavily JS-based, you may need to enable dynamic rendering or wait for elements.
- Check if your content filter is too aggressive. Lower thresholds or disable the filter to see if content reappears.

2. **Performance Considerations**

- Very large pages with multiple filters can be slower. Consider `cache_mode` to avoid re-downloading.
- If your final use case is LLM ingestion, consider summarizing further or chunking big texts.

3. **Take Advantage of`fit_markdown`**

- Great for RAG pipelines, semantic search, or any scenario where extraneous boilerplate is unwanted.
- Still verify the textual quality—some sites have crucial data in footers or sidebars.

4. **Adjusting`html2text` Options**

- If you see lots of raw HTML slipping into the text, turn on `escape_html`.
- If code blocks look messy, experiment with `mark_code` or `handle_code_in_pre`.

---

## 10. Summary & Next Steps

In this **Markdown Generation Basics** tutorial, you learned to:

- Configure the **DefaultMarkdownGenerator** with HTML-to-text options.
- Select different HTML sources using the `content_source` parameter.
- Use **BM25ContentFilter** for query-specific extraction or **PruningContentFilter** for general noise removal.
- Distinguish between raw and filtered markdown (`fit_markdown`).
- Leverage the `MarkdownGenerationResult` object to handle different forms of output (citations, references, etc.).

Now you can produce high-quality Markdown from any website, focusing on exactly the content you need—an essential step for powering AI models, summarization pipelines, or knowledge-base queries.
**Last Updated** : 2025-01-01
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/markdown-generation/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/markdown-generation/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/markdown-generation/)

ESC to close

#### On this page

- [1. Quick Example](https://docs.crawl4ai.com/core/markdown-generation/#1-quick-example)
- [2. How Markdown Generation Works](https://docs.crawl4ai.com/core/markdown-generation/#2-how-markdown-generation-works)
- [2.1 HTML-to-Text Conversion (Forked & Modified)](https://docs.crawl4ai.com/core/markdown-generation/#21-html-to-text-conversion-forked-modified)
- [2.2 Link Citations & References](https://docs.crawl4ai.com/core/markdown-generation/#22-link-citations-references)
- [2.3 Optional Content Filters](https://docs.crawl4ai.com/core/markdown-generation/#23-optional-content-filters)
- [3. Configuring the Default Markdown Generator](https://docs.crawl4ai.com/core/markdown-generation/#3-configuring-the-default-markdown-generator)
- [4. Selecting the HTML Source for Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/#4-selecting-the-html-source-for-markdown-generation)
- [HTML Source Options](https://docs.crawl4ai.com/core/markdown-generation/#html-source-options)
- [When to Use Each Option](https://docs.crawl4ai.com/core/markdown-generation/#when-to-use-each-option)
- [5. Content Filters](https://docs.crawl4ai.com/core/markdown-generation/#5-content-filters)
- [5.1 BM25ContentFilter](https://docs.crawl4ai.com/core/markdown-generation/#51-bm25contentfilter)
- [5.2 PruningContentFilter](https://docs.crawl4ai.com/core/markdown-generation/#52-pruningcontentfilter)
- [5.3 LLMContentFilter](https://docs.crawl4ai.com/core/markdown-generation/#53-llmcontentfilter)
- [6. Using Fit Markdown](https://docs.crawl4ai.com/core/markdown-generation/#6-using-fit-markdown)
- [7. The MarkdownGenerationResult Object](https://docs.crawl4ai.com/core/markdown-generation/#7-the-markdowngenerationresult-object)
- [8. Combining Filters (BM25 + Pruning) in Two Passes](https://docs.crawl4ai.com/core/markdown-generation/#8-combining-filters-bm25-pruning-in-two-passes)
- [Two-Pass Example](https://docs.crawl4ai.com/core/markdown-generation/#two-pass-example)
- [What’s Happening?](https://docs.crawl4ai.com/core/markdown-generation/#whats-happening)
- [Tips & Variations](https://docs.crawl4ai.com/core/markdown-generation/#tips-variations)
- [One-Pass Combination?](https://docs.crawl4ai.com/core/markdown-generation/#one-pass-combination)
- [9. Common Pitfalls & Tips](https://docs.crawl4ai.com/core/markdown-generation/#9-common-pitfalls-tips)
- [10. Summary & Next Steps](https://docs.crawl4ai.com/core/markdown-generation/#10-summary-next-steps)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/cache-modes

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/cache-modes/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - Cache Modes
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Crawl4AI Cache System and Migration Guide](https://docs.crawl4ai.com/core/cache-modes/#crawl4ai-cache-system-and-migration-guide)
- [Overview](https://docs.crawl4ai.com/core/cache-modes/#overview)
- [Old vs New Approach](https://docs.crawl4ai.com/core/cache-modes/#old-vs-new-approach)
- [Migration Example](https://docs.crawl4ai.com/core/cache-modes/#migration-example)
- [Common Migration Patterns](https://docs.crawl4ai.com/core/cache-modes/#common-migration-patterns)

# Crawl4AI Cache System and Migration Guide

## Overview

Starting from version 0.5.0, Crawl4AI introduces a new caching system that replaces the old boolean flags with a more intuitive `CacheMode` enum. This change simplifies cache control and makes the behavior more predictable.

## Old vs New Approach

### Old Way (Deprecated)

The old system used multiple boolean flags: - `bypass_cache`: Skip cache entirely - `disable_cache`: Disable all caching - `no_cache_read`: Don't read from cache - `no_cache_write`: Don't write to cache

### New Way (Recommended)

The new system uses a single `CacheMode` enum: - `CacheMode.ENABLED`: Normal caching (read/write) - `CacheMode.DISABLED`: No caching at all - `CacheMode.READ_ONLY`: Only read from cache - `CacheMode.WRITE_ONLY`: Only write to cache - `CacheMode.BYPASS`: Skip cache for this operation

## Migration Example

### Old Code (Deprecated)

```
import asyncio
from crawl4ai import AsyncWebCrawler

async def use_proxy():
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url="https://www.nbcnews.com/business",
            bypass_cache=True  # Old way
        )
        print(len(result.markdown))

async def main():
    await use_proxy()

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### New Code (Recommended)

```
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.async_configs import CrawlerRunConfig

async def use_proxy():
    # Use CacheMode in CrawlerRunConfig
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url="https://www.nbcnews.com/business",
            config=config  # Pass the configuration object
        )
        print(len(result.markdown))

async def main():
    await use_proxy()

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

## Common Migration Patterns

| Old Flag              | New Mode                          |
| --------------------- | --------------------------------- |
| `bypass_cache=True`   | `cache_mode=CacheMode.BYPASS`     |
| `disable_cache=True`  | `cache_mode=CacheMode.DISABLED`   |
| `no_cache_read=True`  | `cache_mode=CacheMode.WRITE_ONLY` |
| `no_cache_write=True` | `cache_mode=CacheMode.READ_ONLY`  |

Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/cache-modes/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/cache-modes/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/cache-modes/)

ESC to close

#### On this page

- [Overview](https://docs.crawl4ai.com/core/cache-modes/#overview)
- [Old vs New Approach](https://docs.crawl4ai.com/core/cache-modes/#old-vs-new-approach)
- [Old Way (Deprecated)](https://docs.crawl4ai.com/core/cache-modes/#old-way-deprecated)
- [New Way (Recommended)](https://docs.crawl4ai.com/core/cache-modes/#new-way-recommended)
- [Migration Example](https://docs.crawl4ai.com/core/cache-modes/#migration-example)
- [Old Code (Deprecated)](https://docs.crawl4ai.com/core/cache-modes/#old-code-deprecated)
- [New Code (Recommended)](https://docs.crawl4ai.com/core/cache-modes/#new-code-recommended)
- [Common Migration Patterns](https://docs.crawl4ai.com/core/cache-modes/#common-migration-patterns)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/content-selection

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/content-selection/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - Content Selection
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Content Selection](https://docs.crawl4ai.com/core/content-selection/#content-selection)
- [1. CSS-Based Selection](https://docs.crawl4ai.com/core/content-selection/#1-css-based-selection)
- [2. Content Filtering & Exclusions](https://docs.crawl4ai.com/core/content-selection/#2-content-filtering-exclusions)
- [3. Handling Iframes](https://docs.crawl4ai.com/core/content-selection/#3-handling-iframes)
- [4. Structured Extraction Examples](https://docs.crawl4ai.com/core/content-selection/#4-structured-extraction-examples)
- [5. Comprehensive Example](https://docs.crawl4ai.com/core/content-selection/#5-comprehensive-example)
- [6. Scraping Modes](https://docs.crawl4ai.com/core/content-selection/#6-scraping-modes)
- [7. Combining CSS Selection Methods](https://docs.crawl4ai.com/core/content-selection/#7-combining-css-selection-methods)
- [8. Conclusion](https://docs.crawl4ai.com/core/content-selection/#8-conclusion)

# Content Selection

Crawl4AI provides multiple ways to **select** , **filter** , and **refine** the content from your crawls. Whether you need to target a specific CSS region, exclude entire tags, filter out external links, or remove certain domains and images, **`CrawlerRunConfig`**offers a wide range of parameters.
Below, we show how to configure these parameters and combine them for precise control.

---

## 1. CSS-Based Selection

There are two ways to select content from a page: using `css_selector` or the more flexible `target_elements`.

### 1.1 Using `css_selector`

A straightforward way to **limit** your crawl results to a certain region of the page is **`css_selector`**in**`CrawlerRunConfig`**:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    config = CrawlerRunConfig(
        # e.g., first 30 items from Hacker News
        css_selector=".athing:nth-child(-n+30)"
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com/newest",
            config=config
        )
        print("Partial HTML length:", len(result.cleaned_html))

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Result** : Only elements matching that selector remain in `result.cleaned_html`.

### 1.2 Using `target_elements`

The `target_elements` parameter provides more flexibility by allowing you to target **multiple elements** for content extraction while preserving the entire page context for other features:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    config = CrawlerRunConfig(
        # Target article body and sidebar, but not other content
        target_elements=["article.main-content", "aside.sidebar"]
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com/blog-post",
            config=config
        )
        print("Markdown focused on target elements")
        print("Links from entire page still available:", len(result.links.get("internal", [])))

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key difference** : With `target_elements`, the markdown generation and structural data extraction focus on those elements, but other page elements (like links, images, and tables) are still extracted from the entire page. This gives you fine-grained control over what appears in your markdown content while preserving full page context for link analysis and media collection.

---

## 2. Content Filtering & Exclusions

### 2.1 Basic Overview

```
config = CrawlerRunConfig(
    # Content thresholds
    word_count_threshold=10,        # Minimum words per block

    # Tag exclusions
    excluded_tags=['form', 'header', 'footer', 'nav'],

    # Link filtering
    exclude_external_links=True,
    exclude_social_media_links=True,
    # Block entire domains
    exclude_domains=["adtrackers.com", "spammynews.org"],
    exclude_social_media_domains=["facebook.com", "twitter.com"],

    # Media filtering
    exclude_external_images=True
)
Copy
```

**Explanation** :

- **`word_count_threshold`**: Ignores text blocks under X words. Helps skip trivial blocks like short nav or disclaimers.
- **`excluded_tags`**: Removes entire tags (`<form>` , `<header>`, `<footer>`, etc.).
- **Link Filtering** :
- `exclude_external_links`: Strips out external links and may remove them from `result.links`.
- `exclude_social_media_links`: Removes links pointing to known social media domains.
- `exclude_domains`: A custom list of domains to block if discovered in links.
- `exclude_social_media_domains`: A curated list (override or add to it) for social media sites.
- **Media Filtering** :
- `exclude_external_images`: Discards images not hosted on the same domain as the main page (or its subdomains).

By default in case you set `exclude_social_media_links=True`, the following social media domains are excluded:

```
[
    'facebook.com',
    'twitter.com',
    'x.com',
    'linkedin.com',
    'instagram.com',
    'pinterest.com',
    'tiktok.com',
    'snapchat.com',
    'reddit.com',
]
Copy
```

### 2.2 Example Usage

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def main():
    config = CrawlerRunConfig(
        css_selector="main.content",
        word_count_threshold=10,
        excluded_tags=["nav", "footer"],
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_domains=["ads.com", "spammytrackers.net"],
        exclude_external_images=True,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://news.ycombinator.com", config=config)
        print("Cleaned HTML length:", len(result.cleaned_html))

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Note** : If these parameters remove too much, reduce or disable them accordingly.

---

## 3. Handling Iframes

Some sites embed content in `<iframe>` tags. If you want that inline:

```
config = CrawlerRunConfig(
    # Merge iframe content into the final output
    process_iframes=True,
    remove_overlay_elements=True
)
Copy
```

**Usage** :

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    config = CrawlerRunConfig(
        process_iframes=True,
        remove_overlay_elements=True
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.org/iframe-demo",
            config=config
        )
        print("Iframe-merged length:", len(result.cleaned_html))

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

## 4. Structured Extraction Examples

You can combine content selection with a more advanced extraction strategy. For instance, a **CSS-based** or **LLM-based** extraction strategy can run on the filtered HTML.

### 4.1 Pattern-Based with `JsonCssExtractionStrategy`

```
import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy

async def main():
    # Minimal schema for repeated items
    schema = {
        "name": "News Items",
        "baseSelector": "tr.athing",
        "fields": [
            {"name": "title", "selector": "span.titleline a", "type": "text"},
            {
                "name": "link",
                "selector": "span.titleline a",
                "type": "attribute",
                "attribute": "href"
            }
        ]
    }

    config = CrawlerRunConfig(
        # Content filtering
        excluded_tags=["form", "header"],
        exclude_domains=["adsite.com"],

        # CSS selection or entire page
        css_selector="table.itemlist",

        # No caching for demonstration
        cache_mode=CacheMode.BYPASS,

        # Extraction strategy
        extraction_strategy=JsonCssExtractionStrategy(schema)
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com/newest",
            config=config
        )
        data = json.loads(result.extracted_content)
        print("Sample extracted item:", data[:1])  # Show first item

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### 4.2 LLM-Based Extraction

```
import asyncio
import json
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig
from crawl4ai import LLMExtractionStrategy

class ArticleData(BaseModel):
    headline: str
    summary: str

async def main():
    llm_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider="openai/gpt-4",api_token="sk-YOUR_API_KEY")
        schema=ArticleData.schema(),
        extraction_type="schema",
        instruction="Extract 'headline' and a short 'summary' from the content."
    )

    config = CrawlerRunConfig(
        exclude_external_links=True,
        word_count_threshold=20,
        extraction_strategy=llm_strategy
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://news.ycombinator.com", config=config)
        article = json.loads(result.extracted_content)
        print(article)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

Here, the crawler:

- Filters out external links (`exclude_external_links=True`).
- Ignores very short text blocks (`word_count_threshold=20`).
- Passes the final HTML to your LLM strategy for an AI-driven parse.

---

## 5. Comprehensive Example

Below is a short function that unifies **CSS selection** , **exclusion** logic, and a pattern-based extraction, demonstrating how you can fine-tune your final data:

```
import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy

async def extract_main_articles(url: str):
    schema = {
        "name": "ArticleBlock",
        "baseSelector": "div.article-block",
        "fields": [
            {"name": "headline", "selector": "h2", "type": "text"},
            {"name": "summary", "selector": ".summary", "type": "text"},
            {
                "name": "metadata",
                "type": "nested",
                "fields": [
                    {"name": "author", "selector": ".author", "type": "text"},
                    {"name": "date", "selector": ".date", "type": "text"}
                ]
            }
        ]
    }

    config = CrawlerRunConfig(
        # Keep only #main-content
        css_selector="#main-content",

        # Filtering
        word_count_threshold=10,
        excluded_tags=["nav", "footer"],
        exclude_external_links=True,
        exclude_domains=["somebadsite.com"],
        exclude_external_images=True,

        # Extraction
        extraction_strategy=JsonCssExtractionStrategy(schema),

        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)
        if not result.success:
            print(f"Error: {result.error_message}")
            return None
        return json.loads(result.extracted_content)

async def main():
    articles = await extract_main_articles("https://news.ycombinator.com/newest")
    if articles:
        print("Extracted Articles:", articles[:2])  # Show first 2

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Why This Works** : - **CSS** scoping with `#main-content`.

- Multiple **exclude\_** parameters to remove domains, external images, etc.
- A **JsonCssExtractionStrategy** to parse repeated article blocks.

---

## 6. Scraping Modes

Crawl4AI uses `LXMLWebScrapingStrategy` (LXML-based) as the default scraping strategy for HTML content processing. This strategy offers excellent performance, especially for large HTML documents.
**Note:** For backward compatibility, `WebScrapingStrategy` is still available as an alias for `LXMLWebScrapingStrategy`.

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LXMLWebScrapingStrategy

async def main():
    # Default configuration already uses LXMLWebScrapingStrategy
    config = CrawlerRunConfig()

    # Or explicitly specify it if desired
    config_explicit = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy()
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=config
        )
Copy
```

You can also create your own custom scraping strategy by inheriting from `ContentScrapingStrategy`. The strategy must return a `ScrapingResult` object with the following structure:

```
from crawl4ai import ContentScrapingStrategy, ScrapingResult, MediaItem, Media, Link, Links

class CustomScrapingStrategy(ContentScrapingStrategy):
    def scrap(self, url: str, html: str, **kwargs) -> ScrapingResult:
        # Implement your custom scraping logic here
        return ScrapingResult(
            cleaned_html="<html>...</html>",  # Cleaned HTML content
            success=True,                     # Whether scraping was successful
            media=Media(
                images=[                      # List of images found
                    MediaItem(
                        src="https://example.com/image.jpg",
                        alt="Image description",
                        desc="Surrounding text",
                        score=1,
                        type="image",
                        group_id=1,
                        format="jpg",
                        width=800
                    )
                ],
                videos=[],                    # List of videos (same structure as images)
                audios=[]                     # List of audio files (same structure as images)
            ),
            links=Links(
                internal=[                    # List of internal links
                    Link(
                        href="https://example.com/page",
                        text="Link text",
                        title="Link title",
                        base_domain="example.com"
                    )
                ],
                external=[]                   # List of external links (same structure)
            ),
            metadata={                        # Additional metadata
                "title": "Page Title",
                "description": "Page description"
            }
        )

    async def ascrap(self, url: str, html: str, **kwargs) -> ScrapingResult:
        # For simple cases, you can use the sync version
        return await asyncio.to_thread(self.scrap, url, html, **kwargs)
Copy
```

### Performance Considerations

The LXML strategy provides excellent performance, particularly when processing large HTML documents, offering up to 10-20x faster processing compared to BeautifulSoup-based approaches.
Benefits of LXML strategy: - Fast processing of large HTML documents (especially >100KB) - Efficient memory usage - Good handling of well-formed HTML - Robust table detection and extraction

### Backward Compatibility

For users upgrading from earlier versions: - `WebScrapingStrategy` is now an alias for `LXMLWebScrapingStrategy` - Existing code using `WebScrapingStrategy` will continue to work without modification - No changes are required to your existing code

---

## 7. Combining CSS Selection Methods

You can combine `css_selector` and `target_elements` in powerful ways to achieve fine-grained control over your output:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def main():
    # Target specific content but preserve page context
    config = CrawlerRunConfig(
        # Focus markdown on main content and sidebar
        target_elements=["#main-content", ".sidebar"],

        # Global filters applied to entire page
        excluded_tags=["nav", "footer", "header"],
        exclude_external_links=True,

        # Use basic content thresholds
        word_count_threshold=15,

        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com/article",
            config=config
        )

        print(f"Content focuses on specific elements, but all links still analyzed")
        print(f"Internal links: {len(result.links.get('internal', []))}")
        print(f"External links: {len(result.links.get('external', []))}")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

This approach gives you the best of both worlds: - Markdown generation and content extraction focus on the elements you care about - Links, images and other page data still give you the full context of the page - Content filtering still applies globally

## 8. Conclusion

By mixing **target_elements** or **css_selector** scoping, **content filtering** parameters, and advanced **extraction strategies** , you can precisely **choose** which data to keep. Key parameters in **`CrawlerRunConfig`**for content selection include:

1. **`target_elements`**– Array of CSS selectors to focus markdown generation and data extraction, while preserving full page context for links and media.
2. **`css_selector`**– Basic scoping to an element or region for all extraction processes.
3. **`word_count_threshold`**– Skip short blocks.
4. **`excluded_tags`**– Remove entire HTML tags.
5. **`exclude_external_links`**,**`exclude_social_media_links`**,**`exclude_domains`**– Filter out unwanted links or domains.
6. **`exclude_external_images`**– Remove images from external sources.
7. **`process_iframes`**– Merge iframe content if needed.

Combine these with structured extraction (CSS, LLM-based, or others) to build powerful crawls that yield exactly the content you want, from raw or cleaned HTML up to sophisticated JSON structures. For more detail, see [Configuration Reference](https://docs.crawl4ai.com/api/parameters/). Enjoy curating your data to the max!
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/content-selection/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/content-selection/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/content-selection/)

ESC to close

#### On this page

- [1. CSS-Based Selection](https://docs.crawl4ai.com/core/content-selection/#1-css-based-selection)
- [1.1 Using css_selector](https://docs.crawl4ai.com/core/content-selection/#11-using-css_selector)
- [1.2 Using target_elements](https://docs.crawl4ai.com/core/content-selection/#12-using-target_elements)
- [2. Content Filtering & Exclusions](https://docs.crawl4ai.com/core/content-selection/#2-content-filtering-exclusions)
- [2.1 Basic Overview](https://docs.crawl4ai.com/core/content-selection/#21-basic-overview)
- [2.2 Example Usage](https://docs.crawl4ai.com/core/content-selection/#22-example-usage)
- [3. Handling Iframes](https://docs.crawl4ai.com/core/content-selection/#3-handling-iframes)
- [4. Structured Extraction Examples](https://docs.crawl4ai.com/core/content-selection/#4-structured-extraction-examples)
- [4.1 Pattern-Based with JsonCssExtractionStrategy](https://docs.crawl4ai.com/core/content-selection/#41-pattern-based-with-jsoncssextractionstrategy)
- [4.2 LLM-Based Extraction](https://docs.crawl4ai.com/core/content-selection/#42-llm-based-extraction)
- [5. Comprehensive Example](https://docs.crawl4ai.com/core/content-selection/#5-comprehensive-example)
- [6. Scraping Modes](https://docs.crawl4ai.com/core/content-selection/#6-scraping-modes)
- [Performance Considerations](https://docs.crawl4ai.com/core/content-selection/#performance-considerations)
- [Backward Compatibility](https://docs.crawl4ai.com/core/content-selection/#backward-compatibility)
- [7. Combining CSS Selection Methods](https://docs.crawl4ai.com/core/content-selection/#7-combining-css-selection-methods)
- [8. Conclusion](https://docs.crawl4ai.com/core/content-selection/#8-conclusion)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/apps/llmtxt

![Crawl4AI Logo](https://docs.crawl4ai.com/img/favicon-32x32.png)

# Crawl4AI LLM Context Builder

Multi-Dimensional Context for AI Assistants
[← Back to Docs](https://docs.crawl4ai.com/) [All Apps](https://docs.crawl4ai.com/apps/) [GitHub](https://github.com/unclecode/crawl4ai)

## 🧠 A New Approach to LLM Context

Traditional `llm.txt` files often fail with complex libraries like Crawl4AI. They dump massive amounts of API documentation, causing **information overload** and **lost focus**. They provide the "what" but miss the crucial "how" and "why" that makes AI assistants truly helpful.

### 💡 The Solution: Multi-Dimensional, Modular Contexts

Inspired by modular libraries like Lodash, I've redesigned how we provide context to AI assistants. Instead of one monolithic file, Crawl4AI's documentation is organized by **components** and **perspectives**.
Memory

#### The "What"

Precise API facts, parameters, signatures, and configuration objects. Your unambiguous reference.
Reasoning

#### The "How" & "Why"

Design principles, best practices, trade-offs, and workflows. Teaches AI to think like an expert.
Examples

#### The "Show Me"

Runnable code snippets demonstrating patterns in action. Pure practical implementation.
**Why this matters:** You can now give your AI assistant exactly what it needs - whether that's quick API lookups, help designing solutions, or seeing practical implementations. No more information overload, just focused, relevant context.
[📖 Read the full story behind this approach →](https://docs.crawl4ai.com/blog/articles/llm-context-revolution)

## Select Components & Context Types

Select All Deselect All
| Component | Memory
Full Content | Reasoning
Diagrams | Examples
Code
---|---|---|---|---
| Installation | 1,458 tokens | 2,658 tokens |
| Simple Crawling | 2,390 tokens | 3,133 tokens |
| Configuration Objects | 7,868 tokens | 9,795 tokens |
| Data Extraction Using LLM | 6,775 tokens | 3,543 tokens |
| Data Extraction Without LLM | 6,068 tokens | 3,543 tokens |
| Multi URLs Crawling | 2,230 tokens | 2,853 tokens |
| Deep Crawling | 2,208 tokens | 3,455 tokens |
| Docker | 5,155 tokens | 4,308 tokens |
| CLI | 2,373 tokens | 3,350 tokens |
| HTTP-based Crawler | 2,390 tokens | 3,413 tokens |
| URL Seeder | 4,745 tokens | 3,080 tokens |
| Advanced Filters & Scorers | 2,713 tokens | 3,030 tokens |
Estimated Tokens: 4,116
⬇ Generate & Download Context

## Available Context Files

| Component                       | Memory                                                                                                      | Reasoning                                                                                                           | Examples | Full |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------- | ---- |
| **Installation**                | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/installation.txt) 1,458 tokens                        | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/installation.txt) 2,658 tokens                        | -        | -    |
| **Simple Crawling**             | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/simple_crawling.txt) 2,390 tokens                     | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/simple_crawling.txt) 3,133 tokens                     | -        | -    |
| **Configuration Objects**       | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/config_objects.txt) 7,868 tokens                      | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/config_objects.txt) 9,795 tokens                      | -        | -    |
| **Data Extraction Using LLM**   | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/extraction-llm.txt) 6,775 tokens                      | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/extraction-llm.txt) 3,543 tokens                      | -        | -    |
| **Data Extraction Without LLM** | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/extraction-no-llm.txt) 6,068 tokens                   | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/extraction-no-llm.txt) 3,543 tokens                   | -        | -    |
| **Multi URLs Crawling**         | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/multi_urls_crawling.txt) 2,230 tokens                 | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/multi_urls_crawling.txt) 2,853 tokens                 | -        | -    |
| **Deep Crawling**               | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/deep_crawling.txt) 2,208 tokens                       | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/deep_crawling.txt) 3,455 tokens                       | -        | -    |
| **Docker**                      | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/docker.txt) 5,155 tokens                              | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/docker.txt) 4,308 tokens                              | -        | -    |
| **CLI**                         | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/cli.txt) 2,373 tokens                                 | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/cli.txt) 3,350 tokens                                 | -        | -    |
| **HTTP-based Crawler**          | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/http_based_crawler_strategy.txt) 2,390 tokens         | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/http_based_crawler_strategy.txt) 3,413 tokens         | -        | -    |
| **URL Seeder**                  | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/url_seeder.txt) 4,745 tokens                          | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/url_seeder.txt) 3,080 tokens                          | -        | -    |
| **Advanced Filters & Scorers**  | [Memory](https://docs.crawl4ai.com/assets/llm.txt/txt/deep_crawl_advanced_filters_scorers.txt) 2,713 tokens | [Reasoning](https://docs.crawl4ai.com/assets/llm.txt/diagrams/deep_crawl_advanced_filters_scorers.txt) 3,030 tokens | -        | -    |

---

## Fonte: https://docs.crawl4ai.com/branding

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/branding/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- Brand Book

---

- [🎨 Crawl4AI Brand Book](https://docs.crawl4ai.com/branding/#crawl4ai-brand-book)
- [📖 About This Guide](https://docs.crawl4ai.com/branding/#about-this-guide)

# 🎨 Crawl4AI Brand Book

# Crawl4AI Brand Guidelines

A comprehensive design system for building consistent, terminal-inspired experiences

## 📖 About This Guide

This brand book documents the complete visual language of Crawl4AI. Whether you're building documentation pages, interactive apps, or Chrome extensions, these guidelines ensure consistency while maintaining the unique terminal-aesthetic that defines our brand.

---

🎨

## Color System

Our color palette is built around a terminal-dark aesthetic with vibrant cyan and pink accents. Every color serves a purpose and maintains accessibility standards.

### Primary Colors

Primary Cyan
`#50ffff`
Main brand color, links, highlights, CTAs
Primary Teal
`#09b5a5`
Hover states, dimmed accents, progress bars
Primary Green
`#0fbbaa`
Alternative primary, buttons, nav links
Accent Pink
`#f380f5`
Secondary accents, keywords, highlights

### Background Colors

Deep Black
`#070708`
Main background, code blocks, deep containers
Secondary Dark
`#1a1a1a`
Headers, sidebars, secondary containers
Tertiary Gray
`#3f3f44`
Cards, borders, code backgrounds, modals
Block Background
`#202020`
Block elements, alternate rows

### Text Colors

Primary Text
`#e8e9ed`
Headings, body text, primary content
Secondary Text
`#d5cec0`
Body text, descriptions, warm tone
Tertiary Text
`#a3abba`
Captions, labels, metadata, cool tone
Dimmed Text
`#8b857a`
Disabled states, comments, subtle text

### Semantic Colors

Success Green
`#50ff50`
Success messages, completed states, valid
Error Red
`#ff3c74`
Errors, warnings, destructive actions
Warning Orange
`#f59e0b`
Warnings, beta status, caution
Info Blue
`#4a9eff`
Info messages, external links

---

✍️

## Typography

Our typography system is built around **Dank Mono** , a monospace font that reinforces the terminal aesthetic while maintaining excellent readability.

### Font Family

```
--font-primary: 'Dank Mono', dm, Monaco, Courier New, monospace;
--font-code: 'Dank Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
Copy
```

**Font Weights:** - Regular: 400 - Bold: 700 - Italic: 400 (italic variant)

### Type Scale

H1 / Hero
Size: 2.5rem (40px) Weight: 700 Line-height: 1.2

# The Quick Brown Fox Jumps Over

H2 / Section
Size: 1.75rem (28px) Weight: 700 Line-height: 1.3

## Advanced Web Scraping Features

H3 / Subsection
Size: 1.3rem (20.8px) Weight: 600 Line-height: 1.4

### Installation and Setup Guide

H4 / Component
Size: 1.1rem (17.6px) Weight: 600 Line-height: 1.4

#### Quick Start Instructions

Body / Regular
Size: 14px Weight: 400 Line-height: 1.6
Crawl4AI is the #1 trending GitHub repository, actively maintained by a vibrant community. It delivers blazing-fast, AI-ready web crawling tailored for large language models and data pipelines.
Code / Monospace
Size: 13px Weight: 400 Line-height: 1.5
`async with AsyncWebCrawler() as crawler:`
Small / Caption
Size: 12px Weight: 400 Line-height: 1.5
Updated 2 hours ago • v0.7.2

---

🧩

## Components

### Buttons

### Primary Button

Launch Editor → Processing...
HTML + CSS Copy

```
<button class="brand-btn brand-btn-primary">
  Launch Editor →
</button>Copy
```

### Secondary Button

View Documentation Loading...
HTML + CSS Copy

```
<button class="brand-btn brand-btn-secondary">
  View Documentation
</button>Copy
```

### Accent Button

Try Beta Features Unavailable
HTML + CSS Copy

```
<button class="brand-btn brand-btn-accent">
  Try Beta Features
</button>Copy
```

### Ghost Button

Learn More Coming Soon
HTML + CSS Copy

```
<button class="brand-btn brand-btn-ghost">
  Learn More
</button>Copy
```

### Badges & Status Indicators

### Status Badges

Available Beta Alpha New! Coming Soon
HTML + CSS Copy

```
<span class="brand-badge badge-available">Available</span>
<span class="brand-badge badge-beta">Beta</span>
<span class="brand-badge badge-alpha">Alpha</span>
<span class="brand-badge badge-new">New!</span>Copy
```

### Cards

### 🎨 C4A-Script Editor

A visual, block-based programming environment for creating browser automation scripts. Perfect for beginners and experts alike!
Launch Editor →

### 🧠 LLM Context Builder

Generate optimized context files for your favorite LLM when working with Crawl4AI. Get focused, relevant documentation based on your needs.
Launch Builder →
HTML + CSS Copy

```
<div class="brand-card">
  <h3 class="brand-card-title">Card Title</h3>
  <p class="brand-card-description">Card description...</p>
</div>Copy
```

### Terminal Window

crawl4ai@terminal ~ %
$ pip install crawl4ai
Successfully installed crawl4ai-0.7.2
HTML + CSS Copy

```
<div class="terminal-window">
  <div class="terminal-header">
    <div class="terminal-dots">
      <span class="terminal-dot red"></span>
      <span class="terminal-dot yellow"></span>
      <span class="terminal-dot green"></span>
    </div>
    <span class="terminal-title">Terminal Title</span>
  </div>
  <div class="terminal-content">
    Your content here
  </div>
</div>Copy
```

---

📐

## Spacing & Layout

### Spacing System

Our spacing system is based on multiples of **10px** for consistency and ease of calculation.
10px - Extra Small (xs)
20px - Small (sm)
30px - Medium (md)
40px - Large (lg)
60px - Extra Large (xl)
80px - 2XL

### Layout Patterns

#### Terminal Container

Full-height, flex-column layout with sticky header

```
.terminal-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}
Copy
```

#### Content Grid

Auto-fit responsive grid for cards and components

```
.component-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}
Copy
```

#### Centered Content

Maximum width with auto margins for centered layouts

```
.content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}
Copy
```

---

✅

## Usage Guidelines

### When to Use Each Style

**Documentation Pages (`docs/md_v2/core` , `/advanced`, etc.)** - Use main documentation styles from `styles.css` and `layout.css` - Terminal theme with sidebar navigation - Dense, informative content - ToC on the right side - Focus on readability and technical accuracy
**Landing Pages (`docs/md_v2/apps/crawl4ai-assistant` , etc.)** - Use `assistant.css` style approach - Hero sections with gradients - Feature cards with hover effects - Video/demo sections - Sticky header with navigation - Marketing-focused, visually engaging
**App Home (`docs/md_v2/apps/index.md`)** - Grid-based card layouts - Status badges - Call-to-action buttons - Feature highlights - Mix of informational and promotional
**Interactive Apps (`docs/md_v2/apps/llmtxt` , `/c4a-script`)** - Full-screen application layouts - Interactive controls - Real-time feedback - Tool-specific UI patterns - Functional over decorative
**Chrome Extension (`popup.css`)** - Compact, fixed-width design (380px) - Clear mode selection - Session indicators - Minimal but effective - Fast loading, no heavy assets

### Do's and Don'ts

✅ DO
Launch App →
Use primary cyan for main CTAs and important actions
❌ DON'T
Launch App →
Don't use arbitrary colors not in the brand palette
✅ DO
`async with AsyncWebCrawler():`
Use Dank Mono for all text to maintain terminal aesthetic
❌ DON'T
async with AsyncWebCrawler():
Don't use non-monospace fonts (breaks terminal feel)
✅ DO
Beta

#### New Feature

Use status badges to indicate feature maturity
❌ DON'T

#### New Feature (Beta)

Don't put status indicators in plain text

---

🎯

## Accessibility

### Color Contrast

All color combinations meet WCAG AA standards:

- **Primary Cyan (#50ffff) on Dark (#070708)** : 12.4:1 ✅
- **Primary Text (#e8e9ed) on Dark (#070708)** : 11.8:1 ✅
- **Secondary Text (#d5cec0) on Dark (#070708)** : 9.2:1 ✅
- **Tertiary Text (#a3abba) on Dark (#070708)** : 6.8:1 ✅

### Focus States

All interactive elements must have visible focus indicators:

```
button:focus,
a:focus {
    outline: 2px solid #50ffff;
    outline-offset: 2px;
}
Copy
```

### Motion

Respect `prefers-reduced-motion` for users who need it:

```
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
Copy
```

---

💾

## CSS Variables

Use these CSS variables for consistency across all styles:

```
:root {
    /* Colors */
    --primary-color: #50ffff;
    --primary-dimmed: #09b5a5;
    --primary-green: #0fbbaa;
    --accent-color: #f380f5;

    /* Backgrounds */
    --background-color: #070708;
    --bg-secondary: #1a1a1a;
    --code-bg-color: #3f3f44;
    --border-color: #3f3f44;

    /* Text */
    --font-color: #e8e9ed;
    --secondary-color: #d5cec0;
    --tertiary-color: #a3abba;

    /* Semantic */
    --success-color: #50ff50;
    --error-color: #ff3c74;
    --warning-color: #f59e0b;

    /* Typography */
    --font-primary: 'Dank Mono', dm, Monaco, Courier New, monospace;
    --global-font-size: 14px;
    --global-line-height: 1.6;

    /* Spacing */
    --global-space: 10px;

    /* Layout */
    --header-height: 65px;
    --sidebar-width: 280px;
    --toc-width: 340px;
    --content-max-width: 90em;
}
Copy
```

---

📚

## Resources

### Download Assets

- [Dank Mono Font Files](https://docs.crawl4ai.com/docs/md_v2/assets/) (Regular, Bold, Italic)
- [Brand CSS Template](https://docs.crawl4ai.com/docs/md_v2/branding/assets/brand-examples.css)
- [Component Library](https://docs.crawl4ai.com/docs/md_v2/apps/)

### Reference Files

- Main Documentation Styles: `docs/md_v2/assets/styles.css`
- Layout System: `docs/md_v2/assets/layout.css`
- Landing Page Style: `docs/md_v2/apps/crawl4ai-assistant/assistant.css`
- App Home Style: `docs/md_v2/apps/index.md`
- Extension Style: `docs/md_v2/apps/crawl4ai-assistant/popup/popup.css`

### Questions?

If you're unsure about which style to use or need help implementing these guidelines:

- Check existing examples in the relevant section
- Review the "When to Use Each Style" guidelines above
- Ask in our [Discord community](https://discord.gg/crawl4ai)
- Open an issue on [GitHub](https://github.com/unclecode/crawl4ai)

---

### 🎨 Keep It Terminal

When in doubt, ask yourself: "Does this feel like a terminal?" If yes, you're on brand.

#### On this page

- [📖 About This Guide](https://docs.crawl4ai.com/branding/#about-this-guide)
- [Color System](https://docs.crawl4ai.com/branding/#toc-heading-1-color-system)
- [Primary Colors](https://docs.crawl4ai.com/branding/#primary-colors)
- [Background Colors](https://docs.crawl4ai.com/branding/#background-colors)
- [Text Colors](https://docs.crawl4ai.com/branding/#text-colors)
- [Semantic Colors](https://docs.crawl4ai.com/branding/#semantic-colors)
- [Typography](https://docs.crawl4ai.com/branding/#toc-heading-6-typography)
- [Font Family](https://docs.crawl4ai.com/branding/#font-family)
- [Type Scale](https://docs.crawl4ai.com/branding/#type-scale)
- [Advanced Web Scraping Features](https://docs.crawl4ai.com/branding/#toc-heading-9-advanced-web-scraping-features)
- [Installation and Setup Guide](https://docs.crawl4ai.com/branding/#toc-heading-10-installation-and-setup-guide)
- [Quick Start Instructions](https://docs.crawl4ai.com/branding/#toc-heading-11-quick-start-instructions)
- [Components](https://docs.crawl4ai.com/branding/#toc-heading-12-components)
- [Buttons](https://docs.crawl4ai.com/branding/#buttons)
- [Primary Button](https://docs.crawl4ai.com/branding/#toc-heading-14-primary-button)
- [Secondary Button](https://docs.crawl4ai.com/branding/#toc-heading-15-secondary-button)
- [Accent Button](https://docs.crawl4ai.com/branding/#toc-heading-16-accent-button)
- [Ghost Button](https://docs.crawl4ai.com/branding/#toc-heading-17-ghost-button)
- [Badges & Status Indicators](https://docs.crawl4ai.com/branding/#badges-status-indicators)
- [Status Badges](https://docs.crawl4ai.com/branding/#toc-heading-19-status-badges)
- [Cards](https://docs.crawl4ai.com/branding/#cards)
- [🎨 C4A-Script Editor](https://docs.crawl4ai.com/branding/#toc-heading-21--c4a-script-editor)
- [🧠 LLM Context Builder](https://docs.crawl4ai.com/branding/#toc-heading-22--llm-context-builder)
- [Terminal Window](https://docs.crawl4ai.com/branding/#terminal-window)
- [Spacing & Layout](https://docs.crawl4ai.com/branding/#toc-heading-24-spacing--layout)
- [Spacing System](https://docs.crawl4ai.com/branding/#spacing-system)
- [Layout Patterns](https://docs.crawl4ai.com/branding/#layout-patterns)
- [Terminal Container](https://docs.crawl4ai.com/branding/#terminal-container)
- [Content Grid](https://docs.crawl4ai.com/branding/#content-grid)
- [Centered Content](https://docs.crawl4ai.com/branding/#centered-content)
- [Usage Guidelines](https://docs.crawl4ai.com/branding/#toc-heading-30-usage-guidelines)
- [When to Use Each Style](https://docs.crawl4ai.com/branding/#when-to-use-each-style)
- [Do's and Don'ts](https://docs.crawl4ai.com/branding/#dos-and-donts)
- [New Feature](https://docs.crawl4ai.com/branding/#toc-heading-33-new-feature)
- [New Feature (Beta)](https://docs.crawl4ai.com/branding/#toc-heading-34-new-feature-beta)
- [Accessibility](https://docs.crawl4ai.com/branding/#toc-heading-35-accessibility)
- [Color Contrast](https://docs.crawl4ai.com/branding/#color-contrast)
- [Focus States](https://docs.crawl4ai.com/branding/#focus-states)
- [Motion](https://docs.crawl4ai.com/branding/#motion)
- [CSS Variables](https://docs.crawl4ai.com/branding/#toc-heading-39-css-variables)
- [Resources](https://docs.crawl4ai.com/branding/#toc-heading-40-resources)
- [Download Assets](https://docs.crawl4ai.com/branding/#download-assets)
- [Reference Files](https://docs.crawl4ai.com/branding/#reference-files)
- [Questions?](https://docs.crawl4ai.com/branding/#questions)
- [🎨 Keep It Terminal](https://docs.crawl4ai.com/branding/#toc-heading-44--keep-it-terminal)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/link-media

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/link-media/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - Link & Media
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Link & Media](https://docs.crawl4ai.com/core/link-media/#link-media)
- [Excluding External Images](https://docs.crawl4ai.com/core/link-media/#excluding-external-images)
- [Excluding All Images](https://docs.crawl4ai.com/core/link-media/#excluding-all-images)
- [1. Link Extraction](https://docs.crawl4ai.com/core/link-media/#1-link-extraction)
- [2. Advanced Link Head Extraction & Scoring](https://docs.crawl4ai.com/core/link-media/#2-advanced-link-head-extraction-scoring)
- [3. Domain Filtering](https://docs.crawl4ai.com/core/link-media/#3-domain-filtering)
- [4. Media Extraction](https://docs.crawl4ai.com/core/link-media/#4-media-extraction)
- [5. Putting It All Together: Link & Media Filtering](https://docs.crawl4ai.com/core/link-media/#5-putting-it-all-together-link-media-filtering)
- [6. Common Pitfalls & Tips](https://docs.crawl4ai.com/core/link-media/#6-common-pitfalls-tips)

# Link & Media

In this tutorial, you’ll learn how to:

1. Extract links (internal, external) from crawled pages
2. Filter or exclude specific domains (e.g., social media or custom domains)
3. Access and ma### 3.2 Excluding Images

#### Excluding External Images

If you're dealing with heavy pages or want to skip third-party images (advertisements, for example), you can turn on:

```
crawler_cfg = CrawlerRunConfig(
    exclude_external_images=True
)
Copy
```

This setting attempts to discard images from outside the primary domain, keeping only those from the site you're crawling.

#### Excluding All Images

If you want to completely remove all images from the page to maximize performance and reduce memory usage, use:

```
crawler_cfg = CrawlerRunConfig(
    exclude_all_images=True
)
Copy
```

This setting removes all images very early in the processing pipeline, which significantly improves memory efficiency and processing speed. This is particularly useful when: - You don't need image data in your results - You're crawling image-heavy pages that cause memory issues - You want to focus only on text content - You need to maximize crawling speeddata (especially images) in the crawl result 4. Configure your crawler to exclude or prioritize certain images

> **Prerequisites**
>
> - You have completed or are familiar with the [AsyncWebCrawler Basics](https://docs.crawl4ai.com/core/simple-crawling/) tutorial.
> - You can run Crawl4AI in your environment (Playwright, Python, etc.).

---

Below is a revised version of the **Link Extraction** and **Media Extraction** sections that includes example data structures showing how links and media items are stored in `CrawlResult`. Feel free to adjust any field names or descriptions to match your actual output.

---

## 1. Link Extraction

### 1.1 `result.links`

When you call `arun()` or `arun_many()` on a URL, Crawl4AI automatically extracts links and stores them in the `links` field of `CrawlResult`. By default, the crawler tries to distinguish **internal** links (same domain) from **external** links (different domains).
**Basic Example** :

```
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun("https://www.example.com")
    if result.success:
        internal_links = result.links.get("internal", [])
        external_links = result.links.get("external", [])
        print(f"Found {len(internal_links)} internal links.")
        print(f"Found {len(internal_links)} external links.")
        print(f"Found {len(result.media)} media items.")

        # Each link is typically a dictionary with fields like:
        # { "href": "...", "text": "...", "title": "...", "base_domain": "..." }
        if internal_links:
            print("Sample Internal Link:", internal_links[0])
    else:
        print("Crawl failed:", result.error_message)
Copy
```

**Structure Example** :

```
result.links = {
  "internal": [
    {
      "href": "https://kidocode.com/",
      "text": "",
      "title": "",
      "base_domain": "kidocode.com"
    },
    {
      "href": "https://kidocode.com/degrees/technology",
      "text": "Technology Degree",
      "title": "KidoCode Tech Program",
      "base_domain": "kidocode.com"
    },
    # ...
  ],
  "external": [
    # possibly other links leading to third-party sites
  ]
}
Copy
```

- **`href`**: The raw hyperlink URL.
- **`text`**: The link text (if any) within the`<a>` tag.
- **`title`**: The`title` attribute of the link (if present).
- **`base_domain`**: The domain extracted from`href`. Helpful for filtering or grouping by domain.

---

## 2. Advanced Link Head Extraction & Scoring

Ever wanted to not just extract links, but also get the actual content (title, description, metadata) from those linked pages? And score them for relevance? This is exactly what Link Head Extraction does - it fetches the `<head>` section from each discovered link and scores them using multiple algorithms.

### 2.1 Why Link Head Extraction?

When you crawl a page, you get hundreds of links. But which ones are actually valuable? Link Head Extraction solves this by:

1. **Fetching head content** from each link (title, description, meta tags)
2. **Scoring links intrinsically** based on URL quality, text relevance, and context
3. **Scoring links contextually** using BM25 algorithm when you provide a search query
4. **Combining scores intelligently** to give you a final relevance ranking

### 2.2 Complete Working Example

Here's a full example you can copy, paste, and run immediately:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai import LinkPreviewConfig

async def extract_link_heads_example():
    """
    Complete example showing link head extraction with scoring.
    This will crawl a documentation site and extract head content from internal links.
    """

    # Configure link head extraction
    config = CrawlerRunConfig(
        # Enable link head extraction with detailed configuration
        link_preview_config=LinkPreviewConfig(
            include_internal=True,           # Extract from internal links
            include_external=False,          # Skip external links for this example
            max_links=10,                   # Limit to 10 links for demo
            concurrency=5,                  # Process 5 links simultaneously
            timeout=10,                     # 10 second timeout per link
            query="API documentation guide", # Query for contextual scoring
            score_threshold=0.3,            # Only include links scoring above 0.3
            verbose=True                    # Show detailed progress
        ),
        # Enable intrinsic scoring (URL quality, text relevance)
        score_links=True,
        # Keep output clean
        only_text=True,
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        # Crawl a documentation site (great for testing)
        result = await crawler.arun("https://docs.python.org/3/", config=config)

        if result.success:
            print(f"✅ Successfully crawled: {result.url}")
            print(f"📄 Page title: {result.metadata.get('title', 'No title')}")

            # Access links (now enhanced with head data and scores)
            internal_links = result.links.get("internal", [])
            external_links = result.links.get("external", [])

            print(f"\n🔗 Found {len(internal_links)} internal links")
            print(f"🌍 Found {len(external_links)} external links")

            # Count links with head data
            links_with_head = [link for link in internal_links
                             if link.get("head_data") is not None]
            print(f"🧠 Links with head data extracted: {len(links_with_head)}")

            # Show the top 3 scoring links
            print(f"\n🏆 Top 3 Links with Full Scoring:")
            for i, link in enumerate(links_with_head[:3]):
                print(f"\n{i+1}. {link['href']}")
                print(f"   Link Text: '{link.get('text', 'No text')[:50]}...'")

                # Show all three score types
                intrinsic = link.get('intrinsic_score')
                contextual = link.get('contextual_score')
                total = link.get('total_score')

                if intrinsic is not None:
                    print(f"   📊 Intrinsic Score: {intrinsic:.2f}/10.0 (URL quality & context)")
                if contextual is not None:
                    print(f"   🎯 Contextual Score: {contextual:.3f} (BM25 relevance to query)")
                if total is not None:
                    print(f"   ⭐ Total Score: {total:.3f} (combined final score)")

                # Show extracted head data
                head_data = link.get("head_data", {})
                if head_data:
                    title = head_data.get("title", "No title")
                    description = head_data.get("meta", {}).get("description", "No description")

                    print(f"   📰 Title: {title[:60]}...")
                    if description:
                        print(f"   📝 Description: {description[:80]}...")

                    # Show extraction status
                    status = link.get("head_extraction_status", "unknown")
                    print(f"   ✅ Extraction Status: {status}")
        else:
            print(f"❌ Crawl failed: {result.error_message}")

# Run the example
if __name__ == "__main__":
    asyncio.run(extract_link_heads_example())
Copy
```

**Expected Output:**

```
✅ Successfully crawled: https://docs.python.org/3/
📄 Page title: 3.13.5 Documentation
🔗 Found 53 internal links
🌍 Found 1 external links
🧠 Links with head data extracted: 10

🏆 Top 3 Links with Full Scoring:

1. https://docs.python.org/3.15/
   Link Text: 'Python 3.15 (in development)...'
   📊 Intrinsic Score: 4.17/10.0 (URL quality & context)
   🎯 Contextual Score: 1.000 (BM25 relevance to query)
   ⭐ Total Score: 5.917 (combined final score)
   📰 Title: 3.15.0a0 Documentation...
   📝 Description: The official Python documentation...
   ✅ Extraction Status: valid
Copy
```

### 2.3 Configuration Deep Dive

The `LinkPreviewConfig` class supports these options:

```
from crawl4ai import LinkPreviewConfig

link_preview_config = LinkPreviewConfig(
    # BASIC SETTINGS
    verbose=True,                    # Show detailed logs (recommended for learning)

    # LINK FILTERING
    include_internal=True,           # Include same-domain links
    include_external=True,           # Include different-domain links
    max_links=50,                   # Maximum links to process (prevents overload)

    # PATTERN FILTERING
    include_patterns=[               # Only process links matching these patterns
        "*/docs/*",
        "*/api/*",
        "*/reference/*"
    ],
    exclude_patterns=[               # Skip links matching these patterns
        "*/login*",
        "*/admin*"
    ],

    # PERFORMANCE SETTINGS
    concurrency=10,                  # How many links to process simultaneously
    timeout=5,                      # Seconds to wait per link

    # RELEVANCE SCORING
    query="machine learning API",    # Query for BM25 contextual scoring
    score_threshold=0.3,            # Only include links above this score
)
Copy
```

### 2.4 Understanding the Three Score Types

Each extracted link gets three different scores:

#### 1. **Intrinsic Score (0-10)** - URL and Content Quality

Based on URL structure, link text quality, and page context:

```
# High intrinsic score indicators:
# ✅ Clean URL structure (docs.python.org/api/reference)
# ✅ Meaningful link text ("API Reference Guide")
# ✅ Relevant to page context
# ✅ Not buried deep in navigation

# Low intrinsic score indicators:
# ❌ Random URLs (site.com/x7f9g2h)
# ❌ No link text or generic text ("Click here")
# ❌ Unrelated to page content
Copy
```

#### 2. **Contextual Score (0-1)** - BM25 Relevance to Query

Only available when you provide a `query`. Uses BM25 algorithm against head content:

```
# Example: query = "machine learning tutorial"
# High contextual score: Link to "Complete Machine Learning Guide"
# Low contextual score: Link to "Privacy Policy"
Copy
```

#### 3. **Total Score** - Smart Combination

Intelligently combines intrinsic and contextual scores with fallbacks:

```
# When both scores available: (intrinsic * 0.3) + (contextual * 0.7)
# When only intrinsic: uses intrinsic score
# When only contextual: uses contextual score
# When neither: not calculated
Copy
```

### 2.5 Practical Use Cases

#### Use Case 1: Research Assistant

Find the most relevant documentation pages:

```
async def research_assistant():
    config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_external=True,
            include_patterns=["*/docs/*", "*/tutorial/*", "*/guide/*"],
            query="machine learning neural networks",
            max_links=20,
            score_threshold=0.5,  # Only high-relevance links
            verbose=True
        ),
        score_links=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://scikit-learn.org/", config=config)

        if result.success:
            # Get high-scoring links
            good_links = [link for link in result.links.get("internal", [])
                         if link.get("total_score", 0) > 0.7]

            print(f"🎯 Found {len(good_links)} highly relevant links:")
            for link in good_links[:5]:
                print(f"⭐ {link['total_score']:.3f} - {link['href']}")
                print(f"   {link.get('head_data', {}).get('title', 'No title')}")
Copy
```

#### Use Case 2: Content Discovery

Find all API endpoints and references:

```
async def api_discovery():
    config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_patterns=["*/api/*", "*/reference/*"],
            exclude_patterns=["*/deprecated/*"],
            max_links=100,
            concurrency=15,
            verbose=False  # Clean output
        ),
        score_links=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://docs.example-api.com/", config=config)

        if result.success:
            api_links = result.links.get("internal", [])

            # Group by endpoint type
            endpoints = {}
            for link in api_links:
                if link.get("head_data"):
                    title = link["head_data"].get("title", "")
                    if "GET" in title:
                        endpoints.setdefault("GET", []).append(link)
                    elif "POST" in title:
                        endpoints.setdefault("POST", []).append(link)

            for method, links in endpoints.items():
                print(f"\n{method} Endpoints ({len(links)}):")
                for link in links[:3]:
                    print(f"  • {link['href']}")
Copy
```

#### Use Case 3: Link Quality Analysis

Analyze website structure and content quality:

```
async def quality_analysis():
    config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            max_links=200,
            concurrency=20,
        ),
        score_links=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://your-website.com/", config=config)

        if result.success:
            links = result.links.get("internal", [])

            # Analyze intrinsic scores
            scores = [link.get('intrinsic_score', 0) for link in links]
            avg_score = sum(scores) / len(scores) if scores else 0

            print(f"📊 Link Quality Analysis:")
            print(f"   Average intrinsic score: {avg_score:.2f}/10.0")
            print(f"   High quality links (>7.0): {len([s for s in scores if s > 7.0])}")
            print(f"   Low quality links (<3.0): {len([s for s in scores if s < 3.0])}")

            # Find problematic links
            bad_links = [link for link in links
                        if link.get('intrinsic_score', 0) < 2.0]

            if bad_links:
                print(f"\n⚠️  Links needing attention:")
                for link in bad_links[:5]:
                    print(f"   {link['href']} (score: {link.get('intrinsic_score', 0):.1f})")
Copy
```

### 2.6 Performance Tips

1. **Start Small** : Begin with `max_links: 10` to understand the feature
2. **Use Patterns** : Filter with `include_patterns` to focus on relevant sections
3. **Adjust Concurrency** : Higher concurrency = faster but more resource usage
4. **Set Timeouts** : Use `timeout: 5` to prevent hanging on slow sites
5. **Use Score Thresholds** : Filter out low-quality links with `score_threshold`

### 2.7 Troubleshooting

**No head data extracted?**

```
# Check your configuration:
config = CrawlerRunConfig(
    link_preview_config=LinkPreviewConfig(
        verbose=True   # ← Enable to see what's happening
    )
)
Copy
```

**Scores showing as None?**

```
# Make sure scoring is enabled:
config = CrawlerRunConfig(
    score_links=True,  # ← Enable intrinsic scoring
    link_preview_config=LinkPreviewConfig(
        query="your search terms"  # ← For contextual scoring
    )
)
Copy
```

**Process taking too long?**

```
# Optimize performance:
link_preview_config = LinkPreviewConfig(
    max_links=20,      # ← Reduce number
    concurrency=10,    # ← Increase parallelism
    timeout=3,         # ← Shorter timeout
    include_patterns=["*/important/*"]  # ← Focus on key areas
)
Copy
```

---

## 3. Domain Filtering

Some websites contain hundreds of third-party or affiliate links. You can filter out certain domains at **crawl time** by configuring the crawler. The most relevant parameters in `CrawlerRunConfig` are:

- **`exclude_external_links`**: If`True` , discard any link pointing outside the root domain.
- **`exclude_social_media_domains`**: Provide a list of social media platforms (e.g.,`["facebook.com", "twitter.com"]`) to exclude from your crawl.
- **`exclude_social_media_links`**: If`True` , automatically skip known social platforms.
- **`exclude_domains`**: Provide a list of custom domains you want to exclude (e.g.,`["spammyads.com", "tracker.net"]`).

### 3.1 Example: Excluding External & Social Media Links

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def main():
    crawler_cfg = CrawlerRunConfig(
        exclude_external_links=True,          # No links outside primary domain
        exclude_social_media_links=True       # Skip recognized social media domains
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            "https://www.example.com",
            config=crawler_cfg
        )
        if result.success:
            print("[OK] Crawled:", result.url)
            print("Internal links count:", len(result.links.get("internal", [])))
            print("External links count:", len(result.links.get("external", [])))
            # Likely zero external links in this scenario
        else:
            print("[ERROR]", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

### 3.2 Example: Excluding Specific Domains

If you want to let external links in, but specifically exclude a domain (e.g., `suspiciousads.com`), do this:

```
crawler_cfg = CrawlerRunConfig(
    exclude_domains=["suspiciousads.com"]
)
Copy
```

This approach is handy when you still want external links but need to block certain sites you consider spammy.

---

## 4. Media Extraction

### 4.1 Accessing `result.media`

By default, Crawl4AI collects images, audio and video URLs it finds on the page. These are stored in `result.media`, a dictionary keyed by media type (e.g., `images`, `videos`, `audio`). **Note: Tables have been moved from`result.media["tables"]` to the new `result.tables` format for better organization and direct access.**
**Basic Example** :

```
if result.success:
    # Get images
    images_info = result.media.get("images", [])
    print(f"Found {len(images_info)} images in total.")
    for i, img in enumerate(images_info[:3]):  # Inspect just the first 3
        print(f"[Image {i}] URL: {img['src']}")
        print(f"           Alt text: {img.get('alt', '')}")
        print(f"           Score: {img.get('score')}")
        print(f"           Description: {img.get('desc', '')}\n")
Copy
```

**Structure Example** :

```
result.media = {
  "images": [
    {
      "src": "https://cdn.prod.website-files.com/.../Group%2089.svg",
      "alt": "coding school for kids",
      "desc": "Trial Class Degrees degrees All Degrees AI Degree Technology ...",
      "score": 3,
      "type": "image",
      "group_id": 0,
      "format": None,
      "width": None,
      "height": None
    },
    # ...
  ],
  "videos": [
    # Similar structure but with video-specific fields
  ],
  "audio": [
    # Similar structure but with audio-specific fields
  ],
}
Copy
```

Depending on your Crawl4AI version or scraping strategy, these dictionaries can include fields like:

- **`src`**: The media URL (e.g., image source)
- **`alt`**: The alt text for images (if present)
- **`desc`**: A snippet of nearby text or a short description (optional)
- **`score`**: A heuristic relevance score if you’re using content-scoring features
- **`width`**,**`height`**: If the crawler detects dimensions for the image/video
- **`type`**: Usually`"image"` , `"video"`, or `"audio"`
- **`group_id`**: If you’re grouping related media items, the crawler might assign an ID

With these details, you can easily filter out or focus on certain images (for instance, ignoring images with very low scores or a different domain), or gather metadata for analytics.

### 4.2 Excluding External Images

If you’re dealing with heavy pages or want to skip third-party images (advertisements, for example), you can turn on:

```
crawler_cfg = CrawlerRunConfig(
    exclude_external_images=True
)
Copy
```

This setting attempts to discard images from outside the primary domain, keeping only those from the site you’re crawling.

### 4.3 Additional Media Config

- **`screenshot`**: Set to`True` if you want a full-page screenshot stored as `base64` in `result.screenshot`.
- **`pdf`**: Set to`True` if you want a PDF version of the page in `result.pdf`.
- **`capture_mhtml`**: Set to`True` if you want an MHTML snapshot of the page in `result.mhtml`. This format preserves the entire web page with all its resources (CSS, images, scripts) in a single file, making it perfect for archiving or offline viewing.
- **`wait_for_images`**: If`True` , attempts to wait until images are fully loaded before final extraction.

#### Example: Capturing Page as MHTML

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    crawler_cfg = CrawlerRunConfig(
        capture_mhtml=True  # Enable MHTML capture
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com", config=crawler_cfg)

        if result.success and result.mhtml:
            # Save the MHTML snapshot to a file
            with open("example.mhtml", "w", encoding="utf-8") as f:
                f.write(result.mhtml)
            print("MHTML snapshot saved to example.mhtml")
        else:
            print("Failed to capture MHTML:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

The MHTML format is particularly useful because: - It captures the complete page state including all resources - It can be opened in most modern browsers for offline viewing - It preserves the page exactly as it appeared during crawling - It's a single file, making it easy to store and transfer

---

## 5. Putting It All Together: Link & Media Filtering

Here’s a combined example demonstrating how to filter out external links, skip certain domains, and exclude external images:

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def main():
    # Suppose we want to keep only internal links, remove certain domains,
    # and discard external images from the final crawl data.
    crawler_cfg = CrawlerRunConfig(
        exclude_external_links=True,
        exclude_domains=["spammyads.com"],
        exclude_social_media_links=True,   # skip Twitter, Facebook, etc.
        exclude_external_images=True,      # keep only images from main domain
        wait_for_images=True,             # ensure images are loaded
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://www.example.com", config=crawler_cfg)

        if result.success:
            print("[OK] Crawled:", result.url)

            # 1. Links
            in_links = result.links.get("internal", [])
            ext_links = result.links.get("external", [])
            print("Internal link count:", len(in_links))
            print("External link count:", len(ext_links))  # should be zero with exclude_external_links=True

            # 2. Images
            images = result.media.get("images", [])
            print("Images found:", len(images))

            # Let's see a snippet of these images
            for i, img in enumerate(images[:3]):
                print(f"  - {img['src']} (alt={img.get('alt','')}, score={img.get('score','N/A')})")
        else:
            print("[ERROR] Failed to crawl. Reason:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

## 6. Common Pitfalls & Tips

1. **Conflicting Flags** :

- `exclude_external_links=True` but then also specifying `exclude_social_media_links=True` is typically fine, but understand that the first setting already discards _all_ external links. The second becomes somewhat redundant.
- `exclude_external_images=True` but want to keep some external images? Currently no partial domain-based setting for images, so you might need a custom approach or hook logic.

2. **Relevancy Scores** :

- If your version of Crawl4AI or your scraping strategy includes an `img["score"]`, it’s typically a heuristic based on size, position, or content analysis. Evaluate carefully if you rely on it.

3. **Performance** :

- Excluding certain domains or external images can speed up your crawl, especially for large, media-heavy pages.
- If you want a “full” link map, do _not_ exclude them. Instead, you can post-filter in your own code.

4. **Social Media Lists** :

- `exclude_social_media_links=True` typically references an internal list of known social domains like Facebook, Twitter, LinkedIn, etc. If you need to add or remove from that list, look for library settings or a local config file (depending on your version).

---

**That’s it for Link & Media Analysis!** You’re now equipped to filter out unwanted sites and zero in on the images and videos that matter for your project.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/link-media/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/link-media/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/link-media/)

ESC to close

#### On this page

- [Excluding External Images](https://docs.crawl4ai.com/core/link-media/#excluding-external-images)
- [Excluding All Images](https://docs.crawl4ai.com/core/link-media/#excluding-all-images)
- [1. Link Extraction](https://docs.crawl4ai.com/core/link-media/#1-link-extraction)
- [1.1 result.links](https://docs.crawl4ai.com/core/link-media/#11-resultlinks)
- [2. Advanced Link Head Extraction & Scoring](https://docs.crawl4ai.com/core/link-media/#2-advanced-link-head-extraction-scoring)
- [2.1 Why Link Head Extraction?](https://docs.crawl4ai.com/core/link-media/#21-why-link-head-extraction)
- [2.2 Complete Working Example](https://docs.crawl4ai.com/core/link-media/#22-complete-working-example)
- [2.3 Configuration Deep Dive](https://docs.crawl4ai.com/core/link-media/#23-configuration-deep-dive)
- [2.4 Understanding the Three Score Types](https://docs.crawl4ai.com/core/link-media/#24-understanding-the-three-score-types)
- [1. Intrinsic Score (0-10) - URL and Content Quality](https://docs.crawl4ai.com/core/link-media/#1-intrinsic-score-0-10-url-and-content-quality)
- [2. Contextual Score (0-1) - BM25 Relevance to Query](https://docs.crawl4ai.com/core/link-media/#2-contextual-score-0-1-bm25-relevance-to-query)
- [3. Total Score - Smart Combination](https://docs.crawl4ai.com/core/link-media/#3-total-score-smart-combination)
- [2.5 Practical Use Cases](https://docs.crawl4ai.com/core/link-media/#25-practical-use-cases)
- [Use Case 1: Research Assistant](https://docs.crawl4ai.com/core/link-media/#use-case-1-research-assistant)
- [Use Case 2: Content Discovery](https://docs.crawl4ai.com/core/link-media/#use-case-2-content-discovery)
- [Use Case 3: Link Quality Analysis](https://docs.crawl4ai.com/core/link-media/#use-case-3-link-quality-analysis)
- [2.6 Performance Tips](https://docs.crawl4ai.com/core/link-media/#26-performance-tips)
- [2.7 Troubleshooting](https://docs.crawl4ai.com/core/link-media/#27-troubleshooting)
- [3. Domain Filtering](https://docs.crawl4ai.com/core/link-media/#3-domain-filtering)
- [3.1 Example: Excluding External & Social Media Links](https://docs.crawl4ai.com/core/link-media/#31-example-excluding-external-social-media-links)
- [3.2 Example: Excluding Specific Domains](https://docs.crawl4ai.com/core/link-media/#32-example-excluding-specific-domains)
- [4. Media Extraction](https://docs.crawl4ai.com/core/link-media/#4-media-extraction)
- [4.1 Accessing result.media](https://docs.crawl4ai.com/core/link-media/#41-accessing-resultmedia)
- [4.2 Excluding External Images](https://docs.crawl4ai.com/core/link-media/#42-excluding-external-images)
- [4.3 Additional Media Config](https://docs.crawl4ai.com/core/link-media/#43-additional-media-config)
- [Example: Capturing Page as MHTML](https://docs.crawl4ai.com/core/link-media/#example-capturing-page-as-mhtml)
- [5. Putting It All Together: Link & Media Filtering](https://docs.crawl4ai.com/core/link-media/#5-putting-it-all-together-link-media-filtering)
- [6. Common Pitfalls & Tips](https://docs.crawl4ai.com/core/link-media/#6-common-pitfalls-tips)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/quickstart

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/quickstart/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- Quick Start
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Getting Started with Crawl4AI](https://docs.crawl4ai.com/core/quickstart/#getting-started-with-crawl4ai)
- [1. Introduction](https://docs.crawl4ai.com/core/quickstart/#1-introduction)
- [2. Your First Crawl](https://docs.crawl4ai.com/core/quickstart/#2-your-first-crawl)
- [3. Basic Configuration (Light Introduction)](https://docs.crawl4ai.com/core/quickstart/#3-basic-configuration-light-introduction)
- [4. Generating Markdown Output](https://docs.crawl4ai.com/core/quickstart/#4-generating-markdown-output)
- [5. Simple Data Extraction (CSS-based)](https://docs.crawl4ai.com/core/quickstart/#5-simple-data-extraction-css-based)
- [6. Simple Data Extraction (LLM-based)](https://docs.crawl4ai.com/core/quickstart/#6-simple-data-extraction-llm-based)
- [7. Adaptive Crawling (New!)](https://docs.crawl4ai.com/core/quickstart/#7-adaptive-crawling-new)
- [8. Multi-URL Concurrency (Preview)](https://docs.crawl4ai.com/core/quickstart/#8-multi-url-concurrency-preview)
- [8. Dynamic Content Example](https://docs.crawl4ai.com/core/quickstart/#8-dynamic-content-example)
- [9. Next Steps](https://docs.crawl4ai.com/core/quickstart/#9-next-steps)

# Getting Started with Crawl4AI

Welcome to **Crawl4AI** , an open-source LLM-friendly Web Crawler & Scraper. In this tutorial, you’ll:

1. Run your **first crawl** using minimal configuration.
2. Generate **Markdown** output (and learn how it’s influenced by content filters).
3. Experiment with a simple **CSS-based extraction** strategy.
4. See a glimpse of **LLM-based extraction** (including open-source and closed-source model options).
5. Crawl a **dynamic** page that loads content via JavaScript.

---

## 1. Introduction

Crawl4AI provides:

- An asynchronous crawler, **`AsyncWebCrawler`**.
- Configurable browser and run settings via **`BrowserConfig`**and**`CrawlerRunConfig`**.
- Automatic HTML-to-Markdown conversion via **`DefaultMarkdownGenerator`**(supports optional filters).
- Multiple extraction strategies (LLM-based or “traditional” CSS/XPath-based).

By the end of this guide, you’ll have performed a basic crawl, generated Markdown, tried out two extraction strategies, and crawled a dynamic page that uses “Load More” buttons or JavaScript updates.

---

## 2. Your First Crawl

Here’s a minimal Python script that creates an **`AsyncWebCrawler`**, fetches a webpage, and prints the first 300 characters of its Markdown output:

```
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com")
        print(result.markdown[:300])  # Print first 300 chars

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**What’s happening?** - **`AsyncWebCrawler`**launches a headless browser (Chromium by default). - It fetches`https://example.com`. - Crawl4AI automatically converts the HTML into Markdown.
You now have a simple, working crawl!

---

## 3. Basic Configuration (Light Introduction)

Crawl4AI’s crawler can be heavily customized using two main classes:

1. **`BrowserConfig`**: Controls browser behavior (headless or full UI, user agent, JavaScript toggles, etc.).
2. **`CrawlerRunConfig`**: Controls how each crawl runs (caching, extraction, timeouts, hooking, etc.).
   Below is an example with minimal usage:

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    browser_conf = BrowserConfig(headless=True)  # or False to see the browser
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=run_conf
        )
        print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

> IMPORTANT: By default cache mode is set to `CacheMode.BYPASS` to have fresh content. Set `CacheMode.ENABLED` to enable caching.
> We’ll explore more advanced config in later tutorials (like enabling proxies, PDF output, multi-tab sessions, etc.). For now, just note how you pass these objects to manage crawling.

---

## 4. Generating Markdown Output

By default, Crawl4AI automatically generates Markdown from each crawled page. However, the exact output depends on whether you specify a **markdown generator** or **content filter**.

- **`result.markdown`**:
  The direct HTML-to-Markdown conversion.
- **`result.markdown.fit_markdown`**:
  The same content after applying any configured **content filter** (e.g., `PruningContentFilter`).

### Example: Using a Filter with `DefaultMarkdownGenerator`

```
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

md_generator = DefaultMarkdownGenerator(
    content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed")
)

config = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    markdown_generator=md_generator
)

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun("https://news.ycombinator.com", config=config)
    print("Raw Markdown length:", len(result.markdown.raw_markdown))
    print("Fit Markdown length:", len(result.markdown.fit_markdown))
Copy
```

**Note** : If you do **not** specify a content filter or markdown generator, you’ll typically see only the raw Markdown. `PruningContentFilter` may adds around `50ms` in processing time. We’ll dive deeper into these strategies in a dedicated **Markdown Generation** tutorial.

---

## 5. Simple Data Extraction (CSS-based)

Crawl4AI can also extract structured data (JSON) using CSS or XPath selectors. Below is a minimal CSS-based example:

> **New!** Crawl4AI now provides a powerful utility to automatically generate extraction schemas using LLM. This is a one-time cost that gives you a reusable schema for fast, LLM-free extractions:

```
from crawl4ai import JsonCssExtractionStrategy
from crawl4ai import LLMConfig

# Generate a schema (one-time cost)
html = "<div class='product'><h2>Gaming Laptop</h2><span class='price'>$999.99</span></div>"

# Using OpenAI (requires API token)
schema = JsonCssExtractionStrategy.generate_schema(
    html,
    llm_config = LLMConfig(provider="openai/gpt-4o",api_token="your-openai-token")  # Required for OpenAI
)

# Or using Ollama (open source, no token needed)
schema = JsonCssExtractionStrategy.generate_schema(
    html,
    llm_config = LLMConfig(provider="ollama/llama3.3", api_token=None)  # Not needed for Ollama
)

# Use the schema for fast, repeated extractions
strategy = JsonCssExtractionStrategy(schema)
Copy
```

For a complete guide on schema generation and advanced usage, see [No-LLM Extraction Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/).
Here's a basic extraction example:

```
import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy

async def main():
    schema = {
        "name": "Example Items",
        "baseSelector": "div.item",
        "fields": [
            {"name": "title", "selector": "h2", "type": "text"},
            {"name": "link", "selector": "a", "type": "attribute", "attribute": "href"}
        ]
    }

    raw_html = "<div class='item'><h2>Item 1</h2><a href='https://example.com/item1'>Link 1</a></div>"

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="raw://" + raw_html,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=JsonCssExtractionStrategy(schema)
            )
        )
        # The JSON output is stored in 'extracted_content'
        data = json.loads(result.extracted_content)
        print(data)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Why is this helpful?** - Great for repetitive page structures (e.g., item listings, articles). - No AI usage or costs. - The crawler returns a JSON string you can parse or store.

> Tips: You can pass raw HTML to the crawler instead of a URL. To do so, prefix the HTML with `raw://`.

---

## 6. Simple Data Extraction (LLM-based)

For more complex or irregular pages, a language model can parse text intelligently into a structure you define. Crawl4AI supports **open-source** or **closed-source** providers:

- **Open-Source Models** (e.g., `ollama/llama3.3`, `no_token`)
- **OpenAI Models** (e.g., `openai/gpt-4`, requires `api_token`)
- Or any provider supported by the underlying library

Below is an example using **open-source** style (no token) and closed-source:

```
import os
import json
import asyncio
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig
from crawl4ai import LLMExtractionStrategy

class OpenAIModelFee(BaseModel):
    model_name: str = Field(..., description="Name of the OpenAI model.")
    input_fee: str = Field(..., description="Fee for input token for the OpenAI model.")
    output_fee: str = Field(
        ..., description="Fee for output token for the OpenAI model."
    )

async def extract_structured_data_using_llm(
    provider: str, api_token: str = None, extra_headers: Dict[str, str] = None
):
    print(f"\n--- Extracting Structured Data with {provider} ---")

    if api_token is None and provider != "ollama":
        print(f"API token is required for {provider}. Skipping this example.")
        return

    browser_config = BrowserConfig(headless=True)

    extra_args = {"temperature": 0, "top_p": 0.9, "max_tokens": 2000}
    if extra_headers:
        extra_args["extra_headers"] = extra_headers

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=1,
        page_timeout=80000,
        extraction_strategy=LLMExtractionStrategy(
            llm_config = LLMConfig(provider=provider,api_token=api_token),
            schema=OpenAIModelFee.model_json_schema(),
            extraction_type="schema",
            instruction="""From the crawled content, extract all mentioned model names along with their fees for input and output tokens.
            Do not miss any models in the entire content.""",
            extra_args=extra_args,
        ),
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://openai.com/api/pricing/", config=crawler_config
        )
        print(result.extracted_content)

if __name__ == "__main__":

    asyncio.run(
        extract_structured_data_using_llm(
            provider="openai/gpt-4o", api_token=os.getenv("OPENAI_API_KEY")
        )
    )
Copy
```

**What’s happening?** - We define a Pydantic schema (`PricingInfo`) describing the fields we want. - The LLM extraction strategy uses that schema and your instructions to transform raw text into structured JSON. - Depending on the **provider** and **api_token** , you can use local models or a remote API.

---

## 7. Adaptive Crawling (New!)

Crawl4AI now includes intelligent adaptive crawling that automatically determines when sufficient information has been gathered. Here's a quick example:

```
import asyncio
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler

async def adaptive_example():
    async with AsyncWebCrawler() as crawler:
        adaptive = AdaptiveCrawler(crawler)

        # Start adaptive crawling
        result = await adaptive.digest(
            start_url="https://docs.python.org/3/",
            query="async context managers"
        )

        # View results
        adaptive.print_stats()
        print(f"Crawled {len(result.crawled_urls)} pages")
        print(f"Achieved {adaptive.confidence:.0%} confidence")

if __name__ == "__main__":
    asyncio.run(adaptive_example())
Copy
```

**What's special about adaptive crawling?** - **Automatic stopping** : Stops when sufficient information is gathered - **Intelligent link selection** : Follows only relevant links - **Confidence scoring** : Know how complete your information is
[Learn more about Adaptive Crawling →](https://docs.crawl4ai.com/core/adaptive-crawling/)

---

## 8. Multi-URL Concurrency (Preview)

If you need to crawl multiple URLs in **parallel** , you can use `arun_many()`. By default, Crawl4AI employs a **MemoryAdaptiveDispatcher** , automatically adjusting concurrency based on system resources. Here’s a quick glimpse:

```
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def quick_parallel_example():
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3"
    ]

    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        stream=True  # Enable streaming mode
    )

    async with AsyncWebCrawler() as crawler:
        # Stream results as they complete
        async for result in await crawler.arun_many(urls, config=run_conf):
            if result.success:
                print(f"[OK] {result.url}, length: {len(result.markdown.raw_markdown)}")
            else:
                print(f"[ERROR] {result.url} => {result.error_message}")

        # Or get all results at once (default behavior)
        run_conf = run_conf.clone(stream=False)
        results = await crawler.arun_many(urls, config=run_conf)
        for res in results:
            if res.success:
                print(f"[OK] {res.url}, length: {len(res.markdown.raw_markdown)}")
            else:
                print(f"[ERROR] {res.url} => {res.error_message}")

if __name__ == "__main__":
    asyncio.run(quick_parallel_example())
Copy
```

The example above shows two ways to handle multiple URLs: 1. **Streaming mode** (`stream=True`): Process results as they become available using `async for` 2. **Batch mode** (`stream=False`): Wait for all results to complete
For more advanced concurrency (e.g., a **semaphore-based** approach, **adaptive memory usage throttling** , or customized rate limiting), see [Advanced Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/).

---

## 8. Dynamic Content Example

Some sites require multiple “page clicks” or dynamic JavaScript updates. Below is an example showing how to **click** a “Next Page” button and wait for new commits to load on GitHub, using **`BrowserConfig`**and**`CrawlerRunConfig`**:

```
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy

async def extract_structured_data_using_css_extractor():
    print("\n--- Using JsonCssExtractionStrategy for Fast Structured Output ---")
    schema = {
        "name": "KidoCode Courses",
        "baseSelector": "section.charge-methodology .w-tab-content > div",
        "fields": [
            {
                "name": "section_title",
                "selector": "h3.heading-50",
                "type": "text",
            },
            {
                "name": "section_description",
                "selector": ".charge-content",
                "type": "text",
            },
            {
                "name": "course_name",
                "selector": ".text-block-93",
                "type": "text",
            },
            {
                "name": "course_description",
                "selector": ".course-content-text",
                "type": "text",
            },
            {
                "name": "course_icon",
                "selector": ".image-92",
                "type": "attribute",
                "attribute": "src",
            },
        ],
    }

    browser_config = BrowserConfig(headless=True, java_script_enabled=True)

    js_click_tabs = """
    (async () => {
        const tabs = document.querySelectorAll("section.charge-methodology .tabs-menu-3 > div");
        for(let tab of tabs) {
            tab.scrollIntoView();
            tab.click();
            await new Promise(r => setTimeout(r, 500));
        }
    })();
    """

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=JsonCssExtractionStrategy(schema),
        js_code=[js_click_tabs],
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://www.kidocode.com/degrees/technology", config=crawler_config
        )

        companies = json.loads(result.extracted_content)
        print(f"Successfully extracted {len(companies)} companies")
        print(json.dumps(companies[0], indent=2))

async def main():
    await extract_structured_data_using_css_extractor()

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key Points** :

- **`BrowserConfig(headless=False)`**: We want to watch it click “Next Page.”
- **`CrawlerRunConfig(...)`**: We specify the extraction strategy, pass`session_id` to reuse the same page.
- **`js_code`**and**`wait_for`**are used for subsequent pages (`page > 0`) to click the “Next” button and wait for new commits to load.
- **`js_only=True`**indicates we’re not re-navigating but continuing the existing session.
- Finally, we call `kill_session()` to clean up the page and browser session.

---

## 9. Next Steps

Congratulations! You have:

1. Performed a basic crawl and printed Markdown.
2. Used **content filters** with a markdown generator.
3. Extracted JSON via **CSS** or **LLM** strategies.
4. Handled **dynamic** pages with JavaScript triggers.

If you’re ready for more, check out:

- **Installation** : A deeper dive into advanced installs, Docker usage (experimental), or optional dependencies.
- **Hooks & Auth**: Learn how to run custom JavaScript or handle logins with cookies, local storage, etc.
- **Deployment** : Explore ephemeral testing in Docker or plan for the upcoming stable Docker release.
- **Browser Management** : Delve into user simulation, stealth modes, and concurrency best practices.

Crawl4AI is a powerful, flexible tool. Enjoy building out your scrapers, data pipelines, or AI-driven extraction flows. Happy crawling!
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/quickstart/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/quickstart/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/quickstart/)

ESC to close

#### On this page

- [1. Introduction](https://docs.crawl4ai.com/core/quickstart/#1-introduction)
- [2. Your First Crawl](https://docs.crawl4ai.com/core/quickstart/#2-your-first-crawl)
- [3. Basic Configuration (Light Introduction)](https://docs.crawl4ai.com/core/quickstart/#3-basic-configuration-light-introduction)
- [4. Generating Markdown Output](https://docs.crawl4ai.com/core/quickstart/#4-generating-markdown-output)
- [Example: Using a Filter with DefaultMarkdownGenerator](https://docs.crawl4ai.com/core/quickstart/#example-using-a-filter-with-defaultmarkdowngenerator)
- [5. Simple Data Extraction (CSS-based)](https://docs.crawl4ai.com/core/quickstart/#5-simple-data-extraction-css-based)
- [6. Simple Data Extraction (LLM-based)](https://docs.crawl4ai.com/core/quickstart/#6-simple-data-extraction-llm-based)
- [7. Adaptive Crawling (New!)](https://docs.crawl4ai.com/core/quickstart/#7-adaptive-crawling-new)
- [8. Multi-URL Concurrency (Preview)](https://docs.crawl4ai.com/core/quickstart/#8-multi-url-concurrency-preview)
- [8. Dynamic Content Example](https://docs.crawl4ai.com/core/quickstart/#8-dynamic-content-example)
- [9. Next Steps](https://docs.crawl4ai.com/core/quickstart/#9-next-steps)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/simple-crawling

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/simple-crawling/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - Simple Crawling
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/#simple-crawling)
- [Basic Usage](https://docs.crawl4ai.com/core/simple-crawling/#basic-usage)
- [Understanding the Response](https://docs.crawl4ai.com/core/simple-crawling/#understanding-the-response)
- [Adding Basic Options](https://docs.crawl4ai.com/core/simple-crawling/#adding-basic-options)
- [Handling Errors](https://docs.crawl4ai.com/core/simple-crawling/#handling-errors)
- [Logging and Debugging](https://docs.crawl4ai.com/core/simple-crawling/#logging-and-debugging)
- [Complete Example](https://docs.crawl4ai.com/core/simple-crawling/#complete-example)

# Simple Crawling

This guide covers the basics of web crawling with Crawl4AI. You'll learn how to set up a crawler, make your first request, and understand the response.

## Basic Usage

Set up a simple crawl using `BrowserConfig` and `CrawlerRunConfig`:

```
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def main():
    browser_config = BrowserConfig()  # Default browser configuration
    run_config = CrawlerRunConfig()   # Default crawl run configuration

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=run_config
        )
        print(result.markdown)  # Print clean markdown content

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

## Understanding the Response

The `arun()` method returns a `CrawlResult` object with several useful properties. Here's a quick overview (see [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/) for complete details):

```
config = CrawlerRunConfig(
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.6),
        options={"ignore_links": True}
    )
)

result = await crawler.arun(
    url="https://example.com",
    config=config
)

# Different content formats
print(result.html)         # Raw HTML
print(result.cleaned_html) # Cleaned HTML
print(result.markdown.raw_markdown) # Raw markdown from cleaned html
print(result.markdown.fit_markdown) # Most relevant content in markdown

# Check success status
print(result.success)      # True if crawl succeeded
print(result.status_code)  # HTTP status code (e.g., 200, 404)

# Access extracted media and links
print(result.media)        # Dictionary of found media (images, videos, audio)
print(result.links)        # Dictionary of internal and external links
Copy
```

## Adding Basic Options

Customize your crawl using `CrawlerRunConfig`:

```
run_config = CrawlerRunConfig(
    word_count_threshold=10,        # Minimum words per content block
    exclude_external_links=True,    # Remove external links
    remove_overlay_elements=True,   # Remove popups/modals
    process_iframes=True           # Process iframe content
)

result = await crawler.arun(
    url="https://example.com",
    config=run_config
)
Copy
```

## Handling Errors

Always check if the crawl was successful:

```
run_config = CrawlerRunConfig()
result = await crawler.arun(url="https://example.com", config=run_config)

if not result.success:
    print(f"Crawl failed: {result.error_message}")
    print(f"Status code: {result.status_code}")
Copy
```

## Logging and Debugging

Enable verbose logging in `BrowserConfig`:

```
browser_config = BrowserConfig(verbose=True)

async with AsyncWebCrawler(config=browser_config) as crawler:
    run_config = CrawlerRunConfig()
    result = await crawler.arun(url="https://example.com", config=run_config)
Copy
```

## Complete Example

Here's a more comprehensive example demonstrating common usage patterns:

```
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    browser_config = BrowserConfig(verbose=True)
    run_config = CrawlerRunConfig(
        # Content filtering
        word_count_threshold=10,
        excluded_tags=['form', 'header'],
        exclude_external_links=True,

        # Content processing
        process_iframes=True,
        remove_overlay_elements=True,

        # Cache control
        cache_mode=CacheMode.ENABLED  # Use cache if available
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=run_config
        )

        if result.success:
            # Print clean content
            print("Content:", result.markdown[:500])  # First 500 chars

            # Process images
            for image in result.media["images"]:
                print(f"Found image: {image['src']}")

            # Process links
            for link in result.links["internal"]:
                print(f"Internal link: {link['href']}")

        else:
            print(f"Crawl failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/simple-crawling/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/simple-crawling/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/simple-crawling/)

ESC to close

#### On this page

- [Basic Usage](https://docs.crawl4ai.com/core/simple-crawling/#basic-usage)
- [Understanding the Response](https://docs.crawl4ai.com/core/simple-crawling/#understanding-the-response)
- [Adding Basic Options](https://docs.crawl4ai.com/core/simple-crawling/#adding-basic-options)
- [Handling Errors](https://docs.crawl4ai.com/core/simple-crawling/#handling-errors)
- [Logging and Debugging](https://docs.crawl4ai.com/core/simple-crawling/#logging-and-debugging)
- [Complete Example](https://docs.crawl4ai.com/core/simple-crawling/#complete-example)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/extraction/clustring-strategies

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/extraction/clustring-strategies/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - Clustering Strategies
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Cosine Strategy](https://docs.crawl4ai.com/extraction/clustring-strategies/#cosine-strategy)
- [How It Works](https://docs.crawl4ai.com/extraction/clustring-strategies/#how-it-works)
- [Basic Usage](https://docs.crawl4ai.com/extraction/clustring-strategies/#basic-usage)
- [Configuration Options](https://docs.crawl4ai.com/extraction/clustring-strategies/#configuration-options)
- [Use Cases](https://docs.crawl4ai.com/extraction/clustring-strategies/#use-cases)
- [Advanced Features](https://docs.crawl4ai.com/extraction/clustring-strategies/#advanced-features)
- [Best Practices](https://docs.crawl4ai.com/extraction/clustring-strategies/#best-practices)
- [Error Handling](https://docs.crawl4ai.com/extraction/clustring-strategies/#error-handling)

# Cosine Strategy

The Cosine Strategy in Crawl4AI uses similarity-based clustering to identify and extract relevant content sections from web pages. This strategy is particularly useful when you need to find and extract content based on semantic similarity rather than structural patterns.

## How It Works

The Cosine Strategy: 1. Breaks down page content into meaningful chunks 2. Converts text into vector representations 3. Calculates similarity between chunks 4. Clusters similar content together 5. Ranks and filters content based on relevance

## Basic Usage

```
from crawl4ai import CosineStrategy

strategy = CosineStrategy(
    semantic_filter="product reviews",    # Target content type
    word_count_threshold=10,             # Minimum words per cluster
    sim_threshold=0.3                    # Similarity threshold
)

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(
        url="https://example.com/reviews",
        extraction_strategy=strategy
    )

    content = result.extracted_content
Copy
```

## Configuration Options

### Core Parameters

```
CosineStrategy(
    # Content Filtering
    semantic_filter: str = None,       # Keywords/topic for content filtering
    word_count_threshold: int = 10,    # Minimum words per cluster
    sim_threshold: float = 0.3,        # Similarity threshold (0.0 to 1.0)

    # Clustering Parameters
    max_dist: float = 0.2,            # Maximum distance for clustering
    linkage_method: str = 'ward',      # Clustering linkage method
    top_k: int = 3,                   # Number of top categories to extract

    # Model Configuration
    model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',  # Embedding model

    verbose: bool = False             # Enable logging
)
Copy
```

### Parameter Details

1. **semantic_filter** - Sets the target topic or content type - Use keywords relevant to your desired content - Example: "technical specifications", "user reviews", "pricing information"
2. **sim_threshold** - Controls how similar content must be to be grouped together - Higher values (e.g., 0.8) mean stricter matching - Lower values (e.g., 0.3) allow more variation

```
# Strict matching
strategy = CosineStrategy(sim_threshold=0.8)

# Loose matching
strategy = CosineStrategy(sim_threshold=0.3)
Copy
```

3. **word_count_threshold** - Filters out short content blocks - Helps eliminate noise and irrelevant content

```
# Only consider substantial paragraphs
strategy = CosineStrategy(word_count_threshold=50)
Copy
```

4. **top_k** - Number of top content clusters to return - Higher values return more diverse content

```
# Get top 5 most relevant content clusters
strategy = CosineStrategy(top_k=5)
Copy
```

## Use Cases

### 1. Article Content Extraction

```
strategy = CosineStrategy(
    semantic_filter="main article content",
    word_count_threshold=100,  # Longer blocks for articles
    top_k=1                   # Usually want single main content
)

result = await crawler.arun(
    url="https://example.com/blog/post",
    extraction_strategy=strategy
)
Copy
```

### 2. Product Review Analysis

```
strategy = CosineStrategy(
    semantic_filter="customer reviews and ratings",
    word_count_threshold=20,   # Reviews can be shorter
    top_k=10,                 # Get multiple reviews
    sim_threshold=0.4         # Allow variety in review content
)
Copy
```

### 3. Technical Documentation

```
strategy = CosineStrategy(
    semantic_filter="technical specifications documentation",
    word_count_threshold=30,
    sim_threshold=0.6,        # Stricter matching for technical content
    max_dist=0.3             # Allow related technical sections
)
Copy
```

## Advanced Features

### Custom Clustering

```
strategy = CosineStrategy(
    linkage_method='complete',  # Alternative clustering method
    max_dist=0.4,              # Larger clusters
    model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'  # Multilingual support
)
Copy
```

### Content Filtering Pipeline

```
strategy = CosineStrategy(
    semantic_filter="pricing plans features",
    word_count_threshold=15,
    sim_threshold=0.5,
    top_k=3
)

async def extract_pricing_features(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            extraction_strategy=strategy
        )

        if result.success:
            content = json.loads(result.extracted_content)
            return {
                'pricing_features': content,
                'clusters': len(content),
                'similarity_scores': [item['score'] for item in content]
            }
Copy
```

## Best Practices

1. **Adjust Thresholds Iteratively** - Start with default values - Adjust based on results - Monitor clustering quality
2. **Choose Appropriate Word Count Thresholds** - Higher for articles (100+) - Lower for reviews/comments (20+) - Medium for product descriptions (50+)
3. **Optimize Performance**

```
strategy = CosineStrategy(
    word_count_threshold=10,  # Filter early
    top_k=5,                 # Limit results
    verbose=True             # Monitor performance
)
Copy
```

4. **Handle Different Content Types**

```
# For mixed content pages
strategy = CosineStrategy(
    semantic_filter="product features",
    sim_threshold=0.4,      # More flexible matching
    max_dist=0.3,          # Larger clusters
    top_k=3                # Multiple relevant sections
)
Copy
```

## Error Handling

```
try:
    result = await crawler.arun(
        url="https://example.com",
        extraction_strategy=strategy
    )

    if result.success:
        content = json.loads(result.extracted_content)
        if not content:
            print("No relevant content found")
    else:
        print(f"Extraction failed: {result.error_message}")

except Exception as e:
    print(f"Error during extraction: {str(e)}")
Copy
```

The Cosine Strategy is particularly effective when: - Content structure is inconsistent - You need semantic understanding - You want to find similar content blocks - Structure-based extraction (CSS/XPath) isn't reliable
It works well with other strategies and can be used as a pre-processing step for LLM-based extraction.
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/extraction/clustring-strategies/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/extraction/clustring-strategies/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/extraction/clustring-strategies/)

ESC to close

#### On this page

- [How It Works](https://docs.crawl4ai.com/extraction/clustring-strategies/#how-it-works)
- [Basic Usage](https://docs.crawl4ai.com/extraction/clustring-strategies/#basic-usage)
- [Configuration Options](https://docs.crawl4ai.com/extraction/clustring-strategies/#configuration-options)
- [Core Parameters](https://docs.crawl4ai.com/extraction/clustring-strategies/#core-parameters)
- [Parameter Details](https://docs.crawl4ai.com/extraction/clustring-strategies/#parameter-details)
- [Use Cases](https://docs.crawl4ai.com/extraction/clustring-strategies/#use-cases)
- [1. Article Content Extraction](https://docs.crawl4ai.com/extraction/clustring-strategies/#1-article-content-extraction)
- [2. Product Review Analysis](https://docs.crawl4ai.com/extraction/clustring-strategies/#2-product-review-analysis)
- [3. Technical Documentation](https://docs.crawl4ai.com/extraction/clustring-strategies/#3-technical-documentation)
- [Advanced Features](https://docs.crawl4ai.com/extraction/clustring-strategies/#advanced-features)
- [Custom Clustering](https://docs.crawl4ai.com/extraction/clustring-strategies/#custom-clustering)
- [Content Filtering Pipeline](https://docs.crawl4ai.com/extraction/clustring-strategies/#content-filtering-pipeline)
- [Best Practices](https://docs.crawl4ai.com/extraction/clustring-strategies/#best-practices)
- [Error Handling](https://docs.crawl4ai.com/extraction/clustring-strategies/#error-handling)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/extraction/chunking

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/extraction/chunking/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - Chunking
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Chunking Strategies](https://docs.crawl4ai.com/extraction/chunking/#chunking-strategies)
- [Why Use Chunking?](https://docs.crawl4ai.com/extraction/chunking/#why-use-chunking)
- [Methods of Chunking](https://docs.crawl4ai.com/extraction/chunking/#methods-of-chunking)
- [Combining Chunking with Cosine Similarity](https://docs.crawl4ai.com/extraction/chunking/#combining-chunking-with-cosine-similarity)

# Chunking Strategies

Chunking strategies are critical for dividing large texts into manageable parts, enabling effective content processing and extraction. These strategies are foundational in cosine similarity-based extraction techniques, which allow users to retrieve only the most relevant chunks of content for a given query. Additionally, they facilitate direct integration into RAG (Retrieval-Augmented Generation) systems for structured and scalable workflows.

### Why Use Chunking?

1. **Cosine Similarity and Query Relevance** : Prepares chunks for semantic similarity analysis. 2. **RAG System Integration** : Seamlessly processes and stores chunks for retrieval. 3. **Structured Processing** : Allows for diverse segmentation methods, such as sentence-based, topic-based, or windowed approaches.

### Methods of Chunking

#### 1. Regex-Based Chunking

Splits text based on regular expression patterns, useful for coarse segmentation.
**Code Example** :

```
class RegexChunking:
    def __init__(self, patterns=None):
        self.patterns = patterns or [r'\n\n']  # Default pattern for paragraphs

    def chunk(self, text):
        paragraphs = [text]
        for pattern in self.patterns:
            paragraphs = [seg for p in paragraphs for seg in re.split(pattern, p)]
        return paragraphs

# Example Usage
text = """This is the first paragraph.

This is the second paragraph."""
chunker = RegexChunking()
print(chunker.chunk(text))
Copy
```

#### 2. Sentence-Based Chunking

Divides text into sentences using NLP tools, ideal for extracting meaningful statements.
**Code Example** :

```
from nltk.tokenize import sent_tokenize

class NlpSentenceChunking:
    def chunk(self, text):
        sentences = sent_tokenize(text)
        return [sentence.strip() for sentence in sentences]

# Example Usage
text = "This is sentence one. This is sentence two."
chunker = NlpSentenceChunking()
print(chunker.chunk(text))
Copy
```

#### 3. Topic-Based Segmentation

Uses algorithms like TextTiling to create topic-coherent chunks.
**Code Example** :

```
from nltk.tokenize import TextTilingTokenizer

class TopicSegmentationChunking:
    def __init__(self):
        self.tokenizer = TextTilingTokenizer()

    def chunk(self, text):
        return self.tokenizer.tokenize(text)

# Example Usage
text = """This is an introduction.
This is a detailed discussion on the topic."""
chunker = TopicSegmentationChunking()
print(chunker.chunk(text))
Copy
```

#### 4. Fixed-Length Word Chunking

Segments text into chunks of a fixed word count.
**Code Example** :

```
class FixedLengthWordChunking:
    def __init__(self, chunk_size=100):
        self.chunk_size = chunk_size

    def chunk(self, text):
        words = text.split()
        return [' '.join(words[i:i + self.chunk_size]) for i in range(0, len(words), self.chunk_size)]

# Example Usage
text = "This is a long text with many words to be chunked into fixed sizes."
chunker = FixedLengthWordChunking(chunk_size=5)
print(chunker.chunk(text))
Copy
```

#### 5. Sliding Window Chunking

Generates overlapping chunks for better contextual coherence.
**Code Example** :

```
class SlidingWindowChunking:
    def __init__(self, window_size=100, step=50):
        self.window_size = window_size
        self.step = step

    def chunk(self, text):
        words = text.split()
        chunks = []
        for i in range(0, len(words) - self.window_size + 1, self.step):
            chunks.append(' '.join(words[i:i + self.window_size]))
        return chunks

# Example Usage
text = "This is a long text to demonstrate sliding window chunking."
chunker = SlidingWindowChunking(window_size=5, step=2)
print(chunker.chunk(text))
Copy
```

### Combining Chunking with Cosine Similarity

To enhance the relevance of extracted content, chunking strategies can be paired with cosine similarity techniques. Here’s an example workflow:
**Code Example** :

```
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class CosineSimilarityExtractor:
    def __init__(self, query):
        self.query = query
        self.vectorizer = TfidfVectorizer()

    def find_relevant_chunks(self, chunks):
        vectors = self.vectorizer.fit_transform([self.query] + chunks)
        similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()
        return [(chunks[i], similarities[i]) for i in range(len(chunks))]

# Example Workflow
text = """This is a sample document. It has multiple sentences.
We are testing chunking and similarity."""

chunker = SlidingWindowChunking(window_size=5, step=3)
chunks = chunker.chunk(text)
query = "testing chunking"
extractor = CosineSimilarityExtractor(query)
relevant_chunks = extractor.find_relevant_chunks(chunks)

print(relevant_chunks)
Copy
```

Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/extraction/chunking/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/extraction/chunking/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/extraction/chunking/)

ESC to close

#### On this page

- [Why Use Chunking?](https://docs.crawl4ai.com/extraction/chunking/#why-use-chunking)
- [Methods of Chunking](https://docs.crawl4ai.com/extraction/chunking/#methods-of-chunking)
- [1. Regex-Based Chunking](https://docs.crawl4ai.com/extraction/chunking/#1-regex-based-chunking)
- [2. Sentence-Based Chunking](https://docs.crawl4ai.com/extraction/chunking/#2-sentence-based-chunking)
- [3. Topic-Based Segmentation](https://docs.crawl4ai.com/extraction/chunking/#3-topic-based-segmentation)
- [4. Fixed-Length Word Chunking](https://docs.crawl4ai.com/extraction/chunking/#4-fixed-length-word-chunking)
- [5. Sliding Window Chunking](https://docs.crawl4ai.com/extraction/chunking/#5-sliding-window-chunking)
- [Combining Chunking with Cosine Similarity](https://docs.crawl4ai.com/extraction/chunking/#combining-chunking-with-cosine-similarity)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/core/url-seeding

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/core/url-seeding/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - URL Seeding
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [URL Seeding: The Smart Way to Crawl at Scale](https://docs.crawl4ai.com/core/url-seeding/#url-seeding-the-smart-way-to-crawl-at-scale)
- [Why URL Seeding?](https://docs.crawl4ai.com/core/url-seeding/#why-url-seeding)
- [Your First URL Seeding Adventure](https://docs.crawl4ai.com/core/url-seeding/#your-first-url-seeding-adventure)
- [Understanding the URL Seeder](https://docs.crawl4ai.com/core/url-seeding/#understanding-the-url-seeder)
- [Smart Filtering with BM25 Scoring](https://docs.crawl4ai.com/core/url-seeding/#smart-filtering-with-bm25-scoring)
- [Scaling Up: Multiple Domains](https://docs.crawl4ai.com/core/url-seeding/#scaling-up-multiple-domains)
- [Advanced Integration Patterns](https://docs.crawl4ai.com/core/url-seeding/#advanced-integration-patterns)
- [Best Practices & Tips](https://docs.crawl4ai.com/core/url-seeding/#best-practices-tips)
- [Quick Reference](https://docs.crawl4ai.com/core/url-seeding/#quick-reference)
- [Conclusion](https://docs.crawl4ai.com/core/url-seeding/#conclusion)

# URL Seeding: The Smart Way to Crawl at Scale

## Why URL Seeding?

Web crawling comes in different flavors, each with its own strengths. Let's understand when to use URL seeding versus deep crawling.

### Deep Crawling: Real-Time Discovery

Deep crawling is perfect when you need: - **Fresh, real-time data** - discovering pages as they're created - **Dynamic exploration** - following links based on content - **Selective extraction** - stopping when you find what you need

```
# Deep crawling example: Explore a website dynamically
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

async def deep_crawl_example():
    # Configure a 2-level deep crawl
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,           # Crawl 2 levels deep
            include_external=False, # Stay within domain
            max_pages=50           # Limit for efficiency
        ),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        # Start crawling and follow links dynamically
        results = await crawler.arun("https://example.com", config=config)

        print(f"Discovered and crawled {len(results)} pages")
        for result in results[:3]:
            print(f"Found: {result.url} at depth {result.metadata.get('depth', 0)}")

asyncio.run(deep_crawl_example())
Copy
```

### URL Seeding: Bulk Discovery

URL seeding shines when you want: - **Comprehensive coverage** - get thousands of URLs in seconds - **Bulk processing** - filter before crawling - **Resource efficiency** - know exactly what you'll crawl

```
# URL seeding example: Analyze all documentation
from crawl4ai import AsyncUrlSeeder, SeedingConfig

seeder = AsyncUrlSeeder()
config = SeedingConfig(
    source="sitemap",
    extract_head=True,
    pattern="*/docs/*"
)

# Get ALL documentation URLs instantly
urls = await seeder.urls("example.com", config)
# 1000+ URLs discovered in seconds!
Copy
```

### The Trade-offs

| Aspect             | Deep Crawling               | URL Seeding                       |
| ------------------ | --------------------------- | --------------------------------- |
| **Coverage**       | Discovers pages dynamically | Gets most existing URLs instantly |
| **Freshness**      | Finds brand new pages       | May miss very recent pages        |
| **Speed**          | Slower, page by page        | Extremely fast bulk discovery     |
| **Resource Usage** | Higher - crawls to discover | Lower - discovers then crawls     |
| **Control**        | Can stop mid-process        | Pre-filters before crawling       |

### When to Use Each

**Choose Deep Crawling when:** - You need the absolute latest content - You're searching for specific information - The site structure is unknown or dynamic - You want to stop as soon as you find what you need
**Choose URL Seeding when:** - You need to analyze large portions of a site - You want to filter URLs before crawling - You're doing comparative analysis - You need to optimize resource usage
The magic happens when you understand both approaches and choose the right tool for your task. Sometimes, you might even combine them - use URL seeding for bulk discovery, then deep crawl specific sections for the latest updates.

## Your First URL Seeding Adventure

Let's see the magic in action. We'll discover blog posts about Python, filter for tutorials, and crawl only those pages.

```
import asyncio
from crawl4ai import AsyncUrlSeeder, AsyncWebCrawler, SeedingConfig, CrawlerRunConfig

async def smart_blog_crawler():
    # Step 1: Create our URL discoverer
    seeder = AsyncUrlSeeder()

    # Step 2: Configure discovery - let's find all blog posts
    config = SeedingConfig(
        source="sitemap+cc",      # Use the website's sitemap+cc
        pattern="*/courses/*",    # Only courses related posts
        extract_head=True,          # Get page metadata
        max_urls=100               # Limit for this example
    )

    # Step 3: Discover URLs from the Python blog
    print("🔍 Discovering course posts...")
    urls = await seeder.urls("realpython.com", config)
    print(f"✅ Found {len(urls)} course posts")

    # Step 4: Filter for Python tutorials (using metadata!)
    tutorials = [
        url for url in urls
        if url["status"] == "valid" and
        any(keyword in str(url["head_data"]).lower()
            for keyword in ["tutorial", "guide", "how to"])
    ]
    print(f"📚 Filtered to {len(tutorials)} tutorials")

    # Step 5: Show what we found
    print("\n🎯 Found these tutorials:")
    for tutorial in tutorials[:5]:  # First 5
        title = tutorial["head_data"].get("title", "No title")
        print(f"  - {title}")
        print(f"    {tutorial['url']}")

    # Step 6: Now crawl ONLY these relevant pages
    print("\n🚀 Crawling tutorials...")
    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            only_text=True,
            word_count_threshold=300,  # Only substantial articles
            stream=True
        )

        # Extract URLs and crawl them
        tutorial_urls = [t["url"] for t in tutorials[:10]]
        results = await crawler.arun_many(tutorial_urls, config=config)

        successful = 0
        async for result in results:
            if result.success:
                successful += 1
                print(f"✓ Crawled: {result.url[:60]}...")

        print(f"\n✨ Successfully crawled {successful} tutorials!")

# Run it!
asyncio.run(smart_blog_crawler())
Copy
```

**What just happened?**

1. We discovered all blog URLs from the sitemap+cc
2. We filtered using metadata (no crawling needed!)
3. We crawled only the relevant tutorials
4. We saved tons of time and bandwidth

This is the power of URL seeding - you see everything before you crawl anything.

## Understanding the URL Seeder

Now that you've seen the magic, let's understand how it works.

### Basic Usage

Creating a URL seeder is simple:

```
from crawl4ai import AsyncUrlSeeder

# Method 1: Manual cleanup
seeder = AsyncUrlSeeder()
try:
    config = SeedingConfig(source="sitemap")
    urls = await seeder.urls("example.com", config)
finally:
    await seeder.close()

# Method 2: Context manager (recommended)
async with AsyncUrlSeeder() as seeder:
    config = SeedingConfig(source="sitemap")
    urls = await seeder.urls("example.com", config)
    # Automatically cleaned up on exit
Copy
```

The seeder can discover URLs from two powerful sources:

#### 1. Sitemaps (Fastest)

```
# Discover from sitemap
config = SeedingConfig(source="sitemap")
urls = await seeder.urls("example.com", config)
Copy
```

Sitemaps are XML files that websites create specifically to list all their URLs. It's like getting a menu at a restaurant - everything is listed upfront.
**Sitemap Index Support** : For large websites like TechCrunch that use sitemap indexes (a sitemap of sitemaps), the seeder automatically detects and processes all sub-sitemaps in parallel:

```
<!-- Example sitemap index -->
<sitemapindex>
  <sitemap>
    <loc>https://techcrunch.com/sitemap-1.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://techcrunch.com/sitemap-2.xml</loc>
  </sitemap>
  <!-- ... more sitemaps ... -->
</sitemapindex>
Copy
```

The seeder handles this transparently - you'll get all URLs from all sub-sitemaps automatically!

#### 2. Common Crawl (Most Comprehensive)

```
# Discover from Common Crawl
config = SeedingConfig(source="cc")
urls = await seeder.urls("example.com", config)
Copy
```

Common Crawl is a massive public dataset that regularly crawls the entire web. It's like having access to a pre-built index of the internet.

#### 3. Both Sources (Maximum Coverage)

```
# Use both sources
config = SeedingConfig(source="sitemap+cc")
urls = await seeder.urls("example.com", config)
Copy
```

### Configuration Magic: SeedingConfig

The `SeedingConfig` object is your control panel. Here's everything you can configure:
Parameter | Type | Default | Description
---|---|---|---
`source` | str | "sitemap+cc" | URL source: "cc" (Common Crawl), "sitemap", or "sitemap+cc"
`pattern` | str | "_" | URL pattern filter (e.g., "*/blog/* ", "_.html")
`extract_head` | bool | False | Extract metadata from page `<head>`
`live_check` | bool | False | Verify URLs are accessible
`max_urls` | int | -1 | Maximum URLs to return (-1 = unlimited)
`concurrency` | int | 10 | Parallel workers for fetching
`hits_per_sec` | int | 5 | Rate limit for requests
`force` | bool | False | Bypass cache, fetch fresh data
`verbose` | bool | False | Show detailed progress
`query` | str | None | Search query for BM25 scoring
`scoring_method` | str | None | Scoring method (currently "bm25")
`score_threshold` | float | None | Minimum score to include URL
`filter_nonsense_urls` | bool | True | Filter out utility URLs (robots.txt, etc.)

#### Pattern Matching Examples

```
# Match all blog posts
config = SeedingConfig(pattern="*/blog/*")

# Match only HTML files
config = SeedingConfig(pattern="*.html")

# Match product pages
config = SeedingConfig(pattern="*/product/*")

# Match everything except admin pages
config = SeedingConfig(pattern="*")
# Then filter: urls = [u for u in urls if "/admin/" not in u["url"]]
Copy
```

### URL Validation: Live Checking

Sometimes you need to know if URLs are actually accessible. That's where live checking comes in:

```
config = SeedingConfig(
    source="sitemap",
    live_check=True,  # Verify each URL is accessible
    concurrency=20    # Check 20 URLs in parallel
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("example.com", config)

# Now you can filter by status
live_urls = [u for u in urls if u["status"] == "valid"]
dead_urls = [u for u in urls if u["status"] == "not_valid"]

print(f"Live URLs: {len(live_urls)}")
print(f"Dead URLs: {len(dead_urls)}")
Copy
```

**When to use live checking:** - Before a large crawling operation - When working with older sitemaps - When data freshness is critical
**When to skip it:** - Quick explorations - When you trust the source - When speed is more important than accuracy

### The Power of Metadata: Head Extraction

This is where URL seeding gets really powerful. Instead of crawling entire pages, you can extract just the metadata:

```
config = SeedingConfig(
    extract_head=True  # Extract metadata from <head> section
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("example.com", config)

# Now each URL has rich metadata
for url in urls[:3]:
    print(f"\nURL: {url['url']}")
    print(f"Title: {url['head_data'].get('title')}")

    meta = url['head_data'].get('meta', {})
    print(f"Description: {meta.get('description')}")
    print(f"Keywords: {meta.get('keywords')}")

    # Even Open Graph data!
    print(f"OG Image: {meta.get('og:image')}")
Copy
```

#### What Can We Extract?

The head extraction gives you a treasure trove of information:

```
# Example of extracted head_data
{
    "title": "10 Python Tips for Beginners",
    "charset": "utf-8",
    "lang": "en",
    "meta": {
        "description": "Learn essential Python tips...",
        "keywords": "python, programming, tutorial",
        "author": "Jane Developer",
        "viewport": "width=device-width, initial-scale=1",

        # Open Graph tags
        "og:title": "10 Python Tips for Beginners",
        "og:description": "Essential Python tips for new programmers",
        "og:image": "https://example.com/python-tips.jpg",
        "og:type": "article",

        # Twitter Card tags
        "twitter:card": "summary_large_image",
        "twitter:title": "10 Python Tips",

        # Dublin Core metadata
        "dc.creator": "Jane Developer",
        "dc.date": "2024-01-15"
    },
    "link": {
        "canonical": [{"href": "https://example.com/blog/python-tips"}],
        "alternate": [{"href": "/feed.xml", "type": "application/rss+xml"}]
    },
    "jsonld": [
        {
            "@type": "Article",
            "headline": "10 Python Tips for Beginners",
            "datePublished": "2024-01-15",
            "author": {"@type": "Person", "name": "Jane Developer"}
        }
    ]
}
Copy
```

This metadata is gold for filtering! You can find exactly what you need without crawling a single page.

### Smart URL-Based Filtering (No Head Extraction)

When `extract_head=False` but you still provide a query, the seeder uses intelligent URL-based scoring:

```
# Fast filtering based on URL structure alone
config = SeedingConfig(
    source="sitemap",
    extract_head=False,  # Don't fetch page metadata
    query="python tutorial async",
    scoring_method="bm25",
    score_threshold=0.3
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("example.com", config)

# URLs are scored based on:
# 1. Domain parts matching (e.g., 'python' in python.example.com)
# 2. Path segments (e.g., '/tutorials/python-async/')
# 3. Query parameters (e.g., '?topic=python')
# 4. Fuzzy matching using character n-grams

# Example URL scoring:
# https://example.com/tutorials/python/async-guide.html - High score
# https://example.com/blog/javascript-tips.html - Low score
Copy
```

This approach is much faster than head extraction while still providing intelligent filtering!

### Understanding Results

Each URL in the results has this structure:

```
{
    "url": "https://example.com/blog/python-tips.html",
    "status": "valid",        # "valid", "not_valid", or "unknown"
    "head_data": {            # Only if extract_head=True
        "title": "Page Title",
        "meta": {...},
        "link": {...},
        "jsonld": [...]
    },
    "relevance_score": 0.85   # Only if using BM25 scoring
}
Copy
```

Let's see a real example:

```
config = SeedingConfig(
    source="sitemap",
    extract_head=True,
    live_check=True
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("blog.example.com", config)

# Analyze the results
for url in urls[:5]:
    print(f"\n{'='*60}")
    print(f"URL: {url['url']}")
    print(f"Status: {url['status']}")

    if url['head_data']:
        data = url['head_data']
        print(f"Title: {data.get('title', 'No title')}")

        # Check content type
        meta = data.get('meta', {})
        content_type = meta.get('og:type', 'unknown')
        print(f"Content Type: {content_type}")

        # Publication date
        pub_date = None
        for jsonld in data.get('jsonld', []):
            if isinstance(jsonld, dict):
                pub_date = jsonld.get('datePublished')
                if pub_date:
                    break

        if pub_date:
            print(f"Published: {pub_date}")

        # Word count (if available)
        word_count = meta.get('word_count')
        if word_count:
            print(f"Word Count: {word_count}")
Copy
```

## Smart Filtering with BM25 Scoring

Now for the really cool part - intelligent filtering based on relevance!

### Introduction to Relevance Scoring

BM25 is a ranking algorithm that scores how relevant a document is to a search query. With URL seeding, we can score URLs based on their metadata _before_ crawling them.
Think of it like this: - Traditional way: Read every book in the library to find ones about Python - Smart way: Check the titles and descriptions, score them, read only the most relevant

### Query-Based Discovery

Here's how to use BM25 scoring:

```
config = SeedingConfig(
    source="sitemap",
    extract_head=True,           # Required for scoring
    query="python async tutorial",  # What we're looking for
    scoring_method="bm25",       # Use BM25 algorithm
    score_threshold=0.3          # Minimum relevance score
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("realpython.com", config)

# Results are automatically sorted by relevance!
for url in urls[:5]:
    print(f"Score: {url['relevance_score']:.2f} - {url['url']}")
    print(f"  Title: {url['head_data']['title']}")
Copy
```

### Real Examples

#### Finding Documentation Pages

```
# Find API documentation
config = SeedingConfig(
    source="sitemap",
    extract_head=True,
    query="API reference documentation endpoints",
    scoring_method="bm25",
    score_threshold=0.5,
    max_urls=20
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("docs.example.com", config)

# The highest scoring URLs will be API docs!
Copy
```

#### Discovering Product Pages

```
# Find specific products
config = SeedingConfig(
    source="sitemap+cc",  # Use both sources
    extract_head=True,
    query="wireless headphones noise canceling",
    scoring_method="bm25",
    score_threshold=0.4,
    pattern="*/product/*"  # Combine with pattern matching
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("shop.example.com", config)

# Filter further by price (from metadata)
affordable = [
    u for u in urls
    if float(u['head_data'].get('meta', {}).get('product:price', '0')) < 200
]
Copy
```

#### Filtering News Articles

```
# Find recent news about AI
config = SeedingConfig(
    source="sitemap",
    extract_head=True,
    query="artificial intelligence machine learning breakthrough",
    scoring_method="bm25",
    score_threshold=0.35
)
async with AsyncUrlSeeder() as seeder:
    urls = await seeder.urls("technews.com", config)

# Filter by date
from datetime import datetime, timedelta

recent = []
cutoff = datetime.now() - timedelta(days=7)

for url in urls:
    # Check JSON-LD for publication date
    for jsonld in url['head_data'].get('jsonld', []):
        if 'datePublished' in jsonld:
            pub_date = datetime.fromisoformat(jsonld['datePublished'].replace('Z', '+00:00'))
            if pub_date > cutoff:
                recent.append(url)
                break
Copy
```

#### Complex Query Patterns

```
# Multi-concept queries
queries = [
    "python async await concurrency tutorial",
    "data science pandas numpy visualization",
    "web scraping beautifulsoup selenium automation",
    "machine learning tensorflow keras deep learning"
]

all_tutorials = []

for query in queries:
    config = SeedingConfig(
        source="sitemap",
        extract_head=True,
        query=query,
        scoring_method="bm25",
        score_threshold=0.4,
        max_urls=10  # Top 10 per topic
    )
    async with AsyncUrlSeeder() as seeder:
        urls = await seeder.urls("learning-platform.com", config)
    all_tutorials.extend(urls)

# Remove duplicates while preserving order
seen = set()
unique_tutorials = []
for url in all_tutorials:
    if url['url'] not in seen:
        seen.add(url['url'])
        unique_tutorials.append(url)

print(f"Found {len(unique_tutorials)} unique tutorials across all topics")
Copy
```

## Scaling Up: Multiple Domains

When you need to discover URLs across multiple websites, URL seeding really shines.

### The `many_urls` Method

```
# Discover URLs from multiple domains in parallel
domains = ["site1.com", "site2.com", "site3.com"]

config = SeedingConfig(
    source="sitemap",
    extract_head=True,
    query="python tutorial",
    scoring_method="bm25",
    score_threshold=0.3
)

# Returns a dictionary: {domain: [urls]}
async with AsyncUrlSeeder() as seeder:
    results = await seeder.many_urls(domains, config)

# Process results
for domain, urls in results.items():
    print(f"\n{domain}: Found {len(urls)} relevant URLs")
    if urls:
        top = urls[0]  # Highest scoring
        print(f"  Top result: {top['url']}")
        print(f"  Score: {top['relevance_score']:.2f}")
Copy
```

### Cross-Domain Examples

#### Competitor Analysis

```
# Analyze content strategies across competitors
competitors = [
    "competitor1.com",
    "competitor2.com",
    "competitor3.com"
]

config = SeedingConfig(
    source="sitemap",
    extract_head=True,
    pattern="*/blog/*",
    max_urls=100
)
async with AsyncUrlSeeder() as seeder:
    results = await seeder.many_urls(competitors, config)

# Analyze content types
for domain, urls in results.items():
    content_types = {}

    for url in urls:
        # Extract content type from metadata
        og_type = url['head_data'].get('meta', {}).get('og:type', 'unknown')
        content_types[og_type] = content_types.get(og_type, 0) + 1

    print(f"\n{domain} content distribution:")
    for ctype, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ctype}: {count}")
Copy
```

#### Industry Research

```
# Research Python tutorials across educational sites
educational_sites = [
    "realpython.com",
    "pythontutorial.net",
    "learnpython.org",
    "python.org"
]

config = SeedingConfig(
    source="sitemap",
    extract_head=True,
    query="beginner python tutorial basics",
    scoring_method="bm25",
    score_threshold=0.3,
    max_urls=20  # Per site
)
async with AsyncUrlSeeder() as seeder:
    results = await seeder.many_urls(educational_sites, config)

# Find the best beginner tutorials
all_tutorials = []
for domain, urls in results.items():
    for url in urls:
        url['domain'] = domain  # Add domain info
        all_tutorials.append(url)

# Sort by relevance across all domains
all_tutorials.sort(key=lambda x: x['relevance_score'], reverse=True)

print("Top 10 Python tutorials for beginners across all sites:")
for i, tutorial in enumerate(all_tutorials[:10], 1):
    print(f"{i}. [{tutorial['relevance_score']:.2f}] {tutorial['head_data']['title']}")
    print(f"   {tutorial['url']}")
    print(f"   From: {tutorial['domain']}")
Copy
```

#### Multi-Site Monitoring

```
# Monitor news about your company across multiple sources
news_sites = [
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "arstechnica.com"
]

company_name = "YourCompany"

config = SeedingConfig(
    source="cc",  # Common Crawl for recent content
    extract_head=True,
    query=f"{company_name} announcement news",
    scoring_method="bm25",
    score_threshold=0.5,  # High threshold for relevance
    max_urls=10
)
async with AsyncUrlSeeder() as seeder:
    results = await seeder.many_urls(news_sites, config)

# Collect all mentions
mentions = []
for domain, urls in results.items():
    mentions.extend(urls)

if mentions:
    print(f"Found {len(mentions)} mentions of {company_name}:")
    for mention in mentions:
        print(f"\n- {mention['head_data']['title']}")
        print(f"  {mention['url']}")
        print(f"  Score: {mention['relevance_score']:.2f}")
else:
    print(f"No recent mentions of {company_name} found")
Copy
```

## Advanced Integration Patterns

Let's put everything together in a real-world example.

### Building a Research Assistant

Here's a complete example that discovers, scores, filters, and crawls intelligently:

```
import asyncio
from datetime import datetime
from crawl4ai import AsyncUrlSeeder, AsyncWebCrawler, SeedingConfig, CrawlerRunConfig

class ResearchAssistant:
    def __init__(self):
        self.seeder = None

    async def __aenter__(self):
        self.seeder = AsyncUrlSeeder()
        await self.seeder.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.seeder:
            await self.seeder.__aexit__(exc_type, exc_val, exc_tb)

    async def research_topic(self, topic, domains, max_articles=20):
        """Research a topic across multiple domains."""

        print(f"🔬 Researching '{topic}' across {len(domains)} domains...")

        # Step 1: Discover relevant URLs
        config = SeedingConfig(
            source="sitemap+cc",     # Maximum coverage
            extract_head=True,       # Get metadata
            query=topic,             # Research topic
            scoring_method="bm25",   # Smart scoring
            score_threshold=0.4,     # Quality threshold
            max_urls=10,             # Per domain
            concurrency=20,          # Fast discovery
            verbose=True
        )

        # Discover across all domains
        discoveries = await self.seeder.many_urls(domains, config)

        # Step 2: Collect and rank all articles
        all_articles = []
        for domain, urls in discoveries.items():
            for url in urls:
                url['domain'] = domain
                all_articles.append(url)

        # Sort by relevance
        all_articles.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Take top articles
        top_articles = all_articles[:max_articles]

        print(f"\n📊 Found {len(all_articles)} relevant articles")
        print(f"📌 Selected top {len(top_articles)} for deep analysis")

        # Step 3: Show what we're about to crawl
        print("\n🎯 Articles to analyze:")
        for i, article in enumerate(top_articles[:5], 1):
            print(f"\n{i}. {article['head_data']['title']}")
            print(f"   Score: {article['relevance_score']:.2f}")
            print(f"   Source: {article['domain']}")
            print(f"   URL: {article['url'][:60]}...")

        # Step 4: Crawl the selected articles
        print(f"\n🚀 Deep crawling {len(top_articles)} articles...")

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                only_text=True,
                word_count_threshold=200,  # Substantial content only
                stream=True
            )

            # Extract URLs and crawl all articles
            article_urls = [article['url'] for article in top_articles]
            results = []
            crawl_results = await crawler.arun_many(article_urls, config=config)
            async for result in crawl_results:
                if result.success:
                    results.append({
                        'url': result.url,
                        'title': result.metadata.get('title', 'No title'),
                        'content': result.markdown.raw_markdown,
                        'domain': next(a['domain'] for a in top_articles if a['url'] == result.url),
                        'score': next(a['relevance_score'] for a in top_articles if a['url'] == result.url)
                    })
                    print(f"✓ Crawled: {result.url[:60]}...")

        # Step 5: Analyze and summarize
        print(f"\n📝 Analysis complete! Crawled {len(results)} articles")

        return self.create_research_summary(topic, results)

    def create_research_summary(self, topic, articles):
        """Create a research summary from crawled articles."""

        summary = {
            'topic': topic,
            'timestamp': datetime.now().isoformat(),
            'total_articles': len(articles),
            'sources': {}
        }

        # Group by domain
        for article in articles:
            domain = article['domain']
            if domain not in summary['sources']:
                summary['sources'][domain] = []

            summary['sources'][domain].append({
                'title': article['title'],
                'url': article['url'],
                'score': article['score'],
                'excerpt': article['content'][:500] + '...' if len(article['content']) > 500 else article['content']
            })

        return summary

# Use the research assistant
async def main():
    async with ResearchAssistant() as assistant:
        # Research Python async programming across multiple sources
        topic = "python asyncio best practices performance optimization"
        domains = [
            "realpython.com",
            "python.org",
            "stackoverflow.com",
            "medium.com"
        ]

        summary = await assistant.research_topic(topic, domains, max_articles=15)

    # Display results
    print("\n" + "="*60)
    print("RESEARCH SUMMARY")
    print("="*60)
    print(f"Topic: {summary['topic']}")
    print(f"Date: {summary['timestamp']}")
    print(f"Total Articles Analyzed: {summary['total_articles']}")

    print("\nKey Findings by Source:")
    for domain, articles in summary['sources'].items():
        print(f"\n📚 {domain} ({len(articles)} articles)")
        for article in articles[:2]:  # Top 2 per domain
            print(f"\n  Title: {article['title']}")
            print(f"  Relevance: {article['score']:.2f}")
            print(f"  Preview: {article['excerpt'][:200]}...")

asyncio.run(main())
Copy
```

### Performance Optimization Tips

1. **Use caching wisely**

```
# First run - populate cache
config = SeedingConfig(source="sitemap", extract_head=True, force=True)
urls = await seeder.urls("example.com", config)

# Subsequent runs - use cache (much faster)
config = SeedingConfig(source="sitemap", extract_head=True, force=False)
urls = await seeder.urls("example.com", config)
Copy
```

2. **Optimize concurrency**

```
# For many small requests (like HEAD checks)
config = SeedingConfig(concurrency=50, hits_per_sec=20)

# For fewer large requests (like full head extraction)
config = SeedingConfig(concurrency=10, hits_per_sec=5)
Copy
```

3. **Stream large result sets**

```
# When crawling many URLs
async with AsyncWebCrawler() as crawler:
    # Assuming urls is a list of URL strings
    crawl_results = await crawler.arun_many(urls, config=config)

    # Process as they arrive
    async for result in crawl_results:
        process_immediately(result)  # Don't wait for all
Copy
```

4. **Memory protection for large domains**

The seeder uses bounded queues to prevent memory issues when processing domains with millions of URLs:

```
# Safe for domains with 1M+ URLs
config = SeedingConfig(
    source="cc+sitemap",
    concurrency=50,  # Queue size adapts to concurrency
    max_urls=100000  # Process in batches if needed
)

# The seeder automatically manages memory by:
# - Using bounded queues (prevents RAM spikes)
# - Applying backpressure when queue is full
# - Processing URLs as they're discovered
Copy
```

## Best Practices & Tips

### Cache Management

The seeder automatically caches results to speed up repeated operations:

- **Common Crawl cache** : `~/.crawl4ai/seeder_cache/[index]_[domain]_[hash].jsonl`
- **Sitemap cache** : `~/.crawl4ai/seeder_cache/sitemap_[domain]_[hash].jsonl`
- **HEAD data cache** : `~/.cache/url_seeder/head/[hash].json`

Cache expires after 7 days by default. Use `force=True` to refresh.

### Pattern Matching Strategies

```
# Be specific when possible
good_pattern = "*/blog/2024/*.html"  # Specific
bad_pattern = "*"                     # Too broad

# Combine patterns with metadata filtering
config = SeedingConfig(
    pattern="*/articles/*",
    extract_head=True
)
urls = await seeder.urls("news.com", config)

# Further filter by publish date, author, category, etc.
recent = [u for u in urls if is_recent(u['head_data'])]
Copy
```

### Rate Limiting Considerations

```
# Be respectful of servers
config = SeedingConfig(
    hits_per_sec=10,      # Max 10 requests per second
    concurrency=20        # But use 20 workers
)

# For your own servers
config = SeedingConfig(
    hits_per_sec=None,    # No limit
    concurrency=100       # Go fast
)
Copy
```

## Quick Reference

### Common Patterns

```
# Blog post discovery
config = SeedingConfig(
    source="sitemap",
    pattern="*/blog/*",
    extract_head=True,
    query="your topic",
    scoring_method="bm25"
)

# E-commerce product discovery
config = SeedingConfig(
    source="sitemap+cc",
    pattern="*/product/*",
    extract_head=True,
    live_check=True
)

# Documentation search
config = SeedingConfig(
    source="sitemap",
    pattern="*/docs/*",
    extract_head=True,
    query="API reference",
    scoring_method="bm25",
    score_threshold=0.5
)

# News monitoring
config = SeedingConfig(
    source="cc",
    extract_head=True,
    query="company name",
    scoring_method="bm25",
    max_urls=50
)
Copy
```

### Troubleshooting Guide

| Issue                          | Solution                                              |
| ------------------------------ | ----------------------------------------------------- |
| No URLs found                  | Try `source="cc+sitemap"`, check domain spelling      |
| Slow discovery                 | Reduce `concurrency`, add `hits_per_sec` limit        |
| Missing metadata               | Ensure `extract_head=True`                            |
| Low relevance scores           | Refine query, lower `score_threshold`                 |
| Rate limit errors              | Reduce `hits_per_sec` and `concurrency`               |
| Memory issues with large sites | Use `max_urls` to limit results, reduce `concurrency` |
| Connection not closed          | Use context manager or call `await seeder.close()`    |

### Performance Benchmarks

Typical performance on a standard connection:

- **Sitemap discovery** : 100-1,000 URLs/second
- **Common Crawl discovery** : 50-500 URLs/second
- **HEAD checking** : 10-50 URLs/second
- **Head extraction** : 5-20 URLs/second
- **BM25 scoring** : 10,000+ URLs/second

## Conclusion

URL seeding transforms web crawling from a blind expedition into a surgical strike. By discovering and analyzing URLs before crawling, you can:

- Save hours of crawling time
- Reduce bandwidth usage by 90%+
- Find exactly what you need
- Scale across multiple domains effortlessly

Whether you're building a research tool, monitoring competitors, or creating a content aggregator, URL seeding gives you the intelligence to crawl smarter, not harder.

### Smart URL Filtering

The seeder automatically filters out nonsense URLs that aren't useful for content crawling:

```
# Enabled by default
config = SeedingConfig(
    source="sitemap",
    filter_nonsense_urls=True  # Default: True
)

# URLs that get filtered:
# - robots.txt, sitemap.xml, ads.txt
# - API endpoints (/api/, /v1/, .json)
# - Media files (.jpg, .mp4, .pdf)
# - Archives (.zip, .tar.gz)
# - Source code (.js, .css)
# - Admin/login pages
# - And many more...
Copy
```

To disable filtering (not recommended):

```
config = SeedingConfig(
    source="sitemap",
    filter_nonsense_urls=False  # Include ALL URLs
)
Copy
```

### Key Features Summary

1. **Parallel Sitemap Index Processing** : Automatically detects and processes sitemap indexes in parallel
2. **Memory Protection** : Bounded queues prevent RAM issues with large domains (1M+ URLs)
3. **Context Manager Support** : Automatic cleanup with `async with` statement
4. **URL-Based Scoring** : Smart filtering even without head extraction
5. **Smart URL Filtering** : Automatically excludes utility/nonsense URLs
6. **Dual Caching** : Separate caches for URL lists and metadata

Now go forth and seed intelligently! 🌱🚀
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/core/url-seeding/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/core/url-seeding/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/core/url-seeding/)

ESC to close

#### On this page

- [Why URL Seeding?](https://docs.crawl4ai.com/core/url-seeding/#why-url-seeding)
- [Deep Crawling: Real-Time Discovery](https://docs.crawl4ai.com/core/url-seeding/#deep-crawling-real-time-discovery)
- [URL Seeding: Bulk Discovery](https://docs.crawl4ai.com/core/url-seeding/#url-seeding-bulk-discovery)
- [The Trade-offs](https://docs.crawl4ai.com/core/url-seeding/#the-trade-offs)
- [When to Use Each](https://docs.crawl4ai.com/core/url-seeding/#when-to-use-each)
- [Your First URL Seeding Adventure](https://docs.crawl4ai.com/core/url-seeding/#your-first-url-seeding-adventure)
- [Understanding the URL Seeder](https://docs.crawl4ai.com/core/url-seeding/#understanding-the-url-seeder)
- [Basic Usage](https://docs.crawl4ai.com/core/url-seeding/#basic-usage)
- [1. Sitemaps (Fastest)](https://docs.crawl4ai.com/core/url-seeding/#1-sitemaps-fastest)
- [2. Common Crawl (Most Comprehensive)](https://docs.crawl4ai.com/core/url-seeding/#2-common-crawl-most-comprehensive)
- [3. Both Sources (Maximum Coverage)](https://docs.crawl4ai.com/core/url-seeding/#3-both-sources-maximum-coverage)
- [Configuration Magic: SeedingConfig](https://docs.crawl4ai.com/core/url-seeding/#configuration-magic-seedingconfig)
- [Pattern Matching Examples](https://docs.crawl4ai.com/core/url-seeding/#pattern-matching-examples)
- [URL Validation: Live Checking](https://docs.crawl4ai.com/core/url-seeding/#url-validation-live-checking)
- [The Power of Metadata: Head Extraction](https://docs.crawl4ai.com/core/url-seeding/#the-power-of-metadata-head-extraction)
- [What Can We Extract?](https://docs.crawl4ai.com/core/url-seeding/#what-can-we-extract)
- [Smart URL-Based Filtering (No Head Extraction)](https://docs.crawl4ai.com/core/url-seeding/#smart-url-based-filtering-no-head-extraction)
- [Understanding Results](https://docs.crawl4ai.com/core/url-seeding/#understanding-results)
- [Smart Filtering with BM25 Scoring](https://docs.crawl4ai.com/core/url-seeding/#smart-filtering-with-bm25-scoring)
- [Introduction to Relevance Scoring](https://docs.crawl4ai.com/core/url-seeding/#introduction-to-relevance-scoring)
- [Query-Based Discovery](https://docs.crawl4ai.com/core/url-seeding/#query-based-discovery)
- [Real Examples](https://docs.crawl4ai.com/core/url-seeding/#real-examples)
- [Finding Documentation Pages](https://docs.crawl4ai.com/core/url-seeding/#finding-documentation-pages)
- [Discovering Product Pages](https://docs.crawl4ai.com/core/url-seeding/#discovering-product-pages)
- [Filtering News Articles](https://docs.crawl4ai.com/core/url-seeding/#filtering-news-articles)
- [Complex Query Patterns](https://docs.crawl4ai.com/core/url-seeding/#complex-query-patterns)
- [Scaling Up: Multiple Domains](https://docs.crawl4ai.com/core/url-seeding/#scaling-up-multiple-domains)
- [The many_urls Method](https://docs.crawl4ai.com/core/url-seeding/#the-many_urls-method)
- [Cross-Domain Examples](https://docs.crawl4ai.com/core/url-seeding/#cross-domain-examples)
- [Competitor Analysis](https://docs.crawl4ai.com/core/url-seeding/#competitor-analysis)
- [Industry Research](https://docs.crawl4ai.com/core/url-seeding/#industry-research)
- [Multi-Site Monitoring](https://docs.crawl4ai.com/core/url-seeding/#multi-site-monitoring)
- [Advanced Integration Patterns](https://docs.crawl4ai.com/core/url-seeding/#advanced-integration-patterns)
- [Building a Research Assistant](https://docs.crawl4ai.com/core/url-seeding/#building-a-research-assistant)
- [Performance Optimization Tips](https://docs.crawl4ai.com/core/url-seeding/#performance-optimization-tips)
- [Best Practices & Tips](https://docs.crawl4ai.com/core/url-seeding/#best-practices-tips)
- [Cache Management](https://docs.crawl4ai.com/core/url-seeding/#cache-management)
- [Pattern Matching Strategies](https://docs.crawl4ai.com/core/url-seeding/#pattern-matching-strategies)
- [Rate Limiting Considerations](https://docs.crawl4ai.com/core/url-seeding/#rate-limiting-considerations)
- [Quick Reference](https://docs.crawl4ai.com/core/url-seeding/#quick-reference)
- [Common Patterns](https://docs.crawl4ai.com/core/url-seeding/#common-patterns)
- [Troubleshooting Guide](https://docs.crawl4ai.com/core/url-seeding/#troubleshooting-guide)
- [Performance Benchmarks](https://docs.crawl4ai.com/core/url-seeding/#performance-benchmarks)
- [Conclusion](https://docs.crawl4ai.com/core/url-seeding/#conclusion)
- [Smart URL Filtering](https://docs.crawl4ai.com/core/url-seeding/#smart-url-filtering)
- [Key Features Summary](https://docs.crawl4ai.com/core/url-seeding/#key-features-summary)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/extraction/llm-strategies

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/extraction/llm-strategies/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - [LLM-Free Strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
  - LLM Strategies
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Extracting JSON (LLM)](https://docs.crawl4ai.com/extraction/llm-strategies/#extracting-json-llm)
- [1. Why Use an LLM?](https://docs.crawl4ai.com/extraction/llm-strategies/#1-why-use-an-llm)
- [2. Provider-Agnostic via LiteLLM](https://docs.crawl4ai.com/extraction/llm-strategies/#2-provider-agnostic-via-litellm)
- [3. How LLM Extraction Works](https://docs.crawl4ai.com/extraction/llm-strategies/#3-how-llm-extraction-works)
- [4. Key Parameters](https://docs.crawl4ai.com/extraction/llm-strategies/#4-key-parameters)
- [5. Putting It in CrawlerRunConfig](https://docs.crawl4ai.com/extraction/llm-strategies/#5-putting-it-in-crawlerrunconfig)
- [6. Chunking Details](https://docs.crawl4ai.com/extraction/llm-strategies/#6-chunking-details)
- [7. Input Format](https://docs.crawl4ai.com/extraction/llm-strategies/#7-input-format)
- [8. Token Usage & Show Usage](https://docs.crawl4ai.com/extraction/llm-strategies/#8-token-usage-show-usage)
- [9. Example: Building a Knowledge Graph](https://docs.crawl4ai.com/extraction/llm-strategies/#9-example-building-a-knowledge-graph)
- [10. Best Practices & Caveats](https://docs.crawl4ai.com/extraction/llm-strategies/#10-best-practices-caveats)
- [11. Conclusion](https://docs.crawl4ai.com/extraction/llm-strategies/#11-conclusion)

# Extracting JSON (LLM)

In some cases, you need to extract **complex or unstructured** information from a webpage that a simple CSS/XPath schema cannot easily parse. Or you want **AI** -driven insights, classification, or summarization. For these scenarios, Crawl4AI provides an **LLM-based extraction strategy** that:

1. Works with **any** large language model supported by [LiteLLM](https://github.com/BerriAI/litellm) (Ollama, OpenAI, Claude, and more).
2. Automatically splits content into chunks (if desired) to handle token limits, then combines results.
3. Lets you define a **schema** (like a Pydantic model) or a simpler “block” extraction approach.

**Important** : LLM-based extraction can be slower and costlier than schema-based approaches. If your page data is highly structured, consider using [`JsonCssExtractionStrategy`](https://docs.crawl4ai.com/extraction/no-llm-strategies/) or [`JsonXPathExtractionStrategy`](https://docs.crawl4ai.com/extraction/no-llm-strategies/) first. But if you need AI to interpret or reorganize content, read on!

---

## 1. Why Use an LLM?

- **Complex Reasoning** : If the site’s data is unstructured, scattered, or full of natural language context.
- **Semantic Extraction** : Summaries, knowledge graphs, or relational data that require comprehension.
- **Flexible** : You can pass instructions to the model to do more advanced transformations or classification.

---

## 2. Provider-Agnostic via LiteLLM

You can use LlmConfig, to quickly configure multiple variations of LLMs and experiment with them to find the optimal one for your use case. You can read more about LlmConfig [here](https://docs.crawl4ai.com/api/parameters).

```
llmConfig = LlmConfig(provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY"))
Copy
```

Crawl4AI uses a “provider string” (e.g., `"openai/gpt-4o"`, `"ollama/llama2.0"`, `"aws/titan"`) to identify your LLM. **Any** model that LiteLLM supports is fair game. You just provide:

- **`provider`**: The`<provider>/<model_name>` identifier (e.g., `"openai/gpt-4"`, `"ollama/llama2"`, `"huggingface/google-flan"`, etc.).
- **`api_token`**: If needed (for OpenAI, HuggingFace, etc.); local models or Ollama might not require it.
- **`base_url`**(optional): If your provider has a custom endpoint.

This means you **aren’t locked** into a single LLM vendor. Switch or experiment easily.

---

## 3. How LLM Extraction Works

### 3.1 Flow

1. **Chunking** (optional): The HTML or markdown is split into smaller segments if it’s very long (based on `chunk_token_threshold`, overlap, etc.).
2. **Prompt Construction** : For each chunk, the library forms a prompt that includes your **`instruction`**(and possibly schema or examples).
3. **LLM Inference** : Each chunk is sent to the model in parallel or sequentially (depending on your concurrency).
4. **Combining** : The results from each chunk are merged and parsed into JSON.

### 3.2 `extraction_type`

- **`"schema"`**: The model tries to return JSON conforming to your Pydantic-based schema.
- **`"block"`**: The model returns freeform text, or smaller JSON structures, which the library collects.

For structured data, `"schema"` is recommended. You provide `schema=YourPydanticModel.model_json_schema()`.

---

## 4. Key Parameters

Below is an overview of important LLM extraction parameters. All are typically set inside `LLMExtractionStrategy(...)`. You then put that strategy in your `CrawlerRunConfig(..., extraction_strategy=...)`.

1. **`llmConfig`**(LlmConfig): e.g.,`"openai/gpt-4"` , `"ollama/llama2"`.
2. **`schema`**(dict): A JSON schema describing the fields you want. Usually generated by`YourModel.model_json_schema()`.
3. **`extraction_type`**(str):`"schema"` or `"block"`.
4. **`instruction`**(str): Prompt text telling the LLM what you want extracted. E.g., “Extract these fields as a JSON array.”
5. **`chunk_token_threshold`**(int): Maximum tokens per chunk. If your content is huge, you can break it up for the LLM.
6. **`overlap_rate`**(float): Overlap ratio between adjacent chunks. E.g.,`0.1` means 10% of each chunk is repeated to preserve context continuity.
7. **`apply_chunking`**(bool): Set`True` to chunk automatically. If you want a single pass, set `False`.
8. **`input_format`**(str): Determines**which** crawler result is passed to the LLM. Options include:

- `"markdown"`: The raw markdown (default).
- `"fit_markdown"`: The filtered “fit” markdown if you used a content filter.
- `"html"`: The cleaned or raw HTML.

9. **`extra_args`**(dict): Additional LLM parameters like`temperature` , `max_tokens`, `top_p`, etc.
10. **`show_usage()`**: A method you can call to print out usage info (token usage per chunk, total cost if known).
    **Example** :

```
extraction_strategy = LLMExtractionStrategy(
    llm_config = LLMConfig(provider="openai/gpt-4", api_token="YOUR_OPENAI_KEY"),
    schema=MyModel.model_json_schema(),
    extraction_type="schema",
    instruction="Extract a list of items from the text with 'name' and 'price' fields.",
    chunk_token_threshold=1200,
    overlap_rate=0.1,
    apply_chunking=True,
    input_format="html",
    extra_args={"temperature": 0.1, "max_tokens": 1000},
    verbose=True
)
Copy
```

---

## 5. Putting It in `CrawlerRunConfig`

**Important** : In Crawl4AI, all strategy definitions should go inside the `CrawlerRunConfig`, not directly as a param in `arun()`. Here’s a full example:

```
import os
import asyncio
import json
from pydantic import BaseModel, Field
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai import LLMExtractionStrategy

class Product(BaseModel):
    name: str
    price: str

async def main():
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv('OPENAI_API_KEY')),
        schema=Product.schema_json(), # Or use model_json_schema()
        extraction_type="schema",
        instruction="Extract all product objects with 'name' and 'price' from the content.",
        chunk_token_threshold=1000,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800}
    )

    # 2. Build the crawler config
    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=True)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 4. Let's say we want to crawl a single page
        result = await crawler.arun(
            url="https://example.com/products",
            config=crawl_config
        )

        if result.success:
            # 5. The extracted content is presumably JSON
            data = json.loads(result.extracted_content)
            print("Extracted items:", data)

            # 6. Show usage stats
            llm_strategy.show_usage()  # prints token usage
        else:
            print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

---

## 6. Chunking Details

### 6.1 `chunk_token_threshold`

If your page is large, you might exceed your LLM’s context window. **`chunk_token_threshold`**sets the approximate max tokens per chunk. The library calculates word→token ratio using`word_token_rate` (often ~0.75 by default). If chunking is enabled (`apply_chunking=True`), the text is split into segments.

### 6.2 `overlap_rate`

To keep context continuous across chunks, we can overlap them. E.g., `overlap_rate=0.1` means each subsequent chunk includes 10% of the previous chunk’s text. This is helpful if your needed info might straddle chunk boundaries.

### 6.3 Performance & Parallelism

By chunking, you can potentially process multiple chunks in parallel (depending on your concurrency settings and the LLM provider). This reduces total time if the site is huge or has many sections.

---

## 7. Input Format

By default, **LLMExtractionStrategy** uses `input_format="markdown"`, meaning the **crawler’s final markdown** is fed to the LLM. You can change to:

- **`html`**: The cleaned HTML or raw HTML (depending on your crawler config) goes into the LLM.
- **`fit_markdown`**: If you used, for instance,`PruningContentFilter` , the “fit” version of the markdown is used. This can drastically reduce tokens if you trust the filter.
- **`markdown`**: Standard markdown output from the crawler’s`markdown_generator`.

This setting is crucial: if the LLM instructions rely on HTML tags, pick `"html"`. If you prefer a text-based approach, pick `"markdown"`.

```
LLMExtractionStrategy(
    # ...
    input_format="html",  # Instead of "markdown" or "fit_markdown"
)
Copy
```

---

## 8. Token Usage & Show Usage

To keep track of tokens and cost, each chunk is processed with an LLM call. We record usage in:

- **`usages`**(list): token usage per chunk or call.
- **`total_usage`**: sum of all chunk calls.
- **`show_usage()`**: prints a usage report (if the provider returns usage data).

```
llm_strategy = LLMExtractionStrategy(...)
# ...
llm_strategy.show_usage()
# e.g. “Total usage: 1241 tokens across 2 chunk calls”
Copy
```

If your model provider doesn’t return usage info, these fields might be partial or empty.

---

## 9. Example: Building a Knowledge Graph

Below is a snippet combining **`LLMExtractionStrategy`**with a Pydantic schema for a knowledge graph. Notice how we pass an**`instruction`**telling the model what to parse.

```
import os
import json
import asyncio
from typing import List
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai import LLMExtractionStrategy

class Entity(BaseModel):
    name: str
    description: str

class Relationship(BaseModel):
    entity1: Entity
    entity2: Entity
    description: str
    relation_type: str

class KnowledgeGraph(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]

async def main():
    # LLM extraction strategy
    llm_strat = LLMExtractionStrategy(
        llmConfig = LLMConfig(provider="openai/gpt-4", api_token=os.getenv('OPENAI_API_KEY')),
        schema=KnowledgeGraph.model_json_schema(),
        extraction_type="schema",
        instruction="Extract entities and relationships from the content. Return valid JSON.",
        chunk_token_threshold=1400,
        apply_chunking=True,
        input_format="html",
        extra_args={"temperature": 0.1, "max_tokens": 1500}
    )

    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strat,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        # Example page
        url = "https://www.nbcnews.com/business"
        result = await crawler.arun(url=url, config=crawl_config)

        print("--- LLM RAW RESPONSE ---")
        print(result.extracted_content)
        print("--- END LLM RAW RESPONSE ---")

        if result.success:
            with open("kb_result.json", "w", encoding="utf-8") as f:
                f.write(result.extracted_content)
            llm_strat.show_usage()
        else:
            print("Crawl failed:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
Copy
```

**Key Observations** :

- **`extraction_type="schema"`**ensures we get JSON fitting our`KnowledgeGraph`.
- **`input_format="html"`**means we feed HTML to the model.
- **`instruction`**guides the model to output a structured knowledge graph.

---

## 10. Best Practices & Caveats

1. **Cost & Latency**: LLM calls can be slow or expensive. Consider chunking or smaller coverage if you only need partial data.
2. **Model Token Limits** : If your page + instruction exceed the context window, chunking is essential.
3. **Instruction Engineering** : Well-crafted instructions can drastically improve output reliability.
4. **Schema Strictness** : `"schema"` extraction tries to parse the model output as JSON. If the model returns invalid JSON, partial extraction might happen, or you might get an error.
5. **Parallel vs. Serial** : The library can process multiple chunks in parallel, but you must watch out for rate limits on certain providers.
6. **Check Output** : Sometimes, an LLM might omit fields or produce extraneous text. You may want to post-validate with Pydantic or do additional cleanup.

---

## 11. Conclusion

**LLM-based extraction** in Crawl4AI is **provider-agnostic** , letting you choose from hundreds of models via LiteLLM. It’s perfect for **semantically complex** tasks or generating advanced structures like knowledge graphs. However, it’s **slower** and potentially costlier than schema-based approaches. Keep these tips in mind:

- Put your LLM strategy **in`CrawlerRunConfig`**.
- Use **`input_format`**to pick which form (markdown, HTML, fit_markdown) the LLM sees.
- Tweak **`chunk_token_threshold`**,**`overlap_rate`**, and**`apply_chunking`**to handle large content efficiently.
- Monitor token usage with `show_usage()`.

If your site’s data is consistent or repetitive, consider [`JsonCssExtractionStrategy`](https://docs.crawl4ai.com/extraction/no-llm-strategies/) first for speed and simplicity. But if you need an **AI-driven** approach, `LLMExtractionStrategy` offers a flexible, multi-provider solution for extracting structured JSON from any website.
**Next Steps** :

1. **Experiment with Different Providers**

- Try switching the `provider` (e.g., `"ollama/llama2"`, `"openai/gpt-4o"`, etc.) to see differences in speed, accuracy, or cost.
- Pass different `extra_args` like `temperature`, `top_p`, and `max_tokens` to fine-tune your results.

2. **Performance Tuning**

- If pages are large, tweak `chunk_token_threshold`, `overlap_rate`, or `apply_chunking` to optimize throughput.
- Check the usage logs with `show_usage()` to keep an eye on token consumption and identify potential bottlenecks.

3. **Validate Outputs**

- If using `extraction_type="schema"`, parse the LLM’s JSON with a Pydantic model for a final validation step.
- Log or handle any parse errors gracefully, especially if the model occasionally returns malformed JSON.

4. **Explore Hooks & Automation**

- Integrate LLM extraction with [hooks](https://docs.crawl4ai.com/advanced/hooks-auth/) for complex pre/post-processing.
- Use a multi-step pipeline: crawl, filter, LLM-extract, then store or index results for further analysis.
  **Last Updated** : 2025-01-01

---

That’s it for **Extracting JSON (LLM)** —now you can harness AI to parse, classify, or reorganize data on the web. Happy crawling!
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/extraction/llm-strategies/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/extraction/llm-strategies/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/extraction/llm-strategies/)

ESC to close

#### On this page

- [1. Why Use an LLM?](https://docs.crawl4ai.com/extraction/llm-strategies/#1-why-use-an-llm)
- [2. Provider-Agnostic via LiteLLM](https://docs.crawl4ai.com/extraction/llm-strategies/#2-provider-agnostic-via-litellm)
- [3. How LLM Extraction Works](https://docs.crawl4ai.com/extraction/llm-strategies/#3-how-llm-extraction-works)
- [3.1 Flow](https://docs.crawl4ai.com/extraction/llm-strategies/#31-flow)
- [3.2 extraction_type](https://docs.crawl4ai.com/extraction/llm-strategies/#32-extraction_type)
- [4. Key Parameters](https://docs.crawl4ai.com/extraction/llm-strategies/#4-key-parameters)
- [5. Putting It in CrawlerRunConfig](https://docs.crawl4ai.com/extraction/llm-strategies/#5-putting-it-in-crawlerrunconfig)
- [6. Chunking Details](https://docs.crawl4ai.com/extraction/llm-strategies/#6-chunking-details)
- [6.1 chunk_token_threshold](https://docs.crawl4ai.com/extraction/llm-strategies/#61-chunk_token_threshold)
- [6.2 overlap_rate](https://docs.crawl4ai.com/extraction/llm-strategies/#62-overlap_rate)
- [6.3 Performance & Parallelism](https://docs.crawl4ai.com/extraction/llm-strategies/#63-performance-parallelism)
- [7. Input Format](https://docs.crawl4ai.com/extraction/llm-strategies/#7-input-format)
- [8. Token Usage & Show Usage](https://docs.crawl4ai.com/extraction/llm-strategies/#8-token-usage-show-usage)
- [9. Example: Building a Knowledge Graph](https://docs.crawl4ai.com/extraction/llm-strategies/#9-example-building-a-knowledge-graph)
- [10. Best Practices & Caveats](https://docs.crawl4ai.com/extraction/llm-strategies/#10-best-practices-caveats)
- [11. Conclusion](https://docs.crawl4ai.com/extraction/llm-strategies/#11-conclusion)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

## Fonte: https://docs.crawl4ai.com/marketplace/admin

![Crawl4AI](https://docs.crawl4ai.com/assets/images/logo.png)

# [ Admin Access ]

→ Login
![Crawl4AI](https://docs.crawl4ai.com/assets/images/logo.png)

# [ Admin Dashboard ]

Administrator ↗ Logout
▓ Dashboard ◆ Apps ■ Articles □ Categories ◆ Sponsors
↓ Export Data ▪ Backup DB

## Dashboard Overview

## ◆

Total Apps
-- featured, -- sponsored
■
--
Articles
◆
--
Active Sponsors
●
--
Total Views

### Quick Actions

→ Add New App → Write Article → Add Sponsor

## Apps Management

All Categories → Add App

## Articles Management

→ Add Article

## Categories Management

→ Add Category

## Sponsors Management

→ Add Sponsor

## Add/Edit

✕
Cancel Save

---

## Fonte: https://docs.crawl4ai.com/marketplace

![Crawl4AI](https://docs.crawl4ai.com/assets/images/logo.png)

# [ Marketplace ]

Tools, Integrations & Resources for Web Crawling
Apps: -- Articles: -- Downloads: --

> `/`
> All
> SPONSORED

## > Latest Apps

All Open Source Paid

## > Latest Articles

## # Trending

### + Submit Your Tool

Share your integration
Submit →

## > More Apps

Load More ↓

### About Marketplace

Discover tools and integrations built by the Crawl4AI community.

### Become a Sponsor

Reach developers building with Crawl4AI
Learn More →
[ Crawl4AI Marketplace · Updated -- ]

---

## Fonte: https://docs.crawl4ai.com/extraction/no-llm-strategies

[Crawl4AI Documentation (v0.7.x)](https://docs.crawl4ai.com/)

- [ Home ](https://docs.crawl4ai.com/)
- [ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/)
- [ Quick Start ](https://docs.crawl4ai.com/core/quickstart/)
- [ Code Examples ](https://docs.crawl4ai.com/core/examples/)
- [ Brand Book ](https://docs.crawl4ai.com/branding/)
- [ Search ](https://docs.crawl4ai.com/extraction/no-llm-strategies/)

[ unclecode/crawl4ai ](https://github.com/unclecode/crawl4ai)
×

- [Home](https://docs.crawl4ai.com/)
- [Ask AI](https://docs.crawl4ai.com/core/ask-ai/)
- [Quick Start](https://docs.crawl4ai.com/core/quickstart/)
- [Code Examples](https://docs.crawl4ai.com/core/examples/)
- Apps
  - [Demo Apps](https://docs.crawl4ai.com/apps/)
  - [C4A-Script Editor](https://docs.crawl4ai.com/apps/c4a-script/)
  - [LLM Context Builder](https://docs.crawl4ai.com/apps/llmtxt/)
  - [Marketplace](https://docs.crawl4ai.com/marketplace/)
  - [Marketplace Admin](https://docs.crawl4ai.com/marketplace/admin/)
- Setup & Installation
  - [Installation](https://docs.crawl4ai.com/core/installation/)
  - [Docker Deployment](https://docs.crawl4ai.com/core/docker-deployment/)
- Blog & Changelog
  - [Blog Home](https://docs.crawl4ai.com/blog/)
  - [Changelog](https://github.com/unclecode/crawl4ai/blob/main/CHANGELOG.md)
- Core
  - [Command Line Interface](https://docs.crawl4ai.com/core/cli/)
  - [Simple Crawling](https://docs.crawl4ai.com/core/simple-crawling/)
  - [Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/)
  - [Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/)
  - [URL Seeding](https://docs.crawl4ai.com/core/url-seeding/)
  - [C4A-Script](https://docs.crawl4ai.com/core/c4a-script/)
  - [Crawler Result](https://docs.crawl4ai.com/core/crawler-result/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/core/browser-crawler-config/)
  - [Markdown Generation](https://docs.crawl4ai.com/core/markdown-generation/)
  - [Fit Markdown](https://docs.crawl4ai.com/core/fit-markdown/)
  - [Page Interaction](https://docs.crawl4ai.com/core/page-interaction/)
  - [Content Selection](https://docs.crawl4ai.com/core/content-selection/)
  - [Cache Modes](https://docs.crawl4ai.com/core/cache-modes/)
  - [Local Files & Raw HTML](https://docs.crawl4ai.com/core/local-files/)
  - [Link & Media](https://docs.crawl4ai.com/core/link-media/)
- Advanced
  - [Overview](https://docs.crawl4ai.com/advanced/advanced-features/)
  - [Adaptive Strategies](https://docs.crawl4ai.com/advanced/adaptive-strategies/)
  - [Virtual Scroll](https://docs.crawl4ai.com/advanced/virtual-scroll/)
  - [File Downloading](https://docs.crawl4ai.com/advanced/file-downloading/)
  - [Lazy Loading](https://docs.crawl4ai.com/advanced/lazy-loading/)
  - [Hooks & Auth](https://docs.crawl4ai.com/advanced/hooks-auth/)
  - [Proxy & Security](https://docs.crawl4ai.com/advanced/proxy-security/)
  - [Undetected Browser](https://docs.crawl4ai.com/advanced/undetected-browser/)
  - [Session Management](https://docs.crawl4ai.com/advanced/session-management/)
  - [Multi-URL Crawling](https://docs.crawl4ai.com/advanced/multi-url-crawling/)
  - [Crawl Dispatcher](https://docs.crawl4ai.com/advanced/crawl-dispatcher/)
  - [Identity Based Crawling](https://docs.crawl4ai.com/advanced/identity-based-crawling/)
  - [SSL Certificate](https://docs.crawl4ai.com/advanced/ssl-certificate/)
  - [Network & Console Capture](https://docs.crawl4ai.com/advanced/network-console-capture/)
  - [PDF Parsing](https://docs.crawl4ai.com/advanced/pdf-parsing/)
- Extraction
  - LLM-Free Strategies
  - [LLM Strategies](https://docs.crawl4ai.com/extraction/llm-strategies/)
  - [Clustering Strategies](https://docs.crawl4ai.com/extraction/clustring-strategies/)
  - [Chunking](https://docs.crawl4ai.com/extraction/chunking/)
- API Reference
  - [AsyncWebCrawler](https://docs.crawl4ai.com/api/async-webcrawler/)
  - [arun()](https://docs.crawl4ai.com/api/arun/)
  - [arun_many()](https://docs.crawl4ai.com/api/arun_many/)
  - [Browser, Crawler & LLM Config](https://docs.crawl4ai.com/api/parameters/)
  - [CrawlResult](https://docs.crawl4ai.com/api/crawl-result/)
  - [Strategies](https://docs.crawl4ai.com/api/strategies/)
  - [C4A-Script Reference](https://docs.crawl4ai.com/api/c4a-script-reference/)
- [Brand Book](https://docs.crawl4ai.com/branding/)

---

- [Extracting JSON (No LLM)](https://docs.crawl4ai.com/extraction/no-llm-strategies/#extracting-json-no-llm)
- [1. Intro to Schema-Based Extraction](https://docs.crawl4ai.com/extraction/no-llm-strategies/#1-intro-to-schema-based-extraction)
- [2. Simple Example: Crypto Prices](https://docs.crawl4ai.com/extraction/no-llm-strategies/#2-simple-example-crypto-prices)
- [3. Advanced Schema & Nested Structures](https://docs.crawl4ai.com/extraction/no-llm-strategies/#3-advanced-schema-nested-structures)
- [4. RegexExtractionStrategy - Fast Pattern-Based Extraction](https://docs.crawl4ai.com/extraction/no-llm-strategies/#4-regexextractionstrategy-fast-pattern-based-extraction)
- [5. Why "No LLM" Is Often Better](https://docs.crawl4ai.com/extraction/no-llm-strategies/#5-why-no-llm-is-often-better)
- [6. Base Element Attributes & Additional Fields](https://docs.crawl4ai.com/extraction/no-llm-strategies/#6-base-element-attributes-additional-fields)
- [7. Putting It All Together: Larger Example](https://docs.crawl4ai.com/extraction/no-llm-strategies/#7-putting-it-all-together-larger-example)
- [8. Tips & Best Practices](https://docs.crawl4ai.com/extraction/no-llm-strategies/#8-tips-best-practices)
- [9. Schema Generation Utility](https://docs.crawl4ai.com/extraction/no-llm-strategies/#9-schema-generation-utility)
- [10. Conclusion](https://docs.crawl4ai.com/extraction/no-llm-strategies/#10-conclusion)

# Extracting JSON (No LLM)

One of Crawl4AI's **most powerful** features is extracting **structured JSON** from websites **without** relying on large language models. Crawl4AI offers several strategies for LLM-free extraction:

1. **Schema-based extraction** with CSS or XPath selectors via `JsonCssExtractionStrategy` and `JsonXPathExtractionStrategy`
2. **Regular expression extraction** with `RegexExtractionStrategy` for fast pattern matching

These approaches let you extract data instantly—even from complex or nested HTML structures—without the cost, latency, or environmental impact of an LLM.
**Why avoid LLM for basic extractions?**

1. **Faster & Cheaper**: No API calls or GPU overhead.
2. **Lower Carbon Footprint** : LLM inference can be energy-intensive. Pattern-based extraction is practically carbon-free.
3. **Precise & Repeatable**: CSS/XPath selectors and regex patterns do exactly what you specify. LLM outputs can vary or hallucinate.
4. **Scales Readily** : For thousands of pages, pattern-based extraction runs quickly and in parallel.

Below, we'll explore how to craft these schemas and use them with **JsonCssExtractionStrategy** (or **JsonXPathExtractionStrategy** if you prefer XPath). We'll also highlight advanced features like **nested fields** and **base element attributes**.

---

## 1. Intro to Schema-Based Extraction

A schema defines:

1. A **base selector** that identifies each "container" element on the page (e.g., a product row, a blog post card).
2. **Fields** describing which CSS/XPath selectors to use for each piece of data you want to capture (text, attribute, HTML block, etc.).
3. **Nested** or **list** types for repeated or hierarchical structures.

For example, if you have a list of products, each one might have a name, price, reviews, and "related products." This approach is faster and more reliable than an LLM for consistent, structured pages.

---

## 2. Simple Example: Crypto Prices

Let's begin with a **simple** schema-based extraction using the `JsonCssExtractionStrategy`. Below is a snippet that extracts cryptocurrency prices from a site (similar to the legacy Coinbase example). Notice we **don't** call any LLM:

```
import json
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy

async def extract_crypto_prices():
    # 1. Define a simple extraction schema
    schema = {
        "name": "Crypto Prices",
        "baseSelector": "div.crypto-row",    # Repeated elements
        "fields": [
            {
                "name": "coin_name",
                "selector": "h2.coin-name",
                "type": "text"
            },
            {
                "name": "price",
                "selector": "span.coin-price",
                "type": "text"
            }
        ]
    }

    # 2. Create the extraction strategy
    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)

    # 3. Set up your crawler config (if needed)
    config = CrawlerRunConfig(
        # e.g., pass js_code or wait_for if the page is dynamic
        # wait_for="css:.crypto-row:nth-child(20)"
        cache_mode = CacheMode.BYPASS,
        extraction_strategy=extraction_strategy,
    )

    async with AsyncWebCrawler(verbose=True) as crawler:
        # 4. Run the crawl and extraction
        result = await crawler.arun(
            url="https://example.com/crypto-prices",

            config=config
        )

        if not result.success:
            print("Crawl failed:", result.error_message)
            return

        # 5. Parse the extracted JSON
        data = json.loads(result.extracted_content)
        print(f"Extracted {len(data)} coin entries")
        print(json.dumps(data[0], indent=2) if data else "No data found")

asyncio.run(extract_crypto_prices())
Copy
```

**Highlights** :

- **`baseSelector`**: Tells us where each "item" (crypto row) is.
- **`fields`**: Two fields (`coin_name` , `price`) using simple CSS selectors.
- Each field defines a **`type`**(e.g.,`text` , `attribute`, `html`, `regex`, etc.).

No LLM is needed, and the performance is **near-instant** for hundreds or thousands of items.

---

### **XPath Example with`raw://` HTML**

Below is a short example demonstrating **XPath** extraction plus the **`raw://`**scheme. We'll pass a**dummy HTML** directly (no network request) and define the extraction strategy in `CrawlerRunConfig`.

```
import json
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai import JsonXPathExtractionStrategy

async def extract_crypto_prices_xpath():
    # 1. Minimal dummy HTML with some repeating rows
    dummy_html = """
    <html>
      <body>
        <div class='crypto-row'>
          <h2 class='coin-name'>Bitcoin</h2>
          <span class='coin-price'>$28,000</span>
        </div>
        <div class='crypto-row'>
          <h2 class='coin-name'>Ethereum</h2>
          <span class='coin-price'>$1,800</span>
        </div>
      </body>
    </html>
    """

    # 2. Define the JSON schema (XPath version)
    schema = {
        "name": "Crypto Prices via XPath",
        "baseSelector": "//div[@class='crypto-row']",
        "fields": [
            {
                "name": "coin_name",
                "selector": ".//h2[@class='coin-name']",
                "type": "text"
            },
            {
                "name": "price",
                "selector": ".//span[@class='coin-price']",
                "type": "text"
            }
        ]
    }

    # 3. Place the strategy in the CrawlerRunConfig
    config = CrawlerRunConfig(
        extraction_strategy=JsonXPathExtractionStrategy(schema, verbose=True)
    )

    # 4. Use raw:// scheme to pass dummy_html directly
    raw_url = f"raw://{dummy_html}"

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=raw_url,
            config=config
        )

        if not result.success:
            print("Crawl failed:", result.error_message)
            return

        data = json.loads(result.extracted_content)
        print(f"Extracted {len(data)} coin rows")
        if data:
            print("First item:", data[0])

asyncio.run(extract_crypto_prices_xpath())
Copy
```

**Key Points** :

1. **`JsonXPathExtractionStrategy`**is used instead of`JsonCssExtractionStrategy`.
2. **`baseSelector`**and each field's`"selector"` use **XPath** instead of CSS.
3. **`raw://`**lets us pass`dummy_html` with no real network request—handy for local testing.
4. Everything (including the extraction strategy) is in **`CrawlerRunConfig`**.

That's how you keep the config self-contained, illustrate **XPath** usage, and demonstrate the **raw** scheme for direct HTML input—all while avoiding the old approach of passing `extraction_strategy` directly to `arun()`.

---

## 3. Advanced Schema & Nested Structures

Real sites often have **nested** or repeated data—like categories containing products, which themselves have a list of reviews or features. For that, we can define **nested** or **list** (and even **nested_list**) fields.

### Sample E-Commerce HTML

We have a **sample e-commerce** HTML file on GitHub (example):

```
https://gist.githubusercontent.com/githubusercontent/2d7b8ba3cd8ab6cf3c8da771ddb36878/raw/1ae2f90c6861ce7dd84cc50d3df9920dee5e1fd2/sample_ecommerce.html
Copy
```

This snippet includes categories, products, features, reviews, and related items. Let's see how to define a schema that fully captures that structure **without LLM**.

```
schema = {
    "name": "E-commerce Product Catalog",
    "baseSelector": "div.category",
    # (1) We can define optional baseFields if we want to extract attributes
    # from the category container
    "baseFields": [
        {"name": "data_cat_id", "type": "attribute", "attribute": "data-cat-id"},
    ],
    "fields": [
        {
            "name": "category_name",
            "selector": "h2.category-name",
            "type": "text"
        },
        {
            "name": "products",
            "selector": "div.product",
            "type": "nested_list",    # repeated sub-objects
            "fields": [
                {
                    "name": "name",
                    "selector": "h3.product-name",
                    "type": "text"
                },
                {
                    "name": "price",
                    "selector": "p.product-price",
                    "type": "text"
                },
                {
                    "name": "details",
                    "selector": "div.product-details",
                    "type": "nested",  # single sub-object
                    "fields": [
                        {
                            "name": "brand",
                            "selector": "span.brand",
                            "type": "text"
                        },
                        {
                            "name": "model",
                            "selector": "span.model",
                            "type": "text"
                        }
                    ]
                },
                {
                    "name": "features",
                    "selector": "ul.product-features li",
                    "type": "list",
                    "fields": [
                        {"name": "feature", "type": "text"}
                    ]
                },
                {
                    "name": "reviews",
                    "selector": "div.review",
                    "type": "nested_list",
                    "fields": [
                        {
                            "name": "reviewer",
                            "selector": "span.reviewer",
                            "type": "text"
                        },
                        {
                            "name": "rating",
                            "selector": "span.rating",
                            "type": "text"
                        },
                        {
                            "name": "comment",
                            "selector": "p.review-text",
                            "type": "text"
                        }
                    ]
                },
                {
                    "name": "related_products",
                    "selector": "ul.related-products li",
                    "type": "list",
                    "fields": [
                        {
                            "name": "name",
                            "selector": "span.related-name",
                            "type": "text"
                        },
                        {
                            "name": "price",
                            "selector": "span.related-price",
                            "type": "text"
                        }
                    ]
                }
            ]
        }
    ]
}
Copy
```

Key Takeaways:

- **Nested vs. List** :
- **`type: "nested"`**means a**single** sub-object (like `details`).
- **`type: "list"`**means multiple items that are**simple** dictionaries or single text fields.
- **`type: "nested_list"`**means repeated**complex** objects (like `products` or `reviews`).
- **Base Fields** : We can extract **attributes** from the container element via `"baseFields"`. For instance, `"data_cat_id"` might be `data-cat-id="elect123"`.
- **Transforms** : We can also define a `transform` if we want to lower/upper case, strip whitespace, or even run a custom function.

### Running the Extraction

```
import json
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai import JsonCssExtractionStrategy

ecommerce_schema = {
    # ... the advanced schema from above ...
}

async def extract_ecommerce_data():
    strategy = JsonCssExtractionStrategy(ecommerce_schema, verbose=True)

    config = CrawlerRunConfig()

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url="https://gist.githubusercontent.com/githubusercontent/2d7b8ba3cd8ab6cf3c8da771ddb36878/raw/1ae2f90c6861ce7dd84cc50d3df9920dee5e1fd2/sample_ecommerce.html",
            extraction_strategy=strategy,
            config=config
        )

        if not result.success:
            print("Crawl failed:", result.error_message)
            return

        # Parse the JSON output
        data = json.loads(result.extracted_content)
        print(json.dumps(data, indent=2) if data else "No data found.")

asyncio.run(extract_ecommerce_data())
Copy
```

If all goes well, you get a **structured** JSON array with each "category," containing an array of `products`. Each product includes `details`, `features`, `reviews`, etc. All of that **without** an LLM.

---

## 4. RegexExtractionStrategy - Fast Pattern-Based Extraction

Crawl4AI now offers a powerful new zero-LLM extraction strategy: `RegexExtractionStrategy`. This strategy provides lightning-fast extraction of common data types like emails, phone numbers, URLs, dates, and more using pre-compiled regular expressions.

### Key Features

- **Zero LLM Dependency** : Extracts data without any AI model calls
- **Blazing Fast** : Uses pre-compiled regex patterns for maximum performance
- **Built-in Patterns** : Includes ready-to-use patterns for common data types
- **Custom Patterns** : Add your own regex patterns for domain-specific extraction
- **LLM-Assisted Pattern Generation** : Optionally use an LLM once to generate optimized patterns, then reuse them without further LLM calls

### Simple Example: Extracting Common Entities

The easiest way to start is by using the built-in pattern catalog:

```
import json
import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    RegexExtractionStrategy
)

async def extract_with_regex():
    # Create a strategy using built-in patterns for URLs and currencies
    strategy = RegexExtractionStrategy(
        pattern = RegexExtractionStrategy.Url | RegexExtractionStrategy.Currency
    )

    config = CrawlerRunConfig(extraction_strategy=strategy)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=config
        )

        if result.success:
            data = json.loads(result.extracted_content)
            for item in data[:5]:  # Show first 5 matches
                print(f"{item['label']}: {item['value']}")
            print(f"Total matches: {len(data)}")

asyncio.run(extract_with_regex())
Copy
```

### Available Built-in Patterns

`RegexExtractionStrategy` provides these common patterns as IntFlag attributes for easy combining:

```
# Use individual patterns
strategy = RegexExtractionStrategy(pattern=RegexExtractionStrategy.Email)

# Combine multiple patterns
strategy = RegexExtractionStrategy(
    pattern = (
        RegexExtractionStrategy.Email |
        RegexExtractionStrategy.PhoneUS |
        RegexExtractionStrategy.Url
    )
)

# Use all available patterns
strategy = RegexExtractionStrategy(pattern=RegexExtractionStrategy.All)
Copy
```

Available patterns include: - `Email` - Email addresses - `PhoneIntl` - International phone numbers - `PhoneUS` - US-format phone numbers - `Url` - HTTP/HTTPS URLs - `IPv4` - IPv4 addresses - `IPv6` - IPv6 addresses - `Uuid` - UUIDs - `Currency` - Currency values (USD, EUR, etc.) - `Percentage` - Percentage values - `Number` - Numeric values - `DateIso` - ISO format dates - `DateUS` - US format dates - `Time24h` - 24-hour format times - `PostalUS` - US postal codes - `PostalUK` - UK postal codes - `HexColor` - HTML hex color codes - `TwitterHandle` - Twitter handles - `Hashtag` - Hashtags - `MacAddr` - MAC addresses - `Iban` - International bank account numbers - `CreditCard` - Credit card numbers

### Custom Pattern Example

For more targeted extraction, you can provide custom patterns:

```
import json
import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    RegexExtractionStrategy
)

async def extract_prices():
    # Define a custom pattern for US Dollar prices
    price_pattern = {"usd_price": r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?"}

    # Create strategy with custom pattern
    strategy = RegexExtractionStrategy(custom=price_pattern)
    config = CrawlerRunConfig(extraction_strategy=strategy)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.example.com/products",
            config=config
        )

        if result.success:
            data = json.loads(result.extracted_content)
            for item in data:
                print(f"Found price: {item['value']}")

asyncio.run(extract_prices())
Copy
```

### LLM-Assisted Pattern Generation

For complex or site-specific patterns, you can use an LLM once to generate an optimized pattern, then save and reuse it without further LLM calls:

```
import json
import asyncio
from pathlib import Path
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    RegexExtractionStrategy,
    LLMConfig
)

async def extract_with_generated_pattern():
    cache_dir = Path("./pattern_cache")
    cache_dir.mkdir(exist_ok=True)
    pattern_file = cache_dir / "price_pattern.json"

    # 1. Generate or load pattern
    if pattern_file.exists():
        pattern = json.load(pattern_file.open())
        print(f"Using cached pattern: {pattern}")
    else:
        print("Generating pattern via LLM...")

        # Configure LLM
        llm_config = LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token="env:OPENAI_API_KEY",
        )

        # Get sample HTML for context
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://example.com/products")
            html = result.fit_html

        # Generate pattern (one-time LLM usage)
        pattern = RegexExtractionStrategy.generate_pattern(
            label="price",
            html=html,
            query="Product prices in USD format",
            llm_config=llm_config,
        )

        # Cache pattern for future use
        json.dump(pattern, pattern_file.open("w"), indent=2)

    # 2. Use pattern for extraction (no LLM calls)
    strategy = RegexExtractionStrategy(custom=pattern)
    config = CrawlerRunConfig(extraction_strategy=strategy)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com/products",
            config=config
        )

        if result.success:
            data = json.loads(result.extracted_content)
            for item in data[:10]:
                print(f"Extracted: {item['value']}")
            print(f"Total matches: {len(data)}")

asyncio.run(extract_with_generated_pattern())
Copy
```

This pattern allows you to: 1. Use an LLM once to generate a highly optimized regex for your specific site 2. Save the pattern to disk for reuse 3. Extract data using only regex (no further LLM calls) in production

### Extraction Results Format

The `RegexExtractionStrategy` returns results in a consistent format:

```
[
  {
    "url": "https://example.com",
    "label": "email",
    "value": "contact@example.com",
    "span": [145, 163]
  },
  {
    "url": "https://example.com",
    "label": "url",
    "value": "https://support.example.com",
    "span": [210, 235]
  }
]
Copy
```

Each match includes: - `url`: The source URL - `label`: The pattern name that matched (e.g., "email", "phone_us") - `value`: The extracted text - `span`: The start and end positions in the source content

---

## 5. Why "No LLM" Is Often Better

1. **Zero Hallucination** : Pattern-based extraction doesn't guess text. It either finds it or not.
2. **Guaranteed Structure** : The same schema or regex yields consistent JSON across many pages, so your downstream pipeline can rely on stable keys.
3. **Speed** : LLM-based extraction can be 10–1000x slower for large-scale crawling.
4. **Scalable** : Adding or updating a field is a matter of adjusting the schema or regex, not re-tuning a model.

**When might you consider an LLM?** Possibly if the site is extremely unstructured or you want AI summarization. But always try a schema or regex approach first for repeated or consistent data patterns.

---

## 6. Base Element Attributes & Additional Fields

It's easy to **extract attributes** (like `href`, `src`, or `data-xxx`) from your base or nested elements using:

```
{
  "name": "href",
  "type": "attribute",
  "attribute": "href",
  "default": null
}
Copy
```

You can define them in **`baseFields`**(extracted from the main container element) or in each field's sub-lists. This is especially helpful if you need an item's link or ID stored in the parent`<div>`.

---

## 7. Putting It All Together: Larger Example

Consider a blog site. We have a schema that extracts the **URL** from each post card (via `baseFields` with an `"attribute": "href"`), plus the title, date, summary, and author:

```
schema = {
  "name": "Blog Posts",
  "baseSelector": "a.blog-post-card",
  "baseFields": [
    {"name": "post_url", "type": "attribute", "attribute": "href"}
  ],
  "fields": [
    {"name": "title", "selector": "h2.post-title", "type": "text", "default": "No Title"},
    {"name": "date", "selector": "time.post-date", "type": "text", "default": ""},
    {"name": "summary", "selector": "p.post-summary", "type": "text", "default": ""},
    {"name": "author", "selector": "span.post-author", "type": "text", "default": ""}
  ]
}
Copy
```

Then run with `JsonCssExtractionStrategy(schema)` to get an array of blog post objects, each with `"post_url"`, `"title"`, `"date"`, `"summary"`, `"author"`.

---

## 8. Tips & Best Practices

1. **Inspect the DOM** in Chrome DevTools or Firefox's Inspector to find stable selectors.
2. **Start Simple** : Verify you can extract a single field. Then add complexity like nested objects or lists.
3. **Test** your schema on partial HTML or a test page before a big crawl.
4. **Combine with JS Execution** if the site loads content dynamically. You can pass `js_code` or `wait_for` in `CrawlerRunConfig`.
5. **Look at Logs** when `verbose=True`: if your selectors are off or your schema is malformed, it'll often show warnings.
6. **Use baseFields** if you need attributes from the container element (e.g., `href`, `data-id`), especially for the "parent" item.
7. **Performance** : For large pages, make sure your selectors are as narrow as possible.
8. **Consider Using Regex First** : For simple data types like emails, URLs, and dates, `RegexExtractionStrategy` is often the fastest approach.

---

## 9. Schema Generation Utility

While manually crafting schemas is powerful and precise, Crawl4AI now offers a convenient utility to **automatically generate** extraction schemas using LLM. This is particularly useful when:

1. You're dealing with a new website structure and want a quick starting point
2. You need to extract complex nested data structures
3. You want to avoid the learning curve of CSS/XPath selector syntax

### Using the Schema Generator

The schema generator is available as a static method on both `JsonCssExtractionStrategy` and `JsonXPathExtractionStrategy`. You can choose between OpenAI's GPT-4 or the open-source Ollama for schema generation:

```
from crawl4ai import JsonCssExtractionStrategy, JsonXPathExtractionStrategy
from crawl4ai import LLMConfig

# Sample HTML with product information
html = """
<div class="product-card">
    <h2 class="title">Gaming Laptop</h2>
    <div class="price">$999.99</div>
    <div class="specs">
        <ul>
            <li>16GB RAM</li>
            <li>1TB SSD</li>
        </ul>
    </div>
</div>
"""

# Option 1: Using OpenAI (requires API token)
css_schema = JsonCssExtractionStrategy.generate_schema(
    html,
    schema_type="css",
    llm_config = LLMConfig(provider="openai/gpt-4o",api_token="your-openai-token")
)

# Option 2: Using Ollama (open source, no token needed)
xpath_schema = JsonXPathExtractionStrategy.generate_schema(
    html,
    schema_type="xpath",
    llm_config = LLMConfig(provider="ollama/llama3.3", api_token=None)  # Not needed for Ollama
)

# Use the generated schema for fast, repeated extractions
strategy = JsonCssExtractionStrategy(css_schema)
Copy
```

### LLM Provider Options

1. **OpenAI GPT-4 (`openai/gpt4o`)**
2. Default provider
3. Requires an API token
4. Generally provides more accurate schemas
5. Set via environment variable: `OPENAI_API_KEY`
6. **Ollama (`ollama/llama3.3`)**
7. Open source alternative
8. No API token required
9. Self-hosted option
10. Good for development and testing

### Benefits of Schema Generation

1. **One-Time Cost** : While schema generation uses LLM, it's a one-time cost. The generated schema can be reused for unlimited extractions without further LLM calls.
2. **Smart Pattern Recognition** : The LLM analyzes the HTML structure and identifies common patterns, often producing more robust selectors than manual attempts.
3. **Automatic Nesting** : Complex nested structures are automatically detected and properly represented in the schema.
4. **Learning Tool** : The generated schemas serve as excellent examples for learning how to write your own schemas.

### Best Practices

1. **Review Generated Schemas** : While the generator is smart, always review and test the generated schema before using it in production.
2. **Provide Representative HTML** : The better your sample HTML represents the overall structure, the more accurate the generated schema will be.
3. **Consider Both CSS and XPath** : Try both schema types and choose the one that works best for your specific case.
4. **Cache Generated Schemas** : Since generation uses LLM, save successful schemas for reuse.
5. **API Token Security** : Never hardcode API tokens. Use environment variables or secure configuration management.
6. **Choose Provider Wisely** :
7. Use OpenAI for production-quality schemas
8. Use Ollama for development, testing, or when you need a self-hosted solution

---

## 10. Conclusion

With Crawl4AI's LLM-free extraction strategies - `JsonCssExtractionStrategy`, `JsonXPathExtractionStrategy`, and now `RegexExtractionStrategy` - you can build powerful pipelines that:

- Scrape any consistent site for structured data.
- Support nested objects, repeating lists, or pattern-based extraction.
- Scale to thousands of pages quickly and reliably.

**Choosing the Right Strategy** :

- Use **`RegexExtractionStrategy`**for fast extraction of common data types like emails, phones, URLs, dates, etc.
- Use **`JsonCssExtractionStrategy`**or**`JsonXPathExtractionStrategy`**for structured data with clear HTML patterns
- If you need both: first extract structured data with JSON strategies, then use regex on specific fields

**Remember** : For repeated, structured data, you don't need to pay for or wait on an LLM. Well-crafted schemas and regex patterns get you the data faster, cleaner, and cheaper—**the real power** of Crawl4AI.
**Last Updated** : 2025-05-02

---

That's it for **Extracting JSON (No LLM)**! You've seen how schema-based approaches (either CSS or XPath) and regex patterns can handle everything from simple lists to deeply nested product catalogs—instantly, with minimal overhead. Enjoy building robust scrapers that produce consistent, structured JSON for your data pipelines!
Page Copy
Page Copy

- [ Copy as Markdown Copy page for LLMs ](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
- [ View as Markdown Open raw source ](https://docs.crawl4ai.com/extraction/no-llm-strategies/)
- [ Ask AI about page Coming Soon ](https://docs.crawl4ai.com/extraction/no-llm-strategies/)

ESC to close

#### On this page

- [1. Intro to Schema-Based Extraction](https://docs.crawl4ai.com/extraction/no-llm-strategies/#1-intro-to-schema-based-extraction)
- [2. Simple Example: Crypto Prices](https://docs.crawl4ai.com/extraction/no-llm-strategies/#2-simple-example-crypto-prices)
- [XPath Example with raw:// HTML](https://docs.crawl4ai.com/extraction/no-llm-strategies/#xpath-example-with-raw-html)
- [3. Advanced Schema & Nested Structures](https://docs.crawl4ai.com/extraction/no-llm-strategies/#3-advanced-schema-nested-structures)
- [Sample E-Commerce HTML](https://docs.crawl4ai.com/extraction/no-llm-strategies/#sample-e-commerce-html)
- [Running the Extraction](https://docs.crawl4ai.com/extraction/no-llm-strategies/#running-the-extraction)
- [4. RegexExtractionStrategy - Fast Pattern-Based Extraction](https://docs.crawl4ai.com/extraction/no-llm-strategies/#4-regexextractionstrategy-fast-pattern-based-extraction)
- [Key Features](https://docs.crawl4ai.com/extraction/no-llm-strategies/#key-features)
- [Simple Example: Extracting Common Entities](https://docs.crawl4ai.com/extraction/no-llm-strategies/#simple-example-extracting-common-entities)
- [Available Built-in Patterns](https://docs.crawl4ai.com/extraction/no-llm-strategies/#available-built-in-patterns)
- [Custom Pattern Example](https://docs.crawl4ai.com/extraction/no-llm-strategies/#custom-pattern-example)
- [LLM-Assisted Pattern Generation](https://docs.crawl4ai.com/extraction/no-llm-strategies/#llm-assisted-pattern-generation)
- [Extraction Results Format](https://docs.crawl4ai.com/extraction/no-llm-strategies/#extraction-results-format)
- [5. Why "No LLM" Is Often Better](https://docs.crawl4ai.com/extraction/no-llm-strategies/#5-why-no-llm-is-often-better)
- [6. Base Element Attributes & Additional Fields](https://docs.crawl4ai.com/extraction/no-llm-strategies/#6-base-element-attributes-additional-fields)
- [7. Putting It All Together: Larger Example](https://docs.crawl4ai.com/extraction/no-llm-strategies/#7-putting-it-all-together-larger-example)
- [8. Tips & Best Practices](https://docs.crawl4ai.com/extraction/no-llm-strategies/#8-tips-best-practices)
- [9. Schema Generation Utility](https://docs.crawl4ai.com/extraction/no-llm-strategies/#9-schema-generation-utility)
- [Using the Schema Generator](https://docs.crawl4ai.com/extraction/no-llm-strategies/#using-the-schema-generator)
- [LLM Provider Options](https://docs.crawl4ai.com/extraction/no-llm-strategies/#llm-provider-options)
- [Benefits of Schema Generation](https://docs.crawl4ai.com/extraction/no-llm-strategies/#benefits-of-schema-generation)
- [Best Practices](https://docs.crawl4ai.com/extraction/no-llm-strategies/#best-practices)
- [10. Conclusion](https://docs.crawl4ai.com/extraction/no-llm-strategies/#10-conclusion)

---

> Feedback

##### Search

xClose
Type to start searching
[ Ask AI ](https://docs.crawl4ai.com/core/ask-ai/ "Ask Crawl4AI Assistant")

---

# Documentação de Crawl4ai Documentation

## Fonte: https://docs.crawl4ai.com/advanced/

# 403 Forbidden

---

nginx/1.24.0 (Ubuntu)

---
