import logging
from sqlalchemy.orm import Session
from vizu_db_connector.models import ClienteVizu
from vizu_shared_models.cliente_vizu import ClienteVizuCreate

logger = logging.getLogger(__name__)

class ClientService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> ClienteVizu | None:
        """Busca um cliente pelo email de contato."""
        return self.db.query(ClienteVizu).filter(ClienteVizu.email_contato == email).first()

    def create(self, *, cliente_create: ClienteVizuCreate) -> ClienteVizu:
        """Cria um novo objeto ClienteVizu no banco de dados."""

        db_obj = ClienteVizu(
            nome_empresa=cliente_create.nome_empresa,
            email_contato=cliente_create.email_contato,
            telefone_contato=cliente_create.telefone_contato,
            setor=cliente_create.setor
        )

        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        logger.info(f"ClienteVizu '{db_obj.nome_empresa}' persistido no banco de dados.")
        return db_obj