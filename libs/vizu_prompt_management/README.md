# vizu_prompt_management

Centralized prompt management for Vizu services with versioning, templating, and MCP integration.

## Purpose

This library centralizes all prompt-related functionality:
- Loading prompts from database and files
- Versioning and A/B testing of prompts
- Variable substitution with Jinja2
- Client-specific prompt overrides
- MCP resource integration

## Features

### Prompt Loader (`loader.py`)
- Load prompts from database (`PromptTemplate` model)
- Fallback to default templates
- Client-specific override support
- Version pinning

### Prompt Manager (`manager.py`)
- Version management and comparison
- Active version tracking
- Rollback support

### Templates (`templates.py`)
- Built-in prompt templates (system prompts, RAG, etc.)
- Template inheritance
- Jinja2-based rendering

### Variables (`variables.py`)
- Variable extraction from client context
- Safe variable substitution
- Default value handling

### MCP Builder (`mcp_builder.py`)
- Register prompts with FastMCP
- Dynamic prompt discovery
- Parameterized prompts

## Installation

```bash
poetry add vizu_prompt_management
```

## Usage

### Load Prompt from Database
```python
from vizu_prompt_management import PromptLoader

loader = PromptLoader(db_session)
prompt = await loader.load("atendente/system", cliente_id=cliente_id)
print(prompt.content)
```

### Render with Variables
```python
from vizu_prompt_management import TemplateRenderer

renderer = TemplateRenderer()
content = renderer.render(
    template="Hello {{ nome_empresa }}!",
    variables={"nome_empresa": "Vizu"}
)
# Output: "Hello Vizu!"
```

### Register with MCP
```python
from vizu_prompt_management import MCPPromptBuilder

builder = MCPPromptBuilder(mcp, loader)
builder.register_standard_prompts()
builder.register_from_database(["atendente/system", "rag/query"])
```

### Built-in Templates
```python
from vizu_prompt_management.templates import (
    ATENDENTE_SYSTEM_V1,
    ATENDENTE_SYSTEM_V2,
    RAG_QUERY_PROMPT,
)
```

## Dependencies

- `vizu_models` - PromptTemplate model
- `vizu_db_connector` - Database access
- `jinja2` - Template rendering
