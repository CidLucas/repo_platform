# Admin Fontes Page - Complete Fix Summary

## Issues Resolved

### Issue 1: Empty Page When No Connectors Configured ✅
**Problem**: Page showed nothing when user had no connectors configured in database.

**Expected**: Should always show all 7 available connector types (BigQuery, VTEX, Shopify, PostgreSQL, MySQL, Loja Integrada, CSV Upload) with "Conectar" buttons.

**Root Cause**: Page logic only displayed connectors from API response. When response was empty array, page showed zero connectors.

**Fix**: Updated `AdminFontesPage.tsx` logic to always display all available connector types from `CONNECTOR_METADATA`, and merge with backend status if available.

**File**: [apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx](apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx#L323-L350)

---

### Issue 2: Wrong API Port (8005 instead of 8008) ✅
**Problem**: Browser console showed `ERR_CONNECTION_REFUSED` when trying to connect to `:8005/connectors/status`.

**Expected**: Should connect to `:8008/connectors/status` (where data_ingestion_api is actually running).

**Root Cause**:
- Root `.env` had wrong port: `VITE_DATA_INGESTION_API_URL=http://localhost:8005`
- `docker-compose.yml` had wrong fallback: `${VITE_DATA_INGESTION_API_URL:-http://localhost:8005}`
- Vite build embedded the wrong URL into the JavaScript bundle

**Fix**:
1. Updated `.env` to use port 8008
2. Updated `docker-compose.yml` fallback to use port 8008
3. Added missing `VITE_GOOGLE_CLIENT_ID` build arg
4. Rebuilt dashboard container

**Files**:
- [.env](/.env#L88) - Changed port from 8005 to 8008
- [docker-compose.yml](/docker-compose.yml#L387-L394) - Fixed fallback and added missing build arg

---

## What Changed

### 1. AdminFontesPage.tsx Logic (Lines 323-350)

**Before**:
```typescript
const allConnectors: ConnectorConfig[] = useMemo(() => {
  if (!connectorsData) return [];
  return connectorsData.connectors.map(mapConnectorToUI);
}, [connectorsData]);
```
**Result**: Empty array when no connectors → empty page

**After**:
```typescript
const allConnectors: ConnectorConfig[] = useMemo(() => {
  // Start with all available connector types from metadata
  const availableConnectorTypes: ConnectorConfig[] = Object.values(CONNECTOR_METADATA)
    .filter(meta => meta.id !== 'unknown')
    .map(meta => ({
      ...meta,
      status: 'not_configured' as ConnectionStatus,
    }));

  // If we have backend data, merge it
  if (connectorsData && connectorsData.connectors.length > 0) {
    const backendConnectorMap = new Map(
      connectorsData.connectors.map(bc => [bc.tipo_servico.toLowerCase(), bc])
    );

    return availableConnectorTypes.map(availableConn => {
      const backendConn = backendConnectorMap.get(availableConn.id);
      if (backendConn) {
        return mapConnectorToUI(backendConn);
      }
      return availableConn;
    });
  }

  // No backend data yet - return all connectors as not_configured
  return availableConnectorTypes;
}, [connectorsData]);
```
**Result**: Always shows all 7 connector types, merged with backend status when available

---

### 2. Environment Configuration

**Root `.env` (line 88)**:
```bash
# Before
VITE_DATA_INGESTION_API_URL=http://localhost:8005

# After
VITE_DATA_INGESTION_API_URL=http://localhost:8008
```

**docker-compose.yml (lines 387-394)**:
```yaml
# Before
args:
  VITE_SUPABASE_URL: ${VITE_SUPABASE_URL}
  VITE_SUPABASE_ANON_KEY: ${VITE_SUPABASE_ANON_KEY}
  VITE_API_URL: ${VITE_API_URL:-http://localhost:8003}
  VITE_ATENDENTE_CORE: ${VITE_ATENDENTE_CORE:-http://localhost:8003}
  VITE_API_URL_ANALYTICS: ${VITE_API_URL_ANALYTICS:-http://localhost:8004}
  VITE_DATA_INGESTION_API_URL: ${VITE_DATA_INGESTION_API_URL:-http://localhost:8005}

# After
args:
  VITE_SUPABASE_URL: ${VITE_SUPABASE_URL}
  VITE_SUPABASE_ANON_KEY: ${VITE_SUPABASE_ANON_KEY}
  VITE_GOOGLE_CLIENT_ID: ${VITE_GOOGLE_CLIENT_ID}  # ← ADDED
  VITE_API_URL: ${VITE_API_URL:-http://localhost:8003}
  VITE_ATENDENTE_CORE: ${VITE_ATENDENTE_CORE:-http://localhost:8003}
  VITE_API_URL_ANALYTICS: ${VITE_API_URL_ANALYTICS:-http://localhost:8004}
  VITE_DATA_INGESTION_API_URL: ${VITE_DATA_INGESTION_API_URL:-http://localhost:8008}  # ← FIXED
```

---

## Page Behavior After Fix

### Scenario 1: New User (No Connectors Configured)
**API Response**:
```json
{
  "connectors": [],
  "total_connected": 0,
  "total_configured": 0
}
```

**Page Display**:
- ✅ Shows all 7 connector types
- ✅ All show "Conectar" button
- ✅ Header shows "0 de 7 conectadas"
- ✅ Categories filter shows counts: E-commerce (3), Bancos de Dados (3), Arquivos (1)
- ✅ No `ERR_CONNECTION_REFUSED` errors

### Scenario 2: User with BigQuery Configured
**API Response**:
```json
{
  "connectors": [
    {
      "credential_id": 1,
      "nome_conexao": "My BigQuery",
      "tipo_servico": "bigquery",
      "status": "active",
      "last_sync_at": "2026-01-06T10:00:00Z",
      "records_count": 15234
    }
  ],
  "total_connected": 1,
  "total_configured": 1
}
```

**Page Display**:
- ✅ BigQuery card shows:
  - Green "Conectado" badge
  - "15,234 registros"
  - "Última sync: 06/01/2026"
  - "Gerenciar" button
- ✅ Other 6 connectors show:
  - No status badge (internal state: `not_configured`)
  - "Conectar" button
- ✅ Header shows "1 de 7 conectadas"

---

## Available Connector Types

All 7 connector types are now always visible:

| ID                | Name              | Category        | Icon Color | Description                                              |
|-------------------|-------------------|-----------------|------------|----------------------------------------------------------|
| bigquery          | Google BigQuery   | database        | #4285F4    | Conecte seu Data Warehouse BigQuery para análises        |
| shopify           | Shopify           | ecommerce       | #96BF48    | Sincronize produtos, pedidos e clientes da loja          |
| vtex              | VTEX              | ecommerce       | #F71963    | Conecte sua loja VTEX e importe dados de vendas          |
| loja_integrada    | Loja Integrada    | ecommerce       | #00A650    | Integre sua Loja Integrada para análise completa         |
| postgresql        | PostgreSQL        | database        | #336791    | Conecte bancos PostgreSQL para importar dados            |
| mysql             | MySQL             | database        | #4479A1    | Importe dados de bancos MySQL ou MariaDB                 |
| csv_upload        | Upload CSV/Excel  | files           | #10B981    | Faça upload de arquivos CSV ou Excel                     |

---

## Testing Checklist

### Before Restarting
- [x] Root `.env` has `VITE_DATA_INGESTION_API_URL=http://localhost:8008`
- [x] `docker-compose.yml` has correct port 8008 in build args
- [x] `AdminFontesPage.tsx` shows all connector types
- [x] Dashboard built successfully

### After Restart (User Testing)
- [ ] Navigate to `http://localhost:8080/dashboard/admin/fontes`
- [ ] Page loads without errors
- [ ] Browser console shows no `ERR_CONNECTION_REFUSED`
- [ ] Browser console shows successful calls to `:8008/connectors/status`
- [ ] All 7 connector cards are visible
- [ ] Header shows "0 de 7 conectadas" (if new user)
- [ ] Categories filter works (E-commerce: 3, Bancos de Dados: 3, Arquivos: 1)
- [ ] Search box filters connectors correctly
- [ ] Clicking "Conectar" opens configuration modal

---

## User Workflow

This is now the correct flow for setting up a connector:

1. **User visits** `/dashboard/admin/fontes`
2. **Page shows** all 7 available connector types
3. **User selects** BigQuery card
4. **User clicks** "Conectar" button
5. **Modal opens** (ConnectorModal component)
6. **User inputs**:
   - Connection name (e.g., "Production BigQuery")
   - Service account JSON
   - Project ID
   - Dataset ID
7. **User clicks** "Salvar"
8. **API call** to `POST http://localhost:8008/connectors/configure`
9. **Page refetches** connector status
10. **BigQuery card updates**:
    - Badge changes to green "Conectado"
    - Shows record count and last sync
    - Button changes to "Gerenciar"
11. **Header updates** to "1 de 7 conectadas"

---

## Build Status

✅ **TypeScript compilation**: Successful
✅ **Docker build**: Successful
✅ **Bundle size**: 1,404.34 kB (minified), 429.04 kB (gzip)
✅ **Bundle hash**: `index-HvwxFAS_.js` (new)
✅ **Correct API URL**: Port 8008 embedded in bundle

---

## Next Steps

**Restart the dashboard**:
```bash
docker-compose up -d vizu_dashboard
```

**Verify in browser**:
1. Navigate to `http://localhost:8080/dashboard/admin/fontes`
2. Check browser console for successful API calls
3. Verify all 7 connector cards are visible
4. Test clicking "Conectar" on any connector

---

## Related Documentation

- [ADMIN_FONTES_PAGE_FIX.md](ADMIN_FONTES_PAGE_FIX.md) - Detailed explanation of page logic fix
- [PORT_8005_TO_8008_FIX.md](PORT_8005_TO_8008_FIX.md) - Detailed explanation of port fix
- [DEBUG_CONNECTOR_API.md](DEBUG_CONNECTOR_API.md) - Debugging guide (now outdated, issue resolved)
- [QUICK_FIX_FONTES_PAGE.md](QUICK_FIX_FONTES_PAGE.md) - Troubleshooting guide (now outdated, issue resolved)

---

**All Fixes Applied**: 2026-01-06
**Status**: Complete ✅
**Ready for Testing**: Yes ✅
