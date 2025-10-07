import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# --- 1. Configuração da Conexão ---
# A URL de conexão com o banco de dados é lida de uma variável de ambiente.
# Isso está alinhado com o nosso princípio de Agnosticismo: a aplicação não
# deve ter credenciais "hardcoded". Fornecemos um valor padrão para facilitar
# o desenvolvimento local com Docker.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/vizu_db")


# --- 2. Criação da Engine ---
# A 'engine' é o ponto central de comunicação com o banco de dados.
# Ela gerencia um "pool" de conexões para reutilizá-las de forma eficiente.
# O 'pool_pre_ping=True' verifica se a conexão ainda está ativa antes de usá-la,
# evitando erros em conexões de longa duração.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


# --- 3. Criação da Fábrica de Sessões ---
# O 'SessionLocal' é uma "fábrica" que, quando chamada, cria uma nova
# instância de Sessão do SQLAlchemy. Cada sessão é uma unidade de trabalho
# isolada para interagir com o banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- 4. Função de Dependência para FastAPI ---
# Esta função é a forma como nossos serviços (APIs) obterão uma sessão de DB.
# Ela foi projetada para ser usada como uma dependência no FastAPI.
def get_db() -> Generator[Session, None, None]:
    """
    Gerencia o ciclo de vida de uma sessão do banco de dados.
    - Cria uma sessão para uma requisição.
    - Disponibiliza a sessão (yield).
    - Garante que a sessão seja fechada ao final, mesmo se ocorrerem erros.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()