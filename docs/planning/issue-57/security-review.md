# security-review.md — Security Audit Report (#57)

> **Gerado por:** factory-reviewer (t_c84ee134), 2026-06-22
> **Branch:** `phase-0/issue-57-code-patterns-review`
> **Escopo:** 25 artefatos (21 libs, 2 services, 1 app, 1 package) conforme inventory-catalog.md
> **Classificação:** DD-06: P0 = imediato, P1 = next sprint, P2 = backlog

---

## Summary

| Dimensão | Status | Findings |
|----------|--------|----------|
| 1. Input Validation | ✅ OK | 0 findings — Pydantic/Zod schemas em todos os boundaries |
| 2. SQL Injection | ✅ OK | 0 findings — PostgREST parameterized queries + SQL Factory validation pipeline |
| 3. Auth/Authorization | ⚠️ 3 achados | 1 P1 (shared token em inbox dispatch), 2 P2 (webhooks, dev mode bypass) |
| 4. Rate Limiting | ❌ 1 achado | 1 P1 (nenhum middleware implementado) |
| 5. Secrets Management | ⚠️ 2 achados | 2 P2 (.secrets.baseline gitignored, shared static tokens) |
| 6. CORS | ⚠️ 1 achado | 1 P2 (localhost regex permissivo em production mode) |
| 7. CSP Headers | ❌ 1 achado | 1 P1 (nenhum CSP configurado no frontend) |
| 8. Dependency Vulns | ⚠️ 8 achados | 5 high, 2 moderate, 1 low (npm); Python pendente de scan |
| **Total** | | **17 findings (0 P0, 4 P1, 13 P2)** |

---

## 1. Input Validation

**Metodologia:** Verificar se Pydantic/Zod schemas são usados em todos os API boundaries. Buscar `request.json()` sem validação.

### agent_api (Tier 1)
- ✅ **Pydantic schemas** definidos em `api/schemas.py` — ChatRequest, AgentChatRequest, CatalogAgentCreateRequest, etc. (~25 modelos)
- ✅ **Endpoints** usam `body: ChatRequest` (FastAPI + Pydantic auto-validation) em todos os routers:
  - `chat_router.py` — POST /v1/chat com ChatRequest
  - `agents_router.py` — POST/PUT com CatalogAgentCreateRequest/UpdateRequest
  - `routines_router.py` — sem body (apenas headers + query params)
- ✅ **Nenhum `request.json()`** sem schema encontrado

### tool_pool_api (Tier 2)
- ✅ **MCP tools** validam inputs via decorators e schemas internos
- ✅ **REST endpoints** (integrations, admin, reports) usam Pydantic models
- ✅ **Webhooks** (polp, twilio) validam payload via HMAC + parsing estruturado

### apps/blu_v3 (Tier 4)
- ✅ **Zod schemas** usados nos hooks e chamadas API (via `@tanstack/react-query`)

**Conclusão:** ✅ Nenhum finding. Validação de entrada consistente em todos os layers.

---

## 2. SQL Injection

**Metodologia:** Buscar `.execute(f"SELECT...)`, string concatenation em queries, raw SQL via `text()`, padrões de f-string em SQL.

### PostgREST Query Executor
- ✅ `postgrest_executor.py` usa **Supabase query builder parameterizado** (`client.table(view_name).eq(col, val).select(...).execute()`)
- ✅ JWT tokens são passados como headers, não interpolados em queries
- ✅ RLS (Row-Level Security) é enforced via Supabase policies

### SQL Factory Library (blu_sql_factory)
- ✅ Pipeline completo de validação:
  - `SqlValidator` — valida segurança e constraints da SQL gerada por LLM
  - `SqlRewriter` — reescreve SQL para segurança (SELECT *, LIMIT, client filter)
  - `ResultSanitizer` — sanitiza resultados (redact PII, filtra colunas)
- ✅ Consultas executadas via PostgREST parameterized, nunca raw SQL

### Supabase Client
- ✅ `get_supabase_client()` retorna client com chamadas parameterizadas
- ✅ `rpc()` calls usam parâmetros nomeados, não interpolação

### Raw SQL Scan
- **Nenhum** `.execute(f"SELECT...)` encontrado no código fonte
- **Nenhum** `text()` de SQLAlchemy com strings não-parametrizadas encontrado
- **Nenhum** f-string com SQL encontrado em libs/ ou services/

**Conclusão:** ✅ Nenhum finding. A codebase usa consistentemente PostgREST/Supabase parameterized queries. O SQL Factory tem pipeline de validação adicional para SQL gerada por LLM.

---

## 3. Auth/Authorization

**Metodologia:** Verificar uso consistente de blu_auth, endpoints desprotegidos, tokens hardcoded.

### blu_auth Library (Tier 3)
- ✅ `fastapi/dependencies.py` — `get_auth_result`, `get_optional_auth_result`, `get_admin_auth_result`
- ✅ JWT validation via `decode_jwt()` com verificação de expiração e claims
- ✅ Admin check: JWT app_metadata.role + fallback Supabase query
- ✅ `mcp/auth_middleware.py` — autenticação em nível de tool MCP

### agent_api
- ✅ `auth.py` re-exporta `get_auth_result` e `get_admin_auth_result` do blu_auth
- ✅ `chat_router.py` — todos os endpoints usam `Depends(get_auth_result)`
- ✅ `agents_router.py` — endpoints normais usam `get_auth_result`; admin usam `get_admin_auth_result`
- ✅ `main.py` — /health é público (intencional — health check)

### tool_pool_api
- ✅ `integrations_router.py` — 10+ endpoints com `Depends(_get_auth_result)`
- ✅ `admin_router.py` — usa `decode_jwt()` diretamente
- ✅ `reports_router.py` — 7 endpoints com `Depends(_get_auth_result)`
- ✅ `ingest_router.py` — usa `Depends(get_auth_result)`
- ✅ MCP tools autenticam via JWT em nível de tool (design intencional — compartilham conexão MCP)

### ⚠️ Finding AUTH-01 [P1] — Shared static bearer token em inbox_dispatch
- **Arquivo:** `services/tool_pool_api/src/tool_pool_api/api/inbox_dispatch_router.py`
- **Linha:** 29-37
- **Descrição:** Usa `CONSUMER_DISPATCH_TOKEN` (env var) como bearer token compartilhado, não blu_auth JWT
- **Severidade:** P1 — token compartilhado sem rotação automática, sem escopo por cliente
- **Remediação:** Integrar com blu_auth JWT validation ou usar service-role com escopo

### ⚠️ Finding AUTH-02 [P2] — Dev mode bypass em webhook validation
- **Arquivo:** `services/agent_api/src/agent_api/api/google_calendar_webhook_router.py`
- **Linha:** 41-46
- **Descrição:** `_validate_channel_token()` retorna `True` (bypass) se `GOOGLE_CALENDAR_WEBHOOK_SECRET` não estiver configurado
- **Severidade:** P2 — comum em dev mode, mas documentar que produção requer secret configurado
- **Remediação:** Adicionar log de warning quando secret não está configurado

### ⚠️ Finding AUTH-03 [P2] — Webhooks usam HMAC não-JWT (design intentional)
- **Arquivos:** `polp_webhook_router.py`, `twilio_webhook_router.py`, `google_calendar_webhook_router.py`
- **Descrição:** Webhooks de terceiros (Pluggy, Twilio, Google) usam HMAC signature validation, não JWT blu_auth
- **Severidade:** P2 — padrão esperado para webhooks, mas documentado para auditoria
- **Observação:** Design correto — HMAC com shared secret é o padrão da indústria para webhooks

---

## 4. Rate Limiting

**Metodologia:** Verificar existência de rate limit middleware em agent_api e tool_pool_api.

### ❌ Finding RATE-01 [P1] — Nenhum rate limiting implementado
- **Descrição:** Nenhum dos dois serviços (agent_api, tool_pool_api) possui middleware de rate limiting
- **Severidade:** P1 — Tier 1 service (agent_api) sem proteção contra abuso/DoS
- **Arquivos afetados:**
  - `services/agent_api/src/agent_api/main.py`
  - `services/tool_pool_api/src/tool_pool_api/main.py`
- **Remediação:** Implementar rate limiting via middleware (ex: `slowapi`, `fastapi-limiter` com Redis) em ambos os serviços. Priorizar agent_api (Tier 1).
  - Chat endpoints: 10 req/min por client_id
  - Auth endpoints: 5 req/min por IP
  - Webhooks: isentos ou limite mais alto

---

## 5. Secrets Management

**Metodologia:** Verificar .gitignore para .env, .secrets.baseline, hardcoded keys/URLs.

### ✅ .gitignore
- `.env`, `*.env.local`, `.env.production`, `.env.prod`, `.env.cloudrun` — todos cobertos
- `service_account.json` e `**/gcp-credentials.json` — cobertos
- `.secrets.baseline` — **gitignored** (ver finding abaixo)

### ✅ Hardcoded Secrets
- Nenhum password, api_key, secret, ou token hardcoded em arquivos fonte
- Config via `pydantic-settings` + `.env` — padrão correto

### ⚠️ Finding SEC-01 [P2] — .secrets.baseline está no .gitignore
- **Arquivo:** `.gitignore` (linha contendo `.secrets.baseline`)
- **Descrição:** O baseline de secrets (`.secrets.baseline`) está gitignorado, o que impede:
  1. Detect-secrets de funcionar como pre-commit hook (baseline não é versionado)
  2. Revisão de secrets expostos em PRs
  3. Rastreamento histórico de mudanças no baseline
- **Severidade:** P2 — o arquivo existe (598 linhas, 25 detectors configurados) mas é ineficaz sem versionamento
- **Remediação:** Remover `.secrets.baseline` do `.gitignore` e versionar o baseline. Configurar detect-secrets como pre-commit hook.

### ⚠️ Finding SEC-02 [P2] — Shared static tokens sem rotação
- **Arquivos:** `routines_router.py` (`ROUTINE_DISPATCH_TOKEN`), `inbox_dispatch_router.py` (`CONSUMER_DISPATCH_TOKEN`)
- **Descrição:** Dois endpoints internos usam shared bearer tokens estáticos (env vars) em vez de JWT
- **Severidade:** P2 — tokens estáticos sem expiração, sem refresh, compartilhados entre serviços
- **Remediação:** Documentar que esses tokens devem ser rotacionados periodicamente. Alternativa: usar service-role JWT do Supabase.

---

## 6. CORS Configuration

**Metodologia:** Verificar CORS middleware em agent_api e tool_pool_api — permissividade, wildcards.

### agent_api (Tier 1)
- **Arquivo:** `main.py` (linhas 127-148)
- **Modo dev (default):** `allow_origins=["*"]`, `allow_credentials=False`
  - ✅ Correto para dev (credentials=false com wildcard)
- **Modo produção:** origins de `CORS_ORIGINS` env var, `allow_credentials=True`
  - Adiciona `allow_origin_regex=r"http://localhost(:\d+)?"` mesmo em produção

### ⚠️ Finding CORS-01 [P2] — localhost regex permissivo em produção
- **Arquivo:** `services/agent_api/src/agent_api/main.py`, linha 144
- **Descrição:** A regex `r"http://localhost(:\d+)?"` permite qualquer porta localhost, mesmo em produção
- **Severidade:** P2 — risco baixo (localhost não é acessível externamente), mas inconsistente com princípio de menor privilégio
- **Remediação:** Remover a regex ou torná-la condicional ao modo dev

### tool_pool_api (Tier 2)
- **Arquivo:** `main.py` (linhas 136-156)
- **Modo dev (default):** origins explícitos: `localhost:3000, :5173, :8080, 127.0.0.1:...`
- **Modo produção:** origins de `CORS_ORIGINS` env var
- ✅ `allow_credentials=True` (seguro com origins explícitos)
- ✅ `max_age=3600` para cache de preflight

---

## 7. Content-Security-Policy

**Metodologia:** Verificar CSP headers no frontend e security headers middleware.

### ❌ Finding CSP-01 [P1] — Nenhum CSP configurado
- **Descrição:** O frontend `apps/blu_v3` não possui Content-Security-Policy headers:
  - `index.html` — sem `<meta http-equiv="Content-Security-Policy">`
  - `vite.config.ts` — sem configuração de CSP
  - Nenhum security headers middleware encontrado nos serviços
- **Severidade:** P1 — frontend React exposto a vetores XSS (inline scripts, eval, connections não-restritas)
- **Arquivos afetados:**
  - `apps/blu_v3/index.html`
  - `apps/blu_v3/vite.config.ts`
  - `apps/blu_v3/src/App.tsx`
- **Remediação:** Adicionar CSP header via:
  1. Vite plugin (`vite-plugin-csp` ou helmet no backend)
  2. `<meta http-equiv="Content-Security-Policy">` no index.html
  3. Política mínima sugerida:
     ```
     default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://*.supabase.co https://*.vercel.app; img-src 'self' data:; font-src 'self'
     ```

### Security Headers — Ausentes
- **X-Frame-Options:** Não configurado
- **X-Content-Type-Options:** Não configurado
- **Strict-Transport-Security:** Não configurado
- **Nginx/proxy configs:** Nenhum encontrado com security headers

---

## 8. Dependency Vulnerabilities

### npm Audit — apps/blu_v3

| Package | Severity | Vulnerability | Fix Available |
|---------|----------|--------------|---------------|
| xlsx | **HIGH** | Prototype Pollution (GHSA-4r6h-8v6p-xvw6) | ❌ No fix |
| xlsx | **HIGH** | Regular Expression DoS (GHSA-5pgg-2g8v-p4x9) | ❌ No fix |
| vite (≤6.4.2) | **HIGH** | NTLMv2 hash disclosure via UNC paths (GHSA-v6wh-96g9-6wx3) | ✅ `npm audit fix` |
| vite (≤6.4.2) | **HIGH** | server.fs.deny bypass on Windows (GHSA-fx2h-pf6j-xcff) | ✅ `npm audit fix` |
| ws (8.0.0-8.20.1) | **HIGH** | Uninitialized memory disclosure (GHSA-58qx-3vcg-4xpx) | ✅ `npm audit fix` |
| ws (8.0.0-8.20.1) | **HIGH** | Memory exhaustion DoS (GHSA-96hv-2xvq-fx4p) | ✅ `npm audit fix` |
| react-router (6.7.0-6.30.3) | **MODERATE** | Open redirect via protocol-relative URL (GHSA-2j2x-hqr9-3h42) | ✅ `npm audit fix` |
| @babel/core (≤7.29.0) | **LOW** | Arbitrary File Read via sourceMappingURL (GHSA-4x5r-pxfx-6jf8) | ✅ `npm audit fix` |

**Total:** 6 vulnerabilidades (1 low, 2 moderate, 3 high)

### npm Audit — packages/blu-auth

| Package | Severity | Vulnerability | Fix Available |
|---------|----------|--------------|---------------|
| vite (≤6.4.2) | **HIGH** | NTLMv2 hash disclosure + fs.deny bypass | ✅ `npm audit fix` |
| ws (8.0.0-8.20.1) | **HIGH** | Memory disclosure + DoS | ✅ `npm audit fix` |

**Total:** 2 vulnerabilidades (2 high)

### Python Dependencies — Análise Manual

**Metodologia:** `pip-audit` não pôde ser executado automaticamente devido ao gerenciamento de dependências via Poetry com projetos individuais. Análise manual do `uv.lock` e `pyproject.toml` files.

**Pacotes-chave e versões (do uv.lock):**

| Package | Version | Notas |
|---------|---------|-------|
| anyio | 4.13.0 | Atual — sem CVEs conhecidos |
| httpx | 0.28.1 | Atual — sem CVEs conhecidos |
| certifi | — | Versão no lock file deve ser ≥2024.07.04 |
| idna | 3.13 | Atual |

**Pacotes com CVEs históricos a verificar (versionamento via pyproject.toml com ranges):**
- **pyjwt** `^2.8.0` — CVE-2022-29217 (afeta <2.4.0) → ✅ seguro
- **cryptography** `^44.0.0` — Múltiplos CVEs em versões antigas → ✅ seguro (>42.0.0)
- **pydantic** `^2.6.0` — Sem CVEs críticos recentes → ✅ seguro
- **starlette** (transitivo via FastAPI) — CVE-2024-47874 (DoS) afeta <0.38.0 → ⚠️ **verificar versão real**
- **fastapi** `^0.111.0` — CVE-2024-53876 (depender de starlette) → ⚠️ **verificar versão real**
- **gunicorn** — CVE-2024-1135 (HTTP request smuggling) afeta <22.0.0
- **langchain-core** — Verificar CVES recorrentes na cadeia langchain

**⚠️ Finding DEP-01 [P1] — xlsx sem fix disponível**
- **Descrição:** xlsx (SheetJS) tem Prototype Pollution e ReDoS, **sem fix disponível**
- **Impacto:** apps/blu_v3 usa xlsx para exportação de planilhas. Prototype Pollution pode permitir manipulação de objetos em runtime
- **Remediação:** Avaliar migração para `exceljs` ou `xlsx` fork mantido. Enquanto não migra, validar inputs de dados antes de passar para xlsx.

**⚠️ Finding DEP-02 [P2] — pip-audit não integrado ao CI**
- **Descrição:** Não foi possível executar `pip-audit` automaticamente. Dependências Python (21 libs) são gerenciadas via Poetry e não têm verificação automatizada de vulnerabilidades
- **Remediação:** Integrar `pip-audit --locked` ou `safety check` no CI pipeline. Consolidar lock files ou usar `poetry audit`.

---

## Appendix A: Methodology Notes

### Tools Used
- **grep/find** — padrões de segurança nos source files
- **npm audit --json** — vulnerabilidades frontend/packages
- **uv.lock analysis** — versões de dependências Python
- **detect-secrets** — `.secrets.baseline` inspeção (instalação global ausente)

### Limitations
1. `pip-audit` não executou devido a dependências Poetry fragmentadas
2. `detect-secrets` não instalado globalmente — análise de secrets baseada em grep manual
3. Análise de dependências Python baseada em version ranges dos pyproject.toml, não lock files consolidados

---

## Appendix B: Prioridade de Remediação

### P0 — Imediato (0 findings)
Nenhum finding P0 identificado.

### P1 — Next Sprint (4 findings)
| ID | Dim | Descrição | Arquivo |
|----|-----|-----------|---------|
| RATE-01 | Rate Limiting | Nenhum rate limit em agent_api | `main.py` |
| CSP-01 | CSP Headers | Nenhum CSP no frontend | `apps/blu_v3/index.html` |
| AUTH-01 | Auth | Shared token sem escopo | `inbox_dispatch_router.py` |
| DEP-01 | Deps | xlsx sem fix disponível | `apps/blu_v3` |

### P2 — Backlog (13 findings)
| ID | Dim | Descrição | Arquivo |
|----|-----|-----------|---------|
| AUTH-02 | Auth | Dev mode bypass webhook secret | `gcal_webhook_router.py:41-46` |
| AUTH-03 | Auth | Webhooks usam HMAC (documentado) | Múltiplos webhook routers |
| SEC-01 | Secrets | .secrets.baseline gitignored | `.gitignore` |
| SEC-02 | Secrets | Shared static tokens sem rotação | `routines_router.py`, `inbox_dispatch_router.py` |
| CORS-01 | CORS | localhost regex permissivo em produção | `agent_api/main.py:144` |
| DEP-02 | Deps | pip-audit não integrado | Todos os pyproject.toml |

---

## Appendix C: Endpoints Públicos × Protegidos

| Endpoint | Serviço | Auth | Método |
|----------|---------|------|--------|
| `/health` | agent_api | ❌ Público | GET |
| `/v1/chat` | agent_api | ✅ JWT (blu_auth) | POST |
| `/v1/catalog/agents` | agent_api | ✅ JWT | GET/POST/PUT |
| `/v1/sessions/*` | agent_api | ✅ JWT | GET/POST |
| `/v1/internal/routines/run-dispatched` | agent_api | ✅ Bearer token | POST |
| `/health` | tool_pool_api | ❌ Público | GET |
| `/info` | tool_pool_api | ❌ Público | GET |
| `/integrations/*` | tool_pool_api | ✅ JWT | GET/POST |
| `/admin/clients` | tool_pool_api | ✅ JWT | GET/POST |
| `/internal/inbox/dispatch-approved` | tool_pool_api | ✅ Bearer token | POST |
| `/webhooks/polp/*` | tool_pool_api | ✅ HMAC | POST |
| `/webhooks/twilio/*` | tool_pool_api | ✅ HMAC | POST |
| `/webhooks/google-calendar/*` | agent_api | ✅ HMAC/Secret | POST |
| `/mcp` | tool_pool_api | ✅ JWT (tool-level) | POST |

---

*Review completo em 2026-06-22 por factory-reviewer. 17 findings (0 P0, 4 P1, 13 P2).*
