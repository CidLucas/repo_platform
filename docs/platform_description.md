Blu (repo_platform) — Platform description

Overview

Blu is an AI-first virtual office platform for Brazilian business owners. The repo_platform codebase contains: frontend React app, multiple Python backend libs and microservices, and orchestration for AI agents built around LangGraph / LangChain.

Key conventions

- Language: repository artifacts (docs, code comments) are in English; personal drafts and voice transcriptions in Portuguese.
- TDD-first: every code change should start with a failing unit test.
- Branch naming: fix/BL-<id>-<short-slug> for bug fixes, feat/<short-slug> for features.
- Commit messages: one-line summary and a two-line body with context.
- STT: present and configured in the environment. Agents must assume STT is available.

Recent audit & artifacts

We performed an audit focused on libs/blu_agent_framework. Outcomes and artifacts:

- Audit file: docs/blu_agent_framework_audit.md
- Fix plan: docs/blu_agent_framework_fix_plan.md
- Test stubs and utilities created: libs/blu_agent_framework/src/blu_agent_framework/utils/llm_parse.py, tests/, scripts/generate_agent_docs.py

How to continue

- Follow the fix plan with TDD, starting with BL-001..BL-005. Use the code-assist prompt saved in the user's assistant notes to guide VS Code actions.
- Keep docs/auto-skills.md and docs/auto-agent-types.md up to date by running scripts/generate_agent_docs.py and enabling the docs_check CI job.
