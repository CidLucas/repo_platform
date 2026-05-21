# Blu App — Conceito & Produto

> Última atualização: 2026-05-21

---

## 1. Filosofia do Produto

**Blu é um escritório virtual com IA para donos de PMEs brasileiras.**

Não é um dashboard. Não é um chatbot. É um time de agentes que trabalha para o dono de negócio.

**O que acreditamos:**
- O dono já sabe. Ele não precisa ser ensinado — precisa de visibilidade para confirmar o que suspeita e pegar o que quase escapou.
- Decisões são o trabalho. Tudo mais é preparação. A interface deve surfacar decisões, não dados.
- Aprovação é confiança. Cada ação que um agente toma em nome do usuário constrói ou destrói confiança.
- Rotinas são o produto. Não o chat. O valor do Blu é o que acontece sem o dono precisar pedir.

---

## 2. Interface — Salas

O app (`apps/blu_v3/`) é organizado em **salas** — cada sala é o espaço de trabalho de uma dimensão do negócio.

| Sala | Rota | Dimensão | Propósito |
|---|---|---|---|
| Home | `/app` | — | Morning brief, insights do dia, aprovações pendentes |
| Clientes | `/app/clientes` | clientes | CRM, cobrança, follow-up, reativação |
| Compras | `/app/compras` | compras | Fornecedores, RFQ, pedidos |
| Financeiro | `/app/financeiro` | financeiro | Caixa, conciliação, Polp integração |
| Agenda | `/app/agenda` | agenda | Google Calendar, briefs de reunião |
| Estratégia | `/app/estrategia` | estrategia | Padrões ocultos, análise competitiva, metas |
| Documentos | `/app/documentos` | documentos | Documentos + Biblioteca (merged) — HITL → RAG |

**Princípios de UI:**
- Sem dados hardcodados — sempre skeleton loaders enquanto o fetch não retorna
- Sidebar com ícones; labels aparecem em hover (tooltip), não expandidas permanentemente
- Rotinas ativas mostradas em tira inferior dentro da Config de cada sala
- Onboarding overlay só aparece se não houve ingestão de dados (`blu_has_data` no localStorage)

---

## 3. Fluxo de Decisão (HITL)

Todo agente pode criar uma `approval_request`. O usuário aprova, edita ou rejeita na UI.

```
Agente propõe ação
      ↓
approval_request (status: pending)
      ↓
Usuário vê card na Home ou na sala
      ↓
Aprova → ação executada + audit_log
Edita  → ação executada com versão editada
Rejeita → ação cancelada + feedback ao agente
Snooze → re-aparece em X horas
```

**Confiança progressiva:** `client_approval_stats` rastreia histórico de aprovações. Quando `trust_level = 'auto'`, agentes podem executar sem HITL em contextos de baixo risco.

---

## 4. Rotinas — O Produto Real

Rotinas são automações que rodam em background, sem o dono precisar pedir.

**Exemplos ativos no catálogo:**

| Rotina | Sala | Frequência |
|---|---|---|
| Plano matinal | Home | Diária (manhã) |
| Digest fim de dia | Home | Diária (noite) |
| Resumo semanal | Financeiro | Semanal |
| Mensagens de cobrança | Clientes | Sob demanda / gatilho |
| Follow-up draft | Clientes | Semanal |
| Brief de reunião | Agenda | Antes de cada reunião |
| Padrões ocultos | Estratégia | Semanal |

Cada rotina gera: `client_insights`, `notifications`, `approval_requests`, ou escreve em `dimension_state` — alimentando o snapshot de memória do agente principal.

---

## 5. Memória de Negócio (Shared Memory)

O User-Facing Agent recebe um snapshot compacto de contexto a cada conversa:

```
## Estado do Negócio
### Aprovações pendentes      ← approval_requests (pending)
### Alertas não lidos         ← notifications (urgentes)
### Metas ativas              ← client_goals
### Estado por dimensão       ← dimension_state (escrito pelas rotinas)
### Insights recentes         ← client_insights (warning/critical)
```

Gerado por `ContextService.get_business_memory_snapshot(client_id)`. Budget: 6 000 chars (~1 500 tokens). Retorna string vazia se não há nada relevante — sem overhead em clientes novos.

---

## 6. Contexto de Negócio (BluClientContext)

Cada cliente tem um perfil persistido em `clientes_blu`:

| Campo | Conteúdo |
|---|---|
| `company_profile` | Setor, tamanho, proposta de valor, produtos/serviços |
| `brand_voice` | Tom de voz, vocabulário, estilo de comunicação |
| `team_structure` | Times, responsáveis, hierarquia |
| `policies` | Políticas de crédito, aprovação, compliance |
| `data_schema` | Tabelas disponíveis para o agente (enriquecido com `sql_table_config`) |
| `available_tools` | Tools habilitadas para o cliente |

Carregado pelo `ContextService` com cache Redis (TTL 5 min). Injetado no prompt system de cada agente.

---

## 7. Onboarding

Fluxo: Landing (`apps/landing/`) → wizard → `onboarding_state` em `clientes_blu` → provisionamento de tenant.

- `onboarding_completed_at` marca fim do onboarding
- Pop-out de onboarding no app só aparece se `firstRun && !blu_has_data`
- Dados ingeridos no onboarding populam `company_profile`, `brand_voice`, etc.

---

## 8. Integrações suportadas

| Integração | Tabela | Status |
|---|---|---|
| Google Calendar | `integration_tokens` + `calendar_settings` | ✅ Ativo |
| Polp (open banking) | `polp_integrations`, `polp_accounts`, `polp_transactions`, `polp_bills` | ✅ Ativo |
| BigQuery (FDW) | `bigquery_servers`, `bigquery_foreign_tables` | ✅ Infra pronta |
| Monday.com | `integration_configs` | 🔲 Fase 4 |
| Excel / Sheets | `integration_configs` | 🔲 Fase 4 |
| WhatsApp | `credencial_servico_externo` | 🔲 Backlog |
