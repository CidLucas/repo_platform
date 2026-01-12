# Supabase MCP Setup for Claude Desktop

## Issue 1: SQL Script Fixed ✅

The `COPY_PASTE_TO_SUPABASE.sql` has been updated to handle both views AND tables.

**What Changed:**
- Now drops both views and tables before creating new ones
- Ensures clean slate for RLS-enabled tables

**Run this again in Supabase SQL Editor:**
1. Copy updated `COPY_PASTE_TO_SUPABASE.sql`
2. Paste in Supabase Dashboard → SQL Editor
3. Run
4. Should work without errors now ✅

## Issue 2: Claude MCP Setup

The `claude` CLI command is not automatically available even with Claude Desktop installed.

### Option A: Configure MCP via Claude Desktop UI (Recommended)

**Steps:**

1. **Open Claude Desktop App** (already installed at `/Applications/Claude.app`)

2. **Open Settings:**
   - macOS: `Claude → Settings` (or `Cmd+,`)

3. **Navigate to Developer:**
   - Click on "Developer" tab

4. **Add Supabase MCP Server:**
   - Click "Edit Config" or similar
   - This opens your MCP config file at: `~/Library/Application Support/Claude/claude_desktop_config.json`

5. **Add Supabase Server Configuration:**

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-supabase"
      ],
      "env": {
        "SUPABASE_URL": "https://haruewffnubdgyofftut.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "<your-service-role-key>"
      }
    }
  }
}
```

6. **Get Your Service Role Key:**
   - Go to Supabase Dashboard
   - Project Settings → API
   - Copy `service_role` key (NOT anon key)
   - Paste in the config above

7. **Restart Claude Desktop**

8. **Verify:**
   - Open a new conversation in Claude Desktop
   - Type: "Can you list my Supabase tables?"
   - Claude should now have access to your Supabase database

### Option B: Manual Config File Edit

If the UI method doesn't work:

```bash
# Create or edit the config file
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Paste this configuration:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-supabase"],
      "env": {
        "SUPABASE_URL": "https://haruewffnubdgyofftut.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "YOUR_SERVICE_ROLE_KEY_HERE"
      }
    }
  }
}
```

Save (`Ctrl+O`, `Enter`, `Ctrl+X`) and restart Claude Desktop.

### Option C: Use Supabase CLI Instead (Alternative)

If you just need to run migrations without MCP:

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Link to your project
supabase link --project-ref haruewffnubdgyofftut
# Enter password: tMz1us7KsAHQs6QT

# Push migrations
supabase db push
```

## Troubleshooting

### "command not found: claude"

This is expected. The `claude` CLI command is not part of Claude Desktop. You configure MCP through:
- The Claude Desktop UI (Settings → Developer)
- Or by editing `claude_desktop_config.json` directly

### "Error: It seems there is already an App at '/Applications/Claude.app'"

This is fine - Claude Desktop is already installed. Just configure MCP using Option A or B above.

### How to Get Service Role Key

1. Go to https://supabase.com/dashboard
2. Select project: `haruewffnubdgyofftut`
3. Settings (gear icon) → API
4. Under "Project API keys", copy the `service_role` secret key
5. ⚠️ **Keep this secret!** Don't commit to git

### Verify MCP is Working

After configuration:

1. **Restart Claude Desktop completely**
2. **Start new conversation**
3. **Ask Claude:**
   ```
   Can you list all tables in my Supabase database?
   ```
4. **Expected:** Claude should show your database tables

If it works, you can ask Claude to:
- Query your database
- Create tables
- Run migrations
- Check RLS policies
- And more!

## Alternative: Give Me Database Access Directly

If MCP setup is too complex, you can share credentials with me via secure method:

**Option 1: Share via .env**
```bash
# In your .env file (already has database URL)
SUPABASE_URL=https://haruewffnubdgyofftut.supabase.co
SUPABASE_SERVICE_KEY=<your-service-role-key>
```

**Option 2: I can guide you through SQL queries**
- You run queries in Supabase Dashboard
- I provide the SQL
- You paste and execute

## What MCP Gives You

Once configured, you can ask Claude Desktop to:

✅ "Show me all analytics tables"
✅ "Check if RLS is enabled on analytics_gold_orders"
✅ "List all RLS policies on analytics tables"
✅ "Insert test data into analytics_gold_orders"
✅ "Query the analytics_gold_orders table"

All without leaving Claude Desktop!

## Current Status

- ✅ SQL script fixed (handles both views and tables)
- ⏳ MCP setup (optional, use Option A above)
- ✅ Analytics API connected to Supabase
- ✅ CORS working
- ⏳ Need to run updated SQL migration

## Next Step

**Run the updated SQL script:**
1. Copy `COPY_PASTE_TO_SUPABASE.sql` (it's been fixed)
2. Paste in Supabase Dashboard → SQL Editor
3. Run
4. Verify tables created with: `SELECT * FROM pg_tables WHERE tablename LIKE 'analytics_%';`
