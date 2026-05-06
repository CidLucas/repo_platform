# add-integration — Reference

## Pre-implementation questionnaire

Answer before writing any code:

1. What data does it expose? (orders, invoices, transactions, products, customers…)
2. How does it authenticate? (OAuth2, API Key, Basic Auth, Client ID+Secret)
3. What are its rate limits and pagination model? (cursor, page+limit, offset, link header)
4. What category? → e-commerce: `'ecommerce'` / accounting-ERP-CRM: `'api'` / SQL: `'database'`
5. Does a `react-icons/si` entry exist? Icon decision order: `si` → `fa` → semantic fallback already imported (`FiFileText`, `FiShoppingCart`, `FiDatabase`)
6. What is the official brand HEX color?

---

## Base class selection

```
REST API with products/orders/customers/inventory
  └── extend EcommerceBaseConnector
        required: validate_connection, get_products, get_orders, get_customers, get_inventory, get_connection_string

Accounting / ERP / CRM / anything else
  └── extend AbstractDataConnector directly
        required: validate_connection, fetch_schema, extract_data, get_connection_string
        add: get_invoices(), get_transactions(), get_accounts_payable(), …
```

---

## Pagination patterns

**Page-based** (most common — Conta Azul, Loja Integrada):
```python
async def get_invoices(self, limit: int = 100, page: int = 1) -> list[dict]:
    response = await self._make_request("GET", "/invoices", params={"per_page": min(limit, 200), "page": page})
    return response if isinstance(response, list) else response.get("data", [])
```

**Cursor-based** (Mercado Livre, some REST APIs):
```python
async def get_orders(self, limit: int = 100, cursor: str | None = None):
    params = {"limit": limit}
    if cursor:
        params["scroll_id"] = cursor
    response = await self._make_request("GET", "/orders/search", params=params)
    return response.get("results", []), response.get("scroll_id")
```

Stop condition in `extract_data`: `len(data) < chunk_size` → no more pages.

---

## Integration archetypes

### Accounting (Conta Azul, Contabilizei, Omie, Bling)

- Auth: OAuth2 or Client ID + Secret
- Resources: `invoices` (NF-e/NFS-e), `accounts_payable`, `accounts_receivable`, `entries`
- Category: `'api'`
- Canonical focus: `documento` (NF number or chave), `data_competencia_id`, `valor`, `fornecedor_cnpj`, `cliente_cpf_cnpj`
- Base URL pattern: `https://api.<platform>.com.br/v1`

Key aliases to add in `match-columns`:
```typescript
documento:           ["numero_nota", "chave_nfe", "document_number", "numero_nf"],
data_competencia_id: ["data_emissao", "issue_date", "competencia", "dt_emissao"],
valor:               ["valor_total",  "total_amount", "vl_total", "valor_liquido"],
fornecedor_cnpj:     ["cnpj_emitente", "issuer_cnpj", "emitente_cnpj"],
fornecedor_nome:     ["nome_emitente", "issuer_name", "razao_social_emitente"],
cliente_cpf_cnpj:    ["cnpj_destinatario", "destinatario_cnpj", "recipient_cnpj"],
```

Context signals:
```typescript
"cnpj_emitente": "supplier",   "issuer_cnpj": "supplier",
"cnpj_destinatario": "customer", "destinatario": "customer",
```

### E-commerce marketplace (Nuvemshop, Mercado Livre, Magento)

- Extend `EcommerceBaseConnector` — implement the 4 abstract resource methods
- Resources: products, orders, customers, inventory
- Category: `'ecommerce'`
- Mercado Livre rate limit is strict (60 req/min free tier) — override `_make_request` with backoff if needed

### CRM / ERP (Salesforce, HubSpot, SAP)

- Extend `AbstractDataConnector` directly
- Resources depend on client config — expose as a multi-select in the form
- Category: `'api'`
- OAuth flows require a separate modal type — flag and implement basic API key path first

---

## connectorService.ts additions

For each new connector, add in `apps/blu_dashboard/src/services/connectorService.ts`:

```typescript
// 1. Credentials interface
export interface ContaAzulCredentials {
  client_id: string;
  client_secret: string;
  access_token?: string;
}

// 2. Extend the platform union
export type ConnectorPlatform =
  | 'shopify' | 'vtex' | 'loja_integrada' | 'bigquery' | 'postgresql' | 'mysql'
  | 'conta_azul' | 'contabilizei';  // ← add here
```

---

## Common pitfalls

**`id` coupling** — `connector.id` in CONNECTOR_METADATA, `case` keys in both Modal switches, and `tipo_servico.toUpperCase().replace('-','_')` in `handleSubmit` must all resolve to the same string. One mismatch silently skips the connector's credential form.

**`validate_connection()` must return bool** — a raised exception instead of `return False` breaks the modal's sync flow with an unhandled error toast.

**COLUMN_ALIASES keys must be existing canonical names** — adding `"valor_total": [...]` as a top-level key does nothing. It must be nested under `valor: [..., "valor_total"]`.

**Icon color must be a CSS hex string** — not a Tailwind class or named color. It is used in `borderColor` and `boxShadow` CSS-in-JS expressions.

**Don't hardcode `client_id` in the connector** — connectors receive only the credentials dict. The Supabase client ID comes from the auth context in the frontend.
