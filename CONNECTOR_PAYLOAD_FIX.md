# Fix: BigQuery Connector Payload Structure Mismatch (422 Error)

## Issue

When trying to create a BigQuery connector through the Admin Fontes page, the "Testar conexão" (test connection) works successfully, but "Conectar e Sincronizar" (connect and sync) fails with:

```
Erro ao configurar conector
[object Object],[object Object],[object Object],[object Object],[object Object],[object Object]
```

**Browser Console**:
```
:8008/credentials/create:1 Failed to load resource: the server responded with a status of 422 (Unprocessable Entity)
```

**Server Logs**:
```
INFO: 185.199.110.133:57347 - "POST /credentials/test-connection HTTP/1.1" 200 OK
INFO: 185.199.110.133:22042 - "POST /credentials/create HTTP/1.1" 422 Unprocessable Entity
```

## Root Cause

**Payload Structure Mismatch**: The frontend sends a **nested** payload structure, but the backend expects a **flattened** structure.

### Frontend Sends (WRONG):
```json
{
  "client_id": "uuid",
  "nome_conexao": "My BigQuery",
  "tipo_servico": "BIGQUERY",
  "credentials": {
    "project_id": "my-project",
    "dataset_id": "my_dataset",
    "service_account_json": { ... }
  }
}
```

### Backend Expects (CORRECT):
```json
{
  "client_id": "uuid",
  "nome_conexao": "My BigQuery",
  "tipo_servico": "BIGQUERY",
  "project_id": "my-project",
  "dataset_id": "my_dataset",
  "service_account_json": { ... }
}
```

## Why This Happened

The frontend TypeScript interface defined:

```typescript
export interface CreateCredentialRequest {
  client_id: string;
  nome_conexao: string;
  tipo_servico: string;
  credentials: CredentialPayload; // ← Nested object
}
```

But the backend Pydantic schema expects:

```python
class BigQueryCredentialCreate(CredencialBase):
    # Base fields (inherited)
    client_id: str
    nome_conexao: str
    tipo_servico: str

    # BigQuery fields at root level (NOT nested)
    project_id: str
    dataset_id: str | None
    service_account_json: dict[str, Any]
```

## The Fix

Updated `connectorService.ts` to **flatten the payload** before sending to the backend:

**File**: [apps/vizu_dashboard/src/services/connectorService.ts](apps/vizu_dashboard/src/services/connectorService.ts#L172-L178)

**Before** (lines 178):
```typescript
const response = await fetch(endpoint, {
  method: 'POST',
  headers: { ... },
  body: JSON.stringify(request), // ← Sends nested structure
});
```

**After** (lines 172-186):
```typescript
// Flatten the payload: backend expects credentials fields at root level, not nested
const payload = {
  client_id: request.client_id,
  nome_conexao: request.nome_conexao,
  tipo_servico: request.tipo_servico,
  ...request.credentials, // Spread credentials fields to root level
};

const response = await fetch(endpoint, {
  method: 'POST',
  headers: { ... },
  body: JSON.stringify(payload), // ← Sends flattened structure
});
```

## Better Error Messages

Also improved error handling for FastAPI validation errors (422):

**Before**:
```typescript
if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Falha ao criar credencial');
}
// When detail is an array: "Error: [object Object],[object Object]"
```

**After** (lines 189-199):
```typescript
if (!response.ok) {
  const error = await response.json();
  // Handle FastAPI validation errors (422) which return an array of error objects
  if (error.detail && Array.isArray(error.detail)) {
    const errorMessages = error.detail.map((err: any) =>
      `${err.loc?.join('.') || 'field'}: ${err.msg}`
    ).join('; ');
    throw new Error(errorMessages);
  }
  throw new Error(error.detail || 'Falha ao criar credencial');
}
// Now shows: "Error: project_id: field required; dataset_id: field required"
```

## Example Error Format

FastAPI's `422 Unprocessable Entity` response looks like:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "project_id"],
      "msg": "Field required",
      "input": { ... }
    },
    {
      "type": "missing",
      "loc": ["body", "service_account_json"],
      "msg": "Field required",
      "input": { ... }
    }
  ]
}
```

Now the frontend properly formats this as:
```
body.project_id: Field required; body.service_account_json: Field required
```

## How BigQuery Connector Payload Works Now

### 1. User fills form in ConnectorModal:
```typescript
{
  connectionName: "Production BigQuery",
  projectId: "my-gcp-project",
  datasetId: "ecommerce_data",
  serviceAccount: { /* JSON object */ }
}
```

### 2. Frontend creates request:
```typescript
const request: CreateCredentialRequest = {
  client_id: auth.clienteVizuId,
  nome_conexao: formData.connectionName,
  tipo_servico: "BIGQUERY",
  credentials: {
    project_id: formData.projectId,
    dataset_id: formData.datasetId,
    service_account_json: formData.serviceAccount,
  }
}
```

### 3. `createCredential()` flattens it:
```typescript
const payload = {
  client_id: "uuid-here",
  nome_conexao: "Production BigQuery",
  tipo_servico: "BIGQUERY",
  project_id: "my-gcp-project",        // ← Flattened
  dataset_id: "ecommerce_data",        // ← Flattened
  service_account_json: { ... },       // ← Flattened
}
```

### 4. Backend validates successfully:
```python
# FastAPI/Pydantic validates against BigQueryCredentialCreate
payload = BigQueryCredentialCreate(**request_json)
# ✅ All required fields present at root level
```

## Files Modified

1. [apps/vizu_dashboard/src/services/connectorService.ts](apps/vizu_dashboard/src/services/connectorService.ts#L159-L202)
   - Added payload flattening (line 172-178)
   - Improved error handling for 422 validation errors (line 189-199)

## Container Restart

```bash
docker-compose build vizu_dashboard
docker-compose up -d vizu_dashboard
```

**Status**: Container rebuilt and restarted ✅

## Testing

After refreshing the page:

1. **Navigate to** `/dashboard/admin/fontes`
2. **Click "Conectar"** on BigQuery card
3. **Fill in**:
   - Connection name: "Test BigQuery"
   - Project ID: "your-project-id"
   - Dataset ID: "your_dataset"
   - Service Account JSON: (paste JSON)
4. **Click "Testar conexão"** → Should show "✅ Conexão testada com sucesso"
5. **Click "Conectar e Sincronizar"** → Should now work (no more 422 error)

**Expected**: Connector saves successfully and appears in the list with "Conectado" badge.

---

**Fix Applied**: 2026-01-06
**Status**: Complete ✅
**Container Restarted**: Yes ✅
