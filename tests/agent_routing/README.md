# Agent Routing Tests

## Setup

```bash
# 1. Start the agent API locally
cd services/agent_api
uvicorn agent_api.main:app --port 8003 --reload

# 2. Get your JWT from Supabase (login via frontend and copy from DevTools → Network → Authorization header)
# Or generate a test token via Supabase dashboard → Authentication → Users → generate link

# 3. Set env vars
export BLU_API_URL=http://localhost:8003
export BLU_JWT=<supabase_access_token>

# 4. Install deps if not in venv
pip install httpx
```

## Run

```bash
cd tests/agent_routing

# All 50 queries
python run_tests.py

# Single layer
python run_tests.py --layer 1   # routing coverage (20 queries)
python run_tests.py --layer 2   # edge cases (10 queries)
python run_tests.py --layer 3   # tool invocation (10 queries)
python run_tests.py --layer 4   # graceful failure (10 queries)

# Specific queries
python run_tests.py --ids 21,22,27   # edge cases with risk flags

# Dry run (print without calling API)
python run_tests.py --dry-run

# Custom sleep (default: 2s)
python run_tests.py --sleep 3

# Save to different file
python run_tests.py --output my_results.json
```

## Interpreting results

### In the terminal
Each query prints:
- Routing decision (expected_agent)
- HTTP status + latency
- First 120 chars of the response

### In Langfuse
Filter traces by session_id prefix: `test-YYYYMMDD-HHMMSS-`
Each session_id encodes the run timestamp + query ID.

What to look for in the trace:
1. Which system prompt was loaded? (frontdesk vs synthesis vs specialist)
2. Which tools were called? (tool_calls in the trace)
3. Were there errors or retries?
4. Latency per step

### Result JSON
`results.json` has one object per query with:
- `status`: "ok" | "error" | "skipped"
- `http_status`: 200, 422, 500, etc.
- `response_preview`: first 500 chars of the agent response
- `duration_ms`: end-to-end latency
- `session_id`: use this to find the trace in Langfuse

## Known gaps (document here as you find them)

See TEST_PLAN.md section "Identified routing gaps" for pre-identified issues.

Add new findings here during the test run.

| Query ID | Issue found | Root cause | Fix applied |
|----------|-------------|-----------|-------------|
| (fill in during testing) | | | |
