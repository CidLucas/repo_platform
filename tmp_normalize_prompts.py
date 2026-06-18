from pathlib import Path

base = Path("docs/prompt_drafts")
files = [
    "agenda.md",
    "compras.md",
    "context-gatherer.md",
    "crm.md",
    "data-analyst.md",
    "data-entry.md",
    "doc-writer.md",
    "financeiro.md",
    "fiscal-agent.md",
    "frontdesk.md",
    "platform.md",
    "strategy.md",
]

updated = []

for name in files:
    path = base / name
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    if "status: ready_for_review" in text:
        continue
    if "status: draft" not in text:
        continue

    text = text.replace("status: draft", "status: ready_for_review", 1)

    start_marker = "<!-- IMPROVEMENT REQUEST"
    end_marker = "## Current Prompt (Langfuse"
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    if start_idx != -1 and end_idx != -1:
        fenced = text[end_idx:]
        fence1 = fenced.find("```")
        if fence1 != -1:
            after1 = fenced[fence1 + 3 :]
            fence2 = after1.find("```")
            if fence2 != -1:
                prompt_body = after1[:fence2].strip()
                after_end = after1[fence2 + 3 :]
            else:
                prompt_body = after1.strip()
                after_end = ""
        else:
            prompt_body = ""
            after_end = fenced

        improved = (
            "## Improved Prompt\n\n"
            "You are a Blu specialist agent. Always respond in the user's language.\n\n"
            f"{prompt_body}\n\n"
            "---\n"
        )
        new_text = text[:start_idx] + improved + after_end
        path.write_text(new_text, encoding="utf-8")
        updated.append(name)
    else:
        updated.append(name)

print("Updated:", updated)
print("Count:", len(updated))
