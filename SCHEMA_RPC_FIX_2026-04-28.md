# Schema Mismatch Fix — RPC Column References

**Date:** 2026-04-28
**Status:** ✅ Fixed — All RPC functions now match actual schema

---

## Issues Found & Fixed

### ❌ Problem 1: `list_inbox_threads()` — Invalid Column References

**Error:** `column c.agent_id does not exist`

**Root Cause:** RPC was referencing columns that don't exist in `conversa` table

- Attempted columns: `agent_id`, `created_by_role`, `status`, `snippet`
- Actual columns: `id`, `client_id`, `created_at`, `updated_at`

**Fix Applied:**

```sql
-- Updated to use actual conversa columns and join with messages
SELECT
  c.id,
  c.client_id,
  c.created_at,
  c.updated_at,
  (SELECT COUNT(*) FROM public.messages m WHERE m.session_id = c.id) as message_count,
  (SELECT MAX(m.created_at) FROM public.messages m WHERE m.session_id = c.id) as last_message_at
FROM public.conversa c
WHERE c.client_id = public.get_my_client_id()
```

**Key Changes:**

- Messages are linked via `session_id` (not `conversa_id`)
- Removed non-existent columns (agent_id, created_by_role, status, snippet)
- Added message count and last message timestamp

---

### ❌ Problem 2: `list_report_runs()` — Invalid Column References

**Error:** `column r.template_id does not exist`

**Root Cause:** RPC was referencing columns that don't exist in `report_runs` table

- Attempted columns: `template_id`, `format`
- Actual columns: `id`, `schedule_id`, `client_id`, `status`, `output_url`, `error`, `started_at`, `completed_at`, `metadata`

**Fix Applied:**

```sql
-- Updated to use actual report_runs columns
SELECT
  r.id,
  r.schedule_id,
  r.status,
  r.output_url,
  r.error,
  r.started_at,
  r.completed_at
FROM public.report_runs r
WHERE r.client_id = public.get_my_client_id()
ORDER BY COALESCE(r.started_at, r.completed_at) DESC
```

**Key Changes:**

- Removed non-existent columns (template_id, format, output_metadata)
- Use `schedule_id` to link to schedules (if needed)
- Metadata stored as JSONB (can be parsed as needed)

---

### ❌ Problem 3: `list_report_schedules()` — Column Name Mismatch

**Root Cause:** RPC was referencing non-existent columns

- Attempted columns: `template_id`, `cadence`, `format`
- Actual columns: `name`, `report_type`, `cron_expr`, `active`, `recipients`, `config`

**Fix Applied:**

```sql
-- Updated to use actual report_schedules columns
SELECT
  s.id,
  s.name,
  s.report_type,
  s.cron_expr,
  s.active,
  s.next_run_at,
  s.created_at
FROM public.report_schedules s
WHERE s.client_id = public.get_my_client_id()
ORDER BY s.next_run_at ASC
```

**Key Changes:**

- Renamed: `template_id` → `report_type`
- Renamed: `cadence` → `cron_expr`
- Removed: `format` (not needed for schedule list)

---

## Updated RPC Function Schemas

### `list_inbox_threads(p_limit INT)`

**Returns:**

```
id              UUID
client_id       UUID
created_at      TIMESTAMP WITH TIME ZONE
updated_at      TIMESTAMP WITH TIME ZONE
message_count   INT
last_message_at TIMESTAMP WITH TIME ZONE
```

**Usage:**

```sql
SELECT * FROM public.list_inbox_threads(50);
```

---

### `list_report_runs(p_limit INT)`

**Returns:**

```
id              UUID
schedule_id     UUID
status          TEXT
output_url      TEXT
error           TEXT
started_at      TIMESTAMP WITH TIME ZONE
completed_at    TIMESTAMP WITH TIME ZONE
```

**Usage:**

```sql
SELECT * FROM public.list_report_runs(50);
```

---

### `list_report_schedules()`

**Returns:**

```
id          UUID
name        TEXT
report_type TEXT
cron_expr   TEXT
active      BOOLEAN
next_run_at TIMESTAMP WITH TIME ZONE
created_at  TIMESTAMP WITH TIME ZONE
```

**Usage:**

```sql
SELECT * FROM public.list_report_schedules();
```

---

### `list_due_report_schedules()`

**Returns:**

```
schedule_id UUID
client_id   UUID
name        TEXT
report_type TEXT
cron_expr   TEXT
```

**Usage:**

```sql
SELECT * FROM public.list_due_report_schedules();
-- Returns only schedules where next_run_at <= NOW() and active = true
```

---

## Verification

✅ All functions now return correct results (empty result sets indicate proper execution, not errors):

```
list_inbox_threads(10)      → ✅ Works
list_report_runs(10)        → ✅ Works
list_report_schedules()     → ✅ Works
list_due_report_schedules() → ✅ Works
```

---

## API Endpoints — Now Working

| Endpoint                              | Function                      | Status   |
| ------------------------------------- | ----------------------------- | -------- |
| `GET /integrations/inbox/threads`     | `list_inbox_threads()`        | ✅ Fixed |
| `GET /integrations/reports/runs`      | `list_report_runs()`          | ✅ Fixed |
| `GET /integrations/reports/schedules` | `list_report_schedules()`     | ✅ Fixed |
| Reports worker (cron)                 | `list_due_report_schedules()` | ✅ Fixed |

---

## Summary

| Issue                  | Before                                | After                      | Status   |
| ---------------------- | ------------------------------------- | -------------------------- | -------- |
| Inbox API 500 errors   | `column c.agent_id does not exist`    | Empty result set (correct) | ✅ Fixed |
| Reports API 500 errors | `column r.template_id does not exist` | Empty result set (correct) | ✅ Fixed |
| Report schedules API   | Referencing wrong columns             | Using correct columns      | ✅ Fixed |
| Due schedules worker   | Referencing wrong columns             | Using correct columns      | ✅ Fixed |

**All schema mismatches corrected. Endpoints should now return 200 with empty arrays instead of 500 errors.**

---

**Remediation completed:** 2026-04-28 16:15 UTC
**Root cause:** RPC functions were designed against documentation assumptions, not actual schema
