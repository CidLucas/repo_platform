# Blu App — Conceito & Produto

> Última atualização: 2026-06-02

---

## 1. Filosofia do Produto

Blu é um escritório virtual com IA para donos de PMEs brasileiras.

Não é um dashboard. Não é um chatbot. É um time de agentes que trabalha para o dono de negócio — entregando serviços de inteligência artificial de alta qualidade com o mínimo de configuração, porque o dono não é developer e tem um negócio para tocar.

**O que acreditamos:**

- **O dono já sabe.** Ele não precisa ser ensinado — precisa de visibilidade para confirmar o que suspeita e pegar o que quase escapou.
- **Decisões são o trabalho.** Tudo mais é preparação. A interface deve surfacar decisões, não dados.
- **Rotinas são o produto.** Não o chat. O valor do Blu é o que acontece sem o dono precisar pedir — enquanto ele dorme, os agentes trabalham.
- **Rotinas fazem duas coisas ao mesmo tempo.** Organizam o dono (plano do dia, alertas, relatórios) e criam contexto para os agentes (dimension_state, client_insights, artefatos internos) — para que quando o sistema ou o usuário precisar agir, a LLM já conheça o estado do negócio.
- **Aprovação é enforcement, não sugestão.** Qualquer operação que afeta o mundo real — registrar uma venda, enviar uma mensagem, criar um pedido — é bloqueada em um node de aprovação obrigatório. Não é instrução no prompt. É arquitetura. O agente não passa desse ponto sem resposta explícita do usuário. Isso constrói confiança progressiva.
- **IA de alta qualidade, pouca configuração.** O onboarding é automático. O sistema vai no site do cliente, lê as notas fiscais, monta o schema de dados. O dono não precisa configurar nada para ter valor desde o primeiro dia.

---

## 2. Interface — Salas

O app (`apps/blu_v3/`) é organizado em salas — cada sala é o espaço de trabalho de uma dimensão do negócio, com seu agente responsável.

| Sala | Rota | Agente principal | Propósito |
|---|---|---|---|
| Home | `/app` | `strategy` | Cockpit do dia: plano, alertas urgentes, aprovações pendentes |
| Clientes | `/app/clientes` | `crm` | CRM, cobrança, follow-up, reativação, NPS |
| Compras | `/app/compras` | `compras` | Fornecedores, RFQ, lista de compras, ordens de compra |
| Financeiro | `/app/financeiro` | `financeiro` | Caixa, conciliação, alertas de anomalia, relatórios |
| Agenda | `/app/agenda` | `agenda` | Google Calendar, briefs de reunião, Monday.com |
| Estratégia | `/app/estrategia` | `strategy` + `data-analyst` + `doc-writer` + `context-gatherer` (Documentos) | Padrões ocultos, análise competitiva, síntese cross-domain + aba de Documentos (criação e curadoria) |

> **Agentes sem sala própria:** `frontdesk` (roteador global), `data-entry` (gateway de escrita), `platform` (criação de rotinas/metas), `fiscal-agent` (chamado por outros agentes), `context-gatherer` (onboarding e curadoria). São infraestrutura — operam em background.

> **AgentOpsRoom** (`/app/agent-ops`): sala exclusiva de administradores internos do Blu para monitoramento de agentes. Não aparece para usuários finais.

**Princípios de UI:**
- Sem dados hardcodados — skeleton loaders enquanto o fetch não retorna
- Sidebar com ícones; labels em hover (tooltip), não expandidas permanentemente
- Rotinas ativas mostradas em tira inferior dentro da Config de cada sala
- Home exibe apenas o que é urgente ou relevante para o dia — highlights, não detalhes. Profundidade fica nas salas específicas

---

## 3. Chat — Frontdesk Contextualizado

Não existe um chat separado por agente para o usuário. Há um único **Frontdesk** que entende o contexto da sala em que o usuário está.

- O usuário está na sala Financeiro → o Frontdesk roteia automaticamente para o agente `financeiro`
- O usuário está na Home → o Frontdesk roteia para `strategy` ou responde diretamente se a query for simples
- O Frontdesk nunca faz análise profunda — se precisar de mais de 1-2 consultas, roteia para o specialist

O contexto da sala é injetado no prompt do Frontdesk — o usuário não precisa explicar onde está ou o que quer fazer lá.

---

## 4. Sala Biblioteca — Base de Conhecimento + Criação de Documentos

A Biblioteca (rota `/app/biblioteca`) é organizada em **5 abas**:

### Aba: Ativos
Documentos finalizados e aprovados pelo usuário. Visualização, edição e reaproveitamento de documentos já criados.

### Aba: Rascunhos
Documentos em elaboração — criados pelo `doc-writer` via chat, aguardando revisão ou aprovação do usuário antes de serem promovidos para Ativos.

### Aba: Modelos
Templates de documentos pré-configurados (propostas, SOPs, relatórios, respostas padrão) que o usuário ou o sistema pode usar como ponto de partida.

### Aba: Base
Base de conhecimento vetorial do cliente. Documentos indexados (PDFs, notas fiscais, contratos, CSVs) que alimentam o `executar_rag_cliente` usado por todos os agentes. Upload via UI ou via chat com o agente. `context-gatherer` cuida da ingestão, curadoria e atualização contínua.

### Aba: Config
Configuração das rotinas da sala (toggle, cron picker, config_schema).

**Fluxo de criação de documento:**
1. Usuário conversa com o `doc-writer` via chat (proposta comercial, SOP, relatório, resposta de email…)
2. Agente pesquisa a KB, redige e exibe **preview inline**
3. Usuário edita diretamente no preview se necessário
4. Node de aprovação — obrigatório antes de persistir
5. Usuário escolhe destino: **Google Drive** (exporta como Google Doc) ou **Base vetorial** (indexa na KB para uso futuro pelos agentes)

---

## 5. Fluxo de Decisão (HITL)

Todo agente pode criar uma `approval_request`. O node de aprovação é **arquitetural** — não pode ser bypassed por instrução no prompt.

```
Agente propõe ação
      ↓
Node de aprovação (status: pending) — execução suspensa
      ↓
Usuário vê card na Home ou na sala
      ↓
Aprova  → ação executada + audit_log
Edita   → ação executada com versão editada pelo usuário
Rejeita → ação cancelada + feedback ao agente
Snooze  → re-aparece em X horas
```

**Operações que sempre exigem aprovação:**
- Registrar transações (venda, despesa, pedido)
- Enviar mensagens (WhatsApp, email)
- Criar/modificar documentos e exportar
- Criar ordens de compra

**Confiança progressiva:** `client_approval_stats` rastreia histórico. Quando `trust_level = 'auto'` (configurado pelo usuário), agentes podem executar sem HITL em contextos de baixo risco que o próprio usuário definiu.

---

## 6. Rotinas — O Produto Real

Rotinas são automações que rodam em background. São o coração do Blu.

Cada rotina faz duas coisas:
1. **Entrega valor direto ao usuário** — plano do dia, alerta de inadimplência, brief de reunião
2. **Cria contexto para os agentes** — escreve em `dimension_state`, `client_insights`, artefatos internos — para que a LLM saiba o estado do negócio quando precisar agir

### Catálogo de Rotinas (MVP)

| Slug | Sala | O que entrega | Frequência |
|---|---|---|---|
| `morning_plan` | Home | Plano do dia: agenda, prioridades, alertas | Diária 07h |
| `end_of_day_digest` | Home | Resumo do dia + pendências | Diária 18h |
| `weekly_summary` | Financeiro | Saúde financeira da semana | Semanal |
| `reconciliation_report` | Financeiro | Conciliação mensal | Mensal |
| `collection_messages` | Clientes | Drafts de cobrança para aprovação | Semanal |
| `followup_draft` | Clientes | Drafts de follow-up com clientes | Semanal |
| `reactivation_proposal` | Clientes | Proposta de reativação de clientes inativos | Mensal |
| `satisfaction_survey` | Clientes | Pesquisa NPS com clientes | Mensal |
| `meeting_brief` | Agenda | Brief de reunião antes de cada evento | Antes de reuniões |
| `hidden_patterns` | Estratégia | Padrões ocultos cross-domain | Semanal |
| `competitor_analysis` | Estratégia | Análise de concorrentes via web | Mensal |

### Rotinas Customizadas

O usuário pode criar rotinas customizadas conversando com o Frontdesk (roteado para o agente `platform`). O catálogo padrão cobre o MVP — rotinas que surgem por demanda recorrente dos usuários são incorporadas ao catálogo ao longo do tempo.

### Tipos de Rotina

**Do catálogo (`builtin`):** Entregues a todos os clientes ativos, sempre ligadas, não podem ser desativadas. O Blu determina a frequência — o usuário pode ajustar o horário.

**Opcionais (`optional`):** O usuário ativa/desativa na aba Config de cada sala. Podem ser parametrizadas (ex: dia da semana, hora, configurações específicas da rotina).

**Customizadas:** Criadas pelo usuário via conversa com o Frontdesk (roteado para `platform`). Construídas a partir de funções e skills do catálogo existente. Rotinas customizadas muito solicitadas são eventualmente incorporadas ao catálogo como builtin.

---

## 7. Memória de Negócio

O sistema mantém dois tipos de contexto:

### Contexto imediato (por conversa)
O `ContextService` monta um snapshot compacto injetado no início de cada conversa:
- Aprovações pendentes (`approval_requests`)
- Alertas urgentes (`notifications`)
- Metas ativas (`client_goals`)
- Estado por sala (`dimension_state` — escrito pelas rotinas)
- Insights recentes (`client_insights` com severidade warning/critical)

Budget: 6.000 chars (~1.500 tokens). Vazio para clientes novos — sem overhead.

### Perfil de negócio (persistente)
Cada cliente tem um perfil em `clientes_blu`:

| Campo | Conteúdo |
|---|---|
| `company_profile` | Setor, tamanho, proposta de valor, produtos/serviços |
| `brand_voice` | Tom de voz, vocabulário, estilo de comunicação |
| `team_structure` | Times, responsáveis, hierarquia |
| `policies` | Políticas de crédito, aprovação, compliance |
| `data_schema` | Tabelas disponíveis (enriquecido com `sql_table_config`) |
| `available_tools` | Tools habilitadas para o cliente |

Cache Redis TTL 5 min. Injetado no system prompt de cada agente.

---

## 8. Onboarding

O onboarding é automático — o dono informa o nome da empresa e o site, e o sistema faz o resto.

**Fluxo:**
1. Landing (`apps/landing/`) → wizard
2. Sistema visita o site do cliente, extrai perfil da empresa, setor, produtos, tom de voz
3. Cliente sobe notas fiscais → sistema extrai métricas, mapeia para schema estrela (facilmente consultável via SQL)
4. Cliente pode subir arquivos adicionais via UI (Biblioteca) ou via chat
5. `context-gatherer` cuida da ingestão, curadoria e atualização contínua da KB

O pop-up de onboarding no app só aparece se `firstRun && !blu_has_data` (localStorage).

---

## 9. Integrações suportadas

| Integração | Status | Sala |
|---|---|---|
| Google Calendar | ✅ Ativo | Agenda |
| Polp (open banking) | ✅ Ativo | Financeiro |
| BigQuery (FDW) | ✅ Infra pronta | — |
| Google Drive / Docs | ✅ Ativo (PREMIUM) | Biblioteca |
| Monday.com | 🔲 Fase 4 | Agenda |
| WhatsApp | 🔲 Backlog | Clientes / Compras |
| Excel / Sheets | 🔲 Fase 4 | — |
| Slack | 🔲 Backlog | — |
