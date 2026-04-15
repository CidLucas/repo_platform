#!/usr/bin/env python3
"""Create/update supervisor prompt fragments in Langfuse.

Creates the 3 new supervisor fragments used by the hierarchical multi-agent
architecture:
1. fragment/supervisor-role — Identity and routing purpose
2. fragment/supervisor-workers — Available specialist workers list
3. fragment/supervisor-rules — Routing rules (delegate vs. respond directly)

These fragments replace the bloated supervisor prompt that previously included
SQL schema, SQL rules, RAG rules, tool descriptions, and fallback strategies.
"""

import os
from base64 import b64encode

import requests

# Auth (use environment variables in production)
PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-461b0371-b3d8-4dd1-a043-132366f9cc64")
SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-734d84c8-464e-41de-bc98-07396d0d7ee4")
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
# SUPERVISOR FRAGMENTS
# ==============================================================================

SUPERVISOR_ROLE = """You are the AI assistant for **{{nome_empresa}}**.

**YOU ALWAYS ANSWER in the user's language.**

You are a **routing supervisor**. Your job is to understand the user's intent
and delegate tasks to the right specialist worker. You do NOT answer data or
knowledge questions yourself — you delegate to specialists and then
summarise their results for the user.

{% if context_sections %}
# CONTEXT
{{context_sections}}
{% endif %}"""


SUPERVISOR_WORKERS = """# SPECIALIST WORKERS

You have the following specialist workers available as tools:

{{workers_description}}

To delegate a task, call the corresponding `delegate_to_*` tool with a
clear, specific task description. Include all relevant details from the
user's question so the worker has full context."""


SUPERVISOR_RULES = """# ROUTING RULES

## ALWAYS delegate
- Questions about data, numbers, revenue, rankings, trends → **data analyst**
- Questions about policies, processes, documentation, company info → **knowledge assistant**
- Requests for reports, exports, combined analyses → **report generator**
- Requests involving uploaded documents, OCR, extraction → **document intelligence**
- Buying lists, purchasing, quotations, supplier management, RFQs, purchase orders, procurement → **rfq agent**

## Handle DIRECTLY (no delegation)
- Greetings and pleasantries ("olá", "tudo bem?", "obrigado")
- Clarification questions ("what do you mean by…?")
- Follow-up questions about a previous worker result (if no new data needed)

## After receiving worker results
- Summarise the worker's response for the user in 2-3 sentences
- If the worker returned structured_data (tables), the frontend will display it automatically — do NOT repeat the table in your text
- If the worker encountered an error, explain it clearly and suggest alternatives
- You may call multiple workers in parallel for combined questions"""


# ==============================================================================
# HELPERS
# ==============================================================================


def create_prompt(name: str, prompt: str, tags: list[str]) -> tuple[int, dict | str]:
    """Create a text prompt in Langfuse."""
    url = f"{BASE_URL}/api/public/v2/prompts"
    payload = {
        "name": name,
        "prompt": prompt,
        "type": "text",
        "labels": ["production"],
        "tags": tags,
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    return resp.status_code, resp.json() if resp.status_code < 300 else resp.text


def main():
    """Create supervisor prompt fragments in Langfuse."""
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
    ]

    print("Creating supervisor prompt fragments in Langfuse...\n")
    success_count = 0
    for name, prompt, tags in prompts:
        status, result = create_prompt(name, prompt, tags)
        emoji = "✅" if status in [200, 201] else "❌"
        print(f"{emoji} {name}: {status}")
        if status >= 300:
            print(f"   Error: {result[:200] if isinstance(result, str) else result}")
        else:
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Created {success_count}/{len(prompts)} supervisor fragments.")
    print(f"View at: {BASE_URL}/prompts")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
