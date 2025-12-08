# vizu_elicitation_service

Human-in-the-loop elicitation service for Vizu agents.

## Purpose

This library implements the elicitation pattern that allows agents to:
1. Pause execution to wait for user input
2. Store state in Redis while waiting
3. Resume execution when user responds
4. Handle various response types (confirmation, selection, text)

## Features

### Elicitation Types
- **CONFIRMATION** - Yes/No questions
- **SELECTION** - Multiple choice options
- **TEXT_INPUT** - Free-form text input
- **DATE_TIME** - Date and time selection

### Core Components

#### ElicitationManager
Central coordinator for elicitation flows.

```python
from vizu_elicitation_service import ElicitationManager

manager = ElicitationManager(redis_client)

# Create a confirmation
elicitation = manager.create_confirmation(
    message="Confirm appointment for Jan 15?",
    tool_name="schedule_appointment",
    tool_args={"date": "2025-01-15", "time": "14:00"},
)

# Store for later
await manager.store_pending(session_id, elicitation)

# When user responds
response = await manager.retrieve_pending(session_id)
result = manager.process_response(response, user_input)
```

#### PendingElicitationStore
Redis-backed storage for pending elicitations.

```python
from vizu_elicitation_service import PendingElicitationStore

store = PendingElicitationStore(redis_client, ttl_seconds=3600)

# Store
await store.save(session_id, elicitation)

# Retrieve
pending = await store.get(session_id)

# Clear
await store.delete(session_id)
```

#### ElicitationResponseHandler
Process and validate user responses.

```python
from vizu_elicitation_service import ElicitationResponseHandler

handler = ElicitationResponseHandler()

# Validate response
is_valid, error = handler.validate(elicitation, user_response)

# Normalize response
normalized = handler.normalize(elicitation, user_response)
```

### Exception Handling

```python
from vizu_elicitation_service import ElicitationRequired

# In a tool, raise to pause execution
raise ElicitationRequired(
    type=ElicitationType.CONFIRMATION,
    message="Confirm?",
    tool_name="my_tool",
    tool_args={"arg": "value"},
)
```

## Usage with LangGraph

```python
async def execute_tools_node(state: AgentState) -> AgentState:
    try:
        result = await tool.execute(**args)
        return {"tool_result": result}
    except ElicitationRequired as e:
        return {
            "pending_elicitation": e.to_pending_elicitation(),
            "messages": [AIMessage(content=e.message)],
        }
```

## Dependencies

- `vizu_models` - ElicitationType, ElicitationOption enums
- `redis` - Storage backend
