# Hermes Cron Jobs — Design & Prompts

> Última atualização: 2026-06-01

---

## agent-audit-cron

**Schedule:** every 10 minutes  
**Goal:** Audita um agente por vez (round-robin), compara prompt Langfuse vs template.py, avalia skills e gera mapa lógico em `docs/agent_audits/`.

**State file:** `/Users/lucascruz/Documents/GitHub/repo_platform/docs/agent_audits/.rr_state.json`  
**Output dir:** `/Users/lucascruz/Documents/GitHub/repo_platform/docs/agent_audits/`

**Agents auditados (em ordem):**  
frontdesk, data-entry, platform, financeiro, compras, crm, agenda, data-analyst, strategy, doc-writer, context-gatherer, fiscal-agent

---
