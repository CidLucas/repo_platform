# Skill Improvement Report: satisfaction_survey
**Date:** 2026-05-29T23:45:00
**Round:** 1

## What Changed

### Before (template fallback)
- Written entirely in Portuguese (prompt content)
- Minimal structure: just instructions as a numbered list
- No explicit constraint on number of questions
- No pitfalls section
- No trigger condition or architecture description
- Tone guidance was vague ("amigável e leve")
- No emoji guidance

### After (new Langfuse prompt)
- Written entirely in ENGLISH (as required)
- Full structured prompt: Trigger / Architecture / Tool Rules / Constraints / Output Format / Pitfalls
- Hard constraint: ONE rating question only (prevents LLM over-asking)
- Explicit NPS vs CSAT decision rule
- Output format with concrete example showing expected structure
- Pitfall section covers verbosity, missing context, tone mismatch, emoji overuse
- Jinja guards specified for all optional variables
- Max ~80 words constraint added for conciseness

### Patterns borrowed from
- `~/.hermes/skills/productivity/business-documents/SKILL.md` — structured output format with concrete example
- `~/.hermes/skills/email/himalaya/SKILL.md` — pitfall blocks with named failure modes, explicit "NEVER does" constraints
- General Hermes skill patterns: trigger-first structure, numbered tool rules, hard limits in constraints

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Suggest expanding to: `"Generate a concise, personalised post-delivery satisfaction survey message (NPS or CSAT) adapted to the customer's profile and recent purchase. No tools required."` — makes it clearer for planner routing that no tools are needed and both NPS/CSAT are supported.
- **required_tool_names**: Currently `[]` — correct, no tools needed. Consider adding a future `send_whatsapp_message` tool when delivery channel integration is available.
- **max_turns**: `2` is appropriate — single-shot draft with at most one revision cycle.
- **tags**: Current tags `["routines", "clients", "nps", "satisfaction"]` are good. Suggest adding `"survey"` and `"post_delivery"` for more precise routing. Consider renaming `"nps"` to `"csat_nps"` to reflect both supported rating formats.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `survey_response_handler` | Process and categorize incoming survey responses (NPS scores, CSAT ratings, free-text comments). Trigger alerts for detractors (NPS < 7) and route promoters to referral flows. | `clients`, `nps` | CRM agent / client monitor agent |
| `review_request_draft` | Generate a follow-up message requesting a Google/Trustpilot/App Store review from satisfied customers (NPS ≥ 9 or CSAT 5/5), with deep link to review platform. | `clients`, `marketing` | CRM agent |
| `churn_risk_alert` | Detect early churn signals from survey responses, support ticket frequency, and purchase recency. Generate a proactive re-engagement action plan. | `clients`, `retention` | Client monitor agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `send_whatsapp_template` | Send a pre-approved WhatsApp Business API template message to a customer phone number. Returns delivery status. | `satisfaction_survey`, `collection_messages`, `reactivation_proposal` |
| `log_survey_response` | Write a survey response (score + comment + customer_id) to the CRM or data warehouse. Returns record ID. | `survey_response_handler` |
| `get_customer_nps_history` | Retrieve historical NPS/CSAT scores for a customer from the CRM. Used to personalize tone and skip repeat surveys sent within 90 days. | `satisfaction_survey`, `survey_response_handler` |

---

## Langfuse Prompt Published
- **Prompt name:** skill:satisfaction_survey:system
- **Labels:** ["production"]
- **Version:** 1
- **Status:** ✅ Published successfully
