# Admin Fontes Page Fix - Display All Available Connectors

## Issue

The Admin Fontes de Dados page was showing an empty state when no connectors were configured in the database. However, the page should **always show all available connector types** (BigQuery, VTEX, Shopify, CSV Upload, PostgreSQL, MySQL, etc.) regardless of configuration status.

## Root Cause

The page logic only displayed connectors returned from the API:

```typescript
// OLD LOGIC (INCORRECT)
const allConnectors: ConnectorConfig[] = useMemo(() => {
  if (!connectorsData) return [];
  return connectorsData.connectors.map(mapConnectorToUI);
}, [connectorsData]);
```

When `connectorsData.connectors` was an empty array (new user with no configured connectors), the page showed **zero connectors** instead of showing all available options.

## Understanding the Page Purpose

This is a **data setup/configuration page**, not just a status viewer. Users need to:

1. **See all available connector types** (BigQuery, VTEX, Shopify, PostgreSQL, MySQL, CSV Upload, etc.)
2. **View metadata for each connector** (description, category, icon)
3. **See configuration status**:
   - `not_configured` - Available but not set up yet (shows "Conectar" button)
   - `connected` - Active and syncing data (shows "Gerenciar" button, record count, last sync)
   - `error` - Configured but failing (shows "Reconectar" button)
   - `pending` - Currently syncing (shows "Sincronizando" badge)
4. **Click "Conectar"** to open the configuration modal and input credentials (service account, secrets, etc.)

## The Fix

Updated the logic to **always show all available connector types** and merge with backend status when available:

```typescript
// NEW LOGIC (CORRECT)
const allConnectors: ConnectorConfig[] = useMemo(() => {
  // Start with all available connector types from metadata
  const availableConnectorTypes: ConnectorConfig[] = Object.values(CONNECTOR_METADATA)
    .filter(meta => meta.id !== 'unknown') // Exclude DEFAULT/unknown
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

## Behavior After Fix

### Scenario 1: New User (No Connectors Configured)
**API Response**: `{ connectors: [], total_connected: 0, total_configured: 0 }`

**Page Display**:
- Shows all 7 connector types (BigQuery, Shopify, VTEX, Loja Integrada, PostgreSQL, MySQL, CSV Upload)
- All show status: `not_configured`
- All show button: "Conectar"
- Header shows: "0 de 7 conectadas"

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
- BigQuery: Status `connected`, shows "15,234 registros", "Última sync: 06/01/2026", button "Gerenciar"
- Shopify: Status `not_configured`, button "Conectar"
- VTEX: Status `not_configured`, button "Conectar"
- Loja Integrada: Status `not_configured`, button "Conectar"
- PostgreSQL: Status `not_configured`, button "Conectar"
- MySQL: Status `not_configured`, button "Conectar"
- CSV Upload: Status `not_configured`, button "Conectar"
- Header shows: "1 de 7 conectadas"

### Scenario 3: User with Error in Connection
**API Response**: BigQuery returns with `status: "error"`

**Page Display**:
- BigQuery: Red badge "Erro", button "Reconectar"
- Other connectors: Status `not_configured`, button "Conectar"

## Available Connector Types

The page shows these connectors (defined in `CONNECTOR_METADATA`):

1. **Google BigQuery** (database)
   - Icon: SiGooglebigquery
   - Color: #4285F4 (Google Blue)
   - Description: "Conecte seu Data Warehouse BigQuery para análises avançadas"

2. **Shopify** (ecommerce) - NEW badge
   - Icon: SiShopify
   - Color: #96BF48
   - Description: "Sincronize produtos, pedidos e clientes da sua loja Shopify"

3. **VTEX** (ecommerce) - NEW badge
   - Icon: FiShoppingCart
   - Color: #F71963
   - Description: "Conecte sua loja VTEX e importe todos os dados de vendas"

4. **Loja Integrada** (ecommerce) - NEW badge
   - Icon: FiShoppingCart
   - Color: #00A650
   - Description: "Integre sua Loja Integrada para análise de vendas completa"

5. **PostgreSQL** (database)
   - Icon: SiPostgresql
   - Color: #336791
   - Description: "Conecte bancos PostgreSQL para importar dados transacionais"

6. **MySQL** (database)
   - Icon: SiMysql
   - Color: #4479A1
   - Description: "Importe dados de bancos MySQL ou MariaDB"

7. **Upload CSV/Excel** (files)
   - Icon: FiFileText
   - Color: #10B981
   - Description: "Faça upload de arquivos CSV ou Excel para análise"

## User Workflow

1. **User visits `/dashboard/admin/fontes`**
2. **Page loads** - shows all 7 connector types
3. **User sees "0 de 7 conectadas"** if new account
4. **User clicks "Conectar"** on BigQuery card
5. **Modal opens** (ConnectorModal component)
6. **User inputs**:
   - Connection name (e.g., "My BigQuery Production")
   - Service account JSON
   - Project ID
   - Dataset ID
7. **User clicks "Salvar"**
8. **API call** to `POST /connectors/configure` (data_ingestion_api)
9. **Page refetches** - now shows BigQuery as `pending` or `connected`
10. **User sees "1 de 7 conectadas"**

## File Modified

**File**: [apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx](apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx)

**Changes**:
- Line 323-350: Updated `allConnectors` useMemo logic to always show all available connector types
- Line 402-403: Added comment explaining behavior when user not authenticated

## Testing

After rebuilding the dashboard, verify:

1. **New user (no connectors)**:
   - [ ] Page shows 7 connector cards
   - [ ] All show "Conectar" button
   - [ ] No "not_configured" badge visible (that's internal state only)
   - [ ] Header shows "0 de 7 conectadas"

2. **User with 1 connector configured**:
   - [ ] Configured connector shows green "Conectado" badge
   - [ ] Configured connector shows record count and last sync
   - [ ] Configured connector shows "Gerenciar" button
   - [ ] Other 6 connectors show "Conectar" button
   - [ ] Header shows "1 de 7 conectadas"

3. **Filter by category**:
   - [ ] "E-commerce" tab shows 3 items (Shopify, VTEX, Loja Integrada)
   - [ ] "Bancos de Dados" tab shows 3 items (BigQuery, PostgreSQL, MySQL)
   - [ ] "Arquivos" tab shows 1 item (CSV Upload)

4. **Search functionality**:
   - [ ] Typing "big" filters to show only BigQuery
   - [ ] Typing "shop" shows Shopify
   - [ ] Typing "csv" shows CSV Upload

## Build Status

✅ **Build completed successfully**
✅ **No TypeScript errors**
✅ **Ready for deployment**

## Related Files

- [useConnectorStatus.tsx](apps/vizu_dashboard/src/hooks/useConnectorStatus.tsx) - Hook that fetches backend data
- [connectorStatusService.ts](apps/vizu_dashboard/src/services/connectorStatusService.ts) - API service
- [ConnectorModal.tsx](apps/vizu_dashboard/src/components/admin/ConnectorModal.tsx) - Configuration modal
- Backend API: `services/data_ingestion_api/src/data_ingestion_api/api/connector_status_routes.py`

---

## Next Steps

1. **Restart the dashboard container**:
   ```bash
   docker-compose up -d vizu_dashboard
   ```

2. **Navigate to** `http://localhost:8080/dashboard/admin/fontes`

3. **Verify** all 7 connector types are visible

4. **Test** clicking "Conectar" on BigQuery to open the configuration modal

---

**Fix Applied**: 2026-01-06
**Status**: Complete ✅
