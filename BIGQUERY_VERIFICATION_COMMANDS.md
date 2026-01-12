# BigQuery Verification Commands

## 1. List all datasets in your project
```bash
bq ls --project_id=analytics-big-query-242119
```

## 2. List all tables in the dataform dataset
```bash
bq ls --project_id=analytics-big-query-242119 dataform
```

## 3. Get details about a specific table
```bash
bq show --project_id=analytics-big-query-242119 dataform.productsinvoices
```

## 4. Check if table exists (will error if not)
```bash
bq head --project_id=analytics-big-query-242119 dataform.productsinvoices
```

## Expected Output Examples

If table exists:
```
+----------+
| column_1 |
+----------+
| value1   |
| value2   |
+----------+
```

If table doesn't exist:
```
Error parsing arguments: Cannot find dataset dataform.productsinvoices
```

## Important Finding

We found TWO servers in your Supabase:

1. **Correct Server:**
   - project_id: `analytics-big-query-242119` ✅ (with hyphen)
   - dataset_id: `dataform` ✅
   - location: `US` ✅

2. **Incorrect Server (OLD):**
   - project_id: `analytics-big-query242119` ❌ (MISSING hyphen)
   - dataset_id: `productsinvoices` ❌ (this is a table name, not dataset)
   - location: `US`

The incorrect server should be deleted. Use these commands:

```bash
# Delete the incorrect server and its foreign tables
psql <SUPABASE_CONNECTION_STRING> -c "
  drop server if exists bigquery_c_760f2c80_bde0_4522_9615_1bb85c3bb28d cascade;
  delete from public.bigquery_servers where client_id = 'c_760f2c80_bde0_4522_9615_1bb85c3bb28d';
"
```

Or via Supabase dashboard SQL editor:
```sql
drop server if exists bigquery_c_760f2c80_bde0_4522_9615_1bb85c3bb28d cascade;
delete from public.bigquery_servers where client_id = 'c_760f2c80_bde0_4522_9615_1bb85c3bb28d';
delete from vault.secrets where name like '%c_760f2c80%';
```

## Run These Commands

Please run:
1. `bq ls --project_id=analytics-big-query-242119 dataform` - to list all tables
2. Share the output so we know the exact table names available
3. Confirm which table name matches what the user is trying to connect to
