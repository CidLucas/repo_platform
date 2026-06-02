# AGENT_SYSTEM.md — Fonte da Verdade: Agentes e Skills

> **Este é o documento autoritativo** para o sistema de agentes do Blu.
> Qualquer agente que precisar entender a arquitetura, o papel de outro agente,
> ou que skills usar em qual contexto deve consultar este documento primeiro.
>
> Última revisão: 2026-06-02

---

## Visão Geral

O Blu é um escritório virtual com IA para donos de PMEs brasileiras. O "time" do Blu
é composto por agentes especializados que trabalham sobre dados do negócio do cliente.

**Princípios fundamentais:**

- Agentes são **stateless** — toda memória de negócio fica no Supabase.
- Agentes **não conversam diretamente** entre si — comunicam via shared memory.
- **Nenhum agente pula uma camada** na hierarquia L1→L4.
- **Somente `data-entry` escreve transações** — todos os outros são read-only.

---

## Arquitetura: 4 Camadas

```
L4  Orchestrator (Frontdesk)       — recebe input do usuário, classifica, roteia
L3  Domain Specialists             — executa tarefas de domínio (financeiro, compras, etc.)
L2  Skills                         — unidades de trabalho (prompt + tools), stateless
L1  Tools (Tool Pool API)          — execute_sql · executar_rag · google_calendar · OCR …
```

---

## Agentes (L3–L4)

### `frontdesk` — Entry Point / Roteador (L4)

**Papel:** Ponto de entrada de toda interação com o usuário. Responde queries simples
diretamente (RAG, SQL básico). Roteia tarefas complexas ou de domínio específico para
o specialist correto via `route_to_specialist`.

**Regra:** Nunca faz análise profunda. Se precisar de mais de 1-2 consultas simples,
roteie para o specialist.

**Skills:** `data_access`, `sql_analytics`
**Tools extras (não-skill):** `route_to_specialist`
**Modelo:** FAST | **Max turns:** 10 | **Memory:** session

---

### `data-entry` — Gateway de Escrita (L3)

**Papel:** **Único agente autorizado a escrever transações operacionais.**
Recebe input em linguagem natural (venda, registro de cliente/fornecedor, despesa, evento), faz parsing
estruturado e persiste via `register_transaction`.

**Regra crítica:** Qualquer outro agente que receber um pedido de registro
**deve redirecionar para `data-entry`**, nunca executar a escrita ele mesmo.

**Skills:** `ledger`, `data_access`, `csv_analytics`, `sql_analytics`
**Modelo:** DEFAULT | **Max turns:** 6 | **Memory:** session

---

### `platform` — Configuração da Plataforma (L3)

**Papel:** Converte linguagem natural em configurações operacionais — cria rotinas,
define metas, gerencia automações. Ativado por frases imperativas como
"cria uma rotina", "define uma meta", "ativa o monitoramento de X".

**Skills:** `platform_ops`, `data_access`
**Modelo:** DEFAULT | **Max turns:** 6

---

### `financeiro` — Saúde Financeira (L3)

**Papel:** Análise financeira read-only. Fluxo de caixa, tendências de receita,
padrões de despesa, anomalias, relatórios estruturados com gráficos.
Usado em rotinas para snapshots semanais e alertas.

**Regra:** Não registra transações. Pedidos de escrita → redirecionar para `data-entry`.

**Skills:** `financeiro_ops`, `data_access`, `sql_analytics`, `analytics_charts`, `csv_analytics`
**Modelo:** POWERFUL | **Max turns:** 5

---

### `compras` — Procurement e Fornecedores (L3)

**Papel:** Ciclo completo de compras. Gestão de catálogo de fornecedores, pipeline
de lista de compras (parse → validar → otimizar → PO), despacho de RFQ via WhatsApp/email,
parsing de respostas, criação de ordens de compra. Identifica riscos de fornecedor
e recomenda otimização de custo.

**Skills:** `compras_ops`, `data_access`, `sql_analytics`, `communication`
**Modelo:** DEFAULT | **Max turns:** 6

---

### `crm` — Relacionamento com Clientes (L3)

**Papel:** Análise de relacionamento e comunicação com clientes. LTV, churn risk,
NPS, segmentação, oportunidades de reativação. Redige mensagens personalizadas
via WhatsApp e email. Usado em rotinas de cobrança, follow-up e campanhas de satisfação.

**Skills:** `crm_ops`, `data_access`, `sql_analytics`, `communication`, `analytics_charts`
**Modelo:** POWERFUL | **Max turns:** 8

---

### `agenda` — Calendário e Agenda (L3)

**Papel:** Planejamento de agenda, verificação de disponibilidade, detecção de conflitos,
slots ótimos. Gestão de boards Monday.com: listar, criar, atualizar itens e status.
Produz briefings de reuniões e digests de agenda.

**Scope:** Calendário + Monday.com. Google Calendar = PREMIUM. Google Docs/Sheets/Gmail = `doc-writer`.

**Skills:** `agenda_ops`, `sql_analytics`, `monday`, `calendar`, `meeting_brief`
**Modelo:** DEFAULT | **Max turns:** 5

---

### `data-analyst` — Análise Quantitativa (L3)

**Papel:** Análise quantitativa profunda. Tendências, correlações, modelagem de cenários
sobre dados financeiros, de compras e clientes. Exporta relatórios para Google Docs/Sheets.
Ativado quando a pergunta é analítica e não pertence a um domínio único.

**Skills:** `data_access`, `sql_analytics`, `analytics_charts`, `csv_analytics`, `document_io`
**Modelo:** POWERFUL | **Max turns:** 6

---

### `strategy` — Estratégia e Síntese Cross-Domain (L3)

**Papel:** Análise estratégica que cruza múltiplos domínios (financeiro × compras × clientes × agenda).
Identifica padrões de KPI, oportunidades de crescimento, posicionamento competitivo.
Produz morning/EOD digests e briefings estratégicos.

**Ativar quando:** pergunta toca 2+ áreas de negócio, ou usa linguagem estratégica
("investimento", "prioridade", "tendência", "como está meu negócio", "o que devo focar").

**Topologia:** `fanout` — coleta dados em paralelo de finance + CRM + market, depois reduz.

**Skills:** `data_access`, `sql_analytics`, `analytics_charts`, `strategy_ops`
**Modelo:** POWERFUL | **Max turns:** 8

---

### `doc-writer` — Criação de Documentos (L3)

**Papel:** Criação de documentos estratégicos. Pesquisa a base de conhecimento,
redige documentos estruturados (briefs, SOPs, propostas, relatórios), exporta para
Google Docs/Sheets, persiste conteúdo aprovado na KB.

**Ativar quando:** usuário pede explicitamente para escrever, redigir ou criar um documento.

**Skills:** `data_access`, `knowledge_base_write`, `document_io`, `document_curation`, `notion`
**Modelo:** POWERFUL | **Max turns:** 8

---

### `fiscal-agent` — Nota Fiscal (L3, ENTERPRISE stub)

**Papel:** Emissão de NF-e/NFS-e, validação de dados fiscais, status SEFAZ.
Candidato a ser incorporado ao `financeiro` pós-MVP.

**Skills:** `fiscal`, `data_access`, `sql_analytics`
**Modelo:** DEFAULT | **Max turns:** 4

---

### `context-gatherer` — Coleta de Contexto (Background, não visível)

**Papel:** Agente de background. Mapeia fontes de dados do cliente ao schema da plataforma,
processa documentos ingeridos (OCR, extração, sumarização), persiste contexto estruturado
na KB. Roda por agendamento e via webhooks (`onboarding_complete`, `doc_ingested`).

**Regra:** Não é um agente de chat — nunca aparece como opção de roteamento. Não registra
transações (escrita = `data-entry`).

**Skills:** `data_access`, `sql_analytics`, `knowledge_base_write`, `onboarding`, `document_curation`
**Modelo:** DEFAULT | **Max turns:** 8 | **Memory:** none (stateless por trigger)

---

## Skills (L2)

Skills são unidades de trabalho reutilizáveis: um prompt + um subset de tools.
Cada skill é stateless e executa uma capacidade específica e bem delimitada.

### Skills Transversais (usadas por múltiplos agentes)

| Skill                  | O que faz                                           | Tools principais                                              |
| ---------------------- | --------------------------------------------------- | ------------------------------------------------------------- |
| `data_access`          | Busca semântica na KB (RAG) + catálogo de dados     | `executar_rag_cliente`, `query_data_catalog`                  |
| `sql_analytics`        | Queries SQL sobre dados estruturados do negócio     | `execute_sql`                                                 |
| `analytics_charts`     | Gera gráficos HTML (bar, line, pie) com Chart.js    | `generate_chart_html`                                         |
| `csv_analytics`        | Inspeção de colunas de arquivos CSV antes de import | `peek_csv_columns`                                            |
| `communication`        | Redigir e enviar WhatsApp/email; parsear replies    | `send_whatsapp_message`, `send_email`, `parse_business_reply` |
| `document_io`          | Criar/ler/editar Google Docs e Sheets               | `google_docs_*`, `write_to_sheet`, `export_to_sheet`          |
| `ledger`               | Escrita transacional (somente `data-entry`)         | `register_transaction`, `execute_sql`                         |
| `knowledge_base_write` | Persistir conteúdo na KB do cliente                 | `write_summary_to_kb`, `update_context_document`              |

### Skills de Domínio

| Skill               | Agente principal                 | O que faz                                                        |
| ------------------- | -------------------------------- | ---------------------------------------------------------------- |
| `platform_ops`      | `platform`                       | Criar/listar rotinas, definir metas, confirmar antes de executar |
| `financeiro_ops`    | `financeiro`                     | Análise financeira read-only (fluxo de caixa, receita, despesas) |
| `compras_ops`       | `compras`                        | Pipeline completo de compras (parse → validate → PO → RFQ)       |
| `crm_ops`           | `crm`                            | Análise de clientes read-only (churn, LTV, NPS, segmentação)     |
| `agenda_ops`        | `agenda`                         | Contexto de scheduling via SQL/RAG (sem Google Calendar)         |
| `calendar`          | `agenda`                         | Google Calendar: query, write, import de Sheets (PREMIUM)        |
| `monday`            | `agenda`                         | Monday.com: boards, items, status, updates                       |
| `meeting_brief`     | `agenda`                         | Briefing pré-reunião com contexto do participante                |
| `strategy_ops`      | `strategy`                       | Análise cross-domain de KPIs + prioridades estratégicas          |
| `document_curation` | `context-gatherer`, `doc-writer` | OCR + extração + sumarização de documentos                       |
| `onboarding`        | `context-gatherer`               | Mapeamento inicial: config, fontes de dados, schema              |
| `notion`            | `doc-writer`                     | CRUD de páginas e bancos de dados no Notion                      |
| `fiscal`            | `fiscal-agent`                   | Emissão NF-e/NFS-e, validação fiscal, status SEFAZ               |

### Skills de Rotinas (narrativas puras — sem tools)

Chamadas pelo engine de rotinas (step type `"skill"`). O contexto é pré-injetado
pelo engine; `required_tool_names` é vazio intencionalmente.

| Skill                    | Rotina associada     | O que produz                        |
| ------------------------ | -------------------- | ----------------------------------- |
| `morning_plan`           | `morning_sync`       | Plano diário priorizado             |
| `end_of_day_digest`      | `end_of_day_digest`  | Digest EOD: feito/aberto            |
| `weekly_summary`         | `weekly_review`      | Resumo semanal com tendências       |
| `insights_synthesis`     | `daily_insights`     | Narrativa cross-domain              |
| `hidden_patterns`        | `pattern_analysis`   | Anomalias e sazonalidades           |
| `competitor_analysis`    | `market_monitor`     | Análise competitiva                 |
| `reconciliation_report`  | `monthly_close`      | Relatório de conciliação            |
| `finance_monitor_report` | `financeiro_monitor` | Snapshot de saúde financeira        |
| `clients_monitor_report` | `clientes_monitor`   | Snapshot de saúde de clientes       |
| `agenda_monitor_report`  | `agenda_monitor`     | Snapshot de agenda e follow-ups     |
| `inventory_digest`       | `compras_monitor`    | Digest de estoque e POs             |
| `followup_draft`         | `followup`           | Mensagem de pós-venda personalizada |
| `collection_messages`    | `collection`         | Mensagem de cobrança por prazo      |
| `reactivation_proposal`  | `reactivation`       | Proposta de reativação de cliente   |
| `satisfaction_survey`    | `nps_survey`         | Survey de satisfação pós-entrega    |

---

## Regras de Roteamento (para o Frontdesk)

| Situação                                          | Rotear para                  |
| ------------------------------------------------- | ---------------------------- |
| Registrar venda, compra, despesa, evento          | `data-entry`                 |
| Relatório financeiro, fluxo de caixa              | `financeiro`                 |
| Fornecedores, cotações, ordens de compra          | `compras`                    |
| Clientes, churn, reativação, CRM                  | `crm`                        |
| Agenda, reuniões, Monday.com                      | `agenda`                     |
| Documento escrito, SOP, proposta                  | `doc-writer`                 |
| Análise quantitativa profunda (sem domínio único) | `data-analyst`               |
| Estratégia, visão geral do negócio, 2+ domínios   | `strategy`                   |
| Criar rotina, definir meta, configurar plataforma | `platform`                   |
| NF-e, NFS-e, fiscal                               | `fiscal-agent`               |
| Query simples de KB ou SQL                        | Resolver direto (sem rotear) |

---

## Matriz Agente × Skills

```
                       data_access  sql_analytics  analytics_charts  communication  ledger  knowledge_base_write  document_io
frontdesk                  ✓             ✓
data-entry                 ✓             ✓                                              ✓
platform                   ✓
financeiro                 ✓             ✓               ✓
compras                    ✓             ✓                                  ✓
crm                        ✓             ✓               ✓                  ✓
agenda                     ✓             ✓
data-analyst               ✓             ✓               ✓                                                             ✓
strategy                   ✓             ✓               ✓
doc-writer                 ✓                                                                        ✓                   ✓
context-gatherer           ✓             ✓                                                          ✓
fiscal-agent               ✓             ✓
```

_(Skills de domínio e rotinas omitidos aqui por clareza — ver seção Skills acima)_

---

## O que NÃO está definido ainda (decisões abertas)

- **Memory Agent** — skill leve pós-conversa que escreve na `shared_business_memory`.
  Será L2 skill ou L3 specialist? (ver PRD Blu Intelligent Memory)
- **`fiscal-agent`** — candidato a merge no `financeiro` pós-MVP.
- **`compras_ops` sub-skills** — split em `supplier_mgmt` + `procurement_pipeline` + `rfq_ops`
  planejado mas ainda não executado (D9 refactor).
- **Supplier-agent** — aparece no FEATURE_MAP mas não existe no registry. Remover referência
  ou criar o agente?

---

## Histórico de Decisões de Arquitetura

| ID  | Decisão                                                                   |
| --- | ------------------------------------------------------------------------- |
| D1  | `execute_sql` absorveu `executar_sql_agent` (modo direct/agent)           |
| D3  | Somente `data-entry` pode escrever transações via `ledger` skill          |
| D5  | `parse_business_reply` absorveu `parse_supplier_reply`                    |
| D6  | `calendar` separado de `document_io`; Google Calendar = PREMIUM           |
| D7  | `knowledge_base_write` (write) separado de `document_curation` (ingest)   |
| D8  | 13 tools de fornecedores consolidadas em `compras_ops` (sub-split adiado) |
| D9  | Sub-split de compras_ops em 3 skills — planejado, não executado           |
| D12 | RAG + catálogo unificados em `data_access`                                |
