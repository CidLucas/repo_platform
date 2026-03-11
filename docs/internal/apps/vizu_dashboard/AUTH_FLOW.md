# Authentication Flow Documentation

## Overview

The vizu_dashboard uses Supabase Auth for authentication with support for:
- Email/Password authentication
- Social login (Google, Microsoft, Apple)
- Protected routes with role-based access control
- Automatic session management

## Architecture

### Key Components

1. **AuthContext** (`src/contexts/AuthContext.tsx`)
   - Manages global auth state
   - Provides user session and authentication methods
   - Auto-refreshes on auth state changes

2. **useAuth Hook** (`src/hooks/useAuth.tsx`)
   - Provides access to AuthContext
   - Must be used within AuthProvider

3. **useUserProfile Hook** (`src/hooks/useUserProfile.tsx`)
   - Extracts and formats user profile data
   - Handles full_name, email, initials, and admin status
   - Provides fallbacks for missing data

4. **PrivateRoute** (`src/routes/PrivateRoute.tsx`)
   - Protects dashboard routes
   - Redirects to /login if not authenticated
   - Shows loading spinner during auth check

5. **AdminRoute** (`src/routes/AdminRoute.tsx`)
   - Protects admin-only routes
   - Checks for admin role in user metadata
   - Shows access denied page for non-admins

## User Data Flow

### User Metadata Structure

```typescript
{
  user: {
    id: string,
    email: string,
    user_metadata: {
      full_name?: string,      // Display name
      name?: string,            // Alternative name field
      role?: 'admin' | 'user'  // User role
    },
    app_metadata: {
      role?: 'admin' | 'user'  // System-level role
    }
  }
}
```

### Display Name Priority

1. `user_metadata.full_name`
2. `user_metadata.name`
3. Email username (part before @)
4. Fallback: "Usuário"

### Admin Check Priority

1. `user_metadata.role === 'admin'`
2. `app_metadata.role === 'admin'`
3. Default: `false`

## Configuration

### Environment Variables

Required in `apps/vizu_dashboard/.env`:

```env
# Supabase Configuration
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# Optional: Bypass auth in development
VITE_DEV_BYPASS_AUTH=false
```

### Supabase Setup

1. **Get your credentials** from Supabase Dashboard:
   - Project Settings > API
   - Copy "Project URL" to `VITE_SUPABASE_URL`
   - Copy "anon/public" key to `VITE_SUPABASE_ANON_KEY`

2. **Enable Auth Providers** in Supabase Dashboard:
   - Authentication > Providers
   - Enable Google, Microsoft, Apple as needed
   - Configure redirect URLs

## Setting User Metadata

### Option 1: During Signup (Programmatic)

```typescript
const { error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password',
  options: {
    data: {
      full_name: 'John Doe',
      role: 'user' // or 'admin'
    }
  }
});
```

### Option 2: Update Existing User

```typescript
const { error } = await supabase.auth.updateUser({
  data: {
    full_name: 'John Doe',
    role: 'admin'
  }
});
```

### Option 3: Via Supabase Dashboard

1. Go to Authentication > Users
2. Click on a user
3. Scroll to "User Metadata" section
4. Add/Edit metadata:
   ```json
   {
     "full_name": "John Doe",
     "role": "admin"
   }
   ```

### Option 4: Via SQL (for app_metadata)

```sql
-- Set admin role in app_metadata
UPDATE auth.users
SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
WHERE email = 'admin@example.com';
```

## Route Protection

### Public Routes
- `/` - Landing page
- `/login` - Login page

### Protected Routes (requires authentication)
- `/dashboard/*` - All dashboard pages

### Admin Routes (requires admin role)
- `/dashboard/admin/*` - All admin pages

## Troubleshooting

### Issue: User data not showing

**Possible causes:**
1. User not logged in - check `auth.user` in console
2. Supabase env vars incorrect - verify `.env` file
3. User metadata not set - set via methods above

**Solution:**
```javascript
// Check auth state in browser console
console.log('Auth user:', auth?.user);
console.log('User metadata:', auth?.user?.user_metadata);
```

### Issue: Always seeing "Usuário" instead of name

**Cause:** No `full_name` in user metadata

**Solution:** Set full_name using one of the methods above

### Issue: Can't access admin pages

**Cause:** User doesn't have admin role

**Solution:**
1. Check current role: `console.log(auth?.user?.user_metadata?.role)`
2. Set admin role via Supabase Dashboard or SQL

### Issue: Stuck on loading screen

**Possible causes:**
1. Invalid Supabase credentials
2. Network issues
3. CORS configuration

**Solution:**
1. Verify env variables
2. Check browser network tab for errors
3. Check Supabase dashboard for CORS settings

## Development Mode

To bypass authentication during development:

1. Set in `.env`:
   ```env
   VITE_DEV_BYPASS_AUTH=true
   ```

2. Restart dev server

**Warning:** Never use this in production!

## Security Best Practices

1. **Never commit** Supabase keys to git
2. **Use environment variables** for all sensitive data
3. **Set up RLS policies** in Supabase for data access
4. **Enable MFA** for admin accounts
5. **Regular** audit user roles and permissions

## API Integration

When making API calls with authentication:

```typescript
const token = auth?.session?.access_token;

const response = await fetch('/api/endpoint', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

## Session Management

- Sessions auto-refresh via Supabase
- Session data stored in local storage
- Logout clears session and redirects to /login
- Session expires after inactivity (configurable in Supabase)

## Migration Guide

If migrating from hardcoded values to auth context:

1. Replace all hardcoded user names with `useUserProfile` hook
2. Replace admin checks with role-based checks
3. Wrap admin routes with `AdminRoute` component
4. Set user metadata for existing users
5. Test all auth flows thoroughly

## Example Usage

```typescript
import { useUserProfile } from '../hooks/useUserProfile';

function MyComponent() {
  const profile = useUserProfile();

  if (!profile) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h1>Hello, {profile.full_name}!</h1>
      <p>Email: {profile.email}</p>
      <p>Initials: {profile.initials}</p>
      {profile.isAdmin && <p>Admin Access Granted</p>}
    </div>
  );
}
```
