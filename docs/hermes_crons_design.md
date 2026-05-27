# Hermes Crons — Design (WIP)

> Documento de iteração. Ainda não implementado. Atualizar conforme decisões evoluem.
> Criado: 2026-05-27

---

## Cron 1 — `blu-agent-validator`

**Objetivo:** testar um agente por vez, em ciclo rotativo, reportando saúde no Telegram.

**Frequência:** 3x/dia (08h, 13h, 18h) — cobre todos os 15 agentes em ~5 dias por ciclo.

**Mecânica:**
- Mantém estado em `~/.hermes/blu_agent_cycle.json` (índice do agente atual)
- A cada execução: lê índice → testa agente → avança índice → salva
- Com 3x/dia e 15 agentes: ciclo completo em 5 dias → cada agente testado 2x em 10 dias

**Ordem dos agentes:**
```
frontdesk → clientes → compras → financeiro → agenda →
estrategia → documentos → synthesis → data-analyst →
platform → context-gatherer → supplier-agent → crm →
scheduler-agent → doc-writer
```

**O que verifica por agente:**
1. Posta query de teste padrão para aquele agente via agent_api
2. Avalia resposta: tem conteúdo? dados reais? sem alucinação?
3. Reporta no Telegram: ✅ passou / ⚠️ resposta vazia / ❌ erro de API

**Pendente:** confirmar rota de chat do agent_api + URL base.

---

## Cron 2 — `blu-db-guardian`

**Objetivo:** data quality e saúde operacional do banco.

**Frequência:** a definir (sugestão: 1x/dia às 06h)

**4 dimensões de verificação:**

### a) Integridade referencial
- Transações sem `client_id` válido
- Registros em tabelas fato sem dimensão correspondente
- `approval_requests` presas há mais de X horas

### b) Saúde dos dados de negócio
- `dim_clientes` com clientes sem nenhuma transação (fantasmas)
- `fact_transactions` com valores negativos suspeitos
- Estoque zerado sem alerta gerado
- Metas sem progresso registrado há +7 dias

### c) Operacional / infra
- Tabelas com crescimento anormal (possível loop de inserção)
- `client_routine_executions` acumulando `failed` sem resolução
- pgvector embeddings pendentes (documentos sem embedding gerado)
- Migrations pendentes / schema drift

### d) Imagens e assets
- Documentos upados sem OCR processado
- `uploaded_files_metadata` com status `pending` há +1h
- Coleta de logos/imagens de fornecedores (Polp/merchant logo_url — gap INF-04)

**Pendente:** definir prioridade entre dimensões. Sugestão: começar por (c) + (a), depois (b) e (d).

---

## Cron 3 — `blu-routine-monitor`

**Objetivo:** detectar rotinas quebradas, lentas ou presas.

**Frequência:** a definir (sugestão: a cada 30min em horário comercial)

**O que verifica:**
- `client_routine_executions` com `status = 'failed'` — reporta slug + erro
- Execuções lentas (running há +10 min)
- Rotinas que **deveriam ter rodado** mas não rodaram (cron_expression × último executed_at)
- `approval_requests` HITL sem resposta há +24h
- Breakdown por cliente (não só por rotina)

**Pendente:** definir threshold de latência aceitável por tipo de rotina.

---

## Próximos passos

- [ ] Confirmar rota de chat do agent_api para o validator
- [ ] Definir prioridade das dimensões do db-guardian
- [ ] Definir thresholds do routine-monitor
- [ ] Implementar os 3 crons após validação manual dos agentes MVP
