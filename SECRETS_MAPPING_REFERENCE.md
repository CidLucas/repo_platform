# Service-to-Secrets Mapping Reference

Quick lookup table showing which secrets each service actually needs.

## Service Directory

### Agent Services

#### atendente_core (Main LLM Agent)
```
Required:
  - DATABASE_URL        (PostgreSQL for context/history)
  - REDIS_URL          (State checkpointing)
  
Optional:
  - OLLAMA_BASE_URL    (For local model inference)
  - LANGCHAIN_API_KEY  (LangSmith observability)
  - TWILIO_AUTH_TOKEN  (If using Twilio integration)
  - OTEL_EXPORTER_OTLP_ENDPOINT (Observability)
```

#### tool_pool_api (MCP Server - Tools & Integrations)
```
Required:
  - DATABASE_URL                (PostgreSQL)
  - REDIS_URL                   (Caching, session)
  - MCP_AUTH_GOOGLE_CLIENT_ID   (OAuth for tool integration)
  - CREDENTIALS_ENCRYPTION_KEY  (Encrypts user OAuth tokens)
  
Optional:
  - MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV (Development only)
  - OTEL_EXPORTER_OTLP_ENDPOINT (Observability)
  - SENTRY_DSN                   (Error tracking)
```

#### vendas_agent (Sales Agent)
```
Required:
  - DATABASE_URL  (PostgreSQL)
  - REDIS_URL     (State, checkpointing)
  
Optional:
  - MCP_SERVER_URL        (Internal discovery: http://tool_pool_api:9000/mcp/)
  - LANGFUSE_PUBLIC_KEY   (LLM observability)
  - LANGFUSE_SECRET_KEY   (LLM observability)
  - LANGFUSE_HOST         (Langfuse instance)
  - OTEL_EXPORTER_OTLP_ENDPOINT (Observability)
```

#### support_agent (Support Agent)
```
Required:
  - DATABASE_URL  (PostgreSQL)
  - REDIS_URL     (State, checkpointing)
  
Optional:
  - MCP_SERVER_URL        (Internal discovery: http://tool_pool_api:9000/mcp/)
  - LANGFUSE_PUBLIC_KEY   (LLM observability)
  - LANGFUSE_SECRET_KEY   (LLM observability)
  - LANGFUSE_HOST         (Langfuse instance)
  - OTEL_EXPORTER_OTLP_ENDPOINT (Observability)
```

### API Services

#### analytics_api (Metrics & Analytics)
```
Required:
  - DATABASE_URL  (PostgreSQL for metrics aggregation)
  - REDIS_URL     (Cache: 5-min TTL for dashboard queries)
  
Optional:
  - GOOGLE_CLIENT_ID      (OAuth for analytics dashboard)
  - GOOGLE_CLIENT_SECRET  (OAuth)
  - GOOGLE_REDIRECT_URI   (OAuth callback)
  - OTEL_EXPORTER_OTLP_ENDPOINT (Observability)
```

#### file_upload_api (File Upload Handler)
```
Required:
  - GCP_PROJECT_ID    (Google Cloud project)
  - GCS_BUCKET_NAME   (Hardcoded or config)
  - PUBSUB_TOPIC_ID   (Hardcoded or config)
  
Optional:
  - OTEL_EXPORTER_OTLP_ENDPOINT (Observability)
```

#### data_ingestion_api (Data Import)
```
Required:
  - DATABASE_URL        (PostgreSQL)
  - SUPABASE_URL        (Supabase instance)
  - SUPABASE_SERVICE_KEY (Service role key)
```

### Worker Services

#### file_processing_worker (File Processing & Embedding)
```
Required:
  - GCP_PROJECT_ID           (Google Cloud project)
  - GCS_BUCKET_NAME          (Hardcoded or config)
  - PUBSUB_SUBSCRIPTION_ID   (Hardcoded or config)
  
Auto-discovered:
  - QDRANT_HOST    (From service discovery: qdrant_client)
  - QDRANT_PORT    (From service discovery)
  - QDRANT_COLLECTION_NAME (Config: "documents")
```

#### data_ingestion_worker (Data Processing)
```
Required:
  - DATABASE_URL  (PostgreSQL for worker jobs)
```

#### embedding_service (Embeddings)
```
No secrets required!
Local inference using transformer models.

Optional config (hardcoded):
  - EMBEDDING_MODEL_NAME:   "intfloat/multilingual-e5-large"
  - EMBEDDING_VECTOR_SIZE:  1024
  - EMBEDDING_MODEL_DEVICE: "cpu" (or "cuda")
```

## Dependency Graph

```
GitHub Secrets (13 standardized)
    ↓
    ├→ DATABASE_URL
    │   ├→ atendente_core
    │   ├→ tool_pool_api
    │   ├→ vendas_agent
    │   ├→ support_agent
    │   ├→ analytics_api
    │   ├→ data_ingestion_api
    │   └→ data_ingestion_worker
    │
    ├→ REDIS_URL
    │   ├→ atendente_core
    │   ├→ tool_pool_api
    │   ├→ vendas_agent
    │   ├→ support_agent
    │   └→ analytics_api
    │
    ├→ GCP_PROJECT_ID
    │   ├→ file_upload_api
    │   └→ file_processing_worker
    │
    ├→ MCP_AUTH_GOOGLE_CLIENT_ID
    │   └→ tool_pool_api
    │
    ├→ CREDENTIALS_ENCRYPTION_KEY
    │   └→ tool_pool_api
    │
    ├→ SUPABASE_URL & SUPABASE_SERVICE_KEY
    │   └→ data_ingestion_api
    │
    ├→ LANGFUSE_*
    │   ├→ vendas_agent
    │   └→ support_agent
    │
    ├→ OLLAMA_BASE_URL
    │   └→ atendente_core
    │
    └→ GRAFANA_API_KEY
        └→ Observability dashboards
```

## Startup Checklist by Service

### To run atendente_core:
- [ ] DATABASE_URL
- [ ] REDIS_URL
- [ ] ✅ (others optional)

### To run tool_pool_api:
- [ ] DATABASE_URL
- [ ] REDIS_URL
- [ ] MCP_AUTH_GOOGLE_CLIENT_ID
- [ ] CREDENTIALS_ENCRYPTION_KEY
- [ ] ✅ (others optional)

### To run vendas_agent:
- [ ] DATABASE_URL
- [ ] REDIS_URL
- [ ] ✅ (others optional)

### To run support_agent:
- [ ] DATABASE_URL
- [ ] REDIS_URL
- [ ] ✅ (others optional)

### To run analytics_api:
- [ ] DATABASE_URL
- [ ] REDIS_URL
- [ ] ✅ (others optional)

### To run file_upload_api:
- [ ] GCP_PROJECT_ID
- [ ] ✅ (others optional)

### To run file_processing_worker:
- [ ] GCP_PROJECT_ID
- [ ] ✅ (others optional)

### To run data_ingestion_api:
- [ ] DATABASE_URL
- [ ] SUPABASE_URL
- [ ] SUPABASE_SERVICE_KEY
- [ ] ✅ (others optional)

### To run data_ingestion_worker:
- [ ] DATABASE_URL
- [ ] ✅ (others optional)

### To run embedding_service:
- [ ] ✅ No secrets needed!

## Minimal Production Set (Absolute Minimum)

If you only want core functionality running:

```
Critical 5:
  - DATABASE_URL
  - REDIS_URL
  - GCP_PROJECT_ID
  - SUPABASE_URL
  - SUPABASE_SERVICE_KEY

Then add:
  - GCP_SA_EMAIL (for deploy)
  - GCP_SA_KEY (for deploy)
  - MCP_AUTH_GOOGLE_CLIENT_ID (if using tools)
  - CREDENTIALS_ENCRYPTION_KEY (if using tools)
```

This 8-secret set enables: agents, tools, data ingestion, and worker processing.

