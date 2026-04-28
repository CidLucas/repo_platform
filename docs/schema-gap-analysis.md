# Schema Gap Analysis — Frontend × New DB Baseline

**Date:** 2026-04-28
**Scope:** `HomePage`, `InboxPage`, `ReportsPage`, `LoginPage`, all admin pages, onboarding wizard
**Reference:** `supabase/SCHEMA_PLAN.md` (baseline applied 2026-04-28)

---

## Legend

- 🔴 **CRITICAL** — runtime DB error (relation/column does not exist)
- 🟡 **STALE TYPE** — no crash but sends/receives wrong field names
- 🟠 **MISSING DB OBJECT** — frontend calls an RPC/view not yet created in any migration
- 🗑️ **ELIMINATE** — code only used by deprecated out-of-scope pages; delete it

---

## 1. Critical Breaks — Queries That Will Fail at Runtime

### 1.1 🔴 `connector_sync_history` → does not exist (merged into `analytics_v2.reg_jobs`)

**Affected files:**
| File | Function | Line range |
|---|---|---|
| [connectorStatusService.ts](../apps/blu_dashboard/src/services/connectorStatusService.ts) | `getConnectorStatus()` | ~120–160 |
| [connectorStatusService.ts](../apps/blu_dashboard/src/services/connectorStatusService.ts) | `getSyncHistory()` | ~166–208 |
| [connectorStatusService.ts](../apps/blu_dashboard/src/services/connectorStatusService.ts) | `getDashboardStats()` | ~306–388 |

**Used by:** `useConnectorStatus` → AdminConnectorsPage, AdminFontesPage
`useDashboardStats` → AdminHomePage

**Fix:** Rewrite these three functions to query `analytics_v2.reg_jobs` filtered by `job_type = 'connector_sync'`.
New column mapping for `reg_jobs`:

| Old `connector_sync_history` | New `analytics_v2.reg_jobs`                    |
| ---------------------------- | ---------------------------------------------- |
| `id`                         | `job_id` (UUID)                                |
| `credential_id`              | `credential_id`                                |
| `status`                     | `status`                                       |
| `sync_started_at`            | `started_at`                                   |
| `sync_completed_at`          | `completed_at`                                 |
| `records_processed`          | _(no direct equivalent — use `rows_inserted`)_ |
| `records_inserted`           | `rows_inserted`                                |
| `records_updated`            | _(removed — not tracked)_                      |
| `records_failed`             | _(removed — covered by `error_message`)_       |
| `resource_type`              | `resource_type`                                |
| `error_message`              | `error_message`                                |
| `created_at`                 | `created_at`                                   |

> `getDashboardStats()` also queries `connector_sync_history` twice (today's syncs and last sync timestamp). Both need rewriting.

---

### 1.2 🔴 `client_data_uploads` → does not exist (replaced by `public.uploaded_files_metadata`)

**Affected files:**
| File | Function |
|---|---|
| [connectorStatusService.ts](../apps/blu_dashboard/src/services/connectorStatusService.ts) | `getUploadedFiles()` |
| [connectorStatusService.ts](../apps/blu_dashboard/src/services/connectorStatusService.ts) | `deleteUploadedFile()` |

**Used by:** `useUploadedFiles` → AdminFontesDetalhesPage

**Fix:** Replace `client_data_uploads` with `public.uploaded_files_metadata`.

Column mapping:

| Old `client_data_uploads` | New `uploaded_files_metadata`                      |
| ------------------------- | -------------------------------------------------- |
| `id`                      | `id` (UUID, not int)                               |
| `file_name`               | `file_name`                                        |
| `file_size_bytes`         | `size_bytes`                                       |
| `file_type`               | `mime_type`                                        |
| `status`                  | `status`                                           |
| `records_count`           | _(removed)_                                        |
| `records_imported`        | _(removed)_                                        |
| `created_at`              | `created_at`                                       |
| `processed_at`            | _(removed — check `status`)_                       |
| `storage_path`            | `storage_path`                                     |
| `download_url`            | _(removed — construct from storage_path + bucket)_ |

Storage bucket: `client-uploads` → **`file-uploads`** (schema plan §Storage Buckets).

---

### 1.3 🔴 `credencial_servico_externo` column names changed

The migration renamed several columns. The old names no longer exist.

| Old name                                                 | New name      | Type change            |
| -------------------------------------------------------- | ------------- | ---------------------- |
| `nome_servico`                                           | `nome`        | —                      |
| `tipo_servico`                                           | `tipo`        | —                      |
| `status` (text: `'active'/'inactive'/'error'/'pending'`) | `ativo`       | **boolean**            |
| _(new)_                                                  | `credenciais` | JSONB — not mapped yet |

**Affected files:**
| File | Functions |
|---|---|
| [connectorStatusService.ts](../apps/blu_dashboard/src/services/connectorStatusService.ts) | `getConnectorStatus()`, `getDashboardStats()` |
| [hooks/useConnectorsNeedingReview.ts](../apps/blu_dashboard/src/hooks/useConnectorsNeedingReview.ts) | `refetch()` |

**Fix (connectorStatusService):**

- `select('id, nome_servico, tipo_servico, status, ...')` → `select('id, nome, tipo, ativo, ...')`
- Status logic (`status === 'active'`) → `ativo === true`

**Fix (useConnectorsNeedingReview):**

- `.select('id, nome_servico, tipo_servico')` → `.select('id, nome, tipo')`
- `cred.nome_servico` → `cred.nome`; `cred.tipo_servico` → `cred.tipo`

---

### 1.4 🔴 `current_moment` column removed from `clientes_blu`

Schema decision (SCHEMA*PLAN.md): *"ephemeral; never belonged in persistent storage."\_

**Affected files:**
| File | What it does |
|---|---|
| [services/onboardingService.ts](../apps/blu_dashboard/src/services/onboardingService.ts) | Selects + updates `current_moment` |
| [hooks/useOnboarding.ts](../apps/blu_dashboard/src/hooks/useOnboarding.ts) | Manages `current_moment` state |
| [types/onboarding.ts](../apps/blu_dashboard/src/types/onboarding.ts) | `` interface + defaults |
| [components/onboarding/steps/CurrentMomentStep.tsx](../apps/blu_dashboard/src/components/onboarding/steps/CurrentMomentStep.tsx) | UI for editing this field |

**Fix:**

1. Remove `current_moment` from `CONTEXT_COLUMNS` in `onboardingService.ts`.
2. Remove `current_moment` from the `saveOnboardingData` payload builder.
3. Remove `current_moment` from `OnboardingData` and `emptyOnboardingData` in `types/onboarding.ts`.
4. Remove `ONBOARDING_STEPS` entry `'current_moment'` and `updateCurrentMoment` from `useOnboarding.ts`.
5. Archive `CurrentMomentStep.tsx` — do not render it.

**Also:** Replace direct `.update()` in `saveOnboardingData` with the `merge_onboarding_state(jsonb)` RPC (listed in phase5) to get race-free JSON merge semantics.

---

### 1.5 🔴 `rfq_requests` and `purchase_orders` tables removed

`getProcurementOverview()` and `getRecentPurchaseOrders()` in `analyticsService.ts` query these dropped tables.

**Used by:** These functions are **only used by out-of-scope pages** (marked 🗑️ below). No fix needed for in-scope pages — but must be removed to stop the code from reaching a dropped table.

---

## 2. Missing DB Objects — RPCs Not in Any Migration

These are called by in-scope pages/hooks but are not defined in any of the 11 migration files.

### 2.1 🟠 `public` schema — RPCs needed for HomePage

| RPC name                             | Called by              | Used by                                 |
| ------------------------------------ | ---------------------- | --------------------------------------- |
| `get_recent_activity(p_limit)`       | `getRecentActivity()`  | `useRecentActivity` → HomePage          |
| `get_pendencias()`                   | `getPendencias()`      | `usePendencias` → HomePage              |
| `get_my_insights(p_limit, p_status)` | `getInsights()`        | `useInsights` → InsightsCard → HomePage |
| `get_agent_runs_today()`             | `getAgentRunsToday()`  | `useAgentRunsToday` → HomePage          |
| `get_nps_score(p_window_days)`       | `getNpsScore()`        | `useNps` → HomePage                     |
| `get_my_dashboard_kpis()`            | `getMyDashboardKpis()` | `useDashboardKpis` → HomePage           |

> `dismiss_insight(p_insight_id)` **is** in phase5 ✅
> `list_kpi_catalog`, `set_client_dimension_kpis` **are** in phase5 ✅

**Action required:** Add a new migration (e.g., `20260428150000_phase8_missing_rpcs.sql`) defining all 6 functions above.

**Note on `get_pendencias`:** The old implementation likely referenced `rfq_requests` (dropped). The new implementation must source pending items from `approval_requests`, `reg_jobs` (failed/stale jobs), and `client_data_sources` only.

---

### 2.2 🟠 `analytics_v2` schema — dimension RPCs needed for KPI section (HomePage)

The `useDimensionKpis` hook (used by the KPI section on HomePage) fans out to:

| RPC                                                          | Called by                         |
| ------------------------------------------------------------ | --------------------------------- |
| `analytics_v2.get_finance_indicators(p_period)`              | `getFinanceIndicators()`          |
| `analytics_v2.get_commercial_indicators(p_period)`           | `getCommercialIndicators()`       |
| `analytics_v2.get_inventory_indicators(p_period)`            | `getInventoryIndicators()`        |
| `analytics_v2.get_supply_indicators(p_period)`               | `getSupplyIndicators()`           |
| `analytics_v2.get_marketing_indicators(p_period)`            | `getMarketingIndicators()`        |
| `analytics_v2.get_admin_indicators(p_period)`                | `getAdminIndicators()`            |
| `analytics_v2.get_commercial_revenue_by_channel(p_period)`   | `getCommercialRevenueByChannel()` |
| `analytics_v2.get_commercial_top_clients(p_period, p_limit)` | `getCommercialTopClients()`       |

**Action required:** These need to be created in the DB. They read from `fato_transacoes`, `dim_*` tables and `approval_requests`. The `SupplyIndicators` fields (rfqs_abertas, pos_aprovadas, etc.) need to be redesigned since `rfq_requests` and `purchase_orders` were dropped — source from `approval_requests` instead.

---

### 2.3 🟠 `d1_engagement_summary` view (AdminHomePage)

`adminService.ts:getD1EngagementMetrics()` reads from `d1_engagement_summary` which is not in any migration.

**Used by:** AdminHomePage (or a component it renders).

**Action required:** Either create this view or remove the function and its UI surface.

---

## 3. Stale Types — TypeScript Interfaces Reference Removed Columns

### 3.1 🟡 `adminService.ts` — `ClienteBlu` interfaces carry dropped fields

The three interfaces (`ClienteBlu`, `ClienteBluCreate`, `ClienteBluUpdate`) include:

- `tipo_cliente` → **removed** from `clientes_blu`
- `horario_funcionamento` → **removed**
- `prompt_base` → **removed**

These types feed the Tool Pool API admin endpoints. The API backend also needs to stop returning/accepting these fields, but the frontend types must be cleaned up now to avoid confusion.

**Fix:** Remove those 3 fields from all three interfaces in [adminService.ts](../apps/blu_dashboard/src/services/adminService.ts).

---

## 4. Items Flagged for Elimination

These hooks, service functions, and interfaces are **only used by deprecated pages not in the user's scope** (e.g., the old `/dashboard/pedidos`, `/dashboard/clientes`, etc. dimension pages).

### 4.1 🗑️ Hooks — eliminate

| Hook                     | Reason                                  |
| ------------------------ | --------------------------------------- |
| `useDashboardIndicators` | Used only by `PedidosPage` (deprecated) |

### 4.2 🗑️ `analyticsService.ts` functions — eliminate

| Function                          | Reason                                             |
| --------------------------------- | -------------------------------------------------- |
| `getPedidosOverview()`            | PedidosPage only                                   |
| `getPedidoDetails()`              | PedidosPage only                                   |
| `getFornecedores()`               | Deprecated Fornecedores dimension page             |
| `getFornecedor()`                 | Deprecated Fornecedor detail page                  |
| `getClientes()`                   | Deprecated Clientes dimension page                 |
| `getCliente()`                    | Deprecated Cliente detail page                     |
| `getProdutosOverview()`           | Deprecated Produtos dimension page                 |
| `getProdutoDetails()`             | Deprecated Produto detail page                     |
| `getProductsForFilter()`          | Deprecated cross-analysis filter                   |
| `getCustomersForFilter()`         | Deprecated cross-analysis filter                   |
| `getCustomersByProduct()`         | Deprecated cross-analysis                          |
| `getProductsByCustomer()`         | Deprecated cross-analysis                          |
| `getCustomerMonthlyOrders()`      | Deprecated cross-analysis                          |
| `getCustomersBySupplier()`        | Deprecated cross-analysis                          |
| `getProductsBySupplier()`         | Deprecated cross-analysis                          |
| `getSuppliersByProduct()`         | Deprecated cross-analysis                          |
| `getProcurementOverview()`        | Queries dropped `rfq_requests` + `purchase_orders` |
| `getRecentPurchaseOrders()`       | Queries dropped `purchase_orders`                  |
| `exportPoToSheets()`              | Procurement flow (dropped tables)                  |
| `getOrderIndicators()`            | PedidosPage only                                   |
| `getOrderStatusBreakdown()`       | PedidosPage only                                   |
| `getPedidosOverviewScorecards()`  | PedidosPage only                                   |
| `getPedidosTimeSeries()`          | PedidosPage only                                   |
| `summarizeOrderStatusBreakdown()` | PedidosPage only                                   |

### 4.3 🗑️ `analyticsService.ts` interfaces — eliminate with their functions

`PedidosOverviewResponse`, `PedidoItem`, `PedidoItemDetalhe`, `PedidoDetailResponse`,
`FornecedoresOverviewResponse`, `FornecedorDetailResponse`, `ClientesOverviewResponse`,
`ClienteDetailResponse`, `ProdutosOverviewResponse`, `ProdutoDetailResponse`,
`PedidosOverviewScorecards`, `RfqStatusBreakdown`, `PurchaseOrderStatusBreakdown`,
`ProcurementOverview`, `PurchaseOrderListItem`, `PoExportToSheetsResponse`,
`CustomerByProduct`, `ProductByCustomer`, `MonthlyOrderData`,
`CustomerBySupplier`, `SupplierByProduct`, `OrderStatusBucket`, `OrderStatusSummary`,
`ORDER_STATUS_BUCKETS` constant.

> `CustomerMetricsResponse`, `ProductMetricsResponse`, `OrderMetricsResponse` — verify if used by any in-scope page before deleting.

---

## 5. Action Plan

### Frontend (do now)

| Priority | File                                                                | Action                                                                                              |
| -------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 🔴 1     | `connectorStatusService.ts`                                         | Rewrite `getConnectorStatus`, `getSyncHistory`, `getDashboardStats` to use `analytics_v2.reg_jobs`  |
| 🔴 2     | `connectorStatusService.ts`                                         | Replace `client_data_uploads` → `uploaded_files_metadata`; bucket `client-uploads` → `file-uploads` |
| 🔴 3     | `connectorStatusService.ts` + `useConnectorsNeedingReview.ts`       | Fix column names: `nome_servico` → `nome`, `tipo_servico` → `tipo`, `status` → `ativo` (boolean)    |
| 🔴 4     | `onboardingService.ts` + `useOnboarding.ts` + `types/onboarding.ts` | Remove `current_moment`; use `merge_onboarding_state` RPC instead of direct UPDATE                  |
| 🟡 5     | `adminService.ts`                                                   | Remove `tipo_cliente`, `horario_funcionamento`, `prompt_base` from all three interfaces             |
| 🗑️ 6     | `analyticsService.ts` + `useDashboardIndicators.ts`                 | Delete all flagged functions and interfaces (§4)                                                    |

### DB (migration needed)

| Priority | What to create                                                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 🟠 1     | `public.get_recent_activity`, `get_pendencias`, `get_my_insights`, `get_agent_runs_today`, `get_nps_score`, `get_my_dashboard_kpis` |
| 🟠 2     | All 8 `analytics_v2` dimension RPCs (finance, commercial, inventory, supply, marketing, admin, revenue_by_channel, top_clients)     |
| 🟠 3     | `d1_engagement_summary` view (or remove the UI surface)                                                                             |
