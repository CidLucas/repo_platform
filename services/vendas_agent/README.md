# Vendas Agent

Sales agent for B2C order processing, built using the `vizu_agent_framework`.

## Architecture

This agent demonstrates the **95% code reuse** goal of the multi-agent architecture:

- **~150 lines of agent-specific code** vs 1200+ lines in the old monolithic approach
- Uses `AgentBuilder` from `vizu_agent_framework` for graph construction
- Dynamic tool loading via `vizu_tool_registry`
- Elicitation handling via `vizu_elicitation_service`

## Features

- **Sales Pipeline Elicitation**: Gathers customer needs before recommending products
- **Product Recommendations**: Suggests products based on customer context
- **Order Processing**: Handles order creation and payment flow
- **Discount Management**: Tier-based discount availability

## Running Locally

```bash
cd services/vendas_agent
poetry install
cp .env.example .env
# Edit .env with your settings
poetry run uvicorn src.vendas_agent.main:app --reload --port 8001
```

## Running with Docker

```bash
docker compose up vendas_agent
```

## API Endpoints

### POST /chat
Main chat endpoint for sales conversations.

```json
{
    "message": "Quero comprar um produto",
    "session_id": "unique-session-id"
}
```

### GET /health
Health check endpoint.

### GET /context
Returns client context with available tools and features.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `MCP_SERVER_URL` | Tool Pool API URL | `http://tool_pool_api:8000/mcp/v1` |
| `LLM_PROVIDER` | LLM provider (openai, ollama, etc.) | `openai` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry endpoint | `http://localhost:4317` |

## Differences from Atendente Core

| Aspect | Atendente Core | Vendas Agent |
|--------|---------------|--------------|
| Role | Customer Support | Sales Representative |
| Elicitation | Support Triage | Sales Pipeline |
| Max Turns | 20 | 15 |
| Focus | Problem resolution | Product sales |
