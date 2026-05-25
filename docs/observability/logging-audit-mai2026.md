# Logging & Telemetry Audit — Pre-Onboarding (Mai/2026)

Auditoria do estado de logging estruturado e instrumentação OTEL antes da abertura
do onboarding de clientes. Foco: identificar pontos onde, em produção, vamos
**perder visibilidade** ou **vazar dados sensíveis** em logs.

## TL;DR

| Item                                          | Status | Severidade |
|-----------------------------------------------|--------|------------|
| Structured logging (JSON) em prod             | ❌     | high       |
| OTEL traces no agent_api                      | ✅ via `core/observability.py` (Langfuse callbacks) | ok |
| OTEL traces no tool_pool_api                  | ⚠️ via `server/otel_instrumentation.py`, opcional | medium |
| `logger.*` adoption (Python stdlib `logging`) | ✅ 55+ arquivos | ok |
| `print()` em paths de produção                | ⚠️ ~12 ocorrências em scripts/tests + 1 em `core/config.py` | low |
| Risco de secrets em logs                      | ⚠️ não há scrubber central, mas auditoria não achou vazamento ativo (só literais em test_e2e_helper) | medium |
| `LOG_LEVEL` por env                           | ✅ `agent_api/main.py:115` lê `settings.LOG_LEVEL` | ok |
| Correlation IDs (request_id / trace_id)       | ⚠️ parcial — `trace_id` existe em observability, mas não propaga via middleware HTTP | high |
| Sampling OTEL                                 | ❌ default (sempre) — alto custo em escala | medium |

## Inventário

### agent_api
- `services/agent_api/src/agent_api/main.py:114` — `logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s — %(message)s')` — **texto plano**, sem JSON
- `services/agent_api/src/agent_api/core/observability.py` — gera `trace_id` (uuid4) e injeta no Langfuse CallbackHandler por requisição de rotina. Não há `contextvars` linkando o trace_id ao logger Python — logs paralelos ao trace ficam sem correlação.
- `services/agent_api/run_routine.py:30` — também usa `logging.basicConfig`, mesma config text.

### tool_pool_api
- `services/tool_pool_api/src/tool_pool_api/server/mcp_server.py:90` — chama `instrument_mcp_tools` se OTEL endpoint configurado.
- `server/otel_instrumentation.py` — wrapper que cria span por tool MCP invocada. Boa cobertura para tools, mas APIs HTTP (routers em `api/`) não estão instrumentadas explicitamente; dependem do auto-instrumentation FastAPI (precisa verificar `setup.py`/`pyproject.toml`).
- ~50 arquivos usando `logging.getLogger(__name__)` — pattern correto, mas formato textual.

### Anti-patterns confirmados
1. `services/tool_pool_api/src/tool_pool_api/core/config.py:68-70` — `print(settings.model_dump_json(indent=2))` no `__main__` (script de debug — aceitável, MAS não pode rodar em prod). Não há guard além de `if __name__=='__main__'` — OK.
2. `agent_api/run_routine.py:101,105` — `print(f"ERROR: ...")` em CLI standalone — OK no contexto CLI mas se invocado por subprocess perde estrutura. **Recomendar substituir por `logger.error`** para uniformidade.
3. `services/tool_pool_api/src/tool_pool_api/scripts/oauth_e2e_test.py` — vários `print(...)`. Script de E2E manual, não roda em prod. ✅ tolerável.

## Gaps críticos pré-onboarding

### G1 — Sem logger JSON em prod (high)
Cloud Run captura stdout/stderr e indexa, mas com formato texto perdemos:
- Filtros estruturados (`severity`, `trace_id`, `client_id`)
- Linkagem trace ↔ log no Grafana/Cloud Logging
- Alertas baseados em campos JSON

**Recomendação**: introduzir `python-json-logger` (sem migrar para structlog num primeiro momento — mantém compatibilidade com `logging.getLogger` existente).

Patch sugerido (1 arquivo por serviço):

```python
# services/agent_api/src/agent_api/main.py — substituir basicConfig
import json, logging
from pythonjsonlogger.jsonlogger import JsonFormatter

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"levelname": "severity", "asctime": "timestamp"},
))
root = logging.getLogger()
root.handlers.clear()
root.addHandler(handler)
root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
```

Custo: ~30 min por serviço. Sem mudar nenhum call site de `logger.*`.

### G2 — Correlation ID não propaga (high)
`trace_id` é gerado em `core/observability.py` mas vive só no closure do
`CallbackHandler` Langfuse. Adicionar middleware FastAPI que:

```python
from contextvars import ContextVar
_TRACE_ID: ContextVar[str | None] = ContextVar("trace_id", default=None)

@app.middleware("http")
async def trace_id_middleware(request, call_next):
    tid = request.headers.get("x-trace-id") or str(uuid.uuid4())
    token = _TRACE_ID.set(tid)
    response = await call_next(request)
    response.headers["x-trace-id"] = tid
    _TRACE_ID.reset(token)
    return response

class TraceIdFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = _TRACE_ID.get() or "-"
        return True
```

Add `%(trace_id)s` ao JsonFormatter e o frontend pode mandar `x-trace-id` que
amarra UI → backend → LLM call.

### G3 — Risco de secrets em logs (medium)
Não há scrubber central. Auditoria por regex (`refresh_token`, `access_token`,
`client_secret`, `password`, `api_key`) achou só ocorrências em
`test_e2e_helper.py` com valores `***`. **Mas** futuros `logger.exception` em
rotas OAuth podem espirrar tokens no traceback.

**Mitigação**: filter logging que faz redaction de chaves comuns:

```python
SENSITIVE_KEYS = {"access_token","refresh_token","client_secret","authorization","password","api_key"}

class RedactFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        for k in SENSITIVE_KEYS:
            if k in msg.lower():
                record.msg = re.sub(
                    rf'({k}["\']?\s*[:=]\s*["\']?)[^,\s"\']+',
                    r'\1***REDACTED***', record.msg, flags=re.I,
                )
        return True
```

Aplicar no root logger. Não é à prova de bala, mas cobre 80% dos vazamentos
acidentais (log de dict, traceback com kwargs).

### G4 — OTEL sampling (medium)
`OTEL_EXPORTER_OTLP_ENDPOINT` está em produção sem sampling configurado — todo
span vai pro Grafana Cloud. Para o volume atual de validação 72h tudo bem; mas
quando passarmos de 5 clientes simultâneos, configurar:

```
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1   # 10% em prod, 100% em staging
```

Custo: zero — só variáveis de ambiente no Cloud Run.

### G5 — APIs HTTP do tool_pool_api sem auto-instrumentation explícita (medium)
Confirmar se `opentelemetry-instrumentation-fastapi` está nos requirements e
sendo registrado. Se não, spans dos routers `api/*.py` não aparecem nas traces.

## Recomendações priorizadas

| # | Ação                                                      | Esforço | Bloqueia onboarding? |
|---|-----------------------------------------------------------|---------|----------------------|
| 1 | G1 + G2: JSON logger + trace_id middleware (ambos serviços) | 2h     | **Sim**              |
| 2 | G3: RedactFilter no root logger                            | 1h      | **Sim**              |
| 3 | G5: confirmar FastAPI auto-instrumentation                 | 30min   | Não — bom ter        |
| 4 | G4: sampling config                                       | 15min   | Não — pós-5-clientes |
| 5 | Substituir `print()` em `run_routine.py` por `logger.*`   | 15min   | Não                  |

## Anti-objetivos
- **Não** migrar para `structlog` agora — diff massivo em 55+ arquivos, sem
  ganho que não venha do JSON logger.
- **Não** introduzir Sentry — Cloud Logging + Grafana cobrem o suficiente para
  os primeiros 10 clientes.

## Follow-ups
- Adicionar `client_id` ao contexto do logger via middleware (depende do JWT
  middleware existente, fácil)
- Logbook de incidentes em `docs/incidents/YYYYMMDD_*.md` template
- Considerar `loguru` se equipe crescer — DX melhor, mas substitui logging
  inteiro (decisão para Q3)
