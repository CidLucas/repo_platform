# Skill Improvement Report: fiscal
**Date:** 2026-05-30T08:48:34Z
**Round:** 1

## What Changed

### Before
The `agents/fiscal-agent` template (used as fallback) had a reasonable structure but:
- Was written partially in PT-BR (mixing languages in the system prompt)
- Lacked an explicit **Trigger** section — the planner had no one-sentence routing condition
- Tool Rules were buried in `<Tool Rules>` tags without ordered steps or call-order declaration
- No distinction between NF-e (products/ICMS) vs NFS-e (services/ISS) pitfall
- `fiscal_preparar_dados_nfe` and `fiscal_status_integracao` were listed in SkillDefinition tools but NOT mentioned in the template — gap between code and prompt
- No explicit constraint on `max_turns` variable or Jinja guard pattern
- Confirmation gate was mentioned but not enforced as a hard constraint
- No dedicated **Pitfalls** section

### After (new `skill:fiscal:system` prompt in Langfuse)
- Full English prompt following the standardized Blu skill structure
- **Trigger** — one clear sentence for frontdesk routing
- **Architecture** — linear flow from request to confirmation to emission
- **Tool Rules** — 5 tools in explicit numbered order with required call conditions
- `fiscal_preparar_dados_nfe` and `fiscal_status_integracao` now properly documented with behavior (raises on incomplete data, SEFAZ status check)
- **Constraints** — includes `{{max_turns}}`, confirmation gate as hard rule, NF-e field completeness requirement, Jinja guard for `company_profile`
- **Output Format** — 4 distinct output templates (pre-emission, post-emission, guidance, integration-not-active)
- **Pitfalls** — 6 explicit failure modes documented (alíquota guessing, NF-e vs NFS-e confusion, skipping gate, partial data retry, integration state assumption, max_turns pressure)

### Patterns Borrowed From
- `blu-prompt-engineering` SKILL.md (Hermes): numbered tool rules, Jinja guards pattern, output format declarations
- `langfuse-prompt-management` SKILL.md (Hermes): auth pattern, label/type requirements
- `agents/fiscal-agent` template (repo_platform): domain knowledge, output formats, constraint language
- Hermes skill structure standard: Trigger / Architecture / Tool Rules / Constraints / Output Format / Pitfalls sections

---

## SkillDefinition Suggestions (not auto-applied)

- **description:** Current: `"NF-e / NFS-e issuance, fiscal data validation, and SEFAZ integration. Transactional: raises on incomplete data rather than returning partial output."` → Suggested: `"NF-e / NFS-e issuance, fiscal data preparation, SEFAZ integration status, and tax regime queries (Simples Nacional, Lucro Presumido, Lucro Real, MEI). Raises on incomplete data — never returns partial invoice payloads."` (more complete for planner routing)
- **required_tool_names:** Current list is missing `whatsapp_enviar_mensagem` which is referenced in the template as an optional sending step. Suggest adding it or noting it as optional_tool_names if the framework supports that.
- **max_turns:** Current value is `4`. For the full flow (RAG → SQL → prepare → confirm → emit → status) that's 6 logical steps. Suggest increasing to `6` to match the actual agent template which says "Máximo 6 turnos por tarefa fiscal."
- **tags:** Current: `["fiscal", "nfe", "nfse", "tax", "sefaz"]` — all English ✅. Consider adding `"invoice"` and `"tax-regime"` for more granular routing.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `fiscal_deadline_monitor` | Monitor fiscal deadlines (DAS, DARF, DEFIS, PGDAS-D) and proactively alert the user before due dates | `fiscal` | fiscal-agent |
| `tax_regime_advisor` | Analyze current revenue data and simulate tax burden under different regimes (Simples vs Lucro Presumido vs Real) to suggest optimal regime | `fiscal` | fiscal-agent |
| `nota_fiscal_history` | Retrieve, filter, and summarize issued invoices (NF-e / NFS-e) by period, client, or status (authorized, cancelled, denied) | `fiscal` | fiscal-agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `fiscal_consultar_nota` | Query emitted NF-e/NFS-e by number, key, or date range from SEFAZ or the ERP integration | `fiscal`, `nota_fiscal_history` |
| `fiscal_cancelar_nota` | Cancel an emitted NF-e/NFS-e with SEFAZ confirmation — requires reason and time-window validation (24h rule for NFS-e varies by municipality) | `fiscal` |
| `fiscal_deadline_calendar` | Return upcoming fiscal obligation dates for the company's regime (DAS, DARF, DEFIS, etc.) | `fiscal_deadline_monitor` |
| `fiscal_regime_simulator` | Simulate tax burden across Simples Nacional anexos, Lucro Presumido, and Lucro Real given revenue inputs | `tax_regime_advisor` |

---

## Langfuse Prompt Published

- **Prompt name:** `skill:fiscal:system`
- **Labels:** `["production"]`
- **Tags:** `["skill", "fiscal", "blu", "auto-improved"]`
- **Langfuse ID:** `bfe3e6de-2078-4937-954f-4eaf736bcb5f`
- **Status:** ✅ Published (HTTP 201 — created new prompt, no previous version existed)
