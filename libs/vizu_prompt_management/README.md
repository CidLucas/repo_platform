# vizu_prompt_management

Simplified prompt management for Vizu services using Langfuse as source of truth.

## Purpose

This library centralizes all prompt-related functionality:
- Loading prompts from Langfuse (primary) with builtin fallback
- Variable substitution via Langfuse's `{{variable}}` syntax
- Redis caching via ContextService
- Unified dynamic prompt building

## Architecture (Simplified)

```
1. Langfuse (source of truth)
   - Version control via Langfuse UI
   - A/B testing via labels (production, staging, etc.)
   - Variables: {{nome_empresa}}, {{tools_description}}, etc.

2. Builtin templates (fallback)
   - Jinja2-based rendering for {% if %}, {% for %}
   - Used when Langfuse is unavailable
```

## Features

### Prompt Loader (`loader.py`)
- Load prompts from Langfuse with SDK's native `get_prompt()` + `compile()`
- Fallback to builtin templates
- Circuit breaker for connection failures
- Returns `LoadedPrompt` with `langfuse_prompt` for trace linking

### Dynamic Builder (`dynamic_builder.py`)
- `build_prompt()` - Unified entry point for all prompts
- `build_prompt_full()` - Returns full `LoadedPrompt` with metadata
- Redis caching via ContextService

### Templates (`templates.py`)
- Built-in prompt templates (system prompts, RAG, etc.)
- Jinja2-based rendering for complex logic

### Variables (`variables.py`)
- Variable extraction from client context (`SafeClientContext`)
- Safe variable substitution
- Default value handling

## Installation

```bash
poetry add vizu_prompt_management
```

## Usage

### Load Prompt (Async)
```python
from vizu_prompt_management import build_prompt

# Simple usage
content = await build_prompt(
    name="atendente/default",
    variables={"nome_empresa": "Acme", "tools_description": "..."},
)

# With Redis caching
content = await build_prompt(
    name="atendente/default",
    variables={"nome_empresa": "Acme"},
    context_service=ctx_service,
)

# With custom Langfuse label
content = await build_prompt(
    name="atendente/default",
    variables={"nome_empresa": "Acme"},
    langfuse_label="staging",
)
```

### Get Full LoadedPrompt (for trace linking)
```python
from vizu_prompt_management import build_prompt_full

loaded = await build_prompt_full(
    name="atendente/default",
    variables={"nome_empresa": "Acme"},
)

# Use for trace linking
print(loaded.langfuse_prompt)  # Langfuse prompt object
print(loaded.get_trace_metadata())  # {prompt_name, prompt_version, ...}
```

### Direct Loader Access
```python
from vizu_prompt_management import PromptLoader

loader = PromptLoader()
loaded = await loader.load("atendente/default", variables={"nome_empresa": "Vizu"})
print(loaded.content)
```

### Builtin Templates (Sync)
```python
from vizu_prompt_management import build_prompt_sync

# For contexts where async is not available
content = build_prompt_sync(
    name="atendente/default",
    variables={"nome_empresa": "Vizu"},
)
```

### Render with Jinja2 (for builtin templates)
```python
from vizu_prompt_management import TemplateRenderer

renderer = TemplateRenderer()
content = renderer.render(
    template="Hello {{ nome_empresa }}!",
    variables={"nome_empresa": "Vizu"}
)
# Output: "Hello Vizu!"
```

## Dependencies

- `vizu_observability_bootstrap` - Langfuse client
- `vizu_context_service` - Redis caching (optional)
- `jinja2` - Template rendering for builtins
