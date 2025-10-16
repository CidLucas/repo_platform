# services/clients_api/src/clients_api/services/client_service.py (VERSÃO FINAL)
from sqlalchemy.orm import Session
from vizu_db_connector.crud import BaseCRUD # <-- CORREÇÃO: Importa da biblioteca compartilhada
from vizu_shared_models.cliente_vizu import ClienteVizuCreate, ClienteVizuUpdate
from vizu_db_connector.models.cliente_vizu import ClienteVizu
from ..core.security import create_api_key

class ClienteVizuService(BaseCRUD[ClienteVizu, ClienteVizuCreate, ClienteVizuUpdate]):
    # A lógica de CRUD (get, get_multi, etc.) é herdada automaticamente.
    # Nós apenas sobrescrevemos ou adicionamos a lógica específica deste serviço.
    def create_cliente_vizu(self, db_session: Session, *, cliente_in: ClienteVizuCreate) -> ClienteVizu:
        api_key, hashed_api_key = create_api_key()
        obj_in_data = cliente_in.model_dump()
        db_obj = self.model(**obj_in_data, api_key=hashed_api_key)

        db_session.add(db_obj)
        db_session.commit()
        db_session.refresh(db_obj)

        setattr(db_obj, 'api_key', api_key)
        return db_obj

# A instância singleton é removida. O router obterá a instância via injeção de dependência.