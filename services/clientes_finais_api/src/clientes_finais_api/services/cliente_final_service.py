import logging
import uuid
from typing import List

from sqlalchemy.orm import Session

from vizu_models import ClienteFinal, ClienteFinalCreate

logger = logging.getLogger(__name__)


class ClienteFinalService:
    """
    Serviço para encapsular a lógica de negócio de Clientes Finais.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_cliente_final(
        self, cliente_in: ClienteFinalCreate, cliente_vizu_id: uuid.UUID
    ) -> ClienteFinal:
        """
        Cria um novo registro de ClienteFinal no banco de dados.
        """
        logger.info(
            f"Criando cliente final no banco para o Cliente Vizu: {cliente_vizu_id}"
        )
        cliente_data = cliente_in.model_dump()
        db_cliente = ClienteFinal(**cliente_data, cliente_vizu_id=cliente_vizu_id)

        self.db.add(db_cliente)
        self.db.flush()  # Envia para o DB, mas não commita. Pega o ID gerado.
        self.db.refresh(db_cliente)  # Atualiza o objeto com os dados do DB (como o ID).

        logger.info(f"Cliente final criado com sucesso com ID: {db_cliente.id}")
        return db_cliente

    def list_clientes_finais(self, cliente_vizu_id: uuid.UUID) -> List[ClienteFinal]:
        """
        Retorna todos os clientes finais de um Cliente Vizu específico.
        """
        logger.info(f"Buscando clientes finais para o Cliente Vizu: {cliente_vizu_id}")
        return (
            self.db.query(ClienteFinal)
            .filter(ClienteFinal.cliente_vizu_id == cliente_vizu_id)
            .all()
        )
