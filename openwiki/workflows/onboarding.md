# Onboarding Workflow

Blu's onboarding is an automatic, low-config wizard that provisions a tenant and builds its data schema. Source: `docs/system_reference/ONBOARDING.md`, `docs/llm_wiki/06_onboarding.md`.

---

## Flow

```text
/auth?mode=signup|login
  → /onboarding (StepAuth)
    → StepInfo (company profile + website detection)
      → StepData (data connection: BigQuery | Google Drive | CSV/XLSX)
        → StepMapping (match-columns + manual review) [conditional]
          → StepLaunch (bootstrap + ETL + post-config)
            → /app (Home)
```

The frontend wizard lives in `apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx`; step components in `components/onboarding/`; draft state in `hooks/useOnboardingDraft.ts`.

---

## Steps

### StepAuth
- Modes: `login` (email+password) or `signup` (email+password or Google OAuth).
- Post-auth routing: new user → `ensure_tenant_row()` creates a provisional `clientes_blu` row → `info`; existing incomplete → `info`; existing complete → `/app`.

### StepInfo
Collects: `nome`, `empresa`, `cnpj`, `website`, `vertical`, `porte`, `primaryFocus`, `produtoServico`. Website triggers scraping via edge function `onboarding-website-intel`; auto-fills if confidence ≥ 0.5.

### StepData
- Systems: BigQuery (active); Shopify/VTEX/PostgreSQL/Conta Azul (planned).
- Files: CSV/XLSX (upload + smart parsing) and Google Drive (Picker API + OAuth scope handling).
- **Credentials collected locally; only sent at StepLaunch.**

### StepMapping (conditional)
- CSV: match-columns runs in StepData (pre-launch).
- BQ/Drive: match-columns after column discovery at StepLaunch (post-launch).
- Groups: ✅ mapped · ⚠ needs confirmation · ✗ unrecognized.
- Canonical schema: 20 fields (`documento`, `data_competencia_id`, `quantidade`, `valor`, `status`, `tipo_lancamento`, `categoria`, `cliente_*`, `fornecedor_*`, `produto_*`).

### StepLaunch
- `onbootstrap`: `client_id`, agents, routines, prompts seeded.
- BigQuery: `createBigQueryCredentialWithDiscovery` (blocking).
- Upload: `upload-csv-source` / `upload-drive-source` → `source_id`.
- ETL: `run-csv-etl` / `run-sync-etl`.
- Google Drive token: `onboarding-capture-drive-token`.
- Post-launch: if BQ/Drive has data → StepMapping; else → `/app`.

---

## Edge Functions

`onboarding-website-intel`, `onboarding-bootstrap`, `onboarding-capture-drive-token`, `match-columns`, `upload-csv-source`, `upload-drive-source`, `run-csv-etl`, `run-sync-etl`, `google-oauth-start`, `google-oauth-callback`, `ensure_tenant_row`, `get_my_client_id`.

Shared helpers in `_shared`: `requireAuth`, `resolveClientId`, `fernetEncrypt` (token encryption).

---

## Draft state

Hook `useOnboardingDraft(user?.email)`. localStorage keys: `blu_onb_{email}`, `onboarding_returning_to_data`, `blu_has_data`.
Defaults: `agents=[compras,financeiro,clientes,agenda,documentos,estrategia]`, `approvalTasks=[make_payment,supplier_order]`, `notifyChannel=email`.

> Note: the draft default `agents` list still references `documentos`/`estrategia` (legacy names). Current canonical agent slugs are `doc-writer` and `strategy` — see [agents/catalog](agents/catalog.md).

---

## Post-launch

- `context-gatherer` runs ingestion/curation (KB, OCR, schema mapping) triggered by `onboarding_complete` and `doc_ingested` webhooks.
- Routines seed from `cross_agent_routines` into `client_routines`.

---

## Next

- Tenant data model → [data-models/schema](data-models/schema.md)
- Background context curation → [agents/catalog](agents/catalog.md) (`context-gatherer`)
- Routine seeding → [routines](architecture/routines.md)
