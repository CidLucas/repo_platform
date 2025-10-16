# services/db_manager/src/db_manager/main.py (VERSÃO FINAL E ROBUSTA)
import os
import re
import sys
import argparse
from sqlalchemy import create_engine, text

# --- CORREÇÃO DEFINITIVA ---
# Importamos a função principal do Alembic diretamente.
from alembic.config import main as alembic_main

def run_migrations():
    """Executa as migrações do Alembic de forma programática."""
    print("INFO: Iniciando migrações do banco de dados...")
    try:
        # Chamamos a função principal do Alembic, passando os argumentos
        # como uma lista. Isso é mais seguro e robusto que o subprocess.
        alembic_main(["upgrade", "head"])
        print("SUCESSO: Migrações concluídas.")
    except Exception as e:
        # Se o Alembic encontrar um erro, ele geralmente levanta uma exceção.
        # Nós a capturamos para fornecer uma mensagem de erro clara.
        print(f"ERRO: Falha ao executar migrações do Alembic: {e}")
        raise SystemExit(1)

def create_database(db_name: str):
    """Cria um novo banco de dados. Lança SystemExit(1) em caso de falha."""
    if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
        print(f"ERRO: Nome de banco inválido: '{db_name}'.")
        raise SystemExit(1)
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERRO: Variável de ambiente DATABASE_URL não definida.")
        raise SystemExit(1)
    try:
        admin_db_url = db_url.rsplit('/', 1)[0] + '/postgres'
        engine = create_engine(admin_db_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as connection:
            check_db_query = text("SELECT 1 FROM pg_database WHERE datname = :db_name")
            if connection.execute(check_db_query, {"db_name": db_name}).scalar():
                print(f"AVISO: Banco de dados '{db_name}' já existe.")
            else:
                connection.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"SUCESSO: Banco de dados '{db_name}' criado.")
    except Exception as e:
        print(f"ERRO: Exceção ao criar banco: {e}")
        raise SystemExit(1)

def main():
    """Ponto de entrada que lida com a CLI e com a saída do programa."""
    parser = argparse.ArgumentParser(description="Ferramenta de Gerenciamento de Banco de Dados Vizu.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Executa as migrações.")
    parser_create_db = subparsers.add_parser("create-db", help="Cria um novo banco de dados.")
    parser_create_db.add_argument("db_name", type=str, help="Nome do banco a ser criado.")

    try:
        args = parser.parse_args()
        if args.command == "migrate":
            run_migrations()
        elif args.command == "create-db":
            create_database(args.db_name)
    except SystemExit as e:
        # Se uma das nossas funções levantar SystemExit, nós saímos com o código de erro.
        sys.exit(e.code)

if __name__ == "__main__":
    main()