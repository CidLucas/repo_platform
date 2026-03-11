# Vizu Experiment Service

Serviço de orquestração de experimentos para geração orgânica de datasets de treinamento.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EXPERIMENT PIPELINE FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. MANIFEST DEFINITION                                                      │
│     └── experiments/my_experiment.yaml                                       │
│         ├── clients: [cliente_a, cliente_b, ...]                            │
│         ├── cases: [{message, expected_tool, ...}, ...]                     │
│         └── hitl_config: {confidence_threshold, sample_rate, ...}           │
│                                                                              │
│  2. EXPERIMENT EXECUTION                                                     │
│     └── ExperimentRunner.run_from_manifest(manifest)                        │
│         ├── For each client variant:                                         │
│         │   └── For each test case:                                          │
│         │       └── POST /chat → Atendente API                              │
│         └── Collect responses + Langfuse traces                             │
│                                                                              │
│  3. RESPONSE CLASSIFICATION                                                  │
│     └── ResponseClassifier.classify_run(run)                                │
│         ├── HIGH_CONFIDENCE → Direct to dataset                             │
│         ├── MEDIUM/LOW_CONFIDENCE → Route to HITL                           │
│         ├── TOOL_USED (sensitive) → Route to HITL                           │
│         └── ERROR → Log and skip                                            │
│                                                                              │
│  4. HITL REVIEW (if routed)                                                  │
│     └── HITL Dashboard (apps/hitl_dashboard)                                 │
│         ├── Human reviews and approves/corrects                              │
│         └── Feedback stored in hitl_review table                            │
│                                                                              │
│  5. DATASET GENERATION                                                       │
│     └── TrainingDatasetGenerator.add_cases_from_run(run_id)                 │
│         ├── Collect approved cases (direct + HITL)                           │
│         ├── Format for training (input/output pairs)                         │
│         └── Push to Langfuse Dataset                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Instalação

```bash
cd libs/vizu_experiment_service
poetry install
```

## CLI

```bash
# Run an experiment
poetry run experiment run experiments/my_experiment.yaml

# Classify results and route to HITL
poetry run experiment classify <run_id>

# Export training data
poetry run experiment export <run_id> --format jsonl --output dataset.jsonl
```

## Uso Programático

### 1. Definir Manifesto

```yaml
# experiments/atendente_baseline.yaml
name: atendente_baseline
version: "1.0.0"
description: "Baseline evaluation for all clients"

api_url: http://localhost:8003

clients:
  - cliente_id: "550e8400-e29b-41d4-a716-446655440001"
    name: "Studio J"
  - cliente_id: "550e8400-e29b-41d4-a716-446655440002"
    name: "Casa com Alma"

cases:
  - id: "services"
    message: "Quais serviços vocês oferecem?"
    expected_tool: buscar_informacoes
    tags: ["rag"]

  - id: "hours"
    message: "Qual o horário de funcionamento?"
    expected_contains: ["horário", "funcionamento"]
    tags: ["basic"]

hitl:
  enabled: true
  confidence_threshold: 0.7
  sample_rate: 0.1
  always_review_tools:
    - executar_sql_agent

langfuse:
  enabled: true
  create_dataset: true
  dataset_name: "atendente-baseline"
```

### 2. Executar Experimento

```python
from vizu_experiment_service import ExperimentRunner, ManifestLoader

# Load manifest
manifest = ManifestLoader.load_from_file("experiments/atendente_baseline.yaml")

# Run experiment
async with AsyncSession(engine) as session:
    runner = ExperimentRunner(db_session=session)
    run = await runner.run_from_manifest(manifest)

    print(f"Run ID: {run.id}")
    print(f"Success: {run.success_cases}/{run.total_cases}")
```

### 3. Classificar e Rotear para HITL

```python
from vizu_experiment_service import ResponseClassifier

classifier = ResponseClassifier(db_session=session, hitl_service=hitl_service)
counts = await classifier.classify_run(run, route_to_hitl=True)

print(f"High confidence: {counts['high_confidence']}")
print(f"Routed to HITL: {counts['low_confidence'] + counts['tool_used']}")
```

### 4. Gerar Dataset de Treinamento

```python
from vizu_experiment_service import TrainingDatasetGenerator

generator = TrainingDatasetGenerator(db_session=session, langfuse_client=langfuse)

# Create Langfuse dataset
await generator.create_langfuse_dataset(
    name="atendente-v1-training",
    description="Training data from experiment runs",
)

# Add cases from run
added = await generator.add_cases_from_run(
    dataset_name="atendente-v1-training",
    run_id=run.id,
    include_high_confidence=True,
    include_reviewed=True,
)
print(f"Added {added} items to dataset")

# Export to JSONL
jsonl = await generator.export_run_to_jsonl(run.id)
Path("training_data.jsonl").write_text(jsonl)
```

## Modelos de Dados

### ExperimentRun

Armazena informações de uma execução de experimento:
- `manifest_name`, `manifest_version`: Identificação do manifesto
- `status`: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
- `total_cases`, `success_cases`, `failure_cases`, `error_cases`
- `hitl_routed_cases`: Quantos casos foram enviados para revisão

### ExperimentCase

Armazena cada caso de teste individual:
- `input_message`: Mensagem enviada ao atendente
- `actual_response`: Resposta recebida
- `outcome`: SUCCESS, FAILURE, ERROR, NEEDS_REVIEW, REVIEWED
- `classification`: HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, LOW_CONFIDENCE, TOOL_USED
- `langfuse_trace_id`: Link para trace no Langfuse

## Integração com Langfuse

- Cada experimento cria traces no Langfuse
- Datasets são criados automaticamente com samples aprovados
- Métricas de qualidade são registradas para análise

## Migrations

A migration `007_add_experiment_tables.py` cria as tabelas necessárias:
- `experiment_run`
- `experiment_case`

Execute com:
```bash
cd libs/vizu_db_connector
poetry run alembic upgrade head
```
