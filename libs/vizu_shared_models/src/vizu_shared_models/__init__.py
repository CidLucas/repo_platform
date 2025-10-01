from .cliente_vizu import ClienteVizuBase, ClienteVizuCreate, ClienteVizuInDB
from .configuracao import ConfiguracaoNegocioBase, ConfiguracaoNegocioCreate, ConfiguracaoNegocioInDB
from .cliente_final import ClienteFinalBase, ClienteFinalCreate, ClienteFinalInDB
from .conversa import ConversaBase, ConversaCreate, ConversaInDB, MensagemBase, MensagemCreate, MensagemInDB

# Adicionar as novas importações
from .fonte_de_dados import FonteDeDadosBase, FonteDeDadosCreate, FonteDeDadosInDB, TipoFonte, StatusIndexacao
from .credencial_servico_externo import CredencialServicoExternoBase, CredencialServicoExternoCreate, CredencialServicoExternoInDB

__all__ = [
    "ClienteVizuBase", "ClienteVizuCreate", "ClienteVizuInDB",
    "ConfiguracaoNegocioBase", "ConfiguracaoNegocioCreate", "ConfiguracaoNegocioInDB",
    "ClienteFinalBase", "ClienteFinalCreate", "ClienteFinalInDB",
    "ConversaBase", "ConversaCreate", "ConversaInDB",
    "MensagemBase", "MensagemCreate", "MensagemInDB",
    # Adicionar os novos nomes
    "FonteDeDadosBase", "FonteDeDadosCreate", "FonteDeDadosInDB", "TipoFonte", "StatusIndexacao",
    "CredencialServicoExternoBase", "CredencialServicoExternoCreate", "CredencialServicoExternoInDB",
]

