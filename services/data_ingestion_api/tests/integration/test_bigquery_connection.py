# data_ingestion_api/tests/integration/test_bigquery_connection.py

import json
import os

import pytest
from data_ingestion_api.connectors.bigquery_connector import BigQueryConnector

# CRÍTICO VIZU: Este teste só deve rodar se as credenciais reais estiverem disponíveis
pytestmark = pytest.mark.skipif(
    not os.getenv("BIGQUERY_INTEGRATION_TEST_CREDS_JSON"),
    reason="Requer a variável BIGQUERY_INTEGRATION_TEST_CREDS_JSON para rodar."
)

@pytest.fixture(scope="module")
def real_bigquery_connector():
    """
    Fixture que carrega o JSON da Service Account Key da variável de ambiente 
    e retorna uma instância real do BigQueryConnector.
    """
    # 1. Obter o JSON da Service Account Key (deve ser um JSON string)
    creds_json_string = os.getenv("BIGQUERY_INTEGRATION_TEST_CREDS_JSON")
    if not creds_json_string:
        pytest.skip("BIGQUERY_INTEGRATION_TEST_CREDS_JSON não configurado.")

    try:
        credentials_info = json.loads(creds_json_string)
    except json.JSONDecodeError:
        raise ValueError("Variável BIGQUERY_INTEGRATION_TEST_CREDS_JSON não é JSON válido.")

    # 2. A classe BigQueryConnector valida e conecta ao GCP
    connector = BigQueryConnector(credentials=credentials_info)
    return connector

@pytest.mark.asyncio # <--- CRÍTICO: Marca o teste como assíncrono
async def test_real_bigquery_connection(real_bigquery_connector):
    """
    Teste de integração: Garante que o conector pode autenticar e conectar 
    ao serviço BigQuery do GCP.
    """
    # O método real de teste de conexão executa um SELECT 1
    assert await real_bigquery_connector.validate_connection() is True # CORREÇÃO: validate_connection()

@pytest.mark.asyncio # <--- CRÍTICO: Marca o teste como assíncrono
async def test_real_bigquery_simple_query(real_bigquery_connector):
    """
    Teste de integração: Garante que o conector pode executar uma consulta simples 
    e retornar um DataFrame.
    """
    # Query de exemplo que deve funcionar em qualquer projeto GCP
    query = "SELECT 1 as teste_coluna, 'Vizu' as nome_empresa"

    # 1. O método agora retorna um gerador (iterable). Removemos o 'await' e consumimos o primeiro chunk.
    df_generator = real_bigquery_connector.extract_data(query)

    # 2. CORREÇÃO: Usar 'await' para obter o PRÓXIMO item do gerador assíncrono.
    #    Em Python 3.10+, poderia ser 'await anext(df_generator)'.
    #    Usaremos o método mágico __anext__() para máxima compatibilidade e clareza.
    try:
        df = await df_generator.__anext__()
    except StopAsyncIteration:
        # Garante que, se o gerador estiver vazio, o teste falhe com uma mensagem clara.
        raise AssertionError("O gerador assíncrono não retornou nenhum DataFrame (chunk).")

    # Assertivas Vizu para o DataFrame
    assert not df.empty
    assert 'teste_coluna' in df.columns
    assert df['nome_empresa'].iloc[0] == 'Vizu'
