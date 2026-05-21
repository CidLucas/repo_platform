"""Fiscal Module — NF-e / NFS-e stub

This module provides data preparation and status tools for fiscal (NF-e/NFS-e)
operations. The actual SEFAZ integration is pending partner selection.
"""

import logging
import os

from fastmcp import Context, FastMCP

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register fiscal tools with the MCP server."""

    @mcp.tool(
        name="fiscal_preparar_dados_nfe",
        description=(
            "Prepara e valida os dados necessários para emissão de NF-e ou NFS-e. "
            "Não emite — apenas organiza e valida os campos obrigatórios. "
            "Quando a integração SEFAZ estiver ativa, estes dados serão enviados "
            "automaticamente."
        ),
    )
    async def fiscal_preparar_dados_nfe(
        tipo: str,
        valor_total: float,
        descricao_servico: str,
        cnpj_tomador: str | None = None,
        cpf_tomador: str | None = None,
        municipio_prestacao: str | None = None,
        ctx: Context = None,
    ) -> dict:
        """
        Prepare and validate NF-e / NFS-e data fields.

        Args:
            tipo: 'nfe' or 'nfse'
            valor_total: Total invoice value (must be > 0)
            descricao_servico: Service description
            cnpj_tomador: CNPJ of the service taker (optional)
            cpf_tomador: CPF of the service taker (optional)
            municipio_prestacao: Municipality where service was rendered (required for nfse)
        """
        tipo_lower = tipo.lower().strip()
        if tipo_lower not in ("nfe", "nfse"):
            raise ValueError("O campo 'tipo' deve ser 'nfe' ou 'nfse'.")

        if valor_total <= 0:
            raise ValueError("O campo 'valor_total' deve ser maior que zero.")

        if tipo_lower == "nfse" and not municipio_prestacao:
            raise ValueError(
                "Para NFS-e, o campo 'municipio_prestacao' é obrigatório."
            )

        return {
            "status": "preparado",
            "tipo": tipo_lower,
            "dados": {
                "tipo": tipo_lower,
                "valor_total": valor_total,
                "descricao_servico": descricao_servico,
                "cnpj_tomador": cnpj_tomador,
                "cpf_tomador": cpf_tomador,
                "municipio_prestacao": municipio_prestacao,
            },
            "integracao_ativa": False,
            "mensagem": (
                "Dados validados. A emissão automática estará disponível em breve "
                "com a integração SEFAZ. Por enquanto, use estes dados para emissão "
                "manual no seu sistema fiscal."
            ),
        }

    @mcp.tool(
        name="fiscal_status_integracao",
        description=(
            "Informa o status atual da integração fiscal (NF-e/NFS-e). "
            "Use quando o usuário perguntar sobre emissão de notas."
        ),
    )
    async def fiscal_status_integracao(ctx: Context = None) -> dict:
        """Return current NF-e/NFS-e integration status."""
        api_key = os.environ.get("FISCAL_PARTNER_API_KEY")
        partner = os.environ.get("FISCAL_PARTNER_NAME", "não configurado")
        ativo = bool(api_key)
        return {
            "integracao_ativa": ativo,
            "parceiro": partner,
            "status": "ativo" if ativo else "pendente",
            "mensagem": (
                "Integração ativa."
                if ativo
                else (
                    "Integração NF-e/NFS-e em implementação. Parceiro SEFAZ a ser "
                    "configurado. Previsão: 2-3 semanas após escolha do parceiro "
                    "(FocusNFe, PlugNotas ou similar)."
                )
            ),
        }

    logger.info(
        "[Fiscal Module] Tools registered: fiscal_preparar_dados_nfe, "
        "fiscal_status_integracao"
    )
    return ["fiscal_preparar_dados_nfe", "fiscal_status_integracao"]
