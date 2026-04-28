# Prompt Engineering Patterns

## Overview

These prompt patterns are adapted to `blu-mono`'s actual prompt stack: Langfuse-managed prompts, fragment composition, builtin fallbacks in selected paths, and runtime variables injected from client/session/tool context.

## Core Principles

### Prompt text should encode behavior policy, not workflow control

If the prompt starts deciding retry loops, fan-out behavior, or routing between specialists, the workflow likely belongs in LangGraph or service code instead.

### Prefer shared prompt loaders and composition paths

This repo already has shared prompt-management infrastructure. Reuse it before adding direct SDK prompt loading or inline string assembly.

### Prompt variables must reflect real repo entities

Typical variables in this repo include:

- `nome_empresa`
- `context_sections` or client context sections
- `tools_description`
- session-collected context
- file and document metadata
- worker or agent identity fields

## Common Repo Patterns

### Pattern 1: Langfuse-first with stable labels

The sampled prompt-management stack expects production-labeled prompts as the live contract.

Use when:

- the prompt is runtime-configurable
- operators or admin tools need to inspect or update prompt versions
- the prompt belongs to a reusable agent or tool flow

### Pattern 2: Fragment composition for reusable agent families

Standalone agents can compose prompts from multiple fragments instead of one monolithic instruction block. Use this when multiple agents share base tone, tool rules, output constraints, or onboarding behavior.

### Pattern 3: Builtin fallback only where the loader already supports it

Builtin templates are useful for resilience and local defaults, but they are not a license to duplicate the same prompt logic in two places indefinitely.

Use builtin fallback when:

- the shared loader already implements it
- the service must remain usable if Langfuse is unavailable

Avoid it when:

- it creates two competing sources of truth for the same live prompt

### Pattern 4: Prompt variables are assembled from context and metadata, not improvised ad hoc

Examples from repo patterns:

- client context from `ContextService`
- collected onboarding/session context
- uploaded file and document summaries
- tier or enabled tool scopes
- worker-specific tool descriptions

## Best Practices

### Keep prompt structure aligned with graph/tool structure

If the graph fans out to specialist workers, the supervisor prompt should know only delegation surfaces, not every specialist implementation detail.

### Keep prompts grounded in the actual schema and tools

For SQL, RAG, onboarding, or reporting prompts, use the repo's real table names, tool names, and context field names. Generic examples drift quickly.

### Change the smallest prompt surface that can explain the behavior

If a problem is isolated to one worker, one fragment, or one prompt variable, do not rewrite the entire system prompt stack.

### Preserve prompt names where downstream tooling depends on them

Scripts, admin routes, or shared loaders may expect stable prompt names and labels.

## Anti-Patterns To Avoid

### Hiding missing context assembly behind prompt instructions

If a prompt is compensating for missing `client_context`, missing file metadata, or absent tool descriptions, fix the assembly path first.

### Encoding branching workflow in the prompt when the graph should own it

Prompts should guide decisions, not emulate a state machine the graph can represent directly.

### Copying prompt text between Langfuse and builtin templates without a migration plan

That creates silent drift.

## Unknowns To Verify

- Some prompt families in the repo may still be partially documented only in Langfuse, not in code.
- Not every fragment composition path was sampled here.

## Further Reading

- `libs/blu_prompt_management`
- `/memories/repo/langfuse-prompts.md`
- `/memories/repo/agent-configuration-context-flow.md`
