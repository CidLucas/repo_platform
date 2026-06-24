# tool_pool_api/server/tool_modules/communication_module.py
"""
Módulo Communication — D5 (v3 architecture)

Semântica unificada de comunicação externa do cliente: envio de mensagens,
parsing de respostas livres e disparo de cotações por canal.

Tools expostas ao LLM (3):
  send_message        — envia ou rascunha mensagem para contato do cliente (CRM/comercial)
  send_rfq_via_channel — dispara cotação para fornecedor via canal (WhatsApp/email)
  parse_incoming_reply — parseia resposta livre com context_type="rfq"|"nps"|"payment"

Lógica de negócio:
  - Cores originais (draft_consumer_reply_core, send_consumer_reply_core,
    parse_supplier_reply_core, _dispatch_rfq_whatsapp_logic) mantidas intactas
    para reuso por webhooks e testes unitários.
  - Este módulo é wrapper semântico — não duplica lógica.
"""

import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# SEND_MESSAGE — mensagem para contato do cliente (CRM/comercial)
# =============================================================================


async def _send_message_logic(
    contact_id: str,
    action: str = "draft",
    hint: str | None = None,
    message_id: str | None = None,
    edited_body: str | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Envia ou rascunha mensagem de resposta para um contato do cliente.

    action="draft"  → gera rascunho de resposta com IA baseado no histórico do contato
    action="send"   → promove rascunho existente para envio (ou aprovação, conforme política)

    Args:
        contact_id:  UUID do contato (consumer_contacts)
        action:      "draft" ou "send" (padrão: "draft")
        hint:        Orientação para o LLM ao gerar o rascunho (apenas action=draft)
        message_id:  UUID da mensagem rascunho a enviar (apenas action=send)
        edited_body: Corpo editado antes de enviar (apenas action=send, opcional)
    """
    from tool_pool_api.server.tool_modules.consumer_inbox_module import (
        draft_consumer_reply_core,
        send_consumer_reply_core,
    )

    if not client_id:
        raise ToolError("client_id não disponível — autenticação necessária.")

    action = (action or "draft").strip().lower()

    if action == "draft":
        if not contact_id:
            raise ToolError("contact_id é obrigatório para action='draft'.")
        return await draft_consumer_reply_core(
            client_id=client_id,
            contact_id=contact_id,
            hint=hint,
        )

    if action == "send":
        if not message_id:
            raise ToolError("message_id é obrigatório para action='send'.")
        return await send_consumer_reply_core(
            client_id=client_id,
            message_id=message_id,
            edited_body=edited_body,
        )

    raise ToolError(
        f"action='{action}' inválido. Valores aceitos: 'draft', 'send'."
    )


# =============================================================================
# SEND_RFQ_VIA_CHANNEL — disparo de cotação por canal
# =============================================================================


async def _send_rfq_via_channel_logic(
    rfq_id: str,
    channel: str = "whatsapp",
    message_template: str | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Envia uma cotação (RFQ) para um fornecedor pelo canal especificado.

    Atualmente suporta channel="whatsapp". Outros canais (email, sms) serão
    adicionados sem mudança de interface.

    Args:
        rfq_id:           UUID da cotação (rfq_requests, status='sent' ou 'pending')
        channel:          Canal de envio: "whatsapp" (padrão)
        message_template: Mensagem personalizada (opcional — gera automaticamente se omitida)
    """
    channel = (channel or "whatsapp").strip().lower()

    if channel == "whatsapp":
        from tool_pool_api.server.tool_modules.rfq_whatsapp_module import (
            _dispatch_rfq_whatsapp_logic,
        )
        return await _dispatch_rfq_whatsapp_logic(
            ctx=ctx,
            rfq_id=rfq_id,
            message_template=message_template,
            client_id=client_id,
        )

    raise ToolError(
        f"channel='{channel}' ainda não suportado. Canal disponível: 'whatsapp'."
    )


# =============================================================================
# PARSE_INCOMING_REPLY — parsing de resposta livre por contexto
# =============================================================================

_PARSE_PROMPTS: dict[str, str] = {
    "rfq": (
        "Você é um parser de respostas de fornecedores sobre cotações de compras. "
        "Extraia dados estruturados de mensagens de texto livre.\n\n"
        "Responda APENAS com JSON válido no formato:\n"
        "{\n"
        '  "prices": [{"name": "item", "unit_price": 0.00, "available": true, "moq": 0}],\n'
        '  "delivery_days": 0,\n'
        '  "payment_terms": "texto",\n'
        '  "notes": "observações extras"\n'
        "}\n\n"
        "Regras:\n"
        "- unit_price: float sem R$ ou pontos de milhar\n"
        "- available=false + unit_price=0 se item indisponível\n"
        "- delivery_days=0 se não mencionado; payment_terms='' se não mencionado\n"
        "- moq=0 se não mencionado\n"
        "- Mantenha nomes dos itens como na mensagem"
    ),
    "nps": (
        "Você é um parser de respostas de NPS/pesquisa de satisfação. "
        "Extraia dados estruturados do texto livre.\n\n"
        "Responda APENAS com JSON válido no formato:\n"
        "{\n"
        '  "score": null,\n'
        '  "sentiment": "positive|neutral|negative",\n'
        '  "main_feedback": "resumo em 1 frase",\n'
        '  "topics": ["lista", "de", "tópicos"]\n'
        "}\n\n"
        "Regras:\n"
        "- score: número 0-10 se mencionado explicitamente, null caso contrário\n"
        "- sentiment: baseado no tom geral da mensagem\n"
        "- topics: temas recorrentes (entrega, atendimento, preço, produto, etc.)"
    ),
    "payment": (
        "Você é um parser de respostas sobre pagamentos e cobranças. "
        "Extraia dados estruturados do texto livre.\n\n"
        "Responda APENAS com JSON válido no formato:\n"
        "{\n"
        '  "intent": "will_pay|paid|dispute|ignore|other",\n'
        '  "promised_date": null,\n'
        '  "amount_mentioned": null,\n'
        '  "reason": "motivo do atraso se mencionado",\n'
        '  "notes": "observações extras"\n'
        "}\n\n"
        "Regras:\n"
        "- intent: intenção do pagador\n"
        "- promised_date: ISO date se mencionada (ex: '2026-06-10'), null caso contrário\n"
        "- amount_mentioned: float sem R$ se mencionado, null caso contrário"
    ),
}


async def _parse_incoming_reply_logic(
    message_text: str,
    context_type: str = "rfq",
    reference_id: str | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Parseia uma mensagem de texto livre recebida de fornecedor ou cliente,
    extraindo dados estruturados conforme o contexto.

    Para context_type="rfq" com reference_id de rfq_requests, atualiza
    automaticamente o registro com os dados parseados (via parse_supplier_reply_core).
    Para outros context_types, retorna apenas o JSON estruturado.

    Args:
        message_text:  Texto livre recebido (WhatsApp, email, formulário, etc.)
        context_type:  Tipo de contexto: "rfq" | "nps" | "payment" (padrão: "rfq")
        reference_id:  UUID de referência (rfq_id para context_type="rfq")
    """
    import json as _json

    context_type = (context_type or "rfq").strip().lower()

    if context_type not in _PARSE_PROMPTS:
        raise ToolError(
            f"context_type='{context_type}' inválido. "
            "Valores aceitos: 'rfq', 'nps', 'payment'."
        )

    if not message_text or not message_text.strip():
        raise ToolError("message_text não pode ser vazio.")

    # Para RFQ com reference_id: delegar ao core existente (atualiza DB)
    if context_type == "rfq" and reference_id:
        if not client_id:
            raise ToolError("client_id não disponível — autenticação necessária.")
        from tool_pool_api.server.tool_modules.rfq_whatsapp_module import (
            parse_supplier_reply_core,
        )
        return await parse_supplier_reply_core(
            client_id=client_id,
            rfq_id=reference_id,
            reply_text=message_text,
        )

    # Parsing genérico sem persistência (NPS, payment, RFQ sem reference_id)
    raw = ""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from blu_llm_service import get_model
        from blu_llm_service.client import ModelTier

        system_prompt = _PARSE_PROMPTS[context_type]
        model = get_model(
            tier=ModelTier.FAST,
            tags=["communication", f"parse-{context_type}"],
        )

        response = await model.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message_text),
        ])
        raw = (response.content or "").strip()

        # Extrair JSON de markdown se necessário
        json_str = raw
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        parsed = _json.loads(json_str)

        logger.info(
            f"[Communication] Parsed {context_type} reply"
            + (f" ref={reference_id}" if reference_id else "")
        )

        return {
            "context_type": context_type,
            "reference_id": reference_id,
            "parsed_data": parsed,
            "status": "ok",
        }

    except _json.JSONDecodeError as e:
        logger.error(f"[Communication] JSON parse failed for {context_type}: {e}")
        return {
            "context_type": context_type,
            "reference_id": reference_id,
            "parsed_data": None,
            "status": "parse_error",
            "message": "Não foi possível extrair dados estruturados. Verifique o texto.",
            "raw_output": raw[:500],
        }
    except Exception as e:
        logger.exception(f"[Communication] Unexpected error parsing {context_type}: {e}")
        raise ToolError(f"Erro ao processar mensagem: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Communication (v3 — D5)."""

    # -------------------------------------------------------------------------
    # send_message — CRM / comercial
    # -------------------------------------------------------------------------
    mcp.tool(
        name="send_message",
        description=(
            "Envia ou rascunha mensagem de resposta para um contato do cliente (WhatsApp/canal).\n\n"
            "action='draft' (DEFAULT): gera rascunho de resposta usando IA baseado no histórico "
            "do contato. Requer contact_id. Use hint para orientar o tom ou conteúdo.\n"
            "action='send': promove rascunho existente para envio (ou fila de aprovação conforme "
            "política do cliente). Requer message_id. Use edited_body para ajustar o texto antes "
            "de enviar.\n\n"
            "Fluxo típico: send_message(contact_id=..., action='draft') → revisar → "
            "send_message(message_id=..., action='send')."
        ),
    )(mcp_inject_client_id(get_context_service)(_send_message_logic))

    # -------------------------------------------------------------------------
    # send_rfq_via_channel — compras
    # -------------------------------------------------------------------------
    mcp.tool(
        name="send_rfq_via_channel",
        description=(
            "Envia uma cotação (RFQ) para um fornecedor pelo canal especificado.\n\n"
            "channel='whatsapp' (DEFAULT): envia via WhatsApp usando o telefone cadastrado "
            "no supplier_roster. Gera mensagem automaticamente com itens e prazo, ou use "
            "message_template para personalizar.\n\n"
            "Requer rfq_id de uma cotação já criada (status='sent' ou 'pending'). "
            "Use as tools de compras (rfq_dispatch) para criar a cotação antes."
        ),
    )(mcp_inject_client_id(get_context_service)(_send_rfq_via_channel_logic))

    # -------------------------------------------------------------------------
    # parse_incoming_reply — parsing genérico
    # -------------------------------------------------------------------------
    mcp.tool(
        name="parse_incoming_reply",
        description=(
            "Parseia uma mensagem de texto livre recebida e extrai dados estruturados "
            "conforme o contexto.\n\n"
            "context_type='rfq' (DEFAULT): extrai preços, prazo e condições de resposta de "
            "fornecedor. Com reference_id=rfq_id, atualiza automaticamente o registro da cotação.\n"
            "context_type='nps': extrai score, sentimento e tópicos de pesquisa de satisfação.\n"
            "context_type='payment': extrai intenção de pagamento, data prometida e valor.\n\n"
            "Retorna parsed_data como JSON estruturado + status (ok/parse_error)."
        ),
    )(mcp_inject_client_id(get_context_service)(_parse_incoming_reply_logic))

    registered = ["send_message", "send_rfq_via_channel", "parse_incoming_reply"]
    logger.info(f"[Communication Module] Tools registered (v3, D5): {registered}")
    return registered
