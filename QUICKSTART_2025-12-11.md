# 🚀 Quick Start - Atividades do Dia

Esse arquivo é seu companheiro prático. Marque os itens conforme progride!

---

## 1️⃣ FRONT NA IMAGEM DOCKER

### Status: ⏳ Não iniciado

```bash
# Próximo passo imediato:
cd /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard

# 1. Verificar package.json
cat package.json | grep -A10 '"scripts"'

# 2. Verificar se Dockerfile já existe
ls -la | grep -i docker

# 3. Verificar pasta de output do build
ls -la dist/ || echo "Pasta dist não existe"
```

### Checklist de Implementação
- [ ] Investigar estrutura do projeto (package.json, build output)
- [ ] Criar Dockerfile multi-stage
- [ ] Criar nginx.conf para SPA
- [ ] Adicionar ao docker-compose.yml
- [ ] Testar build: `docker build -t vizu-dashboard .`
- [ ] Testar run: `docker run -p 3000:80 vizu-dashboard`
- [ ] Integrar ao docker-compose: `docker compose up vizu_dashboard`
- [ ] Verificar em http://localhost:3000
- [ ] Documentar no README

**Saída esperada:**
```
✓ Frontend acessível em localhost:3000
✓ Rotas funcionam sem 404
✓ APIs conseguem chamar backend em http://atendente_core:8001
✓ Build é rápido e eficiente
```

---

## 2️⃣ ANALYTICS API - GRÁFICOS & INDICADORES

### Status: ⏳ Não iniciado

```bash
# Próximo passo imediato:
cd /Users/tarsobarreto/Documents/vizu-mono/services/analytics_api

# 1. Explorar estrutura
find src -type f -name "*.py" | head -20

# 2. Listar endpoints existentes
grep -r "@router\|@app" src --include="*.py" | grep "post\|get\|put"

# 3. Verificar se Redis já está integrado
grep -r "redis\|cache" src --include="*.py"
```

### Checklist de Implementação
- [ ] Investigar endpoints atuais
- [ ] Criar models/indicators.py com dataclasses
- [ ] Criar services/cache_service.py para Redis
- [ ] Criar services/aggregation_service.py (daily/weekly/monthly)
- [ ] Expandir analytics_routes.py com novos endpoints
- [ ] Implementar cálculos:
  - [ ] Growth rate (% vs período anterior)
  - [ ] Conversion rates
  - [ ] Bestsellers
  - [ ] Low stock alerts
  - [ ] Customer lifetime value
- [ ] Adicionar testes unitários
- [ ] Documentar schema de resposta

**Saída esperada:**
```bash
# Request
curl -X POST http://localhost:8002/analytics/indicators \
  -H "Content-Type: application/json" \
  -d '{
    "period": "today",
    "metrics": ["orders", "products", "customers"]
  }'

# Response (200 OK)
{
  "orders": {
    "total": 42,
    "revenue": 15000.50,
    "growth": 12.5,
    "by_status": {...}
  },
  "products": {...},
  "customers": {...},
  "cached": false,
  "generated_at": "2025-12-11T..."
}

# Segunda request é mais rápida (cached)
```

---

## 3️⃣ TEXT-TO-SQL NA TELA DE CHAT

### Status: ⏳ Não iniciado

```bash
# Próximo passo imediato:

# 1. Verificar se Text-to-SQL já existe no tool_pool_api
find /Users/tarsobarreto/Documents/vizu-mono/services/tool_pool_api \
  -type f -name "*.py" | xargs grep -l "text.*sql\|sql.*text" 2>/dev/null

# 2. Verificar atendente_core graph structure
cat /Users/tarsobarreto/Documents/vizu-mono/services/atendente_core/src/atendente_core/core/graph.py | head -50

# 3. Verificar ChatInterface no frontend
cat /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/components/ChatInterface.tsx 2>/dev/null | head -50
```

### Checklist de Implementação

**Backend (tool_pool_api):**
- [ ] Criar ou verificar services/text_to_sql_service.py
- [ ] Implementar:
  - [ ] Parsing de pergunta natural
  - [ ] Geração de SQL via LLM
  - [ ] Validação de query (security)
  - [ ] Execução no banco
  - [ ] Formatação de resposta
- [ ] Adicionar ferramenta ao MCP registry

**Backend (atendente_core):**
- [ ] Adicionar nó text_to_sql ao grafo
- [ ] Criar conditional logic para detectar perguntas SQL
- [ ] Integrar ferramenta ao tool pool
- [ ] Testar fluxo com `make chat`

**Frontend:**
- [ ] Adicionar botão toggle "Chat Normal" / "Consulta SQL"
- [ ] Adicionar indicador visual para modo SQL
- [ ] Modificar chatService para enviar `mode` flag
- [ ] Renderizar resultados em tabela se for SQL
- [ ] Mostrar SQL gerado para referência

**Testes:**
- [ ] [ ] E2E: "Quais produtos têm estoque baixo?"
- [ ] [ ] E2E: "Top 5 clientes por volume gasto"
- [ ] [ ] Security: Tentar DROP/DELETE (deve falhar)
- [ ] [ ] Performance: Query com muitos dados retorna em < 5s

**Saída esperada:**
```
User: "Mostre meus 10 produtos mais vendidos"

System:
├─ Detecta: Modo SQL
├─ Gera: SELECT p.*, COUNT(oi.id) as vendas 
│        FROM products p
│        LEFT JOIN order_items oi ON p.id = oi.product_id
│        GROUP BY p.id
│        ORDER BY vendas DESC LIMIT 10
├─ Executa: ✓
├─ Retorna: Tabela com 10 linhas
└─ Mostra: "SQL gerado (expandir/copiar)"
```

---

## 📊 Quadro de Controle

```
┌─────────────────────────────────────────────────────────┐
│  ATIVIDADE                STATUS    ESFORÇO  PRIORIDADE  │
├─────────────────────────────────────────────────────────┤
│  1. Front Docker          ⏳         2-3h     🟡 Média   │
│  2. Analytics Melhorias   ⏳         3-4h     🟢 Alta    │
│  3. Text-to-SQL Chat      ⏳         3-4h     🟢 Alta    │
├─────────────────────────────────────────────────────────┤
│  TOTAL                                8-11h            │
└─────────────────────────────────────────────────────────┘

Legenda:
⏳ = Não iniciado
🔄 = Em progresso
✅ = Completo

Prioridade:
🟢 = Alta (fazer primeiro)
🟡 = Média
🔴 = Baixa
```

---

## 🔍 Troubleshooting Rápido

### Problema: "Docker build falha no frontend"
**Solução:**
```bash
# 1. Verificar node version no Dockerfile
node --version
# Se < 18, usar node:20-alpine

# 2. Limpar cache
docker system prune -a

# 3. Rebuild
docker build --no-cache -t vizu-dashboard .
```

### Problema: "Analytics API lenta"
**Solução:**
```bash
# 1. Verificar conexão Redis
redis-cli ping
# Deve retornar: PONG

# 2. Adicionar cache decorator
@cache(ttl=300)  # 5 minutos
async def get_indicators():
    ...

# 3. Usar índices no banco
CREATE INDEX idx_orders_date ON orders(created_at);
```

### Problema: "Text-to-SQL não encontra ferramenta"
**Solução:**
```bash
# 1. Verificar ferramenta está registrada no tool_pool_api
curl http://localhost:8005/tools
# Deve incluir: text_to_sql

# 2. Verificar atendente_core consegue acessar
curl http://localhost:8001/tools
# Deve listar: text_to_sql

# 3. Testar diretamente
curl -X POST http://localhost:8005/execute_tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "text_to_sql",
    "input": "Quantos pedidos temos hoje?"
  }'
```

---

## 📝 Padrão de Commit

Quando completar cada atividade:

```bash
# Atividade 1:
git commit -m "feat(frontend): Dockerfile para dashboard SPA

- Multi-stage build com Node + Nginx
- nginx.conf com fallback para react-router
- Serviço integrado ao docker-compose.yml
- Testes E2E validados

Closes #XXX"

# Atividade 2:
git commit -m "feat(analytics): Novos indicadores e caching

- Indicadores: growth_rate, conversion, lifetime_value
- Cache Redis com TTL configurável
- Agregações por período (daily/weekly/monthly)
- +5 novos endpoints

Closes #XXX"

# Atividade 3:
git commit -m "feat(chat): Integrar Text-to-SQL ao atendente

- Nó text_to_sql no grafo LangGraph
- Query validation (security)
- Frontend: toggle entre Chat Normal / SQL
- E2E tests com validação de segurança

Closes #XXX"
```

---

## ✨ Próximas Etapas Após Completar

1. **Deployment**: Push para staging/production
2. **Testes**: Rodar suite de testes completa
3. **Monitoring**: Verificar Langfuse/Observability
4. **Docs**: Atualizar API documentation
5. **Code Review**: Submeter PRs para revisão

---

## 🎯 Dica de Ouro

> **Comece pela atividade que você acha mais fácil!**
> 
> Isso te dá momentum e confiança para as outras.
> Se começar pela mais difícil (Text-to-SQL), pode ficar travado.
>
> Sugestão: **1 → 2 → 3** (Front → Analytics → SQL)

---

Boa sorte! Você vai arrasar! 🔥
