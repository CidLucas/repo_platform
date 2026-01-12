# Quick Fix: Admin Fontes Page "Failed to fetch" Error

## TL;DR - Most Likely Fix

**You're probably not logged in or your session expired.**

### Solution:
1. Go to `/` (home page)
2. Click "Login with Google"
3. After logging in successfully, navigate to `/dashboard/admin/fontes`

---

## Why This Happens

The Admin Fontes page calls the data_ingestion_api which requires JWT authentication. If you're not logged in, the fetch fails with "Failed to fetch" because:

1. No auth token is sent in the request
2. Server returns 401 Unauthorized
3. Browser shows generic "Failed to fetch"

## How to Verify You're Logged In

### Method 1: Check Browser Console
```javascript
// Open browser console (F12) and run:
localStorage.getItem('sb-haruewffnubdgyofftut-auth-token')
```

**Expected**: Should return a JSON object with `access_token`
**If NULL**: You need to log in

### Method 2: Check Network Tab
1. Open DevTools → Network tab
2. Navigate to `/dashboard/admin/fontes`
3. Look for request to `localhost:8008/connectors/status`
4. Check the request **Headers** tab:
   - Should see `Authorization: Bearer eyJ...`
   - If missing → Not logged in

---

## Temporary Fix for Testing: Bypass Auth Check

If you just want to test the UI without logging in, you can temporarily disable the auth check:

### Option 1: Mock the Hook (Easiest)

**File**: `apps/vizu_dashboard/src/hooks/useConnectorStatus.tsx`

Replace the entire file with:

```typescript
import { useState } from 'react';
import { ConnectorListResponse } from '../services/connectorStatusService';

export const useConnectorStatus = () => {
  // Return empty list (this is what happens when no connectors are configured)
  const [connectors] = useState<ConnectorListResponse>({
    connectors: [],
    total_connected: 0,
    total_configured: 0,
    total_pending: 0,
    total_error: 0,
  });

  const [loading] = useState(false);
  const [error] = useState<Error | null>(null);
  const refetch = () => {};

  return { connectors, loading, error, refetch };
};
```

This will show the page with zero connectors (which is correct for a new user).

### Option 2: Add Sample Connector

If you want to see the UI with a sample connector:

```typescript
import { useState } from 'react';
import { ConnectorListResponse } from '../services/connectorStatusService';

export const useConnectorStatus = () => {
  const [connectors] = useState<ConnectorListResponse>({
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
    total_configured: 1,
    total_pending: 0,
    total_error: 0,
  });

  const [loading] = useState(false);
  const [error] = useState<Error | null>(null);
  const refetch = () => {};

  return { connectors, loading, error, refetch };
};
```

---

## Real Fix: Ensure Authentication Works

### 1. Check AuthContext

Add logging to see if auth is working:

**File**: `apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx`

Add this near the top of the component (around line 200):

```typescript
function AdminFontesPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();

  // ADD THIS DEBUG CODE:
  const auth = useContext(AuthContext); // Import from '../contexts/AuthContext'

  useEffect(() => {
    console.log('=== AdminFontesPage Auth Debug ===');
    console.log('Auth:', auth);
    console.log('User:', auth?.user);
    console.log('User ID:', auth?.user?.id);
  }, [auth]);
  // END DEBUG CODE

  // ... rest of component
```

### 2. Check what the hook sees

**File**: `apps/vizu_dashboard/src/hooks/useConnectorStatus.tsx`

Add logging at the top of the useEffect (line ~25):

```typescript
useEffect(() => {
  console.log('=== useConnectorStatus Debug ===');
  console.log('auth:', auth);
  console.log('auth.user:', auth?.user);
  console.log('auth.user.id:', auth?.user?.id);

  if (!auth?.user?.id) {
    console.log('❌ No user ID - returning early');
    setConnectors(null);
    setLoading(false);
    return;
  }

  console.log('✅ User ID found:', auth.user.id);
  console.log('📡 Fetching connectors...');

  // ... rest of useEffect
}, [auth?.user?.id, refetchFlag]);
```

### 3. Check the actual API call

**File**: `apps/vizu_dashboard/src/services/connectorStatusService.ts`

Add logging to the fetch (around line 106):

```typescript
export async function getConnectorStatus(
  clienteVizuId: string
): Promise<ConnectorListResponse> {
  const token = await getAuthToken();

  console.log('=== getConnectorStatus Debug ===');
  console.log('Client ID:', clienteVizuId);
  console.log('Token exists:', !!token);
  console.log('API URL:', `${API_BASE_URL}/connectors/status?client_id=${clienteVizuId}`);

  const response = await fetch(
    `${API_BASE_URL}/connectors/status?client_id=${clienteVizuId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  console.log('Response status:', response.status);
  console.log('Response OK:', response.ok);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch connector status' }));
    console.error('API Error:', error);
    throw new Error(error.detail || 'Failed to fetch connector status');
  }

  const data = await response.json();
  console.log('Success! Data:', data);
  return data;
}
```

---

## Expected Console Output (When Working)

```
=== AdminFontesPage Auth Debug ===
Auth: {user: {…}, session: {…}}
User: {id: "abc123...", email: "user@example.com", ...}
User ID: abc123...

=== useConnectorStatus Debug ===
auth: {user: {…}}
auth.user: {id: "abc123..."}
auth.user.id: abc123...
✅ User ID found: abc123...
📡 Fetching connectors...

=== getConnectorStatus Debug ===
Client ID: abc123...
Token exists: true
API URL: http://localhost:8008/connectors/status?client_id=abc123...
Response status: 200
Response OK: true
Success! Data: {connectors: [], total_connected: 0, ...}
```

## Expected Console Output (When NOT Logged In)

```
=== AdminFontesPage Auth Debug ===
Auth: {user: null, session: null}
User: null
User ID: undefined

=== useConnectorStatus Debug ===
auth: {user: null}
auth.user: null
auth.user.id: undefined
❌ No user ID - returning early
```

---

## Next Steps

1. **Add the debug logging above**
2. **Refresh the page**
3. **Check browser console**
4. **Tell me what you see**

The output will tell us exactly where the problem is:
- No auth object → AuthContext not working
- No user → Not logged in
- User but no token → Session expired
- Token but request fails → API issue

Let me know what the console shows and we can fix it!
