#!/usr/bin/env python3
"""Apply RLS policies to clientes_vizu table"""
import psycopg2
import os
import sys

db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg2://", "postgresql://")

if not db_url:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

print(f"Connecting to database...")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cursor = conn.cursor()
print("✅ Connected")

try:
    # Enable RLS
    print("\nEnabling RLS...")
    cursor.execute("ALTER TABLE public.clientes_vizu ENABLE ROW LEVEL SECURITY;")
    print("✅ RLS enabled")

    # Drop existing policies
    print("\nDropping old policies if they exist...")
    policies = [
        "Users can read own cliente record",
        "Service role has full access to clientes_vizu",
        "Authenticated users can insert own cliente record",
        "Users can update own cliente record"
    ]

    for policy_name in policies:
        try:
            cursor.execute(f"DROP POLICY IF EXISTS \"{policy_name}\" ON public.clientes_vizu;")
            print(f"  - Dropped: {policy_name}")
        except Exception as e:
            print(f"  - Skip: {policy_name} ({e})")

    # Create policies
    print("\nCreating RLS policies...")

    # Policy 1: Users can read their own record
    cursor.execute("""
        CREATE POLICY "Users can read own cliente record"
        ON public.clientes_vizu
        FOR SELECT
        USING (
            external_user_id = auth.jwt() ->> 'sub'
            OR api_key IS NOT NULL
        );
    """)
    print("✅ Created SELECT policy")

    # Policy 2: Service role full access
    cursor.execute("""
        CREATE POLICY "Service role has full access to clientes_vizu"
        ON public.clientes_vizu
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
    """)
    print("✅ Created service_role policy")

    # Policy 3: Authenticated users can insert
    cursor.execute("""
        CREATE POLICY "Authenticated users can insert own cliente record"
        ON public.clientes_vizu
        FOR INSERT
        TO authenticated
        WITH CHECK (
            external_user_id = auth.jwt() ->> 'sub'
        );
    """)
    print("✅ Created INSERT policy")

    # Policy 4: Users can update their own record
    cursor.execute("""
        CREATE POLICY "Users can update own cliente record"
        ON public.clientes_vizu
        FOR UPDATE
        TO authenticated
        USING (external_user_id = auth.jwt() ->> 'sub')
        WITH CHECK (external_user_id = auth.jwt() ->> 'sub');
    """)
    print("✅ Created UPDATE policy")

    # Verify
    cursor.execute("SELECT COUNT(*) FROM pg_policies WHERE tablename = 'clientes_vizu'")
    count = cursor.fetchone()[0]
    print(f"\n✅ Total RLS policies created: {count}")

    print("\n✅ All RLS policies applied successfully!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    cursor.close()
    conn.close()
