#!/usr/bin/env python3
"""
WhatsApp Chat Loader.

Parses WhatsApp chat exports (.txt) and outputs anonymized CSV.

Format supported: [DD/MM/YY, HH:MM:SS] Sender: Message

Usage:
    # CLI
    python -m evaluation_suite.data_loaders.whatsapp_loader input.txt -o output.csv

    # Python
    from evaluation_suite.data_loaders import load_whatsapp_chat
    df = load_whatsapp_chat("chat.txt")
"""

import re
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# WhatsApp message pattern: [DD/MM/YY, HH:MM:SS] Sender: Message
WHATSAPP_PATTERN = re.compile(
    r'\[(\d{2}/\d{2}/\d{2}),?\s+(\d{2}:\d{2}:\d{2})\]\s+([^:]+):\s*(.*)'
)

# Alternative pattern without brackets
WHATSAPP_PATTERN_ALT = re.compile(
    r'(\d{2}/\d{2}/\d{2,4}),?\s+(\d{2}:\d{2}(?::\d{2})?)\s*[-–]\s*([^:]+):\s*(.*)'
)


def parse_whatsapp_line(line: str) -> Optional[Dict]:
    """Parse a single WhatsApp message line."""
    line = line.strip()
    if not line:
        return None

    # Try main pattern [DD/MM/YY, HH:MM:SS] Sender: Message
    match = WHATSAPP_PATTERN.match(line)
    if match:
        date_str, time_str, sender, message = match.groups()
        return {
            "timestamp": f"{date_str} {time_str}",
            "sender": sender.strip(),
            "message": message.strip(),
        }

    # Try alternative pattern DD/MM/YY, HH:MM - Sender: Message
    match = WHATSAPP_PATTERN_ALT.match(line)
    if match:
        date_str, time_str, sender, message = match.groups()
        return {
            "timestamp": f"{date_str} {time_str}",
            "sender": sender.strip(),
            "message": message.strip(),
        }

    return None


def load_whatsapp_chat(file_path: str) -> pd.DataFrame:
    """
    Load WhatsApp chat export.

    Args:
        file_path: Path to WhatsApp export file (.txt)

    Returns:
        DataFrame with columns: timestamp, sender, message
    """
    messages = []
    current_msg = None

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_whatsapp_line(line)

            if parsed:
                # Save previous message
                if current_msg:
                    messages.append(current_msg)
                current_msg = parsed
            elif current_msg and line.strip():
                # Continuation of previous message (multiline)
                current_msg["message"] += "\n" + line.strip()

        # Don't forget the last message
        if current_msg:
            messages.append(current_msg)

    df = pd.DataFrame(messages)
    logger.info(f"Loaded {len(df)} messages from {file_path}")
    return df


def anonymize_senders(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Anonymize sender names with consistent mapping.

    Args:
        df: Input DataFrame with 'sender' column

    Returns:
        Tuple of (DataFrame with anonymized senders, mapping dict)
    """
    df = df.copy()

    # Get unique senders in order of appearance
    unique_senders = df["sender"].unique()

    # Create consistent mapping
    sender_map = {
        sender: f"interlocutor_{i+1}"
        for i, sender in enumerate(unique_senders)
    }

    # Apply mapping
    df["sender"] = df["sender"].map(sender_map)

    logger.info(f"Anonymized {len(sender_map)} unique senders")
    return df, sender_map


def anonymize_content(df: pd.DataFrame) -> pd.DataFrame:
    """
    Anonymize PII in message content.
    """
    from .pii_anonymizer import anonymize_text

    df = df.copy()
    df["message"] = df["message"].apply(anonymize_text)
    return df


def add_test_id(df: pd.DataFrame, start_id: int = 1000) -> pd.DataFrame:
    """Add sequential test_id column."""
    df = df.copy()
    df.insert(0, "test_id", range(start_id, start_id + len(df)))
    return df


# --- CLI ---

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Load WhatsApp chat export to CSV (with anonymization)"
    )
    parser.add_argument("input", help="Input WhatsApp export file (.txt)")
    parser.add_argument("-o", "--output", help="Output CSV path", default="output.csv")
    parser.add_argument(
        "--no-anonymize-senders",
        action="store_true",
        help="Skip sender name anonymization"
    )
    parser.add_argument(
        "--no-anonymize-content",
        action="store_true",
        help="Skip PII anonymization in message content"
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

    # Load
    df = load_whatsapp_chat(args.input)
    print(f"📱 Loaded {len(df)} messages from {args.input}")

    if len(df) == 0:
        print("❌ No messages parsed! Check file format.")
        return 1

    # Anonymize senders
    if not args.no_anonymize_senders:
        df, sender_map = anonymize_senders(df)
        print(f"👤 Anonymized {len(sender_map)} unique senders")

    # Anonymize content
    if not args.no_anonymize_content:
        df = anonymize_content(df)
        print(f"🔒 PII removed from message content")

    # Add test_id
    if args.add_test_id:
        df = add_test_id(df)

    # Export
    df.to_csv(args.output, index=False)
    print(f"✅ Exported to {args.output}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
