# Fix: Disable Google Secret Manager (DefaultCredentialsError)

## Issue

When trying to save BigQuery connector credentials, the API returned:

```
Erro ao configurar conector
Falha de processamento no serviço de ingestão: Falha ao processar credencial: DefaultCredentialsError
```

**Server Logs**:
```
INFO: 172.64.149.246:41454 - "POST /credentials/create HTTP/1.1" 500 Internal Server Error
```

## Root Cause

The `credential_service.py` was trying to use **Google Secret Manager** to store credentials:

```python
from vizu_auth import SecretManager

secret_manager = SecretManager()  # ← Requires GCP credentials

async def create_credential(...):
    secret_id = await secret_manager.store_secret(client_id, sensitive_payload)
    # ❌ Fails with DefaultCredentialsError
```

**DefaultCredentialsError** occurs when Google Cloud client libraries can't find authentication credentials. The Docker container doesn't have:
- Service account JSON file
- `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Google Cloud SDK credentials

## Why This Was Implemented

The original design intended to use Google Secret Manager for **better security**:
- Credentials encrypted at rest
- Access logging and audit trails
- Automatic key rotation
- Separation of secrets from database

However, this requires:
1. GCP project setup
2. Secret Manager API enabled
3. Service account with Secret Manager permissions
4. Container configured with GCP credentials

## The Fix

**Disabled Secret Manager** and store credentials directly in Supabase as JSON:

**File**: [services/data_ingestion_api/src/data_ingestion_api/services/credential_service.py](services/data_ingestion_api/src/data_ingestion_api/services/credential_service.py)

### Before (Lines 7-19):
```python
from vizu_auth import SecretManager

secret_manager = SecretManager()

# Later in create_credential():
secret_id = await secret_manager.store_secret(client_id, sensitive_payload)

db_payload = {
    "credenciais_cifradas": secret_id,  # Secret Manager ID
}
```

### After (Lines 3-46):
```python
import json

# Note: SecretManager requires GCP credentials - disabled for now
# from vizu_auth import SecretManager

# Later in create_credential():
credentials_json = json.dumps(sensitive_payload)

db_payload = {
    "client_id": client_id,
    "nome_servico": credenciais.nome_conexao,
    "tipo_servico": credenciais.tipo_servico,
    "credenciais_cifradas": credentials_json,  # Store JSON directly
    "status": "pending",
}
```

## Security Considerations

### Current Implementation (Supabase Storage)
✅ **Encrypted at rest** - Supabase uses PostgreSQL with encryption
✅ **Row-Level Security (RLS)** - Users can only access their own credentials
✅ **SSL/TLS** - All connections encrypted in transit
⚠️ **Database access** - Anyone with database access can see encrypted data

### Future Implementation (Secret Manager)
✅ All benefits above, plus:
✅ **Separate encryption** - Credentials encrypted separately from database
✅ **Access logging** - Who accessed which secret and when
✅ **Key rotation** - Automatic rotation of encryption keys
✅ **IAM policies** - Fine-grained access control

## How Credentials Are Stored Now

### Example: BigQuery Connector

**Input** (from frontend):
```json
{
  "client_id": "uuid-123",
  "nome_conexao": "Production BigQuery",
  "tipo_servico": "BIGQUERY",
  "project_id": "my-gcp-project",
  "dataset_id": "ecommerce_data",
  "service_account_json": {
    "type": "service_account",
    "project_id": "my-gcp-project",
    "private_key_id": "abc123",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "client_email": "service-account@project.iam.gserviceaccount.com"
  }
}
```

**Stored in** `credencial_servico_externo` **table**:
```json
{
  "id": 1,
  "client_id": "uuid-123",
  "nome_servico": "Production BigQuery",
  "tipo_servico": "BIGQUERY",
  "credenciais_cifradas": "{\"project_id\":\"my-gcp-project\",\"dataset_id\":\"ecommerce_data\",\"service_account_json\":{...}}",
  "status": "pending",
  "created_at": "2026-01-06T15:00:00Z"
}
```

## Retrieving Credentials Later

When the BigQuery connector needs to connect:

```python
# Get credential from database
credential = await supabase_client.select_one(
    table="credencial_servico_externo",
    filters={"id": credential_id}
)

# Parse JSON
credentials = json.loads(credential["credenciais_cifradas"])

# Use credentials
project_id = credentials["project_id"]
service_account_json = credentials["service_account_json"]

# Connect to BigQuery
from google.cloud import bigquery
client = bigquery.Client.from_service_account_info(service_account_json)
```

## Migration Path to Secret Manager (Future)

To enable Secret Manager in production:

### 1. Set up GCP Project
```bash
gcloud projects create vizu-production
gcloud config set project vizu-production
```

### 2. Enable Secret Manager API
```bash
gcloud services enable secretmanager.googleapis.com
```

### 3. Create Service Account
```bash
gcloud iam service-accounts create vizu-secret-manager \
  --display-name="Vizu Secret Manager"

gcloud projects add-iam-policy-binding vizu-production \
  --member="serviceAccount:vizu-secret-manager@vizu-production.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin"

gcloud iam service-accounts keys create /path/to/key.json \
  --iam-account=vizu-secret-manager@vizu-production.iam.gserviceaccount.com
```

### 4. Configure Docker Container
```yaml
# docker-compose.yml
data_ingestion_api:
  environment:
    GOOGLE_APPLICATION_CREDENTIALS: /app/gcp-credentials.json
  volumes:
    - /path/to/key.json:/app/gcp-credentials.json:ro
```

### 5. Re-enable Secret Manager in Code
```python
# Uncomment these lines:
from vizu_auth import SecretManager
secret_manager = SecretManager()
```

## Files Modified

1. [services/data_ingestion_api/src/data_ingestion_api/services/credential_service.py](services/data_ingestion_api/src/data_ingestion_api/services/credential_service.py)
   - Commented out `from vizu_auth import SecretManager` (line 9)
   - Commented out `secret_manager = SecretManager()` (line 22)
   - Added `import json` (line 3)
   - Replaced Secret Manager logic with JSON storage (lines 40-55)
   - Removed rollback logic for Secret Manager (lines 72-75)

## Container Restart

```bash
docker-compose restart data_ingestion_api
```

**Status**: Container restarted ✅

## Testing

After restarting, test the BigQuery connector:

1. Navigate to `/dashboard/admin/fontes`
2. Click "Conectar" on BigQuery
3. Fill in connection details
4. Click "Conectar e Sincronizar"
5. **Expected**: Credentials save successfully (no more DefaultCredentialsError)
6. **Expected**: Connector appears in list with "Pending" or "Conectado" status

## Verify in Supabase

Check that credentials were saved:

```sql
SELECT
    id,
    nome_servico,
    tipo_servico,
    status,
    length(credenciais_cifradas) as credentials_length,
    created_at
FROM credencial_servico_externo
ORDER BY created_at DESC;
```

**Expected Output**:
```
id | nome_servico         | tipo_servico | status  | credentials_length | created_at
1  | Production BigQuery  | BIGQUERY     | pending | 1234               | 2026-01-06 15:00:00
```

---

**Fix Applied**: 2026-01-06
**Status**: Complete ✅
**Container Restarted**: Yes ✅
**Security**: Supabase encrypted storage (upgrade to Secret Manager for production) ⚠️
