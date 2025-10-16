# services/db_manager/tests/integration/test_db_manager_integration.py
import os
from sqlalchemy import inspect
from db_manager import main as db_manager_main

def test_run_migrations_creates_tables(test_db_engine):
    """
    Testa se a função run_migrations realmente cria as tabelas no banco de teste.
    Este é o teste de integração mais importante para o db-manager.
    """
    # Define a DATABASE_URL para que o alembic a encontre dentro do processo de teste.
    os.environ["DATABASE_URL"] = str(test_db_engine.url)

    # Executa a função de migração
    db_manager_main.run_migrations()

    # Verificação: Inspecionamos o banco de dados de teste e garantimos que as tabelas
    # definidas em vizu_db_connector/models/ foram realmente criadas.
    inspector = inspect(test_db_engine)
    tables = inspector.get_table_names()

    assert "cliente_vizu" in tables
    assert "cliente_final" in tables