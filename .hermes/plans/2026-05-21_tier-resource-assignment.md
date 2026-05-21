# Plano: Tier Enforcement & Resource Assignment

**Status:** Plano — sem execução de código
**Motivação:** Identificado durante Layer 1 dos testes de routing — a atribuição de tools aos agentes
está na granularidade errada. O tier controla tools individuais, mas deveria controlar capacidades de negócio.

---

## Estado atual (o que foi lido no repo)

### Três pontos de enforcement, todos atuando em tools diretamente

```
TierValidator.TIER_DEFINITIONS         tier → lista de slugs de tools (tier_validator.py)
ToolMetadata.tier_required             por tool, tier mínimo (tool_metadata.py)
factory.py get_frontdesk_graph()       filtra enabled_tools por meta.is_accessible_by_tier(tier)
factory.py get_standalone_agent()      idem, + enforce catalog.tier_required
routines.py                            enforce cfg.tier_required antes de rodar worker
agents_router.py /catalog/agents       filtra agents visíveis por tier do cliente
```

### Dois registros com `enabled_tools` hardcoded e divergentes

```
blu_tool_registry/registry.py          ToolMetadata por tool, com tier_required individual
blu_agent_framework/registry.py        AgentTypeConfig por agente, com enabled_tools: list[str]
```

Problema: um agente tem uma lista de tools definida em `AgentTypeConfig.enabled_tools`. O tier do
cliente fatia essa lista por `ToolMetadata.tier_required`. Resultado: o agente recebe um conjunto
de tools que não representa nenhuma capacidade coerente — é simplesmente o que sobrou após o corte.

### Inconsistências encontradas

- `ENTERPRISE` tem os mesmos `included_tools` que `PREMIUM` no `tier_validator.py` (Docker MCP tools faltam)
- `features` em `TIER_DEFINITIONS` existe mas **nunca é lido em nenhum lugar do codebase** (dead code)
- `clientes_blu.available_tools` existe no banco mas está `{}` em todos os clientes — override não usado
- `agent_catalog.tier_required` é um terceiro lugar onde tier é verificado (além de ToolRegistry e TierValidator)
- `tool_pool_api/server/resources.py` tem um quarto ponto: `context.get_enabled_tools_list()`
- `AgentTypeConfig.tier_required` existe mas não é verificado no path de routing de chat (só standalone)

### O hook que já existe mas é dead code

`TierValidator.TIER_DEFINITIONS["PREMIUM"]["features"]` já existe com uma lista de strings como
`["rag", "sql", "scheduling", "google_integrations"]`. A arquitetura queria chegar aqui mas
nunca implementou a Feature layer entre tier e tools.

---

## Modelo correto

```
Tier do cliente
  └── habilita Features  (capacidades de negócio — ex: "crm_avancado", "fiscal", "compras")
        └── cada Feature declara Resources
              ├── agents habilitados  (slugs do AgentTypeRegistry)
              ├── tools habilitadas   (slugs do ToolRegistry)
              └── skills habilitadas  (slugs do SkillRegistry — futuro)
```

O `AgentBuilder` recebe o conjunto de resources resolvido no build-time, nunca uma lista estática.

---

## Inventário completo (resultado da auditoria)

### Agents (15 no AgentTypeRegistry)

| Slug | Capacidade de negócio | Tier atual no registry |
|------|-----------------------|------------------------|
| frontdesk | Chat geral, RAG, SQL básico | BASIC |
| context-gatherer | Onboarding / coleta de contexto | BASIC |
| synthesis | Análise cross-dimensional | BASIC (deveria ser SME+) |
| data-analyst | SQL avançado + RAG | BASIC (deveria ser SME+) |
| platform | Configuração de rotinas e metas | BASIC (deveria ser SME+) |
| crm | CRM: RFM, churn, LTV, cohort | BASIC (deveria ser SME+) |
| estrategia | Planejamento estratégico | BASIC (deveria ser PREMIUM+) |
| financeiro | Monitor financeiro | BASIC |
| compras | Monitor de compras/estoque | BASIC |
| agenda | Monitor de agenda | BASIC |
| documentos | Monitor de documentos/biblioteca | BASIC |
| supplier-agent | Cotações e comunicação com fornecedores | BASIC (deveria ser SME+) |
| scheduler-agent | Agenda + Monday + Asana | BASIC (deveria ser SME+) |
| doc-writer | Redação de documentos com HITL | BASIC |
| fiscal-agent | Emissão de NF (stub SEFAZ) | BASIC (deveria ser PREMIUM+) |

### Tools críticas por domínio (do ToolRegistry)

| Domínio | Tools |
|---------|-------|
| RAG | executar_rag_cliente |
| SQL | execute_sql, executar_sql_agent |
| Google | google_calendar_list_events, google_calendar_create_event, google_drive_list_files |
| Agenda | agendar_consulta |
| Compras | list_suppliers, send_rfq, whatsapp_* (supplier tools) |
| Fiscal | emitir_nfe, consultar_sefaz (stub) |
| Comunicação | slack_post_message, whatsapp_send_message |
| Monday | monday_list_boards, monday_create_item, etc. |
| Plataforma | listar_rotinas_catalogo, listar_metas, criar_rotina, definir_meta |

---

## Feature Map proposto

Cada Feature é um bundle nomeado de recursos que tem semântica de produto clara.

```python
FEATURES = {
    # ── Presentes em todos os tiers ──────────────────────────────────────
    "chat_basico": Feature(
        agents=["frontdesk", "context-gatherer"],
        tools=["ferramenta_publica_de_teste"],
    ),
    "rag": Feature(
        agents=["frontdesk", "documentos"],
        tools=["executar_rag_cliente"],
    ),

    # ── SME ──────────────────────────────────────────────────────────────
    "sql_analytics": Feature(
        agents=["frontdesk", "data-analyst"],
        tools=["execute_sql", "executar_sql_agent"],
    ),
    "platform_ops": Feature(
        agents=["platform"],
        tools=["listar_rotinas_catalogo", "listar_metas", "criar_rotina", "definir_meta"],
    ),
    "synthesis": Feature(
        agents=["synthesis", "data-analyst"],
        tools=["execute_sql", "executar_rag_cliente"],
    ),
    "compras": Feature(
        agents=["compras", "supplier-agent"],
        tools=["list_suppliers", "send_rfq", "execute_sql"],
    ),
    "agenda": Feature(
        agents=["agenda", "scheduler-agent"],
        tools=["agendar_consulta", "monday_list_boards"],
    ),

    # ── PREMIUM ──────────────────────────────────────────────────────────
    "crm_avancado": Feature(
        agents=["crm"],
        tools=["execute_sql", "executar_rag_cliente", "slack_post_message"],
    ),
    "google_integrations": Feature(
        agents=["agenda"],
        tools=["google_calendar_list_events", "google_calendar_create_event",
               "google_drive_list_files"],
    ),
    "financeiro": Feature(
        agents=["financeiro"],
        tools=["execute_sql"],
    ),
    "estrategia": Feature(
        agents=["estrategia", "synthesis", "data-analyst"],
        tools=["execute_sql", "executar_rag_cliente"],
    ),
    "doc_writer": Feature(
        agents=["doc-writer", "documentos"],
        tools=["executar_rag_cliente"],
    ),

    # ── ENTERPRISE ───────────────────────────────────────────────────────
    "fiscal": Feature(
        agents=["fiscal-agent"],
        tools=["emitir_nfe", "consultar_sefaz"],
    ),
    "docker_mcp": Feature(
        agents=[],
        tools=["*docker_mcp*"],  # wildcard para todas as tools Docker MCP
    ),
}
```

### Tier → Features matrix

| Feature | FREE | BASIC | SME | PREMIUM | ENTERPRISE |
|---------|:----:|:-----:|:---:|:-------:|:----------:|
| chat_basico | ✓ | ✓ | ✓ | ✓ | ✓ |
| rag | — | ✓ | ✓ | ✓ | ✓ |
| sql_analytics | — | — | ✓ | ✓ | ✓ |
| platform_ops | — | — | ✓ | ✓ | ✓ |
| synthesis | — | — | ✓ | ✓ | ✓ |
| compras | — | — | ✓ | ✓ | ✓ |
| agenda | — | — | ✓ | ✓ | ✓ |
| financeiro | — | — | ✓ | ✓ | ✓ |
| doc_writer | — | — | ✓ | ✓ | ✓ |
| crm_avancado | — | — | — | ✓ | ✓ |
| google_integrations | — | — | — | ✓ | ✓ |
| estrategia | — | — | — | ✓ | ✓ |
| fiscal | — | — | — | — | ✓ |
| docker_mcp | — | — | — | — | ✓ |

---

## Arquitetura da solução

### Novo componente: `FeatureRegistry` + `ResourceResolver`

Local: `libs/blu_tool_registry/src/blu_tool_registry/features.py` (novo arquivo)

```python
@dataclass(frozen=True)
class FeatureConfig:
    name: str
    agents: list[str]        # slugs de AgentTypeConfig
    tools: list[str]         # slugs de ToolMetadata
    skills: list[str] = ()   # slugs de skill (futuro)
    description: str = ""

class FeatureRegistry:
    _features: dict[str, FeatureConfig]
    _tier_features: dict[str, list[str]]  # tier → lista de feature names

    @classmethod
    def get_features_for_tier(cls, tier: str) -> list[FeatureConfig]: ...

    @classmethod
    def get_agents_for_tier(cls, tier: str) -> set[str]: ...

    @classmethod
    def get_tools_for_tier(cls, tier: str) -> set[str]: ...

    @classmethod
    def get_tools_for_agent(cls, agent_slug: str, tier: str) -> list[str]:
        """Intersecção: tools do agente ∩ tools habilitadas pelo tier do cliente."""
        ...
```

Local: `libs/blu_tool_registry/src/blu_tool_registry/resource_resolver.py` (novo arquivo)

```python
class ResourceResolver:
    """
    Ponto único de resolução de recursos em runtime.
    Recebe (agent_slug, client_tier) → retorna lista de tools.
    """
    @classmethod
    def resolve_tools(cls, agent_slug: str, client_tier: str) -> list[str]:
        feature_tools = FeatureRegistry.get_tools_for_agent(agent_slug, client_tier)
        agent_cfg = AgentTypeRegistry.get(agent_slug)
        agent_tools = set(agent_cfg.enabled_tools) if agent_cfg else set()
        # Tools disponíveis = interseção entre o que o agente sabe usar
        # e o que o Feature do tier habilita
        return list(agent_tools & feature_tools)

    @classmethod
    def resolve_agents(cls, client_tier: str) -> list[str]:
        """Quais agents este tier pode acessar."""
        return list(FeatureRegistry.get_agents_for_tier(client_tier))

    @classmethod
    def can_access_agent(cls, agent_slug: str, client_tier: str) -> bool:
        return agent_slug in cls.resolve_agents(client_tier)
```

---

## Fases de implementação

### Fase 0 — Auditoria e documentação (sem código) [1–2 dias]

Antes de qualquer código, produzir dois artefatos:

1. **Tool inventory completo** — ler `tool_pool_api/server/resources.py` e todas as tool_modules
   e montar uma tabela com: slug | categoria | tier_required atual | domínio de negócio

2. **Feature map validado** — revisar o Feature Map proposto acima contra o inventário de tools
   real e confirmar que nenhuma tool crítica ficou sem Feature

Entregável: `docs/FEATURE_MAP.md` e `docs/TOOL_INVENTORY.md`

---

### Fase 1 — FeatureRegistry [2–3 dias]

**Arquivos a criar:**
- `libs/blu_tool_registry/src/blu_tool_registry/features.py`
  - `FeatureConfig` dataclass
  - `FeatureRegistry` com FEATURES dict e TIER_FEATURES dict
  - Métodos: `get_features_for_tier`, `get_agents_for_tier`, `get_tools_for_tier`

- `libs/blu_tool_registry/src/blu_tool_registry/resource_resolver.py`
  - `ResourceResolver.resolve_tools(agent_slug, tier) → list[str]`
  - `ResourceResolver.resolve_agents(tier) → list[str]`
  - `ResourceResolver.can_access_agent(slug, tier) → bool`

**Arquivos a modificar:**
- `libs/blu_tool_registry/src/blu_tool_registry/__init__.py`
  → exportar `FeatureRegistry`, `ResourceResolver`, `FeatureConfig`

**Sem modificar nada no factory nem no service ainda** — esta fase é só a lib.

**Testes:**
- `libs/blu_tool_registry/tests/test_feature_registry.py`
  - BASIC tier não acessa `crm_avancado`
  - PREMIUM tier acessa `estrategia`
  - `resolve_tools("crm", "BASIC")` retorna lista vazia
  - `resolve_tools("crm", "PREMIUM")` retorna tools corretas

---

### Fase 2 — Migrar factory.py para ResourceResolver [1–2 dias]

**Arquivos a modificar:**
- `services/agent_api/src/agent_api/core/factory.py`
  - `get_frontdesk_graph()`: substituir filtro inline por `ResourceResolver.resolve_tools("frontdesk", tier)`
  - `get_standalone_agent()`: substituir filtro inline por `ResourceResolver.resolve_tools(slug, tier)`
  - Substituir `TierValidator.is_tier_higher_or_equal()` por `ResourceResolver.can_access_agent(slug, tier)`

**Arquivos a modificar:**
- `services/agent_api/src/agent_api/core/routines.py`
  - Substituir filtro de tools do worker por `ResourceResolver.resolve_tools(slug, tier)`

**Backward compatibility:** manter `TierValidator` e `ToolMetadata.tier_required` funcionando —
o `ResourceResolver` consulta ambos como fallback quando um agente não está mapeado em nenhuma Feature.

---

### Fase 3 — Migrar routing de chat [1 dia]

**Arquivos a modificar:**
- `services/agent_api/src/agent_api/core/service.py`
  - `detect_specialist_intent()`: verificar se o agente resolvido é acessível via
    `ResourceResolver.can_access_agent(slug, tier)` antes de rotear
  - Se não for acessível → fallback para frontdesk com mensagem de upsell
  - Routing de PlatformAgent e SynthesisAgent: idem

**Arquivos a modificar:**
- `services/agent_api/src/agent_api/api/agents_router.py`
  - `/catalog/agents`: substituir filtro manual de tier_order por `ResourceResolver.resolve_agents(tier)`

---

### Fase 4 — Migrar tool_pool_api [1 dia]

**Arquivos a modificar:**
- `services/tool_pool_api/src/tool_pool_api/server/resources.py`
  - `context.get_enabled_tools_list()` → `ResourceResolver.resolve_tools(agent_slug, tier)`
  - Esta é a 4ª cópia do enforcement — unificar aqui elimina o último ponto divergente

---

### Fase 5 — Limpar dead code e inconsistências [1 dia]

**O que remover/corrigir:**
- `TierValidator.TIER_DEFINITIONS[*]["features"]` — reativar ou remover
  (recomendação: mapear para `FeatureRegistry._tier_features` e remover o dict duplicado)
- `TierValidator.TIER_DEFINITIONS["ENTERPRISE"]["included_tools"]` — está igual a PREMIUM, falta Docker MCP
- `clientes_blu.available_tools` — coluna existe mas não é usada; ou implementar override de feature
  por cliente via essa coluna, ou documentar que é deprecated
- `AgentTypeConfig.tier_required` — todos os agentes têm BASIC; atualizar para os valores corretos
  da Feature Map (synthesis → SME, estrategia → PREMIUM, etc.)

---

## Arquivos que mudam, por fase

```
Fase 0 (docs apenas):
  docs/FEATURE_MAP.md                              (novo)
  docs/TOOL_INVENTORY.md                           (novo)

Fase 1 (nova lib):
  libs/blu_tool_registry/src/blu_tool_registry/features.py          (novo)
  libs/blu_tool_registry/src/blu_tool_registry/resource_resolver.py (novo)
  libs/blu_tool_registry/src/blu_tool_registry/__init__.py          (patch)
  libs/blu_tool_registry/tests/test_feature_registry.py             (novo)

Fase 2 (factory):
  services/agent_api/src/agent_api/core/factory.py   (patch: 3 pontos)
  services/agent_api/src/agent_api/core/routines.py  (patch: 1 ponto)

Fase 3 (routing):
  services/agent_api/src/agent_api/core/service.py          (patch: 3 funções)
  services/agent_api/src/agent_api/api/agents_router.py     (patch: 1 endpoint)

Fase 4 (tool_pool):
  services/tool_pool_api/src/tool_pool_api/server/resources.py  (patch: 4 pontos)

Fase 5 (cleanup):
  libs/blu_tool_registry/src/blu_tool_registry/tier_validator.py   (patch: ENTERPRISE + features)
  libs/blu_agent_framework/src/blu_agent_framework/registry.py     (patch: tier_required por agente)
```

**Total: 14 arquivos** — nenhuma migration de banco necessária.

---

## Riscos e decisões abertas

| Risco | Mitigação |
|-------|-----------|
| Feature Map errado — tool crítica fora do Feature | Fase 0 obrigatória antes de qualquer código |
| Regressão no PREMIUM (que hoje funciona) | Testes de routing Layer 1 existentes servem como regression suite |
| `clientes_blu.available_tools` — override por cliente | Decisão: implementar override opcional no ResourceResolver ou deprecar a coluna |
| Agents sem Feature mapeada ficam sem tools | Fallback: se slug não está em nenhuma Feature, usar `AgentTypeConfig.enabled_tools` direto |
| Cache de graphs no factory é por tier — após mudança, tier ainda é chave válida | OK — a mudança está no que entra no build, não na chave de cache |

---

## O que NÃO muda

- Schema do banco — nenhuma migration necessária
- API pública (`/v1/chat`, `/v1/sessions`, `/v1/catalog`) — contratos idênticos
- Langfuse traces — instrumentação não muda
- `AgentTypeConfig.enabled_tools` — permanece como "o que o agente sabe usar" (candidatos)
  O `ResourceResolver` usa isso como input, não substitui

---

## Sequência recomendada de execução

```
Fase 0: Auditoria de tools (1–2 dias, pode fazer em paralelo com outros trabalhos)
  ↓
Fase 1: FeatureRegistry + testes isolados (2–3 dias)
  ↓ validar: testes passam, nada mudou em produção
Fase 2: factory.py (1–2 dias)
  ↓ validar: Layer 1 dos testes de routing ainda 20/20
Fase 3: service.py routing (1 dia)
  ↓ validar: Layer 2 edge cases
Fase 4: tool_pool_api (1 dia)
  ↓ validar: tools corretas chegam ao MCP para cada tier
Fase 5: cleanup (1 dia)
```

**Estimativa total: 7–10 dias** sem paralelismo, 5–7 dias com dois devs.
