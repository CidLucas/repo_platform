"""
Seed script para popular o banco de dados com clientes de teste.
Cada cliente representa uma persona de negocio com configuracoes especificas.
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine, select

from vizu_models import SEED_CLIENTS, ClienteVizu

# Configuracao de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_LOCAL_DATABASE(db_url: str):
    """
    Função principal de Seed.
    É chamada automaticamente pelo comando 'vizu-db LOCAL_DATABASE'.
    """
    logger.info(f"🌱 Iniciando Seed no banco: {db_url.split('@')[-1]}")

    # Cria a engine de conexão
    engine = create_engine(db_url)

    with Session(engine) as session:
        count_inserted = 0
        count_skipped = 0

        for client_data in SEED_CLIENTS:
            nome = client_data["nome_empresa"]

            # 1. Verifica se o cliente já existe para evitar duplicatas
            statement = select(ClienteVizu).where(ClienteVizu.nome_empresa == nome)
            existing_client = session.exec(statement).first()

            if existing_client:
                logger.info(f"   ⚠️  Cliente '{nome}' já existe. Pulando.")
                count_skipped += 1
                continue

            # 2. Cria o Cliente
            # O SQLModel/Pydantic validará se a string corresponde a um Enum válido automaticamente
            try:
                novo_cliente = ClienteVizu(
                    nome_empresa=nome,
                    tipo_cliente=client_data["tipo_cliente"],
                    tier=client_data["tier"],
                    id=uuid.uuid4(),
                    api_key=str(uuid.uuid4()),
                )
                session.add(novo_cliente)

                # Flush para gerar o ID do cliente e usarmos na config
                session.flush()

                # 3. Popula os campos de configuração diretamente no Cliente (merged model)
                config_data = client_data.get("config", {})
                novo_cliente.prompt_base = config_data.get(
                    "prompt_base", "Você é um assistente útil."
                )
                novo_cliente.horario_funcionamento = config_data.get(
                    "horario_funcionamento"
                )
                novo_cliente.ferramenta_rag_habilitada = config_data.get(
                    "ferramenta_rag_habilitada", False
                )
                novo_cliente.ferramenta_sql_habilitada = config_data.get(
                    "ferramenta_sql_habilitada", False
                )
                novo_cliente.ferramenta_agendamento_habilitada = config_data.get(
                    "ferramenta_agendamento_habilitada", False
                )
                novo_cliente.collection_rag = config_data.get("collection_rag")
                session.add(novo_cliente)

                count_inserted += 1
                logger.info(f"   ✅ Cliente '{nome}' preparado para inserção.")

            except Exception as e:
                logger.error(f"   ❌ Erro ao preparar cliente '{nome}': {e}")
                session.rollback()
                continue

        # Commit final da transação
        try:
            session.commit()
            logger.info("=" * 40)
            logger.info("🎉 Seed concluído!")
            logger.info(f"   Novos registros: {count_inserted}")
            logger.info(f"   Existentes (pulados): {count_skipped}")
            logger.info("=" * 40)
        except IntegrityError as e:
            session.rollback()
            logger.error(f"❌ Erro de integridade ao salvar LOCAL_DATABASE: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erro inesperado no commit: {e}")
