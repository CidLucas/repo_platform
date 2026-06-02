# Backlog — Integrações Externas & MVP Roadmap

---

## ⚠ QUASE PRONTO — Twilio WhatsApp Sandbox

**O que já foi feito:**
- Conta Twilio trial criada (Account SID: ACe0dc9a02b6db4b9ea5766007d0b49edb)
- Número US: `+136****1207` — `.env` atualizado
- Sandbox configurado com webhook; número de teste verificado: `+551****2709`
- `blu_twilio_client` e `twilio_webhook_router` existem e são funcionais ✅

**O que falta (1 passo):**
1. `tool_pool_api` expõe na porta **8003** (não 8001)
2. Recriar ngrok na porta certa: `ngrok http 8003`
3. Atualizar URL no Twilio Sandbox → "When a message comes in"
4. Testar enviando mensagem para sandbox number (`+141****8886`)

**Esforço:** 30min

---

## ⏳ PENDENTE — i18n: App Multi-idioma

**Ideia:** PT-BR, EN, ES como prioridade.

**Abordagem:** injetar `user_language` nos prompts (já fazemos `Responda sempre no idioma do usuário` nos prompts novos). Para arquitetura mais robusta: nó `response_language_node` no LangGraph.

**Quando explorar:** após estabilização dos agentes principais.

---

## ⏳ PENDENTE — NotebookLM: Bases de Conhecimento por Domínio

**Ideia:** Integrar NotebookLM para gerar bases de conhecimento especializadas por domínio (financeira, CRM). Usar summary/podcast como contexto enriquecido ou RAG alternativo ao pgvector.

**Quando explorar:** útil para onboarding de clientes com base de documentos rica.

---

## ⏳ PENDENTE — GitHub Cloud: Fluxo de Desenvolvimento Automatizado

**Ideia:** Integrar Hermes com GitHub Actions, Issues, PRs — criar issues de conversas de backlog, abrir PRs com código gerado via Codex/Claude Code, receber notificações de CI/CD, vincular Linear a commits.

---

## MVP Roadmap — Fases Pendentes

### 1. Onboarding ciclo completo (2 clientes)
- Cliente A: fonte BigQuery
- Cliente B: fonte Google Sheets
- Validar todo o fluxo de entrada de dados para cada fonte

### 2. Validação de métricas
- Pegar todas as métricas do frontend e validar geração correta de cada uma (ver `05_frontend_e_metricas.md`)

### 3. Integrações
- Monday, Slack, Google Drive, Gmail, Google Agenda, Open Finance

### 4. Mesa de trabalho da Agenda
- Hoje hardcoded/figurativa — tornar dinâmica e funcional

### Pós-MVP
- Routing semântico (embedding similarity ou classificador leve — exact match atual é frágil)
- Otimizar retrieval (chunking, metadata, estrutura da base)
- Refinamento contínuo de prompts
