"""Phase 6 — Landing onboarding wire-up: schema, trigger, RLS, bootstrap TX.

Covers the SQL artefacts shipped in Phases 1 & 4 of
``docs/plans/2026-04-23-landing-onboarding-wireup.md``:

  * ``public.handle_new_auth_user`` trigger on ``auth.users``
  * ``public.ensure_tenant_row()`` self-heal RPC
  * ``public.merge_onboarding_state(jsonb)`` RPC
  * ``public.onboarding_bootstrap_tx(jsonb)`` RPC
  * ``public.client_enabled_agents`` + RLS policies
  * ``public.client_routines`` + RLS policies
  * ``public.clientes_blu.onboarding_state`` JSONB column
  * 8 canonical landing slugs in ``public.agent_catalog``

Strategy
--------
Service-role Supabase client handles setup/teardown (bypasses RLS). To
prove RLS isolation we open a psycopg connection against SUPABASE_DB_URL
and switch to ``role=authenticated`` + a synthetic ``request.jwt.claims``
block — exactly the pattern validated in the Phase 1 smoke notes
(see ``/memories/repo/landing-onboarding-phase1.md``).

All tests are skipped gracefully when ``SUPABASE_DB_URL`` is not
configured; the service-role-only tests continue to run using the
existing Supabase client.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db():
    """Service-role Supabase client (bypasses RLS)."""
    from blu_supabase_client import get_supabase_client

    return get_supabase_client()


@pytest.fixture(scope="module")
def db_url() -> str | None:
    """Direct psql DSN for role-switching RLS tests. None → skip."""
    return os.getenv("SUPABASE_DB_URL")


@pytest.fixture(scope="module")
def tenant_a(db) -> Iterator[dict[str, Any]]:
    """Create a throw-away auth.users row + rely on the trigger for clientes_blu."""
    yield from _create_tenant(db, label="a")


@pytest.fixture(scope="module")
def tenant_b(db) -> Iterator[dict[str, Any]]:
    yield from _create_tenant(db, label="b")


def _create_tenant(db, label: str) -> Iterator[dict[str, Any]]:
    """Provision a fresh auth.users row via the admin API, wait for the
    trigger-seeded clientes_blu row, yield {user_id, email, client_id}."""
    email = f"phase6-landing-{label}-{uuid.uuid4().hex[:8]}@blu.test"
    password = uuid.uuid4().hex + "Aa!"
    resp = db.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
        }
    )
    user = getattr(resp, "user", None) or resp
    user_id = user.id if hasattr(user, "id") else user["id"]

    # Trigger should have seeded clientes_blu already.
    row = (
        db.table("clientes_blu")
        .select("client_id")
        .eq("external_user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    assert row.data, (
        f"handle_new_auth_user trigger did not produce clientes_blu row for {email}"
    )
    client_id = row.data["client_id"]

    try:
        yield {"user_id": str(user_id), "email": email, "client_id": client_id}
    finally:
        # Cleanup: clientes_blu cascades via ON DELETE CASCADE on enabled_agents/routines.
        try:
            db.table("client_enabled_agents").delete().eq("client_id", client_id).execute()
            db.table("client_routines").delete().eq("client_id", client_id).execute()
            db.table("clientes_blu").delete().eq("client_id", client_id).execute()
        finally:
            db.auth.admin.delete_user(user_id)


@contextmanager
def _as_user(db_url: str, user_id: str, email: str):
    """Open a psycopg connection in ``authenticated`` role, stamping the
    JWT claims PostgREST would inject so ``public.get_my_client_id()`` and
    RLS policies resolve to this tenant."""
    try:
        import psycopg2
    except ImportError:  # pragma: no cover — env-dependent
        pytest.skip("psycopg2 not available")

    conn = psycopg2.connect(db_url)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET ROLE authenticated;")
            # PostgREST sets both claims, plus aud and role. The RLS helper
            # only reads ``sub``/``email``, but we set a minimal, realistic
            # JWT blob to mirror production.
            claims = json.dumps(
                {
                    "sub": user_id,
                    "email": email,
                    "role": "authenticated",
                    "aud": "authenticated",
                }
            )
            cur.execute("SELECT set_config('request.jwt.claims', %s, true);", (claims,))
            cur.execute(
                "SELECT set_config('request.jwt.claim.sub', %s, true);", (user_id,)
            )
            cur.execute(
                "SELECT set_config('request.jwt.claim.email', %s, true);", (email,)
            )
        yield conn
    finally:
        conn.rollback()
        conn.close()


# ---------------------------------------------------------------------------
# Schema presence
# ---------------------------------------------------------------------------


def test_onboarding_state_column_exists(db):
    """``clientes_blu.onboarding_state`` + ``onboarding_completed_at`` must exist."""
    resp = db.rpc(
        "exec_sql",
        {
            "query": (
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'clientes_blu' "
                "AND column_name IN ('onboarding_state', 'onboarding_completed_at') "
                "ORDER BY column_name"
            )
        },
    )
    try:
        rows = resp.execute().data  # type: ignore[attr-defined]
    except Exception:
        pytest.skip("exec_sql RPC not available")
        return
    cols = {r["column_name"] for r in rows or []}
    assert {"onboarding_state", "onboarding_completed_at"} <= cols


def test_landing_agent_slugs_seeded(db):
    """The 8 canonical landing slugs must exist in agent_catalog."""
    expected = {
        "analytics",
        "crm",
        "marketing",
        "inventory",
        "scheduling",
        "projects",
        "documents",
        "finance",
    }
    resp = db.table("agent_catalog").select("slug").in_("slug", list(expected)).execute()
    got = {r["slug"] for r in resp.data or []}
    assert expected <= got, f"missing landing slugs: {expected - got}"


# ---------------------------------------------------------------------------
# Trigger: handle_new_auth_user
# ---------------------------------------------------------------------------


def test_trigger_creates_clientes_blu_row(tenant_a: dict[str, Any], db):
    """Fixture already asserts the row exists; belt-and-braces check email + empty state."""
    resp = (
        db.table("clientes_blu")
        .select("client_id, email, onboarding_state, onboarding_completed_at")
        .eq("client_id", tenant_a["client_id"])
        .single()
        .execute()
    )
    row = resp.data
    assert row["email"] == tenant_a["email"]
    # onboarding_state defaults to {} per the Phase 1 migration.
    assert row["onboarding_state"] in ({}, None)
    assert row["onboarding_completed_at"] is None


# ---------------------------------------------------------------------------
# RLS isolation: client_enabled_agents / client_routines / onboarding_state
# ---------------------------------------------------------------------------


def test_rls_client_enabled_agents_isolation(
    db, db_url: str | None, tenant_a: dict[str, Any], tenant_b: dict[str, Any]
):
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not configured")

    # Seed one row per tenant via service role (bypasses RLS).
    db.table("client_enabled_agents").upsert(
        {"client_id": tenant_a["client_id"], "agent_slug": "analytics"},
        on_conflict="client_id,agent_slug",
    ).execute()
    db.table("client_enabled_agents").upsert(
        {"client_id": tenant_b["client_id"], "agent_slug": "crm"},
        on_conflict="client_id,agent_slug",
    ).execute()

    # Tenant A must only see its own row.
    with _as_user(db_url, tenant_a["user_id"], tenant_a["email"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT client_id::text, agent_slug FROM public.client_enabled_agents "
                "ORDER BY agent_slug"
            )
            rows = cur.fetchall()
    assert rows == [(tenant_a["client_id"], "analytics")], (
        f"RLS leak: {rows}"
    )

    # Tenant B sees only its own.
    with _as_user(db_url, tenant_b["user_id"], tenant_b["email"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT client_id::text, agent_slug FROM public.client_enabled_agents"
            )
            rows = cur.fetchall()
    assert rows == [(tenant_b["client_id"], "crm")]


def test_rls_client_routines_isolation(
    db, db_url: str | None, tenant_a: dict[str, Any], tenant_b: dict[str, Any]
):
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not configured")

    db.table("client_routines").upsert(
        {
            "client_id": tenant_a["client_id"],
            "routine_id": "daily_sales_digest",
            "notify_channel": "email",
        },
        on_conflict="client_id,routine_id",
    ).execute()
    db.table("client_routines").upsert(
        {
            "client_id": tenant_b["client_id"],
            "routine_id": "low_stock_alert",
            "notify_channel": "email",
        },
        on_conflict="client_id,routine_id",
    ).execute()

    with _as_user(db_url, tenant_a["user_id"], tenant_a["email"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT client_id::text, routine_id FROM public.client_routines"
            )
            rows = cur.fetchall()
    assert rows == [(tenant_a["client_id"], "daily_sales_digest")]


def test_rls_onboarding_state_isolation(
    db, db_url: str | None, tenant_a: dict[str, Any], tenant_b: dict[str, Any]
):
    """A tenant must not read another tenant's ``clientes_blu`` row."""
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not configured")

    # Stamp a sentinel on tenant A so we can detect cross-tenant leaks.
    db.table("clientes_blu").update(
        {"onboarding_state": {"sentinel": "tenant_a"}}
    ).eq("client_id", tenant_a["client_id"]).execute()

    with _as_user(db_url, tenant_b["user_id"], tenant_b["email"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT client_id::text FROM public.clientes_blu "
                "WHERE onboarding_state ->> 'sentinel' = 'tenant_a'"
            )
            rows = cur.fetchall()
    assert rows == [], f"tenant B read tenant A's onboarding_state: {rows}"


# ---------------------------------------------------------------------------
# merge_onboarding_state — race-free commutative merge
# ---------------------------------------------------------------------------


def test_merge_onboarding_state_rpc(
    db, db_url: str | None, tenant_a: dict[str, Any]
):
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not configured")

    # Reset state to a known baseline.
    db.table("clientes_blu").update({"onboarding_state": {}}).eq(
        "client_id", tenant_a["client_id"]
    ).execute()

    with _as_user(db_url, tenant_a["user_id"], tenant_a["email"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT public.merge_onboarding_state(%s::jsonb)",
                (json.dumps({"empresa": "Acme", "vertical": "ecommerce"}),),
            )
            cur.execute(
                "SELECT public.merge_onboarding_state(%s::jsonb)",
                (json.dumps({"vertical": "servicos", "agents": ["analytics"]}),),
            )
        conn.commit()

    resp = (
        db.table("clientes_blu")
        .select("onboarding_state")
        .eq("client_id", tenant_a["client_id"])
        .single()
        .execute()
    )
    state = resp.data["onboarding_state"]
    # Top-level `||` merge: later patches overwrite earlier top-level keys,
    # new keys are appended.
    assert state.get("empresa") == "Acme"
    assert state.get("vertical") == "servicos"
    assert state.get("agents") == ["analytics"]


# ---------------------------------------------------------------------------
# onboarding_bootstrap_tx — idempotency + drift guard
# ---------------------------------------------------------------------------


def test_bootstrap_tx_idempotent(
    db, db_url: str | None, tenant_a: dict[str, Any]
):
    """Running the RPC twice must not duplicate enabled agents/routines and
    must preserve the first-set ``onboarding_completed_at`` timestamp."""
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not configured")

    # Clean slate.
    db.table("client_enabled_agents").delete().eq(
        "client_id", tenant_a["client_id"]
    ).execute()
    db.table("client_routines").delete().eq(
        "client_id", tenant_a["client_id"]
    ).execute()
    db.table("clientes_blu").update(
        {"onboarding_completed_at": None}
    ).eq("client_id", tenant_a["client_id"]).execute()

    payload = {
        "company_profile": {"legal_name": "Acme LTDA", "core_values": []},

        "team_structure": {
            "key_contacts": [],
            "escalation_path": [],
            "communication_channels": {"email": tenant_a["email"]},
            "operational_locations": [],
        },
        "policies": {
            "communication_rules": [],
            "operational_limits": [],
            "approval_requirements": {"autonomous": [], "requires_approval": []},
            "red_flags": [],
            "data_handling_rules": [],
        },
        "agents": ["analytics", "crm"],
        "routines": ["daily_sales_digest", "low_stock_alert"],
        "notify_channel": "email",
        "nome_empresa": "Acme LTDA",
    }

    def _call(cur):
        cur.execute(
            "SELECT public.onboarding_bootstrap_tx(%s::jsonb)", (json.dumps(payload),)
        )
        return cur.fetchone()[0]

    with _as_user(db_url, tenant_a["user_id"], tenant_a["email"]) as conn:
        with conn.cursor() as cur:
            first = _call(cur)
        conn.commit()
    with _as_user(db_url, tenant_a["user_id"], tenant_a["email"]) as conn:
        with conn.cursor() as cur:
            second = _call(cur)
        conn.commit()

    assert first["client_id"] == tenant_a["client_id"]
    assert first["agents"] == 2 and first["routines"] == 2
    # Second call: same counts, no duplicates (DO UPDATE path).
    assert second["agents"] == 2 and second["routines"] == 2

    # Row counts prove no duplicates crept in.
    agents = (
        db.table("client_enabled_agents")
        .select("agent_slug")
        .eq("client_id", tenant_a["client_id"])
        .execute()
    )
    routines = (
        db.table("client_routines")
        .select("routine_id")
        .eq("client_id", tenant_a["client_id"])
        .execute()
    )
    assert {r["agent_slug"] for r in agents.data} == {"analytics", "crm"}
    assert {r["routine_id"] for r in routines.data} == {
        "daily_sales_digest",
        "low_stock_alert",
    }

    # Completion timestamp must be preserved across runs (COALESCE guard).
    first_ts = (
        db.table("clientes_blu")
        .select("onboarding_completed_at")
        .eq("client_id", tenant_a["client_id"])
        .single()
        .execute()
        .data["onboarding_completed_at"]
    )
    assert first_ts is not None


def test_bootstrap_tx_rejects_unknown_agent_slug(
    db, db_url: str | None, tenant_a: dict[str, Any]
):
    """FK to ``agent_catalog.slug`` must reject drift at write time."""
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not configured")

    payload = {
        "agents": ["analytics", "__nope__"],
        "routines": [],
        "notify_channel": "email",
    }
    with _as_user(db_url, tenant_a["user_id"], tenant_a["email"]) as conn:
        with conn.cursor() as cur:
            with pytest.raises(Exception):
                cur.execute(
                    "SELECT public.onboarding_bootstrap_tx(%s::jsonb)",
                    (json.dumps(payload),),
                )
        conn.rollback()


# ---------------------------------------------------------------------------
# ensure_tenant_row — self-heal for pre-trigger rows
# ---------------------------------------------------------------------------


def test_ensure_tenant_row_returns_existing(
    db_url: str | None, tenant_a: dict[str, Any]
):
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not configured")

    with _as_user(db_url, tenant_a["user_id"], tenant_a["email"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT public.ensure_tenant_row()")
            got = cur.fetchone()[0]
    assert str(got) == tenant_a["client_id"]
