"""
Approval Engine helper — Phase 0 / F0.3.

Thin Python wrapper around the `request_approval`, `decide_approval`, and
`list_pending_approvals` RPCs (see
``supabase/migrations/20260426230000_approval_engine_v1.sql``).

Design contract:

- The helper does NOT raise an :class:`ElicitationRequired` itself. Callers
  (typically MCP tool modules) decide whether to translate the returned
  :class:`ApprovalRequest` into an elicitation flow, a hard error, or a
  silent queue insert. Keeping the two concerns separate lets the helper
  serve both interactive (LangGraph) and non-interactive (cron / webhook)
  consumers.
- All writes go through the SECURITY DEFINER RPCs so that JWT-scoped
  callers cannot bypass the RLS deny-direct-write policies on
  ``public.approval_requests``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApprovalRequest:
    """In-memory mirror of a ``public.approval_requests`` row."""

    id: str
    client_id: str
    agent_slug: str
    action: str
    payload: dict[str, Any]
    status: str
    requested_by: str | None
    routed_to_role: str | None
    decided_by: str | None
    decision_reason: str | None
    session_id: str | None
    tool_call_id: str | None
    sla_hours: int
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    payload_hash: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_terminal(self) -> bool:
        return self.status in {"approved", "rejected", "expired", "cancelled"}

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ApprovalRequest":
        """Build from a Supabase RPC row (snake_case keys)."""

        def _ts(value: Any) -> datetime | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

        return cls(
            id=str(row["id"]),
            client_id=str(row["client_id"]),
            agent_slug=row["agent_slug"],
            action=row["action"],
            payload=row.get("payload") or {},
            status=row["status"],
            requested_by=row.get("requested_by"),
            routed_to_role=row.get("routed_to_role"),
            decided_by=row.get("decided_by"),
            decision_reason=row.get("decision_reason"),
            session_id=row.get("session_id"),
            tool_call_id=row.get("tool_call_id"),
            sla_hours=int(row.get("sla_hours") or 72),
            expires_at=_ts(row["expires_at"]) or datetime.utcnow(),
            decided_at=_ts(row.get("decided_at")),
            created_at=_ts(row["created_at"]) or datetime.utcnow(),
            updated_at=_ts(row["updated_at"]) or datetime.utcnow(),
            payload_hash=row.get("payload_hash") or "",
            raw=dict(row),
        )


class ApprovalError(RuntimeError):
    """Raised when the Approval Engine RPCs fail."""


class ApprovalEngine:
    """Sync facade over the approval RPCs.

    Pass any object that exposes the supabase-py ``rpc(name, params)`` API
    and an ``.execute()`` chain. In practice this is the singleton from
    :func:`blu_supabase_client.get_supabase_client`.
    """

    def __init__(self, supabase: Any | None = None) -> None:
        self._supabase = supabase

    # -- internals ---------------------------------------------------------

    def _client(self) -> Any:
        if self._supabase is not None:
            return self._supabase
        # Local import — blu_supabase_client is an optional dep at typing time.
        from blu_supabase_client import get_supabase_client

        self._supabase = get_supabase_client()
        return self._supabase

    @staticmethod
    def _unwrap(resp: Any) -> Any:
        data = getattr(resp, "data", None)
        if data is None and isinstance(resp, dict):
            data = resp.get("data")
        return data

    @staticmethod
    def _row(data: Any) -> dict[str, Any]:
        if isinstance(data, list):
            if not data:
                raise ApprovalError("RPC returned empty result set")
            return dict(data[0])
        if isinstance(data, dict):
            return dict(data)
        raise ApprovalError(f"RPC returned unexpected payload: {type(data).__name__}")

    # -- public API --------------------------------------------------------

    def request(
        self,
        *,
        agent_slug: str,
        action: str,
        payload: dict[str, Any],
        session_id: str | None = None,
        tool_call_id: str | None = None,
        routed_to_role: str | None = None,
        sla_hours: int = 72,
    ) -> ApprovalRequest:
        """Enqueue a new approval request and return it."""
        if not action:
            raise ValueError("action is required")
        params = {
            "p_agent_slug": agent_slug,
            "p_action": action,
            "p_payload": payload or {},
            "p_session_id": session_id,
            "p_tool_call_id": tool_call_id,
            "p_routed_to_role": routed_to_role,
            "p_sla_hours": int(sla_hours),
        }
        try:
            resp = self._client().rpc("request_approval", params).execute()
        except Exception as exc:  # pragma: no cover - thin shim
            raise ApprovalError(f"request_approval RPC failed: {exc}") from exc
        return ApprovalRequest.from_row(self._row(self._unwrap(resp)))

    def decide(
        self,
        *,
        request_id: str,
        decision: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Resolve a pending approval request."""
        if decision not in {"approved", "rejected", "cancelled"}:
            raise ValueError("decision must be one of approved|rejected|cancelled")
        params = {
            "p_request_id": request_id,
            "p_decision": decision,
            "p_reason": reason,
        }
        try:
            resp = self._client().rpc("decide_approval", params).execute()
        except Exception as exc:  # pragma: no cover
            raise ApprovalError(f"decide_approval RPC failed: {exc}") from exc
        return ApprovalRequest.from_row(self._row(self._unwrap(resp)))

    def list_pending(
        self,
        *,
        agent_slug: str | None = None,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        """Return up to ``limit`` pending requests for the caller's tenant."""
        params = {"p_agent_slug": agent_slug, "p_limit": int(limit)}
        try:
            resp = self._client().rpc("list_pending_approvals", params).execute()
        except Exception as exc:  # pragma: no cover
            raise ApprovalError(f"list_pending_approvals RPC failed: {exc}") from exc
        data = self._unwrap(resp) or []
        if not isinstance(data, list):
            raise ApprovalError("list_pending_approvals returned non-list payload")
        return [ApprovalRequest.from_row(dict(row)) for row in data]


# ---------------------------------------------------------------------------
# Policy resolution — Phase 3A (P3.1) BLU-MVP-040 / BLU-MVP-041
# ---------------------------------------------------------------------------
#
# The Approval Engine is generic: its `mode/threshold/routed_role/sla_hours`
# fields apply to any mutating MCP tool. The policy bag lives on
# `client_enabled_agents.approval_policy` (jsonb), keyed by action name.
#
# Resolution order (per roadmap §9):
#   action override → role policy → tier default → fallback "Owner-only".
#
# `resolve_policy` returns a :class:`PolicyDecision` describing whether the
# tool should enqueue a separate `approval_requests` row (i.e. surface the
# action in the dashboard Approvals Tray) or whether the in-chat elicitation
# is itself the approval. BASIC tier with no per-action override falls into
# the latter bucket — only one human is involved and the chat UI is enough.


# Tier defaults applied when neither the per-action override nor the role
# policy is set. Keep these conservative — they ship with every tenant.
_TIER_DEFAULTS: dict[str, dict[str, Any]] = {
    # BASIC: elicitation alone is sufficient (single-owner workspaces).
    "BASIC": {"mode": "always", "threshold": None, "routed_role": None, "sla_hours": 72},
    # SME / PRO: route higher-value POs to finance-responsible role.
    "SME": {
        "mode": "threshold", "threshold": 5_000.0,
        "routed_role": "finance-responsible", "sla_hours": 48,
    },
    "PRO": {
        "mode": "threshold", "threshold": 5_000.0,
        "routed_role": "finance-responsible", "sla_hours": 48,
    },
    "PREMIUM": {
        "mode": "threshold", "threshold": 5_000.0,
        "routed_role": "finance-responsible", "sla_hours": 48,
    },
    "ENTERPRISE": {
        "mode": "always", "threshold": None,
        "routed_role": "finance-responsible", "sla_hours": 24,
    },
    "ADMIN": {"mode": "never", "threshold": None, "routed_role": None, "sla_hours": 72},
}

_DEFAULT_FALLBACK = {"mode": "always", "threshold": None, "routed_role": None, "sla_hours": 72}


@dataclass(frozen=True)
class PolicyDecision:
    """Outcome of :func:`resolve_policy`.

    `requires_async_approval` is the single boolean tools should branch on:
    when True they should enqueue an `approval_requests` row and return a
    `pending_approval` status; when False the in-chat elicitation already
    counts as the approval.
    """

    mode: str
    threshold: float | None
    routed_role: str | None
    sla_hours: int
    requires_async_approval: bool
    reason: str
    raw_policy: dict[str, Any] = field(default_factory=dict)


def _lookup_agent_policy(
    supabase: Any,
    *,
    client_id: str,
    agent_slug: str,
) -> dict[str, Any]:
    """Return the `approval_policy` jsonb for a (client, agent) pair, or {}."""
    try:
        resp = (
            supabase.table("client_enabled_agents")
            .select("approval_policy")
            .eq("client_id", client_id)
            .eq("agent_slug", agent_slug)
            .maybe_single()
            .execute()
        )
    except Exception:  # pragma: no cover - thin shim
        logger.warning("resolve_policy: failed to read approval_policy", exc_info=True)
        return {}
    data = getattr(resp, "data", None) or {}
    return dict(data.get("approval_policy") or {})


def _lookup_tenant_tier(supabase: Any, *, client_id: str) -> str:
    """Return the tenant's tier (uppercased), defaulting to BASIC."""
    try:
        resp = (
            supabase.table("clientes_blu")
            .select("tier")
            .eq("client_id", client_id)
            .maybe_single()
            .execute()
        )
    except Exception:  # pragma: no cover
        logger.warning("resolve_policy: failed to read tenant tier", exc_info=True)
        return "BASIC"
    data = getattr(resp, "data", None) or {}
    return (data.get("tier") or "BASIC").upper()


def resolve_policy(
    *,
    client_id: str,
    agent_slug: str,
    action: str,
    payload: dict[str, Any] | None = None,
    supabase: Any | None = None,
    tier: str | None = None,
    policy: dict[str, Any] | None = None,
) -> PolicyDecision:
    """Decide whether ``action`` requires an Approvals-Tray row or not.

    Pass ``policy`` and/or ``tier`` to short-circuit the DB lookups (used by
    tests and by tools that already have the row in hand).
    """
    if policy is None:
        if supabase is None:
            from blu_supabase_client import get_supabase_client

            supabase = get_supabase_client()
        policy = _lookup_agent_policy(supabase, client_id=client_id, agent_slug=agent_slug)

    if tier is None:
        if supabase is None:
            from blu_supabase_client import get_supabase_client

            supabase = get_supabase_client()
        tier = _lookup_tenant_tier(supabase, client_id=client_id)

    tier_norm = (tier or "BASIC").upper()
    action_override = (policy or {}).get(action) if isinstance(policy, dict) else None
    tier_default = _TIER_DEFAULTS.get(tier_norm, _DEFAULT_FALLBACK)
    resolved = {**_DEFAULT_FALLBACK, **tier_default, **(action_override or {})}

    mode = (resolved.get("mode") or "always").lower()
    threshold = resolved.get("threshold")
    routed_role = resolved.get("routed_role")
    sla_hours = int(resolved.get("sla_hours") or 72)

    payload = payload or {}
    total = _coerce_amount(payload.get("total_amount"))

    requires = False
    reason = ""

    if mode == "never":
        reason = "policy.mode=never"
    elif mode == "always":
        # If a routed role is configured, the action goes to the tray even
        # when the chat caller is the owner — the role might be a different
        # human (e.g. finance-responsible).
        if routed_role:
            requires = True
            reason = f"policy.mode=always; routed_to={routed_role}"
        else:
            reason = "policy.mode=always; owner-only via chat elicitation"
    elif mode == "threshold":
        if threshold is None:
            reason = "policy.mode=threshold without threshold; treating as always"
            requires = bool(routed_role)
        elif total is None:
            # Cannot evaluate threshold safely → require approval.
            requires = True
            reason = f"policy.mode=threshold; payload missing total_amount"
        elif total >= float(threshold):
            requires = True
            reason = f"total_amount {total:.2f} ≥ threshold {float(threshold):.2f}"
        else:
            reason = f"total_amount {total:.2f} < threshold {float(threshold):.2f}"
    else:
        reason = f"unknown policy.mode={mode!r}; defaulting to async approval"
        requires = True

    return PolicyDecision(
        mode=mode,
        threshold=float(threshold) if threshold is not None else None,
        routed_role=routed_role,
        sla_hours=sla_hours,
        requires_async_approval=requires,
        reason=reason,
        raw_policy=dict(resolved),
    )


def _coerce_amount(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ApprovalEngine",
    "ApprovalError",
    "ApprovalRequest",
    "PolicyDecision",
    "resolve_policy",
]
