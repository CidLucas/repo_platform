import uuid
from typing import Any

from vizu_models.credencial_servico_externo import CredencialServicoExternoBase

from .cliente_vizu import ClienteVizuBase


class VizuClientContext(ClienteVizuBase):
    """
    Modelo Pydantic que agrega todas as informações de contexto necessárias
    para a operação do agente.

    PHASE 1: Dynamic Tool Allocation
    - enabled_tools: Lista dinâmica de ferramentas habilitadas (substitui 3 booleans)
    - tier: Tier do cliente determina acesso baseline
    """

    # Informações de Identificação do Cliente
    id: uuid.UUID
    api_key: str
    nome_empresa: str

    # PHASE 1: Dynamic Tool Allocation - New enabled_tools list
    enabled_tools: list[str] = []

    # Configurações de Negócio para o Agente
    prompt_base: str | None
    horario_funcionamento: dict[str, Any] | None

    # Legacy boolean flags (deprecated, kept for backward compatibility)
    ferramenta_rag_habilitada: bool = False
    ferramenta_sql_habilitada: bool = False
    collection_rag: str | None

    # Lista de credenciais já decifradas
    # Usamos o modelo Pydantic 'CredencialServicoExternoBase' para a tipagem
    credenciais: list[CredencialServicoExternoBase] = []

    def get_enabled_tools_list(self) -> list[str]:
        """
        Returns enabled tools list, computing from legacy booleans if needed.

        This helper ensures backward compatibility during migration:
        - If enabled_tools is populated, use it
        - Otherwise, compute from legacy boolean flags
        """
        if self.enabled_tools:
            return self.enabled_tools

        # Fallback: compute from legacy booleans
        tools = []
        if self.ferramenta_rag_habilitada:
            tools.append("executar_rag_cliente")
        if self.ferramenta_sql_habilitada:
            tools.append("executar_sql_agent")
        return tools
