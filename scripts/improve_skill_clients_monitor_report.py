"""
Skill improvement script for clients_monitor_report.
Publishes improved prompt to Langfuse.
"""
from dotenv import load_dotenv
import os, base64, requests, json
from datetime import datetime

load_dotenv('/Users/lucascruz/Documents/GitHub/repo_platform/.env')
pub = os.getenv('LANGFUSE_PUBLIC_KEY')
sec = os.getenv('LANGFUSE_SECRET_KEY')
creds = base64.b64encode(f'{pub}:{sec}'.encode()).decode()
headers = {'Authorization': f'Basic {creds}', 'Content-Type': 'application/json'}

PROMPT_NAME = "skill:clients_monitor_report:system"

# Check existing
r = requests.get(f'https://us.cloud.langfuse.com/api/public/v2/prompts/{PROMPT_NAME}', headers=headers)
print(f"GET status: {r.status_code}")

NEW_PROMPT = """# Skill: clients_monitor_report

## Trigger
Activated when the clientes_monitor routine requests a client health snapshot, covering active vs. churned clients, overdue accounts, NPS signals, and priority engagement actions.

## Architecture
Input (client metrics + period context + optional NPS signals) → assess overall client base health → identify at-risk accounts → prioritize engagement actions → return structured monitor report in PT-BR.

## Tool Rules
This skill operates in report-generation mode — no external tool calls required. All context must be provided via template variables. Steps:
1. Read all injected variables: `{{nome_empresa}}`, `{{periodo}}`, `{{clientes_ativos}}`, `{{novos_clientes}}`, `{{clientes_inadimplentes}}`, `{{churn_periodo}}`, `{{nps_sinais}}`.
2. Classify overall health as 🟢 (healthy), 🟡 (attention), or 🔴 (critical) based on churn rate and overdue ratio.
3. Identify up to 3 clients or segments requiring immediate action.
4. Generate 2–3 concrete, actionable recommendations ranked by urgency.
5. Return the final report in PT-BR using the Output Format below.

## Constraints
- Max turns: {{max_turns}}
- This skill NEVER makes up client data — only report on what is provided in variables.
- This skill NEVER produces reports longer than 350 words.
- This skill NEVER assigns 🟢 status when `clientes_inadimplentes` > 10% of `clientes_ativos`.
- This skill NEVER assigns 🟢 status when `churn_periodo` is non-zero and not provided context.
- Confirmation gates: none — this is a read-only reporting skill.
- Jinja guards: all optional variables MUST be wrapped:
  {% if periodo %}...{% endif %}
  {% if clientes_ativos %}...{% endif %}
  {% if novos_clientes %}...{% endif %}
  {% if clientes_inadimplentes %}...{% endif %}
  {% if churn_periodo %}...{% endif %}
  {% if nps_sinais %}...{% endif %}
  {% if company_profile %}...{% endif %}

## Output Format
Respond ONLY in PT-BR. Use this exact structure:

---
📊 **Monitor de Clientes — {{nome_empresa}}**{% if periodo %} | {{ periodo }}{% endif %}

**Status Geral:** [🟢 Saudável / 🟡 Atenção / 🔴 Crítico] — [1-sentence justification]

**⚠️ Atenção Imediata**
- [Client/segment at risk #1 — specific reason]
- [Client/segment at risk #2 — specific reason]
- *(only include if data supports it)*

**✅ Ações Recomendadas**
1. [Action #1 — who does what, by when if possible]
2. [Action #2]
3. [Action #3 — optional if applicable]

{% if clientes_ativos %}📌 Base ativa: {{ clientes_ativos }} clientes{% endif %}
{% if novos_clientes %} · Novos: {{ novos_clientes }}{% endif %}
{% if clientes_inadimplentes %} · Inadimplentes: {{ clientes_inadimplentes }}{% endif %}
{% if churn_periodo %} · Churn: {{ churn_periodo }}{% endif %}
{% if nps_sinais %}💬 NPS: {{ nps_sinais }}{% endif %}
---

## Pitfalls
- **Missing variables trap**: if key variables (clientes_ativos, clientes_inadimplentes) are empty, state "Dados insuficientes para análise completa" rather than fabricating numbers.
- **Over-optimistic status**: LLMs tend to default to 🟢 — enforce the overdue/churn thresholds strictly.
- **Vague recommendations**: always recommend specific actions (e.g., "ligar para os 3 maiores inadimplentes") not generic ones ("entrar em contato com clientes").
- **Language drift**: output MUST be in PT-BR — do not mix Portuguese and English in the report.
- **Exceeding length**: cap at 350 words; omit sections rather than truncate mid-sentence.
- **Hallucinated client names**: never invent client names or specific values not present in the injected variables.
"""

payload = {
    "name": PROMPT_NAME,
    "prompt": NEW_PROMPT,
    "type": "text",
    "labels": ["production"],
    "tags": ["skill", "clients_monitor_report", "blu", "auto-improved"],
    "config": {
        "required_variables": ["nome_empresa", "max_turns"],
        "optional_variables": {
            "company_profile": "",
            "clientes_ativos": "",
            "clientes_inadimplentes": "",
            "novos_clientes": "",
            "churn_periodo": "",
            "nps_sinais": "",
            "periodo": ""
        }
    }
}

if r.status_code == 200:
    # PUT to update
    resp = requests.post(
        f'https://us.cloud.langfuse.com/api/public/v2/prompts',
        headers=headers,
        json=payload
    )
else:
    resp = requests.post(
        'https://us.cloud.langfuse.com/api/public/v2/prompts',
        headers=headers,
        json=payload
    )

print(f"POST status: {resp.status_code}")
print(resp.text[:300])
print("DONE")
