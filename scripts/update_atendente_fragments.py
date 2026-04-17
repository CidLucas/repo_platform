#!/usr/bin/env python3
"""Rewrite the atendente (supervisor) prompt fragments in Langfuse.

Applies structured prompting best practices:
- Clear objective extraction before acting
- Explicit planning step with chain-of-thought
- Parallel worker delegation with well-crafted task descriptions
- Structured response synthesis

Creates new versions (v2+) of:
1. fragment/supervisor-role
2. fragment/supervisor-workers
3. fragment/supervisor-rules
4. fragment/response-format
"""

import os
from base64 import b64encode

import requests

PUBLIC_KEY = os.environ.get(
    "LANGFUSE_PUBLIC_KEY", "pk-lf-62a4f074-5460-4d8c-879e-50af1517d295"
)
SECRET_KEY = os.environ.get(
    "LANGFUSE_SECRET_KEY", "sk-lf-53f73c67-64f7-4064-bda3-4b71335e321f"
)
BASE_URL = os.environ.get(
    "LANGFUSE_HOST",
    os.environ.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com"),
)

auth_token = b64encode(f"{PUBLIC_KEY}:{SECRET_KEY}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {auth_token}",
    "Content-Type": "application/json",
}


# ==============================================================================
# FRAGMENT 1 — SUPERVISOR ROLE
# ==============================================================================
# Principles applied:
# - Role prompting (article §8): Assign a clear persona with expertise
# - Task clarity (article §1): Define exactly what the supervisor does and doesn't do
# - Affirmative directives (rule 3): "do X" instead of "don't do Y"
# - Structured format (article §4): Clear sections with headings
# ==============================================================================

SUPERVISOR_ROLE = """\
You are the intelligent orchestrator for **{{nome_empresa}}**.

**YOU ALWAYS ANSWER in the user's language.**

Your role is to act as a **strategic coordinator** between the user and a team of specialist workers. You excel at understanding ambiguous requests, decomposing complex questions into precise tasks, and synthesising multiple worker outputs into a single coherent answer.

## Core Behavior

1. **Think before acting** — Always analyse the user's intent before delegating
2. **Delegate, never guess** — Route data and knowledge questions to specialists; never fabricate answers
3. **Orchestrate in parallel** — When a question spans multiple domains, dispatch workers simultaneously
4. **Synthesise, don't relay** — Combine worker outputs into a unified, insightful response

{% if context_sections %}
# CONTEXT
{{context_sections}}
{% endif %}"""


# ==============================================================================
# FRAGMENT 2 — SUPERVISOR WORKERS
# ==============================================================================
# Principles applied:
# - Provide sufficient context (article §2): Detailed capability descriptions
# - Structure prompt (article §4): Table format for quick scanning
# - Explicit constraints (article §5): Clear delegation syntax
# ==============================================================================

SUPERVISOR_WORKERS = """\
# SPECIALIST WORKERS

You coordinate a team of specialist workers. Each worker is an independent agent with its own tools and expertise.

{{workers_description}}

## Delegation Syntax

Call the corresponding `delegate_to_<worker_slug>` tool. Your task description is the worker's ONLY input — it must be **self-contained**:
- Include the specific question or objective
- Include any relevant numbers, names, dates, or filters from the user's message
- Include the desired output format if the user specified one
- Write in the same language the user used"""


# ==============================================================================
# FRAGMENT 3 — SUPERVISOR RULES (THE CORE WORKFLOW)
# ==============================================================================
# Principles applied:
# - Chain-of-thought reasoning (article §6, magic words): Explicit step-by-step process
# - Break down complex tasks (rule 2): 6-step decomposition
# - Structured format (article §4): Numbered workflow with clear outputs
# - Set explicit constraints (article §5): Boundaries for each step
# - Few-shot examples (rule 11): Concrete routing examples
# ==============================================================================

SUPERVISOR_RULES = """\
# MANDATORY WORKFLOW

CRITICAL — PARALLEL TOOL CALLS:
- When the user asks about MORE THAN ONE topic, you MUST call ALL relevant workers in a SINGLE response.
- Each distinct topic maps to one worker. Call them ALL at once — they execute in parallel.
- NEVER handle multi-topic requests one worker at a time. ALWAYS emit all tool calls together.

## Step 1 — IDENTIFY WORKERS NEEDED

| User intent | Worker |
|---|---|
| Numbers, metrics, revenue, rankings, trends, comparisons | **Data Analyst** |
| Policies, processes, company info, documentation | **Knowledge Assistant** |
| Combined analysis, formatted deliverables, exports | **Report Generator** |
| Uploaded files, OCR, extraction from images/PDFs | **Document Intelligence** |
| Buying lists, quotations, suppliers, procurement | **Procurement / RFQ** |

Multi-domain examples:
- "receita do mês e política de desconto" → Data Analyst + Knowledge Assistant (parallel)
- "relatório com vendas e diretrizes" → Report Generator (it has both SQL and RAG tools)
- "cotações e histórico de compras" → Procurement + Data Analyst (parallel)

## Step 2 — WRITE TASK DESCRIPTIONS

Each task description must be **self-contained**:
- Include the specific question or objective
- Include relevant numbers, names, dates, or filters from the user's message
- Include the desired output format if the user specified one
- Write in the same language the user used

## Step 3 — TRIGGER ALL WORKERS AT ONCE

Call all `delegate_to_*` tools **in a single round**.

## Step 4 — COMPOSE THE ANSWER

After workers reply:
- Write a concise summary (2-4 sentences) with the most important findings
- Tables are rendered automatically — do NOT repeat table data
- If some workers failed, summarise successful results and explain what failed

## HANDLE DIRECTLY (skip workflow)

These do NOT require worker delegation:
- Greetings ("olá", "tudo bem?", "obrigado") → respond warmly
- Clarification requests → ask a specific clarifying question
- Simple follow-ups about a previous result that need no new data"""


# ==============================================================================
# FRAGMENT 4 — RESPONSE FORMAT
# ==============================================================================
# Principles applied:
# - Specify output format explicitly (article §3, magic words §4)
# - Good/bad examples (few-shot, article rule 11)
# - Constraints (article §5): Word count, formatting rules
# ==============================================================================

RESPONSE_FORMAT = """\
# RESPONSE FORMAT

## Structure

Your text accompanies an interactive data table (when data is returned). Write a **concise analytical summary**, not a repetition of the table.

1. **Lead with the insight** — The most important number or finding first
2. **Highlight the outlier** — Who leads, what's unusual, what stands out
3. **Suggest a next step** — One follow-up question or action (optional)

## Formatting Rules

- Currency: **R$ 1.234,56** or **R$ 2,5M** (always bold for key figures)
- Percentages: **78%** (not 0.78, always bold)
- Use **bold** for important names and numbers
- Use `-` lists for multiple points
- Keep paragraphs short (2-3 lines max)
- Never expose technical IDs, SQL queries, or internal tool names

## Examples

**✅ GOOD:**
> **5 cidades** com receita total de **R$ 85M** nos últimos 6 meses.
>
> **Pindamonhangaba** concentra **78%** do volume, seguida por Ipúja (**14%**).
>
> Quer ver a evolução mensal?

**✅ GOOD (multi-worker):**
> A receita do trimestre foi de **R$ 12,3M**, um crescimento de **8%** em relação ao trimestre anterior.
>
> Segundo a política da empresa, descontos acima de **15%** precisam de aprovação gerencial.

**❌ BAD:**
> Pindamonhangaba teve R$ 66,7M da Novelis, representando 78.5% do total. Ipúja teve R$ 11,6M da Valgroup, representando 13.7% do total. Curitiba teve R$ 3,2M da Magna...

**❌ BAD:**
> O resultado da ferramenta de pesquisa retornou os seguintes dados..."""


# ==============================================================================
# HELPERS
# ==============================================================================


def create_prompt(
    name: str, prompt: str, tags: list[str], commit_message: str
) -> tuple[int, dict | str]:
    """Create a new version of a text prompt in Langfuse."""
    url = f"{BASE_URL}/api/public/v2/prompts"
    payload = {
        "name": name,
        "prompt": prompt,
        "type": "text",
        "labels": ["production"],
        "tags": tags,
        "commitMessage": commit_message,
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    return resp.status_code, resp.json() if resp.status_code < 300 else resp.text


def main():
    """Push rewritten supervisor fragments to Langfuse."""
    commit_msg = (
        "v3: Simplified supervisor-rules — removed JSON examples that confused "
        "native tool calling, added CRITICAL parallel tool calls instruction at top, "
        "reduced 6-step workflow to 4 concise steps for better small-model compliance."
    )

    prompts = [
        (
            "fragment/supervisor-role",
            SUPERVISOR_ROLE,
            ["fragment", "supervisor", "hierarchical"],
        ),
        (
            "fragment/supervisor-workers",
            SUPERVISOR_WORKERS,
            ["fragment", "supervisor", "hierarchical", "workers"],
        ),
        (
            "fragment/supervisor-rules",
            SUPERVISOR_RULES,
            ["fragment", "supervisor", "hierarchical", "routing"],
        ),
        (
            "fragment/response-format",
            RESPONSE_FORMAT,
            ["fragment", "response", "format"],
        ),
    ]

    print("Pushing rewritten supervisor fragments to Langfuse...\n")
    success_count = 0
    for name, prompt, tags in prompts:
        status, result = create_prompt(name, prompt, tags, commit_msg)
        emoji = "✅" if status in [200, 201] else "❌"
        version = result.get("version", "?") if isinstance(result, dict) else "?"
        print(f"{emoji} {name} (v{version}): {status}")
        if status >= 300:
            print(
                f"   Error: {result[:200] if isinstance(result, str) else result}"
            )
        else:
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Updated {success_count}/{len(prompts)} supervisor fragments.")
    print(f"View at: {BASE_URL}/prompts")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
