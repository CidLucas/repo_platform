-- ============================================================
-- Disable Supabase built-in email provider via auth hook
-- Date: 2026-06-27
--
-- Why: the Supabase built-in email provider rate-limits
-- /auth/v1/signup to 2 emails/hour. This blocks onboarding
-- after a couple of test signups. By installing a no-op
-- `send_email` hook we tell Supabase to skip the built-in
-- provider — the 2/h cap no longer applies, and the
-- 30/h-by-IP limit takes over (plenty for dev/test).
--
-- Combined with the auto-confirm trigger below, signups
-- become fully silent: no confirmation email, no rate
-- limit, user is created and immediately loginable.
--
-- To enable the hook in the remote project, either:
--   1. supabase config push  (if CLI is linked to the project)
--   2. Dashboard → Authentication → Hooks → Send Email →
--      Enable, uri = pg-functions://postgres/public/send_email_hook
-- ============================================================

-- ── 1. send_email hook: no-op (Supabase uses this instead of
--      the built-in provider, which is what unlocks the rate
--      limit. Returning '{}' is a no-op; we deliberately do
--      NOT call any email provider.) ──────────────────────
create or replace function public.send_email_hook(event jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
begin
  -- No-op: we don't want to send emails in dev.
  -- The Supabase built-in provider is bypassed because this
  -- hook is enabled, which removes the 2/h email rate limit.
  return '{}'::jsonb;
end;
$$;

-- supabase_auth_admin runs hooks; revoke from public to lock down.
grant execute on function public.send_email_hook(jsonb) to supabase_auth_admin;
revoke execute on function public.send_email_hook(jsonb) from authenticated, anon, public;

-- ── 2. Auto-confirm new email signups. Because the send_email
--      hook above is a no-op, users never receive a confirmation
--      email. Without this trigger, signups would create the
--      user but leave email_confirmed_at = NULL — login via
--      password would fail with "Email not confirmed". ─────
create or replace function public.handle_new_auth_user_auto_confirm()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.email_confirmed_at is null then
    new.email_confirmed_at := now();
  end if;
  return new;
end;
$$;

drop trigger if exists trg_auto_confirm_email on auth.users;
create trigger trg_auto_confirm_email
  before insert on auth.users
  for each row execute function public.handle_new_auth_user_auto_confirm();
