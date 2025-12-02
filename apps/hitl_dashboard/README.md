# Vizu HITL Dashboard

Dashboard Streamlit para revisão humana de interações do agente.

## Setup

```bash
cd apps/hitl_dashboard
poetry install
```

## Run

```bash
poetry run streamlit run src/app.py
```

## Features

- 📋 Lista de interações pendentes de revisão
- 🔍 Filtros por cliente, critério, data
- ✅ Aprovação/correção de respostas
- 📊 Estatísticas de revisão
- 🔗 Integração com Langfuse para datasets

## Configuração

Variáveis de ambiente:

```env
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://...
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```
