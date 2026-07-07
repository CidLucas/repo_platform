"""
Artifact handler registry for routine step execution.

Artifact steps produce side effects (emails, alerts, stored documents) and
return a small dict with delivery metadata merged into routine state.

Registration:
    @register("channels.send_email_batch")
    async def my_handler(inputs: dict, client_id: str) -> dict: ...

Calling from the runner:
    from agent_api.core.routine_artifacts import call as call_artifact
    outputs = await call_artifact("channels.send_email_batch", inputs, client_id)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

ArtifactHandler = Callable[[dict, str], Awaitable[dict]]

_REGISTRY: dict[str, ArtifactHandler] = {}
_METADATA: dict[str, dict] = {}


def _make_label(name: str) -> str:
    ns, _, fn = name.partition(".")
    return f"{ns.title()} › {fn.replace('_', ' ').title()}"


def register(
    name: str,
    *,
    description: str = "",
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
) -> Callable[[ArtifactHandler], ArtifactHandler]:
    def decorator(fn: ArtifactHandler) -> ArtifactHandler:
        _REGISTRY[name] = fn
        doc_first_line = (fn.__doc__ or "").strip().split("\n")[0].strip()
        _METADATA[name] = {
            "id": name,
            "label": _make_label(name),
            "description": description or doc_first_line,
            "inputs": inputs or [],
            "outputs": outputs or [],
        }
        return fn
    return decorator


async def call(name: str, inputs: dict, client_id: str) -> dict:
    """Call a registered artifact handler by name. Raises KeyError if unknown."""
    fn = _REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"Unknown artifact handler: '{name}'. Available: {list(_REGISTRY)}")
    try:
        result = await fn(inputs, client_id)
        return result if isinstance(result, dict) else {"artifact_result": result}
    except Exception:
        logger.exception("[routine_artifact] %s failed for client %s", name, client_id)
        raise


def list_artifacts_with_meta() -> list[dict]:
    return [_METADATA.get(k, {"id": k, "label": k, "description": "", "inputs": [], "outputs": []}) for k in sorted(_REGISTRY)]


# ---------------------------------------------------------------------------
# channels.* — delivery handlers
# ---------------------------------------------------------------------------


@register(
    "channels.send_email_batch",
    description="Envia e-mails personalizados em lote, um por destinatário, com log de entrega.",
    inputs=[
        {"key": "emails", "type": "list", "description": "Lista de objetos {to_email, subject, body_html}", "required": True},
    ],
    outputs=[
        {"key": "emails_sent", "type": "int", "description": "Quantidade de e-mails entregues com sucesso"},
        {"key": "emails_failed", "type": "int", "description": "Quantidade de e-mails com falha"},
        {"key": "delivery_log", "type": "list", "description": "Log por destinatário com status de entrega"},
    ],
)
async def _send_email_batch(inputs: dict, client_id: str) -> dict:
    """
    Send a batch of personalised emails.

    inputs:
        emails — list of {to_email, subject, body_html} dicts

    outputs:
        emails_sent   — int
        emails_failed — int
        delivery_log  — list of {to_email, status}
    """
    emails: list[dict[str, Any]] = inputs.get("emails", [])
    if not emails:
        logger.warning("[routine_artifact] send_email_batch: empty email list for %s", client_id)
        return {"emails_sent": 0, "emails_failed": 0, "delivery_log": []}

    sent = 0
    failed = 0
    log: list[dict] = []

    for item in emails:
        to = item.get("to_email") or item.get("to", "")
        subject = item.get("subject", "(sem assunto)")
        body_html = item.get("body_html") or item.get("body", "")

        if not to:
            failed += 1
            log.append({"to_email": to, "status": "skipped_no_address"})
            continue

        try:
            await _deliver_email(to, subject, body_html, client_id)
            sent += 1
            log.append({"to_email": to, "status": "sent"})
        except Exception as exc:
            logger.warning("[routine_artifact] email to %s failed: %s", to, exc)
            failed += 1
            log.append({"to_email": to, "status": "failed", "error": str(exc)})

    logger.info(
        "[routine_artifact] send_email_batch: client=%s sent=%d failed=%d",
        client_id, sent, failed,
    )
    return {"emails_sent": sent, "emails_failed": failed, "delivery_log": log}


@register(
    "channels.send_email",
    description="Envia um único e-mail via SendGrid.",
    inputs=[
        {"key": "to", "type": "str", "description": "Endereço do destinatário", "required": True},
        {"key": "subject", "type": "str", "description": "Assunto do e-mail", "required": True},
        {"key": "body_html", "type": "str", "description": "Corpo HTML do e-mail (ou body para texto simples)", "required": True},
    ],
    outputs=[
        {"key": "email_sent", "type": "bool", "description": "True se o e-mail foi enviado com sucesso"},
    ],
)
async def _send_email(inputs: dict, client_id: str) -> dict:
    """
    Send a single email.

    inputs:
        to       — recipient address
        subject  — email subject
        body_html — HTML body (or body as plain text fallback)

    outputs:
        email_sent — bool
    """
    to = inputs.get("to", "")
    subject = inputs.get("subject", "(sem assunto)")
    body_html = inputs.get("body_html") or inputs.get("body", "")

    if not to:
        logger.warning("[routine_artifact] send_email: no recipient for client %s", client_id)
        return {"email_sent": False}

    try:
        await _deliver_email(to, subject, body_html, client_id)
        logger.info("[routine_artifact] send_email: sent to %s", to)
        return {"email_sent": True}
    except Exception as exc:
        logger.warning("[routine_artifact] send_email to %s failed: %s", to, exc)
        return {"email_sent": False, "email_error": str(exc)}


@register(
    "channels.create_alert",
    description="Cria um alerta in-app visível no painel do cliente.",
    inputs=[
        {"key": "title", "type": "str", "description": "Título do alerta (máx 200 caracteres)", "required": True},
        {"key": "body", "type": "str", "description": "Texto do alerta / snippet do conteúdo gerado", "required": True},
        {"key": "priority", "type": "str", "description": "Prioridade: low | normal | high", "default": "normal", "required": False},
        {"key": "agent_slug", "type": "str", "description": "Slug do agente que gerou o alerta (opcional)", "required": False},
        {"key": "artifact_type", "type": "str", "description": "Tipo do artefato gerado: document | email | report (opcional)", "required": False},
        {"key": "artifact_id", "type": "str", "description": "UUID do artefato gerado (use {{document_id}} de um passo anterior)", "required": False},
        {"key": "artifact_url", "type": "str", "description": "URL externa do artefato (para reports)", "required": False},
        {"key": "execution_id", "type": "str", "description": "UUID da execução (client_routine_executions.id) — preenchido automaticamente pelo engine", "required": False},
        {"key": "routine_id", "type": "str", "description": "ID da rotina que gerou o alerta — preenchido automaticamente pelo engine", "required": False},
    ],
    outputs=[
        {"key": "alert_id", "type": "str", "description": "UUID do alerta criado"},
        {"key": "alert_created", "type": "bool", "description": "True se o alerta foi criado com sucesso"},
    ],
)
async def _create_alert(inputs: dict, client_id: str) -> dict:
    """
    Create an in-app alert by inserting into approval_requests.
    Alerts differ from approvals: action_type='routine_alert', no approval needed.

    inputs:
        title         — alert title (max 200 chars)
        body          — alert body / snippet of generated content
        priority      — 'low' | 'normal' | 'high' (default 'normal')
        agent_slug    — which agent generated this (optional)
        artifact_type — 'document' | 'email' | 'report' (optional)
        artifact_id   — UUID of the linked artifact in public.documents (optional)
        artifact_url  — external URL for reports (optional)

    outputs:
        alert_id      — UUID of the created row
        alert_created — bool
    """
    from blu_supabase_client import get_supabase_client

    title = str(inputs.get("title", "Alerta de Rotina"))[:200]
    body = str(inputs.get("body", ""))
    priority = inputs.get("priority", "normal")
    agent_slug = inputs.get("agent_slug", "routine-runner")
    artifact_type = inputs.get("artifact_type", "")
    artifact_id = inputs.get("artifact_id", "")
    artifact_url = inputs.get("artifact_url", "")

    metadata: dict = {}
    if artifact_type:
        metadata["artifact_type"] = artifact_type
    if artifact_id:
        metadata["artifact_id"] = artifact_id
    if artifact_url:
        metadata["artifact_url"] = artifact_url

    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.table("approval_requests")
            .insert({
                "client_id": client_id,
                "requested_by": "routine-runner",
                "action_type": "routine_alert",
                "title": title,
                "body": body,
                "priority": priority,
                "agent_slug": agent_slug,
                "status": "pending",
                "payload": {
                    "source": "routine",
                    "execution_id": inputs.get("execution_id", ""),
                    "routine_id": inputs.get("routine_id", ""),
                },
                "metadata": metadata or None,
            })
            .execute()
        )
        alert_id = resp.data[0]["id"] if resp.data else None
        logger.info("[routine_artifact] create_alert: id=%s for client=%s", alert_id, client_id)
        return {"alert_id": alert_id, "alert_created": True}

    except Exception as exc:
        logger.warning("[routine_artifact] create_alert failed for %s: %s", client_id, exc)
        return {"alert_id": "", "alert_status": "failed", "alert_error": str(exc)}


@register(
    "channels.request_approval",
    description="Cria uma solicitação de aprovação humana (HITL) vinculada à execução atual. A rotina pausa até o operador aprovar.",
    inputs=[
        {"key": "title", "type": "str", "description": "Título exibido no painel de aprovação", "required": True},
        {"key": "body", "type": "str", "description": "Conteúdo gerado para revisão (JSON ou texto)", "required": True},
        {"key": "execution_id", "type": "str", "description": "ID da execução atual — injetado automaticamente pelo engine", "required": True},
        {"key": "priority", "type": "str", "description": "Prioridade: low | normal | high", "default": "normal", "required": False},
        {"key": "agent_slug", "type": "str", "description": "Slug do agente que gerou o conteúdo", "default": "routine-runner", "required": False},
    ],
    outputs=[
        {"key": "approval_id", "type": "str", "description": "UUID da approval_request criada"},
        {"key": "_awaiting_approval", "type": "bool", "description": "Sinaliza ao engine que a execução deve pausar"},
    ],
)
async def _request_approval(inputs: dict, client_id: str) -> dict:
    """
    HITL: create an approval_request with status='pending' linked to the execution.
    Returns _awaiting_approval=True so the engine pauses and sets status='awaiting_approval'.
    The DB trigger on approval_requests re-dispatches the execution when approved.
    """
    import json as _json

    from blu_supabase_client import get_supabase_client

    execution_id = str(inputs.get("execution_id", ""))
    title = str(inputs.get("title", "Aprovação necessária"))[:200]
    body = inputs.get("body", "")
    priority = inputs.get("priority", "normal")
    agent_slug = inputs.get("agent_slug", "routine-runner")

    # Serialize body to string if it's a complex object
    if not isinstance(body, str):
        body = _json.dumps(body, ensure_ascii=False)

    db = get_supabase_client(use_service_role=True)

    try:
        resp = await asyncio.to_thread(
            lambda: db.table("approval_requests")
            .insert({
                "client_id": client_id,
                "requested_by": "routine-runner",
                "action_type": "routine_hitl",
                "title": title,
                "body": body,
                "priority": priority,
                "agent_slug": agent_slug,
                "status": "pending",
                "payload": {"execution_id": execution_id, "source": "routine_hitl"},
            })
            .execute()
        )
        approval_id = (resp.data or [{}])[0].get("id") or ""
        logger.info(
            "[routine_artifact] request_approval: exec=%s approval=%s client=%s",
            execution_id, approval_id, client_id,
        )
        return {"approval_id": approval_id, "_awaiting_approval": True}

    except Exception as exc:
        logger.warning("[routine_artifact] request_approval failed for %s: %s", client_id, exc)
        # On failure, don't block execution — return without the pause signal
        return {"approval_id": None, "_awaiting_approval": False, "approval_error": str(exc)}


@register(
    "channels.send_whatsapp",
    description="Envia mensagem WhatsApp via Twilio.",
    inputs=[
        {"key": "to", "type": "str", "description": "Número no formato E.164 (ex: +5511999999999)", "required": True},
        {"key": "body", "type": "str", "description": "Texto da mensagem", "required": True},
    ],
    outputs=[
        {"key": "whatsapp_sent", "type": "bool", "description": "True se a mensagem foi enviada com sucesso"},
    ],
)
async def _send_whatsapp(inputs: dict, client_id: str) -> dict:
    """
    Send a WhatsApp message via Twilio.

    inputs:
        to   — phone in E.164 format (e.g. +5511999999999); also accepted as 'phone'
        body — message text

    outputs:
        whatsapp_sent — bool
    """
    to: str = inputs.get("to") or inputs.get("phone", "")
    body: str = inputs.get("body", "")

    if not to:
        logger.warning("[routine_artifact] send_whatsapp: no recipient for client %s", client_id)
        return {"whatsapp_sent": False}

    try:
        from blu_twilio_client import TwilioClient
        from blu_twilio_client.config import get_twilio_settings
        twilio = TwilioClient(get_twilio_settings())
        await asyncio.to_thread(twilio.send_whatsapp, to, body)
        logger.info("[routine_artifact] send_whatsapp: sent to %s", to)
        return {"whatsapp_sent": True}
    except Exception as exc:
        logger.warning("[routine_artifact] send_whatsapp to %s failed: %s", to, exc)
        return {"whatsapp_sent": False, "whatsapp_error": str(exc)}


# ---------------------------------------------------------------------------
# storage.* — document persistence
# ---------------------------------------------------------------------------


def _markdown_to_tiptap(content: str) -> dict:
    """Convert plain markdown text to a minimal Tiptap document JSON."""
    paragraphs = []
    for line in content.split("\n"):
        text = line.rstrip()
        if text:
            paragraphs.append({"type": "paragraph", "content": [{"type": "text", "text": text}]})
        else:
            paragraphs.append({"type": "paragraph"})
    return {"type": "doc", "content": paragraphs or [{"type": "paragraph"}]}


@register(
    "storage.save_context_document",
    description="Salva documento markdown no Storage e indexa no RAG para uso pelos agentes. Também persiste em public.documents para edição no app.",
    inputs=[
        {"key": "content", "type": "str", "description": "Conteúdo markdown do documento", "required": True},
        {"key": "title", "type": "str", "description": "Título do documento", "required": True},
        {"key": "file_name", "type": "str", "description": "Nome do arquivo no Storage", "default": "context_map.md", "required": False},
        {"key": "category", "type": "str", "description": "Categoria para indexação no RAG", "default": "business_context", "required": False},
    ],
    outputs=[
        {"key": "document_saved", "type": "bool", "description": "True se o documento foi salvo com sucesso"},
        {"key": "storage_path", "type": "str", "description": "Caminho do arquivo no bucket knowledge-base"},
        {"key": "document_id", "type": "str", "description": "UUID do documento em public.documents (para referenciar no alerta)"},
    ],
)
async def _save_context_document(inputs: dict, client_id: str) -> dict:
    """
    Upload a markdown document to Supabase Storage and index it in the RAG
    knowledge base via the process-document Edge Function.

    inputs:
        content   — markdown string
        title     — document title
        file_name — storage file name (default: context_map.md)
        category  — vector_db category tag (default: business_context)

    outputs:
        document_saved — bool
        storage_path   — path in the knowledge-base bucket
    """
    import os

    import httpx
    from blu_supabase_client import get_supabase_client

    content = inputs.get("content", "") or ""
    if isinstance(content, dict):
        content = content.get("filled_masterprompt") or ""
    if not isinstance(content, str):
        content = str(content)
    content = "\n".join(content.splitlines())
    title = inputs.get("title", "Business Context Map")
    file_name = inputs.get("file_name", "context_map.md")
    category = inputs.get("category", "business_context")

    if not content.strip():
        logger.warning("[routine_artifact] save_context_document: empty content for %s", client_id)
        return {"document_saved": False, "storage_path": ""}

    storage_path = f"{client_id}/{file_name}"
    db = get_supabase_client(use_service_role=True)

    try:
        # 1. Archive previous version of this document
        await asyncio.to_thread(
            lambda: db.schema("vector_db")
            .table("documents")
            .update({"source": "archived"})
            .eq("client_id", client_id)
            .eq("source", "generated")
            .eq("category", category)
            .eq("file_name", file_name)
            .execute()
        )

        # 2. Upload to Storage (upsert)
        raw = content.encode("utf-8")
        await asyncio.to_thread(
            lambda: db.storage.from_("knowledge-base").upload(
                storage_path,
                raw,
                file_options={"content-type": "text/markdown; charset=utf-8", "upsert": "true"},
            )
        )

        # 3. Insert document row for processing
        resp = await asyncio.to_thread(
            lambda: db.schema("vector_db")
            .table("documents")
            .insert({
                "client_id": client_id,
                "title": title,
                "file_name": file_name,
                "file_type": "md",
                "storage_path": storage_path,
                "source": "generated",
                "scope": "client",
                "category": category,
                "status": "pending",
            })
            .execute()
        )
        if not resp.data:
            raise RuntimeError("documents INSERT returned no rows")
        document_id: str = resp.data[0]["id"]

        # 4. Trigger process-document Edge Function (async — don't block routine)
        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        anon_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("VITE_SUPABASE_ANON_KEY", "")
        service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        bearer = service_key if service_key.startswith("eyJ") else anon_key

        async with httpx.AsyncClient(timeout=120.0) as client_http:
            await client_http.post(
                f"{supabase_url}/functions/v1/process-document",
                json={
                    "document_id": document_id,
                    "storage_path": storage_path,
                    "client_id": client_id,
                    "file_name": file_name,
                    "file_type": "md",
                    "target_tokens": 300,
                    "skip_metadata_enrichment": True,
                },
                headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
            )

        # Fire document_created event so any subscribed routines can react.
        # Best-effort: a failure here must not roll back the save.
        try:
            await asyncio.to_thread(
                lambda: db.rpc("fire_event_for_client", {
                    "p_event_type": "document_created",
                    "p_client_id": client_id,
                    "p_trigger_data": {
                        "event_type": "document_created",
                        "category": category,
                        "document_id": document_id,
                        "file_name": file_name,
                        "storage_path": storage_path,
                    },
                }).execute()
            )
        except Exception as ev_exc:
            logger.warning(
                "[routine_artifact] fire_event_for_client(document_created) failed for %s: %s",
                client_id, ev_exc,
            )

        # 5. Also persist to public.documents so the user can view/edit in the app
        tiptap_content = _markdown_to_tiptap(content)
        pub_resp = await asyncio.to_thread(
            lambda: db.table("documents")
            .upsert(
                {
                    "client_id": client_id,
                    "title": title,
                    "agent_slug": "documentos",
                    "editor_content": tiptap_content,
                },
                on_conflict="client_id,title",
                returning="representation",
            )
            .execute()
        )
        public_document_id: str | None = pub_resp.data[0]["id"] if pub_resp.data else None
        if not public_document_id:
            logger.warning(
                "[routine_artifact] save_context_document: public.documents upsert returned no rows for %s", client_id
            )

        logger.info(
            "[routine_artifact] save_context_document: saved %d bytes to %s (doc_id=%s)",
            len(raw), storage_path, public_document_id,
        )

        return {"document_saved": True, "storage_path": storage_path, "document_id": public_document_id or ""}

    except Exception as exc:
        logger.warning(
            "[routine_artifact] save_context_document failed for %s: %s", client_id, exc
        )
        return {"document_saved": False, "storage_path": storage_path, "document_id": "", "save_error": str(exc)}



_DIMENSION_TO_ROOM: dict[str, str] = {
    "finance":    "financeiro",
    "financas":   "financeiro",
    "commercial": "clientes",
    "comercial":  "clientes",
    "inventory":  "compras",
    "supply":     "compras",
    "estoque":    "compras",
    "strategy":   "estrategia",
}


def _map_dimension_to_room(dimension: str) -> str:
    """Map legacy dimension slugs to room slugs. Passthrough for unknown values."""
    return _DIMENSION_TO_ROOM.get(dimension, dimension)


# client_insights.severity tem CHECK (info|warning|error); um valor fora do enum
# abortaria o insert em lote inteiro
_ALLOWED_SEVERITIES = {"info", "warning", "error"}
_SEVERITY_ALIASES = {"alert": "warning", "warn": "warning", "critical": "error", "crit": "error"}


def _normalize_severity(value: object) -> str:
    sev = str(value or "info").strip().lower()
    sev = _SEVERITY_ALIASES.get(sev, sev)
    return sev if sev in _ALLOWED_SEVERITIES else "info"


@register(
    "storage.save_insights",
    description="Persiste lista de insights gerados no banco de dados, exibidos nos cards de cada room.",
    inputs=[
        {"key": "insights", "type": "list", "description": "Lista de insights (use {{insights}}). Cada item: {room, kpi, title, observation, severity, recommendation?}. room: financeiro|clientes|compras|agenda|estrategia", "required": True},
    ],
    outputs=[
        {"key": "insights_written", "type": "int", "description": "Quantidade de insights salvos com sucesso"},
    ],
)
async def _save_insights(inputs: dict, client_id: str) -> dict:
    """
    Upsert a list of insights into client_insights.

    inputs:
        insights — list of dicts with keys:
                   room, kpi, title, observation, severity,
                   recommendation (optional), metric_value (optional),
                   baseline_value (optional), variance_pct (optional)

    outputs:
        insights_written — int
    """
    from datetime import date, datetime, timezone

    from blu_supabase_client import get_supabase_client

    insights = inputs.get("insights", [])
    if isinstance(insights, str):
        # Steps anteriores podem entregar a lista serializada (template inline)
        try:
            insights = json.loads(insights)
        except (ValueError, TypeError):
            insights = None
    if not isinstance(insights, list):
        logger.warning("[routine_artifact] save_insights: insights is not a list for %s", client_id)
        return {"insights_written": 0}

    if not insights:
        return {"insights_written": 0}

    db = get_supabase_client(use_service_role=True)
    run_date = date.today().isoformat()
    now = datetime.now(timezone.utc).isoformat()

    # B3.3 / Issue #121 — Batch insert all insights in a single DB call
    valid = [it for it in insights if isinstance(it, dict)]
    if not valid:
        return {"insights_written": 0}
    try:
        await asyncio.to_thread(
            lambda: db.table("client_insights").insert([
                {
                    "client_id": client_id,
                    "room": _map_dimension_to_room(it.get("room") or it.get("dimension") or "financeiro"),
                    "kpi": it.get("kpi"),
                    "title": str(it.get("title", "Insight"))[:200],
                    "body": it.get("body") or it.get("observation"),
                    "observation": it.get("observation"),
                    "recommendation": it.get("recommendation"),
                    "severity": _normalize_severity(it.get("severity")),
                    "metric_value": it.get("metric_value"),
                    "baseline_value": it.get("baseline_value"),
                    "variance_pct": it.get("variance_pct"),
                    "run_date": run_date,
                    "generated_at": now,
                    "dismissed": False,
                }
                for it in valid
            ]).execute()
        )
    except Exception as exc:
        logger.warning(
            "[routine_artifact] save_insights: failed to batch insert insights for %s: %s",
            client_id,
            exc,
        )
        return {"insights_written": 0}
    logger.info(
        "[routine_artifact] save_insights: wrote %d insights for %s",
        len(valid),
        client_id,
    )
    return {"insights_written": len(valid)}


# ---------------------------------------------------------------------------
@register(
    "channels.request_document_review",
    description="Salva documento como rascunho e cria solicitação de revisão humana (HITL). Aparece na aba Rascunhos da Biblioteca.",
    inputs=[
        {"key": "title", "type": "str", "description": "Título do documento", "required": True},
        {"key": "content", "type": "str", "description": "Conteúdo markdown do documento gerado", "required": True},
        {"key": "summary", "type": "str", "description": "Resumo em 1-2 frases do que o documento contém", "required": True},
        {"key": "agent_slug", "type": "str", "description": "Slug do agente que gerou (ex: biblioteca, estrategia)", "default": "biblioteca", "required": False},
        {"key": "priority", "type": "str", "description": "Prioridade: low | normal | high", "default": "normal", "required": False},
        {"key": "execution_id", "type": "str", "description": "ID da execução atual — injetado pelo engine", "required": False},
    ],
    outputs=[
        {"key": "document_id", "type": "str", "description": "UUID do documento criado em public.documents (status=draft)"},
        {"key": "approval_id", "type": "str", "description": "UUID da approval_request criada"},
        {"key": "_awaiting_approval", "type": "bool", "description": "Sinaliza ao engine que a execução deve pausar"},
    ],
)
async def _request_document_review(inputs: dict, client_id: str) -> dict:
    """
    HITL for document review:
    1. Insert a row in public.documents with status='draft', agent_slug from input.
    2. Insert an approval_request with action_type='document_review', linking the document.
    3. Return _awaiting_approval=True so the engine pauses execution.

    inputs:
        title        — document title
        content      — markdown body
        summary      — 1-2 line description shown in the approval card
        agent_slug   — which agent generated this
        priority     — approval priority
        execution_id — routine execution id (for re-dispatch on approval)

    outputs:
        document_id        — uuid of the saved draft document
        approval_id        — uuid of the approval_request row
        _awaiting_approval — True (pauses routine execution)
    """
    import json as _json

    from blu_supabase_client import get_supabase_client

    title = str(inputs.get("title", "Documento sem título"))[:200]
    content = inputs.get("content", "")
    summary = str(inputs.get("summary", ""))[:500]
    agent_slug = inputs.get("agent_slug", "biblioteca")
    priority = inputs.get("priority", "normal")
    execution_id = str(inputs.get("execution_id", ""))

    if not content:
        logger.warning("[routine_artifact] request_document_review: empty content for %s", client_id)
        return {"document_id": None, "approval_id": None, "_awaiting_approval": False}

    db = get_supabase_client(use_service_role=True)
    document_id: str | None = None
    approval_id: str | None = None

    # 1. Save draft document
    try:
        def _to_tiptap(md: str) -> dict:
            paragraphs = []
            for line in md.split("\n"):
                t = line.rstrip()
                if t:
                    paragraphs.append({"type": "paragraph", "content": [{"type": "text", "text": t}]})
                else:
                    paragraphs.append({"type": "paragraph"})
            return {"type": "doc", "content": paragraphs or [{"type": "paragraph"}]}

        resp = await asyncio.to_thread(
            lambda: db.table("documents")
            .insert({
                "client_id": client_id,
                "title": title,
                "agent_slug": agent_slug,
                "status": "draft",
                "editor_content": _to_tiptap(content),
            })
            .execute()
        )
        document_id = (resp.data or [{}])[0].get("id")
        logger.info("[routine_artifact] request_document_review: draft doc_id=%s", document_id)
    except Exception as exc:
        logger.warning("[routine_artifact] request_document_review: doc insert failed for %s: %s", client_id, exc)
        return {"document_id": None, "approval_id": None, "_awaiting_approval": False, "error": str(exc)}

    # 2. Create approval request
    try:
        resp2 = await asyncio.to_thread(
            lambda: db.table("approval_requests")
            .insert({
                "client_id": client_id,
                "requested_by": "routine-runner",
                "action_type": "document_review",
                "title": f"Revisar: {title}",
                "body": summary,
                "priority": priority,
                "agent_slug": agent_slug,
                "status": "pending",
                "payload": {
                    "document_id": document_id,
                    "execution_id": execution_id,
                    "source": "document_review",
                },
                "metadata": {
                    "artifact_type": "document",
                    "artifact_id": document_id,
                },
            })
            .execute()
        )
        approval_id = (resp2.data or [{}])[0].get("id")
        logger.info(
            "[routine_artifact] request_document_review: approval_id=%s doc_id=%s client=%s",
            approval_id, document_id, client_id,
        )
    except Exception as exc:
        logger.warning("[routine_artifact] request_document_review: approval insert failed for %s: %s", client_id, exc)
        # Doc already saved — don't block, but don't pause execution either
        return {"document_id": document_id, "approval_id": None, "_awaiting_approval": False, "error": str(exc)}

    return {
        "document_id": document_id,
        "approval_id": approval_id,
        "_awaiting_approval": True,
    }


# Internal delivery helper
# ---------------------------------------------------------------------------


async def _deliver_email(to: str, subject: str, body_html: str, client_id: str) -> None:
    """
    Deliver a single email. Tries Twilio Email (SendGrid) if configured,
    falls back to logging for non-production environments.
    """
    import os

    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("EMAIL_FROM", "noreply@blu.com.br")

    if sendgrid_key:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                "https://api.sendgrid.com/v3/mail/send",
                json={
                    "personalizations": [{"to": [{"email": to}]}],
                    "from": {"email": from_email},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": body_html}],
                },
                headers={
                    "Authorization": f"Bearer {sendgrid_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code not in (200, 202):
                raise RuntimeError(f"SendGrid returned {resp.status_code}: {resp.text}")
    else:
        # Dev/test: log instead of sending
        logger.info(
            "[routine_artifact] EMAIL (no provider configured): to=%s subject=%r client=%s",
            to, subject, client_id,
        )
