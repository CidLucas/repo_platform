# Vizu Supabase Client

Cliente wrapper para acesso ao Supabase via SDK Python.

## Visão Geral

Esta biblioteca fornece um cliente singleton para operações com o Supabase usando a **API REST** (PostgREST), não conexão direta PostgreSQL. Isso resolve problemas de conectividade DNS e oferece uma interface mais simples.

## Configuração

Defina as seguintes variáveis de ambiente:

```env
# API URL do Supabase (não é connection string PostgreSQL!)
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co

# Service Role Key (para operações server-side que precisam de RLS bypass ou admin)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# (Opcional) Anon Key para operações com RLS ativo
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Uso

### Singleton Client

```python
from vizu_supabase_client import get_supabase_client

# Client singleton (usa service_role por padrão para operações server-side)
client = get_supabase_client()

# Consultas
response = client.table("cliente_vizu").select("*").eq("id", "uuid-here").execute()
clientes = response.data

# Inserção
response = client.table("cliente_vizu").insert({"nome_empresa": "Teste"}).execute()

# Update
response = client.table("cliente_vizu").update({"nome_empresa": "Novo Nome"}).eq("id", "uuid").execute()

# Delete
response = client.table("cliente_vizu").delete().eq("id", "uuid").execute()
```

### Chamar funções PostgreSQL (RPC)

```python
# Definir contexto RLS (antes de queries que precisam de isolamento)
client.rpc("set_current_cliente_id", {"cliente_id": "uuid-aqui"}).execute()
```

### Operações assíncronas

```python
from vizu_supabase_client import get_async_supabase_client

async def fetch_cliente(cliente_id: str):
    client = await get_async_supabase_client()
    response = await client.table("cliente_vizu").select("*").eq("id", cliente_id).execute()
    return response.data
```

## Arquitetura

- **Singleton Pattern**: Uma única instância do client por processo
- **Service Role**: Usa a service_role key por padrão (bypassa RLS quando necessário)
- **RLS Context**: Para queries que precisam respeitar RLS, chame `set_current_cliente_id` via RPC

## Diferenças do SQLAlchemy

| SQLAlchemy | Supabase SDK |
|------------|--------------|
| `session.execute(select(Model))` | `client.table("table").select("*")` |
| `session.add(obj)` | `client.table("table").insert({...})` |
| `session.query(Model).filter(...)` | `client.table("table").select("*").eq(...)` |
| Conexão PostgreSQL direta | API REST via HTTP |
| `DATABASE_URL=postgresql://...` | `SUPABASE_URL=https://...` |

## Migrations

As migrations continuam sendo gerenciadas via Supabase MCP ou SQL Editor no Dashboard. O SDK não suporta migrations DDL diretamente.
