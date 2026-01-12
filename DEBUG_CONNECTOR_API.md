# Debug Guide: Connector API "Failed to fetch" Error

## Problem
The Admin Fontes page shows "Erro ao carregar conectores: Failed to fetch"

## Root Cause Analysis

The error "Failed to fetch" is a generic browser error that occurs **before** the server responds. This means:
- ✅ The API is running (we confirmed port 8008 is listening)
- ✅ The endpoints exist (we verified `/connectors/status` in OpenAPI)
- ✅ CORS is configured
- ❌ The request is failing at the browser level

## Most Likely Causes

### 1. **Mixed Content (HTTP/HTTPS)**
If the dashboard is served over HTTPS but trying to call HTTP localhost, browsers block it.

**Check**: Look in browser console for "Mixed Content" warnings

**Solution**: Ensure both frontend and backend use the same protocol

### 2. **User Not Logged In**
The hook checks `if (!auth?.user?.id)` and returns early, but might still show loading error.

**Check**:
```javascript
// Add this console.log to AdminFontesPage.tsx (line ~200)
console.log('Auth user:', auth?.user);
console.log('User ID:', auth?.user?.id);
```

**Solution**: Make sure you're logged in to Supabase

### 3. **Network/Firewall Blocking**
Something is blocking the request to localhost:8008

**Check**: Open browser DevTools → Network tab → Look for failed request

### 4. **ENV Variable Not Loaded**
The .env file might not be loaded properly in the running dashboard.

**Check**:
```javascript
// Add this to connectorStatusService.ts line 8
console.log('API_BASE_URL:', API_BASE_URL);
```

## Step-by-Step Debug Process

### Step 1: Verify You're Logged In
1. Open browser console
2. Run: `localStorage.getItem('sb-haruewffnubdgyofftut-auth-token')`
3. You should see a JWT token
4. If NULL → You need to log in first

### Step 2: Check Network Tab
1. Open DevTools → Network tab
2. Navigate to `/dashboard/admin/fontes`
3. Look for a request to `localhost:8008/connectors/status`
4. Click on it and check:
   - **Status**: Should be 200 (if it's there at all)
   - **Headers**: Check if Authorization Bearer token is present
   - **Response**: See what error message you get

### Step 3: Test API Directly from Browser
Open a new tab and try:
```
http://localhost:8008/health
```

If this works, the API is accessible. If not, check Docker.

### Step 4: Check Console Logs
Add debug logging to `useConnectorStatus.tsx`:

```typescript
useEffect(() => {
  console.log('=== useConnectorStatus Debug ===');
  console.log('auth:', auth);
  console.log('auth.user:', auth?.user);
  console.log('auth.user.id:', auth?.user?.id);

  if (!auth?.user?.id) {
    console.log('No user ID, returning early');
    setConnectors(null);
    setLoading(false);
    return;
  }

  const fetchConnectors = async () => {
    console.log('Fetching connectors for user:', auth.user!.id);
    setLoading(true);
    setError(null);

    try {
      const data = await getConnectorStatus(auth.user!.id);
      console.log('Connectors data received:', data);
      setConnectors(data);
    } catch (err) {
      console.error('Error fetching connectors:', err);
      setError(err instanceof Error ? err : new Error('Failed to fetch connectors'));
    } finally {
      setLoading(false);
    }
  };

  fetchConnectors();
}, [auth?.user?.id, refetchFlag]);
```

### Step 5: Check if Data Exists
The API might be working but returning empty data. Let's verify:

```bash
# Check if there are any credentials in the database
# Run this in Supabase SQL Editor:
SELECT * FROM credencial_servico_externo LIMIT 5;
```

If empty, you have no connectors configured yet!

## Quick Fix: Create Test Data

If the database is empty, create some test data:

```sql
-- Insert a test connector
INSERT INTO credencial_servico_externo (
  client_id,
  nome_conexao,
  tipo_servico,
  status,
  credenciais_json
) VALUES (
  'YOUR_USER_ID_HERE',  -- Replace with your actual user ID from auth.user.id
  'Test BigQuery Connector',
  'bigquery',
  'active',
  '{}'::jsonb
);
```

## Alternative: Use Mock Data for Testing

If you just want to test the UI without the API, you can temporarily mock the data:

**File**: `apps/vizu_dashboard/src/hooks/useConnectorStatus.tsx`

```typescript
// TEMPORARY: Mock data for testing
const MOCK_DATA: ConnectorListResponse = {
  connectors: [
    {
      credential_id: 1,
      nome_conexao: 'BigQuery Test',
      tipo_servico: 'bigquery',
      status: 'active',
      last_sync_at: new Date().toISOString(),
      last_sync_status: 'completed',
      records_count: 1250,
      error_message: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  ],
  total_connected: 1,
  total_pending: 0,
  total_error: 0
};

export const useConnectorStatus = (): UseConnectorStatusReturn => {
  const auth = useContext(AuthContext);
  const [connectors, setConnectors] = useState<ConnectorListResponse | null>(MOCK_DATA); // Use mock
  const [loading, setLoading] = useState(false); // Set to false
  const [error, setError] = useState<Error | null>(null);

  // Comment out the useEffect for now
  // useEffect(() => { ... }, [auth?.user?.id, refetchFlag]);

  const refetch = () => {}; // No-op

  return { connectors, loading, error, refetch };
};
```

## Final Checklist

- [ ] User is logged in (check localStorage for auth token)
- [ ] Dashboard .env has correct API URL (`VITE_DATA_INGESTION_API_URL=http://localhost:8008`)
- [ ] Docker container is running (`docker ps | grep data_ingestion`)
- [ ] API health check works (`curl http://localhost:8008/health`)
- [ ] Browser network tab shows the request being made
- [ ] No CORS or mixed content errors in console
- [ ] Database has at least one connector record for your user ID

## Next Steps

1. **Check browser console** for exact error message
2. **Check network tab** to see if request is even being sent
3. **Verify you're logged in** with a valid Supabase session
4. **Check database** to see if any connector records exist
5. If all else fails, use mock data temporarily to test the UI

---

Once you identify which of these is the issue, let me know and I can help fix it specifically!
