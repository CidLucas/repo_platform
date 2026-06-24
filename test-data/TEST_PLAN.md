# Plano de Teste — Pipeline de Ingestão de Dados (Blu)

> **Objetivo:** Validar cada ponto de entrada de dados do usuário no Blu, desde o upload
> até a disponibilização para consulta via agentes (RAG / fatos / shared memory).
>
> **Personas de teste:** Carolina (designer), Lúcia (buffet), NovaTech (TI)
> Dados em: `test-data/personas/`
>
> **Última atualização:** 24-Jun-2026

---

## 📋 Visão Geral do Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                            FORMAS DE RECEBER CONTEXTO                                │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  FASE 1 ─ Planilhas de NF (Onboarding Step "Dados")                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Upload CSV/XLSX  →  Parse Headers  →  match-columns (EF)                     │   │
│  │                                            ↓                                  │   │
│  │              User Review Mapping → Confirm → run-csv-etl                      │   │
│  │                                            ↓                                  │   │
│  │        csv_import_staging → reg_jobs → fato_transacoes (dimensional)          │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  FASE 2 ─ Conectores Diretos (BigQuery, PostgreSQL, etc.)                           │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Credential Form → discover-bigquery-columns → match-columns                   │   │
│  │                             → run-sync-etl → reg_jobs                         │   │
│  │                             → etl-bigquery-ingest (paginado 10k)              │   │
│  │                             → ingest_staging → apply_staging_to_facts         │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  FASE 3 ─ Extratos Bancários (CSV)                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Upload CSV → Parse (Nubank/Itaú) → Column Mapping                             │   │
│  │                  → fato_transacoes (tipo_lancamento='bancario')               │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  FASE 4 ─ Documentos Gerais (PDFs, contratos, cardápios, etc.)                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Upload File (UI) → Storage (knowledge-base) → vector_db.documents (pending)   │   │
│  │                                                    ↓                          │   │
│  │  ┌── Simples (PDF texto, DOCX, TXT) ──→ process-document EF                  │   │
│  │  │                                          ↓                                 │   │
│  │  │    parse → chunk (400t) → embed (Cohere 384d) → enrich (LLM) → insert     │   │
│  │  │                                          ↓                                 │   │
│  │  │    vector_db.document_chunks → client_knowledge_documents                  │   │
│  │  │                                                                           │   │
│  │  └── Complexo (scan PDF, PPTX, XLSX) → tool_pool_api /v1/ingest/document     │   │
│  │                                           ↓                                  │   │
│  │             DoclingParser (OCR + tabelas + layout) → process-document         │   │
│  │                                           ↓                                  │   │
│  │             (com pre_extracted_text) → vector_db.document_chunks              │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  FASE 5 ─ Integrações Bancárias (Polp / Open Finance)                               │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ polp-connect → auth → polp-webhook → polp_transactions                       │   │
│  │                 → sync_polp_transactions → fato_transacoes                    │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  FASE 6 ─ Onboarding Shared Memory Hook                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Pós-onboarding → onboarding_shared_memory_hook.py                             │   │
│  │                    ↓                                                          │   │
│  │   shared_business_memory (company_profile, brand_voice, goals, snapshot)      │   │
│  │                                                                               │   │
│  │   + Post-flight hook (toda execução de agente):                               │   │
│  │     agent_result + agent_metadata → shared_business_memory                    │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  FASE 7 ─ Shared Memory / Light RAG + SBM Synthesis                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Agent → executar_rag_cliente (MCP tool)                                       │   │
│  │    ↓                                                                          │   │
│  │  create_rag_retriever → search-documents EF                                    │   │
│  │    ├── Cohere embed query → vector search (cosine IP)                          │   │
│  │    ├── hybrid_match_documents() (vector + FTS + RRF fusion)                   │   │
│  │    ├── reranker (Cohere Rerank opcional)                                       │   │
│  │    ├── MMR diversifier (opcional)                                              │   │
│  │    └── chunks + metadata + scores → LLM                                       │   │
│  │                                                                               │   │
│  │  + SBM → LightRAG Synthesis (job semanal):                                     │   │
│  │    shared_business_memory → Markdown → LightRAG ainsert_custom_kg()           │   │
│  │                                   → knowledge_graph_summary (T4.3)            │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧪 FASE 1: Planilhas de NF via Onboarding (Column Mapping)

### Fluxo completo

```
Usuário → StepData → "Upload CSV/XLSX" → parseSpreadsheetHeaders()
                                          ↓
                    headers[] → match-columns EF
                                          ↓
                    ColumnMappingResult (matched, unmatched,
                    needs_review, confidence_scores)
                                          ↓
                    StepMapping → user confirma/corrige mapeamento
                                          ↓
                    StepLaunch → bootstrap → ETL pipeline
```

### O que testar

| # | Teste | Persona | Arquivo | O que verificar |
|---|---|---|---|---|
| 1.1 | **Upload CSV NFs de serviço** | Carolina | `notas-fiscais/nfs_servicos_prestados.csv` (37 linhas) | Headers detectados corretamente; `match-columns` mapeia `cliente`, `valor_servico`, `data_emissao`; ISS separado do valor líquido |
| 1.2 | **Upload CSV NFs de despesa** | Carolina | `notas-fiscais/nfs_compras_despesas.csv` (56 linhas) | Mapeamento de `fornecedor`, `valor`, `tipo`; dados de assinatura recorrente (Adobe, Google) |
| 1.3 | **Upload CSV vendas buffet** | Lúcia | `notas-fiscais/nfs_vendas_servicos.csv` (47 linhas) | Mix de PJ e PF; `observacao` com texto narrativo ("Prejuízo"); sazonalidade nov/dez |
| 1.4 | **Upload CSV compras insumos** | Lúcia | `notas-fiscais/nfs_compras_insumos.csv` (41 linhas) | Múltiplos fornecedores; Mercearia do Porto com observações de atraso |
| 1.5 | **Upload CSV vendas hardware** | NovaTech | `notas-fiscais/nfs_vendas_hardware.csv` (9 linhas) | Notas de alto valor (R$ 45K); `natureza_operacao` = SERVIÇO vs VENDA_HW |
| 1.6 | **Upload CSV contratos recorrentes** | NovaTech | `notas-fiscais/nfs_vendas_servicos_recorrentes.csv` (131 linhas) | Grande volume; dados mensais consistentes; mix de valores entre clientes |
| 1.7 | **Upload XLSX (planilha da Carol)** | Carolina | `planilhas/planilha_controle_carol.xlsx` | 2 abas (Projetos + Financeiro); `parseSpreadsheetHeaders` deve selecionar aba correta |
| 1.8 | **Upload XLSX fluxo de caixa** | NovaTech | `planilhas/fluxo_caixa_2025.xlsx` | Múltiplas abas; aba "Fluxo de Caixa" com datas e valores; `match-columns` com colunas não-padrão |

### Critérios de sucesso

☐ Headers detectados corretamente de CSV (delimitador `;`) e XLSX  
☐ `match-columns` retorna `matched` com confidence ≥ 0.8 para colunas óbvias (valor, data, cliente)  
☐ Colunas ambíguas vão para `needs_review` (ex: "Observação" com texto narrativo)  
☐ Usuário pode corrigir manualmente mapeamentos com baixa confiança  
☐ Dados inseridos em `analytics_v2.fato_transacoes` com `tipo_transacao` correto  
☐ `dim_clientes` populado com CPF/CNPJ dos clientes  
☐ `dim_fornecedores` populado com CNPJ dos fornecedores  

---

## 🧪 FASE 2: Conectores Diretos (BigQuery)

### Fluxo

```
StepData → "Conectar BigQuery" → CredentialForm (service_account JSON)
                                   ↓
        createBigQueryCredentialWithDiscovery()
                                   ↓
        discover-bigquery-columns EF → match-columns EF
                                   ↓
        → FDW Server → foreign table → enqueue_incremental_syncs()
```

### O que testar

| # | Teste | Persona | O que verificar |
|---|---|---|---|
| 2.1 | **Credencial BigQuery** | NovaTech | Service Account JSON armazenado com segurança no Vault |
| 2.2 | **Descoberta de colunas** | NovaTech | `discover-bigquery-columns` retorna schema da tabela |
| 2.3 | **FDW Server + Foreign Table** | NovaTech | `bigquery_servers` + `bigquery_foreign_tables` criados; CASCADE DELETE funcional |
| 2.4 | **Sync incremental** | NovaTech | `enqueue_incremental_syncs()` agenda pg_cron; `run_etl_job()` classifica `tipo_transacao` |

> ⚠️ **Dependência externa:** BigQuery real ou mock. Se não tiver acesso, testar apenas a criação da credencial + validação do schema.

---

## 🧪 FASE 3: Extratos Bancários

### Fluxo

```
Upload CSV → Parse (formato Nubank ou Itaú) → Column Mapping
                                                 ↓
        → analytics_v2.fato_transacoes (tipo_lancamento='bancario')
```

### O que testar

| # | Teste | Persona | Arquivo | O que verificar |
|---|---|---|---|---|
| 3.1 | **Extrato Nubank** | Carolina | `extratos/extrato_nubank_062026.csv` | Formato Nubank (data, valor, identificador, descricao); mapear para receita/despesa |
| 3.2 | **Extrato Itaú** | Lúcia | `extratos/extrato_itau_062026.csv` | Formato Itaú (vírgula decimal, ponto milhar); headers diferentes |
| 3.3 | **Extrato Nubank** | NovaTech | `extratos/extrato_nubank_062026.csv` | Alto volume; movimentações de grande valor (R$ 12K+, R$ 15K) |
| 3.4 | **Mesma transação em NF + Extrato** | Todos | Cruzar NFs com extratos | Transações devem aparecer nos dois lugares (ex: recebimento da Construtora Novo Norte na NF da Lúcia *e* no extrato) |

### Critérios de sucesso

☐ Formato Nubank (aspas, vírgula) parseado corretamente  
☐ Formato Itaú (decimal BR) parseado corretamente  
☐ `tipo_lancamento='bancario'` nos registros de extrato  
☐ Transações que já existem como NF não duplicam  

---

## 🧪 FASE 4: Documentos Gerais (Upload + process-document)

### Fluxo

```
Usuário → Upload File (UI) → Supabase Storage (knowledge-base bucket)
                                ↓
        INSERT vector_db.documents (status='pending')
                                ↓
        process-document EF → parse → chunk → embed → enrich → insert
                                ↓
        vector_db.document_chunks (status='completed')
                                ↓
        client_knowledge_documents upsert (inventário)
```

### Formatos suportados pelo parser

| Formato | Parser | Testar com |
|---|---|---|
| PDF | `pdf-parse` (texto selecionável) | DANFE, NFSe, contratos, cardápio, propostas |
| DOCX | `mammoth` | Contratos, carta de apresentação |
| TXT | raw text | Checklists, receitas, listas |
| CSV | → linha: `coluna: valor` | Qualquer CSV |
| JSON | raw parse | APIs |
| XML/HTML | strip tags | NFe XML |

### O que testar (por tipo de documento)

| # | Teste | Persona | Arquivo | O que verificar |
|---|---|---|---|---|
| 4.1 | **DANFE PDF escaneado** | Lúcia | `nfs_escaneadas/danfe_000.000.011.pdf` (Casamento) | PDF parseado; chunks com texto dos tributos; metadata: `theme=financial_reporting`; observação "PREJUÍZO" capturada |
| 4.2 | **NFSe PDF** | Carolina | `nfs_escaneadas/nfse_NFSE-2025-0012.pdf` (NovaTech) | Prestador/tomador extraídos; valor R$ 3.500; categoria `nf` |
| 4.3 | **DANFE hardware** | NovaTech | `nfs_escaneadas/danfe_novatech_000.000.015.pdf` (AutoPeças) | Produtos listados (Monitores Dell, SSDs); CFOP 5102 |
| 4.4 | **Cardápio PDF** | Lúcia | `cardapio_lucias_food.pdf` | Texto de receitas; `theme=product_knowledge`; word_cloud com ingredientes |
| 4.5 | **Contrato assinado** | Carolina | `contratos/contrato_carolina_lucia_assinado.pdf` | Partes contratuais; valor R$ 2.500; cláusulas preservadas |
| 4.6 | **Contrato de TI** | NovaTech | `contratos/contrato_novatech_autopecas_assinado.pdf` | Contrato desde 2019; R$ 2.500/mês; cláusula de renovação |
| 4.7 | **Flyer de divulgação** | Todos | `divulgacao/flyer_*.pdf` | Texto de marketing extraído; `theme=sales_strategy`; contato/whatsapp |
| 4.8 | **Proposta técnica** | NovaTech | `propostas_antigas/proposta_construtora_nuvem_45000.pdf` | Escopo técnico; R$ 45K; cronograma; `theme=operational_procedures` |
| 4.9 | **Proposta de design** | Carolina | `propostas_antigas/proposta_technova_28000.pdf` | 3 parcelas; condição de pagamento; prazo 45 dias |
| 4.10 | **Lista de convidados (ruído)** | Lúcia | `lista_convidados_casamento.txt` | Arquivo pessoal NÃO financeiro; classificado como ruído; não gerar KPI |
| 4.11 | **Receita de arroz (ruído)** | Lúcia | `receita_arroz_forno.txt` | Ingredientes culinários; `theme=general` mas com contexto de buffet |
| 4.12 | **Lista de senhas (ruído)** | NovaTech | `controle_senhas_interno.txt` | Documento interno sensível; não deve criar alerta financeiro |
| 4.13 | **Relatório de chamados** | NovaTech | `relatorio_chamados_maio2026.txt` | 47 chamados; dados operacionais; `theme=operational_procedures` |
| 4.14 | **Nota de empenho (ruído)** | NovaTech | `nota_empenho_prefeitura.txt` | Documento público fictício; não confundir com NF real |
| 4.15 | **XML NFe** | Lúcia | `exemplo_nfe_casamento.xml` | XML parseado como HTML/XML; tags de produto e impostos extraídos |
| 4.16 | **Planilha XLSX fornecedores** | Lúcia | `controle_fornecedores.xlsx` | 3 abas; Fornecedores com pontualidade (score 1-5); Eventos; Fluxo de Caixa |
| 4.17 | **Logo placeholder (PNG)** | Todos | `imagens/logo_placeholder_*.png` | **Deve falhar** — process-document não suporta imagem; erro 422 |

### Critérios de chunking

| # | Teste | O que verificar |
|---|---|---|
| C.1 | **Chunk size** | Nenhum chunk > 500 tokens estimados (target default 400) |
| C.2 | **Sentence overlap** | Últimas 2 sentenças de cada chunk repetidas no próximo |
| C.3 | **Documento curto** | Cardápio, contratos: chunks pequenos (1-3 chunks) |
| C.4 | **Documento longo** | Planilhas com muitas linhas: chunks por seção |
| C.5 | **Re-upload** | ON CONFLICT (document_id, content_hash) atualiza sem duplicar |

### Critérios de metadata enrichment

| # | Teste | O que verificar |
|---|---|---|
| M.1 | **word_cloud** | 10-15 termos extraídos; português respeitado |
| M.2 | **theme** | Um de 13 temas controlados (`financial_reporting`, `business_operations`, `product_knowledge`, etc.) |
| M.3 | **usage_context** | Frase curta em português descrevendo quando o chunk é útil |
| M.4 | **Categoria do documento** | Mapeada para `knowledge_document_types` quando reconhecida |
| M.5 | **Fallback** | Se LLM falha, chunk inserido sem enrichment (não é fatal) |

---

## 🧪 FASE 5: Integrações Bancárias (Polp / Open Finance)

### Fluxo

```
polp-connect (EF) → URL de autenticação → User auth
                                              ↓
        polp-webhook (EF) ← eventos em tempo real
         (integrations.updated, accounts.synchronized,
          transactions.created, bills.created)
                                              ↓
        polp_transactions → sync_polp_transactions()
                                              ↓
        analytics_v2.fato_transacoes (tipo_lancamento='bancario')
```

### O que testar

| # | Teste | Persona | O que verificar |
|---|---|---|---|
| 5.1 | **Webhook recebido** | Todas | `polp-webhook` processa eventos `transactions.created` e `accounts.synchronized` |
| 5.2 | **Sync manual** | Todas | `polp-sync` puxa contas + transações + faturas |
| 5.3 | **ETL para fato** | Todas | `sync_polp_transactions()` upsert em `fato_transacoes`; CREDIT→'venda', DEBIT→'compra' |
| 5.4 | **ON CONFLICT preserva classificação** | Todas | `tipo_transacao` e `categoria` já classificados não são sobrescritos |

> ⚠️ Dependência de API externa (Polp). Para teste offline, mockar webhook.

---

## 🧪 FASE 6: Onboarding Shared Memory Hook

### Fluxo

```
onboarding-bootstrap (após criar cliente)
    │
    └──► onboarding_shared_memory_hook.py (fire-and-forget)
            │
            ├── company_profile → SBM (entity_type='snapshot')
            ├── brand_voice → SBM
            ├── goals → SBM
            └── snapshot inicial do negócio


Post-flight (toda execução de agente via ChatService)
    │
    └──► memory_post_flight.py (fire-and-forget)
            │
            ├── agent_result (summary, tool_calls) → SBM
            ├── agent_metadata (session_id, elapsed) → SBM
            └── agent_link_pending (sugestões de links entre memórias)
```

### O que testar

| # | Teste | Persona | O que verificar |
|---|---|---|---|
| 6.1 | **Snapshot inicial pós-onboarding** | Carolina | SBM contém company_profile, brand_voice, goals após bootstrap |
| 6.2 | **Post-flight agent_result** | Todas | Após execução de agente, agent_result aparece na SBM |
| 6.3 | **Post-flight agent_metadata** | Todas | session_id, elapsed registrados |
| 6.4 | **Entity types válidos** | Todas | Apenas: skill, client, contact, supplier, user, snapshot, routine, agent_result, agent_metadata |

---

## 🧪 FASE 7: Shared Memory / Light RAG + SBM Synthesis

### Fluxo

```
Agent → executar_rag_cliente (MCP tool)
  │
  ├─ Resolve client_id + document_ids
  ├─ Valida tier (is_tool_accessible_by_tier)
  │
  └─ create_rag_retriever(blu_context, document_ids):
      ├─ QueryPreprocessor: expande query com sinônimos pt-br
      ├─ HybridRetriever:
      │   ├─ Chama search-documents EF
      │   ├─ EF: embed query (Cohere) → vector match (cosine IP, halfvec)
      │   ├─ OU: hybrid_match_documents() RPC (RRF fusion: vector + FTS)
      │   └─ Retorna chunks + scores
      ├─ CohereReranker (opcional): re-rank com Cohere Rerank API
      ├─ MMRDiversifier (opcional): diversifica resultados
      └─ Formata contexto → [Fonte: X | Relevância: 85% | Escopo: client]


SBM → LightRAG Synthesis (job semanal, T4.1)
  │
  ├─ Lê SBM (curated=true, expires_at IS NULL)
  ├─ Agrupa por (entity_type, entity_name)
  ├─ Gera Markdown synthesis por template de entity_type
  ├─ Insere em LightRAG via ainsert_custom_kg()
  └─ Atualiza knowledge_graph_summary (T4.3)
```

### O que testar

| # | Teste | Persona | Pergunta / Ação | O que verificar |
|---|---|---|---|---|
| 7.1 | **Busca por fornecedor** | Lúcia | "Qual fornecedor de camarão tem melhor qualidade?" | Mercearia do Porto; word_cloud "camarão, frutos do mar" |
| 7.2 | **Busca por cliente com atraso** | Carolina | "Quem são os clientes que mais atrasam?" | Padaria Vitória; menção a "atraso" no texto |
| 7.3 | **Busca por contrato antigo** | NovaTech | "Quando começou o contrato com AutoPeças Lima?" | 2019; R$ 2.500/mês |
| 7.4 | **Busca por evento específico** | Lúcia | "O que aconteceu no casamento Silva & Costa?" | Prejuízo; só 130 convidados |
| 7.5 | **Busca por tema** | NovaTech | "Projeto de migração para nuvem" | R$ 45.000; Construtora Novo Norte; theme=operational_procedures |
| 7.6 | **Busca cross-persona** | Sistema | "Quem fez o logo da NovaTech?" | Verificar se scope permite busca cross-client |
| 7.7 | **Documento ruído NÃO retorna** | Lúcia | "Lista de convidados" | Documento existe mas não deve gerar KPI financeiro |
| 7.8 | **SBM → LightRAG synthesis** | Carolina | SBM facts viram LightRAG | Markdown gerado por template; inserido via ainsert_custom_kg() |
| 7.9 | **Reranker melhora resultados** | NovaTech | Comparar top-5 com e sem reranker | Precisão (relevance@5) maior com reranker |
| 7.10 | **MMR diversifica resultados** | Lúcia | Múltiplos chunks do mesmo documento | MMR reduz redundância; chunks de documentos diferentes aparecem |

---

## 📊 MATRIZ COMPLETA DE TESTES

| Fase | Descrição | Testes | Personas envolvidas |
|---|---|---|---|
| 1 | NF Spreadsheets via Onboarding | 8 | Carolina, Lúcia, NovaTech |
| 2 | BigQuery Connector | 4 | NovaTech |
| 3 | Bank Statements (CSV) | 4 | Carolina, Lúcia, NovaTech |
| 4 | Document Upload (process-document) | 17 | Carolina, Lúcia, NovaTech |
| 5 | Polp / Open Finance | 4 | Todos |
| 6 | Onboarding Shared Memory Hook | 4 | Todos |
| 7 | Shared Memory / Light RAG + SBM | 10 | Todos |
| | **Total** | **51** | |

---

## 🔄 Execução Recomendada

### Ordem sugerida

1. **Fase 1** (NFs) → **Fase 3** (extratos) → **Fase 4** (documentos) → **Fase 6** (RAG)
2. **Fase 2** e **Fase 5** requerem APIs externas — testar separadamente com mock

### Setup inicial

```bash
# 1. Gerar dados
cd /home/ec2-user/repo_platform
python test-data/generate_persona_data.py
python test-data/generate_rich_documents.py

# 2. Verificar estrutura
find test-data/personas -type f | wc -l  # deve mostrar 59
```

### Para cada teste

Para cada caso, documentar:
1. **Arquivo de entrada** (path exato)
2. **Endpoint/EF** chamado
3. **Payload** enviado
4. **Resposta esperada** (status, campos)
5. **Resposta real** (capturar log)
6. **Verificação no DB** (SQL query + resultado)
7. **Aprovado/Reprovado** + observações

---

## 🐛 Roteiro de Bugs Potenciais (Edge Cases)

| # | Situação | Risco | Mitigação |
|---|---|---|---|
| E.1 | CSV com `;` vs `,` | Detecção falhar | `parseSpreadsheetHeaders` testa ambos |
| E.2 | XLSX com múltiplas abas | Aba errada selecionada | Score por keyword + row count |
| E.3 | PDF com só imagem (scan sem OCR) | `pdf-parse` retorna vazio | Erro 422 + hint sobre OCR |
| E.4 | PDF de DANFE muito grande | Timeout do Edge Function | Verificar timeout de 60s |
| E.5 | Chunk único > 500 tokens | Embedding truncado | Algoritmo quebra por sentença |
| E.6 | LLM de metadata fora do ar | Chunk sem enrichment | Non-fatal; `enrichedMetadata[i] = null` |
| E.7 | Nome de cliente inconsistente | Dim não encontra match | "Ana" vs "Ana Clara Barbosa" — testar fuzzy |
| E.8 | CPF/CNPJ com formatação variada | 384.029.170-50 vs 38402917050 | Normalizar dígitos |
| E.9 | Cross-persona: contrato Carolina-Lúcia | Documento aparece no cliente errado | Verificar `client_id` no chunk |
| E.10 | ON CONFLICT em re-upload | Dupĺicação silenciosa | content_hash SHA-256 |
