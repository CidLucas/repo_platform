#!/usr/bin/env python3
"""
PII Anonymizer using Presidio with Portuguese NLP support.

Anonymizes sensitive data in CSV files including:
- Names (PERSON) - using spaCy NER
- Phone numbers
- Emails
- CPF/CNPJ
- PIX keys
- URLs
- Credit cards

Maintains consistent sender mappings (e.g., João → interlocutor_1).

Usage:
    # CLI
    python -m evaluation_suite.data_loaders.pii_anonymizer input.csv -o output.csv

    # Python
    from evaluation_suite.data_loaders import anonymize_dataframe
    df_clean = anonymize_dataframe(df)
"""

import re
import logging
import pandas as pd
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# --- Presidio setup ---

_analyzer = None
_anonymizer = None


def _get_analyzer():
    """Get or create the Presidio analyzer with Portuguese support."""
    global _analyzer

    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        logger.info("Initializing Presidio Analyzer with Portuguese NLP...")

        # Configure spaCy for Portuguese
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "pt", "model_name": "pt_core_news_sm"},
            ],
        }

        # Try to create provider with Portuguese model
        try:
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            _analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                supported_languages=["pt"]
            )
        except Exception as e:
            logger.warning(f"Failed to load Portuguese model, falling back to default: {e}")
            _analyzer = AnalyzerEngine()

        # Add custom recognizers for Brazilian data
        _add_brazilian_recognizers(_analyzer)

        logger.info("Presidio Analyzer initialized")

    return _analyzer


def _get_anonymizer():
    """Get or create the Presidio anonymizer."""
    global _anonymizer

    if _anonymizer is None:
        from presidio_anonymizer import AnonymizerEngine
        _anonymizer = AnonymizerEngine()
        logger.info("Presidio Anonymizer initialized")

    return _anonymizer


def _add_brazilian_recognizers(analyzer):
    """Add custom recognizers for Brazilian PII patterns."""
    from presidio_analyzer import PatternRecognizer, Pattern

    # CPF: 123.456.789-00 or 12345678900
    cpf_pattern = Pattern(
        name="cpf_pattern",
        regex=r"\b\d{3}\.?\d{3}\.?\d{3}[-.]?\d{2}\b",
        score=0.85
    )
    cpf_recognizer = PatternRecognizer(
        supported_entity="CPF",
        patterns=[cpf_pattern],
        supported_language="pt"
    )
    analyzer.registry.add_recognizer(cpf_recognizer)

    # CNPJ: 12.345.678/0001-00
    cnpj_pattern = Pattern(
        name="cnpj_pattern",
        regex=r"\b\d{2}\.?\d{3}\.?\d{3}[/\\]?\d{4}[-.]?\d{2}\b",
        score=0.85
    )
    cnpj_recognizer = PatternRecognizer(
        supported_entity="CNPJ",
        patterns=[cnpj_pattern],
        supported_language="pt"
    )
    analyzer.registry.add_recognizer(cnpj_recognizer)

    # PIX keys (UUID format)
    pix_pattern = Pattern(
        name="pix_uuid_pattern",
        regex=r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b",
        score=0.8
    )
    pix_recognizer = PatternRecognizer(
        supported_entity="PIX_KEY",
        patterns=[pix_pattern],
        supported_language="pt"
    )
    analyzer.registry.add_recognizer(pix_recognizer)

    # Brazilian phone numbers with WhatsApp mentions
    phone_patterns = [
        Pattern(
            name="whatsapp_mention",
            regex=r"@\d{10,13}",
            score=0.9
        ),
        Pattern(
            name="br_phone_full",
            regex=r"\+?55\s*\(?\d{2}\)?\s*\d{4,5}[-.\s]?\d{4}",
            score=0.85
        ),
        Pattern(
            name="br_phone_local",
            regex=r"\(?\d{2}\)?\s*9?\d{4}[-.\s]?\d{4}",
            score=0.7
        ),
    ]
    br_phone_recognizer = PatternRecognizer(
        supported_entity="BR_PHONE",
        patterns=phone_patterns,
        supported_language="pt"
    )
    analyzer.registry.add_recognizer(br_phone_recognizer)

    logger.info("Added Brazilian PII recognizers (CPF, CNPJ, PIX, BR_PHONE)")


def anonymize_text(
    text: str,
    language: str = "pt",
    entities_to_detect: Optional[List[str]] = None,
) -> str:
    """
    Anonymize PII in text using Presidio.

    Args:
        text: Input text
        language: Language code (default: pt for Portuguese)
        entities_to_detect: List of entities to detect. If None, detects all.

    Returns:
        Anonymized text with PII replaced by entity tags
    """
    if not text or pd.isna(text):
        return text

    text = str(text)

    # Skip very short texts
    if len(text.strip()) < 2:
        return text

    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()

    # Default entities to detect
    if entities_to_detect is None:
        entities_to_detect = [
            "PERSON",           # Names
            "EMAIL_ADDRESS",    # Emails
            "PHONE_NUMBER",     # Phone numbers
            "URL",              # URLs
            "CREDIT_CARD",      # Credit cards
            "CPF",              # Brazilian CPF
            "CNPJ",             # Brazilian CNPJ
            "PIX_KEY",          # PIX keys
            "BR_PHONE",         # Brazilian phone numbers
            "LOCATION",         # Location names
        ]

    try:
        # Analyze text
        results = analyzer.analyze(
            text=text,
            entities=entities_to_detect,
            language=language
        )

        # Anonymize
        if results:
            anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymized.text

        return text

    except Exception as e:
        # Log but don't fail - return original text
        logger.debug(f"Presidio error on text '{text[:50]}...': {e}")
        return text


def anonymize_senders(
    df: pd.DataFrame,
    sender_column: str = "sender",
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Anonymize sender names with consistent mapping.

    Preserves order: first sender seen becomes interlocutor_1, etc.

    Args:
        df: Input DataFrame
        sender_column: Name of the sender column

    Returns:
        Tuple of (DataFrame with anonymized senders, mapping dict)
    """
    df = df.copy()

    # Get unique senders in order of first appearance (excluding NaN)
    seen = {}
    unique_senders = []
    for sender in df[sender_column]:
        if pd.notna(sender) and sender not in seen:
            seen[sender] = True
            unique_senders.append(sender)

    # Create consistent mapping
    sender_map = {
        sender: f"interlocutor_{i+1}"
        for i, sender in enumerate(unique_senders)
    }

    # Apply mapping
    df[sender_column] = df[sender_column].map(
        lambda x: sender_map.get(x, x) if pd.notna(x) else x
    )

    logger.info(f"Anonymized {len(sender_map)} unique senders")
    return df, sender_map


def anonymize_dataframe(
    df: pd.DataFrame,
    message_column: str = "message",
    sender_column: str = "sender",
    anonymize_messages: bool = True,
    anonymize_sender_names: bool = True,
    language: str = "pt",
) -> pd.DataFrame:
    """
    Anonymize a DataFrame with chat messages using Presidio.

    Args:
        df: Input DataFrame
        message_column: Column containing message text
        sender_column: Column containing sender names
        anonymize_messages: If True, run PII removal on message content
        anonymize_sender_names: If True, replace sender names with interlocutor_N
        language: Language code for NLP (default: pt)

    Returns:
        Anonymized DataFrame
    """
    df = df.copy()

    # Anonymize sender names first (consistent mapping)
    sender_map = {}
    if anonymize_sender_names and sender_column in df.columns:
        df, sender_map = anonymize_senders(df, sender_column)
        logger.info(f"Sender mapping created with {len(sender_map)} senders")

    # Anonymize message content with Presidio
    if anonymize_messages and message_column in df.columns:
        logger.info(f"Anonymizing {len(df)} messages with Presidio...")

        # Initialize Presidio lazily (first call)
        _ = _get_analyzer()
        _ = _get_anonymizer()

        # Process messages
        anonymized_count = 0
        for i, text in enumerate(df[message_column]):
            if pd.notna(text):
                original = str(text)
                anonymized = anonymize_text(original, language=language)
                if anonymized != original:
                    anonymized_count += 1
                df.at[df.index[i], message_column] = anonymized

            # Progress logging
            if (i + 1) % 500 == 0:
                logger.info(f"  Processed {i+1}/{len(df)} messages...")

        logger.info(f"Anonymization complete: {anonymized_count} messages modified")

    return df


def add_test_id(df: pd.DataFrame, start_id: int = 1000) -> pd.DataFrame:
    """Add sequential test_id column (or replace existing)."""
    df = df.copy()
    if "test_id" in df.columns:
        df = df.drop(columns=["test_id"])
    df.insert(0, "test_id", range(start_id, start_id + len(df)))
    return df


# --- CLI ---

def main():
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Anonymize PII in chat CSV using Presidio"
    )
    parser.add_argument("input", help="Input CSV file")
    parser.add_argument("-o", "--output", help="Output CSV path", default="output_anonymized.csv")
    parser.add_argument(
        "--message-col",
        default="message",
        help="Message column name (default: message)"
    )
    parser.add_argument(
        "--sender-col",
        default="sender",
        help="Sender column name (default: sender)"
    )
    parser.add_argument(
        "--language",
        default="pt",
        help="Language code for NLP (default: pt)"
    )
    parser.add_argument(
        "--no-message-anonymization",
        action="store_true",
        help="Skip PII anonymization of message content"
    )
    parser.add_argument(
        "--no-sender-anonymization",
        action="store_true",
        help="Skip sender name anonymization"
    )
    parser.add_argument(
        "--add-test-id",
        action="store_true",
        help="Add test_id column"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Load CSV
    df = pd.read_csv(args.input)
    print(f"📊 Loaded {len(df)} rows from {args.input}")

    # Anonymize
    df = anonymize_dataframe(
        df,
        message_column=args.message_col,
        sender_column=args.sender_col,
        anonymize_messages=not args.no_message_anonymization,
        anonymize_sender_names=not args.no_sender_anonymization,
        language=args.language,
    )

    # Add test_id if requested
    if args.add_test_id:
        df = add_test_id(df)

    # Export
    df.to_csv(args.output, index=False)
    print(f"🔒 Anonymized data saved to {args.output}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
