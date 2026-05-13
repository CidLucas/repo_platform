## Schema Mapping

When the user uploads a spreadsheet or describes a data source, follow this process:

### Step 1 — Understand the Source
Call `list_data_sources` to show what is already mapped. Ask the user: what does this source track, what period does it cover, and who maintains it?

### Step 2 — Propose Mappings
Call `suggest_column_mapping`. Present proposals in a table:

| Source Column | Proposed Mapping | Confidence | Reason |
|---|---|---|---|
| "Cust ID" | customers.erp_id | 0.85 | Values match existing ERP customer codes |
| "Val" | transactions.amount | 0.70 | Numeric column, currency-like values |

### Step 3 — Resolve Ambiguities
For any column where confidence < 0.80 or two mappings are equally plausible, ask the user directly in your response — one question per ambiguous column. Never silently resolve low-confidence mappings or call any tool to do so.

### Step 4 — Confirm and Store
Present the **complete** mapping table in your response before storing. Ask "Confirma? (sim / não)". Only call `update_schema_mapping` after the user explicitly confirms. When confirming, explain the downstream impact: "Once stored, the Data Analyst skill will be able to query your sheet directly."
