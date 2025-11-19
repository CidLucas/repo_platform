# libs/vizu_models/ingestion/vizu_schema.py

from enum import Enum

class VizuCanonicalColumn(str, Enum):
    """
    Nomes Canônicos de Colunas (Schema Interno Vizu).
    O nosso sistema trabalha APENAS com estes nomes.
    """
    INVOICE_DATE = "invoice_date"         # Corresponde à data de faturamento do cliente
    INVOICE_AMOUNT = "invoice_amount"     # Corresponde ao valor do item/fatura
    PRODUCT_NAME = "product_name_key"     # Corresponde ao nome do produto
    CUSTOMER_ID = "customer_identifier"   # Corresponde ao ID do cliente
    CHUNK_KEY = "chunk_key_column"        # Coluna usada para extração em batches (geralmente data)
