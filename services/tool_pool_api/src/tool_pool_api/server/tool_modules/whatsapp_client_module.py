# tool_pool_api/server/tool_modules/whatsapp_client_module.py
"""
WhatsApp client messaging tools (customer/contact communication).

Este módulo é separado do rfq_whatsapp_module (fluxo de fornecedores/RFQ).
Use estas tools para comunicação com clientes e contatos em geral.
"""

import asyncio
import logging
import os

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from twilio.base.exceptions import TwilioRestException

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from blu_twilio_client.client import TwilioClient
from blu_twilio_client.config import TwilioSettings
from tool_pool_api.server.dependencies import get_context_service

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)


def _get_twilio_client() -> TwilioClient:
    """Build Twilio client with clear validation errors for env configuration."""
    try:
        settings = TwilioSettings()
    except ValidationError as e:
        raise ToolError(
            "Configuração Twilio incompleta. Defina TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN e TWILIO_WHATSAPP_FROM."
        ) from e

    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")
    if not settings.default_from_number and whatsapp_from:
        settings = settings.model_copy(update={"default_from_number": whatsapp_from})

    if not settings.default_from_number:
        raise ToolError(
            "Número remetente WhatsApp não configurado. Defina TWILIO_WHATSAPP_FROM "
            "(ou TWILIO_DEFAULT_FROM_NUMBER)."
        )

    try:
        return TwilioClient(settings)
    except Exception as e:
        raise ToolError(f"Erro ao inicializar cliente Twilio: {e}") from e


async def _whatsapp_enviar_mensagem_logic(
    ctx: Context,
    telefone: str,
    mensagem: str,
    nome_destinatario: str | None = None,
    client_id: str | None = None,
) -> dict:
    """Envia uma mensagem WhatsApp para um cliente/contato."""
    _ = client_id or ctx.request_context.lifespan_context.get("client_id")

    if len(mensagem) > 1600:
        raise ToolError("A mensagem excede o limite de 1600 caracteres.")

    twilio = _get_twilio_client()

    try:
        message_sid = await asyncio.to_thread(
            twilio.send_whatsapp,
            f"whatsapp:{telefone}",
            mensagem,
        )

        if not message_sid:
            raise ToolError(
                "Falha ao enviar mensagem WhatsApp. Verifique configuração do remetente "
                "e validade do telefone de destino."
            )

        return {
            "status": "ok",
            "message_sid": message_sid,
            "destinatario": nome_destinatario or telefone,
        }
    except TwilioRestException as e:
        raise ToolError(f"Erro Twilio ao enviar WhatsApp: {e.msg}") from e
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Erro ao enviar mensagem WhatsApp: {e}") from e


async def _whatsapp_enviar_lote_logic(
    ctx: Context,
    destinatarios: list[dict],
    mensagem: str,
    personalizar: bool = True,
    client_id: str | None = None,
) -> dict:
    """Envia a mesma mensagem para múltiplos destinatários (máx. 20)."""
    _ = client_id or ctx.request_context.lifespan_context.get("client_id")

    if len(destinatarios) > 20:
        raise ToolError("Máximo de 20 destinatários por chamada.")

    twilio = _get_twilio_client()

    resultados: list[dict] = []
    enviados = 0

    for destinatario in destinatarios:
        telefone = (destinatario or {}).get("telefone")
        nome = (destinatario or {}).get("nome")

        if not telefone:
            resultados.append(
                {
                    "telefone": telefone,
                    "nome": nome,
                    "status": "error",
                    "error": "Destinatário sem telefone.",
                }
            )
            continue

        mensagem_final = mensagem
        if personalizar and nome:
            mensagem_final = mensagem.replace("{{nome}}", str(nome))

        try:
            message_sid = await asyncio.to_thread(
                twilio.send_whatsapp,
                f"whatsapp:{telefone}",
                mensagem_final,
            )

            if not message_sid:
                resultados.append(
                    {
                        "telefone": telefone,
                        "nome": nome,
                        "status": "error",
                        "error": "Falha no envio (SID não retornado).",
                    }
                )
                continue

            enviados += 1
            resultados.append(
                {
                    "telefone": telefone,
                    "nome": nome,
                    "status": "ok",
                    "message_sid": message_sid,
                }
            )

        except TwilioRestException as e:
            resultados.append(
                {
                    "telefone": telefone,
                    "nome": nome,
                    "status": "error",
                    "error": f"Erro Twilio: {e.msg}",
                }
            )
        except Exception as e:
            resultados.append(
                {
                    "telefone": telefone,
                    "nome": nome,
                    "status": "error",
                    "error": str(e),
                }
            )

    falhas = len(resultados) - enviados
    return {
        "total": len(destinatarios),
        "enviados": enviados,
        "falhas": falhas,
        "resultados": resultados,
    }


async def _whatsapp_status_mensagem_logic(
    ctx: Context,
    message_sid: str,
    client_id: str | None = None,
) -> dict:
    """Consulta o status de entrega de uma mensagem WhatsApp pelo SID."""
    _ = client_id or ctx.request_context.lifespan_context.get("client_id")
    twilio = _get_twilio_client()

    try:
        message = await asyncio.to_thread(
            lambda: twilio.client.messages(message_sid).fetch()
        )
        return {
            "message_sid": message.sid,
            "status": message.status,
            "to": message.to,
            "date_sent": str(message.date_sent),
            "error_code": message.error_code,
        }
    except TwilioRestException as e:
        raise ToolError(f"Erro Twilio ao consultar status da mensagem: {e.msg}") from e
    except Exception as e:
        raise ToolError(f"Erro ao consultar status da mensagem: {e}") from e


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register WhatsApp client messaging tools."""
    _inject = mcp_inject_client_id(get_context_service)

    mcp.tool(
        name="whatsapp_enviar_mensagem",
        description=(
            "Envia uma mensagem WhatsApp para um cliente ou contato. "
            "Use para comunicação com clientes (não fornecedores — "
            "para fornecedores use dispatch_rfq_whatsapp)."
        ),
    )(_inject(_whatsapp_enviar_mensagem_logic))

    mcp.tool(
        name="whatsapp_enviar_lote",
        description=(
            "Envia a mesma mensagem WhatsApp para múltiplos destinatários. "
            "Útil para comunicados, cobranças e confirmações em lote. "
            "Máximo 20 destinatários por chamada."
        ),
    )(_inject(_whatsapp_enviar_lote_logic))

    mcp.tool(
        name="whatsapp_status_mensagem",
        description=(
            "Consulta o status de entrega de uma mensagem WhatsApp pelo message_sid."
        ),
    )(_inject(_whatsapp_status_mensagem_logic))

    logger.info(
        "[WhatsApp Client Module] Tools registradas: whatsapp_enviar_mensagem, "
        "whatsapp_enviar_lote, whatsapp_status_mensagem"
    )

    return [
        "whatsapp_enviar_mensagem",
        "whatsapp_enviar_lote",
        "whatsapp_status_mensagem",
    ]
