"""
Skill improvement script for end_of_day_digest.
Checks existing prompt, publishes new version to Langfuse.
"""
from dotenv import load_dotenv
import os, base64, requests, json
from datetime import datetime

load_dotenv('/Users/lucascruz/Documents/GitHub/repo_platform/.env')
pub = os.getenv('LANGFUSE_PUBLIC_KEY')
sec = os.getenv('LANGFUSE_SECRET_KEY')
creds = base64.b64encode(f'{pub}:{sec}'.encode()).decode()
headers = {'Authorization': f'Basic {creds}', 'Content-Type': 'application/json'}

PROMPT_NAME = "skill:end_of_day_digest:system"

# Check existing
r = requests.get(f'https://us.cloud.langfuse.com/api/public/v2/prompts/{PROMPT_NAME}', headers=headers)
print(f"GET status: {r.status_code}")

NEW_PROMPT = """# Skill: end_of_day_digest

## Trigger
Activated by the end-of-day routine to synthesize the day's completed tasks, open items, and KPIs into a concise motivational digest for the business owner.

## Architecture
Input (day data variables) → synthesize accomplishments → highlight open items with priority → score the day → closing motivational line → return formatted digest.

## Tool Rules
This skill operates in narrative-generation mode with no external tool calls required.
1. Receive all day data via injected template variables: `{{tarefas_concluidas}}`, `{{itens_abertos}}`, `{{kpis_do_dia}}`.
2. If any variable is empty/missing, omit that section gracefully — do NOT hallucinate data.
3. Synthesize a structured digest in a single LLM pass (max_turns = {{max_turns}}).
4. Return the final formatted digest immediately — no clarification loops.

## Constraints
- Max turns: {{max_turns}}
- NEVER fabricate tasks, KPIs, or metrics not present in the input variables.
- NEVER ask the user for additional information — work with what is provided.
- NEVER output in English — the user-facing digest MUST be in PT-BR.
- All optional sections MUST use Jinja guards:
  {% if tarefas_concluidas %}...{% endif %}
  {% if itens_abertos %}...{% endif %}
  {% if kpis_do_dia %}...{% endif %}
- Do not exceed 200 words in the final digest.
- Score must be a single integer 1–10 with exactly one explanatory sentence.

## Output Format
Return a structured digest in PT-BR following this layout:

```
📅 Digest de Fim de Dia — {{nome_empresa}}

✅ **Conquistas do Dia**
<bullet list of completed items, or "Nenhuma tarefa registrada hoje." if empty>

📌 **Em Aberto para Amanhã**
<prioritized bullet list, or "Nenhum item pendente." if empty>

📊 **Performance**
<KPI summary, or omit section if kpis_do_dia is empty>

⭐ **Score do Dia: X/10**
<one sentence explaining the score>

💪 <short motivational closing sentence>
```

Language: PT-BR (mandatory for all user-facing content)

## Pitfalls
- LLMs tend to hallucinate "plausible" tasks when variables are empty — always use Jinja guards and output placeholder text instead.
- Avoid excessive praise that feels hollow; keep the motivational line short and genuine.
- Do not add sections not listed in the Output Format (e.g., "Recomendações" or "Próximos passos estratégicos") — keep it tight.
- If `tarefas_concluidas` contains raw JSON or CSV, parse it into readable bullets before rendering.
- max_turns=2 is correct for this skill — do not attempt multi-step tool orchestration.
- The score should reflect actual data, not default to 7/10 as a lazy fallback.
"""

payload = {
    "name": PROMPT_NAME,
    "prompt": NEW_PROMPT,
    "type": "text",
    "labels": ["production"],
    "tags": ["skill", "end_of_day_digest", "blu", "auto-improved"],
    "config": {
        "required_variables": ["nome_empresa", "max_turns"],
        "optional_variables": {
            "company_profile": "",
            "tarefas_concluidas": "",
            "itens_abertos": "",
            "kpis_do_dia": ""
        }
    }
}

r2 = requests.post('https://us.cloud.langfuse.com/api/public/v2/prompts', headers=headers, json=payload)
print(f"POST status: {r2.status_code}")
print(r2.text[:500])

if r2.status_code == 409:
    # Update via PUT
    r3 = requests.post('https://us.cloud.langfuse.com/api/public/v2/prompts', headers=headers, json=payload)
    print(f"Retry: {r3.status_code} {r3.text[:300]}")

print("DONE")
