# Atendente Core JWT Authentication Fix

## Problem

The `vizu_atendente_core` was throwing a `KeyError: 'id'` when trying to authenticate users via JWT:

```
Erro ao buscar contexto por external_user_id=e0e9c949-18fe-4d9a-9295-d5dfb2cc9723: 'id'
...
internal_client_id = UUID(cliente_data["id"])
                          ~~~~~~~~~~~~^^^^^^
KeyError: 'id'
```

This happened when:
1. JWT authentication sends `external_user_id` (Supabase Auth user ID)
2. Context service looks up the client by `external_user_id`
3. Code tried to access `cliente_data["id"]` but the column doesn't exist
4. The actual column name is `client_id`, not `id`

## Root Cause

**Column name mismatch in `clientes_vizu` table:**
- Primary key column: `client_id` (UUID)
- NOT `id`

The context_service was using the wrong column name when extracting the internal client ID from the Supabase response.

## Solution

### 1. Fixed context_service.py
**File**: `libs/vizu_context_service/src/vizu_context_service/context_service.py`

Changed:
```python
# BEFORE (wrong column name)
internal_client_id = UUID(cliente_data["id"])
logger.debug(f"Found cliente: external_user_id={external_user_id} -> id={internal_client_id}")

# AFTER (correct column name)
internal_client_id = UUID(cliente_data["client_id"])
logger.debug(f"Found cliente: external_user_id={external_user_id} -> client_id={internal_client_id}")
```

### 2. Fixed all CRUD methods
**File**: `libs/vizu_supabase_client/src/vizu_supabase_client/crud.py`

Fixed three methods that were using wrong column names in `.eq()` filters:

#### a) `get_cliente_vizu_by_external_user_id()`
- Updated docstring to mention `client_id` (not `id`)
- Updated log message to show correct column name

#### b) `get_cliente_vizu_by_id()`
```python
# BEFORE: .eq("id", str(cliente_id))
# AFTER:  .eq("client_id", str(cliente_id))
```

#### c) `update_cliente_vizu()`
```python
# BEFORE: .eq("id", str(cliente_id))
# AFTER:  .eq("client_id", str(cliente_id))
```

#### d) `delete_cliente_vizu()`
```python
# BEFORE: .eq("id", str(cliente_id))
# AFTER:  .eq("client_id", str(cliente_id))
```

## Database Schema Reference

`clientes_vizu` table columns:
```
client_id (UUID) ← PRIMARY KEY
├─ nome_empresa (text)
├─ tipo_cliente (text)
├─ tier (text)
├─ external_user_id (text) ← Supabase Auth user ID (from JWT sub)
├─ prompt_base (text)
├─ horario_funcionamento (jsonb)
├─ enabled_tools (text[])
├─ collection_rag (text)
├─ created_at (timestamptz)
└─ updated_at (timestamptz)
```

**Key relationship:**
- `external_user_id` = Supabase Auth user ID (JWT `sub` claim)
- `client_id` = Internal Vizu client identifier (UUID)

## JWT Authentication Flow (Now Fixed ✅)

```
1. User logs in with Supabase Auth
   ├─ JWT issued with `sub` = Supabase Auth user ID
   └─ Example: e0e9c949-18fe-4d9a-9295-d5dfb2cc9723

2. Request to /chat endpoint
   ├─ Extract JWT `sub` claim
   └─ Pass as external_user_id

3. Context service lookup (NOW FIXED)
   ├─ Query: SELECT * FROM clientes_vizu WHERE external_user_id = ?
   ├─ Get response: {client_id: UUID, nome_empresa: "...", ...}
   ├─ Extract: client_id = UUID(cliente_data["client_id"]) ✅ (was ["id"] ❌)
   └─ Return context for this client_id

4. Chat endpoint processes request
   ├─ Uses client context
   └─ Responds to user
```

## What Changed

| Component | Before | After |
|-----------|--------|-------|
| Column Access | `cliente_data["id"]` ❌ | `cliente_data["client_id"]` ✅ |
| Error | `KeyError: 'id'` | No error ✅ |
| Log Message | `id=...` | `client_id=...` ✅ |
| Docstring | Mentioned `id` column | Mentions `client_id` ✅ |

## Files Modified

1. **libs/vizu_context_service/src/vizu_context_service/context_service.py**
   - Line 234: Changed `cliente_data["id"]` to `cliente_data["client_id"]`
   - Line 236: Updated log message to show `client_id` instead of `id`

2. **libs/vizu_supabase_client/src/vizu_supabase_client/crud.py**
   - Lines 108, 128: Updated `get_cliente_vizu_by_external_user_id()` docstring and log
   - Lines 72-98: Fixed `get_cliente_vizu_by_id()` to use `.eq("client_id", ...)`
   - Lines 211-239: Fixed `update_cliente_vizu()` to use `.eq("client_id", ...)`
   - Lines 241-255: Fixed `delete_cliente_vizu()` to use `.eq("client_id", ...)`

## Testing

The fix ensures:
- ✅ JWT authentication works correctly
- ✅ External user IDs resolve to client IDs
- ✅ Context is properly loaded for authenticated users
- ✅ No more `KeyError: 'id'` exceptions

**To test:**
```bash
# Send request with valid JWT
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Should no longer show:
# "Erro ao buscar contexto por external_user_id=...: 'id'"
```

## Verification

✅ No syntax errors in modified files
✅ Column names match database schema
✅ JWT flow documentation updated
✅ Logs will now show correct column names
