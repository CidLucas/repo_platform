# Phase 8 — Troubleshooting & Issues Found

All 16 tests pass (down from 49 — dead code removed). Below is every issue discovered and fixed.

---

## Issues Fixed (Round 1 — Bug Fixes)

### 1. Wrong import module
- **Fix**: `blu_db_connector.supabase` → `blu_supabase_client`

### 2. Missing test fixtures
- **Fix**: Created `tests/conftest.py` with `client_id` fixture.

### 3. Environment variables not loaded
- **Fix**: `conftest.py` calls `dotenv.load_dotenv()`.

### 4. Async calls on sync client
- **Fix**: Removed all `await` from `db.table()` chains (24 occurrences).

### 5. FK constraint — fake client IDs
- **Fix**: Used real `client_id` from `clientes_blu`.

### 6. Column name mismatches — `uploaded_files_metadata`
- **Fix**: `client_id` → `cliente_blu_id`, `file_size` → `file_size_bytes`.

### 7. Schema access API — `vector_db.documents`
- **Fix**: `db.table("documents", schema="vector_db")` → `db.schema("vector_db").table("documents")`.

### 8. Invalid `content` column in `vector_db.documents`
- **Fix**: Removed `content` from insert, added required `client_id`.

### 9. Invalid status enum — `documents_status_check`
- **Fix**: `"embedding"` → `"pending"`.

### 10. Wrong return value in `test_3_upload_knowledge_documents`
- **Fix**: `return doc` → `return updated_session`.

### 11. Unused imports
- **Fix**: Removed unused imports across all files.

---

## Issues Fixed (Round 2 — Cleanup & Architecture)

### 12. Production DB pollution
- **Symptom**: 220 sessions + 132 files + 64 documents accumulated from test runs.
- **Fix**: Deleted all test data. Added `autouse=True` teardown fixture in `conftest.py` that cleans up after each test.

### 13. Test sequential coupling (class-based chaining)
- **Symptom**: Each test method called all previous ones (`test_4` → `test_3` → `test_2` → `test_1`), causing exponential re-execution and cascading failures.
- **Fix**: Rewrote all 3 E2E test files from class-based chained methods into flat standalone functions with shared helper functions. Each test creates its own state.

### 14. Log-only "tests" (zero assertions)
- **Symptom**: `test_phase_8_error_handling.py` (231 lines) and `test_phase_8_ux_loading_states.py` (271 lines) had zero assertions — pure specification documents pretending to be tests. Several methods in E2E files (test_7/8/9 in data_analyst and report_generator, test_6/7 in knowledge_assistant) were also log-only.
- **Fix**: Deleted both files entirely. Removed log-only methods from the 3 E2E files.

### 15. Hardcoded client_id
- **Fix**: `conftest.py` now reads `TEST_CLIENT_ID` env var with fallback.

### 16. Unused `doc_content` variable
- **Fix**: Removed from knowledge_assistant test.

### 17. Migration files don't match production schema
- **Symptom**: `20260105_create_uploaded_files_metadata.sql` used `client_id REFERENCES clientes_blu(id)` but production has `cliente_blu_id REFERENCES clientes_blu(client_id)`. Had extra `content_type` column and wrong `storage_bucket` default.
- **Fix**: Updated both migration files to match production: corrected FK column names, references, removed `content_type`, fixed `'file-uploads'` → `'blu-uploads'`, fixed RLS policies.

### 18. Dead Phase 8 documentation files
- **Fix**: Deleted `PHASE_8_QUICK_REFERENCE.md`, `PHASE_8_SUMMARY.md`, `PHASE_8_TEST_EXECUTION_GUIDE.md`, and `tests/PHASE_8_INTEGRATION_CHECKLIST.md` (~1,716 lines total, all outdated after rewrites).

---

## Final State

- **16 tests**, all passing (36s)
- **3 test files**: `test_phase_8_e2e_data_analyst.py`, `test_phase_8_e2e_knowledge_assistant.py`, `test_phase_8_e2e_report_generator.py`
- **1 conftest**: `tests/conftest.py` (env loading, client_id fixture, autouse teardown)
- **0 remaining action items**
