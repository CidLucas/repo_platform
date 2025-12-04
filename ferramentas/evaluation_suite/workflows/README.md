# Evaluation Suite - Workflow Experiments

This directory contains LangGraph workflows and their associated datasets for evaluation experiments.

## Structure

Each workflow experiment should be organized as follows:

```
workflows/
├── <workflow_name>/
│   ├── workflow.py        # LangGraph workflow definition (v1 - direct Ollama)
│   ├── workflow_v2.py     # Modernized workflow with vizu_llm_service
│   ├── evaluator.py       # Optional: Custom evaluator functions
│   ├── manifest.yaml      # Experiment configuration (v1)
│   ├── manifest_v2.yaml   # Experiment configuration (v2)
│   ├── run_experiment.py  # Standalone runner
│   └── data/
│       └── *.csv          # Test datasets
```

## Running Experiments

### Quick Start - V1 (Legacy Direct Ollama)

```bash
# Run workflow experiment - outputs results to JSON file
make experiment-workflow-local

# Run with database storage (saves to PostgreSQL)
make experiment-workflow-db

# Run with Langfuse tracing (observability)
make experiment-workflow-langfuse

# Run with both DB + Langfuse
make experiment-workflow-full
```

### Quick Start - V2 (Recommended - Multi-Provider Support)

The V2 workflows use `vizu_llm_service` for unified LLM access:

```bash
# Run with local Ollama (default)
make experiment-workflow-v2

# Run with Ollama Cloud
make experiment-workflow-v2-cloud

# Run with MCP tools enabled (connects to tool_pool_api)
make experiment-workflow-v2-mcp

# Run with full options (DB + Langfuse + custom provider)
make experiment-workflow-v2-full LLM_PROVIDER=openai
```

### Supported LLM Providers (V2)

| Provider | Env Variable | Description |
|----------|-------------|-------------|
| `ollama` | `LLM_PROVIDER=ollama` | Local Ollama container (default) |
| `ollama_cloud` | `LLM_PROVIDER=ollama_cloud` | Ollama Cloud API |
| `openai` | `LLM_PROVIDER=openai` | OpenAI API |
| `anthropic` | `LLM_PROVIDER=anthropic` | Anthropic Claude API |
| `google` | `LLM_PROVIDER=google` | Google Gemini API |

Required API keys (set in `.env`):
- `OLLAMA_CLOUD_API_KEY` - For Ollama Cloud
- `OPENAI_API_KEY` - For OpenAI
- `ANTHROPIC_API_KEY` - For Anthropic
- `GOOGLE_API_KEY` - For Google Gemini

### MCP Integration (V2)

V2 workflows can optionally connect to the `tool_pool_api` MCP server to use:
- RAG search tools
- SQL query tools
- Google integrations
- Other registered tools

```bash
# Enable MCP tools
ENABLE_MCP_TOOLS=true make experiment-workflow-v2

# Or use the dedicated target
make experiment-workflow-v2-mcp
```

### Output

Results are **always saved to a JSON file** in the workflow directory:
```
ferramentas/evaluation_suite/workflows/boleta_trader/results_20231203_214055.json
```

Example output:
```json
{
  "manifest_name": "boleta_trader_extraction_v2",
  "run_id": "abc-123-def",
  "total_cases": 3,
  "success_cases": 3,
  "failure_cases": 0,
  "error_cases": 0,
  "results": [
    {
      "test_id": "trigger_4_1004",
      "success": true,
      "boleta_formatada": "✅ **CONFIRMATION TICKET** ...",
      "dados_extraidos": {"valor_cotacao": 5.493, "valor_total": 130000.0}
    }
  ]
}
```

### Storage Options

| Flag | Description |
|------|-------------|
| (none) | JSON output only |
| `--db` | Save to PostgreSQL via `vizu_db_connector` |
| `--langfuse` | Enable Langfuse tracing (requires env vars) |
| `--db --langfuse` | Both database and Langfuse |

### Environment Variables

For LLM provider (V2):
- `LLM_PROVIDER` - Provider to use (ollama, ollama_cloud, openai, anthropic, google)
- Provider-specific API keys (see above)

For database storage:
- `DATABASE_URL` - PostgreSQL connection string

For Langfuse tracing:
- `LANGFUSE_HOST` - Langfuse server URL (e.g., `http://localhost:3000`)
- `LANGFUSE_PUBLIC_KEY` - API public key
- `LANGFUSE_SECRET_KEY` - API secret key

## Creating a New Workflow Experiment

1. **Create directory structure:**
   ```bash
   mkdir -p ferramentas/evaluation_suite/workflows/my_workflow/data
   ```

2. **Create workflow.py:**
   ```python
   from langgraph.graph import StateGraph, END
   from pydantic import BaseModel, Field

   def get_workflow(checkpointer=None):
       workflow = StateGraph(MyState)
       # ... add nodes and edges
       return workflow.compile(checkpointer=checkpointer)
   ```

3. **Create evaluator.py (optional):**
   ```python
   def evaluate_result(run) -> dict:
       # Custom evaluation logic
       return {"score": 0.8, "details": "..."}
   ```

4. **Create manifest.yaml:**
   ```yaml
   name: my_experiment
   version: "1.0.0"
   description: Description of the experiment

   workflow_path: ferramentas.evaluation_suite.workflows.my_workflow.workflow
   workflow_function: get_workflow

   data_file: ferramentas/evaluation_suite/workflows/my_workflow/data/test.csv
   message_column: message
   conversation_group_column: conversation_id
   sender_column: sender

   trigger_keywords: ["keyword1", "keyword2"]

   evaluator_path: ferramentas.evaluation_suite.workflows.my_workflow.evaluator
   evaluator_function: evaluate_result
   ```

5. **Add a Makefile target** (or reuse the existing runner):
   ```makefile
   experiment-my-workflow:
   	@docker exec -e PYTHONPATH=/app:/app/ferramentas:/app/libs/vizu_db_connector/src:/app/libs/vizu_models/src \
   		-w /app \
   		vizu_atendente_core python -m ferramentas.evaluation_suite.workflows.my_workflow.run_experiment \
   		ferramentas/evaluation_suite/workflows/my_workflow/manifest.yaml
   ```

## Available Workflows

### boleta_trader

Extracts trading tickets (boletas) from WhatsApp conversations.

- **Trigger keywords:** `trava`, `fecha`, `fechado`, `fechamos`, `travo`, `fecho`
- **Extracts:** Quote value (cotação), Volume (valor_total)
- **LLM:** Ollama (llama3.2 by default)

**Usage:**
```bash
# Quick run (JSON output)
make experiment-workflow-local

# With database storage
make experiment-workflow-db

# With observability
make experiment-workflow-langfuse
```

## Manifest Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Experiment identifier |
| `version` | No | Semantic version (default: 1.0.0) |
| `description` | No | Human-readable description |
| `workflow_path` | Yes | Python module path to workflow file |
| `workflow_function` | No | Function name (default: `get_workflow`) |
| `data_file` | Yes | Path to CSV test data |
| `message_column` | Yes | Column containing message text |
| `conversation_group_column` | Yes | Column to group messages into conversations |
| `sender_column` | Yes | Column with sender identifier |
| `trigger_keywords` | No | Words that trigger workflow execution |
| `evaluator_path` | No | Python module path to evaluator |
| `evaluator_function` | No | Evaluator function name |
| `ollama_base_url` | No | Ollama server URL (default: http://localhost:11434) |
| `ollama_model` | No | Model to use (default: llama3.2) |
| `timeout_seconds` | No | Max execution time per case (default: 120) |
| `tags` | No | List of tags for experiment organization |

## Troubleshooting

### Langfuse Not Working

1. Start Langfuse locally:
   ```bash
   cd langfuse && docker compose up -d
   ```

2. Access at http://localhost:3000 and create a project to get API keys

3. Set environment variables in `.env`:
   ```
   LANGFUSE_HOST=http://host.docker.internal:3000
   LANGFUSE_PUBLIC_KEY=pk-...
   LANGFUSE_SECRET_KEY=sk-...
   ```

### Database Errors

Ensure `DATABASE_URL` is set and the database is running:
```bash
docker compose up postgres -d
```
