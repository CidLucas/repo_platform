# TASK PLAYBOOKS — repo_platform

> Receitas passo a passo para tarefas recorrentes de desenvolvimento no Blu.
> Mantido automaticamente pelo agente de documentação (cron noturno).
> Última atualização: 2026-05-25

---

## Índice

1. [Adicionar uma nova Rotina](#1-adicionar-uma-nova-rotina)
2. [Adicionar uma Fetch Function](#2-adicionar-uma-fetch-function)
3. [Adicionar uma Skill L3 (prompt Langfuse)](#3-adicionar-uma-skill-l3-prompt-langfuse)
4. [Adicionar uma nova Integração de API Token](#4-adicionar-uma-nova-integração-de-api-token)
5. [Adicionar um Tool Module](#5-adicionar-um-tool-module)
6. [Criar uma Migration de Schema](#6-criar-uma-migration-de-schema)
7. [Adicionar uma Edge Function](#7-adicionar-uma-edge-function)
8. [Adicionar um novo Room no Frontend](#8-adicionar-um-novo-room-no-frontend)
9. [Testar uma Rotina Manualmente](#9-testar-uma-rotina-manualmente)
10. [Onboarding de Cliente de Teste](#10-onboarding-de-cliente-de-teste)

---

## 1. Adicionar uma nova Rotina

Uma "rotina" é um job periódico ou event-driven que executa uma sequência de steps (fetch → LLM → artifact).

### Arquivos envolvidos
- `supabase/migrations/` — seed em `cross_agent_routines`
- `services/agent_api/src/agent_api/core/routine_functions.py` — fetch functions
- `services/agent_api/src/agent_api/core/routine_artifacts.py` — save do output
- `libs/blu_agent_framework/src/blu_agent_framework/routines/` — skills L3
- `libs/blu_prompt_management/src/blu_prompt_management/templates.py` — prompt builtin (fallback)
- Langfuse — prompt com type=skill (produção)

### Passos

**1. Definir a rotina no DB**
```sql
INSERT INTO cross_agent_routines (
  id,            -- slug em inglês (ex: 'daily_cash_alert')
  name,          -- nome legível PT-BR (ex: 'Alerta de Caixa Diário')
  room,          -- sala destino (financeiro|clientes|compras|agenda|estrategia|home)
  trigger_type,  -- 'cron' | 'event' | 'manual'
  trigger_config, -- ex: '{"expression": "0 8 * * *"}' para diário às 8h
  steps,         -- array de step objects (ver formato abaixo)
  agent_slug,    -- slug do agente responsável
  active         -- true
) VALUES (...);
```

**Formato de um step:**
```json
{
  "id": "fetch_data",
  "type": "function",           // 'function' | 'skill'
  "name": "get_cash_position",  // nome da fetch function ou skill slug
  "inputs": {"days": 7},
  "on_failure": "continue"      // 'continue' | 'abort'
}
```

**2. Criar a fetch function** (se precisar de dados novos)
- Abrir `routine_functions.py`
- Adicionar função `async def get_xxx(client_id: str, ...) -> dict`
- Registrar no dict de dispatch no topo do arquivo

**3. Criar a skill L3** (step type=skill)
- Criar arquivo em `libs/blu_agent_framework/src/blu_agent_framework/routines/`
- Adicionar prompt em `templates.py` com key `skill:nome_skill:system` e `type=skill`
- Criar prompt equivalente no Langfuse (produção)

**4. Definir o artefato de output**
- Se gerar insight: usar `save_insights()` em `routine_artifacts.py` com o `room` correto
- Se gerar relatório: usar `save_report()`

**5. Ativar para clientes**
```sql
INSERT INTO client_routines (client_id, routine_id, active, status, source, trigger_config)
VALUES ('<uuid>', 'daily_cash_alert', true, 'active', 'catalog', '{}');
```

**6. Testar**
Ver playbook [9. Testar uma Rotina Manualmente](#9-testar-uma-rotina-manualmente).

### Pitfalls críticos
- `triggered_by` é NOT NULL em `client_routine_executions` — sempre passar `'cron'` no INSERT manual
- Steps com `{{variavel}}` precisam de default no step, não no config do cliente
- `client_routines.source` aceita só: `catalog | custom | system`
- `active=false` bloqueia dispatch silenciosamente — checar antes de testar
- Nunca usar `is_active` (não existe) — usar `active`

---

## 2. Adicionar uma Fetch Function

Fetch functions alimentam rotinas com dados do DB antes da execução do LLM.

### Arquivo
`services/agent_api/src/agent_api/core/routine_functions.py`

### Passos

**1. Criar a função**
```python
async def get_minha_funcao(client_id: str, param1: int = 30) -> dict:
    """Descrição do que retorna."""
    # Usar get_direct_engine() para queries pesadas
    from blu_supabase_client.db_engine import get_pooler_engine
    engine = get_pooler_engine()
    # ... query ...
    return {"key": value}
```

**2. Registrar no dispatcher**
No topo de `routine_functions.py`, adicionar ao dict `FUNCTION_REGISTRY`:
```python
FUNCTION_REGISTRY = {
    ...
    "get_minha_funcao": get_minha_funcao,
}
```

**3. Referenciar no step da rotina**
```json
{"id": "fetch", "type": "function", "name": "get_minha_funcao", "inputs": {"param1": 30}}
```

### Pitfalls
- Usar `get_pooler_engine()` para queries rápidas, `get_direct_engine()` para bulk/ETL
- Retornar sempre dict serializável (sem objetos Pydantic nem datetime não-serializado)

---

## 3. Adicionar uma Skill L3 (prompt Langfuse)

Skills L3 são os prompts que os agentes usam para executar tarefas específicas.

### Arquivos
- `libs/blu_prompt_management/src/blu_prompt_management/templates.py` — fallback builtin
- Langfuse (produção) — prompt versionado

### Passos

**1. Definir o prompt builtin (fallback)**
Em `templates.py`, adicionar ao array `_L3_SKILL_TEMPLATES`:
```python
PromptTemplate(
    name="skill:nome_skill:system",
    type="skill",  # SEMPRE type=skill, nunca type=llm
    content="Você é um especialista em X...\n\n{{nome_empresa}}\n{{contexto}}",
    required_variables=["nome_empresa"],
    optional_variables=["contexto"],
)
```

**2. Criar no Langfuse (produção)**
- Key: `skill:nome_skill:system`
- Type: `skill`
- Mesmo conteúdo do builtin
- Configurar variáveis

**3. Usar na skill factory**
```python
# Em skill_factory.py, a skill é carregada automaticamente pelo slug
# O step precisa ter type='skill' e name='nome_skill'
```

### Pitfalls
- `type=llm` está depreciado — SEMPRE `type=skill`
- `nome_empresa` deve estar sempre nas variáveis passadas ao `build_prompt`
- Após adicionar ao `_L3_SKILL_TEMPLATES`, checar que `get_builtin_template()` é usado no loader (não `BUILTIN_TEMPLATES.get()`)

---

## 4. Adicionar uma nova Integração de API Token

Para integrações simples (Slack, Monday, Notion style) que usam API token estático.

### Arquivos envolvidos
- `supabase/functions/save-api-token/` — edge function de save (já existe, verificar se precisa de provider novo)
- `supabase/functions/_shared/` — helpers auth
- `services/tool_pool_api/src/tool_pool_api/server/tool_modules/` — criar `xxx_module.py`
- `services/tool_pool_api/src/tool_pool_api/api/integrations_router.py` — endpoint de save se diferente do padrão
- `apps/blu_v3/src/pages/app/AdminScreen.tsx` — UI de conexão
- `apps/blu_v3/src/api/admin.ts` — `fetchIntegrations()`

### Passos

**1. Verificar se `save-api-token` já suporta o provider**
A edge function valida o token no provider antes de salvar. Se for provider novo, adicionar a lógica de validação.

**2. Criar o tool module**
```python
# services/tool_pool_api/src/tool_pool_api/server/tool_modules/xxx_module.py
async def get_xxx_token(client_id: str) -> str:
    """Busca token de integration_tokens."""
    # provider key: 'xxx' (sem prefixo ic-)
    ...
```

**3. Registrar no `__init__.py` do tool_modules**

**4. Adicionar UI em AdminScreen.tsx**
- Adicionar provider ao array de integrações exibidas
- Botão "Conectar" chama `save-api-token` com `provider: 'xxx'`
- Estado: `doConnect` → `supabase.auth.getSession()` → POST edge function com `Authorization: Bearer <access_token>`

**5. Atualizar `fetchIntegrations()` em `admin.ts`**
Adicionar o novo provider ao filtro de `integration_tokens`.

### Pitfalls críticos
- Provider key em `integration_tokens`: sempre sem prefixo `ic-` (ex: `'monday'`, não `'ic-monday'`)
- `doConnect` precisa do `access_token` do usuário — nunca chamar edge function com anonKey do lado cliente
- Row em `integration_tokens` NÃO garante token válido — sempre validar antes de salvar
- Copiar helpers Fernet (`fernetEncrypt`, `requireAuth`, `resolveClientId`) de `onboarding-capture-drive-token/index.ts` verbatim
- Conflict key: `(client_id, provider, account_email)`

---

## 5. Adicionar um Tool Module

Tools são expostas via MCP ao Tool Pool API e chamadas pelos agentes.

### Arquivos
- `services/tool_pool_api/src/tool_pool_api/server/tool_modules/novo_module.py`
- `services/tool_pool_api/src/tool_pool_api/server/tool_modules/__init__.py`

### Passos

**1. Criar o módulo**
```python
from tool_pool_api.server.tool_helpers import register_tool

@register_tool(name="minha_tool", tier=["starter", "pro", "enterprise"])
async def minha_tool(client_id: str, param: str) -> dict:
    """Descrição clara da tool para o agente."""
    ...
    return {"result": ...}
```

**2. Registrar no `__init__.py`**
Importar e adicionar ao `ALL_MODULES`.

**3. Atualizar TOOL_INVENTORY.md**
Adicionar a tool à tabela com tier e domínio.

**4. Atualizar CODE_MAP.md**
Adicionar ao módulo correspondente.

### Pitfalls
- MCP tools NÃO são endpoints REST — não chamar do frontend diretamente
- Para expor ao frontend: criar edge function Supabase que chama a API externa diretamente

---

## 6. Criar uma Migration de Schema

### Processo

**1. Auditar o DB live antes de qualquer alteração**
```bash
psql "postgresql://..." -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'minha_tabela' AND table_schema = 'analytics_v2';"
```

**2. Verificar locks antes de DDL**
```sql
SELECT pid, state, wait_event_type, left(query,80) 
FROM pg_stat_activity 
WHERE state != 'idle' AND pid != pg_backend_pid();
```

**3. Criar o arquivo de migration**
Naming: `supabase/migrations/YYYYMMDDHHMMSS_descricao_curta.sql`

**4. Aplicar via psql**
```bash
psql "postgresql://..." -f supabase/migrations/NOME_DO_ARQUIVO.sql
```

**5. Verificar aplicação**
Checar que as alterações estão no DB antes de commitar.

### Pitfalls críticos
- `INTO v_n[1], v_n[2]` não existe em plpgsql — usar variáveis individuais
- `CREATE OR REPLACE FUNCTION` não muda `RETURNS TABLE` — usar `DROP FUNCTION IF EXISTS` antes
- DDL bloqueia com DML ativo na mesma tabela — matar processo bloqueador primeiro
- Separar DDL e DML em arquivos distintos
- Pooler port 6543 (transaction mode) trava em DELETE grande — usar port 5432 direto para bulk
- FK nova: sempre verificar `ON DELETE CASCADE` para `clientes_blu`
- `COMMENT ON FUNCTION` com overloads requer lista explícita de args

---

## 7. Adicionar uma Edge Function

### Processo

**1. Criar o diretório e arquivo**
```bash
mkdir supabase/functions/nome-da-funcao
touch supabase/functions/nome-da-funcao/index.ts
```

**2. Implementar usando o padrão auth correto**
```typescript
import { requireAuth, resolveClientId } from '../_shared/auth.ts'

Deno.serve(async (req) => {
  const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
  const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!
  const SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

  const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY)
  const client_id = await resolveClientId(ctx, SUPABASE_URL, SUPABASE_ANON_KEY)
  if (!client_id) return json({ error: 'client_id not found' }, 403)
  ...
})
```

**3. Registrar em `supabase/config.toml`**
```toml
[functions.nome-da-funcao]
verify_jwt = false   # se usa requireAuth interno
```

**4. Deploy**
```bash
npx supabase functions deploy nome-da-funcao --project-ref haruewffnubdgyofftut
```

### Pitfalls críticos
- Toda edge function nova PRECISA de entrada no `config.toml` — sem ela não é deployada corretamente
- `requireAuth` recebe 3 args: `(req, supabaseUrl, anonKey)` — não passar cliente Supabase como 2º arg
- `resolveClientId` é obrigatório para tokens de teste (não têm `client_id` nos metadados)

---

## 8. Adicionar um novo Room no Frontend

### Arquivos
- `apps/blu_v3/src/pages/app/NovoRoom.tsx` — componente principal
- `apps/blu_v3/src/api/novo.ts` — funções de fetch
- `apps/blu_v3/src/App.tsx` — rota
- `apps/blu_v3/src/store/` — se precisar de estado global

### Passos

1. Criar `NovoRoom.tsx` seguindo o padrão das rooms existentes (chat lateral + painel de dados)
2. Criar `novo.ts` em `src/api/` com as funções de fetch (chamam edge functions ou agent API)
3. Adicionar rota em `App.tsx`
4. Criar hook `useNovo.ts` se tiver queries React Query reutilizáveis
5. Adicionar ao menu de navegação

### Padrões obrigatórios
- Navegação entre rooms: usar `go(screen, label)` ou `goWithTab(screen, label, tabId)` do `useAppStore` — nunca `window.location.href`
- Auth: sempre `useAuth()` para obter `client_id` — nunca hardcodar
- Integrações: verificar `useIntegrations()` antes de mostrar CTAs de conexão

---

## 9. Testar uma Rotina Manualmente

### Pré-requisito: JWT válido
```bash
cd /Users/lucascruz/Documents/GitHub/repo_platform
python3 tests/agent_routing/get_test_token.py --email cid.lucas@gmail.com
# JWT salvo em /tmp/blu_test_jwt.txt
# Cliente com Monday: aaa37322 (cid.lucas@gmail.com)
# Cliente padrão: a05dec27 (lucascid@poli.ufrj.br)
```

### Disparar a rotina manualmente
```bash
TOKEN=$(docker exec blu_agent_api printenv ROUTINE_DISPATCH_TOKEN)

curl -X POST http://localhost:8003/v1/internal/routines/run-dispatched \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "<uuid>",
    "routine_id": "nome_da_rotina",
    "execution_id": "test-manual-001",
    "triggered_by": "manual"
  }'
```

### Verificar resultado
```sql
SELECT status, error_message, result_text, created_at
FROM client_routine_executions
WHERE client_id = '<uuid>'
ORDER BY created_at DESC LIMIT 5;
```

### Verificar dispatch via DB (se testando via pg_cron)
```sql
-- Checar net._http_response para erros de conexão
SELECT id, error_msg, created FROM net._http_response ORDER BY created DESC LIMIT 10;

-- Conferir app_config (URL do agent_api deve ser pública)
SELECT key, value FROM public.app_config WHERE key IN ('atendente_core_url','routine_dispatch_token');
```

### Pitfalls
- `triggered_by` é NOT NULL — sempre passar no INSERT manual
- `ROUTINE_DISPATCH_TOKEN` está mascarado no `.env` — pegar via `docker exec`
- `atendente_core_url` deve ser URL pública (não host Docker interno)
- `client_routines` com `active=false` bloqueia silenciosamente — verificar antes

---

## 10. Onboarding de Cliente de Teste

### Processo via frontend
1. Acessar landing page em `localhost:5175`
2. Completar o wizard de onboarding (nome, CNPJ, site, Google Drive ou CSV)
3. A edge function `onboarding-bootstrap` provisiona o tenant automaticamente

### Verificar provisionamento
```sql
-- Client criado?
SELECT client_id, nome_empresa, cpf_cnpj FROM clientes_blu ORDER BY created_at DESC LIMIT 5;

-- Rotinas ativas?
SELECT routine_id, active, status FROM client_routines WHERE client_id = '<uuid>';

-- Dados ingeridos?
SELECT COUNT(*), tipo_lancamento, entry_type FROM analytics_v2.fato_transacoes 
WHERE client_id = '<uuid>' GROUP BY tipo_lancamento, entry_type;
```

### Forçar re-dispatch do onboarding_complete
```sql
SELECT public.dispatch_routine_event(
  'onboarding_complete',
  '<client_id>'::uuid,
  '{"event_type":"onboarding_completed"}'::jsonb
);
```

### Pitfalls
- `active=false` em `client_routines` bloqueia dispatch — ver migration `20260522000300`
- `dispatch_routine_event` retorna null silenciosamente se guard blocked
- Token JWT expira em ~1h — rodar `get_test_token.py` para renovar
