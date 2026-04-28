# Agentic System Design

## Overview

This guide documents the agent system patterns that are actually visible in `blu-mono`: LangGraph supervisors, worker delegation, session-scoped standalone agents, shared state reducers, and context/prompt assembly before execution.

## Core Principles

### Start from the owning runtime

There is no single agent architecture for the entire repo. The main sampled patterns are:

- `atendente_core`: supervisor + worker delegation + parallel fan-out
- `blu_agent_framework`: reusable agent builder/runtime primitives
- `standalone_agent_api`: catalog-driven session agents with factory-based context injection

### Keep orchestration, context, and prompt responsibilities separate

- graph design decides routing and execution order
- services/factories assemble context and metadata
- prompt management renders prompt text
- tools perform side effects or retrieval

### Session and tenant scope are first-class design constraints

Standalone agents in particular depend on strict separation between client-scoped context and session-scoped uploaded data, documents, and OAuth metadata.

## Core Repo Patterns

### Pattern 1: Supervisor with parallel tool fan-out

In `atendente_core`, the supervisor can emit multiple tool calls that are dispatched via LangGraph `Send` objects and merged back through reducers.

Use when:

- the LLM selects multiple independent tools
- worker delegation or MCP calls can happen concurrently

Key characteristics:

- loop guards such as max tool turns
- pending elicitation can short-circuit the normal loop
- tool results accumulate into shared message history

### Pattern 2: Worker delegation instead of giving every tool to one agent

The supervisor sees delegation tools like `delegate_to_*`, while specialists own the detailed toolchains. This keeps top-level prompts smaller and clearer.

### Pattern 3: Session-built standalone agents

`standalone_agent_api` builds agents from:

- catalog configuration
- session-collected context
- uploaded file/document metadata
- tenant/client context
- prompt fragments or Langfuse prompt names

Use this when agent behavior must be customized per session without creating a new service.

### Pattern 4: Reducer-based state accumulation

Message history and tool results are merged through reducers instead of hand-written fan-in glue in every node.

This is a key design constraint when editing graph behavior.

## Best Practices

### Keep graph nodes narrow

Nodes should own one clear responsibility: supervisor decision, tool execution, elicitation wait, or response synthesis.

### Build expensive resources once when the service already does

The repo already uses singleton-like graph/factory/checkpointer patterns in some services. Reuse them where appropriate instead of rebuilding per request.

### Attach context before execution, not during random tool calls

The factory/service layer should inject session and tenant metadata before the graph starts, so tools and prompts receive a coherent view of the world.

### Use prompt changes to refine policy, not to repair graph design

If the agent cannot decide between tools cleanly, the fix may belong in tool availability, state shape, or delegation boundaries.

## Anti-Patterns To Avoid

### One giant agent with every tool and every rule

This repo already demonstrates better separation through worker delegation and catalog-driven enabled tools.

### Mixing tenant-scoped and session-scoped context casually

Uploaded files/documents are session-specific; company profile and tier are client-scoped. Mixing them carelessly weakens isolation and reasoning clarity.

### Replacing graph structure with prompt instructions alone

Parallel fan-out, elicitation pauses, and tool loops are graph concerns.

## Unknowns To Verify

- Some agent families outside the sampled services may use different graph conventions.
- The long-term unification path between `atendente_core` and `blu_agent_framework` is not fully documented here.

## Further Reading

- `/memories/repo/agent-execution-pipeline.md`
- `/memories/repo/agent-configuration-context-flow.md`
- `services/atendente_core/src/atendente_core/core/`
- `services/standalone_agent_api/src/standalone_agent_api/core/`
- `libs/blu_agent_framework`
