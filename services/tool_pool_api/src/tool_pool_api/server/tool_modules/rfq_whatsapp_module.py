# tool_pool_api/server/tool_modules/rfq_whatsapp_module.py
"""
WhatsApp integration for RFQ Agent (Phase 2).

Tools for sending RFQs via WhatsApp and parsing supplier replies
using LLM extraction from free-text messages.

**Architecture**:
- Uses vizu_twilio_client for WhatsApp messaging
- Uses vizu_llm_service (FAST tier) for parsing unstructured replies
- client_id injected via mcp_inject_cliente_id
- All message content sanitized before Langfuse logging
"""

import json
import logging
from datetime import UTC, datetime, timezone

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from tool_pool_api.server.dependencies import get_context_service
from vizu_auth.mcp.auth_middleware import mcp_inject_cliente_id
from vizu_supabase_client import get_supabase_client

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# WHATSAPP DISPATCH
# =============================================================================


async def _dispatch_rfq_whatsapp_logic(
    ctx: Context,
    rfq_id: str,
    message_template: str | None = None,
    cliente_id: str | None = None,
) -> dict:
    """
    Send an RFQ to a supplier via WhatsApp.

    Updates the rfq_requests record with communication_channel='whatsapp'
    and the message SID for tracking.

    Args:
        rfq_id: UUID of an existing rfq_requests record (status='sent' from dispatch_rfq)
        message_template: Optional custom message. If not provided, a default
                         Portuguese template is used with item details.

    Returns:
        dict with rfq_id, supplier_name, whatsapp_status, message_sid
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")

    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    try:
        db = get_supabase_client()

        # Fetch the RFQ with supplier info
        rfq_result = db.table("rfq_requests").select(
            "id,status,items,deadline,"
            "supplier_roster(id,name,contact_phone,contact_email)"
        ).eq("id", rfq_id).eq("client_id", cliente_id).single().execute()

        rfq = rfq_result.data
        if not rfq:
            raise ToolError(f"Cotação não encontrada: {rfq_id}")

        if rfq["status"] not in ("sent", "pending"):
            raise ToolError(
                f"Cotação em status '{rfq['status']}' não pode ser enviada. "
                "Apenas cotações 'sent' ou 'pending' podem receber envio WhatsApp."
            )

        supplier = rfq.get("supplier_roster") or {}
        phone = supplier.get("contact_phone")
        supplier_name = supplier.get("name", "Fornecedor")

        if not phone:
            raise ToolError(
                f"Fornecedor '{supplier_name}' não tem telefone cadastrado. "
                "Atualize o cadastro em supplier_roster."
            )

        # Build message
        items = rfq.get("items", [])
        deadline = rfq.get("deadline", "")

        if not message_template:
            items_text = "\n".join(
                f"  • {it.get('name', '?')} — {it.get('qty', 0)} {it.get('unit', 'un')}"
                f"{' (' + it['specs'] + ')' if it.get('specs') else ''}"
                for it in items
            )
            deadline_text = ""
            if deadline:
                try:
                    dl = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                    deadline_text = f"\n\n📅 Prazo para resposta: {dl.strftime('%d/%m/%Y %H:%M')}"
                except ValueError:
                    pass

            message_template = (
                f"Olá {supplier_name}!\n\n"
                f"Gostaríamos de solicitar cotação para os seguintes itens:\n\n"
                f"{items_text}"
                f"{deadline_text}\n\n"
                f"Por favor, responda com o preço unitário de cada item, "
                f"prazo de entrega e condições de pagamento.\n\n"
                f"Obrigado!"
            )

        # Send via Twilio
        try:
            from vizu_twilio_client import TwilioClient
            from vizu_twilio_client.config import get_twilio_settings

            twilio = TwilioClient(get_twilio_settings())
            message_sid = twilio.send_whatsapp(to=phone, body=message_template)

            if not message_sid:
                raise ToolError(f"Falha ao enviar WhatsApp para {supplier_name} ({phone})")

        except ImportError:
            raise ToolError(
                "Módulo vizu_twilio_client não disponível. "
                "Configure TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN."
            )

        # Update RFQ record
        db.table("rfq_requests").update({
            "communication_channel": "whatsapp",
            "whatsapp_message_sid": message_sid,
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", rfq_id).execute()

        logger.info(
            f"[RFQ-WA] WhatsApp sent to {supplier_name} ({phone}): "
            f"SID={message_sid}, items={len(items)}"
        )

        return {
            "rfq_id": rfq_id,
            "supplier_name": supplier_name,
            "whatsapp_status": "sent",
            "message_sid": message_sid,
            "phone": phone,
            "items_count": len(items),
        }

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ-WA] Failed to send WhatsApp: {e}")
        raise ToolError(f"Erro ao enviar WhatsApp: {e}")


# =============================================================================
# PARSE SUPPLIER REPLY
# =============================================================================

_PARSE_REPLY_SYSTEM_PROMPT = """Você é um parser de respostas de fornecedores.
Extraia dados estruturados de mensagens de texto livre sobre cotações de compras.

Responda APENAS com JSON válido no formato:
{
  "prices": [
    {"name": "nome do item", "unit_price": 0.00, "available": true, "moq": 0}
  ],
  "delivery_days": 0,
  "payment_terms": "texto",
  "notes": "observações extras"
}

Regras:
- unit_price deve ser número float (sem R$, sem pontos de milhar)
- Se o item não estiver disponível, marque available=false e unit_price=0
- Se não mencionar prazo de entrega, use delivery_days=0
- Se não mencionar condições de pagamento, use payment_terms=""
- moq (minimum order quantity) = 0 se não mencionado
- Mantenha os nomes dos itens exatamente como aparecem na mensagem"""


async def _parse_supplier_reply_logic(
    ctx: Context,
    rfq_id: str,
    reply_text: str,
    cliente_id: str | None = None,
) -> dict:
    """
    Parse a free-text supplier reply (e.g. from WhatsApp) into structured quote data
    using LLM extraction, then update the rfq_requests record.

    Args:
        rfq_id: UUID of the RFQ this reply corresponds to
        reply_text: Raw text message from the supplier

    Returns:
        dict with rfq_id, parsed_data, confidence, status
    """
    cliente_id = cliente_id or ctx.request_context.lifespan_context.get("cliente_id")

    if not cliente_id:
        raise ToolError("Missing cliente_id in context")

    if not reply_text or not reply_text.strip():
        raise ToolError("Texto da resposta vazio.")

    try:
        db = get_supabase_client()

        # Verify RFQ exists and belongs to this client
        rfq_result = db.table("rfq_requests").select(
            "id,status,items,supplier_id,"
            "supplier_roster(name)"
        ).eq("id", rfq_id).eq("client_id", cliente_id).single().execute()

        rfq = rfq_result.data
        if not rfq:
            raise ToolError(f"Cotação não encontrada: {rfq_id}")

        supplier_info = rfq.get("supplier_roster") or {}
        supplier_name = supplier_info.get("name", "Fornecedor")

        # Build context with original items for better parsing
        original_items = rfq.get("items", [])
        item_names = [it.get("name", "") for it in original_items]

        user_message = (
            f"Itens originais da cotação: {', '.join(item_names)}\n\n"
            f"Resposta do fornecedor {supplier_name}:\n{reply_text}"
        )

        # Use FAST tier LLM for parsing
        from langchain_core.messages import HumanMessage, SystemMessage

        from vizu_llm_service import get_model
        from vizu_llm_service.client import ModelTier

        model = get_model(tier=ModelTier.FAST, tags=["rfq", "whatsapp-parse"])

        messages = [
            SystemMessage(content=_PARSE_REPLY_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]

        response = await model.ainvoke(messages)
        raw_output = response.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        json_str = raw_output
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        parsed_data = json.loads(json_str)

        # Validate structure
        prices = parsed_data.get("prices", [])
        if not prices:
            return {
                "rfq_id": rfq_id,
                "supplier_name": supplier_name,
                "parsed_data": parsed_data,
                "confidence": "low",
                "status": "parse_incomplete",
                "message": "Nenhum preço extraído da resposta. Verifique o texto.",
            }

        # Calculate confidence based on item coverage
        matched = sum(
            1 for p in prices
            if any(
                orig.lower().strip() in p.get("name", "").lower()
                or p.get("name", "").lower() in orig.lower().strip()
                for orig in item_names
            )
        )
        coverage = matched / len(item_names) if item_names else 0
        confidence = "high" if coverage >= 0.8 else "medium" if coverage >= 0.5 else "low"

        # Update RFQ with parsed response
        response_data = {
            "prices": prices,
            "delivery_days": parsed_data.get("delivery_days", 0),
            "payment_terms": parsed_data.get("payment_terms", ""),
            "notes": parsed_data.get("notes", ""),
            "responded_at": datetime.now(UTC).isoformat(),
            "parse_confidence": confidence,
        }

        db.table("rfq_requests").update({
            "status": "responded",
            "response_data": response_data,
            "raw_response": reply_text,
            "updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", rfq_id).execute()

        logger.info(
            f"[RFQ-WA] Parsed reply for {supplier_name}: "
            f"{len(prices)} prices, confidence={confidence}"
        )

        return {
            "rfq_id": rfq_id,
            "supplier_name": supplier_name,
            "parsed_data": response_data,
            "confidence": confidence,
            "status": "responded",
            "items_parsed": len(prices),
            "items_expected": len(item_names),
        }

    except json.JSONDecodeError as e:
        logger.error(f"[RFQ-WA] Failed to parse LLM output as JSON: {e}")
        return {
            "rfq_id": rfq_id,
            "parsed_data": None,
            "confidence": "failed",
            "status": "parse_error",
            "message": (
                "Não foi possível extrair dados estruturados da resposta. "
                "Tente usar submit_mock_response com os dados manualmente."
            ),
            "raw_output": raw_output[:500],
        }
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"[RFQ-WA] Failed to parse supplier reply: {e}")
        raise ToolError(f"Erro ao processar resposta do fornecedor: {e}")


# =============================================================================
# MODULE REGISTRATION
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register WhatsApp RFQ tools."""

    mcp.tool(
        name="dispatch_rfq_whatsapp",
        description=(
            "Envia uma cotação (RFQ) para fornecedor via WhatsApp.\n\n"
            "O fornecedor deve ter contact_phone cadastrado no supplier_roster.\n"
            "Cria a mensagem automaticamente com os itens e prazo, ou use "
            "message_template para personalizar.\n\n"
            "Passe o rfq_id de uma cotação já criada com dispatch_rfq."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_dispatch_rfq_whatsapp_logic))

    mcp.tool(
        name="parse_supplier_reply",
        description=(
            "Processa resposta de fornecedor em texto livre (ex: WhatsApp) "
            "e extrai dados estruturados (preços, prazo, condições) usando IA.\n\n"
            "Passe rfq_id e o texto da resposta do fornecedor.\n"
            "Retorna dados parseados com nível de confiança (high/medium/low)."
        ),
    )(mcp_inject_cliente_id(get_context_service)(_parse_supplier_reply_logic))

    logger.info(
        "[RFQ WhatsApp Module] Tools registered: "
        "dispatch_rfq_whatsapp, parse_supplier_reply"
    )

    return [
        "dispatch_rfq_whatsapp",
        "parse_supplier_reply",
    ]
