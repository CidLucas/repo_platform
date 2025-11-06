# services/clients_api/src/clients_api/services/config_service.py
from sqlalchemy.orm import Session
from vizu_db_connector.crud import BaseCRUD
from vizu_db_connector.models.configuracao import ConfiguracaoNegocio
from vizu_shared_models.configuracao import ConfiguracaoNegocioCreate, ConfiguracaoNegocioUpdate, ConfiguracaoNegocioBase

class ConfiguracaoService(BaseCRUD[ConfiguracaoNegocioBase, ConfiguracaoNegocioCreate, ConfiguracaoNegocioUpdate]):
    def get_by_cliente(self, db_session: Session, *, cliente_vizu_id: str) -> ConfiguracaoNegocioBase | None:
        return db_session.query(self.model).filter(self.model.cliente_vizu_id == cliente_vizu_id).first()

config_service = ConfiguracaoService(ConfiguracaoNegocio)