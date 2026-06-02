# System Reference — Blu Platform

> **Fonte de verdade do sistema de agentes, skills e arquitetura operacional do Blu.**
> Agentes devem sempre consultar esta pasta antes de responder sobre capacidades, skills disponíveis, rotinas e ferramentas.

---

## Documentos desta pasta

| Arquivo | Descrição |
|---|---|
| `AGENT_SYSTEM.md` | Arquitetura dos 12 agentes: papéis, hierarquia, regras de roteamento, decisões de design |
| `SKILLS_SYSTEM.md` | Catálogo completo de skills: tools por skill, agentes consumidores, governance |
| `FEATURE_MAP.md` | Mapa de features por tier: quais agentes e tools cada feature habilita |
| `TOOL_INVENTORY.md` | Inventário de todas as tools registradas (BUILTIN + tier) |
| `ROUTINES_SYSTEM.md` | Fluxo de execução de rotinas: pg_cron → dispatch → steps (function/skill/artifact/approval) |
| `TASK_PLAYBOOKS.md` | Receitas de desenvolvimento: como adicionar rotina, skill, tool, integração |

---

## Como usar

- **Antes de implementar** qualquer agente, skill ou rotina → consulte `AGENT_SYSTEM.md` + `SKILLS_SYSTEM.md`
- **Para saber quais tools estão disponíveis** → `TOOL_INVENTORY.md`
- **Para entender o fluxo de rotinas** → `ROUTINES_SYSTEM.md`
- **Para tarefas recorrentes de dev** → `TASK_PLAYBOOKS.md`

---

## Regras de manutenção

1. Todo novo agente → documentar em `AGENT_SYSTEM.md`
2. Toda nova skill → documentar em `SKILLS_SYSTEM.md` **e** criar prompt no Langfuse (`skill:{nome}:system`)
3. Toda nova tool → registrar em `TOOL_INVENTORY.md`
4. Toda nova rotina → documentar em `ROUTINES_SYSTEM.md`
5. Mudanças de arquitetura → atualizar `AGENT_SYSTEM.md` e refletir em `HERMES.md`
