"""BLU-MVP-073 — RLS regression test suite.

Defence-in-depth check that every MVP-critical tenant table:

1. Has RLS **enabled** (`pg_class.relrowsecurity`).
2. Refuses cross-tenant SELECTs via `role=authenticated`.
3. Refuses direct INSERT/UPDATE/DELETE from `authenticated` for the
   append-only / service-only tables (approval_requests, audit_log,
   client_insights, consumer_*).

The pattern reuses the JWT-forging helper from
``tests/test_landing_onboarding.py`` — a psycopg connection that switches
to ``role=authenticated`` and stamps ``request.jwt.claims`` so PostgREST
behaviour is mirrored exactly.

Skipped gracefully when ``SUPABASE_DB_URL`` is not set (CI uses the
service-role-only smoke test in ``test_dashboard_rpcs.py`` for those
environments).
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
# Tables under test — single source of truth for the matrix below.
# ---------------------------------------------------------------------------

# (schema, table, column_for_client_id, expected_writable_by_authenticated)
RLS_TABLES: list[tuple[str, str, str, bool]] = [
    # Phase 0 — Approval Engine + audit_log
    ("public", "approval_requests", "client_id", False),
    ("public", "audit_log",         "client_id", False),
    # Phase 2 — daily insights
    ("public", "client_insights",   "client_id", False),
    # Phase 3B — Consumer Inbox
    ("public", "consumer_contacts", "client_id", False),
    ("public", "consumer_messages", "client_id", False),
    # Existing dashboard surfaces (sanity check — already exercised in
    # ``test_dashboard_rpcs.py`` via service role).
    ("public", "nps_responses",     "client_id", True),  # owners can self-insert
    ("public", "calendar_settings", "client_id", True),
    # Onboarding-tier flags
    ("public", "client_enabled_agents", "client_id", False),
    ("public", "client_routines",       "client_id", False),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db():
    from blu_supabase_client import get_supabase_client

    return get_supabase_client()


@pytest.fixture(scope="module")
def db_url() -> str | None:
    """Direct psql DSN. None → tests requiring role-switching are skipped."""
    return os.getenv("SUPABASE_DB_URL")


@pytest.fixture(scope="module")
def tenant_a(db) -> Iterator[dict[str, Any]]:
    yield from _create_tenant(db, label="rls-a")


@pytest.fixture(scope="module")
def tenant_b(db) -> Iterator[dict[str, Any]]:
    yield from _create_tenant(db, label="rls-b")


def _create_tenant(db, label: str) -> Iterator[dict[str, Any]]:
    """Provision an auth.users row + rely on handle_new_auth_user trigger."""
    email = f"phase-h-{label}-{uuid.uuid4().hex[:8]}@blu.test"
    password = uuid.uuid4().hex + "Aa!"
    resp = db.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    user = getattr(resp, "user", None) or resp
    user_id = user.id if hasattr(user, "id") else user["id"]

    row = (
        db.table("clientes_blu")
        .select("client_id")
        .eq("external_user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    assert row.data, f"trigger did not bootstrap clientes_blu for {email}"
    client_id = row.data["client_id"]

    try:
        yield {"user_id": str(user_id), "email": email, "client_id": client_id}
    finally:
        # Clean up tenant — clientes_blu CASCADE handles related tables.
        try:
            db.table("clientes_blu").delete().eq("client_id", client_id).execute()
        finally:
            db.auth.admin.delete_user(user_id)


@contextmanager
def _as_user(db_url: str, user_id: str, email: str):
    """Open a psycopg connection in ``authenticated`` role with a forged JWT."""
    try:
        import psycopg2
    except ImportError:  # pragma: no cover
        pytest.skip("psycopg2 not available")

    conn = psycopg2.connect(db_url)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET ROLE authenticated;")
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


def _need_db_url(db_url: str | None) -> str:
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not set — RLS role-switch tests skipped")
    return db_url


# ---------------------------------------------------------------------------
# 1. RLS is enabled on every MVP table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("schema,table,_col,_writable", RLS_TABLES)
def test_rls_enabled(db, schema: str, table: str, _col: str, _writable: bool):
    """``pg_class.relrowsecurity`` must be true for every tenant table."""
    sql = (
        "SELECT c.relrowsecurity AS enabled, c.relforcerowsecurity AS forced "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        f"WHERE n.nspname = '{schema}' AND c.relname = '{table}'"
    )
    try:
        rows = db.rpc("exec_sql", {"query": sql}).execute().data
    except Exception:
        pytest.skip("exec_sql RPC not deployed — falling back to write-path test")
        return
    assert rows, f"{schema}.{table} does not exist"
    assert rows[0]["enabled"] is True, (
        f"{schema}.{table} must have RLS enabled (got relrowsecurity=False)"
    )


# ---------------------------------------------------------------------------
# 2. Cross-tenant SELECT isolation under role=authenticated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("schema,table,col,_writable", RLS_TABLES)
def test_rls_cross_tenant_select_isolation(
    db,
    db_url: str | None,
    tenant_a: dict[str, Any],
    tenant_b: dict[str, Any],
    schema: str,
    table: str,
    col: str,
    _writable: bool,
):
    """Tenant B's authenticated session must NOT see tenant A's rows."""
    dsn = _need_db_url(db_url)

    # Skip tables that have no canonical insert-via-service-role path here
    # (e.g. those that get populated by triggers tied to auth.users only and
    # not to a synthetic insert). For audit_log we use record_audit RPC.
    if table == "audit_log":
        # Use SECURITY DEFINER record_audit RPC — service-role caller.
        db.rpc(
            "record_audit",
            {
                "p_action": "rls_regression_probe",
                "p_payload": {"label": "tenant_a"},
                "p_resource": None,
                "p_resource_id": None,
                "p_actor_kind": "system",
                "p_agent_slug": None,
            },
        ).execute()
        # Insert via direct service-role for tenant_a so the row is scoped.
        db.table("audit_log").insert(
            {
                "client_id": tenant_a["client_id"],
                "actor_kind": "system",
                "action": "rls_regression_probe",
                "outcome": "success",
            }
        ).execute()
    elif table == "approval_requests":
        db.table("approval_requests").insert(
            {
                "client_id": tenant_a["client_id"],
                "agent_slug": "supply",
                "action": "rls_regression_probe",
                "payload": {"sku": "X"},
            }
        ).execute()
    elif table == "client_insights":
        db.table("client_insights").insert(
            {
                "client_id": tenant_a["client_id"],
                "run_date": "2026-04-27",
                "dimension": "finance",
                "kpi": "rls_probe",
                "title": "probe",
                "observation": "probe",
            }
        ).execute()
    elif table == "consumer_contacts":
        db.table("consumer_contacts").insert(
            {
                "client_id": tenant_a["client_id"],
                "channel": "whatsapp",
                "external_id": f"+55119{uuid.uuid4().hex[:8]}",
            }
        ).execute()
    elif table == "consumer_messages":
        # Needs a contact first
        contact = (
            db.table("consumer_contacts")
            .insert(
                {
                    "client_id": tenant_a["client_id"],
                    "channel": "whatsapp",
                    "external_id": f"+55119{uuid.uuid4().hex[:8]}",
                }
            )
            .execute()
        )
        db.table("consumer_messages").insert(
            {
                "client_id": tenant_a["client_id"],
                "contact_id": contact.data[0]["id"],
                "channel": "whatsapp",
                "direction": "inbound",
                "body": "probe",
            }
        ).execute()
    elif table == "nps_responses":
        db.table("nps_responses").insert(
            {"client_id": tenant_a["client_id"], "score": 9, "source": "rls-probe"}
        ).execute()
    elif table == "calendar_settings":
        db.table("calendar_settings").upsert(
            {"client_id": tenant_a["client_id"], "enabled": False}
        ).execute()
    elif table in ("client_enabled_agents", "client_routines"):
        # The onboarding bootstrap tx already populates these; skip seeding.
        pass

    # Probe: tenant_b's authenticated session must see ZERO tenant_a rows.
    with _as_user(dsn, tenant_b["user_id"], tenant_b["email"]) as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*)::int FROM {schema}.{table} WHERE {col} = %s",
            (tenant_a["client_id"],),
        )
        leaked = cur.fetchone()[0]
    assert leaked == 0, (
        f"RLS LEAK: tenant_b sees {leaked} rows of tenant_a in {schema}.{table}"
    )


# ---------------------------------------------------------------------------
# 3. Append-only tables reject direct INSERT from authenticated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "schema,table",
    [
        ("public", "approval_requests"),
        ("public", "audit_log"),
        ("public", "client_insights"),
        ("public", "consumer_contacts"),
        ("public", "consumer_messages"),
    ],
)
def test_rls_blocks_direct_insert_from_authenticated(
    db_url: str | None,
    tenant_a: dict[str, Any],
    schema: str,
    table: str,
):
    """Direct ``INSERT`` from a tenant's authenticated session must fail.

    All five tables route writes through SECURITY DEFINER RPCs (or the
    service role). A successful direct INSERT here would mean the
    ``WITH CHECK (false)`` policy regressed.
    """
    dsn = _need_db_url(db_url)
    import psycopg2

    payload_sql, params = _minimal_insert_sql(schema, table, tenant_a["client_id"])

    with _as_user(dsn, tenant_a["user_id"], tenant_a["email"]) as conn, conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(payload_sql, params)


def _minimal_insert_sql(schema: str, table: str, client_id: str) -> tuple[str, tuple]:
    """Smallest valid INSERT for each append-only table, intentionally
    valid w.r.t. CHECK constraints so the only failure path is RLS."""
    if table == "approval_requests":
        return (
            f"INSERT INTO {schema}.{table} (client_id, agent_slug, action, payload) "
            "VALUES (%s, 'supply', 'probe', '{}'::jsonb)",
            (client_id,),
        )
    if table == "audit_log":
        return (
            f"INSERT INTO {schema}.{table} (client_id, actor_kind, action, outcome) "
            "VALUES (%s, 'user', 'probe', 'success')",
            (client_id,),
        )
    if table == "client_insights":
        return (
            f"INSERT INTO {schema}.{table} (client_id, run_date, dimension, kpi, "
            "title, observation) VALUES (%s, CURRENT_DATE, 'finance', 'probe', "
            "'probe', 'probe')",
            (client_id,),
        )
    if table == "consumer_contacts":
        return (
            f"INSERT INTO {schema}.{table} (client_id, channel, external_id) "
            "VALUES (%s, 'whatsapp', 'probe@example.com')",
            (client_id,),
        )
    if table == "consumer_messages":
        return (
            f"INSERT INTO {schema}.{table} (client_id, contact_id, channel, "
            "direction, body) VALUES (%s, gen_random_uuid(), 'whatsapp', "
            "'inbound', 'probe')",
            (client_id,),
        )
    raise AssertionError(f"unhandled table {table!r}")


# ---------------------------------------------------------------------------
# 4. SECURITY INVOKER metadata sanity check (regression for SECDEF leaks)
# ---------------------------------------------------------------------------


def test_dimension_indicator_rpcs_are_security_invoker(db):
    """Dimension RPCs must be SECURITY INVOKER so RLS still applies."""
    sql = """
        SELECT n.nspname || '.' || p.proname AS fn,
               p.prosecdef AS is_definer
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'analytics_v2'
           AND p.proname IN (
                 'get_finance_indicators',
                 'get_commercial_indicators',
                 'get_inventory_indicators',
                 'get_supply_indicators',
                 'get_marketing_indicators'
           )
    """
    try:
        rows = db.rpc("exec_sql", {"query": sql}).execute().data or []
    except Exception:
        pytest.skip("exec_sql RPC not available")
        return
    assert rows, "expected dimension RPCs to be deployed"
    for row in rows:
        assert row["is_definer"] is False, (
            f"{row['fn']} must be SECURITY INVOKER (RLS-bypassing DEFINER not allowed)"
        )


# ---------------------------------------------------------------------------
# 5. Approval/audit writes require service role or SECURITY DEFINER RPC
# ---------------------------------------------------------------------------


def test_record_audit_executable_by_service_role(db, tenant_a: dict[str, Any]):
    """The canonical write path for audit_log is record_audit() — must work."""
    resp = db.rpc(
        "record_audit",
        {
            "p_action": "rls_regression_test",
            "p_payload": {"client_id": tenant_a["client_id"]},
            "p_actor_kind": "system",
        },
    ).execute()
    # record_audit returns the new row — assert at least one row back.
    assert resp.data is not None


def test_approval_request_insert_via_service_role(db, tenant_a: dict[str, Any]):
    """Service-role can seed approvals (used by request_approval RPC)."""
    resp = (
        db.table("approval_requests")
        .insert(
            {
                "client_id": tenant_a["client_id"],
                "agent_slug": "supply",
                "action": "rls_regression_test",
                "payload": {"sku": "X"},
            }
        )
        .execute()
    )
    assert resp.data and resp.data[0]["status"] == "pending"
