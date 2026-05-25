"""
Sprint 4 / D2 — Dedupe de artefatos side-effectful.

Insere uma row em `artifact_log` (UNIQUE execution_id, step_id) ANTES de
disparar entrega. Se conflito → retorna None (artefato já entregue, skip).

Após delivery, chame `mark_artifact_sent(claim_id, outputs)` ou
`mark_artifact_failed(claim_id, error)` para registrar o resultado final.

Uso: ver `agent_api.core.routines._execute_artifact_step` (artifact step).
"""

from __future__ import annotations

import logging
from typing import Any

from blu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


async def claim_artifact(
    *,
    execution_id: str,
    step_id: str,
    client_id: str,
    artifact_type: str,
    function_name: str,
) -> str | None:
    """
    Tenta inserir claim em artifact_log. Retorna claim_id (uuid) se 1ª vez,
    None se já existe (dedupe hit — caller deve skipar a entrega).
    """
    try:
        resp = (
            get_supabase_client()
            .table("artifact_log")
            .insert(
                {
                    "execution_id": execution_id,
                    "step_id": step_id,
                    "client_id": client_id,
                    "artifact_type": artifact_type,
                    "function_name": function_name,
                    "status": "claimed",
                },
                returning="representation",
            )
            .execute()
        )
        if resp.data:
            return resp.data[0]["id"]
        return None
    except Exception as exc:
        # Duplicate key (23505) — supabase-py exposes via APIError.message
        msg = str(exc).lower()
        if "duplicate" in msg or "23505" in msg or "artifact_log_dedupe_uq" in msg:
            logger.info(
                "[artifact_dedupe] hit: execution_id=%s step_id=%s type=%s already delivered",
                execution_id, step_id, artifact_type,
            )
            return None
        logger.exception("[artifact_dedupe] claim failed (non-dedupe error)")
        raise


async def mark_artifact_sent(claim_id: str, outputs: dict[str, Any]) -> None:
    """Marca claim como entregue com sucesso."""
    try:
        (
            get_supabase_client()
            .table("artifact_log")
            .update(
                {
                    "status": "sent",
                    "outputs": outputs,
                    "sent_at": "now()",
                }
            )
            .eq("id", claim_id)
            .execute()
        )
    except Exception:
        logger.exception("[artifact_dedupe] mark_sent failed for claim_id=%s", claim_id)


async def mark_artifact_failed(claim_id: str, error: str) -> None:
    """Marca claim como falha. Permite reprocessamento manual via DELETE."""
    try:
        (
            get_supabase_client()
            .table("artifact_log")
            .update({"status": "failed", "error": error})
            .eq("id", claim_id)
            .execute()
        )
    except Exception:
        logger.exception("[artifact_dedupe] mark_failed failed for claim_id=%s", claim_id)
