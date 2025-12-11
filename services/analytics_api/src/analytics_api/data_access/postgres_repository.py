# src/analytics_api/data_access/postgres_repository.py
import logging

import pandas as pd
from analytics_api.core.analytics_mapping import get_silver_table_name

# REMOVIDO: from vizu_db_connector.database import DBConnector
from sqlalchemy.orm import Session  # Importa o tipo Session

logger = logging.getLogger(__name__)

class PostgresRepository:
    """
    Camada de acesso aos dados Prata (exclusivamente do nosso Postgres).
    (Corrigido para usar Session injetada)
    """
    # ALTERADO: Recebe a Session no construtor
    def __init__(self, db_session: Session):
        self.db_session = db_session # Armazena a sessão

    def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
        """
        Busca TODOS os dados da tabela Prata do cliente e carrega em
        um DataFrame Pandas para processamento em memória.
        """
        table_name = get_silver_table_name(client_id)
        query = f"SELECT * FROM {table_name}"

        logger.info(f"Buscando dados Prata da tabela: {table_name}")

        try:
            # ALTERADO: Usa a sessão diretamente com read_sql
            # O SQLAlchemy sabe como obter a conexão a partir da sessão
            df = pd.read_sql(query, self.db_session.bind)

            logger.info(f"{len(df)} linhas carregadas da camada Prata.")
            return df

        except Exception as e:
            logger.error(f"Falha ao buscar dados da tabela Prata '{table_name}': {e}")
            raise
