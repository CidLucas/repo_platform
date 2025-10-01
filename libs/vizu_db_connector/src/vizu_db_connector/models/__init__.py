# Importar a Base primeiro é uma boa prática.
from .base import Base

# Agora, importe todas as suas classes de modelo.
# Isso garante que todas elas sejam registradas na metadata da Base
# assim que o pacote 'models' for importado em qualquer lugar.
from .cliente_vizu import ClienteVizu
from .configuracao import ConfiguracaoNegocio
from .cliente_final import ClienteFinal
from .conversa import Conversa, Mensagem

__all__ = [
    "Base",
    "ClienteVizu",
    "ConfiguracaoNegocio",
    "ClienteFinal",
    "Conversa",
    "Mensagem",
]