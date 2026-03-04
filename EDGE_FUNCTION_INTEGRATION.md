# Edge Function Integration - Data Ingestion Pipeline

## Overview

The Edge Function integration automates the schema matching process in the data ingestion pipeline. When a user creates a BigQuery credential, the system automatically discovers columns and calls the `match-columns` Edge Function to perform intelligent column matching before user review.

## Complete Data Flow

### 1. Credential Creation (Frontend)
**File:** `apps/vizu_dashboard/src/services/connectorService.ts`

```
User creates credential → connectorService.createCredential()
  ├── Calls create_bigquery_server RPC (creates FDW server)
  ├── Inserts into credencial_servico_externo
  └── Calls create_bigquery_foreign_table RPC with p_auto_discover=true
```

### 2. Foreign Table Creation + Auto-Discovery (Database)
**RPC:** `create_bigquery_foreign_table()`
**Location:** Supabase Database

```
create_bigquery_foreign_table(p_auto_discover=true)
  ├── Creates PostgreSQL foreign table pointing to BigQuery
  ├── Calls descobrir_colunas_foreign_table() - discovers columns
  ├── Calls obter_dados_amostrais() - gets sample data
  └── Calls trigger_column_discovery(credential_id)  ← KEY: This triggers Edge Function!
```

### 3. Column Discovery + Edge Function Call (Database)
**RPC:** `trigger_column_discovery()`
**Location:** Supabase Database
**Endpoint Called:** `https://haruewffnubdgyofftut.supabase.co/functions/v1/match-columns`

```
trigger_column_discovery(credential_id)
  ├── Queries information_schema to get discovered columns
  ├── Calls match-columns Edge Function with:
  │   ├── source_columns: discovered column names
  │   ├── schema_type: 'invoices' (default, can be customized)
  │   └── client_id: for tracking
  │
  └── Edge Function Response:
      ├── matched: {source_col → canonical_col} - high confidence (≥0.85)
      ├── unmatched: [source_cols] - low confidence (<0.70)
      ├── needs_review: [{source, candidates}] - medium confidence (0.70-0.85)
      ├── confidence_scores: {source_col → score}
      └── detected_context: 'customer'|'supplier'|'product'|'neutral'
```

### 4. Results Storage (Database)
**Table:** `client_data_sources`

The Edge Function results are stored in:
```sql
UPDATE client_data_sources SET
  source_columns = v_columns,           -- All discovered columns
  column_mapping = v_matched_columns,   -- High confidence matches
  unmapped_columns = v_unmatched_columns,  -- Low confidence
  needs_review_columns = v_needs_review,   -- Medium confidence
  match_confidence = v_confidence_scores,  -- Scores
  detected_entity_context = v_detected_context,  -- Entity type
  sync_status = 'mapping_ready'         -- Ready for user review
```

### 5. Mapping Review (Frontend)
**Component:** `AdminConnectorMappingPage.tsx`
**Path:** `/dashboard/admin/mapeamento/:credentialId`

```
Page Load → Fetch from client_data_sources
  ├── Loads pre-computed Edge Function results
  ├── Displays three sections:
  │   ├── ✅ Auto-matched columns (≥85% confidence)
  │   ├── ⚠️  Needs Review columns (70-85% confidence)
  │   └── ❌ Unmatched columns (<70% confidence)
  │
  └── User Actions:
      ├── Review auto-matched columns
      ├── Select canonical column for needs_review items
      ├── Map or ignore unmatched columns
      └── Confirm and trigger sync
```

### 6. Sync Confirmation (Frontend & Database)
**Component:** `handleConfirmAndSync()` in `AdminConnectorMappingPage.tsx`

```
User clicks "Confirmar e Sincronizar"
  ├── Builds final mapping from:
  │   ├── Auto-matched columns (not changed)
  │   ├── User selections for needs_review
  │   └── User mappings for unmatched
  │
  ├── Updates client_data_sources:
  │   ├── column_mapping = final mapping
  │   ├── ignored_columns = user-ignored columns
  │   └── sync_status = 'syncing'
  │
  └── Calls sincronizar_dados_cliente RPC
      ├── Routes to analytics_v2 tables:
      │   ├── vendas (transactions)
      │   ├── clientes (customers)
      │   ├── fornecedores (suppliers)
      │   └── produtos (products)
      │
      └── Sets sync_status = 'synced' on completion
```

## Key Components

### Edge Function: match-columns
**File:** `supabase/functions/match-columns/index.ts`
**Purpose:** Intelligent column matching using string similarity

**Features:**
- **Fuzzy Matching:** Uses `compareTwoStrings()` for 70%+ similarity detection
- **Alias Resolution:** Recognizes 100+ column aliases for common fields
- **Context Detection:** Identifies entity types (customer, supplier, product)
- **Context-Aware Mapping:** Disambiguates ambiguous columns using detected context
  - Example: "cnpj" → "cliente_cpf_cnpj" (customer) or "fornecedor_cnpj" (supplier)
- **Confidence Scoring:** Returns match confidence for each column

**Input:**
```json
{
  "source_columns": ["cliente_nome", "cnpj", "data", "valor"],
  "schema_type": "invoices",
  "client_id": "client-uuid"
}
```

**Output:**
```json
{
  "matched": {
    "cliente_nome": "cliente_nome",
    "valor": "valor_total"
  },
  "unmatched": ["data"],
  "needs_review": [
    {
      "source": "cnpj",
      "candidates": [
        {"canonical": "cliente_cpf_cnpj", "confidence": 0.92},
        {"canonical": "fornecedor_cnpj", "confidence": 0.88}
      ]
    }
  ],
  "confidence_scores": {
    "cliente_nome": 1.0,
    "cnpj": 0.92,
    "valor": 0.88
  },
  "detected_context": "customer"
}
```

### Database Functions

#### `trigger_column_discovery(credential_id BIGINT)`
- Called automatically by `create_bigquery_foreign_table`
- Discovers columns from foreign table information_schema
- **Calls Edge Function** with discovered columns
- Stores all results in client_data_sources
- Returns sync_status = `mapping_ready`

#### `create_bigquery_foreign_table(..., p_auto_discover BOOLEAN)`
- Creates PostgreSQL foreign table for BigQuery data
- If `p_auto_discover=true`:
  - Discovers columns
  - Gets sample data
  - **Automatically triggers `trigger_column_discovery`**

#### `descobrir_colunas_foreign_table(client_id UUID)`
- Queries information_schema for column metadata
- Returns detailed column information (type, nullable, precision, etc.)

#### `obter_dados_amostrais(client_id UUID, timeout_ms INTEGER)`
- Queries first N rows from foreign table
- Stores in client_data_sources.source_sample_data
- Used for preview in mapping UI

## Status Tracking

### Sync Status Values
```
pending          → Credential created, awaiting discovery
mapping_ready    → Columns discovered & Edge Function results ready for user review
syncing          → User confirmed mapping, sync in progress
synced           → Sync completed successfully
error            → Sync failed (see error_message)
```

## UI Components

### AdminConnectorMappingPage
**Displays three tabbed sections:**

1. **✅ Mapeadas Automaticamente** (Auto-matched columns)
   - High confidence (≥85%)
   - Shows: Source column → Canonical column
   - Shows: Confidence score
   - Shows: Sample data preview

2. **⚠️ Precisam Revisão** (Needs Review)
   - Medium confidence (70-85%)
   - Shows: Source column
   - Shows: Multiple candidate canonical columns with confidence scores
   - User selects the correct mapping

3. **❌ Não Mapeadas** (Unmatched columns)
   - Low confidence (<70%)
   - User can: Select mapping OR Ignore column

## Error Handling

### Edge Function Failures
If the Edge Function call fails:
- Logs warning (doesn't fail)
- Updates client_data_sources with empty mapping
- Sets all discovered columns to `unmapped_columns`
- User can manually review and map

### Database Transaction Safety
All operations use `SECURITY DEFINER` to:
- Execute with database role privileges
- Safely call external Edge Functions
- Handle rollbacks if needed

## Performance Considerations

- **Column Discovery:** O(n) where n = column count
- **Edge Function Call:** ~200-500ms for 10-50 columns
- **Fuzzy Matching:** O(n*m) where m = canonical schema size
- **Sample Data:** Queries first 100 rows by default

## Testing Checklist

- [ ] Create BigQuery credential → foreign table created automatically
- [ ] Check HTTP request to Edge Function in logs
- [ ] Verify results stored in client_data_sources
- [ ] Load AdminConnectorMappingPage → results loaded from database
- [ ] User adjusts medium-confidence matches
- [ ] User maps/ignores unmatched columns
- [ ] Click sync → data written to analytics_v2 tables
- [ ] Verify sync_status transitions: pending → mapping_ready → syncing → synced

## Future Enhancements

1. **AI-Powered Context:** Use LLM to better detect entity context
2. **User Feedback Loop:** Store user corrections to improve Edge Function
3. **Historical Mappings:** Suggest mappings based on previous credentials
4. **Batch Rematch:** Allow users to trigger Edge Function rematch if needed
5. **Multi-schema Support:** Auto-detect if data should go to multiple tables
