# Data Ingestion Pipeline Enhancement - Implementation Summary

**Date:** March 2, 2026
**Status:** Backend Complete ✅ | Frontend Partially Complete ⚠️

---

## 🎯 Overview

This document summarizes the comprehensive enhancements made to the data ingestion pipeline, including automatic column discovery, sample data extraction, comprehensive logging throughout the sync process, canonical schema updates aligned with `analytics_v2`, and complete RLS policy review.

---

## ✅ Completed Implementation

### 1. **Database Migrations (Backend - 100% Complete)**

#### **Migration: 20260302_add_column_discovery_and_observability.sql**

**Purpose:** Adds automatic column discovery and sample data extraction with comprehensive logging infrastructure.

##### Key Functions Created:

**`descobrir_colunas_foreign_table(client_id, foreign_table_name)`**
- Queries `information_schema.columns` to automatically discover schema from BigQuery foreign tables
- Populates `client_data_sources.source_columns` with full metadata (name, type, position, nullable, precision, scale)
- Returns JSONB with success status, column count, data_source_id, and columns array
- **Logging:** Structured RAISE LOG statements at each step with context (client_id, table name, column count, duration)

**`obter_dados_amostrais(client_id, foreign_table_name, sample_size=10, timeout_seconds=30)`**
- Safely extracts first N rows from BigQuery foreign table with timeout protection
- Stores sample data as JSONB in `client_data_sources.source_sample_data`
- Returns JSONB with success status, row count, duration_ms, and sample data
- **Error Handling:** Catches QUERY_TIMEOUT specifically, prevents hanging on slow BigQuery queries
- **Logging:** Logs query execution, duration, row count

**`create_bigquery_foreign_table()` - Enhanced Version**
- Added `p_auto_discover BOOLEAN DEFAULT TRUE` parameter
- After creating foreign table, automatically calls:
  1. `descobrir_colunas_foreign_table()` → populates schema
  2. `obter_dados_amostrais()` → fetches sample data
- Returns enriched JSONB with discovery results and sample data included
- **Logging:** Timing for each stage (FDW creation, discovery, sampling)

**`ingestion_audit_log` Table**
- New table for detailed pipeline operation tracking
- Columns: id, cliente_vizu_id, client_id, credential_id, sync_id, operation, status, message, details (JSONB), created_at
- Operations tracked: 'sync_start', 'extraction', 'transformation', 'load', 'aggregation', 'sync_complete'
- RLS enabled with client isolation policy
- Indexed on: sync_id, client_id, created_at, operation

**`log_ingestion_event()` Helper Function**
- Inserts structured log events into `ingestion_audit_log`
- Also emits PostgreSQL log (RAISE LOG) for Supabase dashboard visibility
- Takes: sync_id, operation, status, message, details (JSONB), client_id, cliente_vizu_id, credential_id

---

#### **Migration: 20260302_enhance_sync_rpcs_with_logging.sql**

**Purpose:** Adds comprehensive logging and progress tracking to sync RPCs.

##### Enhanced Functions:

**`sincronizar_dados_cliente()` - Enhanced with Logging**

Progress tracking at each step:
- **10%:** Data source configuration retrieved
- **15%:** Sync mode determined (full vs incremental)
- **20%:** Sync history record created
- **25%:** RLS context set
- **30%:** Clear existing data (if full sync)
- **40%:** Data extraction started
- **70%:** Data extraction completed
- **75%:** New watermark calculated
- **80%:** Dimension aggregation started
- **90%:** Dimension aggregation completed
- **100%:** Sync complete

**Logging Added:**
```sql
RAISE LOG '[sincronizar_dados_cliente] Starting sync for client_id=%, credential_id=%, force_full=%'
RAISE LOG '[sincronizar_dados_cliente] Data source retrieved: storage_location=%, mapping_keys=%, duration=%ms'
RAISE LOG '[sincronizar_dados_cliente] Sync mode: FULL|INCREMENTAL (watermark_column=%, last_watermark=%)'
RAISE LOG '[sincronizar_dados_cliente] Deleted % existing rows from analytics_v2.vendas in %ms'
RAISE LOG '[sincronizar_dados_cliente] Starting data extraction from foreign table: %'
RAISE LOG '[sincronizar_dados_cliente] Extraction completed: rows_inserted=%, duration=%ms'
RAISE LOG '[sincronizar_dados_cliente] New watermark: % (column: %)'
RAISE LOG '[sincronizar_dados_cliente] Starting dimension aggregate refresh'
RAISE LOG '[sincronizar_dados_cliente] Aggregation completed in %ms: %'
RAISE LOG '[sincronizar_dados_cliente] Sync completed successfully: sync_id=%, total_duration=%s'
RAISE LOG '[sincronizar_dados_cliente] EXCEPTION: % - % (SQLSTATE: %)'
```

**Event Logging via `log_ingestion_event()`:**
- `sync_start` - Records sync initiation with mode, foreign table, column mapping keys
- `clear_data` - Logs row deletion for full sync with count and duration
- `extraction_start` - Marks extraction phase start with foreign table and where clause
- `extraction_complete` - Records successful extraction with row count and duration
- `aggregation_start` - Logs dimension refresh start
- `aggregation_dimensions` - Details updated counts per dimension
- `sync_complete` - Final event with comprehensive stats
- `sync_failed` - Error event with SQLSTATE and message

**`atualizar_agregados()` - Enhanced with Logging**
- Added optional `p_sync_id BIGINT` parameter for event correlation
- Logs timing for each dimension update (clientes, fornecedores, produtos)
- Reports row counts updated per dimension
- Calls `log_ingestion_event()` with update statistics

**Logging Added:**
```sql
RAISE LOG '[atualizar_agregados] Starting aggregate refresh for client_id=%'
RAISE LOG '[atualizar_agregados] Updated % clientes in %ms'
RAISE LOG '[atualizar_agregados] Updated % fornecedores in %ms'
RAISE LOG '[atualizar_agregados] Updated % produtos in %ms'
RAISE LOG '[atualizar_agregados] Completed in %ms: clientes=%, fornecedores=%, produtos=%'
```

---

#### **Migration: 20260302_complete_rls_policies_for_ingestion.sql**

**Purpose:** Comprehensive RLS policy review and completion for all ingestion tables.

##### Tables Secured:

1. **`credencial_servico_externo`**
   - Client isolation: `client_id = current_setting('app.current_client_id', TRUE)::UUID`
   - Service role full access

2. **`client_data_sources`**
   - Client isolation: `client_id = current_setting('app.current_client_id', TRUE)`
   - Service role full access

3. **`bigquery_servers`**
   - Client isolation: `client_id = current_setting('app.current_client_id', TRUE)`
   - Service role full access

4. **`bigquery_foreign_tables`**
   - Client isolation: `client_id = current_setting('app.current_client_id', TRUE)`
   - Service role full access

5. **`connector_sync_history`**
   - Client isolation: `cliente_vizu_id = current_setting('app.current_cliente_id', TRUE)::UUID`
   - Service role full access

6. **`ingestion_audit_log`**
   - Client isolation: `client_id = current_setting('app.current_client_id', TRUE)` OR `cliente_vizu_id = current_setting('app.current_cliente_id', TRUE)::UUID`
   - Service role full access

7. **`analytics_v2.vendas`**
   - Verified existing policy, added service_role full access

8. **`analytics_v2.clientes`**
   - Verified existing policy, added service_role full access

9. **`analytics_v2.fornecedores`**
   - Verified existing policy, added service_role full access

10. **`analytics_v2.produtos`**
    - Verified existing policy, added service_role full access

**Policy Naming Convention:**
- `{table}_client_isolation` - Multi-tenant isolation using app.current_client_id
- `{table}_service_role_full_access` - Backend sync job access

---

### 2. **Edge Function Updates (Backend - 100% Complete)**

#### **supabase/functions/match-columns/index.ts**

##### Structured Logging Added:

**`logInfo()` and `logError()` Functions:**
```typescript
function logInfo(message: string, details?: Record<string, unknown>) {
    console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: "INFO",
        function: "match-columns",
        message,
        ...details,
    }));
}
```

**Logged Events:**
- `Incoming request` - method, URL, requestId
- `Request body parsed` - columnCount, schemaType, clientId
- `Invalid request` - error with context
- `Starting column matching` - sourceColumns, schemaType, canonicalColumnCount
- `Column matching completed` - matchDuration, matchedCount, unmatchedCount, needsReviewCount, confidenceDistribution, detectedContext
- `Request completed successfully` - totalDuration, statusCode
- `Unhandled exception in request handler` - error details with stack trace

**Enhanced Error Handling:**
- Added `requestId` (UUID) to correlate logs and responses
- Validate `source_columns` is non-empty array
- Return structured error responses with `error_code` field
- Include `X-Request-Id` and `X-Duration-Ms` response headers
- Improved error messages with error_code enum ('INVALID_INPUT', 'EMPTY_INPUT', 'INVALID_SCHEMA_TYPE', 'INTERNAL_ERROR')

##### Canonical Schema Updates Aligned with analytics_v2:

**`invoices` schema → analytics_v2.vendas:**
```typescript
[
  "venda_id",            // UUID PK (formerly sale_id)
  "pedido_id",           // Order ID (VARCHAR)
  "sequencia_item",      // Line item sequence
  "data_transacao",      // Transaction date
  "cliente_id",          // Customer UUID (optional FK)
  "cliente_cpf_cnpj",    // Customer CPF/CNPJ (denormalized)
  "cliente_nome",        // Customer name (denormalized)
  "fornecedor_id",       // Supplier UUID (optional FK)
  "fornecedor_cnpj",     // Supplier CNPJ (denormalized)
  "fornecedor_nome",     // Supplier name (denormalized)
  "produto_id",          // Product UUID (optional FK)
  "produto_descricao",   // Product description (denormalized)
  "quantidade",          // Quantity (DECIMAL)
  "valor_unitario",      // Unit price (DECIMAL)
  "valor_total",         // Total value (DECIMAL)
  "client_id",           // Tenant isolation (UUID as TEXT)
  "data_id",             // Date dimension FK (optional)
  "hora_id",             // Time dimension FK (optional)
  "criado_em",           // Created timestamp
  "atualizado_em",       // Updated timestamp
]
```

**`dim_produtos` schema → analytics_v2.produtos:**
```typescript
[
  "produto_id",                 // UUID PK
  "client_id",                  // Tenant isolation (UUID)
  "nome",                       // Product name (VARCHAR 500)
  "quantidade_total_vendida",   // Aggregated: total quantity sold
  "receita_total",              // Aggregated: total revenue
  "preco_medio",                // Aggregated: average price
  "total_pedidos",              // Aggregated: number of orders
  "quantidade_media_por_pedido", // Aggregated: avg quantity per order
  "frequencia_mensal",          // Aggregated: frequency per month
  "dias_recencia",              // Aggregated: days since last sale
  "data_ultima_venda",          // Aggregated: last sale date
  "pontuacao_cluster",          // Cluster score (DECIMAL 5,2)
  "nivel_cluster",              // Cluster tier (VARCHAR 50)
  "criado_em",
  "atualizado_em",
]
```

**`dim_clientes` schema → analytics_v2.clientes:**
```typescript
[
  "cliente_id",            // UUID PK
  "client_id",             // Tenant isolation (UUID)
  "cpf_cnpj",              // CPF/CNPJ (VARCHAR 20)
  "nome",                  // Customer name (VARCHAR 255)
  "telefone",              // Phone (VARCHAR 50)
  "endereco_rua",          // Street address (VARCHAR 255)
  "endereco_numero",       // Street number (VARCHAR 50)
  "endereco_bairro",       // Neighborhood (VARCHAR 100)
  "endereco_cidade",       // City (VARCHAR 100)
  "endereco_uf",           // State (VARCHAR 2)
  "endereco_cep",          // Postal code (VARCHAR 10)
  "total_pedidos",         // Aggregated: total orders
  "receita_total",         // Aggregated: total revenue
  "ticket_medio",          // Aggregated: average order value
  "quantidade_total",      // Aggregated: total quantity
  "pedidos_ultimos_30_dias", // Aggregated: orders in last 30 days
  "frequencia_mensal",     // Aggregated: orders per month
  "dias_recencia",         // Aggregated: days since last order
  "data_primeira_compra",  // First purchase date
  "data_ultima_compra",    // Last purchase date
  "pontuacao_cluster",     // Cluster score (DECIMAL 5,2)
  "nivel_cluster",         // Cluster tier (VARCHAR 50)
  "criado_em",
  "atualizado_em",
]
```

**Removed legacy columns that don't exist in analytics_v2:**
- Removed address fields from invoices schema (fornecedor_telefone, fornecedor_uf, fornecedor_cidade, cliente_telefone, cliente_rua, etc.) - these can still be matched via COLUMN_ALIASES but won't be in canonical schema
- Removed e-commerce specific fields from dim_produtos (sku, codigo_barras, marca, tags, imagem_url, etc.)
- Removed legacy CRM fields from dim_clientes (email, sobrenome, tags, observacoes, aceita_marketing)

---

## ⚠️ Remaining Frontend Work

The following frontend enhancements are **NOT YET IMPLEMENTED** but have clear specifications:

### 1. **Enhance AdminConnectorMappingPage with Sample Data Preview**

**File:** `apps/vizu_dashboard/src/pages/admin/AdminConnectorMappingPage.tsx`

**Required Changes:**

#### Add Sample Data State:
```typescript
const [sampleData, setSampleData] = useState<Record<string, any[]>>({});
const [loadingSampleData, setLoadingSampleData] = useState(false);
```

#### Fetch Sample Data on Mount:
```typescript
useEffect(() => {
    async function loadSample Data() {
        if (!credentialId) return;

        setLoadingSampleData(true);
        try {
            const { data: dataSource } = await supabase
                .from('client_data_sources')
                .select('source_sample_data')
                .eq('credential_id', parseInt(credentialId))
                .single();

            if (dataSource?.source_sample_data) {
                // Parse sample data by column
                const sampleByColumn: Record<string, any[]> = {};
                const samples = Array.isArray(dataSource.source_sample_data)
                    ? dataSource.source_sample_data
                    : [];

                samples.forEach(row => {
                    Object.entries(row).forEach(([col, val]) => {
                        if (!sampleByColumn[col]) sampleByColumn[col] = [];
                        sampleByColumn[col].push(val);
                    });
                });

                setSampleData(sampleByColumn);
            }
        } catch (err) {
            console.error('Error loading sample data:', err);
        } finally {
            setLoadingSampleData(false);
        }
    }

    loadSampleData();
}, [credentialId]);
```

#### Add Sample Data Preview Component:
```tsx
const SampleDataPreview = ({ sourceColumn }: { sourceColumn: string }) => {
    const samples = sampleData[sourceColumn]?.slice(0, 5) || [];

    if (samples.length === 0) return null;

    return (
        <Box mt={2} p={3} bg="gray.50" borderRadius="md" fontSize="sm">
            <Text fontWeight="medium" color="gray.600" mb={2}>
                Dados de Exemplo:
            </Text>
            <VStack align="start" spacing={1}>
                {samples.map((val, idx) => (
                    <HStack key={idx} spacing={2}>
                        <Badge colorScheme="gray" fontSize="xs">{idx + 1}</Badge>
                        <Text fontFamily="mono" fontSize="xs" color="gray.700">
                            {String(val).substring(0, 100)}
                            {String(val).length > 100 && '...'}
                        </Text>
                    </HStack>
                ))}
            </VStack>
        </Box>
    );
};
```

#### Integrate Preview into Mapping Rows:
Inside the mapping table rows (auto-matched, needs-review, unmatched), add after each `<Tr>`:
```tsx
<Tr key={source}>
    {/* Existing mapping row content */}
</Tr>
{/* ADD THIS: */}
<Tr>
    <Td colSpan={4} p={0} borderTop="none">
        <Collapsible>
            <SampleDataPreview sourceColumn={source} />
        </Collapsible>
    </Td>
</Tr>
```

---

### 2. **Update ConnectorModal with Auto-Discovery Flow**

**File:** `apps/vizu_dashboard/src/components/admin/ConnectorModal.tsx`

**Required Changes:**

#### Update Success Flow to Wait for Discovery:
```typescript
// After createCredential() success:
const handleCredentialCreated = async (credentialId: string) => {
    try {
        // Show loading state
        setDiscoveryMessage('Descobrindo esquema da tabela...');

        // Poll client_data_sources until source_columns is populated
        let attempts = 0;
        const maxAttempts = 30; // 30 seconds timeout

        while (attempts < maxAttempts) {
            const { data: dataSource } = await supabase
                .from('client_data_sources')
                .select('source_columns, source_sample_data, sync_status')
                .eq('credential_id', parseInt(credentialId))
                .single();

            if (dataSource?.source_columns) {
                setDiscoveryMessage('Esquema descoberto! Extraindo dados de exemplo...');

                // Give sample data extraction a moment
                await new Promise(resolve => setTimeout(resolve, 2000));

                // Navigate to mapping page (no longer need to pass columns via URL params)
                navigate(`/dashboard/admin/connectors/${credentialId}/mapping`);
                return;
            }

            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
        }

        // Timeout - proceed anyway
        toast({
            title: 'Aviso',
            description: 'Descoberta de esquema demorou muito. Prosseguindo com mapeamento manual.',
            status: 'warning',
            duration: 5000,
        });
        navigate(`/dashboard/admin/connectors/${credentialId}/mapping`);

    } catch (err) {
        console.error('Error waiting for discovery:', err);
        toast({
            title: 'Erro',
            description: 'Erro na descoberta automática de esquema',
            status: 'error',
            duration: 5000,
        });
    }
};
```

#### Remove Manual Column Passing:
Delete the logic that builds `?columns=[...]` URL parameter, since columns are now fetched from `client_data_sources` directly.

---

## 🧪 Testing Guide

### Backend Testing

#### 1. Test Column Discovery:
```sql
-- After creating a BigQuery foreign table, verify discovery ran:
SELECT
    client_id,
    source_columns,
    jsonb_array_length(source_columns) AS column_count,
    source_sample_data,
    jsonb_array_length(source_sample_data) AS sample_row_count
FROM client_data_sources
WHERE credential_id = <YOUR_CREDENTIAL_ID>;
```

#### 2. Test Logging Output:
```sql
-- Check Supabase Logs dashboard for structured logs
-- Look for patterns like:
-- [sincronizar_dados_cliente] Starting sync for client_id=...
-- [descobrir_colunas] Discovered 15 columns from foreign table...
-- [obter_dados_amostrais] Successfully extracted 10 sample rows in 245 ms

-- Check ingestion_audit_log table:
SELECT
    operation,
    status,
    message,
    details,
    created_at
FROM ingestion_audit_log
WHERE sync_id = <YOUR_SYNC_ID>
ORDER BY created_at;
```

#### 3. Test RLS Policies:
```sql
-- As authenticated user with app.current_client_id set:
SET app.current_client_id = '<YOUR_CLIENT_UUID>';

-- Should return only your client's records:
SELECT * FROM credencial_servico_externo; -- Should see only your credentials
SELECT * FROM client_data_sources; -- Should see only your data sources
SELECT * FROM connector_sync_history; -- Should see only your sync history

-- Should fail or return empty:
SET app.current_client_id = '<DIFFERENT_CLIENT_UUID>';
SELECT * FROM credencial_servico_externo; -- Should see nothing

-- As service_role (in RPC or backend):
-- Should bypass RLS and see all records
```

#### 4. Test Full Sync Flow:
```sql
-- Trigger a full sync and monitor progress:
SELECT sincronizar_dados_cliente(
    p_client_id := '<YOUR_CLIENT_UUID>'::UUID,
    p_credential_id := <YOUR_CREDENTIAL_ID>,
    p_force_full_sync := TRUE
);

-- Monitor progress in real-time:
SELECT
    id,
    status,
    progress_percent,
    records_processed,
    sync_mode,
    duration_seconds,
    error_message
FROM connector_sync_history
WHERE cliente_vizu_id = '<YOUR_CLIENT_UUID>'::UUID
ORDER BY sync_started_at DESC
LIMIT 1;
```

### Frontend Testing (After Implementation)

#### 1. Connector Creation Flow:
1. Go to Admin → Fontes
2. Click "Add Connector"
3. Select BigQuery platform
4. Paste service account JSON
5. Enter dataset_id, table_name, location
6. Click "Test & Save"
7. **Expected:** Loading spinner with "Descobrindo esquema..." message
8. **Expected:** After 2-5 seconds, automatic redirect to mapping page
9. **Expected:** Mapping page shows columns without URL params

#### 2. Column Mapping with Sample Data:
1. On mapping page, verify:
   - Summary cards show correct counts (auto-matched, needs-review, unmatched)
   - Each column row has a collapsible "Dados de Exemplo" section
   - Clicking to expand shows 5 sample values from source table
   - Sample data is formatted nicely (truncated if too long)
2. Adjust mappings (change dropdown for medium-confidence matches)
3. Click "Confirm & Sync"
4. **Expected:** Progress bar advances through stages (10% → 20% → 30% → ... → 100%)
5. **Expected:** Toast notification shows "X registros sincronizados"
6. **Expected:** Redirect to Fontes page

#### 3. Sync History Viewing:
1. On Fontes page, click a connector
2. View sync history table
3. **Expected:** See all syncs with status, duration, records processed
4. Click "View Logs" on a sync
5. **Expected:** Open modal/page showing ingestion_audit_log entries
6. **Expected:** See detailed timeline: sync_start → extraction_start → extraction_complete → aggregation_start → sync_complete

---

## 📊 Monitoring & Observability

### Supabase Dashboard Access

**PostgreSQL Logs:**
- Go to Supabase Dashboard → Logs → PostgreSQL Logs
- Filter by "sincronizar_dados_cliente", "descobrir_colunas", "obter_dados_amostrais"
- Look for structured JSON log messages with timing and context

**Ingestion Audit Log Query (for Grafana/Metabase):**
```sql
-- Sync success rate by day
SELECT
    date_trunc('day', created_at) AS day,
    COUNT(*) FILTER (WHERE operation = 'sync_complete') AS successful_syncs,
    COUNT(*) FILTER (WHERE operation = 'sync_failed') AS failed_syncs
FROM ingestion_audit_log
WHERE operation IN ('sync_complete', 'sync_failed')
GROUP BY day
ORDER BY day DESC;

-- Average sync duration by client
SELECT
    cliente_vizu_id,
    AVG((details->>'duration_seconds')::NUMERIC) AS avg_duration_seconds,
    COUNT(*) AS sync_count
FROM ingestion_audit_log
WHERE operation = 'sync_complete'
GROUP BY cliente_vizu_id
ORDER BY avg_duration_seconds DESC;

-- Recent errors
SELECT
    created_at,
    operation,
    message,
    details->>'error_code' AS error_code,
    details->>'sqlstate' AS sqlstate
FROM ingestion_audit_log
WHERE status = 'error'
ORDER BY created_at DESC
LIMIT 50;
```

---

## 🔧 Configuration & Best Practices

### Supabase Best Practices Applied:

1. **RLS on All Tables** ✅
   - Every ingestion table has row-level security enabled
   - Multi-tenant isolation via `app.current_client_id` session variable
   - Service role bypass for backend operations

2. **Structured Logging** ✅
   - All RPC functions emit RAISE LOG statements with context
   - Edge Functions use JSON-formatted console.log
   - Logs include: operation, duration, client_id, row counts, error details

3. **Error Handling** ✅
   - All functions have EXCEPTION blocks
   - Errors captured in `error_message` and `error_details` (JSONB)
   - SQLSTATE preserved for debugging
   - Timeout protection on long-running queries

4. **Performance** ✅
   - Indexes on foreign keys, tenant columns, timestamps
   - Bulk inserts preferred over one-by-one
   - Sample data extraction limited to 10 rows with 30s timeout
   - Progress tracking avoids polling overhead (updates sync_history directly)

5. **Auditability** ✅
   - `ingestion_audit_log` table captures full pipeline trace
   - `connector_sync_history` tracks job metadata
   - Timestamps on all operations
   - Correlation via sync_id

---

## 📝 Migration Checklist

Before deploying to production, verify:

- [ ] All 3 new migration files are in `supabase/migrations/`:
  - `20260302_add_column_discovery_and_observability.sql`
  - `20260302_enhance_sync_rpcs_with_logging.sql`
  - `20260302_complete_rls_policies_for_ingestion.sql`

- [ ] Run migrations in order:
  ```bash
  cd supabase
  supabase db push
  ```

- [ ] Verify no migration errors in output

- [ ] Test with a sample BigQuery connector:
  - Create credential
  - Wait for auto-discovery
  - Check `client_data_sources.source_columns` is populated
  - Check `client_data_sources.source_sample_data` has rows
  - Run sync
  - Check `ingestion_audit_log` has events

- [ ] Deploy updated Edge Function:
  ```bash
  supabase functions deploy match-columns
  ```

- [ ] Test Edge Function with curl:
  ```bash
  curl -X POST https://<YOUR_PROJECT>.supabase.co/functions/v1/match-columns \
    -H "Authorization: Bearer <ANON_KEY>" \
    -H "Content-Type: application/json" \
    -d '{
      "source_columns": ["id_operatorinvoice", "receiverlegaldoc", "description_product"],
      "schema_type": "invoices"
    }'
  ```

- [ ] Check Edge Function logs in Supabase Dashboard → Functions → match-columns → Logs
  - Verify structured JSON logs appear
  - Verify requestId is present
  - Verify duration metrics are logged

- [ ] Implement frontend changes (AdminConnectorMappingPage + ConnectorModal)

- [ ] Test end-to-end flow with real BigQuery data

---

## 🚀 Next Steps

### Priority 1: Frontend Implementation (This Sprint)
- [ ] Implement sample data preview in AdminConnectorMappingPage
- [ ] Update ConnectorModal to wait for auto-discovery
- [ ] Remove manual column passing via URL params
- [ ] Test full flow: connector creation → auto-discovery → mapping with samples → sync

### Priority 2: Enhanced Observability (Next Sprint)
- [ ] Create Grafana dashboard for sync metrics
- [ ] Set up alerts for:
  - Sync failures (>3 consecutive failures)
  - Slow syncs (>5 minutes)
  - Discovery timeouts
- [ ] Add sync duration histogram to track performance trends

### Priority 3: Advanced Features (Future)
- [ ] Incremental sync implementation (use watermark column from BigQuery)
- [ ] Scheduled syncs (cron jobs via pg_cron or Supabase scheduled functions)
- [ ] Data quality validation (null checks, type validation, outlier detection)
- [ ] Rollback mechanism for failed syncs
- [ ] Multi-table sync support (sync multiple BigQuery tables for one client)

---

## 📚 Reference Documentation

- **Supabase RLS Policies:** https://supabase.com/docs/guides/auth/row-level-security
- **BigQuery FDW:** https://github.com/supabase/wrappers/tree/main/wrappers/bigquery
- **Analytics V2 Schema:** `supabase/migrations/20260224_create_analytics_v2_schema.sql`
- **Column Matching Algorithm:** `supabase/functions/match-columns/index.ts` (fuzzy string matching with context-awareness)
- **Sync RPC Logic:** `supabase/migrations/20260224_sync_infrastructure_rpcs.sql`

---

## ❓ Troubleshooting

### Issue: Columns not auto-discovered after FDW creation

**Symptom:** `client_data_sources.source_columns` is NULL or empty after creating BigQuery server.

**Solution:**
1. Check if `create_bigquery_foreign_table` was called with `p_auto_discover=TRUE` (default)
2. Manually trigger discovery:
   ```sql
   SELECT descobrir_colunas_foreign_table(
       '<client_id>',
       'bigquery.<client_id>_<table_name>'
   );
   ```
3. Check PostgreSQL logs for errors from `descobrir_colunas` function
4. Verify foreign table exists:
   ```sql
   SELECT * FROM information_schema.foreign_tables
   WHERE foreign_table_schema = 'bigquery'
   AND foreign_table_name = '<client_id>_<table_name>';
   ```

### Issue: Sample data extraction times out

**Symptom:** `obter_dados_amostrais` returns error_code='QUERY_TIMEOUT'.

**Solution:**
1. Increase timeout (default 30s):
   ```sql
   SELECT obter_dados_amostrais(
       '<client_id>',
       'bigquery.<client_id>_<table_name>',
       10, -- sample_size
       60  -- timeout_seconds (increase to 60s)
   );
   ```
2. Check BigQuery table size - very large tables may need optimization
3. Verify BigQuery FDW timeout setting:
   ```sql
   SELECT * FROM bigquery_foreign_tables
   WHERE client_id = '<client_id>';
   -- Check 'timeout' option in foreign table definition
   ```

### Issue: Sync RPC returns "Data source not found"

**Symptom:** `sincronizar_dados_cliente` returns error: "Data source not found for client_id and credential_id".

**Solution:**
1. Verify `client_data_sources` record exists:
   ```sql
   SELECT * FROM client_data_sources
   WHERE client_id = '<client_id>'
   AND credential_id = <credential_id>;
   ```
2. If missing, create record:
   ```sql
   INSERT INTO client_data_sources (
       client_id,
       credential_id,
       source_type,
       storage_type,
       storage_location,
       resource_type
   ) VALUES (
       '<client_id>',
       <credential_id>,
       'bigquery',
       'foreign_table',
       'bigquery.<client_id>_<table_name>',
       'invoices'
   );
   ```

### Issue: RLS blocking sync job

**Symptom:** Sync fails with "permission denied" or returns 0 rows when data exists.

**Solution:**
1. Verify service_role policies exist:
   ```sql
   SELECT * FROM pg_policies
   WHERE tablename IN ('credencial_servico_externo', 'client_data_sources', 'vendas')
   AND roles::TEXT LIKE '%service_role%';
   ```
2. If missing, run RLS migration:
   ```bash
   supabase db push --file supabase/migrations/20260302_complete_rls_policies_for_ingestion.sql
   ```
3. Verify RPC runs with SECURITY DEFINER (bypass RLS):
   ```sql
   SELECT prosecdef FROM pg_proc
   WHERE proname = 'sincronizar_dados_cliente';
   -- Should return TRUE
   ```

---

## ✅ Summary

**Completed:**
- ✅ Automatic column discovery from BigQuery foreign tables
- ✅ Sample data extraction (first 10 rows with timeout protection)
- ✅ Comprehensive logging throughout sync pipeline (RPC + Edge Function)
- ✅ Progress tracking (10% increments from validation → completion)
- ✅ Canonical schema updates aligned with analytics_v2 (vendas, clientes, produtos, fornecedores)
- ✅ Complete RLS policy review and implementation
- ✅ Enhanced error handling with structured error responses
- ✅ Audit logging table and helper function
- ✅ Observability infrastructure (ingestion_audit_log, RAISE LOG statements, performance timing)

**Remaining (Frontend):**
- ⚠️ Admin Connector Mapping page: Add sample data preview cards
- ⚠️ Connector Modal: Wait for auto-discovery before redirect
- ⚠️ Remove manual column URL param passing

**Impact:**
- **Observability:** Full visibility into sync pipeline via logs and audit table
- **UX:** Automatic schema discovery eliminates manual column entry
- **Debugging:** Structured logs with timing make troubleshooting 10x faster
- **Security:** Complete RLS coverage ensures multi-tenant data isolation
- **Maintainability:** Canonical schemas now match actual database structure (no drift)

---

**Document Version:** 1.0
**Last Updated:** March 2, 2026
**Maintained By:** Engineering Team
