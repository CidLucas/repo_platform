# 📋 Plano de Trabalho - 11 de Dezembro de 2025

## 🎯 Objetivos da Sprint

1. **[FRONT]** Executar frontend na imagem Docker da dashboard
2. **[ANALYTICS]** Melhorar gráficos e indicadores da Analytics API
3. **[CHAT]** Conectar atendente_core com Text-to-SQL na tela de chat

---

## 📌 ATIVIDADE 1: Front na Imagem Docker

### 📝 Contexto
- Dashboard frontend está em `/apps/vizu_dashboard`
- Atualmente desenvolvimento é local (npm/yarn)
- Objetivo: Containerizar e testar na orquestração Docker Compose

### 🎯 Objetivos Específicos
- [ ] Criar Dockerfile multi-stage para o frontend
- [ ] Configurar nginx para servir SPA (Single Page App) com fallback
- [ ] Adicionar serviço no docker-compose.yml
- [ ] Testar routing e hot-reload
- [ ] Documentar no README

### 📂 Arquivos a Alterar/Criar
```
apps/vizu_dashboard/
├── Dockerfile               # CRIAR - multi-stage build
├── docker-compose.override.yml  # CRIAR - override com volumes para dev
├── nginx.conf              # CRIAR - config nginx para SPA
└── README.md              # EDITAR - adicionar instruções Docker
```

### 🛠️ Passos Técnicos

**Passo 1: Investigar estrutura do frontend**
```bash
# Verificar tipo de build
cd /apps/vizu_dashboard
cat package.json | grep -A5 '"scripts"'
# Procurar por: build, dev, start
```

**Passo 2: Criar Dockerfile multi-stage**
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

# Stage 2: Runtime (nginx)
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Passo 3: Criar nginx.conf com SPA fallback**
```nginx
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    # Proxy para APIs
    location /api {
        proxy_pass http://atendente_core:8001;
    }
}
```

**Passo 4: Adicionar ao docker-compose.yml**
```yaml
vizu_dashboard:
  build:
    context: ./apps/vizu_dashboard
  ports:
    - "3000:80"
  depends_on:
    - atendente_core
  environment:
    VITE_API_URL: http://atendente_core:8001
```

### ✅ Entregáveis
- [ ] Dockerfile funcional
- [ ] nginx.conf com fallback para SPA
- [ ] Serviço no docker-compose.yml
- [ ] `docker compose up` funciona e frontend acessível em localhost:3000
- [ ] README.md com instruções

### 🧪 Validação
```bash
docker compose up vizu_dashboard
# Acessar http://localhost:3000
# Verificar DevTools: status 200 para static assets
# Testar navegação entre rotas
```

---

## 📊 ATIVIDADE 2: Melhorar Analytics API

### 📝 Contexto
- Serviço: `/services/analytics_api`
- Objetivo: Gráficos e indicadores mais ricos para dashboard

### 🎯 Objetivos Específicos
- [ ] Revisar endpoints de analytics atual
- [ ] Adicionar novos indicadores (growth rate, conversion, etc.)
- [ ] Implementar agregações por período (daily, weekly, monthly)
- [ ] Criar cache Redis para queries pesadas
- [ ] Documentar schema de resposta

### 📂 Arquivos a Alterar/Criar
```
services/analytics_api/src/analytics_api/
├── models/
│   ├── metrics.py          # CRIAR - Dataclasses para métricas
│   └── indicators.py       # CRIAR - Indicadores calculados
├── services/
│   ├── analytics_service.py     # EDITAR - Expandir cálculos
│   ├── cache_service.py    # CRIAR - Cache Redis
│   └── aggregation_service.py   # CRIAR - Agregações por período
└── api/
    └── analytics_routes.py  # EDITAR - Novos endpoints
```

### 🛠️ Passos Técnicos

**Passo 1: Revisar Analytics API atual**
```bash
cd /services/analytics_api
find src -name "*.py" | head -20
# Verificar estrutura e endpoints existentes
```

**Passo 2: Definir indicadores principais**
```python
# models/indicators.py
@dataclass
class OrderMetrics:
    total_orders: int
    total_revenue: float
    avg_order_value: float
    orders_today: int
    orders_growth: float  # % vs dia anterior

@dataclass
class ProductMetrics:
    total_products: int
    active_products: int
    bestsellers: List[ProductInfo]
    low_stock_alerts: List[str]

@dataclass
class CustomerMetrics:
    total_customers: int
    new_customers_today: int
    repeat_rate: float
    churn_rate: float
    avg_customer_lifetime_value: float
```

**Passo 3: Implementar cache Redis**
```python
# services/cache_service.py
class AnalyticsCache:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_or_compute(self, key: str, ttl: int, compute_fn):
        """Padrão cache-aside"""
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        result = await compute_fn()
        await self.redis.setex(key, ttl, json.dumps(result))
        return result
```

**Passo 4: Novos endpoints**
```python
# POST /analytics/indicators
{
    "period": "today|week|month",
    "metrics": ["orders", "products", "customers"]
}

# Response
{
    "orders": {
        "total": 42,
        "revenue": 15000,
        "growth": 12.5,
        "by_status": {...}
    },
    "products": {...},
    "customers": {...}
}
```

### ✅ Entregáveis
- [ ] 5+ novos indicadores implementados
- [ ] Cache Redis funcionando
- [ ] Endpoints com filtro por período
- [ ] Documentação de schema
- [ ] Testes unitários

### 🧪 Validação
```bash
# Verificar novo endpoint
curl -X POST http://localhost:8002/analytics/indicators \
  -H "Content-Type: application/json" \
  -d '{"period": "today", "metrics": ["orders"]}'

# Verificar cache hit no segundo request
# time curl ... (mais rápido no segundo)
```

---

## 💬 ATIVIDADE 3: Conectar Text-to-SQL na Tela de Chat

### 📝 Contexto
- `atendente_core` já orquestra o chat com LangGraph
- `tool_pool_api` tem ferramenta de Text-to-SQL
- Objetivo: User digita pergunta em SQL natural → executa query → retorna dados no chat

### 🎯 Objetivos Específicos
- [ ] Verificar integração Text-to-SQL no tool_pool_api
- [ ] Adicionar ferramenta ao grafo do atendente_core
- [ ] Frontend: adicionar modo "SQL" na interface de chat
- [ ] Testar fluxo end-to-end

### 📂 Arquivos a Alterar/Criar
```
services/atendente_core/src/atendente_core/
├── core/
│   ├── nodes.py            # EDITAR - Adicionar nó para Text-to-SQL
│   └── graph.py            # EDITAR - Conectar ferramenta ao grafo
└── tools/
    └── text_to_sql_tool.py # CRIAR - Wrapper para ferramenta

services/tool_pool_api/src/tool_pool_api/
├── server/
│   └── tool_modules/
│       └── text_to_sql.py  # VERIFICAR/EDITAR - Existente?

apps/vizu_dashboard/src/
├── components/
│   └── ChatInterface.tsx   # EDITAR - Adicionar botão "Query"
└── services/
    └── chatService.ts      # EDITAR - Suportar modo SQL
```

### 🛠️ Passos Técnicos

**Passo 1: Auditar Text-to-SQL no tool_pool_api**
```bash
# Verificar se existe
find services/tool_pool_api -type f -name "*.py" | xargs grep -l "text_to_sql\|sql"

# Se não existe, criar:
# - Usar biblioteca: sqlalchemy + llm para gerar SQL
# - Validar query (sem DROP, DELETE, etc.)
# - Executar contra banco e retornar resultados
```

**Passo 2: Adicionar ferramenta ao atendente_core**
```python
# core/graph.py
def create_graph():
    graph = StateGraph(AgentState)
    
    # Nós existentes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    
    # Novo nó para Text-to-SQL
    graph.add_node("text_to_sql", text_to_sql_node)
    
    # Condicional: se user pergunta sobre dados
    # → redirect para text_to_sql_node
    # → execute → retorna para agent
    
    return graph.compile()

# core/nodes.py
async def text_to_sql_node(state: AgentState):
    """Nó que interpreta pergunta em SQL e executa"""
    user_message = state["messages"][-1].content
    
    # 1. LLM gera SQL baseado na pergunta
    sql = await llm.invoke(f"Gere SQL para: {user_message}")
    
    # 2. Valida SQL
    if not is_safe_query(sql):
        return {"error": "Query não permitida"}
    
    # 3. Executa
    results = await db.execute(sql)
    
    # 4. Formata resposta
    return {
        "messages": [...],
        "sql_query": sql,
        "results": results
    }
```

**Passo 3: Frontend - adicionar modo SQL**
```tsx
// ChatInterface.tsx
const [chatMode, setChatMode] = useState<'normal' | 'sql'>('normal');

<Box mb={4}>
  <ButtonGroup>
    <Button
      isActive={chatMode === 'normal'}
      onClick={() => setChatMode('normal')}
    >
      💬 Chat Normal
    </Button>
    <Button
      isActive={chatMode === 'sql'}
      onClick={() => setChatMode('sql')}
    >
      📊 Consulta SQL
    </Button>
  </ButtonGroup>
</Box>

{chatMode === 'sql' && (
  <Box bg="gray.100" p={3} borderRadius="md" mb={4}>
    <Text fontSize="sm" color="gray.600">
      Pergunta em linguagem natural será convertida para SQL
    </Text>
  </Box>
)}
```

**Passo 4: ChatService - suportar modo SQL**
```ts
// chatService.ts
export async function sendMessage(
  message: string,
  mode: 'normal' | 'sql' = 'normal'
) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      metadata: {
        mode,
        timestamp: new Date().toISOString()
      }
    })
  });
  
  const data = await response.json();
  
  // Se SQL mode, renderiza tabela de resultados
  if (mode === 'sql' && data.sql_query) {
    return {
      ...data,
      type: 'sql_result',
      sqlQuery: data.sql_query
    };
  }
  
  return data;
}
```

### ✅ Entregáveis
- [ ] Text-to-SQL integrado no tool_pool_api
- [ ] Nó Text-to-SQL no grafo do atendente_core
- [ ] Frontend com opção de modo SQL
- [ ] Validação de queries (security)
- [ ] Testes E2E

### 🧪 Validação
```bash
# Teste 1: Chat normal
make chat
# Digitar: "Quais são meus produtos mais vendidos?"

# Teste 2: Chat SQL (se interface implementada)
# Digitar: "Mostre top 10 produtos por revenue"
# Verificar se retorna tabela de resultados

# Teste 3: Security
# Tentar: "DROP TABLE customers" (deve rejeitar)
```

---

## 📅 Cronograma Estimado

| Atividade | Duração | Prioridade |
|-----------|---------|-----------|
| 1. Front Docker | 2-3h | 🟡 Média |
| 2. Analytics | 3-4h | 🟢 Alta |
| 3. Text-to-SQL | 3-4h | 🟢 Alta |

**Total: 8-11 horas de desenvolvimento**

---

## 🔄 Fluxo de Trabalho

### Para cada atividade:

1. **Investigar** - Entender código atual
2. **Planejar** - Definir mudanças (isso já foi feito!)
3. **Implementar** - Código novo
4. **Testar** - Validar localmente
5. **Documentar** - README, comentários, exemplos
6. **Commit** - Git com mensagem clara

### Exemplo de commit:
```bash
git add .
git commit -m "feat(frontend): Adicionar Dockerfile para dashboard SPA

- Multi-stage build (node + nginx)
- nginx.conf com fallback para SPA routing
- Serviço integrado no docker-compose.yml
- Suporta variáveis de ambiente para API URL

Testes:
✓ docker compose up funciona
✓ localhost:3000 acessível
✓ Navegação entre rotas funciona
✓ Assets estáticos carregam corretamente"
```

---

## 🛑 Checklist Final

- [ ] Todas as 3 atividades completas
- [ ] Código testado localmente
- [ ] Documentação atualizada
- [ ] Commits push para origin/main
- [ ] README.md refletindo novo estado
- [ ] Docker Compose funciona: `docker compose up --build`
- [ ] Todos os serviços saudáveis (health checks)

---

## 📞 Dúvidas? Próximas Etapas?

Se precisar de ajuda em qualquer atividade:
- Ping no Copilot com a atividade específica
- Vou detalhar ainda mais se necessário
- Posso gerar scaffolds de código prontos

**Vamos lá! 🚀**
