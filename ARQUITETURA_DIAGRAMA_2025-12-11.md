# 🏗️ Arquitetura & Diagramas - Atividades do Dia

Visualizações técnicas para cada atividade.

---

## 1️⃣ ARQUITETURA: FRONT NA IMAGEM DOCKER

### Flow Atual (Desenvolvimento Local)
```
┌─────────────────────────────────────────────────────────┐
│  DESENVOLVIMENTO LOCAL                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  npm install → yarn dev                                 │
│        ↓                                                 │
│  Vite Dev Server                                        │
│  (localhost:5173)                                       │
│        ↓                                                 │
│  Hot Module Replacement (HMR)                           │
│  ↓                                                       │
│  Browser: localhost:5173                                │
│                                                         │
│  Problema: Não funciona no docker-compose!             │
│             Não testa imagem de produção                │
│             Dev != Prod                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Flow Novo (Docker)
```
┌─────────────────────────────────────────────────────────┐
│  MULTI-STAGE BUILD                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Stage 1: Builder                                       │
│  ┌─────────────────────────────────────┐               │
│  │ FROM node:20-alpine                 │               │
│  │ COPY package.json yarn.lock ./      │               │
│  │ RUN yarn install                    │               │
│  │ COPY . .                            │               │
│  │ RUN yarn build  →  dist/            │               │
│  └─────────────────────────────────────┘               │
│           ↓ (COPIA dist/)                               │
│                                                         │
│  Stage 2: Runtime                                       │
│  ┌─────────────────────────────────────┐               │
│  │ FROM nginx:alpine                   │               │
│  │ COPY --from=builder dist /html      │               │
│  │ COPY nginx.conf /etc/nginx/         │               │
│  │ EXPOSE 80                           │               │
│  │ CMD ["nginx"]                       │               │
│  └─────────────────────────────────────┘               │
│           ↓ (IMAGEM FINAL: ~50MB)                       │
│                                                         │
│  Docker Container (Produção)                           │
│  ┌─────────────────────────────────────┐               │
│  │  Nginx                              │               │
│  │  ├─ Serve static files (dist/)      │               │
│  │  ├─ SPA fallback (→ index.html)     │               │
│  │  ├─ Proxy /api → atendente_core    │               │
│  │  └─ Port 80                         │               │
│  └─────────────────────────────────────┘               │
│           ↓                                              │
│  Browser: localhost:3000 / http://vizu_dashboard:80    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Docker Compose Network
```
┌───────────────────────────────────────────────────────────┐
│  DOCKER COMPOSE NETWORK (bridge)                          │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  vizu_dashboard (nginx:80)                                │
│         │                                                  │
│         ├─→ /api/* → atendente_core (8001)               │
│         │   └─→ POST /chat (LangGraph)                   │
│         │                                                  │
│         └─→ /admin/* → (internal routes)                 │
│                                                           │
│  Requisições internas (container → container):           │
│  http://atendente_core:8001/api/...  ✓                   │
│                                                           │
│  Requisições do Host (localhost):                        │
│  http://localhost:3000  ✓                                │
│  http://localhost:8001  ✓                                │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### nginx.conf para SPA
```nginx
# Problema: React Router vs Nginx
#
# User clica: /dashboard/admin
# ├─ Nginx procura: /dashboard/admin.html  ✗ NÃO EXISTE
# └─ Deve servir: index.html                ✓ React toma conta

server {
    listen 80;
    
    # Assets estáticos (JS, CSS, imagens)
    # Podem ser cacheados
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        root /usr/share/nginx/html;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # SPA Fallback (CRÍTICO)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        # Explicação:
        # 1. try_files $uri       → Procura arquivo exato
        # 2. try_files ... $uri/  → Procura diretório
        # 3. try_files ... /index.html → FALLBACK (React Router)
    }
    
    # Proxy para APIs Backend
    location /api/ {
        proxy_pass http://atendente_core:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 2️⃣ ARQUITETURA: ANALYTICS API

### Fluxo de Dados Atual (sem cache)
```
┌─────────────────────────────────────────┐
│  Request: GET /analytics/orders?day=   │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────┐
│  SQL Query Pesada (múltiplas JOINs)                     │
│  ┌─────────────────────────────────────────────────────┐│
│  │ SELECT                                              ││
│  │   DATE(o.created_at) as date,                       ││
│  │   COUNT(*) as total_orders,                         ││
│  │   SUM(o.total) as revenue,                          ││
│  │   COUNT(DISTINCT o.customer_id) as unique_customers,││
│  │   AVG(o.total) as avg_order_value,                  ││
│  │   COUNT(CASE WHEN status='completed' THEN 1 END)   ││
│  │ FROM orders o                                       ││
│  │ LEFT JOIN order_items oi ON ...                     ││
│  │ LEFT JOIN customers c ON ...                        ││
│  │ WHERE o.created_at >= NOW() - INTERVAL '7 days'    ││
│  │ GROUP BY DATE(o.created_at)                         ││
│  │ ORDER BY date DESC;  ← LENTO!                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
            ↓ (5-10 segundos no primeiro request!)
┌─────────────────────────────────────────┐
│  JSON Response                          │
│  {                                      │
│    "orders": [                          │
│      {"date": "2025-12-11", ...},       │
│      ...                                │
│    ]                                    │
│  }                                      │
└─────────────────────────────────────────┘
```

### Fluxo Otimizado (com cache)
```
┌─────────────────────────────────────────┐
│  Request: GET /analytics/orders?day=   │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────┐
│  Cache Service (Redis)                                  │
│  ┌─────────────────────────────────────────────────────┐│
│  │ cache_key = f"analytics:orders:{day}"                ││
│  │ cached_value = redis.get(cache_key)                  ││
│  │                                                      ││
│  │ if cached_value:                                     ││
│  │     return cached_value  ← RÁPIDO! (<100ms)         ││
│  │ else:                                                ││
│  │     result = await db.query(...)  ← LENTO (10s)     ││
│  │     redis.setex(cache_key, 300, result)  # 5min TTL ││
│  │     return result                                    ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
            ↓
    ┌───────┴───────┐
    ↓               ↓
HIT (100ms)     MISS (10s)
└───────┬───────┘
        ↓
┌─────────────────────────────────────────┐
│  JSON Response (cached ou fresh)        │
│  {                                      │
│    "orders": [...],                     │
│    "cached": true/false,                │
│    "ttl": 234  # segundos até expirar   │
│  }                                      │
└─────────────────────────────────────────┘
```

### Indicadores Calculados
```
┌────────────────────────────────────────────────────────┐
│  ORDERS METRICS                                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Total Orders (SUM)                                    │
│  └─→ 42 pedidos hoje                                  │
│                                                        │
│  Revenue (SUM total)                                   │
│  └─→ R$ 15.000,00                                     │
│                                                        │
│  Average Order Value (AVG total)                       │
│  └─→ R$ 357,14                                        │
│                                                        │
│  GROWTH RATE (novo indicador!)                        │
│  └─→ ((hoje - ontem) / ontem) * 100                   │
│      = ((42 - 35) / 35) * 100 = 20%  ↑               │
│                                                        │
│  By Status                                            │
│  ├─→ pending: 5                                       │
│  ├─→ completed: 35                                    │
│  └─→ cancelled: 2                                     │
│                                                        │
│  By Payment Method                                    │
│  ├─→ credit_card: 28                                 │
│  ├─→ debit: 10                                        │
│  └─→ pix: 4                                           │
│                                                        │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  PRODUCTS METRICS                                      │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Total Products                                        │
│  └─→ 1.250 SKUs                                       │
│                                                        │
│  Active Products                                       │
│  └─→ 1.100 (88%)                                      │
│                                                        │
│  Bestsellers (Top 5)                                  │
│  └─→ 1. "Produto A" - 450 vendas                     │
│      2. "Produto B" - 380 vendas                     │
│      ...                                              │
│                                                        │
│  Low Stock Alerts                                     │
│  └─→ 15 produtos com qtd < 10                        │
│      ["SKU-001", "SKU-042", ...]                     │
│                                                        │
│  Inventory Turnover (novo!)                           │
│  └─→ (Units Sold / Avg Stock) / Days Period          │
│      = 2.3x/mês (quantas vezes o estoque gira)       │
│                                                        │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  CUSTOMERS METRICS                                     │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Total Customers                                       │
│  └─→ 850                                              │
│                                                        │
│  New Today                                            │
│  └─→ 12 (+1.4% vs yesterday)                          │
│                                                        │
│  Repeat Rate                                          │
│  └─→ 34% (fizeram compra > 1 vez)                    │
│                                                        │
│  Churn Rate (novo!)                                   │
│  └─→ Customers que não compraram há 90 dias          │
│      = 12%                                            │
│                                                        │
│  Lifetime Value (novo!)                               │
│  └─→ Gasto médio por customer durante vida            │
│      = R$ 2.400,00                                    │
│                                                        │
│  Last Order Distribution                              │
│  ├─→ Last 7 days: 450                                │
│  ├─→ Last 30 days: 650                               │
│  └─→ Last 90 days: 750                               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 3️⃣ ARQUITETURA: TEXT-TO-SQL NA CHAT

### Fluxo Atual (sem SQL)
```
┌─────────────────────────────────────────┐
│  User no Chat: "Quais são meus         │
│  produtos mais vendidos?"               │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────┐
│  atendente_core (LangGraph)                             │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 1. agent_node:                                      ││
│  │    - Input: User message                           ││
│  │    - LLM: "O que o user quer?"                      ││
│  │    - Output: Pensamento natural                     ││
│  │                                                     ││
│  │ 2. tools_node:                                      ││
│  │    - Usa ferramentas: RAG, Web Search, etc.        ││
│  │    - Não executa SQL diretamente                   ││
│  │                                                     ││
│  │ 3. agent_node (novamente):                          ││
│  │    - Sintetiza resultados                          ││
│  │    - Retorna resposta natural                      ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
            ↓
┌──────────────────────────────────────────┐
│  Response: "Os produtos mais vendidos    │
│  são... [resposta sem dados específicos] │
└──────────────────────────────────────────┘
```

### Fluxo Novo (com SQL)
```
┌─────────────────────────────────────────┐
│  User no Chat: "Quais são meus         │
│  produtos mais vendidos?"               │
│  [Seleciona modo: SQL 📊]               │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────┐
│  atendente_core (LangGraph - NOVO)                      │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 1. agent_node:                                      ││
│  │    - Input: User message + MODE=sql                ││
│  │    - LLM: "Isso parece uma query sobre dados"      ││
│  │    - Routing: → text_to_sql_node                   ││
│  │                                                     ││
│  │ 2. text_to_sql_node (NOVO!):                        ││
│  │    - Input: "Produtos mais vendidos"              ││
│  │    - LLM: Gera SQL                                 ││
│  │      SELECT p.*, COUNT(oi.id) as vendas           ││
│  │      FROM products p                              ││
│  │      LEFT JOIN order_items oi ON ...              ││
│  │      GROUP BY p.id                                ││
│  │      ORDER BY vendas DESC                         ││
│  │      LIMIT 10                                     ││
│  │    - Valida: ✓ Seguro (sem DROP/DELETE)          ││
│  │    - Executa: → PostgreSQL                        ││
│  │    - Resultado: [                                 ││
│  │        {"id": 1, "name": "Prod A", "vendas": 450},││
│  │        ...                                        ││
│  │      ]                                            ││
│  │                                                     ││
│  │ 3. agent_node (novamente):                          ││
│  │    - Input: Dados da query                        ││
│  │    - LLM: "Sintetiza para linguagem natural"      ││
│  │    - Output: "Os top 3 são..."                    ││
│  │                                                     ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
            ↓
┌──────────────────────────────────────────┐
│  Response com Dados Reais:               │
│  ┌──────────────────────────────────────┐│
│  │ Os produtos mais vendidos são:       ││
│  │                                      ││
│  │ SQL Gerado:                          ││
│  │ SELECT p.*, COUNT(oi.id) ...        ││
│  │ [COPIAR / EXPANDIR]                  ││
│  │                                      ││
│  │ Resultados:                          ││
│  │ ┌─────────────────────────────────┐ ││
│  │ │ id  │ name      │ category │ v.  │ ││
│  │ ├─────┼───────────┼──────────┼────┤ ││
│  │ │ 1   │ Produto A │ Eletrô.  │ 450│ ││
│  │ │ 2   │ Produto B │ Eletrô.  │ 380│ ││
│  │ │ 3   │ Produto C │ Fashion  │ 320│ ││
│  │ │ ... │ ...       │ ...      │... │ ││
│  │ └─────────────────────────────────┘ ││
│  │                                      ││
│  │ Insights:                            ││
│  │ • Crescimento: +15% vs semana pass. ││
│  │ • Categoria: Eletrônicos lidera    ││
│  │                                      ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### Graph do LangGraph (Grafo de Decisões)
```
┌────────────────────────────────────────────────────────┐
│  LangGraph State Machine                               │
├────────────────────────────────────────────────────────┤
│                                                        │
│           ┌──────────────┐                             │
│           │  User Input  │                             │
│           └──────┬───────┘                             │
│                  ↓                                      │
│           ┌──────────────────┐                         │
│           │  agent_node      │                         │
│           │ (LLM analisa)    │                         │
│           └──────┬───────────┘                         │
│                  ↓                                      │
│      ┌───────────┴────────────┐                        │
│      ↓                        ↓                         │
│  "Use Tools"        "Use Text-to-SQL"                  │
│      ↓                        ↓                         │
│  ┌────────────┐        ┌──────────────────┐            │
│  │ tools_node │        │ text_to_sql_node │            │
│  │            │        │ (LLM gera SQL)   │            │
│  │ • RAG      │        │ • Valida         │            │
│  │ • Web      │        │ • Executa        │            │
│  │ • Search   │        │ • Formata        │            │
│  └────┬───────┘        └────────┬─────────┘            │
│       ↓                         ↓                       │
│       └────────────┬────────────┘                       │
│                    ↓                                    │
│           ┌──────────────────┐                         │
│           │  agent_node      │                         │
│           │ (LLM sintetiza)  │                         │
│           └────────┬─────────┘                         │
│                    ↓                                    │
│           ┌──────────────────┐                         │
│           │  Final Response  │                         │
│           │ (Retorna ao user)│                         │
│           └──────────────────┘                         │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Security: Validação de SQL
```
┌─────────────────────────────────────────────────────────┐
│  SQL Validation Service                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input: SELECT * FROM products WHERE id=1; DROP ...   │
│            ↓                                            │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Blacklist: Palavras-chave perigosas             │ │
│  │  ├─ DROP TABLE                                    │ │
│  │  ├─ DELETE FROM                                   │ │
│  │  ├─ UPDATE                                        │ │
│  │  ├─ TRUNCATE                                      │ │
│  │  ├─ ALTER                                         │ │
│  │  ├─ EXEC / EXECUTE                                │ │
│  │  ├─ GRANT / REVOKE                                │ │
│  │  └─ ; (múltiplas queries)                         │ │
│  └───────────────────────────────────────────────────┘ │
│            ↓                                            │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Whitelist: Tabelas/Colunas permitidas           │ │
│  │  ├─ products                                      │ │
│  │  ├─ orders                                        │ │
│  │  ├─ customers                                     │ │
│  │  ├─ order_items                                   │ │
│  │  └─ inventories                                   │ │
│  └───────────────────────────────────────────────────┘ │
│            ↓                                            │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Regex Patterns: Detecta injeção SQL              │ │
│  │  ├─ /--.*$/m  (SQL comments)                      │ │
│  │  ├─ /;.*$/    (Múltiplas queries)                 │ │
│  │  ├─ /'/       (String injection)                  │ │
│  │  └─ CASE WHEN, UNION, etc.                        │ │
│  └───────────────────────────────────────────────────┘ │
│            ↓                                            │
│  Query segura? →  SIM  →  Executa ✓                   │
│            ↓                                            │
│           NÃO   →  Rejeita ✗                           │
│                    "Query contém palavras proibidas"    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔗 Integrações Entre Atividades

```
┌─────────────────────────────────────────────────────────┐
│  SINERGIA ENTRE ATIVIDADES                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  1. FRONTEND (Docker)                           │   │
│  │  └─→ Adiciona tela de analytics com gráficos    │   │
│  │      └─→ Integra com dados da atividade 2      │   │
│  │                                                 │   │
│  │  2. ANALYTICS API                               │   │
│  │  └─→ Fornece dados para dashboard              │   │
│  │  └─→ Usa Text-to-SQL (atividade 3) como fonte  │   │
│  │                                                 │   │
│  │  3. TEXT-TO-SQL                                 │   │
│  │  └─→ Alimenta Analytics com dados dinâmicos    │   │
│  │  └─→ Renderizado na interface Frontend         │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  User Flow Completo:                                    │
│                                                         │
│  1. Acessa Frontend (Docker) em localhost:3000         │
│         ↓                                                │
│  2. Seleciona modo "SQL" no chat                        │
│         ↓                                                │
│  3. Digita: "Meus top 5 produtos por revenue"          │
│         ↓                                                │
│  4. Backend (atendente_core) → Text-to-SQL             │
│         ↓                                                │
│  5. Resultado renderizado em tabela                    │
│         ↓                                                │
│  6. Dados também entram em cache da Analytics API       │
│         ↓                                                │
│  7. Dashboard mostra gráficos atualizados              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Technology Stack

### Frontend
```
Node.js 20  →  Yarn  →  Vite  →  React 18  →  TypeScript
                            ↓
                        Chakra UI (Components)
                        React Router (Routing)
                        TanStack Query (Data Fetching)
                            ↓
                    Nginx (Production)  →  Docker
```

### Backend - Analytics
```
FastAPI  →  SQLAlchemy  →  PostgreSQL
    ↓
Redis (Cache Layer)
    ↓
Pandas (Data Processing)
    ↓
Pydantic (Validation)
```

### Backend - Text-to-SQL
```
FastAPI  →  LangGraph  →  LLM (Ollama/OpenAI)
    ↓
SQL Generation  →  Validation  →  PostgreSQL
    ↓
Tool Pool (MCP Registry)  →  atendente_core
```

---

Pronto! Você tem toda a visão arquitetônica. Bora codar! 🚀
