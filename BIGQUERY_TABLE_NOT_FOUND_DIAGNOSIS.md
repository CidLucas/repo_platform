# BigQuery Table Not Found - Diagnosis

## Error Message Analysis

```
Not found: Table analytics-big-query-242119:dataform.productsinvoices
was not found in location US
```

### Components Extracted:
- **Project ID**: `analytics-big-query-242119` ✅
- **Dataset ID**: `dataform` ✅
- **Table Name**: `productsinvoices` ❓ **VERIFY THIS EXISTS**
- **Location**: `US` ✅

## FDW Syntax Verification ✅

According to [fdw.dev/catalog/bigquery/](https://fdw.dev/catalog/bigquery/):

### Subquery Format (What We're Using)
```sql
table '(select * from `project-id`.`dataset`.`table`)'
```

✅ **CORRECT** - We're using backticks around fully-qualified names
✅ **CORRECT** - Location parameter is set to US
✅ **CORRECT** - Server configuration has dataset_id and project_id

Current SQL generated:
```sql
table '(select * from `analytics-big-query-242119`.`dataform`.`productsinvoices`)'
location 'US'
```

## Database Configuration Verification

### Metadata Check ✅
```sql
select table_name, foreign_table_name, bigquery_table, location
from public.bigquery_foreign_tables;
```

Result:
```
table_name: productsinvoices
foreign_table_name: bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_productsinvoices
bigquery_table: `analytics-big-query-242119`.`dataform`.`productsinvoices`
location: US
```

### Server Configuration ✅
```sql
select srvname, srvoptions
from pg_foreign_server
where srvname = 'bigquery_e0e9c949_18fe_4d9a_9295_d5dfb2cc9723';
```

Result:
```
srvname: bigquery_e0e9c949_18fe_4d9a_9295_d5dfb2cc9723
options:
  - sa_key_id: 8a68785f-9a07-4928-8d77-3a88f39520e6
  - project_id: analytics-big-query-242119 ✅
  - dataset_id: dataform ✅
  - (location defaults to US) ✅
```

## Root Cause: TABLE DOESN'T EXIST IN BIGQUERY

The error is **not** a syntax error. The FDW is correctly:
1. ✅ Connecting to BigQuery
2. ✅ Using correct project/dataset/location
3. ✅ Formatting the table name correctly
4. ❌ **Finding the table** - IT DOESN'T EXIST

## Action Required

### Option 1: Verify Table Exists in BigQuery
```bash
# List tables in the dataform dataset
gcloud bigquery tables list \
  --dataset_id=dataform \
  --project_id=analytics-big-query-242119

# Check if productsinvoices exists
gcloud bigquery tables show \
  analytics-big-query-242119:dataform.productsinvoices
```

### Option 2: Check Correct Table Name
The table might be named differently:
- `products_invoices` (with underscore)?
- `invoices` (just invoices)?
- `orders` (different name)?
- In a different dataset?

```bash
# List all tables in all datasets
gcloud bigquery ls -d -p analytics-big-query-242119
```

### Option 3: Create Test Table (for testing)
```bash
# In BigQuery console or gcloud
bq mk --table \
  analytics-big-query-242119:dataform.productsinvoices \
  'id:INTEGER,name:STRING'
```

## Next Steps

1. **Verify table exists** using one of the `gcloud bigquery` commands above
2. **If table exists**: Share the exact table name (may have typo)
3. **If table doesn't exist**:
   - Either create it in BigQuery
   - OR update the connector to point to the correct table name
   - OR point to different dataset

## FDW Documentation Reference

The FDW itself is working correctly. Reference from docs:

> **Options**
> - `table` - Source table or view name in BigQuery, required
> - `location` - Source table location (default: 'US')
>
> When using subquery, full qualified table name must be used.

✅ We are using fully-qualified name with subquery format
✅ We are specifying location
✅ We are using backticks (required for hyphenated project IDs)

**The issue is that `productsinvoices` table does not exist in the `dataform` dataset.**
