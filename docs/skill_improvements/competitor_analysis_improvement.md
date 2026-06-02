# Skill Improvement Report: competitor_analysis
**Date:** 2026-05-30T00:11:24Z
**Round:** 1

## What Changed

### Before (template in templates.py)
- Prompt written entirely in Portuguese — violates the rule that Langfuse prompts must be in English
- Instructions were minimal: just 4 section titles with brief descriptions
- No explicit constraints on hallucination of competitor metrics
- No Jinja guards on optional variables (missing `{% if foco %}` etc.)
- No pitfalls/edge case documentation
- No output format declaration (word limits, language spec, footer)
- Architecture and trigger not described — hard for frontdesk to route correctly

### After (new Langfuse prompt)
- Full prompt rewritten in **English** with structured sections
- Explicit **Trigger** sentence for frontdesk routing
- **Architecture** block: input → processing → output pipeline
- **Tool Rules** with numbered steps — including fallback when `concorrentes_conteudo` is empty
- **Constraints** block: hallucination guardrails, language enforcement (PT-BR), max_turns, Jinja guards for all optional vars
- **Output Format** fully specified: 4 mandatory sections, table/bullet structure, footer, max ~600 words
- **Pitfalls** section: hallucinated metrics, missing sections, language slip, generic output, competitor conflation, stale data

### Patterns borrowed from
- Hermes `research/blogwatcher` skill: trigger condition phrasing, constraint blocks, output format declaration
- Hermes skill library structural patterns: numbered tool rules, pitfall sections, explicit Jinja guard documentation

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current: _"Produce a competitive analysis comparing the client's performance against scraped competitor content: positioning, gaps, opportunities, and threats."_ → Suggested: _"Produce a structured 4-section competitive intelligence report comparing client positioning, gaps, opportunities, and threats against mapped competitors. Requires competitor content context."_ (more specific about the 4-section structure and context dependency)
- **required_tool_names**: Currently empty `[]` — consider adding a `web_scraper` or `competitor_content_fetcher` tool so the skill can autonomously fetch competitor data rather than relying on pre-provided context. Without a tool, the skill is dependent on upstream data injection.
- **max_turns**: 4 seems appropriate for a structured report with possible clarification turns. Could be reduced to 3 if competitive data is always pre-loaded.
- **tags**: Current: `["routines", "strategy", "competitive", "analysis"]` → Suggest adding `"intelligence"` and `"market"` for better routing: `["routines", "strategy", "competitive", "analysis", "intelligence", "market"]`

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `competitor_monitor` | Automated periodic monitoring of competitor websites/social media for changes in pricing, messaging, or product updates | `competitive`, `monitor` | monitor_agent |
| `swot_analysis` | Generate a structured SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) for the client company based on CRM + financial data | `strategy`, `analysis` | strategy_agent |
| `market_positioning` | Analyze the client's market positioning relative to industry benchmarks and suggest repositioning strategies | `strategy`, `market` | strategy_agent |
| `pricing_intelligence` | Extract and compare competitor pricing from scraped pages or provided content, generating a pricing benchmark report | `competitive`, `finance` | analytics_agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `web_scraper` | Scrape public competitor websites, product pages, and pricing pages on demand | `competitor_analysis`, `competitor_monitor`, `pricing_intelligence` |
| `competitor_content_fetcher` | Fetch and cache competitor social media posts, blog updates, and news mentions via RSS/search APIs | `competitor_analysis`, `competitor_monitor` |
| `benchmark_lookup` | Query industry benchmark databases (e.g., SimilarWeb-like data) for traffic, engagement, and market share estimates | `competitor_analysis`, `market_positioning` |

---

## Langfuse Prompt Published

- **Prompt name:** `skill:competitor_analysis:system`
- **Labels:** `["production"]`
- **Tags:** `["skill", "competitor_analysis", "blu", "auto-improved"]`
- **Status:** ✅ Published (HTTP 201 — new prompt created, no prior version existed)
- **Langfuse ID:** `602b7c9e-87f1-4db7-b4f5-962adaeade02`
