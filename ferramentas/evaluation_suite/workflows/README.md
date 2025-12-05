# Evaluation Suite - Workflows

Ferramentas para testar e avaliar workflows LangGraph do sistema Vizu.

## Estrutura

```
workflows/
├── boleta_trader/           # Workflow de boletas
│   ├── run_experiment.py    # Runner principal
│   ├── test_cases.json      # Casos de teste
│   └── __init__.py
└── README.md
```

## Quick Start

### 1. Preparar ambiente

```bash
cd ferramentas/evaluation_suite
poetry install
```

### 2. Configurar variáveis de ambiente

Criar `.env` com as credenciais necessárias:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
# ou
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Rodar experimento

```bash
# Via Makefile (da raiz do projeto)
make experiment-workflow-v2

# Ou diretamente
cd ferramentas/evaluation_suite
poetry run python -m workflows.boleta_trader.run_experiment
```

### 4. Exportar para CSV

```bash
# Via Makefile
make experiment-workflow-v2-export

# Ou diretamente
poetry run python -m workflows.boleta_trader.run_experiment --export-csv
```

O CSV é salvo em `workflows/boleta_trader/results_<timestamp>.csv` com as colunas:

| Coluna | Descrição |
|--------|-----------|
| test_id | ID do caso de teste |
| query | Conversa completa passada para check_negotiation |
| description | Output do check_negotiation (justificativa) |
| extracted | Output do extrator (JSON) |
| boleta_formatada | Output do formatador (boleta final) |
| success | Se o teste passou |
| duration_ms | Tempo de execução |
| error | Erro se houver |

## Data Loaders

Ferramentas para carregar e transformar dados de diferentes fontes.

### WhatsApp Chat Loader

Carrega exports de chat do WhatsApp (.txt):

```bash
# Via Makefile
make data-load-whatsapp INPUT=chat.txt OUTPUT=data/extracted.csv

# Ou diretamente
python -m evaluation_suite.data_loaders.whatsapp_loader chat.txt -o output.csv

# Opções
python -m evaluation_suite.data_loaders.whatsapp_loader chat.txt \
    --triggers fecha fechado trava \
    --context-window 15 \
    --anonymize \
    -o output.csv
```

### CSV Loader

Carrega CSVs existentes com mensagens:

```bash
# Via Makefile
make data-load-csv INPUT=messages.csv OUTPUT=data/extracted.csv

# Ou diretamente
python -m evaluation_suite.data_loaders.csv_loader messages.csv -o output.csv

# Com colunas customizadas
python -m evaluation_suite.data_loaders.csv_loader messages.csv \
    --message-col content \
    --sender-col author \
    --timestamp-col date \
    -o output.csv
```

### Uso em Python

```python
from evaluation_suite.data_loaders import WhatsAppChatLoader, CSVMessageLoader

# WhatsApp
loader = WhatsAppChatLoader("chat.txt", anonymize=True)
conversations = loader.extract_trigger_conversations(["fecha", "fechado"])

# CSV
loader = CSVMessageLoader("data.csv", message_col="content")
conversations = loader.extract_trigger_conversations(["fecha"])

# Export
from evaluation_suite.data_loaders import export_to_workflow_csv
export_to_workflow_csv(conversations, "output.csv")
```

## Casos de Teste

Os casos de teste ficam em `test_cases.json`:

```json
[
  {
    "id": "buy_simple",
    "input": "compra 100 petr4",
    "expected": {
      "tipo": "compra",
      "ativo": "PETR4",
      "quantidade": 100
    }
  }
]
```

## Makefile Targets

```bash
# Experimentos
make experiment-workflow-v2        # Roda experimento
make experiment-workflow-v2-export # Roda e exporta CSV

# Data Loaders
make data-load-whatsapp INPUT=chat.txt    # WhatsApp → CSV
make data-load-csv INPUT=data.csv         # CSV → Workflow format
```
