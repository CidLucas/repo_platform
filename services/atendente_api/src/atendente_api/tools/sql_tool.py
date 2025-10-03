# src/atendente_api/tools/sql_tool.py

from typing import Dict
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Nossos módulos e modelos Pydantic
from atendente_api.core.schemas import VizuClientContext
from vizu_shared_models.credencial_servico_externo import CredencialServicoExternoBase


def build_db_url_from_credentials(credentials: Dict[str, str]) -> str:
    """
    Constrói uma URL de conexão de banco de dados no formato SQLAlchemy
    a partir de um dicionário de credenciais.
    Exemplo: postgresql://user:password@host:port/dbname
    """
    dialect = credentials.get("dialect", "postgresql")
    user = credentials.get("user")
    password = credentials.get("password")
    host = credentials.get("host")
    port = credentials.get("port")
    dbname = credentials.get("dbname")

    if not all([user, password, host, port, dbname]):
        raise ValueError("Credenciais de banco de dados incompletas.")

    return f"{dialect}://{user}:{password}@{host}:{port}/{dbname}"


def get_sql_database_engine_for_client(context: VizuClientContext) -> Engine:
    """
    Cria e retorna uma Engine SQLAlchemy para o banco de dados do cliente.
    Esta função agora usa create_engine diretamente, que é a abordagem correta
    para se conectar a bancos de dados externos e dinâmicos.
    """
    # 1. Encontra as credenciais específicas para o banco de dados
    db_creds_schema: CredencialServicoExternoBase | None = next(
        (c for c in context.credenciais if c.nome_servico == 'database_cliente_principal'),
        None
    )

    if not db_creds_schema or not db_creds_schema.credenciais:
        raise ValueError(f"Credenciais de DB não encontradas para o cliente {context.nome_empresa}")

    # 2. Constrói a URL e cria a engine usando SQLAlchemy
    db_url = build_db_url_from_credentials(db_creds_schema.credenciais)

    # pool_pre_ping=True é uma boa prática para evitar erros em conexões inativas
    return create_engine(db_url, pool_pre_ping=True)


def create_sql_toolkit(engine: Engine) -> SQLDatabaseToolkit:
    """
    Cria o SQLDatabaseToolkit a partir de uma engine de banco de dados.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    return SQLDatabaseToolkit(db=engine, llm=llm)