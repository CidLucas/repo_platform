# services/clients_api/src/clients_api/api/dependencies.py (VERSÃO CORRIGIDA)
from vizu_db_connector.database import SessionLocal
from vizu_db_connector.models.cliente_vizu import ClienteVizu
from vizu_db_connector.models.configuracao import ConfiguracaoNegocio# <-- CORREÇÃO AQUI
from ..services.client_service import ClienteVizuService
from ..services.config_service import ConfiguracaoService

def get_db_session():
    """Fornece uma sessão de banco de dados para a requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_client_service() -> ClienteVizuService:
    """Fornece uma instância do serviço de cliente."""
    return ClienteVizuService(ClienteVizu)

def get_config_service() -> ConfiguracaoService:
    """Fornece uma instância do serviço de configuração."""
    return ConfiguracaoService(ConfiguracaoNegocio)