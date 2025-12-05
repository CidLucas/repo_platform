# Data Directory

This directory holds input data files for workflow experiments.

## Structure

```
data/
├── raw/           # Original WhatsApp exports (.txt) and raw CSVs
│   └── chat.txt   # WhatsApp export
├── processed/     # Cleaned and anonymized CSVs ready for experiments
│   └── anonymized.csv
└── README.md
```

## Pipeline

### Step 1: Load WhatsApp chat

```bash
make data-load-whatsapp \
    INPUT=ferramentas/evaluation_suite/workflows/boleta_trader/data/raw/chat.txt \
    OUTPUT=ferramentas/evaluation_suite/workflows/boleta_trader/data/raw/loaded.csv
```

Uses LangChain's `WhatsAppChatLoader` to parse the export.

Output columns: `timestamp`, `sender`, `message`

### Step 2: Anonymize

```bash
make data-anonymize \
    INPUT=ferramentas/evaluation_suite/workflows/boleta_trader/data/raw/loaded.csv \
    OUTPUT=ferramentas/evaluation_suite/workflows/boleta_trader/data/processed/anonymized.csv
```

Uses Microsoft Presidio to:
- **Sender anonymization**: `João` → `interlocutor_1` (consistent mapping)
- **Content anonymization**: Removes phone numbers, emails, locations, etc.
- **Adds test_id**: Sequential IDs starting from 1000

## Anonymization Details

### Sender Mapping

Senders are mapped consistently throughout the dataset:
- First unique sender → `interlocutor_1`
- Second unique sender → `interlocutor_2`
- etc.

The mapping is deterministic based on order of appearance.

### PII Detection (Presidio)

Detects and replaces:
- 📍 Locations → `<LOCATION>`
- 📱 Phone numbers → `<PHONE_NUMBER>`
- 📧 Emails → `<EMAIL_ADDRESS>`
- 💳 Credit cards → `<CREDIT_CARD>`
- 🌐 URLs → `<URL>`
- 🖥️ IP addresses → `<IP_ADDRESS>`

**Note:** Trading values (cotação, volume) are NOT anonymized.

## Python Usage

```python
from evaluation_suite.data_loaders import load_whatsapp_chat, anonymize_dataframe

# Load
df = load_whatsapp_chat("data/raw/chat.txt")

# Anonymize
df_clean = anonymize_dataframe(df)

# Export
df_clean.to_csv("data/processed/anonymized.csv", index=False)
```

## .gitignore

Raw data should NOT be committed:
```
data/raw/*.txt
data/raw/*.csv
!data/raw/.gitkeep
```
