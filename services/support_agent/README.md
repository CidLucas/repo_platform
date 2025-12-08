# Support Agent

Technical support agent for issue classification and resolution, built using the `vizu_agent_framework`.

## Architecture

This agent demonstrates the **95% code reuse** goal of the multi-agent architecture:

- **~150 lines of agent-specific code** vs 1200+ lines in the old monolithic approach
- Uses `AgentBuilder` from `vizu_agent_framework` for graph construction
- Dynamic tool loading via `vizu_tool_registry`
- Elicitation handling via `vizu_elicitation_service`

## Features

- **Issue Classification**: Classifies incoming support requests by category and severity
- **Knowledge Base Search**: Uses RAG to find relevant documentation
- **Escalation Handling**: Manages ticket escalation to human agents
- **Resolution Tracking**: Tracks issue resolution status

## Running Locally

```bash
cd services/support_agent
poetry install
cp .env.example .env
# Edit .env with your settings
poetry run uvicorn src.support_agent.main:app --reload --port 8004
```

## Running with Docker

```bash
docker compose up support_agent
```

## API Endpoints

### POST /chat
Main chat endpoint for support conversations.

```json
{
    "message": "Meu sistema está dando erro",
    "session_id": "unique-session-id"
}
```

### POST /ticket
Create a support ticket from the conversation.

```json
{
    "session_id": "unique-session-id",
    "priority": "high"
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

## Differences from Other Agents

| Aspect | Atendente Core | Vendas Agent | Support Agent |
|--------|---------------|--------------|---------------|
| Role | Customer Support | Sales | Technical Support |
| Elicitation | support_triage | sales_pipeline | issue_classification |
| Max Turns | 20 | 15 | 25 |
| Focus | General support | Product sales | Technical issues |
