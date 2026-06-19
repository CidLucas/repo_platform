# resolution.md — Plano de execução: Diretório handoffs/ estruturado

> Gerado por factory-planner em 2026-06-19
> Branch: phase-4/issue-29-dir-handoffs-estruturado
> Issue: #29 — Fase 4 (T4.1): Diretório handoffs/ estruturado

## Decisões de design

| Decisão | Escolha | Justificativa |
|---|---|---|
| D1 — Formato de metadata | YAML frontmatter | Estruturado, parseável, padrão em static site generators, suportado pelo GitHub |
| D2 — Renomear arquivos existentes? | NÃO | Quebraria referência cruzada em `docs/observability/onboarding-trace-mai2026-partial.md` |
| D3 — Template separado ou inline no README? | Arquivo separado `templates/standard.md` | Facilita copy-paste para novos handoffs |
| D4 — Validar convenções? | Documentar no README; CI futuro | Sem bloqueio atual; checklist manual |
| D5 — Atualizar `docs/README.md`? | NÃO neste escopo | Issue #29 cobre apenas `docs/handoffs/` |
| D6 — Idioma | PT-BR com termos técnicos em EN | Consistente com handoffs existentes e convenção do repo |

## Arquivos a criar/modificar

| Arquivo | Ação | Estimativa |
|---|---|---|
| `docs/handoffs/README.md` | CRIAR | ~80 linhas |
| `docs/handoffs/templates/standard.md` | CRIAR | ~60 linhas |
| `docs/handoffs/20260525_onboarding_trace_session.md` | MODIFICAR (+frontmatter) | +8 linhas |
| `docs/handoffs/20260525_security_sprint_pre_onboarding.md` | MODIFICAR (+frontmatter) | +9 linhas |

## Plano de execução (para factory-coder)

### Step 1 — Criar `docs/handoffs/README.md`

- Propósito: comunicação entre agentes humanos+AI
- Convenção de nomenclatura: `YYYYMMDD_tema_descritivo.md`
- Estrutura de frontmatter obrigatório (YAML) com campos explicados
- Seções obrigatórias e opcionais
- Como criar novo handoff (referência ao template)
- Índice dos handoffs existentes
- Checklist de validação pré-commit

### Step 2 — Criar `docs/handoffs/templates/standard.md`

- Frontmatter YAML com placeholders
- Estrutura de seções numeradas com instruções
- Dicas de estilo (emojis, tabelas, blocos de código)

### Step 3 — Refatorar `20260525_onboarding_trace_session.md`

Adicionar frontmatter YAML (sem alterar conteúdo existente):

```yaml
---
title: "Sessão de Tracing do Onboarding (E3 prep)"
date: 2026-05-25
author: "Lucas + Hermes"
status: concluido
tags: [onboarding, observabilidade, tracing, banco]
banco_alvo: "aws-0-us-west-2.pooler.supabase.com"
sessao_tipo: interativa
---
```

### Step 4 — Refatorar `20260525_security_sprint_pre_onboarding.md`

Adicionar frontmatter YAML (sem alterar conteúdo existente):

```yaml
---
title: "Security Sprint pré-Onboarding"
date: 2026-05-25
author: "Lucas + Hermes (claude-opus-4.7)"
status: concluido
tags: [seguranca, rls, secdef, vault, onboarding]
banco_alvo: "aws-0-us-west-2.pooler.supabase.com"
sessao_tipo: auditoria
---
```

### Step 5 — Verificação

- [ ] README.md sem erros de markdown
- [ ] template/standard.md com frontmatter YAML válido
- [ ] Handoff 1: frontmatter inserido, conteúdo intacto
- [ ] Handoff 2: frontmatter inserido, conteúdo intacto
- [ ] Nenhum arquivo renomeado ou movido
- [ ] Referência em `docs/observability/onboarding-trace-mai2026-partial.md` preservada
- [ ] Git diff mostra apenas adições

## Riscos e mitigações

| Risco | Prob | Impacto | Mitigação |
|---|---|---|---|
| Frontmatter YAML quebra renderização | Baixa | Baixo | GitHub suporta nativamente |
| `---` no conteúdo conflita com delimitador YAML | Baixa | Médio | Verificar se há `---` no meio do corpo |
| Template ignorado por agentes futuros | Média | Médio | README referencia; outros docs linkam |
| Quebra de referências | Nula | — | Arquivos não são renomeados |

## Dependências

Nenhuma. Issue #29 é auto-contida.

## Próximos passos (pós-implementação)

1. Atualizar `docs/README.md` para incluir `handoffs/` na tabela de docs ativos
2. Avaliar CI lint de frontmatter YAML nos handoffs
3. Issues #30 (meta/), #31 (triggers), #32 (retenção/prune) — fases seguintes
