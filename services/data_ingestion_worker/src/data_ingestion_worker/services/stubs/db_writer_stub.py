# src/data_ingestion_worker/services/stubs/db_writer_stub.py

import asyncio
import logging

import pandas as pd

logger = logging.getLogger(__name__)

class DBWriterServiceStub:
    """
    Stub (Mock) do DBWriterService para testes de integração (E2E_MODE=STUB).
    
    Esta classe SIMULA a escrita no banco de dados, mas apenas
    imprime os dados recebidos no log, replicando o comportamento
    do teste E2E inicial.

    Ela deve ter a mesma interface (métodos) que o DBWriterService real
    (ou seja, um método async 'load') para que o IngestionService 
    possa usá-la (Princípio do Agnosticismo).
    """
    def __init__(self):
        # O init do stub não precisa de URL de banco, é só um mock.
        logger.info("[DBWriterServiceStub] Inicializado (Modo STUB).")

    async def load(self, df: pd.DataFrame):
        """
        Simula o método 'load' do DBWriterService real.
        Este método é chamado pelo IngestionService.
        """
        chunk_size = len(df)

        # Simula os logs exatos do seu teste E2E original
        logger.info(f"[DBWriterService-STUB] Recebido chunk de {chunk_size} linhas.")
        logger.info(f"[DBWriterService-STUB] Colunas: {df.columns.tolist()}")

        # Log dos tipos de dados
        dtype_info = df.dtypes.to_string()
        logger.info(f"[DBWriterService-STUB] Tipos de dados:\n{dtype_info}")

        logger.info("[DBWriterService-STUB] Chunk 'escrito' (simulado) com sucesso.")

        # Simula um I/O não bloqueante (já que o método real é 'async')
        await asyncio.sleep(0)
