---
name: senior-prompt-engineer
description: World-class prompt engineering skill for LLM optimization, prompt patterns, structured outputs, and AI product development. Expertise in Claude, GPT-4, prompt design patterns, few-shot learning, chain-of-thought, and AI evaluation. Includes RAG optimization, agent design, and LLM system architecture. Use when building AI products, optimizing LLM performance, designing agentic systems, or implementing advanced prompting techniques.
---

# Senior Prompt Engineer

Repo-adapted prompt and agent design guidance for `vizu-mono`.

This skill is tuned to the prompt and agent architecture that actually exists in this monorepo today:

- shared prompt loading and composition through `libs/vizu_prompt_management`
- Langfuse-first prompt management with production labels and builtin fallback where supported
- LangGraph-based agent execution in `services/atendente_core` and `libs/vizu_agent_framework`
- standalone agent factory/session flow in `services/standalone_agent_api`
- context injection through `vizu_context_service`
- tool execution through MCP and worker delegation patterns

Use this skill when you are:

- designing or refactoring system prompts, prompt fragments, or agent prompt variables
- changing agent graph behavior, tool routing, or worker delegation logic
- evaluating prompt quality for SQL, RAG, reporting, or onboarding/config-helper flows
- adding or reviewing standalone agents from catalog definition through runtime invocation
- deciding whether logic belongs in prompts, graph state, tools, or context assembly

## Core Expertise

This skill covers the repo's concrete prompt and agent concerns:

- prompt composition from fragments and variables
- Langfuse prompt lifecycle and production-label usage
- agent state design and context isolation
- fan-out/fan-in tool execution in LangGraph
- evaluation of prompt changes through task-specific tests and runtime traces
- tradeoffs between prompt instructions, tool contracts, and structured outputs

## Tech Stack

**Primary language:** Python
**Prompt management:** Langfuse + `vizu_prompt_management`
**Agent runtime:** LangGraph + `vizu_agent_framework`
**Observability:** Langfuse + `vizu_observability_bootstrap`
**Context layer:** `vizu_context_service`
**Data/tool surfaces:** Supabase, analytics SQL, MCP tools, worker delegation, RAG
**Primary services:** `atendente_core`, `standalone_agent_api`, `tool_pool_api`

## Reference Documentation

### 1. Prompt Engineering Patterns

See `references/prompt_engineering_patterns.md` for the repo's actual prompt composition, fragment, fallback, and variable-injection patterns.

### 2. Llm Evaluation Frameworks

See `references/llm_evaluation_frameworks.md` for how to validate prompt and agent behavior in this repo without falling back to vague manual judgment.

### 3. Agentic System Design

See `references/agentic_system_design.md` for the concrete graph, factory, context, and tool-routing patterns already in use.

## Current Repo Patterns

### Pattern 1: Prompt logic is shared infrastructure, not scattered strings

- Prefer `vizu_prompt_management` over direct ad hoc prompt assembly.
- Use fragment composition when the agent family shares reusable prompt blocks.
- Use production-labeled Langfuse prompts for live runtime behavior.
- Preserve builtin fallback only where the existing loader already supports it.

### Pattern 2: Context is assembled before graph execution

- `ContextService` loads tenant/client context.
- standalone sessions add collected context, uploaded file references, document references, and OAuth links.
- the factory turns that into prompt variables and state metadata before agent execution starts.

### Pattern 3: Tool strategy is architectural, not just prompt wording

- `atendente_core` uses supervisor + worker delegation tools.
- worker tools are tier-gated and can fan out in parallel.
- standalone agents use catalog-defined enabled tools plus session metadata.
- prompt changes should not attempt to paper over missing tool contracts or bad graph structure.

## How To Use This Skill In This Repo

### For prompt changes

1. Identify whether the prompt is fragment-based, monolithic, or builtin fallback.
2. Preserve existing prompt names when code, scripts, or admin routes depend on them.
3. Move branching, loops, or stateful behavior into code or graph logic when the prompt starts encoding workflow.
4. Verify through the actual consuming service or test, not only by reading the text.

### For agent design changes

1. Start from the owning abstraction: `atendente_core`, `vizu_agent_framework`, or `standalone_agent_api`.
2. Decide whether the behavior belongs in graph routing, tool execution, state reducers, context assembly, or prompt text.
3. Keep tenant/session context boundaries explicit.
4. Validate the narrowest real slice: prompt loader, graph node, runtime stream, or focused e2e test.

## Best Practices

### Development

- Reuse shared prompt and agent infrastructure before introducing a new abstraction.
- Keep prompts declarative; keep orchestration in graph or service code.
- Use real repo vocabulary in prompts, including tenant/context/tool names that actually exist.
- Document unknowns instead of fabricating prompt behavior contracts.

### Production

- Prefer `label="production"` prompt loading for live behavior.
- Treat prompt regressions as runtime regressions: verify them where the user experiences them.
- Preserve graceful degradation where Langfuse or optional integrations are intentionally best-effort.

### Evaluation

- Evaluate prompts by task outcome, not by how polished the prompt text looks.
- Prefer existing tests and verification scripts over subjective spot checks.
- When changing SQL or RAG prompts, verify against the real schema and retrieval contracts in the repo.

## High-Signal Repo Anchors

- `libs/vizu_prompt_management`
- `libs/vizu_agent_framework`
- `services/atendente_core/src/atendente_core/core/`
- `services/standalone_agent_api/src/standalone_agent_api/core/`
- `scripts/audit_langfuse_prompts.py`
- `scripts/verify_standalone_prompts.py`
- `/memories/repo/agent-execution-pipeline.md`
- `/memories/repo/agent-configuration-context-flow.md`
- `/memories/repo/langfuse-prompts.md`

## Known Unknowns

- Not every agent implementation in the repo was sampled for this skill.
- Some older prompt consumers may still rely on builtin templates or legacy loaders.
- The full evaluation story across all agents is still partly distributed between tests, scripts, and runtime inspection.

## Resources

- `references/prompt_engineering_patterns.md`
- `references/llm_evaluation_frameworks.md`
- `references/agentic_system_design.md`
