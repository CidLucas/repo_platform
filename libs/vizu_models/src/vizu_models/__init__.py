# vizu_models/__init__.py (Versão Corrigida para Exportação)

from .cliente_vizu import ClienteVizu, ClienteVizuCreate, ClienteVizuRead, ClienteVizuReadWithRelations, ClienteVizuUpdate
from .configuracao_negocio import ConfiguracaoNegocio, ConfiguracaoNegocioBase, ConfiguracaoNegocioCreate, ConfiguracaoNegocioRead, ConfiguracaoNegocioUpdate
from .credencial_servico_externo import CredencialServicoExterno, CredencialServicoExternoBase, CredencialServicoExternoCreate, CredencialServicoExternoInDB
from .fonte_de_dados import FonteDeDados
from .cliente_final import ClienteFinal, ClienteFinalCreate, ClienteFinalRead, ClienteFinalUpdate
from .conversa import ConversaBase, MensagemBase, Remetente
from .vizu_client_context import VizuClientContext
from sqlmodel import SQLModel

class Base(SQLModel):
    """
    Classe base que herda de SQLModel. Usada pelo Alembic como target_metadata.
    """
    pass

__all__ = [
    'Base',
    'ClienteVizu',
    'ClienteVizuCreate',
    'ClienteVizuRead',
    'ClienteVizuReadWithRelations',
    'ClienteVizuUpdate', # Deve ser a classe única ClienteVizuUpdate

    'ConfiguracaoNegocio',
    'ConfiguracaoNegocioBase',
    'ConfiguracaoNegocioCreate',
    'ConfiguracaoNegocioRead',
    'ConfiguracaoNegocioUpdate',

    'CredencialServicoExterno',
    'CredencialServicoExternoBase',
    'CredencialServicoExternoCreate',
    'CredencialServicoExternoInDB',

    'FonteDeDados',

    'ClienteFinal',
    'ClienteFinalCreate',
    'ClienteFinalRead',
    'ClienteFinalUpdate',

    'ConversaBase',
    'MensagemBase',
    'Remetente',
    'VizuClientContext'
]