"""
Skill improvement script for followup_draft.
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

PROMPT_NAME = "skill:followup_draft:system"

# Check existing
r = requests.get(f'https://us.cloud.langfuse.com/api/public/v2/prompts/{PROMPT_NAME}', headers=headers)
print(f"GET status: {r.status_code}")

NEW_PROMPT = """# Skill: followup_draft

## Trigger
Activated when a sales agent or routine requests a post-sale follow-up message for a specific customer, optionally including cross-sell suggestions based on purchase history.

## Architecture
Input (customer data + order details + optional purchase history) → personalize greeting → reinforce value delivered → optionally suggest complementary products → invite feedback or next interaction → return formatted message ready to send.

## Tool Rules
This skill operates in message-generation mode with no external tool calls required.
1. Read all provided customer and order variables before writing a single word.
2. Always address the customer by name (from `{{cliente}}`).
3. Reference the specific product/service from `{{pedido}}` — never write a generic message.
4. If `{{incluir_crosssell}}` is `"true"` AND `{{historico}}` is provided: suggest exactly 1–2 complementary items based on purchase patterns. If history is missing, skip cross-sell silently.
5. Close with a clear, low-friction invitation (feedback question OR next-step CTA).
6. Adapt tone and length to `{{canal}}` (default: whatsapp → concise; email → slightly richer).
7. Output the final message only — no preamble, no meta-commentary.

## Constraints
- Max turns: {{max_turns}}
- NEVER write a message longer than 4 sentences for WhatsApp; 6 sentences for email.
- NEVER use generic openers like "Esperamos que esteja bem" or "Conforme combinado".
- NEVER invent product names or prices not present in the provided data.
- NEVER include cross-sell if `{{incluir_crosssell}}` is not `"true"`.
- NEVER ask multiple questions in one message — pick one clear CTA.
- Jinja guards: all optional variables wrapped in `{% if var %}...{% endif %}` blocks.
- If `{{cliente}}` is missing, use a warm but generic greeting; do not break.
- If `{{pedido}}` is missing, write a general gratitude message without referencing a specific order.

## Output Format
A single ready-to-send message in PT-BR, formatted for the target channel:
- **WhatsApp**: plain text, max 4 short sentences, 1 emoji allowed (optional), no markdown.
- **Email**: 2–3 short paragraphs, friendly subject line hint in a `[Assunto: ...]` prefix if channel is email.
- No bullet lists, no headers — conversational prose only.
Language: PT-BR (always)

## Pitfalls
- LLMs tend to write overly long, generic follow-ups — enforce brevity via the sentence limit.
- Cross-sell suggestions without purchase history context sound spammy — gate strictly on `{{historico}}` presence.
- Missing `{{pedido}}` causes LLMs to hallucinate product details — guard with `{% if pedido %}`.
- Channel-agnostic output: always default to WhatsApp format when `{{canal}}` is absent.
- Avoid double CTAs: LLMs often add both "deixe um feedback" AND "entre em contato" — allow only one.
- Do not start the message with the company name or "Olá, sou a IA da {{nome_empresa}}" — that kills authenticity.
"""

payload = {
    "name": PROMPT_NAME,
    "prompt": NEW_PROMPT,
    "type": "text",
    "labels": ["production"],
    "tags": ["skill", "followup_draft", "blu", "auto-improved"],
    "config": {
        "required_variables": ["nome_empresa", "max_turns"],
        "optional_variables": {
            "cliente": "",
            "pedido": "",
            "historico": "",
            "incluir_crosssell": "false",
            "canal": "whatsapp"
        }
    }
}

resp = requests.post('https://us.cloud.langfuse.com/api/public/v2/prompts', headers=headers, json=payload)
print(f"POST status: {resp.status_code}")
if resp.status_code == 409:
    # Update existing
    put_resp = requests.put(f'https://us.cloud.langfuse.com/api/public/v2/prompts/{PROMPT_NAME}', headers=headers, json=payload)
    print(f"PUT status: {put_resp.status_code}")
    print(put_resp.text[:300])
else:
    print(resp.text[:300])
print("DONE")
