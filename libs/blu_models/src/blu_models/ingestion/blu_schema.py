# libs/blu_models/ingestion/blu_schema.py
from __future__ import annotations

from enum import Enum


class BluCanonicalColumn(Enum):
    """
    Nomes Canônicos de Colunas (Schema Interno Blu).
    O nosso sistema trabalha APENAS com estes nomes.
    """

    INVOICE_DATE = "invoice_date"  # Corresponde à data de faturamento do cliente
    INVOICE_AMOUNT = "invoice_amount"  # Corresponde ao valor do item/fatura
    PRODUCT_NAME = "product_name_key"  # Corresponde ao nome do produto
    CUSTOMER_ID = "customer_identifier"  # Corresponde ao ID do cliente
    CHUNK_KEY = (
        "chunk_key_column"  # Coluna usada para extração em batches (geralmente data)
    )
