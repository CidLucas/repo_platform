# src/data_ingestion_worker/services/db_writer_service.py

import pandas as pd
import logging
import asyncio
import os 
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine


log = logging.getLogger(__name__)

class DBWriterService:
    """
    Serviço responsável por CARREGAR (Load) os dados transformados
    no nosso Data Warehouse (Cloud SQL).
    """
    
    # [VIZU-REFACTOR] CORRIGIDO: O __init__ agora aceita 'db_url' (string)
    # e cria seu próprio Engine.
    def __init__(self, db_url: str):
        """
        Inicializa o serviço e cria o Engine do SQLAlchemy.
        """
        if not db_url:
            log.error("[DBWriterService] A DATABASE_URL (db_url) não foi fornecida.")
            raise ValueError("A DATABASE_URL (db_url) não pode ser Nula.")
            
        try:
            # Responsabilidade Única: O Writer cria sua própria conexão.
            self.engine: Engine = create_engine(db_url) 
            log.info(f"[DBWriterService] Inicializado. Engine criado para o banco: {self.engine.url.database}")
        except Exception as e:
            log.error(f"[DBWriterService] Falha ao criar o engine do SQLAlchemy: {e}")
            raise
    
    def _write_to_db_sync(self, dataframe: pd.DataFrame, table_name: str):
        """
        Função SÍNCRONA auxiliar que executa a escrita (blocking I/O).
        Esta função será chamada em uma thread separada.
        """
        try:
            log.info(f"[DBWriterService] Escrevendo chunk de {len(dataframe)} linhas na tabela '{table_name}'...")
            
            dataframe.to_sql(
                name=table_name, 
                con=self.engine, 
                if_exists="append", 
                index=False
            )
            
            log.info(f"[DBWriterService] Chunk escrito com sucesso.")
            
        except Exception as e:
            log.error(f"[DBWriterService] Falha ao escrever chunk no banco (thread): {e}")
            # Se tiver um ExecutionError, use-o aqui
            # raise ExecutionError(f"Falha na escrita do banco: {e}")
            raise

    async def load(self, dataframe: pd.DataFrame):
        """
        Método ASSÍNCRONO (contrato) chamado pelo IngestionService.
        
        Ele delega a escrita (blocking) para uma thread separada
        para não bloquear o loop de eventos principal.
        """
        
        # [REFACTOR FUTURO] Este nome de tabela ainda está hard-coded.
        # O próximo passo em nosso Agnosticismo será passar
        # o 'target_table' desde o payload do Pub/Sub até aqui.
        # Por enquanto, vamos validar o fluxo de escrita.
        target_table_name = "pm_dados_faturamento_cliente_x" # <--- Seu nome de tabela original do E2E
        
        try:
            # Executa a função síncrona _write_to_db_sync em uma thread
            await asyncio.to_thread(
                self._write_to_db_sync, 
                dataframe, 
                target_table_name
            )
        except Exception as e:
            log.error(f"Erro ao agendar a escrita no banco: {e}")
            raise

# [VIZU-REFACTOR] Adicione esta importação no final para simular o asyncio
import asyncio