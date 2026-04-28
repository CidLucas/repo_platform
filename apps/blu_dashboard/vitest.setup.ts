// Provide stub Supabase env vars so modules that init the client at
// import-time (apps/blu_dashboard/src/lib/supabase.ts) don't throw under
// vitest. Tests must NOT rely on real network calls.
import { vi } from 'vitest';

vi.stubEnv('VITE_SUPABASE_URL', 'http://localhost:54321');
vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'test-anon-key');
