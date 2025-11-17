from .cliente_vizu import ClienteVizuBase, ClienteVizuCreate, ClienteVizuInDB,ClienteVizuRead, VizuClientContext
from .configuracao import ConfiguracaoNegocioBase, ConfiguracaoNegocioCreate, ConfiguracaoNegocioInDB
from .cliente_final import ClienteFinalBase, ClienteFinalCreate, ClienteFinalInDB
from .conversa import ConversaBase, ConversaCreate, ConversaInDB, MensagemBase, MensagemCreate, MensagemInDB

# Adicionar as novas importações
from .fonte_de_dados import FonteDeDadosBase, FonteDeDadosCreate, FonteDeDadosInDB, TipoFonte, StatusIndexacao
from .credencial_servico_externo import CredencialServicoExternoBase, CredencialServicoExternoCreate, CredencialServicoExternoInDB
from .evaluation import ( EvaluationRunBase,
EvaluationRunRead,
    TestResultBase,
    TestResultRead,
)

__all__ = [
    "ClienteVizuBase", "ClienteVizuCreate",
    "ClienteVizuInDB",
    "ConfiguracaoNegocioBase", "ConfiguracaoNegocioCreate",
    "ConfiguracaoNegocioInDB",
    "ClienteFinalBase", "ClienteFinalCreate", "ClienteFinalInDB",
    "ConversaBase", "ConversaCreate", "ConversaInDB",
    "MensagemBase", "MensagemCreate", "MensagemInDB",
    "FonteDeDadosBase", "FonteDeDadosCreate", "FonteDeDadosInDB", "TipoFonte", "StatusIndexacao",
    "CredencialServicoExternoBase", "CredencialServicoExternoCreate", "CredencialServicoExternoInDB",
    "EvaluationRunBase",
    "EvaluationRunRead",
    "TestResultBase",
    "TestResultRead",
    "VizuClientContext",
    "ClienteVizuRead"
]

