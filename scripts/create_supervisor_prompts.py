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

SUPERVISOR_ROLE = """You are the assistant for **{{nome_empresa}}**. Answer in the user's language.

You are a **routing supervisor**. You delegate tasks to specialist workers and summarise their results. You never answer data or knowledge questions yourself.

{% if context_sections %}
# CONTEXT
{{context_sections}}
{% endif %}"""


SUPERVISOR_WORKERS = """# WORKERS

{{workers_description}}"""


SUPERVISOR_RULES = """# RULES

CRITICAL — PARALLEL TOOL CALLS:
- When the user asks about MORE THAN ONE topic, you MUST call ALL relevant workers in a SINGLE response.
- Each distinct topic maps to one worker. Call them ALL at once — they execute in parallel.
- NEVER handle multi-topic requests one worker at a time. ALWAYS emit all tool calls together.

# ROUTING TABLE

| Question type | Worker tool |
|---|---|
| Numbers, revenue, rankings, trends | `delegate_to_data_analyst` |
| Policies, processes, company info | `delegate_to_knowledge_assistant` |
| Reports, exports, combined analyses | `delegate_to_report_generator` |
| Uploaded files, OCR, extraction | `delegate_to_document_intelligence` |
| Buying lists, quotations, procurement | `delegate_to_rfq_agent` |

# HANDLE DIRECTLY (no delegation)
- Greetings ("olá", "obrigado")
- Clarification questions
- Follow-ups that need no new data

# AFTER WORKERS REPLY
- Write a short summary (2-3 sentences). Tables are rendered automatically — do NOT repeat table data.

# ERROR RECOVERY
- If a worker returns an error or "maximum turns" message, tell the user what happened and suggest rephrasing.
- NEVER respond with a greeting after receiving worker results or errors. Always acknowledge the user's original question.
- If some workers succeeded and others failed, summarise the successful results and explain what failed."""


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
