# patterns.md — Padrões detectados nos handoffs existentes

> Gerado por factory-planner em 2026-06-19
> Branch: phase-4/issue-29-dir-handoffs-estruturado

## Handoff 1: onboarding_trace_session

**Arquivo:** `docs/handoffs/20260525_onboarding_trace_session.md` (193 linhas)

### Estrutura detectada

```
# H1: Handoff — Título descritivo (em português)
**Data:** 25/Mai/2026
**Objetivo:** descrição do propósito
--- (separador horizontal)
## Seção: Estado já instalado
## Seção: Setup a refazer
  ### Subseções numeradas (1., 2., 3.)
## Seção: Como vamos trabalhar
## Seção: Queries úteis
## Seção: Roteiro provável
## Seção: Entregáveis ao fim
## Seção: Cleanup ao final
## Seção: Referências
## Seção: Pré-requisitos
```

### Padrões observados
- **Metadata inline** (não YAML): Data, Objetivo como bold text no header
- **Emojis de status:** ✅ (concluído), ⏳ (pendente)
- **Blocos de código:** SQL e bash em fenced blocks
- **Checkboxes:** `- [ ]` para pré-requisitos
- **Tabelas:** containers Docker em tabela markdown
- **Paths:** relativos à raiz do repo
- **Tom:** instrucional, passo-a-passo, voltado para sessão interativa

### Inconsistências vs handoff 2
- Sem campo `Autor:` ou `Status:` no header
- Sem bloco de metadados resumido
- Usa `---` como separador entre header e corpo (handoff 2 também)

---

## Handoff 2: security_sprint_pre_onboarding

**Arquivo:** `docs/handoffs/20260525_security_sprint_pre_onboarding.md` (191 linhas)

### Estrutura detectada

```
# H1: Handoff — Título descritivo (em português)
**Data:** 2026-05-25
**Autor:** Lucas + Hermes (claude-opus-4.7)
**Status:** ✅ Migrations aplicadas · ⚠️ 2 ações pendentes
**Banco alvo:** Supabase prod
--- (separador horizontal)
## 1. Contexto
## 2. O que foi aplicado em prod
  ### Migrations
  ### Mudanças efetivas
  ### Código modificado
## 3. Achado crítico
## 4. Ações pendentes
## 5. Backlog imediato
## 6. Artefatos
## 7. Verificação final
```

### Padrões observados
- **Metadata inline** (não YAML): Data, Autor, Status, Banco alvo como bold text
- **Seções numeradas** para hierarquia principal
- **Tabelas** para listas de migrations
- **Blocos de código:** SQL e bash
- **Status explícito:** ✅⚠️ no header para escaneabilidade
- **Tom:** relatório técnico, voltado para leitura pós-fato

### Inconsistências vs handoff 1
- Metadata mais rica (Autor, Status, Banco alvo)
- Seções numeradas vs seções por tópico
- Sem checkboxes para ações pendentes
- Sem seção de Setup/Pré-requisitos

---

## Padrões comuns (a preservar)

| Elemento | Ambos usam? | Consistente? |
|---|---|---|
| Nome do arquivo: `YYYYMMDD_tema.md` | Sim | Sim |
| Header H1 com prefixo "Handoff —" | Sim | Sim |
| Campo **Data:** no header | Sim | Formatos diferentes |
| Separador `---` após header | Sim | Sim |
| Seções com `##` | Sim | Numeradas vs por-tópico |
| Blocos de código fenced | Sim | Sim |
| Paths relativos à raiz | Sim | Sim |
| Português como idioma principal | Sim | Sim |

## Proposta de frontmatter

```yaml
---
title: "Título descritivo do handoff"
date: YYYY-MM-DD
author: Nome ou "Agente (modelo)"
status: draft | em_andamento | concluido | arquivado
tags: [dominio, tecnologia, urgencia]
banco_alvo: opcional
sessao_tipo: interativa | relatorio | auditoria
---
```

## Seções sugeridas para o template standard

1. **Contexto** — por que este handoff existe
2. **Estado atual** — o que já estava pronto antes
3. **Ações realizadas** — o que foi feito
4. **Achados** — descobertas, bugs, surpresas
5. **Pendências** — o que ainda precisa ser feito
6. **Artefatos** — lista de arquivos/dados gerados
7. **Referências** — links para docs, PRs, issues
8. **Próxima sessão** — continuação (opcional)

## Regras de nomenclatura

- Arquivos: `YYYYMMDD_tema_descritivo.md` (já em uso — formalizar)
- Templates em `docs/handoffs/templates/`
- Assets em `docs/handoffs/assets/` (se necessário)

## Validação (CI futuro)

- `date` deve ser ISO 8601 (YYYY-MM-DD)
- `status` deve ser um dos valores do enum
- Frontmatter YAML deve parsear sem erro
- Nome do arquivo deve seguir `YYYYMMDD_*`
