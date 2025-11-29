# vizu_models/safe_client_context.py
"""
SafeClientContext - Contexto seguro para exposição à LLM.

Este modelo contém APENAS os dados que são seguros para serem
expostos à LLM. Nenhuma informação sensível (API keys, IDs internos,
credenciais) deve estar aqui.

IMPORTANTE: Qualquer dado neste modelo pode potencialmente ser
incluído em prompts ou respostas da LLM.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid


class SafeClientContext(BaseModel):
    """
    Contexto do cliente seguro para uso com LLM.
    
    NÃO INCLUIR:
    - api_key
    - credenciais de serviços externos
    - IDs internos (UUIDs)
    - qualquer dado que possa ser usado para impersonação
    """
    model_config = ConfigDict(frozen=True)  # Imutável para evitar modificações acidentais
    
    # Dados públicos seguros
    nome_empresa: str
    
    # Configurações de comportamento (não sensíveis)
    prompt_base: Optional[str] = None
    horario_funcionamento: Optional[dict] = None
    
    # Flags de features (não sensíveis)
    ferramenta_rag_habilitada: bool = False
    ferramenta_sql_habilitada: bool = False
    collection_rag: Optional[str] = None


class InternalClientContext(BaseModel):
    """
    Contexto interno do cliente com dados sensíveis.
    
    Este modelo é usado APENAS para operações internas do servidor
    (autenticação, injeção de cliente_id em tools, etc.)
    
    NUNCA deve ser exposto à LLM ou incluído em prompts.
    """
    # Identificadores internos
    id: uuid.UUID
    api_key: str
    
    # Contexto seguro (pode ser extraído para a LLM)
    safe_context: SafeClientContext
    
    @classmethod
    def from_vizu_client_context(cls, ctx) -> "InternalClientContext":
        """
        Cria um InternalClientContext a partir de um VizuClientContext.
        Separa claramente os dados sensíveis dos seguros.
        """
        safe = SafeClientContext(
            nome_empresa=ctx.nome_empresa,
            prompt_base=ctx.prompt_base,
            horario_funcionamento=ctx.horario_funcionamento,
            ferramenta_rag_habilitada=ctx.ferramenta_rag_habilitada,
            ferramenta_sql_habilitada=ctx.ferramenta_sql_habilitada,
            collection_rag=ctx.collection_rag,
        )
        return cls(
            id=ctx.id,
            api_key=ctx.api_key,
            safe_context=safe,
        )

    def get_safe_context(self) -> SafeClientContext:
        """Retorna apenas o contexto seguro para uso com LLM."""
        return self.safe_context

    def get_client_id_for_tools(self) -> str:
        """Retorna o ID do cliente para injeção em tools (uso interno)."""
        return str(self.id)
