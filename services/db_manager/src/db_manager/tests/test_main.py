# services/db_manager/tests/test_main.py (VERSÃO FINAL E CORRIGIDA)
import pytest
from unittest.mock import patch, MagicMock
from db_manager import main as db_manager_main

# --- Testes de Sucesso ---

@patch("db_manager.main.create_engine")
@patch.dict("os.environ", {"DATABASE_URL": "postgresql:///test_db"})
def test_create_database_success(mock_create_engine):
    """Testa o caminho feliz de create_database em total isolamento."""
    # Configuração do Mock
    mock_connection = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    mock_create_engine.return_value = mock_engine
    mock_connection.execute.return_value.scalar.return_value = None

    # Execução e verificação: esperamos que NENHUMA exceção seja levantada
    try:
        db_manager_main.create_database("analytics_db")
    except SystemExit:
        pytest.fail("A função create_database levantou SystemExit inesperadamente no teste de sucesso.")

    # Asserção: verificamos se as chamadas corretas foram feitas
    mock_create_engine.assert_called_with("postgresql:///postgres", isolation_level="AUTOCOMMIT")

# --- Testes de Falha (Isolados) ---

def test_create_database_fails_on_invalid_name():
    """Testa se a função sai corretamente com um nome de banco inválido."""
    with pytest.raises(SystemExit) as excinfo:
        db_manager_main.create_database("db;-- DROP TABLES;")
    # Verificamos se o código de saída é 1
    assert excinfo.value.code == 1

@patch.dict("os.environ", {}, clear=True)
def test_create_database_fails_on_missing_env_var():
    """Testa se a função sai corretamente quando DATABASE_URL não está definida."""
    with pytest.raises(SystemExit) as excinfo:
        db_manager_main.create_database("valid_db_name")
    assert excinfo.value.code == 1

@patch("db_manager.main.create_engine", side_effect=Exception("Connection refused"))
@patch.dict("os.environ", {"DATABASE_URL": "postgresql:///test_db"})
def test_create_database_fails_on_db_exception(mock_create_engine):
    """Testa se a função sai corretamente em caso de erro de conexão."""
    with pytest.raises(SystemExit) as excinfo:
        db_manager_main.create_database("valid_db_name")
    assert excinfo.value.code == 1