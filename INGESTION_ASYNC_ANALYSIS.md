# Ingestion Async Processing - Current Situation Analysis

## The Problem

You want 100k rows to process **immediately** after clicking "Sincronizar", not wait 50 minutes for pg_cron to batch them 1000 at a time.

---

## What We Tried & Where It Fails

### Current Architecture (Broken)

```
┌─────────────────────────────────────────────────────────────┐
│ USER CLICKS "SINCRONIZAR"                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ run-sync-etl Edge Function (v15)│
         │  - Validate user            │
         │  - Check mapping exists     │
         │  - Create job in DB         │ ← FAILS HERE
         │  - Call process-job-async   │
         └─────────────────────────────┘

         ❌ ERROR: "supabaseKey is required"

         Root Cause: Cannot initialize Supabase client with SERVICE_ROLE_KEY
                     (env var not properly injected or named differently)
```

### What Should Happen Next (If run-sync-etl Worked)

```
         ┌─────────────────────────────────────┐
         │ process-job-async Edge Function     │
         │  - Receive job_id from run-sync-etl     │
         │  - Call sincronizar_dados_cliente() │
         │  - Process 100k rows in one loop    │
         │  - Update job progress              │
         │  - Mark complete                    │
         └─────────────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────────────────┐
         │ Database RPC Function                │
         │ sincronizar_dados_cliente(job_id)    │
         │  - Read all rows from BigQuery FT    │
         │  - Transform & map columns           │
         │  - Upsert dimensions (dim_clientes,  │
         │    dim_fornecedores, dim_inventory)  │
         │  - Insert into fato_transacoes       │
         │  - Complete in 1-2 minutes           │
         └──────────────────────────────────────┘
```

---

## The Real Issue

**The problem is NOT the RPC function** (it's fine).

**The problem is NOT process-job-async** (it's fine).

**The problem IS run-sync-etl**: It cannot authenticate to Supabase with SERVICE_ROLE_KEY to even create the job.

This happens BEFORE process-job-async is ever called.

---

## Why This Happens

Supabase Edge Functions have limited env var injection:

- Some projects inject `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- Some don't, or name them differently
- JWT auth works (other functions use it), but service role key access is project-specific

---

## Better Solution (Simpler, No Inter-Function Calls)

Instead of edge function calling edge function, use what already works:

```
USER CLICKS "SINCRONIZAR"
         │
         ▼
    run-sync-etl (v15)
    - Validate user ✓ (works, uses auth header)
    - Check mapping exists ✓ (works, reads table)
    - Create job in DB ← Change this part
         │
         ├─ OPTION A: Call RPC directly with auth context
         │   (No service role key needed)
         │
         └─ OPTION B: Create job, let pg_cron call processor
            (Simpler, uses existing infrastructure)
```

### Option A: Direct RPC Call from run-sync-etl

run-sync-etl creates the job, then immediately executes the processor RPC:

- Advantage: No inter-function auth issues, completes synchronously
- Disadvantage: Might timeout if 100k rows > 60 seconds

### Option B: Create Job + Use pg_cron (Keep Existing)

- run-sync-etl creates the job
- pg_cron still calls `process_pending_sync_jobs()`
- But now the processor is optimized to handle 100k rows in one execution
- **Trade-off**: Still waits for next pg_cron tick (~30 seconds)

---

## Recommendation

**Go with Option A** but with a guard:

1. run-sync-etl creates the job
2. run-sync-etl calls the RPC `sincronizar_dados_cliente(job_id)` directly
3. If it completes within timeout → Done in 1-2 min ✓
4. If it times out → Job stays "running", pg_cron picks it up later

This avoids all edge function auth issues and uses the database's native async capabilities.
