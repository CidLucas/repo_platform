# Vizu Evaluation Suite

This directory contains the source code for the Vizu Evaluation Suite, a Streamlit application used for evaluating the Vizu APIs.

## Overview

The Evaluation Suite is a tool for testing and validating the performance of the Vizu APIs, including prompts, models, and business logic.

### Key Technologies

*   **Framework:** Streamlit
*   **Data Manipulation:** Pandas
*   **HTTP Client:** httpx
*   **Package Manager:** Poetry

## Getting Started

The Evaluation Suite is run as a Docker container, as defined in the `docker-compose.yml` file. To run the suite, use the following command:

```bash
docker-compose up evaluation_suite
# Vizu Evaluation Suite

Este diretório contém a Evaluation Suite — um conjunto de ferramentas e fluxos para avaliar prompts, modelos e regras de negócio da Vizu.

**Objetivo:** oferecer formas reprodutíveis de carregar dados (ex.: WhatsApp), anonimizar PII, executar workflows (boleta_trader) e exportar resultados para CSV/JSON.

**Principais componentes:**
- **Loader(s):** parsers para arquivos WhatsApp e CSV (`data_loaders/whatsapp_loader.py`).
- **Anonymizer:** `pii_anonymizer.py` — implementado com Presidio (spaCy `pt_core_news_sm`) para detectar e anonimizar nomes, telefones, PIX, CPF/CNPJ, etc.
- **Workflows:** `workflows/boleta_trader/workflow_v2.py` (graph-based LangGraph workflow) + runner `run_experiment.py`.
- **Experiment runner:** `run_experiment.py` — encontra triggers, invoca workflow, captura outputs e exporta CSV/JSON.

**Stack resumido:** Python 3.11+, Poetry, Docker (container de execução usado nos exemplos), Presidio + spaCy para NER.

**Principais arquivos:**
- `src/evaluation_suite/data_loaders/whatsapp_loader.py` — converte `chat.txt`/CSV WhatsApp para CSV estruturado.
- `src/evaluation_suite/data_loaders/pii_anonymizer.py` — Presidio-based anonymizer.
- `workflows/boleta_trader/workflow_v2.py` — fluxo gatekeeper → validator → extractor → formatter.
- `workflows/boleta_trader/run_experiment.py` — runner CLI com `--export-csv` e `--limit`.
- `workflows/boleta_trader/manifest_*.yaml` — manifests de datasets / configurações de experimento.

**Contribuições recentes importantes:**
- Anonimização de nomes com Presidio (spaCy PT model).
- Suporte a export CSV com colunas: `test_id, query, description, extracted, boleta_formatada, success, duration_ms, error`.
- `run_experiment.py` agora captura estados intermediários antes do formatter resetar dados.
- `workflow_v2.py` adicionou um `time.sleep(3)` antes de cada chamada ao LLM para evitar rate limits.

**Como usar (tutorial rápido)**

**1) Preparar o ambiente (local / container)**
- Local (recomendado em projeto): use Poetry para instalar dependências definidas em `ferramentas/evaluation_suite/pyproject.toml`.

```bash
cd ferramentas/evaluation_suite
poetry install
poetry run python -m spacy download pt_core_news_sm
```

- Alternativa (dentro do container usado pelo monorepo): execute pip / python -m pip conforme o container (`vizu_atendente_core`) já usado em dev.

**2) Gerar / preparar os dados WhatsApp**
- Se você tem um `chat.txt` exportado do WhatsApp, use o loader:

```bash
# converte e cria `data/processed/whatsapp_test.csv`
poetry run python -m evaluation_suite.data_loaders.whatsapp_loader \
	workflows/boleta_trader/data/raw/chat.txt \
	-o workflows/boleta_trader/data/processed/whatsapp_test.csv
```

**3) Anonimizar com Presidio (recomenda-se separar sender-anon e msg-anon)**
- Criar uma amostra (primeiro 25%) para testes rápidos:

```bash
python - <<'PY'
import pandas as pd
df = pd.read_csv('workflows/boleta_trader/data/processed/whatsapp_test.csv')
df_quarter = df.iloc[:len(df)//4]
df_quarter.to_csv('workflows/boleta_trader/data/raw/whats_amostra.csv', index=False)
print('Saved whats_amostra.csv', len(df_quarter))
PY
```

- Rodar o anonymizer (usa Presidio + spaCy PT):

```bash
poetry run python -m evaluation_suite.data_loaders.pii_anonymizer \
	workflows/boleta_trader/data/raw/whats_amostra.csv \
	-o workflows/boleta_trader/data/processed/whats_amostra_anonymized.csv \
	--language pt
```

Observação: o anonymizer mantém um mapeamento consistente de `sender` → `interlocutor_N` (ordem de aparição).

**4) Executar um experimento com o runner**
- Exemplo usando o manifest criado para a amostra anonimizda:

```bash
# rodar 10 casos e exportar CSV (usa workflow_v2 e vizu_llm_service quando disponível)
poetry run python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment \
	ferramentas/evaluation_suite/workflows/boleta_trader/manifest_whats_amostra.yaml \
	--export-csv --limit 10
```

Parâmetros úteis do runner:
- `--export-csv` — gera CSV com as colunas pedidas.
- `--limit N` — limita o número de casos executados.
- `--langfuse` — ativa callbacks do Langfuse (quando configurado via env vars).

**5) Variáveis de ambiente importantes**
- `LLM_PROVIDER` — `ollama`, `ollama_cloud`, `openai`, etc.; o `workflow_v2` usa `vizu_llm_service` quando disponível.
- `OLLAMA_BASE_URL` — URL do Ollama local/external (ex: `http://host.docker.internal:11434` ou `http://ollama:11434` no Docker network).
- `OLLAMA_MODEL` — nome do modelo padrão quando usar Ollama no fallback.
- `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` — se você usar Langfuse tracing.

Export example (zsh):

```bash
export OLLAMA_BASE_URL=http://host.docker.internal:11434
export LLM_PROVIDER=ollama_cloud
```

**6) Saída do experimento**
- O runner exporta um CSV contendo por linha um caso de teste com as colunas:
	- `test_id`, `query` (contexto passado para check_negotiation), `description` (justificativa do validator), `extracted` (JSON), `boleta_formatada`, `success`, `duration_ms`, `error`.

**Procedimentos e dicas de troubleshooting**
- Presidio e spaCy: se o anonymizer não detectar nomes, confirme que o modelo `pt_core_news_sm` está instalado e importável em runtime (`python -c "import spacy; spacy.load('pt_core_news_sm')"`).
- Erros de import no container: alguns containers usam um `.venv` embutido; use `docker exec <container> python -m pip install ...` ou execute com o Python do venv.
- Problemas de conexão com Ollama: se ver `ConnectError: No address associated with hostname` ou `Name or service not known`, verifique `OLLAMA_BASE_URL` e se a rede/container com Ollama está ativa. Em macOS local, `host.docker.internal` costuma funcionar a partir de containers.
- Ajuste de taxa: o workflow inclui `time.sleep(3)` antes de cada chamada LLM para reduzir rate-limits; ajuste se precisar mais throughput.

**Como adicionar um novo dataset / manifest**
- Crie um YAML similar a `manifest_whatsapp.yaml` ou `manifest_whats_amostra.yaml` com campos:
	- `workflow_path` (p.ex. `ferramentas.evaluation_suite.workflows.boleta_trader.workflow_v2`)
	- `data_file`, `message_column`, `sender_column`, `conversation_group_column`
	- `trigger_keywords: [fecha, fechado, trava, ...]`

Exemplo mínimo:

```yaml
name: my_test
workflow_path: ferramentas.evaluation_suite.workflows.boleta_trader.workflow_v2
workflow_function: get_workflow
data_file: workflows/boleta_trader/data/processed/whatsapp_test.csv
message_column: message
sender_column: sender
conversation_group_column: test_id
trigger_keywords: [fecha, fechado]
```

**Comandos úteis (resumo)**
- Instalação dependências (local):

```bash
cd ferramentas/evaluation_suite
poetry install
poetry run python -m spacy download pt_core_news_sm
```

- Loader WhatsApp (gera CSV processado):

```bash
poetry run python -m evaluation_suite.data_loaders.whatsapp_loader \
	workflows/boleta_trader/data/raw/chat.txt -o workflows/boleta_trader/data/processed/whatsapp_test.csv
```

- Anonimizar amostra com Presidio:

```bash
poetry run python -m evaluation_suite.data_loaders.pii_anonymizer \
	workflows/boleta_trader/data/raw/whats_amostra.csv \
	-o workflows/boleta_trader/data/processed/whats_amostra_anonymized.csv
```

- Rodar experimento (runner):

```bash
poetry run python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment \
	ferramentas/evaluation_suite/workflows/boleta_trader/manifest_whats_amostra.yaml \
	--export-csv --limit 10
```

**Quando pedir ajuda**
- Se o anonymizer não anonimizar nomes, envie a saída do comando `python -c "import spacy; print(spacy.info('pt_core_news_sm'))"` e as primeiras linhas do CSV raw (`head -n 30 ...`).
- Se o runner falhar com erros de LLM, cole o trecho de log com `ConnectError` e a variável `OLLAMA_BASE_URL` que está usando.

—

Se quiser, eu posso:
- abrir um PR contendo as alterações que fiz (pyproject + anonymizer + workflow sleep + manifests),
- adicionar um exemplo de notebook para inspecionar resultados, ou
- automatizar a criação de amostras e anonimização via um Makefile/recipe.

---
