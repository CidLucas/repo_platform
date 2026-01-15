"""
Test script to run metric_service with sample data and identify issues.

This script:
1. Creates realistic sample data (bronze/silver layer)
2. Runs metric_service step by step
3. Logs each operation to identify errors, repeated code, and legacy issues
"""

import sys
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import logging

# Add the analytics_api to path
sys.path.insert(0, '/Users/lucascruz/Documents/GitHub/vizu-mono/services/analytics_api/src')

# Setup logging - Enable DEBUG for detailed data quality analysis
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_sample_silver_data() -> pd.DataFrame:
    """
    Create realistic sample silver data matching the canonical schema.

    Returns 100 sample transactions across:
    - 3 suppliers (emitters)
    - 10 customers (receivers)
    - 15 products
    - 3 months of data
    - 3 states/regions
    """

    # Sample data parameters
    num_rows = 100
    suppliers = [
        {"nome": "Fornecedor Alpha LTDA", "cnpj": "12.345.678/0001-90", "estado": "SP", "cidade": "São Paulo"},
        {"nome": "Fornecedor Beta S.A.", "cnpj": "98.765.432/0001-10", "estado": "RJ", "cidade": "Rio de Janeiro"},
        {"nome": "Fornecedor Gamma ME", "cnpj": "11.222.333/0001-44", "estado": "MG", "cidade": "Belo Horizonte"},
    ]

    customers = [
        {"nome": "Cliente A Comércio", "cpf_cnpj": "123.456.789-00", "estado": "SP", "cidade": "Campinas"},
        {"nome": "Cliente B Distribuidora", "cpf_cnpj": "98.765.432/0001-22", "estado": "SP", "cidade": "Santos"},
        {"nome": "Cliente C Importação", "cpf_cnpj": "234.567.890-11", "estado": "RJ", "cidade": "Niterói"},
        {"nome": "Cliente D Varejo", "cpf_cnpj": "345.678.901-22", "estado": "RJ", "cidade": "Petrópolis"},
        {"nome": "Cliente E Atacado", "cpf_cnpj": "456.789.012-33", "estado": "MG", "cidade": "Uberlândia"},
        {"nome": "Cliente F Logística", "cpf_cnpj": "567.890.123-44", "estado": "MG", "cidade": "Contagem"},
        {"nome": "Cliente G Indústria", "cpf_cnpj": "678.901.234-55", "estado": "SP", "cidade": "Sorocaba"},
        {"nome": "Cliente H Tecnologia", "cpf_cnpj": "789.012.345-66", "estado": "SP", "cidade": "Ribeirão Preto"},
        {"nome": "Cliente I Serviços", "cpf_cnpj": "890.123.456-77", "estado": "RJ", "cidade": "Campos"},
        {"nome": "Cliente J Construção", "cpf_cnpj": "901.234.567-88", "estado": "MG", "cidade": "Juiz de Fora"},
    ]

    products = [
        "Produto A - Eletrônico",
        "Produto B - Alimentos",
        "Produto C - Vestuário",
        "Produto D - Material Construção",
        "Produto E - Ferramentas",
        "Produto F - Móveis",
        "Produto G - Eletrodomésticos",
        "Produto H - Automotivo",
        "Produto I - Informática",
        "Produto J - Papelaria",
        "Produto K - Limpeza",
        "Produto L - Cosméticos",
        "Produto M - Esportivos",
        "Produto N - Brinquedos",
        "Produto O - Jardinagem",
    ]

    # Generate date range (last 3 months)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=90)

    import random
    random.seed(42)  # Reproducible results

    rows = []
    for i in range(num_rows):
        # Random date in the range
        days_offset = random.randint(0, 90)
        data_transacao = start_date + timedelta(days=days_offset)

        # Random supplier and customer
        supplier = random.choice(suppliers)
        customer = random.choice(customers)
        product = random.choice(products)

        # Random quantities and prices
        quantidade = round(random.uniform(1, 50), 2)
        valor_unitario = round(random.uniform(10, 500), 2)
        valor_total_emitter = round(quantidade * valor_unitario, 2)

        row = {
            "order_id": f"ORD-{i+1:05d}",
            "data_transacao": data_transacao,
            "emitter_nome": supplier["nome"],
            "emitter_cnpj": supplier["cnpj"],
            "emitterstateuf": supplier["estado"],
            "emitter_cidade": supplier["cidade"],
            "receiver_nome": customer["nome"],
            "receiver_cpf_cnpj": customer["cpf_cnpj"],
            "receiverstateuf": customer["estado"],
            "receiver_cidade": customer["cidade"],
            "raw_product_description": product,
            "quantidade": quantidade,
            "valor_unitario": valor_unitario,
            "valor_total_emitter": valor_total_emitter,
            "status": random.choice(["completed", "completed", "completed", "pending"]),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"✅ Created sample dataset with {len(df)} rows")
    logger.info(f"   - {df['emitter_nome'].nunique()} suppliers")
    logger.info(f"   - {df['receiver_nome'].nunique()} customers")
    logger.info(f"   - {df['raw_product_description'].nunique()} products")
    logger.info(f"   - {df['emitterstateuf'].nunique()} supplier states")
    logger.info(f"   - {df['receiverstateuf'].nunique()} customer states")
    logger.info(f"   - Total revenue: R$ {df['valor_total_emitter'].sum():,.2f}")

    return df


def test_metric_service():
    """Run metric_service with sample data and trace execution."""

    logger.info("=" * 80)
    logger.info("STARTING METRIC SERVICE TEST")
    logger.info("=" * 80)

    # Step 1: Create sample data
    logger.info("\n📊 STEP 1: Creating sample silver data...")
    df_silver = create_sample_silver_data()

    # Step 2: Create mock repository
    logger.info("\n🔧 STEP 2: Setting up mock repository...")

    class MockRepository:
        """Mock repository that returns our sample data."""

        def __init__(self, df):
            self.df = df

        def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
            logger.info(f"   MockRepo: get_silver_dataframe('{client_id}') -> {len(self.df)} rows")
            return self.df.copy()

        def write_gold_customers(self, client_id: str, data: list[dict]) -> int:
            logger.info(f"   MockRepo: write_gold_customers('{client_id}') -> {len(data)} customers")
            return len(data)

        def write_gold_suppliers(self, client_id: str, data: list[dict]) -> int:
            logger.info(f"   MockRepo: write_gold_suppliers('{client_id}') -> {len(data)} suppliers")
            return len(data)

        def write_gold_products(self, client_id: str, data: list[dict]) -> int:
            logger.info(f"   MockRepo: write_gold_products('{client_id}') -> {len(data)} products")
            return len(data)

        def write_gold_orders(self, client_id: str, data: dict) -> bool:
            logger.info(f"   MockRepo: write_gold_orders('{client_id}') -> {data}")
            return True

        def write_gold_time_series(self, client_id: str, data: list[dict]) -> int:
            logger.info(f"   MockRepo: write_gold_time_series('{client_id}') -> {len(data)} points")
            return len(data)

        def write_gold_regional(self, client_id: str, data: list[dict]) -> int:
            logger.info(f"   MockRepo: write_gold_regional('{client_id}') -> {len(data)} regions")
            return len(data)

        def write_gold_last_orders(self, client_id: str, data: list[dict]) -> int:
            logger.info(f"   MockRepo: write_gold_last_orders('{client_id}') -> {len(data)} orders")
            return len(data)

    mock_repo = MockRepository(df_silver)

    # Step 3: Initialize MetricService
    logger.info("\n🚀 STEP 3: Initializing MetricService...")
    try:
        from analytics_api.services.metric_service import MetricService

        client_id = "test-client-123"

        # Test without writing to gold (write_gold=False)
        logger.info(f"   Creating MetricService(client_id='{client_id}', write_gold=False)")
        service = MetricService(mock_repo, client_id, write_gold=False)

        logger.info(f"   ✅ MetricService initialized successfully")
        logger.info(f"   - DataFrame shape: {service.df.shape}")
        logger.info(f"   - Customers aggregated: {service.df_clientes_agg.shape}")
        logger.info(f"   - Suppliers aggregated: {service.df_fornecedores_agg.shape}")
        logger.info(f"   - Products aggregated: {service.df_produtos_agg.shape}")

    except Exception as e:
        logger.error(f"   ❌ Failed to initialize MetricService: {e}", exc_info=True)
        return

    # Step 4: Test Level 1 - Home Metrics
    logger.info("\n📍 STEP 4: Testing get_home_metrics() [Level 1]...")
    try:
        home_metrics = service.get_home_metrics()
        logger.info(f"   ✅ Home metrics calculated successfully")
        logger.info(f"   Scorecards: {home_metrics.scorecards}")
        logger.info(f"   Charts: {len(home_metrics.charts)} chart(s)")
    except Exception as e:
        logger.error(f"   ❌ Failed to get home metrics: {e}", exc_info=True)

    # Step 5: Test Level 2 - Fornecedores Overview
    logger.info("\n🏭 STEP 5: Testing get_fornecedores_overview() [Level 2]...")
    try:
        fornecedores = service.get_fornecedores_overview()
        logger.info(f"   ✅ Fornecedores overview calculated successfully")
        logger.info(f"   Total fornecedores: {fornecedores.scorecard_total_fornecedores}")
        logger.info(f"   Crescimento: {fornecedores.scorecard_crescimento_percentual}")
        logger.info(f"   Rankings:")
        logger.info(f"     - Por receita: {len(fornecedores.ranking_por_receita)} items")
        logger.info(f"     - Por ticket médio: {len(fornecedores.ranking_por_ticket_medio)} items")
    except Exception as e:
        logger.error(f"   ❌ Failed to get fornecedores overview: {e}", exc_info=True)

    # Step 6: Test Level 2 - Clientes Overview
    logger.info("\n👥 STEP 6: Testing get_clientes_overview() [Level 2]...")
    try:
        clientes = service.get_clientes_overview()
        logger.info(f"   ✅ Clientes overview calculated successfully")
        logger.info(f"   Total clientes: {clientes.scorecard_total_clientes}")
        logger.info(f"   Ticket médio geral: R$ {clientes.scorecard_ticket_medio_geral:,.2f}")
        logger.info(f"   Frequência média: {clientes.scorecard_frequencia_media_geral:.2f}")
        logger.info(f"   Crescimento: {clientes.scorecard_crescimento_percentual}")
    except Exception as e:
        logger.error(f"   ❌ Failed to get clientes overview: {e}", exc_info=True)

    # Step 7: Test Level 2 - Produtos Overview
    logger.info("\n📦 STEP 7: Testing get_produtos_overview() [Level 2]...")
    try:
        produtos = service.get_produtos_overview()
        logger.info(f"   ✅ Produtos overview calculated successfully")
        logger.info(f"   Total itens únicos: {produtos.scorecard_total_itens_unicos}")
        logger.info(f"   Rankings:")
        logger.info(f"     - Por receita: {len(produtos.ranking_por_receita)} items")
        logger.info(f"     - Por volume: {len(produtos.ranking_por_volume)} items")
    except Exception as e:
        logger.error(f"   ❌ Failed to get produtos overview: {e}", exc_info=True)

    # Step 8: Test Level 2 - Pedidos Overview
    logger.info("\n📋 STEP 8: Testing get_pedidos_overview() [Level 2]...")
    try:
        pedidos = service.get_pedidos_overview()
        logger.info(f"   ✅ Pedidos overview calculated successfully")
        logger.info(f"   Ticket médio por pedido: R$ {pedidos.scorecard_ticket_medio_por_pedido:,.2f}")
        logger.info(f"   Qtd média produtos: {pedidos.scorecard_qtd_media_produtos_por_pedido:.2f}")
        logger.info(f"   Últimos pedidos: {len(pedidos.ultimos_pedidos)} items")
    except Exception as e:
        logger.error(f"   ❌ Failed to get pedidos overview: {e}", exc_info=True)

    # Step 9: Test with write_gold=True
    logger.info("\n💾 STEP 9: Testing with write_gold=True...")
    try:
        service_with_write = MetricService(mock_repo, client_id, write_gold=True)
        logger.info(f"   ✅ MetricService with write_gold=True completed")
        logger.info(f"   Gold tables written: {service_with_write._gold_tables_written}")
    except Exception as e:
        logger.error(f"   ❌ Failed with write_gold=True: {e}", exc_info=True)

    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_metric_service()
