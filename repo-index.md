# repo-index.md — Planejamento Issue #29 (Diretório handoffs/)

> Gerado por factory-planner em 2026-06-19
> Branch: phase-4/issue-29-dir-handoffs-estruturado

## Arquivos diretamente afetados

| Arquivo | Linhas | Função atual | Ação |
|---|---|---|---|
| `docs/handoffs/20260525_onboarding_trace_session.md` | 193 | Handoff de tracing de onboarding (E3 prep) | Refatorar: adicionar frontmatter YAML |
| `docs/handoffs/20260525_security_sprint_pre_onboarding.md` | 191 | Handoff de security sprint pré-onboarding | Refatorar: adicionar frontmatter YAML |
| `docs/handoffs/README.md` | (novo) | Convenções e índices | Criar |
| `docs/handoffs/templates/standard.md` | (novo) | Template padronizado de handoff | Criar |

## Arquivos com referências cruzadas a docs/handoffs/

| Arquivo | Linha | Referência | Risco |
|---|---|---|---|
| `docs/observability/onboarding-trace-mai2026-partial.md` | 199 | `docs/handoffs/20260525_onboarding_trace_session.md` | BAIXO — path permanece inalterado |
| `docs/handoffs/20260525_security_sprint_pre_onboarding.md` | 167 | Self-reference ao próprio handoff | BAIXO — path permanece inalterado |

**Conclusão:** Nenhuma quebra de referência. Os arquivos existentes NÃO serão renomeados/movidos.

## Arquivos de contexto (não modificados)

| Arquivo | Relevância |
|---|---|
| `docs/README.md` | Índice mestre de docs — não inclui handoffs/. Será atualizado via PR separado ou documentado para o coder. |
| `HERMES.md` | Context map do agente — lista system_reference como source of truth. Handoffs não são mencionados. |
| `docs/system_reference/TASK_PLAYBOOKS.md` | Playbooks de dev — não cobre handoffs. |
| `docs/system_reference/AGENT_SYSTEM.md` | 12 agentes — handoffs são artefatos de comunicação entre agentes humanos+AI. |
| `docs/llm_wiki/` | Wiki do projeto — diretório não populado. SHARED_MEMORY_DESIGN.md referenciado na issue não existe neste repo. |

## Padrões de documentação do repo

- Docs em PT-BR com trechos em EN (comandos, SQL, tags técnicas)
- Markdown padrão com headers `##` e `###`
- Referências a arquivos usam paths relativos da raiz do repo
- Listas de ações usam checkboxes `- [ ]` / `- [x]`
- Seções com emojis para escaneabilidade visual
- Nomenclatura de arquivos: snake_case com prefixo de data YYYYMMDD_

## Estrutura atual de docs/

```
docs/
├── README.md              # Índice mestre (não inclui handoffs/)
├── agent_audits/          # 5 arquivos de auditoria de agentes
├── backlog/               # Backlog com referências a handoffs
├── blu_app/               # Documentação do app
├── handoffs/              # ⭐ ALVO — 2 handoffs, sem README, sem templates/
├── llm_wiki/              # Wiki do projeto
├── observability/         # 1 arquivo com cross-ref a handoffs/
├── prompt_drafts/         # Rascunhos de prompt
├── roadmap/               # Roadmap do produto
├── security/              # 2 arquivos de auditoria de segurança
├── skill_improvements/    # Tracking de melhorias de skills
└── system_reference/      # 15+ arquivos de referência (single source of truth)
```
