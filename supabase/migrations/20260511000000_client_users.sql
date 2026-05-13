-- Migration: client_users
-- Creates a multi-user table scoped to each client (workspace).
-- One workspace (client_id) can have many users, each with a role.

-- ── Table ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "public"."client_users" (
    "id"                   uuid         DEFAULT gen_random_uuid() NOT NULL,
    "client_id"            uuid         NOT NULL,
    "auth_user_id"         uuid,                              -- links to auth.users; null until invite accepted
    "email"                text         NOT NULL,
    "name"                 text,
    "role"                 text         NOT NULL DEFAULT 'member',  -- 'owner' | 'admin' | 'manager' | 'member'
    "agent_permissions"    jsonb        NOT NULL DEFAULT '{}',      -- { [agent_slug]: boolean }
    "action_permissions"   jsonb        NOT NULL DEFAULT '{}',      -- { [action_key]: boolean }
    "invited_at"           timestamptz  DEFAULT now(),
    "accepted_at"          timestamptz,                       -- null = invite pending
    "created_at"           timestamptz  DEFAULT now() NOT NULL,
    "updated_at"           timestamptz  DEFAULT now() NOT NULL,
    CONSTRAINT "client_users_pkey"           PRIMARY KEY ("id"),
    CONSTRAINT "client_users_client_id_fkey" FOREIGN KEY ("client_id")
        REFERENCES "public"."clientes_blu" ("client_id") ON DELETE CASCADE,
    CONSTRAINT "client_users_auth_user_fkey" FOREIGN KEY ("auth_user_id")
        REFERENCES "auth"."users" ("id") ON DELETE SET NULL,
    CONSTRAINT "client_users_unique_email"   UNIQUE ("client_id", "email"),
    CONSTRAINT "client_users_role_check"     CHECK (role IN ('owner', 'admin', 'manager', 'member'))
);

ALTER TABLE "public"."client_users" OWNER TO "postgres";

-- ── Indexes ────────────────────────────────────────────────────────────────

CREATE INDEX "idx_client_users_client_id"    ON "public"."client_users" USING btree ("client_id");
CREATE INDEX "idx_client_users_auth_user_id" ON "public"."client_users" USING btree ("auth_user_id") WHERE "auth_user_id" IS NOT NULL;
CREATE INDEX "idx_client_users_email"        ON "public"."client_users" USING btree ("email");

-- ── updated_at trigger ─────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION "public"."set_client_users_updated_at"()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

ALTER FUNCTION "public"."set_client_users_updated_at"() OWNER TO "postgres";

CREATE TRIGGER "trg_client_users_updated_at"
  BEFORE UPDATE ON "public"."client_users"
  FOR EACH ROW EXECUTE FUNCTION "public"."set_client_users_updated_at"();

-- ── RLS ────────────────────────────────────────────────────────────────────

ALTER TABLE "public"."client_users" ENABLE ROW LEVEL SECURITY;

-- Members of a workspace can read all users in that workspace
CREATE POLICY "client_users_select"
  ON "public"."client_users"
  FOR SELECT
  USING (client_id = public.get_my_client_id());

-- Owners and admins can invite / create new users in their workspace
-- Bootstrap exception: allow if no rows exist yet (existing clients before this migration)
CREATE POLICY "client_users_insert"
  ON "public"."client_users"
  FOR INSERT
  WITH CHECK (
    client_id = public.get_my_client_id()
    AND (
      NOT EXISTS (
        SELECT 1 FROM public.client_users WHERE client_id = public.get_my_client_id()
      )
      OR EXISTS (
        SELECT 1 FROM public.client_users cu
        WHERE cu.client_id = public.get_my_client_id()
          AND cu.auth_user_id = auth.uid()
          AND cu.role IN ('owner', 'admin')
      )
    )
  );

-- Owners and admins can update any user in their workspace;
-- regular users can update their own row (e.g. accept invite, change name)
CREATE POLICY "client_users_update"
  ON "public"."client_users"
  FOR UPDATE
  USING (
    client_id = public.get_my_client_id()
    AND (
      auth_user_id = auth.uid()
      OR EXISTS (
        SELECT 1 FROM public.client_users cu
        WHERE cu.client_id = public.get_my_client_id()
          AND cu.auth_user_id = auth.uid()
          AND cu.role IN ('owner', 'admin')
      )
    )
  )
  WITH CHECK (client_id = public.get_my_client_id());

-- Only owners and admins can delete users (not self-delete of owner)
CREATE POLICY "client_users_delete"
  ON "public"."client_users"
  FOR DELETE
  USING (
    client_id = public.get_my_client_id()
    AND EXISTS (
      SELECT 1 FROM public.client_users cu
      WHERE cu.client_id = public.get_my_client_id()
        AND cu.auth_user_id = auth.uid()
        AND cu.role IN ('owner', 'admin')
    )
  );

-- Service role bypasses RLS for backend operations
CREATE POLICY "client_users_service_role"
  ON "public"."client_users"
  USING ((auth.jwt() ->> 'role') = 'service_role')
  WITH CHECK ((auth.jwt() ->> 'role') = 'service_role');

-- ── Seed owner row on new client creation ─────────────────────────────────
-- Automatically inserts an 'owner' row when a new clientes_blu is created,
-- if the creating user has an email in auth.users.

CREATE OR REPLACE FUNCTION "public"."seed_client_owner"()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  v_email text;
  v_name  text;
BEGIN
  -- Resolve email/name from auth.users if this was created via JWT
  SELECT au.email, au.raw_user_meta_data ->> 'full_name'
    INTO v_email, v_name
    FROM auth.users au
   WHERE au.id::text = NEW.external_user_id
   LIMIT 1;

  IF v_email IS NOT NULL THEN
    INSERT INTO public.client_users (client_id, auth_user_id, email, name, role, accepted_at)
    VALUES (
      NEW.client_id,
      (SELECT id FROM auth.users WHERE id::text = NEW.external_user_id LIMIT 1),
      v_email,
      v_name,
      'owner',
      now()
    )
    ON CONFLICT (client_id, email) DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$;

ALTER FUNCTION "public"."seed_client_owner"() OWNER TO "postgres";

CREATE TRIGGER "trg_seed_client_owner"
  AFTER INSERT ON "public"."clientes_blu"
  FOR EACH ROW EXECUTE FUNCTION "public"."seed_client_owner"();
