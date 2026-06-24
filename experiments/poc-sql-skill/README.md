# PoC SQL Skill — Runbook

**Objetivo:** Validar a Skills & Prompts Factory — pipeline completa com experimento real.

## Pre-requisitos

- Docker rodando com a stack Blu (agent_api na porta 8003)
- Python 3.11+ com as libs do repo

## Rodar

```bash
# 1. Token de teste
python tests/agent_routing/get_test_token.py

# 2. Executar experimento (modelo padrao da Agent API)
python -m blu_experiment_service.cli run experiments/poc-sql-skill/manifest.yaml
```

## Resultados

```
Langfuse → Datasets → experiment/poc-sql-skill → Experiments
```

## Estrutura

```
experiments/poc-sql-skill/
├── manifest.yaml       ← 2 personas, 3 test cases SQL
├── README.md           ← este arquivo
```
