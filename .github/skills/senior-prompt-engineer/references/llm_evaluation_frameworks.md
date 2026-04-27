# Llm Evaluation Frameworks

## Overview

This repo does not have one single centralized evaluation harness for all prompt and agent behavior. Evaluation is distributed across focused tests, prompt verification scripts, runtime traces, and service-specific smoke checks. This guide reflects that reality.

## Core Principles

### Evaluate the real consuming path

A prompt change is only validated when the real service, tool, or agent path behaves correctly. Reading the prompt or manually eyeballing one output is not enough.

### Choose the narrowest useful evaluation surface

Good evaluation targets in this repo include:

- focused unit/integration tests
- prompt verification scripts
- admin prompt surfaces
- service startup or endpoint smoke checks
- Langfuse traces for live runtime inspection

### Separate prompt failure from graph or data failure

If a run fails, isolate whether the issue is:

- wrong prompt text
- wrong variables/context injection
- wrong tool availability
- wrong graph routing
- wrong SQL/RAG backend behavior

## Evaluation Surfaces In This Repo

### Pattern 1: Script-based prompt verification

Examples already present:

- `scripts/audit_langfuse_prompts.py`
- `scripts/verify_standalone_prompts.py`

Use these when validating prompt existence, production labeling, or rollout completeness.

### Pattern 2: Focused integration tests for downstream behavior

Examples include task-specific tests for dashboard RPCs, phase flows, RLS regressions, and agent e2e behavior. When a prompt change affects SQL or retrieval outcomes, prefer the closest existing test slice over inventing a generic evaluation harness.

### Pattern 3: Runtime trace inspection

Langfuse is useful for checking which prompt version ran, what variables were compiled, and how the runtime behaved in context. Use it when the change is live-path sensitive or when tests do not capture the failure mode well.

### Pattern 4: Admin-surface validation for prompt management

`standalone_agent_api` exposes admin prompt routes that can list, inspect, edit, and view prompt versions. These are valid evaluation surfaces for prompt-management changes.

## Best Practices

### Define success in task terms

Examples:

- SQL prompt returns queries that match the analytics schema
- config-helper elicits the required fields cleanly
- standalone agent prompt compiles with real session variables
- supervisor delegates to the right worker tools

### Keep golden examples close to the actual feature

If you need fixtures, derive them from the service's existing payloads, context fields, or session tables, not generic benchmark prompts.

### Re-run the same focused check after local repairs

If a fix targets the same slice, do not broaden evaluation before rerunning the original narrow check.

### Prefer behavioral assertions over style judgments

Judge prompts by correctness, tool usage, isolation, and output contract, not by how elegant the wording sounds.

## Anti-Patterns To Avoid

### Declaring prompt success without verifying the compiled variables

Many failures in this repo are variable-assembly issues, not wording issues.

### Treating all agent regressions as prompt regressions

The graph, context service, tool registry, RLS layer, and prompt loader can all fail independently.

### Building a generic eval harness before checking existing tests and scripts

This repo already has multiple narrow validation entry points.

## Unknowns To Verify

- There is not yet one fully unified evaluation framework spanning every agent family.
- Some prompt-sensitive flows may rely on manual product validation in addition to tests.

## Further Reading

- `scripts/audit_langfuse_prompts.py`
- `scripts/verify_standalone_prompts.py`
- `/memories/repo/agent-execution-pipeline.md`
- `/memories/repo/langfuse-prompts.md`
