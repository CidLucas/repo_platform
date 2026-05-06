---
name: add-integration
description: End-to-end playbook for adding a new data source connector to blu_app. Use when implementing any new integration — e-commerce (Nuvemshop, Mercado Livre), accounting (Conta Azul, Contabilizei), ERP, CRM, or database. Covers all 5 touchpoints: Python connector, ConnectorFactory, frontend metadata + form, schema alias enrichment, and icon sourcing.
---

# Add Integration

You are wiring a new integration end-to-end. Five touchpoints, all required.

## Touchpoint map

| # | File | What to do |
|---|------|-----------|
| 1 | `libs/blu_data_connectors/src/blu_data_connectors/<category>/` | New connector class + export |
| 2 | `libs/blu_data_connectors/src/blu_data_connectors/factory.py` | Register `tipo_servico` key + instantiation |
| 3 | `apps/blu_dashboard/src/pages/admin/AdminConnectorsPage.tsx` | `CONNECTOR_METADATA` entry + icon import |
| 4 | `apps/blu_dashboard/src/components/admin/ConnectorModal.tsx` | `prepareCredentials()` + `renderFormFields()` cases |
| 5 | `supabase/functions/match-columns/index.ts` | `COLUMN_ALIASES` entries for native field names |

---

## 1. Python connector

**Reference:** `libs/blu_data_connectors/src/blu_data_connectors/ecommerce/vtex_connector.py`

- E-commerce (orders/products/customers) → extend `EcommerceBaseConnector`
- Accounting/ERP/CRM → extend `AbstractDataConnector` directly
- Required methods: `validate_connection()`, `fetch_schema()`, `extract_data()`, `get_connection_string()`
- Raise `AuthenticationError` in `__init__` when required credentials are absent
- `validate_connection()` must return `bool` — never raise

Export from `<category>/__init__.py`, following the pattern in `ecommerce/__init__.py`.

## 2. ConnectorFactory

**Reference:** `libs/blu_data_connectors/src/blu_data_connectors/factory.py`

Add `"CONTA_AZUL": "conta_azul"` to `_CONNECTOR_MAP`, an `elif tipo == "CONTA_AZUL"` branch in `create_connector`, and its supported resources in `get_supported_resources`.

The `tipo_servico` key is always `UPPER_SNAKE_CASE`.

## 3. Frontend metadata

**Reference:** `CONNECTOR_METADATA` object in `AdminConnectorsPage.tsx` (~line 71)

```tsx
CONTA_AZUL: {
  id: 'conta_azul',        // lowercase_underscore — must match Modal cases
  name: 'Conta Azul',
  description: 'NFs, contas e financeiro',
  icon: FiFileText,        // or SiContaazul if it exists in react-icons/si
  iconColor: '#0066FF',    // official brand HEX
  category: 'api',         // 'ecommerce' | 'database' | 'files' | 'api'
  isNew: true,
},
```

Icon selection order: `react-icons/si` → `react-icons/fa` → semantic fallback already imported (`FiFileText`, `FiShoppingCart`, `FiDatabase`).

Also add the credentials interface + extend `ConnectorPlatform` union in `connectorService.ts`.

## 4. ConnectorModal

**Reference:** `apps/blu_dashboard/src/components/admin/ConnectorModal.tsx`

Add a `case 'conta_azul':` to **both** switch statements:

- `prepareCredentials()` — pack `formData` fields into the credential object
- `renderFormFields()` — use `DARK_INPUT_PROPS` / `DARK_TEXTAREA_PROPS` / `DARK_SELECT_PROPS` (already defined at top of file). Add `FormHelperText` pointing users to where they find each credential in the source platform's UI. Passwords always get `type="password"`.

## 5. Schema aliases

**Reference:** `COLUMN_ALIASES` in `supabase/functions/match-columns/index.ts` (~line 130)

Add the connector's native field names as aliases under the relevant canonical columns. At minimum cover the three required fields:

```typescript
documento:           [...existing, "numero_nota", "chave_nfe", "document_number"],
data_competencia_id: [...existing, "data_emissao", "issue_date", "competencia"],
valor:               [...existing, "valor_total",  "total_amount", "vl_total"],
```

Aliases must be lowercase. Add `CONTEXT_SIGNAL_COLUMNS` entries when the connector's field names clearly indicate entity context (emitter → `"supplier"`, destinatario → `"customer"`).

---

For archetypes (accounting, e-commerce, CRM/ERP), pagination patterns, `connectorService.ts` additions, and common pitfalls → see [REFERENCE.md](REFERENCE.md).

## Verification

- [ ] `id` in CONNECTOR_METADATA === `case` keys in both Modal switches
- [ ] `tipo_servico` UPPER_SNAKE_CASE in factory === key in CONNECTOR_METADATA
- [ ] `validate_connection()` returns bool, never throws
- [ ] All required form fields have `isRequired`
- [ ] `documento`, `data_competencia_id`, `valor` aliases present in match-columns
