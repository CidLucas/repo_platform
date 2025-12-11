"""
Data loaders for the evaluation suite.

Provides tools to extract and transform data from various sources
(WhatsApp exports, CSV files, etc.) into formats usable by workflow experiments.

Pipelines:
    1. WhatsApp Loading: whatsapp_loader.py
       - Parses WhatsApp exports (.txt)
       - Outputs: timestamp, sender, message (anonymized)

    2. PII Anonymization: pii_anonymizer.py
       - Uses regex patterns (no external deps)
       - Consistent sender mapping (João → interlocutor_1)
"""

from .pii_anonymizer import (
    anonymize_dataframe,
    anonymize_text,
)
from .whatsapp_loader import (
    add_test_id,
    anonymize_content,
    anonymize_senders,
    load_whatsapp_chat,
)

__all__ = [
    # WhatsApp loader
    "load_whatsapp_chat",
    "anonymize_senders",
    "anonymize_content",
    "add_test_id",
    # PII anonymizer
    "anonymize_dataframe",
    "anonymize_text",
]
