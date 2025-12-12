# 💻 Code Snippets Prontos - Copy/Paste

Código pronto para copiar e colar em cada atividade!

---

## 1️⃣ FRONTEND DOCKER - Snippets

### Dockerfile (apps/vizu_dashboard/Dockerfile)

```dockerfile
# COPIE ISSO:

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy source code
COPY . .

# Build for production
RUN yarn build

# Stage 2: Runtime
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

### nginx.conf (apps/vizu_dashboard/nginx.conf)

```nginx
# COPIE ISSO:

server {
    listen 80;
    server_name _;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css text/javascript application/javascript application/json;
    gzip_min_length 1000;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        root /usr/share/nginx/html;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # SPA routing
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # API proxy
    location /api/ {
        proxy_pass http://atendente_core:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### docker-compose.yml - Adicione este serviço

```yaml
# ADICIONE NA SEÇÃO 'services:':

  vizu_dashboard:
    build:
      context: ./apps/vizu_dashboard
      dockerfile: Dockerfile
    container_name: vizu_dashboard
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE_URL=http://atendente_core:8001
    depends_on:
      - atendente_core
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - vizu_network
    restart: unless-stopped
```

### Comandos para testar

```bash
# Build da imagem
cd /apps/vizu_dashboard
docker build -t vizu-dashboard:latest .

# Run local
docker run -p 3000:80 vizu-dashboard:latest

# Com docker-compose
docker compose up vizu_dashboard

# Verificar logs
docker compose logs -f vizu_dashboard

# Testar endpoint
curl http://localhost:3000
# Deve retornar HTML da SPA

curl http://localhost:3000/health
# Deve retornar: healthy
```

---

## 2️⃣ ANALYTICS API - Snippets

### models/indicators.py (CRIAR)

```python
# COPIE ISSO:

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class PeriodType(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

@dataclass
class OrderMetrics:
    """Métricas de pedidos"""
    total_orders: int
    total_revenue: float
    avg_order_value: float
    orders_today: int
    growth_rate: float  # % vs período anterior
    by_status: Dict[str, int] = field(default_factory=dict)
    by_payment_method: Dict[str, int] = field(default_factory=dict)
    top_orders: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ProductMetrics:
    """Métricas de produtos"""
    total_products: int
    active_products: int
    bestsellers: List[Dict[str, Any]]  # [{"id": 1, "name": "...", "sold": 100}, ...]
    low_stock_alerts: List[str]  # SKUs em alerta
    inventory_turnover: float  # vezes/período
    avg_inventory_value: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CustomerMetrics:
    """Métricas de clientes"""
    total_customers: int
    new_customers_today: int
    repeat_rate: float  # %
    churn_rate: float  # %
    avg_customer_lifetime_value: float
    avg_order_frequency: float  # orders/customer/month
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AnalyticsResponse:
    """Response completo de analytics"""
    period: str
    orders: Optional[OrderMetrics] = None
    products: Optional[ProductMetrics] = None
    customers: Optional[CustomerMetrics] = None
    cached: bool = False
    ttl: Optional[int] = None  # segundos até expirar cache
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "orders": self.orders.to_dict() if self.orders else None,
            "products": self.products.to_dict() if self.products else None,
            "customers": self.customers.to_dict() if self.customers else None,
            "cached": self.cached,
            "ttl": self.ttl,
            "generated_at": self.generated_at,
        }
```

### services/cache_service.py (CRIAR)

```python
# COPIE ISSO:

import json
import logging
from typing import Any, Callable, Optional
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class AnalyticsCache:
    """Cache service com padrão cache-aside"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def get_or_compute(
        self,
        key: str,
        ttl: int,
        compute_fn: Callable,
        force_refresh: bool = False
    ) -> tuple[Any, bool]:
        """
        Padrão cache-aside (look-aside)
        
        Returns:
            (value, was_cached)
        """
        # Se force_refresh, pula cache
        if not force_refresh:
            cached = await self.redis.get(key)
            if cached:
                logger.info(f"Cache HIT: {key}")
                return json.loads(cached), True
        
        # Cache miss ou force_refresh
        logger.info(f"Cache MISS: {key}")
        result = await compute_fn()
        
        # Salva no cache
        await self.redis.setex(
            key,
            ttl,
            json.dumps(result, default=str)  # default=str para datetime
        )
        
        return result, False
    
    async def invalidate(self, key: str) -> bool:
        """Invalida cache"""
        deleted = await self.redis.delete(key)
        if deleted:
            logger.info(f"Cache invalidated: {key}")
        return bool(deleted)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalida múltiplas chaves por padrão"""
        keys = await self.redis.keys(pattern)
        if keys:
            count = await self.redis.delete(*keys)
            logger.info(f"Cache invalidated ({count} keys): {pattern}")
            return count
        return 0

# Instância global
# Usar: cache_service = AnalyticsCache(redis_client)
```

### services/aggregation_service.py (CRIAR)

```python
# COPIE ISSO:

from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession

class AggregationService:
    """Serviço de agregações por período"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_order_metrics(self, period: str) -> Dict[str, Any]:
        """Calcula métricas de pedidos para um período"""
        
        # Determine date range
        now = datetime.utcnow()
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "week":
            start = now - timedelta(days=now.weekday())
            end = now
        elif period == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        else:
            raise ValueError(f"Invalid period: {period}")
        
        # SQL para métricas de hoje
        query = text(f"""
            SELECT
                COUNT(*) as total_orders,
                SUM(total) as total_revenue,
                AVG(total) as avg_order_value,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM orders
            WHERE created_at >= :start AND created_at < :end
        """)
        
        result = await self.db.execute(
            query,
            {"start": start, "end": end}
        )
        row = result.first()
        
        # SQL para growth rate (vs período anterior)
        prev_start = start - (end - start)
        query_prev = text(f"""
            SELECT COUNT(*) as count FROM orders
            WHERE created_at >= :start AND created_at < :end
        """)
        
        result_prev = await self.db.execute(
            query_prev,
            {"start": prev_start, "end": start}
        )
        prev_count = result_prev.scalar() or 1
        curr_count = row[0] or 1
        
        growth_rate = ((curr_count - prev_count) / prev_count) * 100 if prev_count > 0 else 0
        
        return {
            "total_orders": row[0] or 0,
            "total_revenue": float(row[1] or 0),
            "avg_order_value": float(row[2] or 0),
            "unique_customers": row[3] or 0,
            "growth_rate": round(growth_rate, 2),
        }
    
    async def get_bestsellers(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Top produtos mais vendidos"""
        
        query = text(f"""
            SELECT
                p.id,
                p.name,
                COUNT(oi.id) as sold,
                SUM(oi.quantity) as quantity,
                SUM(oi.quantity * oi.price) as revenue
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            GROUP BY p.id, p.name
            ORDER BY sold DESC
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, {"limit": limit})
        return [
            {
                "id": row[0],
                "name": row[1],
                "sold": row[2],
                "quantity": row[3],
                "revenue": float(row[4] or 0),
            }
            for row in result.fetchall()
        ]
```

### api/analytics_routes.py (ADICIONE estos endpoints)

```python
# COPIE E ADICIONE:

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
from models.indicators import AnalyticsResponse, PeriodType

router = APIRouter(prefix="/analytics", tags=["Analytics"])

class IndicatorsRequest(BaseModel):
    period: PeriodType
    metrics: List[str] = Query(["orders", "products", "customers"])
    force_refresh: bool = False

@router.post("/indicators")
async def get_indicators(
    request: IndicatorsRequest,
    analytics_service = Depends(),
    cache_service = Depends()
) -> AnalyticsResponse:
    """
    Retorna indicadores agregados para um período
    
    Exemplo:
    POST /analytics/indicators
    {
        "period": "today",
        "metrics": ["orders", "products", "customers"],
        "force_refresh": false
    }
    """
    
    cache_key = f"analytics:{request.period}:{':'.join(request.metrics)}"
    
    # Tenta cache
    result, was_cached = await cache_service.get_or_compute(
        cache_key,
        ttl=300,  # 5 minutos
        compute_fn=lambda: analytics_service.compute_indicators(
            request.period,
            request.metrics
        ),
        force_refresh=request.force_refresh
    )
    
    # Converte resultado para response
    response = AnalyticsResponse(**result)
    response.cached = was_cached
    if was_cached:
        response.ttl = await cache_service.redis.ttl(cache_key)
    
    return response
```

### Teste com curl

```bash
# Teste novo endpoint
curl -X POST http://localhost:8002/analytics/indicators \
  -H "Content-Type: application/json" \
  -d '{
    "period": "today",
    "metrics": ["orders", "products", "customers"]
  }' | jq .

# Segunda request (deve vir do cache)
curl -X POST http://localhost:8002/analytics/indicators \
  -H "Content-Type: application/json" \
  -d '{
    "period": "today",
    "metrics": ["orders"]
  }' | jq .

# Forçar refresh
curl -X POST http://localhost:8002/analytics/indicators \
  -H "Content-Type: application/json" \
  -d '{
    "period": "today",
    "metrics": ["orders"],
    "force_refresh": true
  }' | jq .
```

---

## 3️⃣ TEXT-TO-SQL CHAT - Snippets

### services/text_to_sql_service.py (CRIAR)

```python
# COPIE ISSO:

import re
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, inspect

logger = logging.getLogger(__name__)

class TextToSQLService:
    """Converte perguntas naturais em SQL seguro"""
    
    # Palavras-chave perigosas (blacklist)
    DANGEROUS_KEYWORDS = {
        "DROP", "DELETE", "TRUNCATE", "ALTER", "EXEC", "EXECUTE",
        "GRANT", "REVOKE", "INSERT INTO", "UPDATE", "CREATE",
    }
    
    # Tabelas permitidas (whitelist)
    ALLOWED_TABLES = {
        "orders", "order_items", "products", "customers",
        "inventories", "reviews", "payments", "shipments"
    }
    
    def __init__(self, db_session: AsyncSession, llm_service):
        self.db = db_session
        self.llm = llm_service
    
    def is_safe_query(self, sql: str) -> bool:
        """Valida se query é segura"""
        
        # Uppercase para comparação
        sql_upper = sql.upper()
        
        # 1. Check dangerous keywords
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in sql_upper:
                logger.warning(f"Dangerous keyword found: {keyword}")
                return False
        
        # 2. Check for multiple statements
        if ";" in sql and sql.rstrip().endswith(";"):
            # OK (SQL termina com ;)
            pass
        elif ";" in sql:
            logger.warning("Multiple SQL statements detected")
            return False
        
        # 3. Check for SQL comments
        if re.search(r"--.*$", sql, re.MULTILINE):
            logger.warning("SQL comments detected")
            return False
        
        # 4. Check table whitelist
        for table in self.ALLOWED_TABLES:
            if table.upper() in sql_upper:
                return True
        
        logger.warning("No whitelisted tables found in query")
        return False
    
    async def generate_sql(self, user_question: str) -> str:
        """Gera SQL a partir de pergunta natural"""
        
        prompt = f"""
Você é um especialista em SQL. Converta a pergunta em uma query SQL segura.

Pergunta: {user_question}

Tabelas disponíveis:
- orders (id, customer_id, created_at, total, status)
- order_items (id, order_id, product_id, quantity, price)
- products (id, name, category, price, stock_quantity)
- customers (id, email, first_name, last_name, created_at)
- inventories (id, product_id, location_id, quantity)

Regras:
1. Apenas SELECT (nada de UPDATE, DELETE, DROP)
2. Máximo 100 linhas (LIMIT 100)
3. Retorne APENAS a query SQL, nada mais
4. Use INNER JOIN para relacionamentos

SQL:
        """
        
        sql = await self.llm.invoke(prompt)
        return sql.strip()
    
    async def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Executa query segura e retorna resultados"""
        
        # Valida antes de executar
        if not self.is_safe_query(sql):
            raise ValueError("Query validation failed. Potentially dangerous SQL detected.")
        
        # Executa
        result = await self.db.execute(text(sql))
        
        # Formata resultado como lista de dicts
        rows = result.fetchall()
        columns = result.keys()
        
        return [
            {col: row[i] for i, col in enumerate(columns)}
            for row in rows
        ]
    
    async def chat_to_sql(self, user_message: str) -> Dict[str, Any]:
        """Fluxo completo: pergunta → SQL → executa → retorna"""
        
        try:
            # 1. Gera SQL
            logger.info(f"Generating SQL for: {user_message}")
            sql = await self.generate_sql(user_message)
            logger.info(f"Generated SQL: {sql}")
            
            # 2. Executa
            logger.info("Executing query...")
            results = await self.execute_query(sql)
            
            return {
                "success": True,
                "sql_query": sql,
                "results": results,
                "row_count": len(results),
            }
        
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "sql_query": sql if 'sql' in locals() else None,
            }
        except Exception as e:
            logger.error(f"Error in chat_to_sql: {e}")
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
            }
```

### core/graph.py - Adicione nó (EDITAR)

```python
# COPIE E ADICIONE AO GRAFO:

from text_to_sql_service import text_to_sql_service

async def text_to_sql_node(state: AgentState):
    """Nó para processar perguntas em SQL"""
    
    messages = state["messages"]
    user_message = messages[-1].content
    
    # Detecta se é pergunta sobre dados
    classification = await llm.invoke(f"""
    A pergunta "{user_message}" é sobre:
    A) Geral/informação (responda: general)
    B) Dados específicos do banco (responda: data_query)
    
    Responda com uma palavra: """)
    
    if classification != "data_query":
        return state
    
    # Processa como Text-to-SQL
    result = await text_to_sql_service.chat_to_sql(user_message)
    
    if result["success"]:
        # Formata resposta
        formatted_results = format_results_as_string(result["results"])
        
        # Adiciona à conversa
        response_message = HumanMessage(
            content=f"""
SQL Generated: {result['sql_query']}

Results ({result['row_count']} rows):
{formatted_results}
            """,
            metadata={"type": "sql_result"}
        )
    else:
        response_message = HumanMessage(
            content=f"Error: {result['error']}",
            metadata={"type": "sql_error"}
        )
    
    return {
        "messages": messages + [response_message],
        "sql_result": result
    }

# No graph builder:
# graph.add_node("text_to_sql", text_to_sql_node)
# graph.add_conditional_edges(
#     "agent",
#     lambda state: should_use_text_to_sql(state),
#     {
#         "text_to_sql": "text_to_sql",
#         "tools": "tools",
#     }
# )
```

### Frontend - ChatInterface.tsx (ADICIONE)

```tsx
// COPIE ISSO:

import React, { useState } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Code,
  useClipboard,
  IconButton,
} from '@chakra-ui/react';
import { CopyIcon } from '@chakra-ui/icons';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: {
    type?: 'sql_result' | 'sql_error' | 'normal';
    sqlQuery?: string;
    results?: Record<string, any>[];
  };
}

export const ChatInterface = () => {
  const [chatMode, setChatMode] = useState<'normal' | 'sql'>('normal');
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Renderiza resultado de SQL em tabela
  const renderSQLResult = (data: Record<string, any>[]) => {
    if (!data || data.length === 0) return <p>No results</p>;

    const columns = Object.keys(data[0]);

    return (
      <Box overflowX="auto" mt={4}>
        <Table size="sm" variant="striped">
          <Thead bg="gray.100">
            <Tr>
              {columns.map((col) => (
                <Th key={col} fontSize="12px">
                  {col}
                </Th>
              ))}
            </Tr>
          </Thead>
          <Tbody>
            {data.map((row, idx) => (
              <Tr key={idx}>
                {columns.map((col) => (
                  <Td key={`${idx}-${col}`} fontSize="12px">
                    {String(row[col])}
                  </Td>
                ))}
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    );
  };

  // Renderiza mensagem com SQL
  const renderMessage = (msg: ChatMessage) => {
    if (msg.metadata?.type === 'sql_result') {
      return (
        <Box bg="green.50" p={4} borderRadius="md" mt={2}>
          <Box mb={3}>
            <SqlQueryDisplay query={msg.metadata.sqlQuery || ''} />
          </Box>
          {msg.metadata.results && (
            renderSQLResult(msg.metadata.results)
          )}
        </Box>
      );
    }

    if (msg.metadata?.type === 'sql_error') {
      return (
        <Box bg="red.50" p={4} borderRadius="md" mt={2}>
          <p style={{ color: 'red' }}>{msg.content}</p>
        </Box>
      );
    }

    return <p>{msg.content}</p>;
  };

  return (
    <Box>
      {/* Mode Selector */}
      <ButtonGroup mb={4}>
        <Button
          isActive={chatMode === 'normal'}
          onClick={() => setChatMode('normal')}
          colorScheme={chatMode === 'normal' ? 'blue' : 'gray'}
        >
          💬 Chat Normal
        </Button>
        <Button
          isActive={chatMode === 'sql'}
          onClick={() => setChatMode('sql')}
          colorScheme={chatMode === 'sql' ? 'blue' : 'gray'}
        >
          📊 Consulta SQL
        </Button>
      </ButtonGroup>

      {/* Info Box */}
      {chatMode === 'sql' && (
        <Box bg="blue.50" p={3} borderRadius="md" mb={4} fontSize="sm">
          Você está no modo SQL. Faça perguntas sobre seus dados em linguagem
          natural e elas serão convertidas para SQL automaticamente.
        </Box>
      )}

      {/* Messages */}
      <Box>
        {messages.map((msg) => (
          <Box key={msg.id} mb={4} p={3} bg={msg.role === 'user' ? 'gray.100' : 'white'}>
            {renderMessage(msg)}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

// Componente auxiliar para exibir SQL
const SqlQueryDisplay = ({ query }: { query: string }) => {
  const { hasCopied, onCopy } = useClipboard(query);

  return (
    <Box bg="gray.800" color="gray.100" p={3} borderRadius="md" fontFamily="mono" fontSize="xs">
      <Box display="flex" justifyContent="space-between" alignItems="start">
        <Box flex={1} overflowX="auto" whiteSpace="pre-wrap">
          {query}
        </Box>
        <IconButton
          aria-label="Copy SQL"
          icon={<CopyIcon />}
          size="sm"
          ml={2}
          onClick={onCopy}
          variant="ghost"
          colorScheme="whiteAlpha"
        />
      </Box>
      {hasCopied && <Box fontSize="10px" color="green.300" mt={1}>Copiado!</Box>}
    </Box>
  );
};
```

### Teste com curl

```bash
# Teste Text-to-SQL
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quais são meus 5 produtos mais vendidos?",
    "mode": "sql"
  }' | jq .

# Resposta esperada:
# {
#   "response": "Os top 5 produtos são...",
#   "sql_query": "SELECT p.*, COUNT(oi.id) as vendas...",
#   "results": [
#     {"id": 1, "name": "Produto A", "vendas": 450},
#     ...
#   ]
# }
```

---

## 🔗 Quick Links para Colar

### 1. Dockerfile Frontend
- Arquivo: `apps/vizu_dashboard/Dockerfile`
- Copie o snippet "Dockerfile (apps/vizu_dashboard/Dockerfile)" acima

### 2. nginx.conf Frontend
- Arquivo: `apps/vizu_dashboard/nginx.conf`
- Copie o snippet "nginx.conf (apps/vizu_dashboard/nginx.conf)" acima

### 3. docker-compose.yml
- Local: Seção `services:`
- Copie o snippet "docker-compose.yml - Adicione este serviço" acima

### 4. Analytics Models
- Arquivo: `services/analytics_api/src/analytics_api/models/indicators.py`
- Copie o snippet "models/indicators.py"

### 5. Analytics Cache
- Arquivo: `services/analytics_api/src/analytics_api/services/cache_service.py`
- Copie o snippet "services/cache_service.py"

### 6. Text-to-SQL Service
- Arquivo: `services/tool_pool_api/src/tool_pool_api/services/text_to_sql_service.py`
- Copie o snippet "services/text_to_sql_service.py"

---

Pronto para copiar/colar! 🚀
