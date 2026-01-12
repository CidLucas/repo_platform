import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# IMPORTAÇÕES CHAVE PARA O ORM METADATA
# Importa a Base que contém o Metadata
# Importa os Models que criam as tabelas (garante que todos os models sejam registrados na Base.metadata)
# Importa o modelo ORM do próprio DB Connector (agora vindo do pacote compartilhado)
from vizu_models import ClienteVizu, CredencialServicoExterno

# Importa os modelos compartilhados para tipagem (Agnosticismo)
from vizu_models.cliente_vizu import TierCliente, TipoCliente

# Usa uma variável de ambiente para o DB de teste, com um fallback
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/vizu_db_test"
)

# --- FUNÇÕES DE AJUDA PARA TESTES (TESTABILITY) ---


def create_vizu_client_in_db(
    db_session: Session,
    nome_empresa: str = "Cliente de Teste Vizu",
    tipo_cliente: TipoCliente = TipoCliente.EXTERNO,
    tier: TierCliente = TierCliente.SME,
    client_id: uuid.UUID | None = None,
) -> ClienteVizu:
    """
    Helper centralizado para criar e persistir um registro ClienteVizu para testes.
    Promove a Modularização e Reutilização em todos os testes de integração.

    Retorna: O objeto ClienteVizu persistido.
    """
    if client_id is None:
        client_id = uuid.uuid4()

    db_cliente_vizu = ClienteVizu(
        id=client_id,
        nome_empresa=nome_empresa,
        tipo_cliente=tipo_cliente,
        tier=tier,
    )
    db_session.add(db_cliente_vizu)
    db_session.commit()
    db_session.refresh(db_cliente_vizu)

    return db_cliente_vizu


def create_external_credential_ref(
    db_session: Session,
    client_id: uuid.UUID,
    secret_manager_id: str = "gcp-secret-mock-123",
    nome_servico: str = "BIGQUERY",
) -> CredencialServicoExterno:
    """
    Helper centralizado para criar uma referência de credencial.
    """
    db_cred = CredencialServicoExterno(
        client_id=client_id,
        nome_servico=nome_servico,
        credenciais_cifradas=secret_manager_id,
    )
    db_session.add(db_cred)
    db_session.commit()
    db_session.refresh(db_cred)
    return db_cred


# --- FIXTURES REUTILIZÁVEIS ---


@pytest.fixture
def vizu_client_fixture(db_session: Session) -> ClienteVizu:
    """Fixture para fornecer um ClienteVizu recém-criado, reusável em qualquer teste."""
    return create_vizu_client_in_db(db_session=db_session)


@pytest.fixture(scope="session")
def engine():
    """Cria uma única engine para toda a sessão de testes."""
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def create_tables(engine):
    """
    Fixture principal de setup: cria todas as tabelas no início dos testes
    e as remove no final. `autouse=True` garante que ela sempre execute.
    """
    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    yield
    models.Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, create_tables) -> Session:
    """
    Fornece uma sessão de banco de dados limpa para cada teste,
    usando um padrão de transação com rollback para isolar os testes.
    """
    connection = engine.connect()
    # Inicia uma transação "externa"
    transaction = connection.begin()
    # Cria uma sessão ligada a essa transação
    session = sessionmaker(bind=connection)()

    yield session

    # Ao final do teste, fecha a sessão e desfaz a transação.
    # Isso garante que cada teste comece com o banco de dados limpo.
    session.close()
    transaction.rollback()
    connection.close()
