# RLS Security Guide for File Upload API

## Overview

This guide explains how Row Level Security (RLS) is implemented in the file upload API to ensure that each cliente_vizu can only access their own data.

## Architecture

### Data Flow
1. Client uploads file → Authenticated with JWT (client_id extracted)
2. File stored in Supabase Storage → Bucket path: `{client_id}/{job_id}-{filename}`
3. Record created in `fonte_de_dados` table → With RLS policies enforced
4. Response returned → With tracking IDs

### Security Layers

#### 1. Storage Bucket Policies (Supabase Storage)

Configure bucket policies in Supabase Dashboard for the `file-uploads` bucket:

```sql
-- Allow users to upload files to their own folder
CREATE POLICY "Users can upload to their own folder"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'file-uploads' AND
  (storage.foldername(name))[1] = auth.jwt() ->> 'client_id'
);

-- Allow users to read files from their own folder
CREATE POLICY "Users can read their own files"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'file-uploads' AND
  (storage.foldername(name))[1] = auth.jwt() ->> 'client_id'
);

-- Allow users to delete their own files
CREATE POLICY "Users can delete their own files"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'file-uploads' AND
  (storage.foldername(name))[1] = auth.jwt() ->> 'client_id'
);
```

#### 2. Database RLS Policies (`fonte_de_dados` table)

Configure RLS policies for the `fonte_de_dados` table:

```sql
-- Enable RLS on the table
ALTER TABLE fonte_de_dados ENABLE ROW LEVEL SECURITY;

-- Allow users to insert their own records
CREATE POLICY "Users can insert their own fonte_de_dados"
ON fonte_de_dados FOR INSERT
WITH CHECK (
  client_id::text = auth.jwt() ->> 'client_id'
);

-- Allow users to read their own records
CREATE POLICY "Users can read their own fonte_de_dados"
ON fonte_de_dados FOR SELECT
USING (
  client_id::text = auth.jwt() ->> 'client_id'
);

-- Allow users to update their own records
CREATE POLICY "Users can update their own fonte_de_dados"
ON fonte_de_dados FOR UPDATE
USING (
  client_id::text = auth.jwt() ->> 'client_id'
);

-- Allow users to delete their own records
CREATE POLICY "Users can delete their own fonte_de_dados"
ON fonte_de_dados FOR DELETE
USING (
  client_id::text = auth.jwt() ->> 'client_id'
);
```

## Security Features Implemented

### 1. JWT-Based Authentication
- Every request must include a valid JWT token
- Token contains `client_id` claim
- `get_client_id_from_token` dependency extracts and validates the ID

### 2. Path-Based Isolation (Storage)
- Files stored at: `{client_id}/{job_id}-{filename}`
- Bucket policies enforce that users can only access their own folder
  - Prevents cross-client file access

### 3. Database RLS (fonte_de_dados)
- RLS policies automatically filter queries by `client_id`
- Even if SQL injection occurs, RLS prevents data leakage
- Server-side enforcement (cannot be bypassed from client)

### 4. Transaction Rollback
- If database registration fails, uploaded file is automatically deleted
- Ensures consistency between storage and database
- Prevents orphaned files

## Testing RLS Security

### Test 1: Verify Storage Isolation
```bash
# Try to access another client's file (should fail)
curl -H "Authorization: Bearer {jwt_cliente_a}" \
  "https://{project}.supabase.co/storage/v1/object/public/file-uploads/{cliente_b}/{file}"
# Expected: 403 Forbidden
```

### Test 2: Verify Database Isolation
```sql
-- As cliente_a, try to query cliente_b's records
SELECT * FROM fonte_de_dados WHERE client_id = '{cliente_b_id}';
-- Expected: Returns empty (RLS filters it out)
```

### Test 3: Verify Upload Works
```bash
# Upload file as cliente_a
curl -X POST -H "Authorization: Bearer {jwt_cliente_a}" \
  -F "file=@test.pdf" \
  "https://your-api.com/upload"
# Expected: 201 Created with fonte_de_dados_id
```

## Common Issues

### Issue 1: RLS Policy Not Working
**Symptom**: Users can see other clients' data
**Solution**:
1. Verify RLS is enabled: `SELECT relrowsecurity FROM pg_class WHERE relname = 'fonte_de_dados';`
2. Check JWT claim name matches: `auth.jwt() ->> 'client_id'`
3. Ensure Supabase client is using service_role key for bypasses (admin operations only)

### Issue 2: Cannot Insert Records
**Symptom**: `new row violates row-level security policy`
**Solution**:
1. Verify JWT contains `client_id` claim
2. Check that INSERT policy WITH CHECK matches the client_id being inserted
3. Ensure data types match (UUID vs text)

### Issue 3: Files Uploaded but Not Registered
**Symptom**: Files in storage but no database record
**Solution**:
1. Check application logs for database errors
2. Verify transaction rollback is working
3. Ensure `fonte_de_dados` table has all required fields

## Migration Checklist

When setting up a new environment:

- [ ] Create `file-uploads` bucket in Supabase Storage
- [ ] Configure storage bucket policies (see above)
- [ ] Enable RLS on `fonte_de_dados` table
- [ ] Create RLS policies for `fonte_de_dados` (see above)
- [ ] Add `client_id` claim to JWT tokens
- [ ] Test upload with valid JWT
- [ ] Test that cross-client access is blocked
- [ ] Verify rollback works on database errors

## Monitoring

### Metrics to Track
1. Failed uploads (rollback triggered)
2. RLS policy violations (should be 0 if working correctly)
3. Orphaned files (files without database records)
4. Cross-client access attempts (security audit)

### Logs to Review
```python
# Success case
logger.info(f"fonte_de_dados registered with ID: {fonte_id}")

# Rollback case
logger.error(f"Job [{job_id}]: Database registration failed. Rolling back storage upload.")

# Critical failure
logger.error(f"Job [{job_id}]: CRITICAL - Failed to delete file during rollback")
```

## Best Practices

1. **Always use JWT authentication** - Never bypass authentication for uploads
2. **Never use service_role key in client** - Only in server-side admin operations
3. **Test RLS policies in staging** - Before deploying to production
4. **Monitor rollback logs** - Indicates system health issues
5. **Regular security audits** - Verify no cross-client data leakage
6. **Keep JWT claims minimal** - Only include necessary information
7. **Use HTTPS only** - Prevent token interception

## References

- [Supabase Storage RLS](https://supabase.com/docs/guides/storage/security/access-control)
- [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
