Blu Agent Framework — Fix Plan & Backlog

This document is the executable plan derived from the audit. It lists each issue, the concrete implementation plan, bite-sized tasks, tests to add, acceptance criteria, priority and time estimates, plus an execution (sprint) schedule.

Executive summary

- Goal: eliminate brittle LLM parsing, make node placeholders fail-fast, fix Redis checkpointer lifecycle, harden tier comparisons, add tests for state reducers, improve observability, and add doc-generation and CI checks. Larger refactors are scheduled as P2.
- Scope: libs/blu_agent_framework/src/blu_agent_framework
- Deliverable: prioritized backlog, per-issue implementation plan, test matrix, and sprint schedule.

Prioritized backlog (compact)

BL-001: LLM JSON extractor + orchestrator integration
- Priority: P0
- Goal: Replace brittle brace-slice parser with a tolerant extractor and integrate into orchestrator parsing flows.
- Files to change:
  - add: libs/blu_agent_framework/src/blu_agent_framework/utils/llm_parse.py
  - modify: libs/blu_agent_framework/src/blu_agent_framework/orchestrator.py (replace _parse_json and callers)
  - add tests: tests/unit/test_llm_parse.py, tests/unit/test_orchestrator_parse_integration.py
- Tasks (atomic):
  1) Implement parse_first_json(text: str) (fenced-block detection, balanced-brace extraction, tolerant cleanup).
  2) Unit tests for expected LLM shapes (fenced, inline, noisy, multiple JSON, malformed).
  3) Replace _parse_json calls with parse_first_json + pydantic validation; log raw response on failure.
- Tests: listed above.
- Acceptance: parser handles common noisy outputs; orchestrator tests pass.
- Estimate: 4–8h

BL-002: Node placeholder strict behavior
- Priority: P0
- Goal: Avoid silent failures when nodes are not wired; surface errors in dev and provide sentinel in prod mode.
- Files to change:
  - modify: libs/blu_agent_framework/src/blu_agent_framework/nodes.py (execute_tool_node, execute_single_tool_node, respond_node)
  - modify: libs/blu_agent_framework/src/blu_agent_framework/builder.py (assert wiring in tests)
  - add tests: tests/unit/test_node_placeholders.py
- Tasks:
  1) Add AgentConfig.fail_on_placeholders flag (or env var) default True in dev.
  2) Change placeholders to raise NotImplementedError when fail_on_placeholders is True; otherwise return explicit sentinel {'_placeholder': True, 'node': ...}.
  3) Add tests verifying behavior.
- Estimate: 1–2h

BL-003: Redis checkpointer lifecycle
- Priority: P0
- Goal: Handle RedisSaver variants safely; expose deterministic close/shutdown API.
- Files to change:
  - modify: libs/blu_agent_framework/src/blu_agent_framework/checkpointer.py
  - add tests: tests/unit/test_checkpointer_lifecycle.py
- Tasks:
  1) Replace naive __enter__ invocation with an adapter that implements close()/__exit__ delegation.
  2) Add tests for context-manager saver and instance saver variants.
- Estimate: 1–3h

BL-004: Tier comparison normalization
- Priority: P0
- Goal: Ensure TierLevel ordering/comparison is correct and type-safe.
- Files to change:
  - modify: libs/blu_agent_framework/src/blu_agent_framework/registry.py
  - add tests: tests/unit/test_registry_tiers.py
- Tasks:
  1) Inspect TierLevel.get_order signature and normalize calls (use TierLevel consistently).
  2) Add tests asserting expected agent lists for BASIC/SME/PREMIUM.
- Estimate: 1–2h

BL-005: State reducers and invariants tests
- Priority: P0
- Goal: Prevent regressions in state reducers and initial state.
- Files to add tests:
  - tests/unit/test_state_reducers.py
- Tasks:
  1) Write tests for add_messages (cap, order), _cap_tool_results, _cap_skill_results, _list_reducer.
  2) Add test for create_initial_state values.
- Estimate: 1–2h

BL-006: Observability & LLM logging wrapper
- Priority: P1
- Goal: Add structured logs and correlation ids for LLM calls and failed parses.
- Files to change:
  - add: libs/blu_agent_framework/src/blu_agent_framework/utils/observability.py
  - modify: libs/blu_agent_framework/src/blu_agent_framework/orchestrator.py (wrap llm calls, log raw outputs on failure)
  - add tests: tests/unit/test_orchestrator_logging.py
- Tasks:
  1) Small helper to generate correlation ids and structured log entries.
  2) Wrap llm calls and ensure logs include correlation id and truncated raw response on parse failure.
- Estimate: 2–4h

BL-007: Auto-generate docs from code + CI check
- Priority: P1
- Goal: Keep docs in sync by generating skills/agent-type docs from code registries.
- Files to add:
  - scripts/generate_agent_docs.py
  - generated: docs/auto-skills.md, docs/auto-agent-types.md
  - CI: .github/workflows/docs_check.yml (or update existing CI)
- Tasks:
  1) Implement the script, run locally.
  2) Add CI check (script --check mode) or add to existing docs job.
- Estimate: 2–4h

BL-008: SpecialistCache extraction & orchestrator helper refactor
- Priority: P2
- Goal: Reduce complexity; extract compiled-specialist cache into testable class, split execute_step_node into helpers.
- Files to change/add:
  - add: libs/blu_agent_framework/src/blu_agent_framework/specialist_cache.py
  - modify: libs/blu_agent_framework/src/blu_agent_framework/orchestrator.py (use cache, extract helpers)
  - add tests: tests/unit/test_specialist_cache.py, tests/unit/test_execute_step_helpers.py
- Tasks (split into PRs):
  1) Implement SpecialistCache with thread-safety and optional TTL.
  2) Replace inline dict cache with cache.get_or_compile.
  3) Extract helpers in execute_step_node for: select_step, enrich_task, compile_specialist, run_specialist, update_plan.
  4) Add tests for concurrency and helpers.
- Estimate: 8–24h (split across incremental PRs)

BL-009: Pre-commit + formatting + type checks
- Priority: P2
- Goal: Add black/isort/pre-commit and minimal mypy config
- Files to add/update:
  - .pre-commit-config.yaml
  - pyproject.toml (black/isort settings)
  - optionally mypy.ini
- Tasks:
  1) Add pre-commit config and run formatting.
  2) Add mypy config and fix minor typing issues.
- Estimate: 1–3h

Testing matrix (quick reference)

Unit tests (add):
- test_llm_parse.py — fenced JSON, inline JSON, noisy JSON, multiple JSON objects, malformed.
- test_node_placeholders.py — missing injection raises vs sentinel mode.
- test_checkpointer_lifecycle.py — saver instance vs context-manager.
- test_registry_tiers.py — expected agent lists per tier.
- test_state_reducers.py — add_messages cap, tool/skill caps, list reducer.
- test_orchestrator_logging.py — structured logs and correlation ids.
- test_specialist_cache.py — concurrency and TTL.

Integration-ish tests (fast):
- test_orchestrator_parse_integration.py — fake LLM returning various outputs and assert state result.
- AgentBuilder graph compile tests — use small graphs to assert node/edge counts.

Acceptance & verification

- Each P0 fix must include unit tests that fail before the fix and pass after.
- New CI job runs the test suite and the docs generation check.

Sprint plan (2-week minimal)

Week 1:
- Day 1–2: BL-001 (LLM parser) + BL-005 (state reducer tests)
- Day 3: BL-002 (node placeholders)
- Day 4: BL-004 (tier normalization)
- Day 5: BL-003 (checkpointer lifecycle)

Week 2:
- Day 6–7: BL-006 (observability) + tests
- Day 8: BL-007 (docs generation) + CI check
- Day 9–10: BL-009 (pre-commit / formatting) and quick fixes

Week 3+:
- BL-008 refactor split into 3 PRs over 2–3 weeks (specialist cache, helper extraction, orchestrator cleanup)

Estimated effort summary

- P0 total: ~8–17 hours
- P1 total: ~4–8 hours
- P2 total: ~10–30 hours
- Full backlog: ~22–55 hours depending on refactor depth and test coverage

Deliverables created by this plan

- This file: docs/blu_agent_framework_fix_plan.md (this file)
- Unit test stubs (optional next step)
- Small scripts: generate_agent_docs.py (optional next step)

Next steps you can pick (I will not change code unless you ask):
- I can generate unit-test stubs and the LLM parser utility in the repo (no production behavior change). (Reply: "generate stubs")
- I can prepare concrete patch diffs for top P0 items so you can review exact code changes. (Reply: "prepare diffs")
- I can create GitHub issues / project cards from the backlog (provide repo and permissions). (Reply: "create issues")

File written:
Documents/GitHub/repo_platform/docs/blu_agent_framework_fix_plan.md

If you want the unit-test stubs and parser files created now, tell me "generate stubs" and I will create them in the repository as drafts.