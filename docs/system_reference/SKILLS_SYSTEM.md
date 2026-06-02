# Blu Skills System
> Fonte da verdade para o catálogo de skills — definições, ferramentas disponíveis, e quais agentes consomem cada skill.
> Atualizado em: 2026-06-02
> Ver também: [`docs/AGENT_SYSTEM.md`](./AGENT_SYSTEM.md) · [`libs/blu_agent_framework/src/blu_agent_framework/skills.py`](../libs/blu_agent_framework/src/blu_agent_framework/skills.py)

---

## Conceito

Uma **skill** é um sub-agente efêmero e focado, ativado por um agente especialista para executar uma tarefa específica. Cada skill tem:

- **Prompt próprio no Langfuse** (`skill:{name}:system`) — define o comportamento para aquela tarefa
- **Whitelist de ferramentas** — só as ferramentas necessárias para a tarefa estão disponíveis
- **Orçamento de turnos** (`max_turns`) — evita loops infinitos
- **Política de falha** (`on_max_turns`) — `return_partial` para tarefas de leitura; `raise` para tarefas transacionais

> **Regra de ouro:** Skill ≠ Agente. A skill executa _uma tarefa_. O agente tem _uma identidade_.  
> Se o escopo da skill = escopo do agente inteiro, a lógica pertence ao `agents/xxx` no Langfuse, não como skill.

---

## Mapa de Skills por Agente

```
frontdesk          → data_access, sql_analytics
data-entry         → ledger, data_access, csv_analytics, sql_analytics
platform           → platform_ops, data_access
financeiro         → data_access, sql_analytics, analytics_charts, csv_analytics
compras            → data_access, sql_analytics, communication
crm                → data_access, sql_analytics, communication, analytics_charts
agenda             → data_access, sql_analytics, monday, calendar, meeting_brief
data-analyst       → data_access, sql_analytics, analytics_charts, csv_analytics, document_io
strategy           → data_access, sql_analytics, analytics_charts, insights_synthesis, hidden_patterns
doc-writer         → data_access, knowledge_base_write, document_io, document_curation, notion
context-gatherer   → data_access, sql_analytics, knowledge_base_write, onboarding, document_curation
fiscal-agent       → fiscal, data_access, sql_analytics
```

---

## Catálogo de Skills

---

### 🔵 Transversais — disponíveis em quase todos os agentes

---

#### `data_access`
**Camada de leitura unificada: busca semântica na KB + catálogo de dados**

| | |
|---|---|
| **Prompt** | `skill:data_access:system` |
| **Ferramentas** | `executar_rag_cliente`, `query_data_catalog` |
| **max_turns** | 4 |
| **on_max_turns** | `return_partial` |
| **Agentes** | todos exceto `fiscal-agent` standalone |

Ponto de entrada para qualquer consulta de contexto de negócio: perfil da empresa, catálogo de produtos, histórico de processos, documentos indexados. `query_data_catalog` orienta o agente sobre quais tabelas existem antes de formular SQL.

---

#### `sql_analytics`
**Consultas SQL sobre dados estruturados de negócio**

| | |
|---|---|
| **Prompt** | `skill:sql_analytics:system` |
| **Ferramentas** | `execute_sql` (mode=`direct`\|`agent`, scope=`read`) |
| **max_turns** | 5 |
| **on_max_turns** | `return_partial` |
| **Agentes** | `frontdesk`, `data-entry`, `financeiro`, `compras`, `crm`, `agenda`, `data-analyst`, `strategy`, `context-gatherer`, `fiscal-agent` |

Acesso SQL a todas as tabelas de negócio: vendas, receitas, estoque, clientes, despesas, fornecedores. Sempre `scope=read` — escrita de transações é exclusiva do `data-entry` via `ledger`.

---

#### `analytics_charts`
**Geração de gráficos HTML via Chart.js**

| | |
|---|---|
| **Prompt** | `skill:analytics_charts:system` |
| **Ferramentas** | `generate_chart_html` |
| **max_turns** | 3 |
| **on_max_turns** | `return_partial` |
| **Agentes** | `financeiro`, `crm`, `data-analyst`, `strategy` |

Gera HTML autocontido com gráficos (bar, line, pie, doughnut, scatter). Usado após análise SQL para entregar visualizações ao usuário. Retorna arquivo HTML abrível no browser ou embutível em relatório.

---

#### `csv_analytics`
**Inspeção de colunas de arquivos CSV antes de análise ou importação**

| | |
|---|---|
| **Prompt** | `skill:csv_analytics:system` |
| **Ferramentas** | `peek_csv_columns` |
| **max_turns** | 2 |
| **on_max_turns** | `return_partial` |
| **Agentes** | `data-entry`, `financeiro`, `data-analyst` |

Lê estrutura do arquivo sem carregá-lo na memória: nomes de colunas, tipos inferidos, amostras, contagem de linhas. Pré-requisito para importação ou mapeamento de schema.

---

### 🟢 Escrita de dados — exclusivo de agentes autorizados

---

#### `ledger`
**Camada transacional de escrita — exclusiva do `data-entry`**

| | |
|---|---|
| **Prompt** | `skill:ledger:system` |
| **Ferramentas** | `register_transaction`, `execute_sql` (read para verificação) |
| **max_turns** | 3 |
| **on_max_turns** | `raise` |
| **Agentes** | `data-entry` (único) |

Persiste transações operacionais (vendas, compras, despesas, eventos) via `register_transaction`. O único ponto de escrita financeira da plataforma — todos os outros agentes são read-only e redirecionam aqui. `on_max_turns=raise` porque escrita parcial é inválida.

---

#### `knowledge_base_write`
**Escrita estruturada na base de conhecimento do cliente**

| | |
|---|---|
| **Prompt** | `skill:knowledge_base_write:system` |
| **Ferramentas** | `write_summary_to_kb`, `get_knowledge_status`, `update_context_document` |
| **max_turns** | 3 |
| **on_max_turns** | `raise` |
| **Agentes** | `doc-writer`, `context-gatherer` |

Persiste sumários, análises e contexto extraído como documentos na KB. Verifica cobertura antes de escrever para evitar duplicatas. Complementa `document_curation` (que extrai) — esta skill persiste. `on_max_turns=raise` porque ingestão parcial deixa a KB inconsistente.

---

### 🟡 Comunicação & Agenda

---

#### `communication`
**Draft, envio e parsing de mensagens WhatsApp e e-mail**

| | |
|---|---|
| **Prompt** | `skill:communication:system` |
| **Ferramentas** | `send_whatsapp_message`, `check_whatsapp_replies`, `send_email`, `read_emails`, `parse_business_reply` |
| **max_turns** | 4 |
| **on_max_turns** | `raise` |
| **Agentes** | `compras`, `crm` |

Canal de saída para clientes e fornecedores. Rascunha e envia mensagens outbound; parseia respostas inbound (RFQ, NPS, pagamento) extraindo dados estruturados. `on_max_turns=raise` porque envio parcial de mensagem é inválido.

---

#### `calendar`
**Google Calendar: consulta, criação e atualização de eventos**

| | |
|---|---|
| **Prompt** | `skill:calendar:system` |
| **Ferramentas** | `query_calendar`, `google_calendar_write`, `import_spreadsheet_schedule` |
| **max_turns** | 4 |
| **on_max_turns** | `raise` |
| **Agentes** | `agenda` |

Integração com Google Calendar: verifica disponibilidade, cria/atualiza eventos, importa agenda de planilhas em bulk. Timezone padrão: America/Sao_Paulo. Sempre confirma detalhes antes de escrever.

---

#### `monday`
**Monday.com: leitura e atualização de boards e itens**

| | |
|---|---|
| **Prompt** | `skill:monday:system` |
| **Ferramentas** | `monday_list_boards`, `monday_list_items`, `monday_create_item`, `monday_update_item_status`, `monday_get_board_summary`, `monday_get_item_updates`, `monday_summarize_board` |
| **max_turns** | 5 |
| **on_max_turns** | `raise` |
| **Agentes** | `agenda` |

Gerencia quadros Monday.com: lista boards/itens, atualiza status e datas, recupera comentários, sumariza estado do board.

---

#### `meeting_brief`
**Briefing pré-reunião com contexto de participantes e agenda**

| | |
|---|---|
| **Prompt** | `skill:meeting_brief:system` |
| **Ferramentas** | nenhuma (LLM puro — contexto injetado pelo agente) |
| **max_turns** | 3 |
| **on_max_turns** | `return_partial` |
| **Agentes** | `agenda` |

Produz briefing pré-reunião: contexto dos participantes, histórico de negócio, pontos-chave, itens sugeridos de pauta.

---

### 🟠 Documentos & Conhecimento

---

#### `document_curation`
**Pipeline de ingestão: OCR, extração e sumarização de documentos**

| | |
|---|---|
| **Prompt** | `skill:document_curation:system` |
| **Ferramentas** | `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data`, `compile_time_series` |
| **max_turns** | 5 |
| **on_max_turns** | `raise` |
| **Agentes** | `doc-writer`, `context-gatherer` |

Pipeline de extração de documentos: OCR em PDFs/imagens, sumarização por seção, extração de campos estruturados (contratos, notas fiscais), compilação de séries temporais. Só extrai — persistência é via `knowledge_base_write`.

---

#### `document_io`
**Google Docs e Sheets: criação, leitura e exportação**

| | |
|---|---|
| **Prompt** | `skill:document_io:system` |
| **Ferramentas** | `google_docs_create`, `google_docs_read`, `google_docs_write`, `google_docs_list`, `write_to_sheet`, `list_spreadsheets`, `export_to_sheet`, `create_spreadsheet_with_data` |
| **max_turns** | 5 |
| **on_max_turns** | `raise` |
| **Agentes** | `data-analyst`, `doc-writer` |

Canal de saída para documentos formais: cria e edita Google Docs e planilhas, exporta dados de análise, lista documentos existentes. Canal primário de output do `doc-writer`.

---

#### `notion`
**Notion: gerenciamento de páginas e bases de dados**

| | |
|---|---|
| **Prompt** | `skill:notion:system` |
| **Ferramentas** | `notion_search`, `notion_read_page`, `notion_query_database`, `notion_list_databases`, `notion_list_pages`, `notion_create_page`, `notion_update_page`, `notion_append_blocks`, `notion_delete_block` |
| **max_turns** | 5 |
| **on_max_turns** | `raise` |
| **Agentes** | `doc-writer` |

KB e wiki internos via Notion: busca, leitura, criação e atualização de páginas e databases. Sempre retorna URL da página após criação/atualização.

---

### 🔴 Operações de Plataforma

---

#### `platform_ops`
**Configuração de rotinas automatizadas e metas de negócio**

| | |
|---|---|
| **Prompt** | `skill:plataforma:system` |
| **Ferramentas** | `criar_rotina`, `listar_rotinas_catalogo`, `listar_rotinas_personalizadas`, `criar_rotina_personalizada`, `enviar_rotina_para_aprovacao`, `definir_meta`, `listar_metas`, `executar_rag_cliente` |
| **max_turns** | 6 |
| **on_max_turns** | `raise` |
| **Agentes** | `platform` |

Converte linguagem natural em configurações operacionais: ativa rotinas, define metas, gerencia automações. Fluxo: elicita intenção → apresenta plano em linguagem simples → executa só após confirmação explícita.

---

#### `onboarding`
**Coleta inicial de contexto: configuração, fontes de dados e mapeamento de schema**

| | |
|---|---|
| **Prompt** | `skill:onboarding:system` |
| **Ferramentas** | `check_config_completeness`, `save_config_field`, `get_agent_requirements`, `finalize_config`, `list_data_sources`, `suggest_column_mapping`, `update_schema_mapping`, `peek_csv_columns` |
| **max_turns** | 6 |
| **on_max_turns** | `raise` |
| **Agentes** | `context-gatherer` |

Guia o processo inicial de configuração do cliente: verifica campos faltantes, mapeia fontes de dados ao schema Blu, sugere e confirma mapeamentos de colunas, finaliza configuração. Abordagem conversacional — uma etapa por vez.

---

#### `fiscal`
**Emissão de NF-e / NFS-e e integração SEFAZ**

| | |
|---|---|
| **Prompt** | `skill:fiscal:system` |
| **Ferramentas** | `fiscal_preparar_dados_nfe`, `fiscal_status_integracao`, `executar_rag_cliente`, `execute_sql`, `whatsapp_enviar_mensagem` |
| **max_turns** | 4 |
| **on_max_turns** | `raise` |
| **Agentes** | `fiscal-agent` |

Emite notas fiscais eletrônicas, valida dados fiscais e verifica status de integração SEFAZ. `on_max_turns=raise` porque emissão parcial de NF é inválida.

---

### 🟣 Rotinas Narrativas — skills pure-LLM (sem ferramentas)

> Estas skills são chamadas pelo motor de rotinas. O contexto (KPIs, dados) é **pré-injetado pelo motor** antes da execução — a skill só redige a narrativa. Por isso `required_tool_names=[]`.

---

#### `reconciliation_report`
Narrativa mensal de reconciliação de caixa: anomalias por categoria, top merchants, discrepâncias.
**Agentes:** `financeiro` (via rotina `financeiro_monitor`)

#### `finance_monitor_report`
Snapshot de saúde financeira: receita vs meta, centros de custo, alertas de fluxo de caixa.
**Agentes:** `financeiro` (via rotina `financeiro_monitor`)

#### `clients_monitor_report`
Snapshot de clientes: ativos vs churned, inadimplentes, sinais de NPS, ações prioritárias.
**Agentes:** `crm` (via rotina `clientes_monitor`)

#### `agenda_monitor_report`
Snapshot de agenda: follow-ups atrasados, reuniões próximas, lacunas de contato.
**Agentes:** `agenda` (via rotina `agenda_monitor`)

#### `inventory_digest`
Digest de estoque e compras: alertas de estoque baixo, atrasos de fornecedor, status de POs.
**Agentes:** `compras` (via rotina `compras_monitor`)

#### `morning_plan`
Plano diário priorizado a partir de KPIs, agenda, aprovações pendentes e alertas.
**Agentes:** `strategy` (via rotina `morning_sync`)

#### `end_of_day_digest`
Resumo do dia: tarefas concluídas, itens em aberto, destaques.
**Agentes:** `strategy` (via rotina `end_of_day_digest`)

#### `weekly_summary`
Sumário semanal de performance: destaques, tendências de KPI, foco recomendado.
**Agentes:** `strategy` (via rotina `weekly_summary`)

#### `insights_synthesis`
Síntese cross-domain de insights (finanças + clientes + compras + agenda) em narrativa estratégica unificada.
**Agentes:** `strategy`

#### `hidden_patterns`
Análise de séries temporais de vendas e KPIs: anomalias, sazonalidade, picos/quedas inesperados.
**Agentes:** `strategy`

#### `competitor_analysis`
Análise competitiva: posicionamento, gaps, oportunidades e ameaças versus concorrentes.
**Agentes:** `strategy`

#### `followup_draft`
Mensagem de follow-up pós-venda para cliente específico, com sugestões de cross-sell.
**Agentes:** `crm`

#### `collection_messages`
Mensagens de cobrança personalizadas por nível de atraso (amigável / firme / urgente).
**Agentes:** `crm`

#### `reactivation_proposal`
Proposta de reativação para cliente inativo com histórico de compras e oferta especial.
**Agentes:** `crm`

#### `satisfaction_survey`
Mensagem de pesquisa de satisfação pós-entrega adaptada ao perfil do cliente.
**Agentes:** `crm`

---

## Regras de Governance

1. **Skill ≠ Agente** — se o escopo da skill é igual ao escopo do agente, a lógica pertence no `agents/xxx` do Langfuse
2. **Um único gateway de escrita** — `register_transaction` só existe na skill `ledger`, usada exclusivamente pelo `data-entry`
3. **Separação extração / persistência** — `document_curation` extrai; `knowledge_base_write` persiste
4. **HITL é middleware, não skill** — `requires_confirmation=True` fica no `ToolRegistry`, não como skill separada
5. **Rotinas narrativas são pure-LLM** — contexto pré-injetado pelo motor; `required_tool_names=[]` é intencional
6. **Prompts no Langfuse são obrigatórios** — toda skill deve ter `skill:{name}:system` com label `production`
7. **Nomenclatura**: skill = `snake_case`; prompt key = `skill:{name}:system`; agente = `kebab-case`
