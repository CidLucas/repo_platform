# Blu LLM Pipeline — Mapa de Prioridades de Validação

> Arquivo lido pelo cron de testes a cada run para selecionar qual skill/cenário testar.
> Ordem = prioridade de execução. O cron avança para o próximo item não testado hoje.

---

## Fase 0 — Baseline: FrontDesk + SQL _(semana 1)_

**Objetivo:** confirmar que o agente principal funciona de ponta a ponta com dados reais.
**Critério de sucesso:** 4/5 queries corretas sem hallucination de dados.

| #   | Skill/Cenário | Mensagem de teste                                       | Tool esperada                                         |
| --- | ------------- | ------------------------------------------------------- | ----------------------------------------------------- |
| 0.1 | frontdesk     | "Oi, como tá meu negócio hoje?"                         | contexto do negócio (morning_brief / context_service) |
| 0.2 | sql_analytics | "Quais foram minhas últimas vendas?"                    | execute_sql → fato_transacoes                         |
| 0.3 | sql_analytics | "Qual meu estoque atual?"                               | execute_sql → dim_inventory                           |
| 0.4 | sql_analytics | "Cadastra uma venda de R$500 para o cliente João Silva" | register_transaction                                  |
| 0.5 | rag_search    | "Pesquisa no meu knowledge base sobre fornecedores"     | executar_rag_cliente                                  |

---

## Fase 1 — Relatórios & Morning Plan _(semana 2)_

**Objetivo:** validar as skills de rotinas que geram narrativa sobre dados.
**Critério de sucesso:** narrativas sem dados inventados, seções completas, tom PME.

| #   | Skill/Cenário         | Mensagem de teste                                   | Tool esperada                |
| --- | --------------------- | --------------------------------------------------- | ---------------------------- |
| 1.1 | morning_plan          | "Faz meu planejamento do dia"                       | morning_plan skill           |
| 1.2 | end_of_day_digest     | "Me dá um resumo do que aconteceu hoje"             | end_of_day_digest skill      |
| 1.3 | weekly_summary        | "Me mostra o resumo financeiro da semana"           | weekly_summary + execute_sql |
| 1.4 | reconciliation_report | "Gera o relatório de conciliação financeira do mês" | reconciliation_report skill  |

---

## Fase 2 — Inserção de Dados via Conversa _(semana 2-3)_

**Objetivo:** validar o flow de data entry NL → banco de dados.
**Critério de sucesso:** dados gravados corretamente, sem gravação sem confirmação (HITL).

| #   | Skill/Cenário     | Mensagem de teste                                                     | Tool esperada                           |
| --- | ----------------- | --------------------------------------------------------------------- | --------------------------------------- |
| 2.1 | financeiro        | "Comprei R$2.300 de material elétrico do fornecedor Elétrica ABC"     | register_transaction                    |
| 2.2 | fornecedores      | "Adiciona novo fornecedor: XYZ Materiais, contato João, tel 11-99999" | add_supplier                            |
| 2.3 | financeiro        | "Cria meta de faturamento de R$50k para esse mês"                     | definir_meta                            |
| 2.4 | plataforma        | "Ativa a rotina de cobrança semanal"                                  | criar_rotina                            |
| 2.5 | financeiro (HITL) | "Registra saída de R$800 de material de limpeza"                      | register_transaction + confirmação HITL |

---

## Fase 3 — Agentes de Domínio _(semana 3-4)_

**Objetivo:** validar especialistas de domínio (CRM, compras, financeiro).

| #   | Skill/Cenário   | Mensagem de teste                                     | Tool esperada                      |
| --- | --------------- | ----------------------------------------------------- | ---------------------------------- |
| 3.1 | crm             | "Quais clientes estão em atraso?"                     | execute_sql + collection_messages  |
| 3.2 | followup_draft  | "Manda follow-up para o cliente Empresa Beta"         | followup_draft skill               |
| 3.3 | fornecedores    | "Quais fornecedores têm melhor preço para parafusos?" | execute_sql + executar_rag_cliente |
| 3.4 | fornecedores    | "Gera uma RFQ para 500 unidades de parafuso M6"       | dispatch_rfq                       |
| 3.5 | financeiro      | "Qual meu fluxo de caixa dos últimos 30 dias?"        | analytics_v2                       |
| 3.6 | hidden_patterns | "Tem alguma anomalia nas minhas despesas?"            | hidden_patterns skill              |

---

## Fase 4 — Integrações Externas _(semana 4-5)_

**Objetivo:** validar agentes de integração (Monday, Google Agenda, google drive).

| #   | Skill/Cenário     | Mensagem de teste                                       | Tool esperada             |
| --- | ----------------- | ------------------------------------------------------- | ------------------------- |
| 4.1 | monday            | "Quais boards eu tenho no Monday?"                      | monday_list_boards        |
| 4.2 | monday            | "Cria item 'Reunião com fornecedor X' no board Compras" | monday_create_item        |
| 4.3 | monday            | "Atualiza status do item Y para Em andamento"           | monday_update_item_status |
| 4.4 | monday            | "Me dá um resumo do board Projetos"                     | monday_summarize_board    |
| 4.5 | agenda            | "Quais reuniões tenho essa semana?"                     | query_calendar            |
| 4.6 | agenda            | "Cria reunião com João amanhã às 14h"                   | google_calendar_write     |
| 4.7 | meeting_brief     | "Manda o brief da reunião de amanhã"                    | meeting_brief skill       |
| 4.8 | google_drive      | "Eu tenho algum relatório anterior no meu drive?"       | google_docs_list          |
| 4.9 | google_drive      | "Abre o documento 'Planilha de Custos Maio' do Drive"   | google_docs_read          |
| 4.10 | google_drive     | "Cria um doc no Drive com o resumo financeiro de hoje"  | google_docs_create        |
| 4.11 | google_drive     | "Atualiza o relatório mensal no Drive com os dados de abril" | google_docs_write    |
| 4.12 | google_drive     | "Exporta meu fluxo de caixa para uma planilha no Drive" | create_spreadsheet_with_data |

---

## Fase 5 — Synthesis & Estratégia _(semana 5-6)_

**Objetivo:** cruzar domínios e gerar insights estratégicos.

| #   | Skill/Cenário       | Mensagem de teste                                        | Tool esperada                  |
| --- | ------------------- | -------------------------------------------------------- | ------------------------------ |
| 5.1 | insights_synthesis  | "Quais clientes compram mais quando tenho estoque alto?" | synthesis cross-domínio        |
| 5.2 | hidden_patterns     | "Analisa padrões ocultos no meu negócio"                 | hidden_patterns skill          |
| 5.3 | competitor_analysis | "Faz análise competitiva dos concorrentes X e Y"         | competitor_analysis + crawl4ai |

---

## Como o cron usa este arquivo

1. Lê este arquivo no início de cada run
2. Lista os arquivos em `docs/blu_app/tests/` para ver quais itens (por `#`) já foram testados hoje
3. Pega o próximo item não testado (ordem numérica: 0.1 → 0.2 → ... → 5.3)
4. Se todos foram testados hoje, recomeça do 0.1
5. Nomeia os arquivos de output como `cases_<fase>_<skill>_<YYYYMMDD_HHMM>.md` e `report_<fase>_<skill>_<YYYYMMDD_HHMM>.md`
